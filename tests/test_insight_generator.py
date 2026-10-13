"""Tests for InsightGenerator priority scoring and ranking."""
import pytest
from app.models.schemas import SentimentAnalysisResult, MarketSnapshot, TechnicalIndicators
from app.services.insight_generator import InsightGenerator


def test_priority_score_divergence_bonus():
    gen = InsightGenerator()

    # Positive news with oversold RSI should get a divergence bonus
    analysis = SentimentAnalysisResult(
        short_summary="NVIDIA earnings breakthrough",
        company_name="NVIDIA Corporation",
        stock_symbol="NVDA",
        sentiment="positive",
        sentiment_score=0.85,
        event_category="Earnings & Revenue",
        business_implications="Revenue surging",
        positive_market_implications="Upside momentum",
        negative_market_implications="Valuation risk",
        evidence="Gross margin 75%",
        confidence=0.9,
        confidence_reasoning="High confidence",
        original_url="https://example.com/nvda",
        published_at="2026-10-13T07:00:00Z"
    )

    snapshot = MarketSnapshot(
        symbol="NVDA",
        timestamp="2026-10-13T07:00:00Z",
        current_price=138.9,
        previous_close=134.2,
        change_amount=4.7,
        change_percent=3.5,
        volume=80000000,
        avg_volume_10d=60000000
    )

    indicators_oversold = TechnicalIndicators(
        symbol="NVDA",
        rsi_14=32.0,  # Oversold condition
        signal_summary="Oversold"
    )

    indicators_neutral = TechnicalIndicators(
        symbol="NVDA",
        rsi_14=50.0,
        signal_summary="Neutral"
    )

    score_oversold, rationale_oversold, _ = gen.calculate_priority_score(analysis, snapshot, indicators_oversold)
    score_neutral, rationale_neutral, _ = gen.calculate_priority_score(analysis, snapshot, indicators_neutral)

    assert score_oversold > score_neutral
    assert "oversold" in rationale_oversold.lower()
