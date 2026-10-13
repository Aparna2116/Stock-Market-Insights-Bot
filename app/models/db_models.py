"""SQLAlchemy ORM models for Stock Market Insights Bot."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ArticleRecord(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    source = Column(String(100), nullable=False)
    url = Column(String(1000), unique=True, nullable=False, index=True)
    published_at = Column(String(50), nullable=True)
    raw_text = Column(Text, nullable=True)
    clean_text = Column(Text, nullable=True)
    matched_symbols = Column(String(200), default="")  # Comma-separated symbols
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    analyses = relationship("SentimentRecord", back_populates="article", cascade="all, delete-orphan")


class SentimentRecord(Base):
    __tablename__ = "sentiment_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    sentiment = Column(String(20), nullable=False)  # positive, negative, neutral
    sentiment_score = Column(Float, nullable=False)
    event_category = Column(String(100), default="General News")
    short_summary = Column(Text, nullable=False)
    business_implications = Column(Text, nullable=True)
    positive_market_implications = Column(Text, nullable=True)
    negative_market_implications = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    confidence = Column(Float, default=0.8)
    confidence_reasoning = Column(Text, nullable=True)
    model_used = Column(String(50), default="rule_based")
    original_url = Column(String(1000), nullable=True)
    published_at = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    article = relationship("ArticleRecord", back_populates="analyses")


class MarketSnapshotRecord(Base):
    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(String(50), nullable=False)
    current_price = Column(Float, nullable=False)
    previous_close = Column(Float, nullable=False)
    change_percent = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    rsi_14 = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    signal_summary = Column(String(100), default="Neutral")
    is_demo_data = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DailyReportRecord(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(100), unique=True, nullable=False, index=True)
    report_date = Column(String(20), nullable=False, index=True)
    market_session = Column(String(50), default="Pre-Market")
    content_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
