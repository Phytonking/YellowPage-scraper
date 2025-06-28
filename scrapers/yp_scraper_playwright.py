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
    """
    async with async_playwright() as p:
        print(f"DEBUG: Starting Playwright yellowPages with URL: {yp_url}")
        
        # Launch browser with options to avoid detection
        browser = await p.chromium.launch(
            headless=False,  # Set to True once working
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
        print(f"DEBUG: Business URL selector: {scrape['business_urls']}")
        
        # Generate page URLs - limit for testing or use all
        total_page_urls = yp_lists(yp_url)[:5]  # Test first 5 pages, change to [:] for all pages
        total_business_urls = []
        
        for idx, url in enumerate(total_page_urls):
            print(f"DEBUG: Processing page {idx+1}/{len(total_page_urls)}: {url}")
            
            try:
                # Navigate to the page
                response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                print(f"DEBUG: HTTP Status for page {idx+1}: {response.status}")
                
                if response.status != 200:
                    print(f"DEBUG: Non-200 status code, skipping page")
                    continue
                
                # Wait for potential Cloudflare challenge to complete
                try:
                    # Wait for either content to load or Cloudflare challenge
                    await page.wait_for_selector('body', timeout=10000)
                    await asyncio.sleep(3)  # Additional wait for any JS to execute
                except:
                    print("DEBUG: Timeout waiting for content, continuing anyway")
                
                # Get page content
                content = await page.content()
                print(f"DEBUG: Page content length: {len(content)}")
                
                # Check if we're blocked by Cloudflare
                if 'cloudflare' in content.lower() or 'checking your browser' in content.lower():
                    print("DEBUG: Detected Cloudflare challenge page")
                    # Wait longer for Cloudflare to resolve
                    await asyncio.sleep(10)
                    content = await page.content()
                    print(f"DEBUG: Content length after waiting for Cloudflare: {len(content)}")
                
                # Parse with BeautifulSoup and lxml
                soup = etree.HTML(str(BeautifulSoup(content, 'lxml')))
                
                # Extract categories
                categories_raw = soup.xpath(scrape['categories'])
                print(f"DEBUG: Categories found: {categories_raw}")
                global categories
                categories = f"""{''.join(categories_raw)} in ."""
                
                # Extract page content to check for "No results"
                page_content = ''.join(soup.xpath(scrape['page_content']))
                print(f"DEBUG: Page content: {page_content[:100]}...")
                
                # Check for "No results" pattern
                pattern = re.search("^No results found for.*", page_content)
                
                # Extract business URLs
                business_links_raw = soup.xpath(scrape['business_urls'])
                print(f"DEBUG: Raw business links found: {len(business_links_raw)}")
                print(f"DEBUG: First few raw links: {business_links_raw[:3]}")
                
                business_links = [f"https://www.yellowpages.com{link}" for link in business_links_raw]
                print(f"DEBUG: Processed business links: {len(business_links)}")
                total_business_urls.extend(business_links)
                
                if pattern is not None:
                    print(f"DEBUG: 'No results' pattern found: {pattern}")
                    print(f"No content. Please try again in few minutes.")
                    break
                
                # Add small delay between pages
                if idx > 0:
                    await asyncio.sleep(2)
                    
            except Exception as e:
                print(f"DEBUG: Error processing page {idx+1}: {e}")
                continue
        
        await browser.close()
        
        print(f"DEBUG: Final total business URLs found: {len(total_business_urls)}")
        return total_business_urls


async def all_business_urls_playwright(url):
    """Wrapper function for Playwright scraper"""
    return await yellowPages_playwright(url)


async def scrapeBusiness_playwright_single(page, urls, scrape):
    """Playwright-based individual business scraper using shared page"""
    yellow_in_dicts = []
    
    try:
        response = await page.goto(urls, wait_until='domcontentloaded', timeout=60000)
        
        if response.status != 200:
            print(f"DEBUG: Failed to load business page: {response.status}")
            return yellow_in_dicts
        
        # Wait for content
        await page.wait_for_selector('body', timeout=10000)
        content = await page.content()
        
        # Parse content
        soup = etree.HTML(str(BeautifulSoup(content, 'lxml')))
        
        business_names = ''.join(soup.xpath(scrape['business_name']))
        datas = {
            "Business": business_names,
            "Contact": ''.join(soup.xpath(scrape['contact'])),
            "Email": ''.join(soup.xpath(scrape['email'])).replace("mailto:", ""),
            "Address": ''.join(soup.xpath(scrape['address'])),
            "Map and direction": ''.join(f'''https://www.yellowpages.com{soup.xpath(scrape['map_and_direction'])}'''),
            "Review": ''.join(soup.xpath(scrape['review'])).replace("rating-stars ", ""),
            "Review count": re.sub(r"[()]", "", ''.join(soup.xpath(scrape['review_count']))),
            "Hyperlink": urls,
            "Images": ''.join(soup.xpath(scrape['images'])),
            "Website": ''.join(soup.xpath(scrape['website'])),
        }
        yellow_in_dicts.append(datas)
        
    except Exception as e:
        print(f"DEBUG: Error scraping business {urls}: {e}")
    
    return yellow_in_dicts


async def scrapeMe_playwright(url_lists):
    """Main scraping function using Playwright with single browser window"""
    yellow_in_dicts = []
    print(f"Scraping | {categories}. Number of business | {len(url_lists)}. Please wait.")
    
    # Use single browser instance for all business scraping
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
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
        for url in url_lists:
            bizz_name = ' '.join(url.split("/")[-1].split("?")[0].split("-")[:-1])
            print(f"Scraping business: {bizz_name}")
            
            result = await scrapeBusiness_playwright_single(page, url, scrape)
            yellow_in_dicts += result
            
            # Small delay between requests
            await asyncio.sleep(1)
        
        await browser.close()

    create_path('Yellowpage database')
    df = pd.DataFrame(yellow_in_dicts)
    df.to_excel(f'Yellowpage database//{categories}.xlsx', index=False)
    print('Scraping complete.')
    
    return yellow_in_dicts 