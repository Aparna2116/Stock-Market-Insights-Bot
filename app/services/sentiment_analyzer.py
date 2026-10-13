"""Financial news sentiment and LLM-driven event impact analysis service."""
import json
import re
from typing import Optional, Dict, Any, List
import requests

from app.config import settings
from app.models.schemas import SentimentAnalysisResult, ArticleBase
from app.utils.logging_config import logger

# Loughran-McDonald inspired financial sentiment lexicon & event patterns
FINANCIAL_POSITIVE_WORDS = {
    "surge", "surged", "surging", "record", "profit", "profitable", "growth", "growing",
    "exceeded", "beat", "outperform", "outperformed", "strong", "rebound", "soar", "soared",
    "breakthrough", "gain", "gains", "dividend", "revenue", "expansion", "partnership",
    "awarded", "deal", "approval", "milestone", "bullish", "rally", "upgrade", "upgraded",
    "higher", "expansion", "optimism", "boost", "boosted"
}

FINANCIAL_NEGATIVE_WORDS = {
    "plunge", "plunged", "drop", "dropped", "decline", "declined", "loss", "losses",
    "miss", "missed", "slump", "probe", "investigation", "recall", "recalls", "lawsuit",
    "antitrust", "penalty", "fine", "scrutiny", "downgrade", "downgraded", "bearish",
    "warning", "slashed", "layoff", "layoffs", "delay", "delayed", "vulnerability",
    "breach", "debt", "default", "scandal", "struggle", "fall", "lower"
}

EVENT_CATEGORIES = {
    "Earnings & Revenue": ["earnings", "quarterly", "revenue", "profit", "margin", "guidance", "fiscal"],
    "Product & Innovation": ["unveil", "unveils", "launch", "announced", "architecture", "chip", "model", "release"],
    "Regulatory & Legal": ["antitrust", "probe", "recall", "recalls", "investigation", "regulators", "lawsuit", "court", "compliance"],
    "Contracts & Partnerships": ["deal", "contract", "agreement", "partnership", "awarded", "procurement"],
    "Management & Corporate": ["ceo", "executive", "board", "leadership", "appoint", "resigned"],
    "Macro & Market": ["inflation", "interest rates", "fed", "tariff", "recession", "gdp"]
}


