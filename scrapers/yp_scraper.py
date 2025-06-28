import re
import asyncio
import aiohttp
import requests
import pandas as pd
from lxml import etree
from time import sleep
from bs4 import BeautifulSoup

from tools.functionalities import userAgents, randomTime, verify_yellow, yaml_by_select, yp_lists,create_path
       
   
async def yellowPages(yp_url): # play parameter is for playwright | heads parameter is for switching a browser headless.       
    # Try to bypass Cloudflare with better browser mimicking
    connector = aiohttp.TCPConnector(ssl=False, limit=1, limit_per_host=1)
    timeout = aiohttp.ClientTimeout(total=60)
    
    # Create a session that looks more like a real browser
    async with aiohttp.ClientSession(
        connector=connector, 
        timeout=timeout,
        cookie_jar=aiohttp.CookieJar(),
        headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }
    ) as session:
        print(f"DEBUG: Starting yellowPages with URL: {yp_url}")
        
        # if verify_yellow(yp_url):
        #     return "Invalid link"

        scrape = yaml_by_select('selectors')    
        print(f"DEBUG: Business URL selector: {scrape['business_urls']}")

        # 101 is just a random number. The scraper will exist if there are no contents.
        total_page_urls = yp_lists(yp_url)
        total_business_urls = []

        # Iterating and using beautifulsoup to extract all business urls:
        for idx, url in enumerate(total_page_urls):      
            print(f"DEBUG: Processing page {idx+1}/{len(total_page_urls)}: {url}")
            try:                
                headers = {
                    'User-Agent': userAgents(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Referer': 'https://www.yellowpages.com/',
                    'Cache-Control': 'max-age=0'
                }
                async with session.get(url, headers=headers) as response:
                    print(f"DEBUG: HTTP Status for page {idx+1}: {response.status}")
                    
                    if response.status != 200:
                        print(f"DEBUG: Non-200 status code, skipping page")
                        continue
                        
                    # sleep(randomTime(interval))
                    # Making soup and using LXML for xpath approach:
                    response_text = await response.text()
                    print(f"DEBUG: Response text length: {len(response_text)}")
                    
                    soup = etree.HTML(str(BeautifulSoup(response_text, 'lxml')))
                    
                    global categories
                    categories_raw = soup.xpath(scrape['categories'])
                    print(f"DEBUG: Categories found: {categories_raw}")
                    categories = f"""{''.join(categories_raw)} in ."""
                    
                    page_content = ''.join(soup.xpath(scrape['page_content']))
                    print(f"DEBUG: Page content: {page_content[:100]}...")

                    # If the search_words contains 'No results' then script will exit. I approach this step if user type a gibberish word or the search word doesn't exist.
                    pattern = re.search("^No results found for.*", page_content)  
                    
                    business_links_raw = soup.xpath(scrape['business_urls'])
                    print(f"DEBUG: Raw business links found: {len(business_links_raw)}")
                    print(f"DEBUG: First few raw links: {business_links_raw[:3]}")
                    
                    business_links = [f"https://www.yellowpages.com{link}" for link in business_links_raw]
                    print(f"DEBUG: Processed business links: {len(business_links)}")
                    total_business_urls.extend(business_links)
                    
                    if pattern != None: 
                        print(f"DEBUG: 'No results' pattern found: {pattern}")
                        print(f"No content. Please try again in few minutes.")           
                        break
                    
                    # Add delay between requests to avoid rate limiting
                    if idx > 0:
                        sleep(randomTime(3))  # 1-3 seconds delay
                    
                    # Stop after first page for debugging
                    if idx == 0:
                        print(f"DEBUG: Stopping after first page for debugging")
                        break                           
            except (requests.exceptions.ConnectTimeout, aiohttp.ClientError) as e:
                print(f"DEBUG: Connection error on page {idx+1}: {e}")
                print(f"Connection error. Skipping url {url}")
                break
            except Exception as e:
                print(f"DEBUG: Unexpected error on page {idx+1}: {e}")
                break                  
            
        print(f"DEBUG: Final total business URLs found: {len(total_business_urls)}")
        return total_business_urls
    

async def all_business_urls(url):
    boy_task = await asyncio.create_task(yellowPages(url))
    return boy_task

    
async def scrapeBusiness(urls):
    scrape = yaml_by_select('selectors')
    # responses = await all_business_urls(urls)
    yellow_in_dicts = []
    async with aiohttp.ClientSession() as session:        
        async with session.get(urls, headers={'User-Agent': userAgents()}) as response:  
            # sleep(2)      
            content = await response.read()
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
        return yellow_in_dicts


async def scrapeMe(url_lists):    
    yellow_in_dicts = []
    print(f"Scraping | {categories}. Number of business | {len(url_lists)}. Please wait.")
    
    tasks =[]
    for url in url_lists:
        bizz_name = ' '.join(url.split("/")[-1].split("?")[0].split("-")[:-1])
        sleep(.5)
        print(f"Scraping business: {bizz_name}")
        tasks.append(scrapeBusiness(url))
    # tasks = [scrapeBusiness(url) for url in url_lists]    
    results = await asyncio.gather(*tasks)
    for res in results:
        yellow_in_dicts += res

    create_path('Yellowpage database')
    df = pd.DataFrame(yellow_in_dicts)
    df.to_excel(f'Yellowpage database//{categories}.xlsx', index=False)
    print('Scraping complete.')

