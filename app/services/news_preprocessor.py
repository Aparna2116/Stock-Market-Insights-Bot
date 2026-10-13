"""News preprocessor for cleaning, normalization, timestamp formatting, and deduplication."""
import re
import urllib.parse
from datetime import datetime, timezone
from typing import List, Set, Tuple
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from app.models.schemas import ArticleBase
from app.utils.logging_config import logger


class NewsPreprocessor:
    """Preprocesses raw article feeds with cleaning, canonicalization, and deduplication."""

    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "ref", "guccounter", "ncid", "src"
    }

    @staticmethod
    def clean_text(text: str) -> str:
        """Removes HTML markup, strips whitespace, and normalises unicode characters."""
        if not text:
            return ""
        # Remove HTML
        soup = BeautifulSoup(text, "html.parser")
        cleaned = soup.get_text(separator=" ")
        # Normalise unicode spaces and excessive whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    @classmethod
    def normalize_url(cls, url: str) -> str:
        """Strips URL tracking parameters and returns a canonical URL."""
        if not url:
            return ""
        parsed = urllib.parse.urlparse(url.strip())
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        filtered_pairs = [
            (k, v) for k, v in query_pairs if k.lower() not in cls.TRACKING_PARAMS
        ]
        new_query = urllib.parse.urlencode(filtered_pairs)
        canonical = urllib.parse.urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            new_query,
            ""
        ))
        return canonical

    @staticmethod
    def parse_timestamp(date_str: str | None) -> str:
        """Parses various datetime string formats into a standardized ISO-8601 UTC string."""
        if not date_str:
            return datetime.now(timezone.utc).isoformat()
        try:
            dt = date_parser.parse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def compute_jaccard_similarity(text1: str, text2: str) -> float:
        """Computes Jaccard word-set similarity between two strings."""
        words1 = set(re.findall(r"\w+", text1.lower()))
        words2 = set(re.findall(r"\w+", text2.lower()))
        if not words1 or not words2:
            return 0.0
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        return intersection / union if union > 0 else 0.0

    def process_articles(self, articles: List[ArticleBase], similarity_threshold: float = 0.75) -> List[ArticleBase]:
        """Cleans, normalises, and deduplicates a batch of articles."""
        seen_urls: Set[str] = set()
        unique_articles: List[ArticleBase] = []

        for article in articles:
            # 1. Basic validation
            clean_title = self.clean_text(article.title)
            if not clean_title or len(clean_title) < 10:
                continue

            # 2. Canonical URL normalization & exact URL deduplication
            canonical_url = self.normalize_url(article.url)
            if not canonical_url or canonical_url in seen_urls:
                continue

            # 3. Text cleaning
            clean_body = self.clean_text(article.raw_text or "")
            clean_ts = self.parse_timestamp(article.published_at)

            # 4. Content similarity check against already accepted articles
            is_duplicate = False
            for existing in unique_articles:
                sim = self.compute_jaccard_similarity(clean_title, existing.title)
                if sim >= similarity_threshold:
                    logger.debug(f"Discarding duplicate article '{clean_title}' (Similarity {sim:.2f} with '{existing.title}')")
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            seen_urls.add(canonical_url)
            unique_articles.append(ArticleBase(
                title=clean_title,
                source=article.source.strip(),
                url=canonical_url,
                published_at=clean_ts,
                raw_text=article.raw_text,
                clean_text=clean_body
            ))

        logger.info(f"Preprocessed {len(articles)} raw articles down to {len(unique_articles)} clean unique articles.")
        return unique_articles
