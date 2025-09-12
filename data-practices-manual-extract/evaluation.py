import json
from pymongo import MongoClient
from collections import defaultdict
import numpy as np

class EvaluationTool:
    def __init__(self, eval_file_path: str, mongo_uri: str = "mongodb://localhost:27017/", db_name: str = "privacy_monitor"):
        self.eval_file_path = eval_file_path
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client[db_name]
        self.target_collection = self.db["processed_prompts"]
        self.expected_data = self._load_evaluation_data()
        
    def _load_evaluation_data(self) -> dict:
        with open(self.eval_file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _get_processed_data(self, url: str) -> dict:
        doc = self.target_collection.find_one({"url": url})
        if not doc:
            raise ValueError(f"No processed data found for URL: {url}")
        return doc["replaced_response"]
    
    def _calculate_category_agreement(self, expected_cat: list, actual_cat: list, all_items: set) -> float:
        expected_vector = {item: 1 if item in expected_cat else 0 for item in all_items}
        actual_vector = {item: 1 if item in actual_cat else 0 for item in all_items}
        
        agreements = sum(1 for item in all_items if expected_vector[item] == actual_vector[item])
        total_items = len(all_items)
        p_observed = agreements / total_items if total_items > 0 else 1.0
        
        p_expected = sum((sum(expected_vector.values()) / total_items) * 
                         (sum(actual_vector.values()) / total_items) for _ in all_items) / total_items
        
        if p_expected >= 1.0:
            return 1.0 if p_observed == 1.0 else 0.0
        if p_expected == 0.0:
            return 1.0 if p_observed == 1.0 else 0.0
            
        return (p_observed - p_expected) / (1.0 - p_expected)
    
    def evaluate_all(self):
        categories = ["collect", "save", "share", "not_collect", "not_save", "not_share", "cookie"]
        results = {}
        category_stats = defaultdict(list)
        overall_scores = []

        for url, expected in self.expected_data.items():
            try:
                actual = self._get_processed_data(url)
                url_results = {}
                
                all_items = set()
                for cat in categories:
                    all_items.update(expected.get(cat, []))
                    all_items.update(actual.get(cat, []))
                
                url_scores = []
                for category in categories:
                    exp_items = expected.get(category, [])
                    act_items = actual.get(category, [])
                    
                    if not all_items:
                        kappa = 1.0
                    elif not exp_items and not act_items:
                        kappa = 1.0
                    elif not exp_items or not act_items:
                        kappa = 0.0
                    else:
                        kappa = self._calculate_category_agreement(exp_items, act_items, all_items)
                    
                    url_results[category] = kappa
                    category_stats[category].append(kappa)
                    url_scores.append(kappa)
                
                url_mean = np.mean(url_scores) if url_scores else 0.0
                overall_scores.append(url_mean)
                results[url] = {"categories": url_results, "mean_score": url_mean}
                
            except Exception as e:
                print(f"Error evaluating {url}: {str(e)}")
                continue
        
        for url, url_data in results.items():
            print(f"\nResults for {url}:")
            for category, kappa in url_data["categories"].items():
                print(f"  {category}: {kappa:.4f}")
            print(f"  Mean Score: {url_data['mean_score']:.4f}")

        print("\n" + "="*60)
        print("FINAL STATISTICAL SUMMARY")
        print("="*60)
        
        print(f"\nOverall Statistics (across all URLs):")
        print(f"Total URLs evaluated: {len(overall_scores)}")
        print(f"Overall Mean Kappa: {np.mean(overall_scores):.4f}")
        print(f"Overall Kappa Variance: {np.var(overall_scores):.4f}")
        print(f"Overall Kappa Std Dev: {np.std(overall_scores):.4f}")
        print(f"Overall Kappa Range: [{np.min(overall_scores):.4f}, {np.max(overall_scores):.4f}]")
        
        print(f"\nCategory-wise Statistics:")
        for category in categories:
            scores = category_stats[category]
            if scores:
                print(f"\n{category}:")
                print(f"  Mean: {np.mean(scores):.4f}")
                print(f"  Variance: {np.var(scores):.4f}")
                print(f"  Std Dev: {np.std(scores):.4f}")
                print(f"  Min: {np.min(scores):.4f}")
                print(f"  Max: {np.max(scores):.4f}")
                print(f"  Count: {len(scores)}")
        
        consensus_categories = {}
        for category in categories:
            scores = category_stats[category]
            if scores:
                mean_score = np.mean(scores)
                consensus_categories[category] = mean_score
        
        print(f"\nConsensus Results (Average Kappa across all URLs):")
        for category, score in sorted(consensus_categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {score:.4f}")
        
        overall_consensus = np.mean(overall_scores) if overall_scores else 0.0
        print(f"\nFinal Overall Consensus Score: {overall_consensus:.4f}")

if __name__ == "__main__":
    evaluator = EvaluationTool(eval_file_path="data-practices-manual-extract/normalized-evaluation-data.json")
    evaluator.evaluate_all()
