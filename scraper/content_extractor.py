import re
from bs4 import BeautifulSoup


class ContentExtractor:
    """Extracts relevant text blocks filtered by keywords."""

    def __init__(self, keywords, min_line_length: int = 10):
        self.keywords = [kw.lower() for kw in keywords]
        self.min_line_length = min_line_length

    def extract_blocks(self, html: str) -> str:
        """Extract relevant text blocks and filter by keyword substrings."""
        soup = BeautifulSoup(html, "html.parser")
        texts = []

        for tag in soup.find_all(["p", "li", "h1", "h2", "h3"]):
            txt = re.sub(r"\s+", " ", tag.get_text(strip=True))
            if len(txt) >= self.min_line_length:
                if any(kw in txt.lower() for kw in self.keywords):
                    texts.append(txt)

        return "\n".join(texts)
