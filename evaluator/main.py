import argparse
from evaluator.privacy_checker import PrivacyChecker


def main():
    parser = argparse.ArgumentParser(description="Privacy Policy Checker")
    parser.add_argument("--prompt", type=str, default="prompts/privacy-checker/sample1.txt",
                        help="Path to violation prompt file")
    parser.add_argument("--report", action="store_true",
                        help="Generate report after processing")
    parser.add_argument("--debug", action="store_true",
                        help="Run in debug mode")

    args = parser.parse_args()

    checker = PrivacyChecker(args.prompt, debug=args.debug)
    checker.run()

    if args.report:
        checker.generate_report()


if __name__ == "__main__":
    main()
