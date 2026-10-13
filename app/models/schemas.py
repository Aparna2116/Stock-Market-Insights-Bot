"""Pydantic data models and schemas for Stock Market Insights Bot."""
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class ArticleBase(BaseModel):
    title: str = Field(..., description="Article headline")
    source: str = Field(..., description="Publisher or news feed name")
    url: str = Field(..., description="Canonical article URL")
    published_at: Optional[str] = Field(None, description="ISO-formatted publication timestamp")
    raw_text: Optional[str] = Field(None, description="Raw article body or description")
    clean_text: Optional[str] = Field(None, description="Cleaned and normalised article text")


class ArticleCreate(ArticleBase):
    pass


class ArticleResponse(ArticleBase):
    id: int
    matched_symbols: List[str] = []
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class CompanyInfo(BaseModel):
    symbol: str
    name: str
    aliases: List[str] = []
    sector: Optional[str] = "Technology"
    exchange: str = "NASDAQ"
    currency: str = "USD"


class SentimentAnalysisResult(BaseModel):
    short_summary: str = Field(..., description="Concise summary of news development")
    company_name: str = Field(..., description="Identified company name")
    stock_symbol: str = Field(..., description="Stock ticker symbol")
    sentiment: Literal["positive", "negative", "neutral"] = Field(..., description="Sentiment label")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment polarity score from -1.0 to 1.0")
    event_category: str = Field(..., description="Category such as Earnings, Product, Legal, M&A, Macro")
    business_implications: str = Field(..., description="Impact on company operations and financials")
    positive_market_implications: str = Field(..., description="Potential upside stock impacts")
    negative_market_implications: str = Field(..., description="Potential downside risks or stock impacts")
    evidence: str = Field(..., description="Direct quote or factual excerpt from article")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    confidence_reasoning: str = Field(..., description="Reasoning behind confidence level")
    original_url: str = Field(..., description="Source article URL")
    published_at: Optional[str] = Field(None, description="Article publication timestamp")
    is_insufficient_information: bool = Field(False, description="Whether article lacks actionable facts")
    model_used: str = Field("rule_based", description="Model/method used for analysis")

    model_config = {"protected_namespaces": ()}


class MarketSnapshot(BaseModel):
    symbol: str
    timestamp: str
    current_price: float
    previous_close: float
    change_amount: float
    change_percent: float
    volume: int
    avg_volume_10d: Optional[int] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    data_source: str = "Yahoo Finance"
    is_demo_data: bool = False


class TechnicalIndicators(BaseModel):
    symbol: str
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    volume_sma_20: Optional[float] = None
    signal_summary: str = "Neutral"


class StockWatchItem(BaseModel):
    symbol: str
    company_name: str
    priority_score: float
    rank: int
    dominant_sentiment: str
    key_headline: str
    selection_rationale: str
    recent_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    rsi: Optional[float] = None
    technical_bias: str = "Neutral"
    material_risks: List[str] = []
    article_urls: List[str] = []


class DailyReport(BaseModel):
    report_id: str
    report_date: str
    generated_at: str
    market_session: str
    market_overview: str
    stocks_to_watch: List[StockWatchItem]
    high_impact_events: List[dict] = []
    risk_factors: List[str] = []
    disclaimer: str
    data_freshness_warning: str
