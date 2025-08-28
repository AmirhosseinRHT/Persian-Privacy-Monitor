# Persian Privacy Monitor

Persian Privacy Monitor is a research-oriented tool to collect and analyze privacy-related information from Persian-language websites. The project currently contains two main components:

- crawler: visits websites with Selenium, attempts to interact with cookie consent banners, scrolls pages, and collects cookies to store in MongoDB.
- scraper: extracts pages (privacy policies and other content) using Playwright/requests, readability and BeautifulSoup, then stores results for analysis.

This README documents how the code is organized, what dependencies are required, and how to run each component.

## Repository layout (important files)

- `crawler/` — Selenium-based crawler that visits pages and saves cookies to MongoDB.
- `scraper/` — Content extraction tools (Playwright + readability + BeautifulSoup) and the scraping entry point `scraper/main.py`.
- `utils/mongo_driver.py` — Lightweight MongoDB helper used by both components (defaults to `mongodb://localhost:27017`, DB `scraperdb`).
- `requirements.txt` — Python dependencies.
- `run.sh` — convenience script with common example commands.
- `urls.txt` — list of target URLs (one per line) used by the scrapers/crawlers.

## Quick checklist (what this README covers)

- Description of code components: Done
- Installation and environment setup: Done
- Dependencies and notes (Playwright + MongoDB): Done
- How to run scraper and crawler from project root (to avoid import issues): Done

## Prerequisites

- Python 3.10+ (the project was developed with Python 3.11/3.13-style features). Use a virtual environment.
- MongoDB running locally or accessible via network. The default Mongo URI used by `MongoDriver` is `mongodb://localhost:27017` and default DB `scraperdb`.
- For the `scraper` component you will likely need Playwright browsers installed (Chromium). See the installation step below.
- A modern shell (instructions below use `zsh` / `bash`).

## Installation

1. Clone the repository and enter its directory:

```bash
git clone https://github.com/<your-username>/Persian-Privacy-Monitor.git
cd Persian-Privacy-Monitor
```

2. Create and activate a virtual environment (zsh/bash):

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. If you plan to run the `scraper` (Playwright), install browsers:

```bash
python -m playwright install chromium
```

5. Ensure MongoDB is running and reachable. For local testing you can use the default URI and DB name; otherwise set the connection in code or pass environment variables/config (not currently implemented).

> NOTE: You can run project after clone with run `run.sh` instead of above steps.

## Major dependencies

See `requirements.txt`. Key packages used by the codebase include:

- playwright — browser automation used in `scraper`.
- selenium — browser automation used in `crawler`.
- pymongo — MongoDB client.
- beautifulsoup4, lxml, readability-lxml — HTML parsing and main-text extraction.
- httpx / requests — HTTP clients.

Note: `requirements.txt` contains the full pinned/unpinned list. Playwright requires separate browser installation (see above).

## How to run

Important: run commands from the project root (`/Users/amir/Desktop/cookie/Persian-Privacy-Monitor`). Running individual `.py` files directly from their subfolders may cause import errors such as "No module named 'utils'". Use `python -m package.module` or run from project root so Python can resolve package imports.

Examples (all commands assume your virtualenv is activated and you are in the project root):

- Run the scraper (concurrent Playwright workers):

```bash
python -m scraper.main --input urls.txt --out result --parallel 3
```

- Run the crawler (Selenium-based cookie collector):

```bash
python -m crawler.crawler --input urls.txt
```

- A convenience example is included in `run.sh`. You can inspect and run it from the project root:

```bash
bash run.sh
```

If you get "ModuleNotFoundError: No module named 'utils'" when running `crawler/crawler.py` directly, use the `-m` option from project root or add the project root to `PYTHONPATH`.

## MongoDB notes

The provided `utils/mongo_driver.py` defaults to:

- uri: `mongodb://localhost:27017`
- db name: `scraperdb`
- collection: `scraped_pages` (used by scraper) or `cookies` (crawler code inserts cookie documents; check code for exact collection name used)

Start a local MongoDB instance before running or update `MongoDriver` to point to your hosted MongoDB.

## Code overview

- `crawler/crawler.py`: utilities for visiting pages with Selenium: navigation, cookie-banner handling, scrolling, extracting cookies, and saving cookie documents to MongoDB. It expects to import `utils.mongo_driver.MongoDriver`.
- `scraper/main.py`: CLI entry for scraping pages. Loads URLs from a file and runs `Scraper` (in `scraper/scraper_core.py`) asynchronously with Playwright.
- `utils/mongo_driver.py`: small wrapper around `pymongo.MongoClient` providing `already_scraped()` and `insert_doc()` helpers.

## Troubleshooting

- Module import errors: always run from project root and prefer `python -m package.module`.
- Playwright errors: ensure you installed browsers via `python -m playwright install`.
- MongoDB connection errors: verify Mongo is running and reachable at configured URI.

## Next steps & suggestions

- Add CLI flags or environment variables for Mongo URI and database names.
- Add unit tests for core helpers (cookie extraction, content extraction).
- Add a small sample `urls.txt` containing a couple of known sites for quick smoke tests.

## License

This project includes source code under the project's LICENSE file. Check `LICENSE` for details.
