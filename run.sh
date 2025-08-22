source .venv/bin/activate

pip install -r requirements.txt

playwright install chromium

python scraper/privacy_scraper.py --input scraper/urls.txt --out scraper/result --parallel 5
