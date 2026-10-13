"""Tests for SentimentAnalyzer."""
import pytest
from app.models.schemas import ArticleBase
from app.services.sentiment_analyzer import SentimentAnalyzer


def test_positive_financial_sentiment():
    analyzer = SentimentAnalyzer(provider="rule_based")
    article = ArticleBase(
        title="NVIDIA Reports Record Earnings Surge and Strong Revenue Growth",
        source="Test Source",
        url="https://example.com/nvda",
        published_at="2026-10-13T07:00:00Z",
        raw_text="The company beat Wall Street expectations and reported a massive profit milestone with gross margin expansion."
    )
    res = analyzer.analyze(article, "NVDA", "NVIDIA Corporation")
    assert res.sentiment == "positive"
    assert res.sentiment_score > 0.2
    assert res.stock_symbol == "NVDA"
    assert res.is_insufficient_information is False
    assert res.confidence >= 0.75


def test_negative_financial_sentiment():
    analyzer = SentimentAnalyzer(provider="rule_based")
    article = ArticleBase(
        title="Tesla Recalls 85000 Vehicles as Safety Regulators Launch Defect Probe",
        source="Test Source",
        url="https://example.com/tsla",
        published_at="2026-10-13T07:00:00Z",
        raw_text="Regulators opened an investigation into steering failure risks. The recall triggered warnings of delivery delays."
    )
    res = analyzer.analyze(article, "TSLA", "Tesla Inc.")
    assert res.sentiment == "negative"
    assert res.sentiment_score < -0.2
    assert "Regulatory & Legal" in res.event_category
    assert res.negative_market_implications is not None


def test_insufficient_information_handling():
    analyzer = SentimentAnalyzer(provider="rule_based")
    article = ArticleBase(
        title="Quick update",
        source="Test",
        url="https://example.com/short",
        published_at="2026-10-13T07:00:00Z",
        raw_text="Short text"
    )
    res = analyzer.analyze(article, "AAPL", "Apple Inc.")
    assert res.is_insufficient_information is True
    assert res.confidence < 0.5