class SentimentAnalyzer:
    """Performs structured financial sentiment analysis and event impact evaluation."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        self.groq_api_key = settings.GROQ_API_KEY
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.groq_model = settings.GROQ_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    def analyze(self, article: ArticleBase, symbol: str, company_name: str) -> SentimentAnalysisResult:
        """Analyzes an article for a given stock symbol using LLM or rule-based fallback."""
        text = f"{article.title}. {article.clean_text or ''}".strip()

        # Insufficient info check
        if len(text.split()) < 8:
            return SentimentAnalysisResult(
                short_summary="Insufficient article content provided to extract market insights.",
                company_name=company_name,
                stock_symbol=symbol,
                sentiment="neutral",
                sentiment_score=0.0,
                event_category="General News",
                business_implications="Not enough verifiable information to evaluate business impact.",
                positive_market_implications="None identified due to sparse data.",
                negative_market_implications="None identified due to sparse data.",
                evidence="Article content below minimum analytical threshold.",
                confidence=0.2,
                confidence_reasoning="Content length is too short to establish causal financial inferences.",
                original_url=article.url,
                published_at=article.published_at,
                is_insufficient_information=True,
                model_used="validator"
            )

        # Attempt LLM if configured and key is present
        if self.provider == "groq" and self.groq_api_key:
            try:
                return self._analyze_groq(article, symbol, company_name)
            except Exception as e:
                logger.warning(f"Groq LLM analysis failed ({e}). Falling back to rule-based financial NLP analyzer.")

        # Default / Fallback: High-precision Financial NLP Lexicon Analyzer
        return self._analyze_rule_based(article, symbol, company_name, model_label="rule_based")

    def _analyze_rule_based(self, article: ArticleBase, symbol: str, company_name: str, model_label: str = "rule_based") -> SentimentAnalysisResult:
        """Rule-based financial sentiment evaluation grounded in financial terminology."""
        text = f"{article.title}. {article.clean_text or ''}"
        words = re.findall(r"\b\w+\b", text.lower())

        pos_count = sum(1 for w in words if w in FINANCIAL_POSITIVE_WORDS)
        neg_count = sum(1 for w in words if w in FINANCIAL_NEGATIVE_WORDS)

        total_sentiment_words = pos_count + neg_count

        if total_sentiment_words == 0:
            score = 0.0
            sentiment = "neutral"
            confidence = 0.70
            conf_reason = "Balanced or neutral narrative with no strong positive or negative financial polarity."
        else:
            raw_score = (pos_count - neg_count) / max(total_sentiment_words, 1)
            score = round(max(min(raw_score, 1.0), -1.0), 2)
            if score >= 0.20:
                sentiment = "positive"
                conf_reason = f"High positive sentiment density ({pos_count} positive vs {neg_count} negative financial terms)."
            elif score <= -0.20:
                sentiment = "negative"
                conf_reason = f"Negative sentiment indicators detected ({neg_count} risk/adverse vs {pos_count} positive terms)."
            else:
                sentiment = "neutral"
                conf_reason = f"Equally balanced sentiment signals ({pos_count} positive, {neg_count} negative terms)."
            confidence = min(round(0.75 + (abs(score) * 0.2), 2), 0.95)

        # Categorize event by highest keyword match frequency
        event_cat = "General Market Development"
        best_match_count = 0
        text_lower = text.lower()
        for cat, keywords in EVENT_CATEGORIES.items():
            count = sum(1 for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", text_lower))
            if count > best_match_count:
                best_match_count = count
                event_cat = cat

        # Extract evidence sentence
        sentences = re.split(r"(?<=[.!?])\s+", text)
        evidence_candidate = ""
        for s in sentences:
            if symbol.lower() in s.lower() or company_name.split()[0].lower() in s.lower():
                evidence_candidate = s.strip()
                break
        if not evidence_candidate and sentences:
            evidence_candidate = sentences[0].strip()

        # Generate contextual implications
        if sentiment == "positive":
            biz_imp = f"Potential operational tailwinds from {event_cat.lower()} supporting revenue momentum for {company_name}."
            pos_mkt = f"Strengthens investor sentiment; potential buying pressure on {symbol} if broader market conditions support."
            neg_mkt = f"Valuation multiple risk if execution milestones fail to match elevated forward expectations."
        elif sentiment == "negative":
            biz_imp = f"Operational and financial headwinds from {event_cat.lower()} may inflate costs or impair sales for {company_name}."
            pos_mkt = f"Oversold conditions could attract long-term value accumulation if risks are proven temporary."
            neg_mkt = f"Elevated near-term downside volatility and potential margin compression for {symbol}."
        else:
            biz_imp = f"Incremental developments regarding {event_cat.lower()} with moderate structural impact on {company_name}."
            pos_mkt = f"Maintains baseline stability if sector fundamentals remain intact."
            neg_mkt = f"Lack of immediate upside catalyst may cause {symbol} to trade in line with broader market indexes."

        return SentimentAnalysisResult(
            short_summary=f"{article.title}. {company_name} faces developments in {event_cat.lower()}.",
            company_name=company_name,
            stock_symbol=symbol,
            sentiment=sentiment,
            sentiment_score=score,
            event_category=event_cat,
            business_implications=biz_imp,
            positive_market_implications=pos_mkt,
            negative_market_implications=neg_mkt,
            evidence=evidence_candidate or article.title,
            confidence=confidence,
            confidence_reasoning=conf_reason,
            original_url=article.url,
            published_at=article.published_at,
            is_insufficient_information=False,
            model_used=model_label
        )

    def _analyze_groq(self, article: ArticleBase, symbol: str, company_name: str) -> SentimentAnalysisResult:
        """Queries Groq Llama 3 API for structured JSON sentiment & impact reasoning."""
        prompt = f"""
You are a senior financial analyst and NLP specialist. Analyze the following news development for {company_name} ({symbol}).
Do not invent prices or fake numerical targets. If evidence is insufficient, note it.

Article Title: {article.title}
Content: {article.clean_text or article.title}
URL: {article.url}
Published: {article.published_at}

Return ONLY a valid JSON object matching this schema:
{{
  "short_summary": "Concise 1-2 sentence summary",
  "company_name": "{company_name}",
  "stock_symbol": "{symbol}",
  "sentiment": "positive" | "negative" | "neutral",
  "sentiment_score": float between -1.0 and 1.0,
  "event_category": "Earnings & Revenue" | "Product & Innovation" | "Regulatory & Legal" | "Contracts & Partnerships" | "Management & Corporate" | "Macro & Market",
  "business_implications": "Impact on business operations",
  "positive_market_implications": "Potential positive market impacts",
  "negative_market_implications": "Potential downside risks",
  "evidence": "Direct quote or exact factual sentence from the text",
  "confidence": float between 0.0 and 1.0,
  "confidence_reasoning": "Reason for this confidence rating",
  "original_url": "{article.url}",
  "published_at": "{article.published_at}",
  "is_insufficient_information": false
}}
"""
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": "You are a professional financial news analyst providing structured JSON outputs."},
                {"role": "user", "content": prompt}
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "response_format": {"type": "json_object"}
        }

        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Groq API returned HTTP {resp.status_code}: {resp.text}")

        res_data = resp.json()
        content = res_data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        parsed["model_used"] = f"groq:{self.groq_model}"
        return SentimentAnalysisResult(**parsed)
