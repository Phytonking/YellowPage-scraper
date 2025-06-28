import re
import os
import yaml
import random


def yp_lists(yp_url, max_pages=100):
    """
    Generate page URLs for pagination
    
    Args:
        yp_url: Base URL for Yellow Pages search
        max_pages: Maximum number of pages to generate (default: 100)
    
    Returns:
        List of page URLs
    """
    total_page_urls = [f"{yp_url}&page={num}" for num in range(1, max_pages + 1)]
    print(f"DEBUG: Generated {len(total_page_urls)} page URLs (max_pages={max_pages})")
    print(f"DEBUG: First few URLs: {total_page_urls[:3]}")
    return total_page_urls

# random time interval between each requests made to server:
# You can decrease the time interval for faster scraping however I discourage you to do so as it may hurt the server.
# Scrape responsibly:
def randomTime(val):
    ranges = [i for i in range(2, val+1)]
    return random.randint(0,len(ranges))


# Hundreds of thousands of user agents for server:
def userAgents():
    with open('user-agents.txt') as f:
        agents = f.read().split("\n")
        return random.choice(agents)
    

def verify_yellow(yp_url):    
    yp_pattern = re.search("""^(https://|www\.|yellowpages).com/.+""", yp_url)
    if yp_pattern == None:
        return True
    else:
        return False


def yaml_by_select(selectors):
    with open(f"scrapers//{selectors}.yml") as file:
        sel = yaml.load(file, Loader=yaml.SafeLoader)
        print(f"DEBUG: Loaded YAML selectors: {list(sel.keys())}")
        return sel


def create_path(dir_name):
    path_name = os.path.join(os.getcwd(), dir_name)
    if os.path.exists(path_name):
        pass
    else:
        os.mkdir(path_name)