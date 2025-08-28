import time
import random
import re
from urllib.parse import urlparse
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def get_root_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def has_been_crawled(root_url, mongo):
    """Check if a root URL has already been crawled."""
    return mongo.collection.find_one({"root_url": root_url}) is not None


def save_cookies(cookies_list, root_url, mongo):
    """Save all cookies of a website as a single document in MongoDB."""
    if not cookies_list:
        print("No cookies to insert.")
        return

    doc = {
        "root_url": root_url,
        "cookies": cookies_list,
        "timestamp": datetime.now().isoformat()
    }

    mongo.collection.insert_one(doc)
    print(f"Inserted {len(cookies_list)} cookies for {root_url}.")


def handle_cookie_banner(driver):
    """Attempt to click cookie consent buttons if present."""
    consent_selectors = [
        (By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]"),
        (By.XPATH, "//button[text()='Allow all cookies']"),
        (By.XPATH, "//button[text()='Accepter']"),
    ]
    for selector_type, selector_value in consent_selectors:
        try:
            consent_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((selector_type, selector_value))
            )
            if consent_button:
                consent_button.click()
                print("Clicked cookie consent button.")
                time.sleep(random.uniform(2, 4))
                return
        except TimeoutException:
            continue


def navigate_and_scroll(driver, url, max_scrolls=3, scroll_pause_time=2):
    """Navigate, handle cookie banners, scroll the page."""
    if not re.match(r'^https?://', url):
        print(f"Invalid URL format: {url}")
        return False

    try:
        driver.get(url)
        print(f"Navigating to: {url}")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("Page loaded successfully.")

        # Handle cookie banners
        try:
            handle_cookie_banner(driver)
        except Exception as e:
            print(f"Cookie banner handling error: {e}")

        # Scroll simulation
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(max_scrolls):
            driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
            time.sleep(scroll_pause_time + random.uniform(0.5, 1.5))
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    except Exception as e:
        print(f"Error navigating {url}: {e}")
        return False

    return True


def extract_cookies(driver):
    """Extract cookies from the driver."""
    cookies_list = []
    try:
        all_cookies = driver.get_cookies()
        for cookie in all_cookies:
            domain_raw = cookie.get('domain', '').lstrip('.')
            cookies_list.append({
                'Domain': domain_raw,
                'cookie_domain': '.' + domain_raw if domain_raw else '',
                'name': cookie.get('name', ''),
                'value': cookie.get('value', '')
            })
    except Exception as e:
        print(f"Error extracting cookies: {e}")
    return cookies_list
