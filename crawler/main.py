import os
import time
import random
import pandas as pd
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from utils.mongo_driver import MongoDriver
from crawler.crawler import (
    get_root_url, has_been_crawled, save_cookies,
    navigate_and_scroll, extract_cookies
)


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


def crawl_urls(urls, mongo: MongoDriver):
    all_cookies = []
    driver = initialize_driver(headless=True)

    try:
        for i, url in enumerate(urls):
            root_url = get_root_url(url)
            if has_been_crawled(root_url, mongo):
                print(f"Skipping {url} (already crawled).")
                continue

            print(f"\n--- Processing {i+1}/{len(urls)}: {url} ---")
            if navigate_and_scroll(driver, url, max_scrolls=5, scroll_pause_time=2):
                cookies = extract_cookies(driver)
                if cookies:
                    save_cookies(cookies, root_url, mongo)
                    all_cookies.extend(cookies)
            else:
                print(f"Failed to crawl {url}")
            time.sleep(random.uniform(5, 10))
    finally:
        driver.quit()

    save_to_csv(all_cookies)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cookie Crawler")
    parser.add_argument("--input", type=str, help="Path to file with URLs (one per line)")
    parser.add_argument("--url", type=str, help="Single URL to crawl")
    args = parser.parse_args()

    if args.input and os.path.exists(args.input):
        with open(args.input, "r") as f:
            raw_urls = [line.strip() for line in f if line.strip()]
    elif args.url:
        raw_urls = [args.url]
    else:
        print("Error: Provide either --input or --url")
        exit()

    print(f"Loaded {len(raw_urls)} URLs.")

    mongo = MongoDriver(db_name="scraperdb", collection="crawled_cookies")
    crawl_urls(raw_urls, mongo)
