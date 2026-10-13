"""Tests for CompanyMatcher."""
import pytest
from app.services.company_matcher import CompanyMatcher


def test_match_symbol_with_dollar_prefix():
    matcher = CompanyMatcher()
    text = "Traders are buying calls on $AAPL following strong pre-market volume."
    matches = matcher.match_article(text)
    symbols = [m.symbol for m in matches]
    assert "AAPL" in symbols
    match = next(m for m in matches if m.symbol == "AAPL")
    assert match.confidence == 1.0
    assert match.method == "symbol_dollar"


def test_match_company_name_and_parentheses():
    matcher = CompanyMatcher()
    text = "Tesla Inc (TSLA) announced a recall of 85,000 vehicles."
    matches = matcher.match_article(text)
    symbols = [m.symbol for m in matches]
    assert "TSLA" in symbols
    match = next(m for m in matches if m.symbol == "TSLA")
    assert match.confidence >= 0.95


def test_avoid_false_positive_ambiguous_words():
    matcher = CompanyMatcher()
    # "A", "ON", "CAN", "IT" are common words that should not be matched without explicit dollar sign
    text = "A major hurricane hit the east coast on Monday and it can cause delays."
    matches = matcher.match_article(text)
    symbols = [m.symbol for m in matches]
    assert "A" not in symbols
    assert "ON" not in symbols
    assert "CAN" not in symbols
    assert "IT" not in symbols
