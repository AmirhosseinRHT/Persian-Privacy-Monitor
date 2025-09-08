import argparse
import os
from extractor.prompt_api import PromptApi

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Prompt Sender with Mongo + OpenAI")
    parser.add_argument("--prompt", type=str, default="data-practices-LLM-result/prompt/sample1.txt", help="Path to the prompt file")
    parser.add_argument("--input", type=str, default="urls.txt", help="Path to file with URLs (one per line)")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode with a sample URL")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    print("Started Sending prompt to Extract practices using LLM")
    sender = PromptApi(prompt_path=args.prompt, urls_path=args.input, debug=args.debug)
    sender.run()
