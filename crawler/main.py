import os
import time
import random
import pandas as pd
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from utils.mongo_driver import MongoDriver
from crawler.crawler import CookieCrawler

def initialize_driver(headless=True):
    """Initialize Selenium WebDriver."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    driver.implicitly_wait(10)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def save_to_csv(all_cookies, output_file="collected_cookies.csv"):
    """Save cookies to CSV."""
    if not all_cookies:
        return
    df = pd.DataFrame(all_cookies)
    target_columns = ['Domain', 'cookie_domain', 'name', 'value']
    df = df.reindex(columns=target_columns, fill_value=None)
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Cookies saved to {output_file}")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Cookie Crawler")
    parser.add_argument("--input", type=str, default="urls.txt", help="Path to file with URLs (one per line)")
    parser.add_argument("--url", type=str, help="Single URL to crawl")
    parser.add_argument("--output", type=str, default="collected_cookies.csv", help="Output CSV file path")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode with sample URL")
    return parser.parse_args()

def load_urls(args):
    """Load URLs based on input parameters."""
    if args.debug:
        return ["https://digikala.com"]
    elif args.input and os.path.exists(args.input):
        with open(args.input, "r") as f:
            return [line.strip() for line in f if line.strip()]
    elif args.url:
        return [args.url]
    else:
        raise ValueError("Provide either --input, --url, or enable --debug mode")

def setup_crawler() -> CookieCrawler:
    """Initialize database connection and crawler instance."""
    mongo = MongoDriver(collection="crawled_cookies")
    return CookieCrawler(mongo)

def execute_crawl(crawler : CookieCrawler, driver, urls):
    """Execute the crawling process for all URLs."""
    all_cookies = []
    for i, url in enumerate(urls):
        root_url = crawler.get_root_url(url)
        if crawler.has_been_crawled(root_url):
            print(f"Skipping {url} (already crawled).")
            continue
            
        print(f"\n--- Processing {i+1}/{len(urls)}: {url} ---")
        if crawler.navigate_and_interact(driver, url, max_scrolls=5, scroll_pause_time=2):
            cookies = crawler.extract_cookies(driver)
            if cookies:
                crawler.save_cookies(cookies, root_url)
                all_cookies.extend(cookies)
        else:
            print(f"Failed to crawl {url}")
            
        time.sleep(random.uniform(5, 10))
    return all_cookies

def main():
    args = parse_arguments()
    urls = load_urls(args)
    print(f"Loaded {len(urls)} URLs.")
    
    driver = initialize_driver(headless=True)
    crawler = setup_crawler()
    
    try:
        all_cookies = execute_crawl(crawler, driver, urls)
    finally:
        driver.quit()
        
    save_to_csv(all_cookies, args.output)

if __name__ == "__main__":
    main()
