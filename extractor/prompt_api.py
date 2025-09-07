import json
import re
from urllib.parse import urlparse
import openai

from utils.mongo_driver import MongoDriver


class PromptApi:
    def __init__(self, prompt_path: str, urls_path: str, debug: bool = False):
        self.prompt_path = prompt_path
        self.urls_path = urls_path
        self.debug = debug

        self.client = openai.OpenAI(
            base_url="https://api.llm7.io/v1",
            api_key="slHENJhFzy4owiF7geiQZrR4CxlR1FPsy+HZSGEPme5pJx9tQWwxMRHc/pVR/epCXMzuSibStPPpWJx1uBvtE9kQL5br4FqaPtj9uPDvkFplE/5qpzmc7TO4ftXfbJvWLjg="
        )

        self.source_driver = MongoDriver(collection="scraped_pages")
        self.target_driver = MongoDriver(collection="processed_prompts")

        with open(self.prompt_path, "r", encoding="utf-8") as f:
            self.base_prompt = f.read().strip()

    def get_root_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def clean_response(self, text: str) -> dict:
        """
        Extract JSON block from text, validate, and return as dict.
        """
        # Extract first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in response")

        raw_json = match.group(0)

        # Parse + normalize
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from model: {e}")

        return data

    def process_url(self, url: str):
        url = self.get_root_url(url)

        if self.target_driver.collection.find_one({"url": url}):
            print(f"[SKIP] Already processed: {url}")
            return None

        doc = self.source_driver.collection.find_one({"site_url": url})

        final_prompt = f"{self.base_prompt}\n\n--- Document Content ---\n{doc['text']}"

        response = self.client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[{"role": "user", "content": final_prompt}]
        )

        result_text = response.choices[0].message.content

        try:
            clean_json = self.clean_response(result_text)
        except Exception as e:
            print(f"[ERROR] Could not parse JSON for {url}: {e}")
            return None

        result_doc = {
            "url": url,
            "prompt_file": self.prompt_path,
            "prompt": self.base_prompt,
            "appended_doc_text": doc["text"],
            "response": clean_json
        }

        self.target_driver.insert_doc(result_doc)
        print(f"[OK] Saved response for {url}")
        return clean_json

    def run(self):
        urls = []
        with open(self.urls_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]

        if self.debug:
            urls = ["https://www.digikala.com"]

        for url in urls:
            self.process_url(url)
