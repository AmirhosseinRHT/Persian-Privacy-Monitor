import time
import random
import re
from urllib.parse import urlparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

class CookieCrawler:
    def __init__(self, mongo_driver):
        self.mongo = mongo_driver
        
    def get_root_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def has_been_crawled(self, root_url):
        """Check if a root URL has already been crawled."""
        return self.mongo.collection.find_one({"url": root_url}) is not None
    
    def save_cookies(self, cookies_list, root_url):
        """Save all cookies of a website as a single document in MongoDB."""
        doc = {
            "url": root_url,
            "cookies": cookies_list,
            "timestamp": datetime.now().isoformat()
        }
        self.mongo.collection.insert_one(doc)
        print(f"Inserted {len(cookies_list)} cookies for {root_url}.")
    
    def initialize_driver(self, headless=True):
        """Initialize Chrome WebDriver with anti-detection measures."""
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
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ]
        chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        driver.implicitly_wait(10)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    
    def handle_cookie_banner(self, driver):
        """Attempt to click cookie consent buttons with multiple strategies."""
        consent_selectors = [
            (By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok') or contains(@aria-label, 'accept') or contains(@title, 'accept')]"),
            (By.CSS_SELECTOR, "button[id*='cookie'][id*='accept'], a[id*='cookie'][id*='accept'], button[class*='cookie'][class*='accept'], a[class*='cookie'][class*='accept']"),
            (By.XPATH, "//div[contains(@class, 'cookie-consent')]//button | //div[contains(@id, 'cookie-consent')]//button"),
            (By.XPATH, "//button[text()='Allow all cookies']"),
            (By.XPATH, "//button[text()='Accepter']"),
            (By.XPATH, "//button[contains(text(), 'قبول')]"),
            (By.XPATH, "//button[contains(text(), 'متوجه شدم')]")
        ]
        
        consent_button = None
        for selector_type, selector_value in consent_selectors:
            try:
                consent_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                if consent_button:
                    print(f"Found cookie consent button: {selector_value}")
                    break
            except TimeoutException:
                continue
        
        if consent_button:
            try:
                consent_button.click()
                print("Clicked cookie consent button.")
                time.sleep(random.uniform(2, 4))
            except ElementClickInterceptedException:
                print("Click intercepted, trying JavaScript click.")
                driver.execute_script("arguments[0].click();", consent_button)
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"Error clicking consent button: {e}")
        else:
            print("No cookie consent banner found.")
    
    def navigate_and_interact(self, driver, url, max_scrolls=3, scroll_pause_time=2):
        """Navigate to URL, handle cookies, scroll, and simulate human interactions."""
        if not re.match(r'^https?://', url):
            print(f"Invalid URL format: {url}")
            return False
        
        try:
            driver.get(url)
            print(f"Navigating to: {url}")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("Page loaded successfully.")
            
            # Handle cookie banners
            self.handle_cookie_banner(driver)
            
            # Scroll simulation
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(max_scrolls):
                driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8)")
                time.sleep(scroll_pause_time + random.uniform(0.5, 1.5))
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Random link interactions
            try:
                all_links = driver.find_elements(By.TAG_NAME, "a")
                clickable_links = []
                for link in all_links:
                    href = link.get_attribute('href')
                    if link.is_displayed() and href and not href.startswith('#') and not href.startswith('mailto:') and not href.startswith('tel:'):
                        if href != url and not (href.startswith(url.split('?')[0].split('#')[0]) and '#' in href):
                            clickable_links.append(link)
                
                if clickable_links:
                    num_clicks = min(random.randint(1, 3), len(clickable_links))
                    print(f"Clicking {num_clicks} random links.")
                    for _ in range(num_clicks):
                        target_link = random.choice(clickable_links)
                        try:
                            link_width = target_link.size.get('width', 0)
                            link_height = target_link.size.get('height', 0)
                            
                            if link_width > 1 and link_height > 1:
                                offset_x = random.randint(1, link_width - 1)
                                offset_y = random.randint(1, link_height - 1)
                                ActionChains(driver).move_to_element_with_offset(
                                    target_link, offset_x, offset_y
                                ).click().perform()
                                print(f"Clicked: {target_link.get_attribute('href')}")
                                time.sleep(random.uniform(3, 7))
                                driver.back()
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                                )
                            else:
                                print("Skipping tiny/invisible link.")
                        except StaleElementReferenceException:
                            print("Stale element reference, skipping.")
                        except ElementClickInterceptedException:
                            print("Click intercepted, skipping.")
            except Exception as e:
                print(f"Error during link interactions: {e}")
                
        except TimeoutException:
            print(f"Timeout loading {url}")
            return False
        except Exception as e:
            print(f"Navigation error: {e}")
            return False
        return True
    
    def extract_cookies(self, driver):
        """Extract cookies with proper formatting."""
        cookies_list = []
        try:
            all_cookies = driver.get_cookies()
            for cookie in all_cookies:
                domain_raw = cookie.get('domain', '').lstrip('.')
                cookie_domain_with_dot = '.' + domain_raw if domain_raw else ''
                cookies_list.append({
                    'Domain': domain_raw,
                    'cookie_domain': cookie_domain_with_dot,
                    'name': cookie.get('name', ''),
                    'value': cookie.get('value', '')
                })
            print(f"Extracted {len(cookies_list)} cookies.")
        except Exception as e:
            print(f"Cookie extraction error: {e}")
        return cookies_list
    
    def format_url_from_domain(self, domain: str) -> str:
        """Format domain into full HTTPS URL with www prefix if needed."""
        domain = re.sub(r'^(http|https)://', '', domain, flags=re.IGNORECASE)
        domain = domain.rstrip('/')
        
        if not domain.lower().startswith('www.') and len(domain.split('.')) <= 2:
            domain = f"www.{domain}"
        
        return f"https://{domain}/"