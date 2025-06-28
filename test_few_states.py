import asyncio
import time
import os
from datetime import datetime
from scrapers.yp_scraper_clean import all_business_urls_playwright, scrapeMe_playwright


# Test with just a few states first
TEST_STATES = {
    'AL': 'Alabama',      # Small state - good for testing
    'DE': 'Delaware',     # Very small state - quick test
    'VT': 'Vermont',      # Small state
    'WY': 'Wyoming',      # Smallest population - fastest
    'NH': 'New Hampshire' # Small state
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


async def test_scrape_few_states():
    """
    Test scraping with just a few small states
    """
    print(f"🧪 TESTING WITH {len(TEST_STATES)} SMALL STATES")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target: {', '.join(TEST_STATES.values())}")
    print(f"🍽️  Category: Restaurants")
    
    overall_start_time = time.time()
    state_results = []
    
    # Create results directory
    results_dir = f"TEST_Restaurants_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(results_dir, exist_ok=True)
    
    total_states = len(TEST_STATES)
    completed_states = 0
    
    for state_code, state_name in TEST_STATES.items():
        try:
            print(f"\n🏁 PROGRESS: {completed_states}/{total_states} states completed")
            
            # Scrape this state
            state_result = await scrape_state_restaurants(state_code, state_name)
            state_results.append(state_result)
            completed_states += 1
            
            # Save intermediate results after each state
            with open(f"{results_dir}/test_progress.txt", "w") as f:
                f.write(f"TEST Restaurant Scraping Progress\n")
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
            
            print(f"💾 Progress saved to {results_dir}/test_progress.txt")
            
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
    
    print(f"\n🎉 TEST SCRAPING COMPLETED!")
    print(f"{'='*80}")
    print(f"📊 TEST RESULTS:")
    print(f"   🏛️  States Tested: {len(state_results)}/{len(TEST_STATES)}")
    print(f"   🍽️  Total Restaurants Found: {total_found:,}")
    print(f"   📋 Total Restaurants Scraped: {total_scraped:,}")
    print(f"   ⏱️  Total Time: {total_time/60:.1f} minutes")
    print(f"   💾 Results saved in: {results_dir}/")
    
    # Estimate for full 50-state operation
    avg_time_per_state = total_time / len(state_results) if state_results else 0
    estimated_full_time = avg_time_per_state * 50
    avg_restaurants_per_state = total_found / len(state_results) if state_results else 0
    estimated_total_restaurants = avg_restaurants_per_state * 50
    
    print(f"\n📈 ESTIMATES FOR FULL 50-STATE OPERATION:")
    print(f"   ⏱️  Estimated Total Time: {estimated_full_time/3600:.1f} hours")
    print(f"   🍽️  Estimated Total Restaurants: {estimated_total_restaurants:,.0f}")
    print(f"   💾 Estimated File Size: {estimated_total_restaurants * 2 / 1000:.0f} MB")
    
    return state_results


if __name__ == "__main__":
    print("🧪 TESTING USA RESTAURANT SCRAPER")
    print("⚠️  This will test with just 5 small states first")
    print("⚠️  Use this to validate the system before running all 50 states")
    
    # Start the test scraping
    start_time = time.time()
    results = asyncio.run(test_scrape_few_states())
    total_time = round(time.time() - start_time, 2)
    
    print(f"\n🏁 TEST COMPLETED!")
    print(f"⏱️  Total test time: {total_time/60:.2f} minutes")
    print(f"🎯 If this test looks good, run: python test_single_window.py")
    print(f"🎯 For the full 50-state operation!") 