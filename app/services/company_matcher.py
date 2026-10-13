"""Company and ticker identification service with boundary regex and confidence scoring."""
import re
from typing import Dict, List, Optional, Tuple, Set
from pydantic import BaseModel
from app.models.schemas import CompanyInfo
from app.utils.logging_config import logger


class TickerMatch(BaseModel):
    symbol: str
    company_name: str
    method: str  # "symbol_dollar", "symbol_word", "exact_name", "alias"
    confidence: float
    is_uncertain: bool


# Registry of known companies in the watchlist with metadata
WATCHLIST_REGISTRY: Dict[str, CompanyInfo] = {
    "AAPL": CompanyInfo(
        symbol="AAPL",
        name="Apple Inc.",
        aliases=["Apple", "iPhone", "MacBook", "Tim Cook"],
        sector="Technology",
        exchange="NASDAQ",
        currency="USD"
    ),
    "MSFT": CompanyInfo(
        symbol="MSFT",
        name="Microsoft Corporation",
        aliases=["Microsoft", "Azure", "Satya Nadella", "Windows", "Xbox"],
        sector="Technology",
        exchange="NASDAQ",
        currency="USD"
    ),
    "GOOGL": CompanyInfo(
        symbol="GOOGL",
        name="Alphabet Inc.",
        aliases=["Alphabet", "Google", "Sundar Pichai", "YouTube", "DeepMind"],
        sector="Communication Services",
        exchange="NASDAQ",
        currency="USD"
    ),
    "AMZN": CompanyInfo(
        symbol="AMZN",
        name="Amazon.com Inc.",
        aliases=["Amazon", "AWS", "Andy Jassy", "Prime Video"],
        sector="Consumer Discretionary",
        exchange="NASDAQ",
        currency="USD"
    ),
    "NVDA": CompanyInfo(
        symbol="NVDA",
        name="NVIDIA Corporation",
        aliases=["NVIDIA", "Nvidia", "Jensen Huang", "Blackwell", "GeForce"],
        sector="Semiconductors",
        exchange="NASDAQ",
        currency="USD"
    ),
    "TSLA": CompanyInfo(
        symbol="TSLA",
        name="Tesla Inc.",
        aliases=["Tesla", "Elon Musk", "Model Y", "Model 3", "Cybertruck", "Gigafactory"],
        sector="Consumer Discretionary",
        exchange="NASDAQ",
        currency="USD"
    ),
    "META": CompanyInfo(
        symbol="META",
        name="Meta Platforms Inc.",
        aliases=["Meta", "Meta Platforms", "Facebook", "Instagram", "WhatsApp", "Mark Zuckerberg", "Llama"],
        sector="Communication Services",
        exchange="NASDAQ",
        currency="USD"
    )
}

# Ambiguous words that should never match as raw ticker symbols without explicit '$' prefix
AMBIGUOUS_TICKERS: Set[str] = {
    "A", "ON", "CAN", "IT", "SO", "NOW", "ALL", "BE", "FOR", "SEE", "AI", "US"
}


class CompanyMatcher:
    """Matches text against ticker symbols and company entities with high precision."""

    def __init__(self, registry: Optional[Dict[str, CompanyInfo]] = None):
        self.registry = registry or WATCHLIST_REGISTRY

    def match_article(self, text: str) -> List[TickerMatch]:
        """Scans headline and article body to identify relevant stocks."""
        if not text:
            return []

        matches: Dict[str, TickerMatch] = {}

        for symbol, info in self.registry.items():
            # 1. Match explicit ticker symbol with dollar sign (e.g. $AAPL) -> Confidence 1.0
            dollar_pattern = rf"\${symbol}\b"
            if re.search(dollar_pattern, text):
                matches[symbol] = TickerMatch(
                    symbol=symbol,
                    company_name=info.name,
                    method="symbol_dollar",
                    confidence=1.0,
                    is_uncertain=False
                )
                continue

            # 2. Match exact corporate name (e.g. "NVIDIA Corporation", "Apple Inc.") -> Confidence 0.98
            escaped_corp_name = re.escape(info.name)
            if re.search(rf"\b{escaped_corp_name}\b", text, re.IGNORECASE):
                matches[symbol] = TickerMatch(
                    symbol=symbol,
                    company_name=info.name,
                    method="exact_name",
                    confidence=0.98,
                    is_uncertain=False
                )
                continue

            # 3. Match explicit ticker in parentheses (e.g. "(NASDAQ: AAPL)" or "(AAPL)") -> Confidence 0.95
            paren_pattern = rf"\((?:NASDAQ:|NYSE:)?\s*{symbol}\)"
            if re.search(paren_pattern, text, re.IGNORECASE):
                matches[symbol] = TickerMatch(
                    symbol=symbol,
                    company_name=info.name,
                    method="symbol_parentheses",
                    confidence=0.95,
                    is_uncertain=False
                )
                continue

            # 4. Match common company alias / brand name (e.g. "Tesla", "Microsoft", "Azure") -> Confidence 0.90
            for alias in info.aliases:
                alias_pattern = rf"\b{re.escape(alias)}\b"
                if re.search(alias_pattern, text, re.IGNORECASE):
                    # Flag uncertain if alias is short or ambiguous
                    is_uncertain = len(alias) < 4
                    confidence = 0.85 if is_uncertain else 0.92
                    matches[symbol] = TickerMatch(
                        symbol=symbol,
                        company_name=info.name,
                        method=f"alias_{alias}",
                        confidence=confidence,
                        is_uncertain=is_uncertain
                    )
                    break

            # 5. Standalone ticker word matching only for non-ambiguous tickers -> Confidence 0.85
            if symbol not in matches and symbol not in AMBIGUOUS_TICKERS:
                word_pattern = rf"\b{symbol}\b"
                if re.search(word_pattern, text):
                    matches[symbol] = TickerMatch(
                        symbol=symbol,
                        company_name=info.name,
                        method="symbol_word",
                        confidence=0.85,
                        is_uncertain=False
                    )

        return list(matches.values())

    def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Returns metadata for a given symbol."""
        return self.registry.get(symbol.upper())
