import argparse
import asyncio
import time
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


KEYWORDS = [
    "privacy", "cookie", "data", "policy", "terms",
    "حریم خصوصی", "کوکی", "اطلاعات", "سیاست", "قوانین"
]


class FileUtils:
    """Utility methods for filenames and paths."""

    @staticmethod
    def sanitize_filename(url: str) -> str:
        """Make a safe filename from URL domain."""
        url = url.replace("http://", "").replace("https://", "")
        safe = url.replace(".", "-").replace(":", "").replace("/", "-")
        safe = "".join(c if c.isalnum() or c in "-_" else "" for c in safe)
        return safe

    @staticmethod
    def get_output_paths(url: str, out_dir: str):
        """Generate HTML/TXT output paths using domain + timestamp."""
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        domain = urlparse(url).netloc or "output"
        safe_name = FileUtils.sanitize_filename(domain)
        return (
            Path(out_dir) / f"{safe_name}_{ts}.html",
            Path(out_dir) / f"{safe_name}_{ts}.txt",
        )


class ContentExtractor:
    """Extracts relevant text blocks filtered by keywords."""

    def __init__(self, keywords, min_line_length: int = 10):
        self.keywords = [kw.lower() for kw in keywords]
        self.min_line_length = min_line_length

    def extract_blocks(self, html: str) -> str:
        """Extract relevant text blocks and filter by keyword substrings."""
        soup = BeautifulSoup(html, "html.parser")
        texts = []

        for tag in soup.find_all(["p", "li", "h1", "h2", "h3"]):
            txt = re.sub(r"\s+", " ", tag.get_text(strip=True))
            if len(txt) >= self.min_line_length:
                if any(kw in txt.lower() for kw in self.keywords):
                    texts.append(txt)

        return "\n".join(texts)


class Scraper:
    """Main scraper class handling both requests + Playwright."""

    def __init__(self, out_dir: str, min_line_length: int = 50):
        self.out_dir = out_dir
        self.extractor = ContentExtractor(KEYWORDS, min_line_length)

    def scrape_with_requests(self, url: str):
        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            html = resp.text
            text = self.extractor.extract_blocks(html)
            if len(text.split()) < 50:
                return None, None
            return html, text
        except Exception:
            return None, None

    async def scrape_with_playwright(self, url: str, pw):
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_selector("body", timeout=20000)
            html = await page.content()
            text = self.extractor.extract_blocks(html)
            return html, text
        except Exception:
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


def main():
    parser = argparse.ArgumentParser(description="Privacy Policy Scraper")
    parser.add_argument("--input", type=str, default="urls.txt", help="File with URLs")
    parser.add_argument("--out", type=str, default="result", help="Output directory")
    parser.add_argument("--parallel", type=int, default=3, help="Concurrent browsers")
    parser.add_argument(
        "--min-length", type=int, default=50, help="Minimum characters per block"
    )
    parser.add_argument("--debug", action="store_true", help="Debug with sample URL")

    args = parser.parse_args()

    if args.debug:
        urls = ["https://www.digikala.com/page/privacy"]
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            urls = f.readlines()

    scraper = Scraper(args.out, args.min_length)
    asyncio.run(scraper.scrape_all(urls, args.parallel))


if __name__ == "__main__":
    main()
