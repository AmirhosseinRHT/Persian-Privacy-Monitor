import argparse
import asyncio
import time
from pathlib import Path
from urllib.parse import urlparse
import re

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

def extract_blocks(html: str, min_line_length: int = 10) -> str:
    soup = BeautifulSoup(html, "html.parser")
    texts = []

    for tag in soup.find_all(["p", "li", "h1", "h2", "h3"]):
        txt = re.sub(r"\s+", " ", tag.get_text(strip=True))
        if len(txt) >= min_line_length:
            texts.append(txt)

    return "\n".join(texts)


def scrape_with_requests(url: str, min_line_length: int = 10):
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        html = resp.text
        text = extract_blocks(html, min_line_length)
        if len(text.split()) < 50:
            return None, None
        return html, text
    except Exception:
        return None, None


async def scrape_with_playwright(url: str, pw, min_line_length: int = 10):
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_selector("body", timeout=20000)
        html = await page.content()
        text = extract_blocks(html, min_line_length)
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
    parser.add_argument("--out", type=str, default="result", help="Output directory")
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
