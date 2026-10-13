"""Orchestrates the entire end-to-end pipeline: ingestion, NLP, market data, and persistence."""
from typing import Dict, List, Any
import json
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.db_models import ArticleRecord, SentimentRecord, MarketSnapshotRecord, DailyReportRecord
from app.models.schemas import (
    ArticleBase, SentimentAnalysisResult, MarketSnapshot,
    TechnicalIndicators, StockWatchItem, DailyReport
)
from app.services.news_collector import NewsCollector
from app.services.news_preprocessor import NewsPreprocessor
from app.services.company_matcher import CompanyMatcher
from app.services.sentiment_analyzer import SentimentAnalyzer
from app.services.market_data import MarketDataService
from app.services.insight_generator import InsightGenerator
from app.services.report_generator import ReportGenerator
from app.utils.logging_config import logger


class PipelineOrchestrator:
    """Master workflow coordinator for Stock Market Insights Bot."""

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.collector = NewsCollector(demo_mode=self.demo_mode)
        self.preprocessor = NewsPreprocessor()
        self.matcher = CompanyMatcher()
        self.analyzer = SentimentAnalyzer()
        self.market_service = MarketDataService(demo_mode=self.demo_mode)
        self.insight_gen = InsightGenerator()
        self.report_gen = ReportGenerator()

    def run_pipeline(self, db: Session = None) -> Dict[str, Any]:
        """Executes full pipeline and returns complete insights payload."""
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            logger.info("Step 1: Ingesting financial news...")
            raw_articles = self.collector.fetch_articles()

            logger.info("Step 2: Cleaning and deduplicating news...")
            clean_articles = self.preprocessor.process_articles(raw_articles)

            logger.info("Step 3: Company entity matching and sentiment analysis...")
            all_analyses: List[SentimentAnalysisResult] = []
            analyses_by_symbol: Dict[str, List[SentimentAnalysisResult]] = {
                sym: [] for sym in settings.WATCHLIST
            }

            for article in clean_articles:
                full_text = f"{article.title}. {article.clean_text or ''}"
                matches = self.matcher.match_article(full_text)
                matched_symbols = [m.symbol for m in matches]

                # Check if article already exists in DB to prevent duplicates
                existing_article = db.query(ArticleRecord).filter_by(url=article.url).first()
                if not existing_article:
                    art_rec = ArticleRecord(
                        title=article.title,
                        source=article.source,
                        url=article.url,
                        published_at=article.published_at,
                        raw_text=article.raw_text,
                        clean_text=article.clean_text,
                        matched_symbols=",".join(matched_symbols)
                    )
                    db.add(art_rec)
                    db.flush()
                    art_id = art_rec.id
                else:
                    art_id = existing_article.id

                # Perform analysis for each matched symbol
                for match in matches:
                    sym = match.symbol
                    analysis = self.analyzer.analyze(article, sym, match.company_name)
                    all_analyses.append(analysis)
                    if sym in analyses_by_symbol:
                        analyses_by_symbol[sym].append(analysis)
                    else:
                        analyses_by_symbol[sym] = [analysis]

                    # Store sentiment analysis record
                    sent_rec = SentimentRecord(
                        article_id=art_id,
                        symbol=sym,
                        company_name=match.company_name,
                        sentiment=analysis.sentiment,
                        sentiment_score=analysis.sentiment_score,
                        event_category=analysis.event_category,
                        short_summary=analysis.short_summary,
                        business_implications=analysis.business_implications,
                        positive_market_implications=analysis.positive_market_implications,
                        negative_market_implications=analysis.negative_market_implications,
                        evidence=analysis.evidence,
                        confidence=analysis.confidence,
                        confidence_reasoning=analysis.confidence_reasoning,
                        model_used=analysis.model_used,
                        original_url=analysis.original_url,
                        published_at=analysis.published_at
                    )
                    db.add(sent_rec)

            db.commit()

            logger.info("Step 4: Fetching market snapshots and calculating technical indicators...")
            snapshots_by_symbol: Dict[str, MarketSnapshot] = {}
            indicators_by_symbol: Dict[str, TechnicalIndicators] = {}

            for sym in settings.WATCHLIST:
                snap, inds = self.market_service.get_market_snapshot(sym)
                snapshots_by_symbol[sym] = snap
                indicators_by_symbol[sym] = inds

                # Save market snapshot record
                mkt_rec = MarketSnapshotRecord(
                    symbol=sym,
                    timestamp=snap.timestamp,
                    current_price=snap.current_price,
                    previous_close=snap.previous_close,
                    change_percent=snap.change_percent,
                    volume=snap.volume,
                    rsi_14=inds.rsi_14,
                    sma_20=inds.sma_20,
                    signal_summary=inds.signal_summary,
                    is_demo_data=snap.is_demo_data
                )
                db.add(mkt_rec)

            db.commit()

            logger.info("Step 5: Ranking watch items and generating daily briefing...")
            stocks_to_watch = self.insight_gen.rank_stocks(
                analyses_by_symbol=analyses_by_symbol,
                snapshots_by_symbol=snapshots_by_symbol,
                indicators_by_symbol=indicators_by_symbol
            )

            report = self.report_gen.generate_report(
                stocks_to_watch=stocks_to_watch,
                analyses=all_analyses
            )

            # Persist report
            rep_rec = DailyReportRecord(
                report_id=report.report_id,
                report_date=report.report_date,
                market_session=report.market_session,
                content_json=report.model_dump_json()
            )
            db.add(rep_rec)
            db.commit()

            # Save report to disk as Markdown and JSON
            self.report_gen.save_report(report)

            logger.info(f"Pipeline execution completed successfully. {len(stocks_to_watch)} stocks prioritized.")

            return {
                "status": "success",
                "report": report,
                "stocks_to_watch": stocks_to_watch,
                "articles_processed": len(clean_articles),
                "analyses": all_analyses,
                "snapshots": snapshots_by_symbol,
                "indicators": indicators_by_symbol
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            raise e
        finally:
            if should_close_db:
                db.close()
