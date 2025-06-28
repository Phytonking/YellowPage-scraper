import re
import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from time import sleep
from bs4 import BeautifulSoup
from lxml import etree

from tools.functionalities import userAgents, randomTime, verify_yellow, yaml_by_select, yp_lists, create_path


async def yellowPages_playwright(yp_url):
    """
    Playwright-based scraper that can handle Cloudflare protection
    Uses single browser window throughout the process
    """
    async with async_playwright() as p:
        print(f"Starting Yellow Pages scraper for: {yp_url}")
        
        # Launch browser with anti-detection options
        browser = await p.chromium.launch(
            headless=False,  # Set to True for headless mode
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )
        
        page = await context.new_page()
        
        # Load selectors
        scrape = yaml_by_select('selectors')
        
        # First, determine the total number of pages by checking the first page
        print("Determining total number of pages...")
        try:
            response = await page.goto(yp_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_selector('body', timeout=10000)
            await asyncio.sleep(3)
            
            content = await page.content()
            soup = etree.HTML(str(BeautifulSoup(content, 'lxml')))
            
            # Try to detect pagination - look for pagination elements
            pagination_elements = soup.xpath(scrape['pagination'])
            total_pages = 1  # Default to 1 page
            
            if pagination_elements:
                # Extract page numbers from pagination
                page_numbers = []
                for element in pagination_elements:
                    try:
                        # Extract text and try to convert to int
                        text = element.strip()
                        if text.isdigit():
                            page_numbers.append(int(text))
                    except:
                        continue
                
                if page_numbers:
                    total_pages = max(page_numbers)
                    print(f"Detected {total_pages} total pages from pagination")
                else:
                    # Fallback: try to find "Next" button and estimate
                    next_buttons = soup.xpath("//a[contains(text(), 'Next') or contains(@class, 'next')]")
                    if next_buttons:
                        print("Found 'Next' button, will scrape until no more results")
                        total_pages = 100  # Set a reasonable maximum
                    else:
                        print("No pagination detected, assuming single page")
            else:
                print("No pagination elements found, assuming single page")
                
        except Exception as e:
            print(f"Error detecting pagination: {e}")
            total_pages = 50  # Conservative fallback
        
        # Generate page URLs based on detected or estimated page count
        total_page_urls = [f"{yp_url}&page={num}" for num in range(1, total_pages + 1)]
        total_business_urls = []
        
        print(f"Processing up to {len(total_page_urls)} pages...")
        
        for idx, url in enumerate(total_page_urls):
            print(f"Processing page {idx+1}/{len(total_page_urls)}")
            
            try:
                # Navigate to the page
                response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                
                if response.status != 200:
                    print(f"Failed to load page {idx+1}: HTTP {response.status}")
                    continue
                
                # Wait for potential Cloudflare challenge to complete
                try:
                    await page.wait_for_selector('body', timeout=10000)
                    await asyncio.sleep(3)  # Additional wait for JS execution
                except:
                    print("Timeout waiting for content, continuing...")
                
                # Get page content
                content = await page.content()
                
                # Check if blocked by Cloudflare
                if 'cloudflare' in content.lower() or 'checking your browser' in content.lower():
                    print("Detected Cloudflare challenge, waiting...")
                    await asyncio.sleep(10)
                    content = await page.content()
                
                # Parse with BeautifulSoup and lxml
                soup = etree.HTML(str(BeautifulSoup(content, 'lxml')))
                
                # Extract categories
                categories_raw = soup.xpath(scrape['categories'])
                global categories
                categories = f"""{''.join(categories_raw)} in ."""
                
                # Extract page content to check for "No results"
                page_content = ''.join(soup.xpath(scrape['page_content']))
                
                # Check for "No results" pattern
                pattern = re.search("^No results found for.*", page_content)
                
                # Extract business URLs
                business_links_raw = soup.xpath(scrape['business_urls'])
                print(f"Found {len(business_links_raw)} businesses on page {idx+1}")
                
                # If no businesses found, we might have reached the end
                if len(business_links_raw) == 0:
                    print(f"No businesses found on page {idx+1}, stopping pagination")
                    break
                
                business_links = [f"https://www.yellowpages.com{link}" for link in business_links_raw]
                total_business_urls.extend(business_links)
                
                if pattern is not None:
                    print("No results found, stopping search")
                    break
                
                # Add delay between pages
                if idx > 0:
                    await asyncio.sleep(2)
                    
            except Exception as e:
                print(f"Error processing page {idx+1}: {e}")
                continue
        
        await browser.close()
        
        print(f"Total business URLs found: {len(total_business_urls)}")
        return total_business_urls


async def scrapeBusiness_single(page, url, scrape):
    """Scrape individual business using shared page"""
    yellow_in_dicts = []
    
    try:
        response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        if response.status != 200:
            print(f"Failed to load business page: HTTP {response.status}")
            return yellow_in_dicts
        
        # Wait for content
        await page.wait_for_selector('body', timeout=10000)
        content = await page.content()
        
        # Debug: Check content length and basic structure
        print(f"DEBUG: Content length for business page: {len(content)}")
        
        # Check if we're blocked by Cloudflare on business page
        if 'cloudflare' in content.lower() or 'checking your browser' in content.lower():
            print("DEBUG: Detected Cloudflare challenge on business page, waiting...")
            await asyncio.sleep(10)
            content = await page.content()
            print(f"DEBUG: Content length after Cloudflare wait: {len(content)}")
        
        # Parse content with better error handling
        bs_soup = BeautifulSoup(content, 'lxml')
        if not bs_soup or not bs_soup.body:
            print(f"DEBUG: BeautifulSoup failed to parse content or no body found")
            return yellow_in_dicts
        
        # Try multiple parsing approaches
        soup = None
        try:
            # First attempt: standard etree.HTML
            soup = etree.HTML(str(bs_soup))
        except Exception as e:
            print(f"DEBUG: First etree.HTML attempt failed: {e}")
            try:
                # Second attempt: parse directly from content
                soup = etree.HTML(content)
            except Exception as e2:
                print(f"DEBUG: Second etree.HTML attempt failed: {e2}")
                try:
                    # Third attempt: clean the HTML first
                    cleaned_html = str(bs_soup).encode('utf-8', 'ignore').decode('utf-8')
                    soup = etree.HTML(cleaned_html)
                except Exception as e3:
                    print(f"DEBUG: Third etree.HTML attempt failed: {e3}")
        
        if soup is None:
            print(f"DEBUG: All HTML parsing attempts failed, trying BeautifulSoup fallback")
            # Fallback: use BeautifulSoup directly with CSS selectors
            try:
                # Convert XPath selectors to approximate CSS selectors
                business_names = ""
                contact = ""
                email = ""
                address = ""
                
                # Try to find business name with different selectors
                name_element = bs_soup.find('h1', class_='dockable business-name')
                if name_element:
                    business_names = name_element.get_text(strip=True)
                else:
                    # Try alternative selectors
                    name_element = bs_soup.find('h1') or bs_soup.find('h2') or bs_soup.find('h3')
                    if name_element:
                        business_names = name_element.get_text(strip=True)
                
                # Try to find contact
                contact_element = bs_soup.find('a', class_='phone dockable')
                if contact_element:
                    contact_strong = contact_element.find('strong')
                    if contact_strong:
                        contact = contact_strong.get_text(strip=True)
                
                print(f"DEBUG: BeautifulSoup fallback found business: '{business_names}'")
                
                datas = {
                    "Business": business_names,
                    "Contact": contact,
                    "Email": email,
                    "Address": address,
                    "Map and direction": f"https://www.yellowpages.com",
                    "Review": "",
                    "Review count": "",
                    "Hyperlink": url,
                    "Images": "",
                    "Website": "",
                }
                yellow_in_dicts.append(datas)
                
            except Exception as fallback_error:
                print(f"DEBUG: BeautifulSoup fallback also failed: {fallback_error}")
                return yellow_in_dicts
        else:
            # Standard XPath extraction
            # Try to extract business name first to check if page structure is correct
            business_names = ''.join(soup.xpath(scrape['business_name']))
            if not business_names:
                print(f"DEBUG: No business name found, page might have different structure")
                # Let's check what the page title is
                title_elements = soup.xpath('//title/text()')
                print(f"DEBUG: Page title: {title_elements}")
            
            datas = {
                "Business": business_names,
                "Contact": ''.join(soup.xpath(scrape['contact'])),
                "Email": ''.join(soup.xpath(scrape['email'])).replace("mailto:", ""),
                "Address": ''.join(soup.xpath(scrape['address'])),
                "Map and direction": f"https://www.yellowpages.com{''.join(soup.xpath(scrape['map_and_direction']))}",
                "Review": ''.join(soup.xpath(scrape['review'])).replace("rating-stars ", ""),
                "Review count": re.sub(r"[()]", "", ''.join(soup.xpath(scrape['review_count']))),
                "Hyperlink": url,
                "Images": ''.join(soup.xpath(scrape['images'])),
                "Website": ''.join(soup.xpath(scrape['website'])),
            }
            yellow_in_dicts.append(datas)
        
    except Exception as e:
        print(f"Error scraping business {url}: {e}")
        print(f"DEBUG: Exception type: {type(e).__name__}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
    
    return yellow_in_dicts


async def scrapeMe_playwright(url_lists, state_info=None):
    """Main scraping function using single Playwright browser window"""
    yellow_in_dicts = []
    
    # Determine filename based on state info or categories
    if state_info:
        state_name = state_info.get('name', 'Unknown')
        state_code = state_info.get('code', 'XX')
        filename_prefix = f"{state_name.replace(' ', '_')}_{state_code}"
        print(f"Scraping restaurants in {state_name} ({state_code}). Number of businesses: {len(url_lists)}")
    else:
        filename_prefix = f"{categories}" if 'categories' in globals() else "YellowPages_Data"
        print(f"Scraping {categories}. Number of businesses: {len(url_lists)}")
    
    # Use single browser instance for all business scraping
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Set to True for headless mode
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        scrape = yaml_by_select('selectors')
        
        # Process businesses sequentially to maintain single window
        for idx, url in enumerate(url_lists):
            bizz_name = ' '.join(url.split("/")[-1].split("?")[0].split("-")[:-1])
            if state_info:
                print(f"Scraping ({idx+1}/{len(url_lists)}) in {state_info['name']}: {bizz_name}")
            else:
                print(f"Scraping ({idx+1}/{len(url_lists)}): {bizz_name}")
            
            result = await scrapeBusiness_single(page, url, scrape)
            yellow_in_dicts += result
            
            # Small delay between requests
            await asyncio.sleep(1)
        
        await browser.close()

    # Save results
    create_path('Yellowpage database')
    df = pd.DataFrame(yellow_in_dicts)
    
    # Save with state-specific filename if state info provided
    excel_filename = f'Yellowpage database//{filename_prefix}.xlsx'
    df.to_excel(excel_filename, index=False)
    print(f'Scraping complete. Results saved to: {excel_filename}')
    
    return yellow_in_dicts


async def all_business_urls_playwright(url):
    """Wrapper function for Playwright scraper"""
    return await yellowPages_playwright(url) 