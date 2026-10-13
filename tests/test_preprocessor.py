"""Tests for NewsPreprocessor."""
import pytest
from app.models.schemas import ArticleBase
from app.services.news_preprocessor import NewsPreprocessor


def test_clean_text_html_stripping():
    preprocessor = NewsPreprocessor()
    html_input = "<p>NVIDIA shares <b>surged</b> today &amp; set records!</p>"
    cleaned = preprocessor.clean_text(html_input)
    assert cleaned == "NVIDIA shares surged today & set records!"
    assert "<p>" not in cleaned


def test_normalize_url_strips_tracking():
    preprocessor = NewsPreprocessor()
    raw_url = "https://finance.yahoo.com/news/apple-deal.html?utm_source=twitter&utm_medium=social&ref=feed"
    canonical = preprocessor.normalize_url(raw_url)
    assert "utm_source" not in canonical
    assert "ref=" not in canonical
    assert canonical == "https://finance.yahoo.com/news/apple-deal.html"


def test_deduplication_via_jaccard():
    preprocessor = NewsPreprocessor()
    art1 = ArticleBase(
        title="Apple Signs Cloud Deal With Google To Power New AI Models",
        source="Source A",
        url="https://source-a.com/article1",
        published_at="2026-10-13T08:00:00Z",
        raw_text="Apple signs major cloud agreement with Google."
    )
    art2 = ArticleBase(
        title="Apple Signs Major Cloud Deal With Google To Power AI Models",
        source="Source B (Syndicated)",
        url="https://source-b.com/article2",
        published_at="2026-10-13T08:10:00Z",
        raw_text="Apple signs major cloud deal with Google."
    )

    processed = preprocessor.process_articles([art1, art2], similarity_threshold=0.70)
    assert len(processed) == 1
    assert processed[0].title == art1.title
