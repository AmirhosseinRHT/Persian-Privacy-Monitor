#!/bin/bash

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

pip install -r requirements.txt

playwright install chromium

docker-compose up -d

# python -m scraper.main --input urls.txt --out scraper/result --parallel 5

# python -m crawler.main --input urls.txt --output crawler/crawled_result.csv

python -m extractor.main --input urls.txt
