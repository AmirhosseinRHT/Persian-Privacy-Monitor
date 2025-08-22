import asyncio
import hashlib
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from readability import Document

from playwright.async_api import async_playwright


def make_safe_filename(url: str) -> str:

    url = url.replace("http://", "").replace("https://", "")
    safe = url.replace(".", "-").replace(":", "").replace("/", "-")
    safe = "".join(c if c.isalnum() or c in "-_" else "" for c in safe)
    return safe[:30]


def save_output(url: str, html: str, text: str, out_dir: str = "scraped"):
    """Save HTML and text to disk with unique name."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    updated_file_name = make_safe_filename(url)
    html_path = Path(out_dir) / f"{updated_file_name}_{ts}.html"
    txt_path = Path(out_dir) / f"{updated_file_name}_{ts}.txt"

    html_path.write_text(html, encoding="utf-8")
    txt_path.write_text(text, encoding="utf-8")

    print(f"[OK] Saved {url} → {html_path}, {txt_path}")


def scrape_with_requests(url: str):
    """Try scraping using requests + readability."""
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    doc = Document(resp.text)
    html_content = doc.summary()
    text_content = BeautifulSoup(html_content, "html.parser").get_text(separator="\n", strip=True)

    if len(text_content.split()) < 50:
        return None, None
    return html_content, text_content


async def scrape_with_playwright(url: str):
    """Scrape using Playwright (handles JS-rendered content)."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_selector("body", timeout=20000)

        html = await page.content()
        text = await page.inner_text("body")

        await browser.close()
        return html, text


def scrape_privacy_page(url: str, out_dir: str = "scraped"):
    """Main entry: try fast scraping first, fallback to Playwright if needed."""
    try:
        html, text = scrape_with_requests(url)
        if html and text:
            save_output(url, html, text, out_dir)
            return
        print(f"[!] Requests failed for {url}, retrying with Playwright...")
    except Exception as e:
        print(f"[!] Requests scraping error for {url}: {e}, switching to Playwright...")

    try:
        html, text = asyncio.run(scrape_with_playwright(url))
        if html and text:
            save_output(url, html, text, out_dir)
    except Exception as e:
        print(f"[ERROR] Playwright scraping failed for {url}: {e}")


if __name__ == "__main__":
    urls = [
        "https://www.technolife.com/staticpage/page-15/%D8%AD%D8%B1%DB%8C%D9%85%20%D8%AE%D8%B5%D9%88%D8%B5%DB%8C%20%DA%A9%D8%A7%D8%B1%D8%A8%D8%B1%D8%A7%D9%86",
        "https://www.digikala.com/page/privacy",
    ]
    for u in urls:
        scrape_privacy_page(u)
