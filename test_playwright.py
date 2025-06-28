import asyncio
import time
from scrapers.yp_scraper_playwright import all_business_urls_playwright, scrapeMe_playwright


if __name__ == "__main__":
    start_time = time.time()
    
    async def main():
        # Use the correct HTTPS URL format
        url = "https://www.yellowpages.com/search?search_terms=restaurants&geo_location_terms=WA"
        print(f"DEBUG: Using URL: {url}")
        
        print("Scraping Business urls with Playwright. Please wait..")
        bizz_urls = await all_business_urls_playwright(url)
        print(f"DEBUG: Found {len(bizz_urls)} business URLs")
        print(f"DEBUG: First few URLs: {bizz_urls[:3] if bizz_urls else 'None'}")
        
        if not bizz_urls:
            print("DEBUG: No business URLs found, stopping here")
            return None
            
        print("Scraping business data...")
        scrape_datas = await scrapeMe_playwright(bizz_urls)        
        return scrape_datas

    result = asyncio.run(main())
    print(f"Final result: {result}")

    total_time = round(time.time()-start_time, 2)
    time_in_secs = round(total_time)
    time_in_mins = round(total_time/60)

    print(f"Took {time_in_secs} seconds | {time_in_mins} minutes.") 