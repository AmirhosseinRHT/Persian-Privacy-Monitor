import json
import re
from urllib.parse import urlparse
import openai
from utils.mongo_driver import MongoDriver
from typing import Optional

LLM_MODEL = "gpt-4.1-nano-2025-04-14"

class PromptApi:
    def __init__(self, 
                 data_practice_prompt_path: str, 
                 normalize_prompt_path: str, 
                 urls_path: str, 
                 entities_path: str, 
                 use_normalizer_prompt: bool = True,
                 debug: bool = False):
        self.data_practice_prompt_path = data_practice_prompt_path
        self.normalize_prompt_path = normalize_prompt_path
        self.urls_path = urls_path
        self.entities_path = entities_path
        self.use_normalizer_prompt = use_normalizer_prompt
        self.debug = debug
        self.client = openai.OpenAI(
            base_url="https://api.llm7.io/v1",
            api_key="slHENJhFzy4owiF7geiQZrR4CxlR1FPsy+HZSGEPme5pJx9tQWwxMRHc/pVR/epCXMzuSibStPPpWJx1uBvtE9kQL5br4FqaPtj9uPDvkFplE/5qpzmc7TO4ftXfbJvWLjg="
        )
        self.source_driver = MongoDriver(collection="scraped_pages")
        self.target_driver = MongoDriver(collection="processed_prompts")
        
        self._load_initial_resources()

    def _load_initial_resources(self):
        """Load prompt templates and entity list"""
        with open(self.data_practice_prompt_path, "r", encoding="utf-8") as f:
            self.raw_prompt_template = f.read().strip()
        with open(self.normalize_prompt_path, "r", encoding="utf-8") as f:
            self.normalization_prompt_template = f.read().strip()
        with open(self.entities_path, "r", encoding="utf-8") as f:
            self.canonical_entities = json.load(f)
            self.normalized_canonical_entities = [
                self._normalize_text(entity) for entity in self.canonical_entities
            ]

    def get_root_url(self, url: str) -> str:
        """Extract root URL from full URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent comparison"""
        text = text.lower()
        text = ''.join(c for c in text if c.isalnum() or c == ' ')
        text = ' '.join(text.split())
        return text

    def _calculate_levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate edit distance between two strings"""
        if len(s1) < len(s2):
            return self._calculate_levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def _find_best_match_for_item(self, item: str) -> str:
        """Find closest canonical entity for a single item"""
        normalized_item = self._normalize_text(item)
        
        # Check for exact match first
        if normalized_item in self.normalized_canonical_entities:
            index = self.normalized_canonical_entities.index(normalized_item)
            return self.canonical_entities[index]
        
        # Fallback to fuzzy matching
        min_distance = float('inf')
        best_match = None
        
        for candidate in self.canonical_entities:
            normalized_candidate = self._normalize_text(candidate)
            distance = self._calculate_levenshtein_distance(normalized_item, normalized_candidate)
            
            if distance < min_distance:
                min_distance = distance
                best_match = candidate
                
        return best_match

    def _apply_entity_replacement(self, data_practices_dict: dict) -> dict:
        """Replace all items in data practices dictionary with canonical entities"""
        if all(len(data_practices_dict[key]) == 0 for key in data_practices_dict):
            return {
                "collect": [],
                "save": [],
                "share": [],
                "not_collect": [],
                "not_save": [],
                "not_share": [],
                "cookie": []
            }
        
        result = {}
        for key, items in data_practices_dict.items():
            if items:
                result[key] = [self._find_best_match_for_item(item) for item in items]
            else:
                result[key] = []
                
        return result

    def clean_response(self, text: str) -> dict:
        """Extract valid JSON from LLM response"""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in response")
        raw_json = match.group(0)
        
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from model: {e}")
        return data

    def _generate_final_prompt(self, extracted_data: dict) -> str:
        """Generate final normalization prompt with extracted data"""
        return (
            f"{self.normalization_prompt_template}\n\n"
            "--- Normalized Entities ---\n"
            f"{json.dumps(self.canonical_entities, ensure_ascii=False)}\n\n"
            "--- Extracted JSON ---\n"
            f"{json.dumps(extracted_data, ensure_ascii=False)}"
        )

    def process_url(self, url: str):
        """Process a single URL through the entire pipeline"""
        url = self.get_root_url(url)
        
        if self._is_already_processed(url):
            return None
        
        doc = self._get_source_document(url)
        if not doc:
            return None
        
        extracted_data = self._extract_data_practices(doc)
        if not extracted_data:
            return None
        
        normalized_data = self._normalize_data(extracted_data)
        if not normalized_data:
            return None
        
        replaced_data = self._apply_entity_replacement(normalized_data)
        result_doc = self._prepare_result_document(url, doc, extracted_data, normalized_data, replaced_data)
        
        self._save_result(result_doc, url)
        return result_doc

    def _is_already_processed(self, url: str) -> bool:
        """Check if URL has already been processed"""
        if self.target_driver.collection.find_one({"url": url}):
            print(f"[SKIP] Already processed: {url}")
            return True
        return False

    def _get_source_document(self, url: str) -> Optional[dict]:
        """Retrieve document content from source database"""
        doc = self.source_driver.collection.find_one({"site_url": url})
        if not doc:
            print(f"[ERROR] No document found for {url}")
        return doc

    def _extract_data_practices(self, doc: dict) -> Optional[dict]:
        """Extract data practices using the first API call"""
        final_raw_prompt = self._build_raw_prompt(doc['text'])
        
        try:
            response_raw = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": final_raw_prompt}]
            )
            result_text_raw = response_raw.choices[0].message.content
            return self.clean_response(result_text_raw)
        except Exception as e:
            print(f"[ERROR] Could not parse JSON for {doc.get('site_url', 'unknown')}: {e}")
            return None

    def _build_raw_prompt(self, document_text: str) -> str:
        """Build the raw prompt for data extraction"""
        return (
            f"{self.raw_prompt_template}\n\n"
            "--- Document Content ---\n"
            f"{document_text}"
        )

    def _normalize_data(self, extracted_data: dict) -> Optional[dict]:
        """Normalize extracted data using second API call if enabled"""
        if not self.use_normalizer_prompt:
            return extracted_data
        
        final_normalized_prompt = self._generate_final_prompt(extracted_data)
        
        try:
            response_normalized = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": final_normalized_prompt}]
            )
            result_text_normalized = response_normalized.choices[0].message.content
            return self.clean_response(result_text_normalized)
        except Exception as e:
            print(f"[ERROR] Could not parse final JSON: {e}")
            return None

    def _prepare_result_document(self, url: str, doc: dict, extracted_data: dict, 
                            normalized_data: dict, replaced_data: dict) -> dict:
        """Prepare the final result document for saving"""
        return {
            "url": url,
            "raw_file": self.data_practice_prompt_path,
            "normalized_file": self.normalize_prompt_path,
            "appended_doc_text": doc["text"],
            "response_raw": extracted_data,
            "response_normalized": normalized_data,
            "replaced_response": replaced_data,
            "entities": self.canonical_entities,
        }

    def _save_result(self, result_doc: dict, url: str):
        """Save the result document to the target database"""
        self.target_driver.insert_doc(result_doc)
        print(f"[OK] Saved responses for {url}")

    def run(self):
        """Run processing for all URLs"""
        urls = []
        with open(self.urls_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
            
        if self.debug:
            urls = ["https://www.digikala.com"]
            
        for url in urls:
            self.process_url(url)