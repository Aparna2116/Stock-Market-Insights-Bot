"""FastAPI REST routes for news, stock data, analyses, and report generation."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.db_models import ArticleRecord, SentimentRecord, MarketSnapshotRecord, DailyReportRecord
from app.models.schemas import (
    ArticleResponse, SentimentAnalysisResult, MarketSnapshot,
    TechnicalIndicators, StockWatchItem, DailyReport
)
from app.services.company_matcher import WATCHLIST_REGISTRY
from app.services.market_data import MarketDataService
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.utils.logging_config import logger

router = APIRouter(prefix="/api")


@router.get("/health")
def health_check():
    """Returns application health status and current operational mode."""
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "demo_mode": settings.DEMO_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "default_exchange": settings.DEFAULT_EXCHANGE
    }


@router.get("/companies")
def get_companies():
    """Returns the registered company watchlist with exchange metadata."""
    return [
        {
            "symbol": info.symbol,
            "name": info.name,
            "sector": info.sector,
            "exchange": info.exchange,
            "currency": info.currency,
            "aliases": info.aliases
        }
        for info in WATCHLIST_REGISTRY.values()
    ]


@router.get("/news")
def get_news(
    symbol: Optional[str] = Query(None, description="Filter by stock ticker symbol"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieves processed news articles from persistent storage."""
    query = db.query(ArticleRecord).order_by(ArticleRecord.created_at.desc())
    if symbol:
        query = query.filter(ArticleRecord.matched_symbols.like(f"%{symbol.upper()}%"))
    articles = query.limit(limit).all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "source": a.source,
            "url": a.url,
            "published_at": a.published_at,
            "matched_symbols": [s for s in a.matched_symbols.split(",") if s] if a.matched_symbols else [],
            "clean_text": a.clean_text,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in articles
    ]


@router.get("/analyses")
def get_analyses(
    symbol: Optional[str] = Query(None, description="Filter by ticker"),
    sentiment: Optional[str] = Query(None, description="positive, negative, or neutral"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieves structured sentiment analyses and event evaluations."""
    query = db.query(SentimentRecord).order_by(SentimentRecord.created_at.desc())
    if symbol:
        query = query.filter_by(symbol=symbol.upper())
    if sentiment:
        query = query.filter_by(sentiment=sentiment.lower())
    records = query.limit(limit).all()

    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "company_name": r.company_name,
            "sentiment": r.sentiment,
            "sentiment_score": r.sentiment_score,
            "event_category": r.event_category,
            "short_summary": r.short_summary,
            "business_implications": r.business_implications,
            "positive_market_implications": r.positive_market_implications,
            "negative_market_implications": r.negative_market_implications,
            "evidence": r.evidence,
            "confidence": r.confidence,
            "confidence_reasoning": r.confidence_reasoning,
            "model_used": r.model_used,
            "original_url": r.original_url,
            "published_at": r.published_at,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]


@router.get("/market-data/{symbol}")
def get_market_data(symbol: str, period: str = Query("60d", pattern="^(1mo|3mo|6mo|1y|60d)$")):
    """Returns historical candles, market snapshot, and technical indicators for a symbol."""
    service = MarketDataService(demo_mode=settings.DEMO_MODE)
    snap, indicators = service.get_market_snapshot(symbol.upper())
    history_df = service.get_historical_data(symbol.upper(), period=period)

    candles = []
    for date_idx, row in history_df.iterrows():
        candles.append({
            "date": date_idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"])
        })

    return {
        "symbol": symbol.upper(),
        "snapshot": snap.model_dump(),
        "indicators": indicators.model_dump(),
        "candles": candles
    }


@router.get("/report/latest")
def get_latest_report(db: Session = Depends(get_db)):
    """Fetches the most recently generated pre-market briefing report."""
    rec = db.query(DailyReportRecord).order_by(DailyReportRecord.created_at.desc()).first()
    if not rec:
        raise HTTPException(status_code=404, detail="No daily reports have been generated yet.")
    return json.loads(rec.content_json)


@router.post("/pipeline/run")
def trigger_pipeline_run(db: Session = Depends(get_db)):
    """Triggers a complete pipeline ingestion, analysis, and report generation run."""
    orchestrator = PipelineOrchestrator(demo_mode=settings.DEMO_MODE)
    result = orchestrator.run_pipeline(db=db)
    return {
        "status": "success",
        "report_id": result["report"].report_id,
        "articles_processed": result["articles_processed"],
        "stocks_watched_count": len(result["stocks_to_watch"]),
        "generated_at": result["report"].generated_at
    }
