import argparse
import asyncio
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from readability import Document
from playwright.async_api import async_playwright


def sanitize_filename(url: str) -> str:

    """Make a safe filename from URL domain."""
    url = url.replace("http://", "").replace("https://", "")
    safe = url.replace(".", "-").replace(":", "").replace("/", "-")
    safe = "".join(c if c.isalnum() or c in "-_" else "" for c in safe)
    return safe


def get_output_paths(url: str, out_dir: str):
    """Generate HTML/TXT output paths using domain + timestamp."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    domain = urlparse(url).netloc or "output"
    safe_name = sanitize_filename(domain)
    return (
        Path(out_dir) / f"{safe_name}_{ts}.html",
        Path(out_dir) / f"{safe_name}_{ts}.txt",
    )


def scrape_with_requests(url: str):
    """Try scraping using requests + readability (fast path)."""
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        doc = Document(resp.text)
        html_content = doc.summary()
        text_content = BeautifulSoup(html_content, "html.parser").get_text(
            separator="\n", strip=True
        )
        if len(text_content.split()) < 50:
            return None, None
        return html_content, text_content
    except Exception:
        return None, None


async def scrape_with_playwright(url: str, pw):
    """Scrape using Playwright (JS-rendered content)."""
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_selector("body", timeout=20000)
        html = await page.content()
        text = await page.inner_text("body")
        return html, text
    except Exception:
        return None, None
    finally:
        await browser.close()


async def process_url(url: str, out_dir: str, pw):
    """Process a single URL with requests first, then Playwright fallback."""
    html, text = scrape_with_requests(url)

    if not html or not text:
        html, text = await scrape_with_playwright(url, pw)

    if html and text:
        html_path, txt_path = get_output_paths(url, out_dir)
        html_path.write_text(html, encoding="utf-8")
        txt_path.write_text(text, encoding="utf-8")
        print(f"[OK] {url} → {html_path.name}, {txt_path.name}")
    else:
        print(f"[FAIL] Could not scrape {url}")


async def scrape_all(urls, out_dir: str, parallel: int):
    """Scrape all URLs in parallel with Playwright."""
    sem = asyncio.Semaphore(parallel)

    async with async_playwright() as pw:

        async def bound_process(u):
            async with sem:
                await process_url(u.strip(), out_dir, pw)

        tasks = [bound_process(u) for u in urls if u.strip()]
        await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(description="Privacy Policy Scraper")
    parser.add_argument("--input", type=str, default="urls.txt", help="File with URLs")
    parser.add_argument("--out", type=str, default="scraped", help="Output directory")
    parser.add_argument(
        "--parallel", type=int, default=3, help="Number of concurrent browsers"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Run static debug example instead of file"
    )

    args = parser.parse_args()

    if args.debug:
        urls = [
            "https://www.digikala.com/page/privacy",
        ]
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            urls = f.readlines()

    asyncio.run(scrape_all(urls, args.out, args.parallel))


if __name__ == "__main__":
    main()
