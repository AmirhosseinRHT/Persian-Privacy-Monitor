source .venv/bin/activate

pip install -r requirements.txt

playwright install chromium

python -m scraper.main --input scraper/urls.txt --out scraper/result --parallel 5
