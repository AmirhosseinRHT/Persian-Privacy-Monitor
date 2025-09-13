import json
import re
from urllib.parse import urlparse
import openai
from utils.mongo_driver import MongoDriver
from typing import Optional
import matplotlib.pyplot as plt
import pandas as pd

LLM_MODEL = "gpt-4.1-nano-2025-04-14"

class PrivacyChecker:
    def __init__(self, violation_prompt_path: str, debug: bool = False):
        self.violation_prompt_path = violation_prompt_path
        self.debug = debug
        self.client = openai.OpenAI(
            base_url="https://api.llm7.io/v1",
            api_key="slHENJhFzy4owiF7geiQZrR4CxlR1FPsy+HZSGEPme5pJx9tQWwxMRHc/pVR/epCXMzuSibStPPpWJx1uBvtE9kQL5br4FqaPtj9uPDvkFplE/5qpzmc7TO4ftXfbJvWLjg="
        )
        self.cookie_driver = MongoDriver(collection="crawled_cookies")
        self.practice_driver = MongoDriver(collection="processed_prompts")
        self.target_driver = MongoDriver(collection="privacy_violations")
        self._load_prompt()

    def _load_prompt(self):
        with open(self.violation_prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read().strip()

    def _clean_response(self, text: str) -> dict:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {"violations": []}
        raw_json = match.group(0)
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return {"violations": []}

    def _build_prompt(self, cookies: list, data_practices: dict) -> str:
        return (
            f"{self.prompt_template}\n\n"
            "--- Cookies ---\n"
            f"{json.dumps(cookies, ensure_ascii=False)}\n\n"
            "--- Declared Data Practices ---\n"
            f"{json.dumps(data_practices, ensure_ascii=False)}"
        )

    def _normalize_scores(self, violations: list) -> list:
        for v in violations:
            score = v.get("severity_score", 0)
            v["severity_normalized"] = round(score / 5, 2)
        return violations

    def process_site(self, root_url: str):
        if self.target_driver.collection.find_one({"url": root_url}):
            return None

        cookie_doc = self.cookie_driver.collection.find_one({"root_url": root_url})
        practice_doc = self.practice_driver.collection.find_one({"url": root_url})

        if not cookie_doc or not practice_doc:
            return None

        cookies = cookie_doc.get("cookies", [])
        practices = practice_doc.get("response_normalized", {})

        prompt = self._build_prompt(cookies, practices)
        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        result_text = response.choices[0].message.content
        violations = self._clean_response(result_text).get("violations", [])
        violations = self._normalize_scores(violations)

        result_doc = {
            "url": root_url,
            "cookies": cookies,
            "declared_practices": practices,
            "violations": violations
        }
        self.target_driver.insert_doc(result_doc)
        print(f"[OK] Privacy check saved for {root_url}")
        return result_doc

    def run(self):
        cursor = self.cookie_driver.collection.find()
        for doc in cursor:
            url = doc["root_url"]
            self.process_site(url)

    def generate_report(self):
        data = list(self.target_driver.collection.find())
        if not data:
            print("No privacy violation data available")
            return

        rows = []
        for doc in data:
            url = doc["url"]
            for v in doc.get("violations", []):
                rows.append({
                    "url": url,
                    "category": v.get("category"),
                    "severity": v.get("severity_score"),
                    "normalized": v.get("severity_normalized")
                })

        if not rows:
            print("No violations detected in processed sites")
            return

        df = pd.DataFrame(rows)

        print("=== Privacy Violation Summary ===")
        print(df.groupby("category")["severity"].describe())

        # Bar chart - average severity per category
        plt.figure(figsize=(8,6))
        df.groupby("category")["severity"].mean().plot(
            kind="bar", 
            title="Average Severity per Category"
        )
        plt.ylabel("Average Severity (1-5)")
        plt.tight_layout()
        plt.show()

        # Horizontal bar chart - normalized severity per website
        plt.figure(figsize=(8,6))
        df.groupby("url")["normalized"].mean().plot(
            kind="barh", 
            title="Normalized Severity per Website"
        )
        plt.xlabel("Normalized Severity (0-1)")
        plt.tight_layout()
        plt.show()

        # Pie chart - distribution of violations by category
        plt.figure(figsize=(7,7))
        df["category"].value_counts().plot(
            kind="pie", 
            autopct="%1.1f%%", 
            title="Distribution of Violations by Category"
        )
        plt.ylabel("")
        plt.tight_layout()
        plt.show()



if __name__ == "__main__":
    checker = PrivacyChecker("prompts/privacy-checker/sample1.txt", debug=False)
    checker.run()
    checker.generate_report()
