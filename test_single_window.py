import asyncio
import time
import os
from datetime import datetime
from scrapers.yp_scraper_clean import all_business_urls_playwright, scrapeMe_playwright


# All 50 US states with their abbreviations
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
}


async def scrape_state_restaurants(state_code, state_name):
    """
    Scrape all restaurants from a specific state
    """
    print(f"\n{'='*80}")
    print(f"🏛️  SCRAPING {state_name.upper()} ({state_code}) RESTAURANTS")
    print(f"{'='*80}")
    
    state_start_time = time.time()
    
    # Generate URL for the state
    url = f"https://www.yellowpages.com/search?search_terms=restaurants&geo_location_terms={state_code}"
    print(f"URL: {url}")
    
    try:
        # Get all business URLs for this state
        print(f"🔍 Finding all restaurant URLs in {state_name}...")
        all_bizz_urls = await all_business_urls_playwright(url)
        
        if not all_bizz_urls:
            print(f"❌ No restaurants found in {state_name}")
            return {
                'state': state_name,
                'state_code': state_code,
                'total_found': 0,
                'total_scraped': 0,
                'status': 'no_results',
                'time_taken': 0
            }
        
        print(f"✅ Found {len(all_bizz_urls)} restaurants in {state_name}")
        
        # Scrape all businesses from this state (no user intervention)
        print(f"🏃‍♂️ Scraping ALL {len(all_bizz_urls)} restaurants from {state_name}...")
        
        # Pass state information to scraper for proper file naming
        state_info = {'name': state_name, 'code': state_code}
        scrape_data = await scrapeMe_playwright(all_bizz_urls, state_info)
        
        state_time = round(time.time() - state_start_time, 2)
        
        result = {
            'state': state_name,
            'state_code': state_code,
            'total_found': len(all_bizz_urls),
            'total_scraped': len(scrape_data) if scrape_data else 0,
            'status': 'completed',
            'time_taken': state_time
        }
        
        print(f"✅ {state_name} COMPLETED!")
        print(f"   📊 Found: {result['total_found']} restaurants")
        print(f"   📋 Scraped: {result['total_scraped']} restaurants")
        print(f"   ⏱️  Time: {state_time} seconds")
        
        return result
        
    except Exception as e:
        print(f"❌ ERROR scraping {state_name}: {e}")
        state_time = round(time.time() - state_start_time, 2)
        return {
            'state': state_name,
            'state_code': state_code,
            'total_found': 0,
            'total_scraped': 0,
            'status': f'error: {str(e)}',
            'time_taken': state_time
        }


async def scrape_all_states():
    """
    Scrape restaurants from all 50 US states
    """
    print(f"🇺🇸 STARTING NATIONWIDE RESTAURANT SCRAPING")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target: All 50 US states")
    print(f"🍽️  Category: Restaurants")
    
    overall_start_time = time.time()
    state_results = []
    
    # Create results directory
    results_dir = f"USA_Restaurants_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(results_dir, exist_ok=True)
    
    total_states = len(US_STATES)
    completed_states = 0
    
    for state_code, state_name in US_STATES.items():
        try:
            print(f"\n🏁 PROGRESS: {completed_states}/{total_states} states completed")
            print(f"⏳ Estimated time remaining: {((time.time() - overall_start_time) / max(completed_states, 1)) * (total_states - completed_states) / 60:.1f} minutes")
            
            # Scrape this state
            state_result = await scrape_state_restaurants(state_code, state_name)
            state_results.append(state_result)
            completed_states += 1
            
            # Save intermediate results after each state
            with open(f"{results_dir}/progress_summary.txt", "w") as f:
                f.write(f"USA Restaurant Scraping Progress\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Progress: {completed_states}/{total_states} states\n\n")
                
                total_found = sum(r['total_found'] for r in state_results)
                total_scraped = sum(r['total_scraped'] for r in state_results)
                
                f.write(f"SUMMARY SO FAR:\n")
                f.write(f"Total Restaurants Found: {total_found:,}\n")
                f.write(f"Total Restaurants Scraped: {total_scraped:,}\n\n")
                
                f.write("STATE DETAILS:\n")
                for result in state_results:
                    f.write(f"{result['state']:<20} | Found: {result['total_found']:>6} | Scraped: {result['total_scraped']:>6} | Status: {result['status']}\n")
            
            print(f"💾 Progress saved to {results_dir}/progress_summary.txt")
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR processing {state_name}: {e}")
            state_results.append({
                'state': state_name,
                'state_code': state_code,
                'total_found': 0,
                'total_scraped': 0,
                'status': f'critical_error: {str(e)}',
                'time_taken': 0
            })
            completed_states += 1
            continue
    
    # Final summary
    total_time = round(time.time() - overall_start_time, 2)
    total_found = sum(r['total_found'] for r in state_results)
    total_scraped = sum(r['total_scraped'] for r in state_results)
    
    print(f"\n🎉 NATIONWIDE SCRAPING COMPLETED!")
    print(f"{'='*80}")
    print(f"📊 FINAL RESULTS:")
    print(f"   🏛️  States Processed: {len(state_results)}/50")
    print(f"   🍽️  Total Restaurants Found: {total_found:,}")
    print(f"   📋 Total Restaurants Scraped: {total_scraped:,}")
    print(f"   ⏱️  Total Time: {total_time/3600:.1f} hours ({total_time/60:.1f} minutes)")
    print(f"   💾 Results saved in: {results_dir}/")
    
    # Save final summary
    with open(f"{results_dir}/FINAL_SUMMARY.txt", "w") as f:
        f.write(f"🇺🇸 USA RESTAURANT SCRAPING - FINAL REPORT\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"⏱️  Total Duration: {total_time/3600:.2f} hours\n")
        f.write(f"🏛️  States Processed: {len(state_results)}/50\n")
        f.write(f"🍽️  Total Restaurants Found: {total_found:,}\n")
        f.write(f"📋 Total Restaurants Scraped: {total_scraped:,}\n\n")
        
        f.write(f"STATE-BY-STATE BREAKDOWN:\n")
        f.write(f"{'State':<20} | {'Found':<8} | {'Scraped':<8} | {'Time(min)':<10} | Status\n")
        f.write(f"{'-'*80}\n")
        
        for result in sorted(state_results, key=lambda x: x['total_found'], reverse=True):
            f.write(f"{result['state']:<20} | {result['total_found']:>8,} | {result['total_scraped']:>8,} | {result['time_taken']/60:>8.1f} | {result['status']}\n")
    
    return state_results


if __name__ == "__main__":
    print("🚀 INITIALIZING USA-WIDE RESTAURANT SCRAPER")
    print("⚠️  WARNING: This will scrape restaurants from ALL 50 states!")
    print("⚠️  This process may take many hours to complete.")
    print("⚠️  Results will be saved automatically as we progress.")
    
    # Start the nationwide scraping
    start_time = time.time()
    results = asyncio.run(scrape_all_states())
    total_time = round(time.time() - start_time, 2)
    
    print(f"\n🏁 MISSION ACCOMPLISHED!")
    print(f"⏱️  Total mission time: {total_time/3600:.2f} hours")
    print(f"🎯 Check the results directory for all data files!") 