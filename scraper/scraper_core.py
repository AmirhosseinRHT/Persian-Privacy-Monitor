import sys
import os

proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

import asyncio
import requests
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Tuple, Optional

from playwright.async_api import async_playwright

from scraper.content_extractor import ContentExtractor
from .keywords import KEYWORDS
from utils.mongo_driver import MongoDriver


class Scraper:
    """Main scraper class handling both requests + Playwright, with MongoDB saving."""

    def __init__(self, min_line_length: int = 50,
                 db_name: str = "privacy_monitor"):
        self.extractor = ContentExtractor(KEYWORDS, min_line_length)
        self.mongo = MongoDriver(db_name=db_name, collection="scraped_pages")

    def _get_root_url(self, url: str) -> str:
        """Return scheme://hostname part of URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def scrape_with_requests(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Scrape page using requests (fast path)."""
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            html = resp.text
            text = self.extractor.extract_blocks(html)
            return html, text
        except Exception as e:
            print(f"[FAIL][requests] {url} ({type(e).__name__}: {e})")
            return None, None

    async def scrape_with_playwright(self, url: str, pw):
        """Scrape page using Playwright (fallback path)."""
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            html = await page.content()
            text = self.extractor.extract_blocks(html)
            return html, text
        except Exception as e:
            print(f"[FAIL][playwright] {url} ({type(e).__name__}: {e})")
            return None, None
        finally:
            await browser.close()

    def _score_candidates(self, html: str):
        """Extract and score candidate containers from HTML."""
        soup = self.extractor._get_soup(html)
        candidates = self.extractor._find_candidates(soup)

        results = []
        for c in candidates:
            score, kw, wc = self.extractor._score_container(c)
            if score > 0:
                results.append({
                    "tag": c.name,
                    "score": score,
                    "keywords": kw,
                    "words": wc
                })
        return results

    async def process_url(self, url: str, pw):
        """Process a single URL with requests first, then Playwright fallback. Save to MongoDB."""
        if self.mongo.already_scraped(url):
            print(f"[SKIP] {url} already scraped")
            return

        method = "requests"
        html, text = self.scrape_with_requests(url)

        if not html or not text:
            method = "playwright"
            html, text = await self.scrape_with_playwright(url, pw)

        if html and text:
            scored_containers = self._score_candidates(html)
            doc = {
                "url": url,
                "site_url": self._get_root_url(url),
                "html": html,
                "text": text,
                "method": method,
                "scores": scored_containers,
                "saved_at": datetime.utcnow()
            }
            self.mongo.insert_doc(doc)
            print(f"[OK] {url} → saved to MongoDB ({method})")
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
