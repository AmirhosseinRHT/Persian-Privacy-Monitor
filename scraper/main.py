import argparse
import asyncio
from scraper.scraper_core import Scraper

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
        urls = ["https://www.filimo.com/asparagus/term"]
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            urls = f.readlines()

    scraper = Scraper(args.min_length)
    asyncio.run(scraper.scrape_all(urls, args.parallel))


if __name__ == "__main__":
    main()
