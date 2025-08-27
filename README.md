# Persian Privacy Monitor

Persian Privacy Monitor is a research and analysis tool designed to study and monitor privacy practices on Persian-language websites.  
It focuses on collecting, extracting, and analyzing website data (such as cookies and privacy policies) in order to evaluate compliance with privacy standards.

## Features

- Automated crawling of Persian websites.
- Cookie extraction and analysis.
- Detection of privacy policy presence and content.
- Data storage for further research and monitoring.
- Modular design to extend with new privacy-related checks.

## Project Structure

```
.
├── crawler/           # Integrated web crawler for cookie extraction
├── docs/              # Documentation and notes
├── src/               # Core logic of the privacy monitor
└── README.md
```

## Installation

Clone the repository and set up the environment:

```bash
git clone https://github.com/<your-username>/Persian-Privacy-Monitor.git
cd Persian-Privacy-Monitor
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run the privacy monitor:

```bash
python src/main.py
```

(Adjust entry point according to your project structure.)

## Acknowledgements

This project includes code from [extracting-cookies-using-webcrawler](https://github.com/MSaeidSedighi/extracting-cookies-using-webcrawler)  
by [MSaeidSedighi](https://github.com/MSaeidSedighi), licensed under the [MIT License](https://github.com/MSaeidSedighi/extracting-cookies-using-webcrawler/blob/main/LICENSE).

We are grateful for this contribution, which powers the cookie extraction component of our system.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
