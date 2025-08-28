source .venv/bin/activate

pip install -r requirements.txt

playwright install chromium

python -m scraper.main --input urls.txt --out scraper/result --parallel 5

python -m crawler.main --input urls.txt
