import asyncio
from playwright.async_api import async_playwright
import requests

from .utils import FileUtils
from .content_extractor import ContentExtractor
from typing import List, Tuple, Optional
from .keywords import KEYWORDS


class Scraper:
    """Main scraper class handling both requests + Playwright."""

    def __init__(self, out_dir: str, min_line_length: int = 50):
        self.out_dir = out_dir
        self.extractor = ContentExtractor(KEYWORDS, min_line_length)

    def scrape_with_requests(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            html = resp.text
            text = self.extractor.extract_blocks(html)
            return html, text
        except Exception as e:
            print(f"[FAIL] {url} ({type(e).__name__}: {e})")
            return None, None


    async def scrape_with_playwright(self, url: str, pw):
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            html = await page.content()
            text = self.extractor.extract_blocks(html)

            return html, text
        except Exception as e: 
            print(f"[FAIL] {url} ({type(e).__name__}: {e})")
            return None, None
        finally:
            await browser.close()



    async def process_url(self, url: str, pw):
        """Process a single URL with requests first, then Playwright fallback."""
        html, text = self.scrape_with_requests(url)

        if not html or not text:
            html, text = await self.scrape_with_playwright(url, pw)

        if html and text:
            html_path, txt_path = FileUtils.get_output_paths(url, self.out_dir)
            html_path.write_text(html, encoding="utf-8")
            txt_path.write_text(text, encoding="utf-8")
            print(f"[OK] {url} → {html_path.name}, {txt_path.name}")
        else:
            print(f"[FAIL] Could not scrape {url}")

    async def scrape_all(self, urls, parallel: int):
        """Scrape all URLs in parallel with Playwright."""
        sem = asyncio.Semaphore(parallel)

        async with async_playwright() as pw:

            async def bound_process(u):
                async with sem:
                    await self.process_url(u.strip(), pw)

            tasks = [bound_process(u) for u in urls if u.strip()]
            await asyncio.gather(*tasks)
