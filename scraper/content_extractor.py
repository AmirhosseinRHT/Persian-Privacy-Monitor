# content_extractor.py
import re
import math
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import List, Tuple, Optional


class ContentExtractor:
    """Extracts relevant text blocks filtered by keywords.
    Features:
    - container scoring (keyword density) to find content areas
    - multi-threshold: select all containers above given score
    - structured parsing: dl/dt/dd and heading-based sections
    - substring keyword matching (keyword can be substring of a word)
    - ancestor-aware nav/footer detection
    """

    def __init__(self, keywords: List[str], min_line_length: int = 10,
                 container_score_threshold: float = 0.05,
                 multi_container_threshold: float = 0.2):
        self.keywords = [kw.lower() for kw in keywords]
        self.min_line_length = min_line_length
        self.min_section_words = max(5, self.min_line_length // 2)
        self.container_score_threshold = container_score_threshold
        self.multi_container_threshold = multi_container_threshold
        self._ancestor_check_depth = 6

    # ---- helpers ----
    def _clean_text(self, s: str) -> str:
        return re.sub(r"\s+", " ", s, flags=re.UNICODE).strip()

    def _words(self, s: str) -> List[str]:
        return re.findall(r"\w+", s, flags=re.UNICODE)

    def _get_soup(self, html: str) -> BeautifulSoup:
        """Helper to create BeautifulSoup object from HTML"""
        return BeautifulSoup(html, "html.parser")

    def _count_keywords(self, s: str) -> int:
        """Count keyword matches where a keyword is a substring of any word in s."""
        low = s.lower()
        words = self._words(low)
        return sum(1 for w in words for kw in self.keywords if kw and kw in w)

    def _is_nav_or_footer(self, el) -> bool:
        """Check the element and its ancestors for nav/footer indicators."""
        node, depth = el, 0
        while node is not None and depth < self._ancestor_check_depth:
            if isinstance(node, NavigableString):
                node = getattr(node, "parent", None)
                depth += 1
                continue

            tagname = getattr(node, "name", "") or ""
            if tagname.lower() == "footer":
                return True

            role = (node.get("role") or "") if isinstance(node, Tag) else ""
            classes = " ".join(node.get("class") or []) if isinstance(node, Tag) else ""
            id_attr = (node.get("id") or "") if isinstance(node, Tag) else ""
            marker = f"{role} {classes} {id_attr}"

            if re.search(
                r"\b(nav|navigation|footer|header|menu|breadcrumb|cookie|ads|navbar|site-footer|footer-shadow|fixed bottom)\b",
                marker,
                flags=re.I,
            ):
                return True

            node = getattr(node, "parent", None)
            depth += 1
        return False

    def _score_container(self, el) -> Tuple[float, int, int]:
        """Return (score, keyword_count, word_count) for a container element.
        If element has lots of text but few keywords, still score moderately.
        """
        if not isinstance(el, Tag):
            return 0.0, 0, 0

        text = self._clean_text(el.get_text(" ", strip=True) or "")
        words = self._words(text)
        word_count = max(1, len(words))
        keyword_count = self._count_keywords(text)
        score = keyword_count / math.sqrt(word_count)

        # Boost score if text is long, even with few keywords
        if word_count >= 50 and keyword_count == 0:
            score = 0.05  # small but enough to pass low threshold

        if self._is_nav_or_footer(el):
            score *= 0.1
        return score, keyword_count, word_count

    # ---- parsing helpers ----
    def _parse_dl_sections(self, container) -> List[Tuple[Optional[str], str]]:
        """Return list of (title, text) from dl/dt/dd pairs."""
        sections = []
        for dl in container.find_all("dl"):
            for dt in dl.find_all("dt"):
                title = self._clean_text(dt.get_text(" ", strip=True) or "")
                dd = dt.find_next_sibling("dd")
                if dd:
                    text = self._clean_text(dd.get_text(" ", strip=True) or "")
                else:
                    parts, sibling = [], dt.next_sibling
                    while sibling and getattr(sibling, "name", None) != "dt":
                        if isinstance(sibling, Tag) and sibling.get_text:
                            parts.append(self._clean_text(sibling.get_text(" ", strip=True)))
                        sibling = sibling.next_sibling
                    text = " ".join(p for p in parts if p)
                if title or text:
                    sections.append((title or None, text))
        return sections

    def _parse_heading_sections(self, container) -> List[Tuple[Optional[str], str]]:
        """Split container into sections by headings h1-h3."""
        headings = container.find_all(["h1", "h2", "h3"])
        if not headings:
            return self._collect_paragraphs(container)

        sections = []
        for h in headings:
            title = self._clean_text(h.get_text(" ", strip=True) or "")
            parts = []
            for sib in h.next_siblings:
                if getattr(sib, "name", None) in ("h1", "h2", "h3"):
                    break
                if isinstance(sib, Tag) and sib.get_text and not self._is_nav_or_footer(sib):
                    t = self._clean_text(sib.get_text(" ", strip=True) or "")
                    if t:
                        parts.append(t)
            sections.append((title or None, " ".join(parts)))
        return sections

    def _collect_paragraphs(self, container) -> List[Tuple[Optional[str], str]]:
        """Collect p/li/dd text inside a container."""
        text = []
        for tag in container.find_all(["p", "li", "dd"]):
            if self._is_nav_or_footer(tag):
                continue
            t = self._clean_text(tag.get_text(" ", strip=True) or "")
            if t:
                text.append(t)
        return [(None, " ".join(text))] if text else []

    def _collect_fallback(self, soup) -> List[str]:
        """Fallback: collect p/li/h1..h3 across body but skip nav/footer."""
        texts = []
        for tag in soup.find_all(["p", "li", "h1", "h2", "h3"]):
            if self._is_nav_or_footer(tag):
                continue
            txt = self._clean_text(tag.get_text(" ", strip=True) or "")
            if len(txt) >= self.min_line_length and (self._count_keywords(txt) > 0):
                texts.append(txt)
        return texts

    # ---- main pipeline ----
    def _find_candidates(self, soup) -> List[Tag]:
        """Find candidate containers for scoring."""
        selectors = [
            "main", "article", "section",
            "div#content", "div[id*='content']", "div[class*='content']",
            "div[class*='privacy']", "div[id*='privacy']", "dl", "body",
        ]
        candidates = [el for sel in selectors for el in soup.select(sel)]
        candidates.extend(soup.find_all("div", recursive=False)[:6])  # top divs
        return candidates

    def _select_containers(self, candidates: List[Tag]) -> List[Tag]:
        """Score and select containers based on thresholds."""
        scored = [(c, *self._score_container(c)) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        selected = []
        if scored:
            best_score = scored[0][1]
            if best_score >= self.container_score_threshold:
                selected.append(scored[0][0])
        for c, score, _, _ in scored[1:]:
            if score >= self.multi_container_threshold:
                selected.append(c)
        return selected

    def _extract_from_container(self, container: Tag) -> List[str]:
        """Extract text blocks from a container, including nested divs with long paragraphs."""
        sections_texts = []

        dl_secs = self._parse_dl_sections(container)
        h_secs = self._parse_heading_sections(container) if not dl_secs else []

        sections = dl_secs if dl_secs else h_secs
        for title, text in sections:
            cond = (
                (title and self._count_keywords(title) > 0)
                or (text and self._count_keywords(text) > 0)
                or (len(self._words(text)) >= self.min_section_words)
            )
            if cond:
                if title:
                    sections_texts.append(title)
                if text:
                    sections_texts.append(text)

        if not sections:
            for tag in container.find_all(["p", "li", "dd", "h1", "h2", "h3", "div"]):
                if self._is_nav_or_footer(tag):
                    continue
                txt = self._clean_text(tag.get_text(" ", strip=True) or "")
                if txt and len(txt.split()) >= 5:
                    sections_texts.append(txt)

        return sections_texts

    def _deduplicate(self, texts: List[str]) -> List[str]:
        """Remove duplicates and empty lines."""
        final_lines, seen = [], set()
        for line in texts:
            l = line.strip()
            if l and l not in seen:
                seen.add(l)
                final_lines.append(l)
        return final_lines

    def extract_blocks(self, html: str) -> str:
        """Extract relevant text blocks and filter by keyword substrings."""
        soup = BeautifulSoup(html, "html.parser")
        candidates = self._find_candidates(soup)
        selected = self._select_containers(candidates)

        sections_texts = []
        for container in selected:
            sections_texts.extend(self._extract_from_container(container))

        if not sections_texts:
            sections_texts.extend(self._collect_fallback(soup))

        return "\n\n".join(self._deduplicate(sections_texts))
