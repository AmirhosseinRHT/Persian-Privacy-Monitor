import argparse
from argparse import Namespace
import os
from extractor.prompt_api import PromptApi

def parse_arguments() -> Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Prompt Sender with Mongo + OpenAI")
    parser.add_argument("--practice_prompt", type=str, default="prompts/extract-data-practice/sample1.txt", help="Path to the extractor prompt file")
    parser.add_argument("--normalizer_prompt", type=str, default="prompts/normalize/sample1.txt", help="Path to the normalizer prompt file")
    parser.add_argument("--entity_list", type=str, default="data-practices-manual-extract/entity-list.json", help="list of seperated entites")
    parser.add_argument("--input", type=str, default="urls.txt", help="Path to file with URLs (one per line)")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode with a sample URL")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    print("Started Sending prompt to Extract practices using LLM")
    sender = PromptApi(data_practice_prompt_path=args.practice_prompt,
                        normalize_prompt_path=args.normalizer_prompt,
                          entities_path=args.entity_list, urls_path=args.input, debug=args.debug)
    sender.run()
