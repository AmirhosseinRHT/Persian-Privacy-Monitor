import json
import re
from urllib.parse import urlparse

class LabelNormalizer:
    def __init__(self, canonical_labels_path: str):
        with open(canonical_labels_path, "r", encoding="utf-8") as f:
            self.canonical_labels = json.load(f)
            self.normalized_canonical_labels = [self._normalize_text(label) for label in self.canonical_labels]
    
    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = ''.join(c for c in text if c.isalnum() or c == ' ')
        text = ' '.join(text.split())
        return text
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
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
    
    def _find_nearest_label(self, target: str) -> str:
        normalized_target = self._normalize_text(target)
        
        if normalized_target in self.normalized_canonical_labels:
            idx = self.normalized_canonical_labels.index(normalized_target)
            return self.canonical_labels[idx]
        
        min_distance = float('inf')
        best_match = None
        
        for label in self.canonical_labels:
            normalized_label = self._normalize_text(label)
            distance = self._levenshtein_distance(normalized_target, normalized_label)
            
            if distance < min_distance:
                min_distance = distance
                best_match = label
                
        return best_match
    
    def normalize_eval_data(self, eval_data_path: str, output_path: str):
        with open(eval_data_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
        
        normalized_data = {}
        
        for url, categories in eval_data.items():
            normalized_categories = {}
            for category, labels in categories.items():
                normalized_labels = [self._find_nearest_label(label) for label in labels]
                normalized_categories[category] = normalized_labels
            normalized_data[url] = normalized_categories
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(normalized_data, f, ensure_ascii=False, indent=2)

# Usage example:
if __name__ == "__main__":
    normalizer = LabelNormalizer(canonical_labels_path="data-practices-manual-extract/entity-list.json")
    normalizer.normalize_eval_data(
        eval_data_path="data-practices-manual-extract/manual-extract.json",
        output_path="data-practices-manual-extract/normalized-evaluation-data.json"
    )