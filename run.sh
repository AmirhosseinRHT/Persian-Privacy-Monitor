source .venv/bin/activate

pip install -r requirements.txt

playwright install chromium

python privacy_scraper.py --input urls.txt --out scraped --parallel 5
