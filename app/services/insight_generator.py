"""Insight generation service combining news sentiment, technical indicators, and priority ranking."""
from typing import List, Dict, Any, Tuple
from app.models.schemas import SentimentAnalysisResult, MarketSnapshot, TechnicalIndicators, StockWatchItem
from app.utils.logging_config import logger

EVENT_WEIGHTS: Dict[str, float] = {
    "Earnings & Revenue": 0.95,
    "Regulatory & Legal": 0.90,
    "Contracts & Partnerships": 0.80,
    "Product & Innovation": 0.75,
    "Macro & Market": 0.70,
    "Management & Corporate": 0.65,
    "General Market Development": 0.50,
}


class InsightGenerator:
    """Ranks and generates actionable pre-market stock insights combining news and technical signals."""

    @staticmethod
    def calculate_priority_score(
        analysis: SentimentAnalysisResult,
        snapshot: MarketSnapshot,
        indicators: TechnicalIndicators
    ) -> Tuple[float, str, List[str]]:
        """Calculates a transparent multi-factor priority score from 0.0 to 10.0.
        
        Formula:
        Score = 4.0 * |sentiment_score| 
              + 3.0 * event_weight 
              + 1.5 * technical_divergence_bonus 
              + 1.5 * volume_activity_factor
        """
        # 1. Sentiment magnitude (0 to 1.0)
        sentiment_mag = abs(analysis.sentiment_score)

        # 2. Event category weight
        event_weight = EVENT_WEIGHTS.get(analysis.event_category, 0.50)

        # 3. Technical divergence detection
        divergence_bonus = 0.0
        divergence_reasons = []
        rsi = indicators.rsi_14

        if rsi is not None:
            if analysis.sentiment == "positive" and rsi < 38:
                divergence_bonus = 0.8
                divergence_reasons.append(f"Bullish catalyst meets oversold technical condition (RSI {rsi:.1f}).")
            elif analysis.sentiment == "negative" and rsi > 65:
                divergence_bonus = 0.8
                divergence_reasons.append(f"Adverse news development collides with overbought technical levels (RSI {rsi:.1f}).")

        # 4. Volume activity factor
        vol_factor = 0.5
        if snapshot.avg_volume_10d and snapshot.volume > snapshot.avg_volume_10d * 1.2:
            vol_factor = 0.9
            divergence_reasons.append("Elevated trading volume preceding news announcement.")

        raw_score = (
            (4.0 * sentiment_mag) +
            (3.0 * event_weight) +
            (1.5 * divergence_bonus) +
            (1.5 * vol_factor)
        )
        final_score = round(min(max(raw_score, 1.0), 10.0), 2)

        # Rationale builder
        reasons = [
            f"High-impact {analysis.event_category} catalyst with {analysis.sentiment} sentiment score of {analysis.sentiment_score:+0.2f}."
        ]
        if divergence_reasons:
            reasons.extend(divergence_reasons)
        reasons.append(
            f"Prior session close at ${snapshot.previous_close:.2f} ({snapshot.change_percent:+0.2f}%)."
        )
        rationale_str = " ".join(reasons)

        # Risk factors
        risks = []
        if analysis.sentiment == "positive":
            risks.append("Execution delays or broader macroeconomic selloffs could temper positive momentum.")
            if indicators.rsi_14 and indicators.rsi_14 > 70:
                risks.append("Elevated RSI indicates short-term overbought risk despite positive headline.")
        elif analysis.sentiment == "negative":
            risks.append("Legal or regulatory scrutiny could result in prolonged margin compression.")
            if indicators.rsi_14 and indicators.rsi_14 < 30:
                risks.append("Deep oversold conditions may trigger technical mean-reversion bounces.")
        else:
            risks.append("Lack of strong directional catalyst may lead to sideways consolidation.")

        return final_score, rationale_str, risks

    def rank_stocks(
        self,
        analyses_by_symbol: Dict[str, List[SentimentAnalysisResult]],
        snapshots_by_symbol: Dict[str, MarketSnapshot],
        indicators_by_symbol: Dict[str, TechnicalIndicators]
    ) -> List[StockWatchItem]:
        """Ranks watchlist stocks by aggregated priority score and generates watchlist items."""
        ranked_candidates = []

        for symbol, analyses in analyses_by_symbol.items():
            if not analyses:
                continue

            snapshot = snapshots_by_symbol.get(symbol)
            indicators = indicators_by_symbol.get(symbol)
            if not snapshot or not indicators:
                continue

            # Pick highest severity analysis or average
            primary_analysis = max(analyses, key=lambda a: abs(a.sentiment_score))
            priority_score, rationale, risks = self.calculate_priority_score(
                primary_analysis, snapshot, indicators
            )

            urls = [a.original_url for a in analyses if a.original_url]

            tech_bias = "Neutral"
            if indicators.rsi_14:
                if indicators.rsi_14 < 35:
                    tech_bias = "Oversold"
                elif indicators.rsi_14 > 65:
                    tech_bias = "Overbought"
                else:
                    tech_bias = "Neutral Range"

            ranked_candidates.append({
                "symbol": symbol,
                "company_name": primary_analysis.company_name,
                "priority_score": priority_score,
                "dominant_sentiment": primary_analysis.sentiment,
                "key_headline": primary_analysis.short_summary,
                "selection_rationale": rationale,
                "recent_price": snapshot.current_price,
                "price_change_pct": snapshot.change_percent,
                "rsi": indicators.rsi_14,
                "technical_bias": tech_bias,
                "material_risks": risks,
                "article_urls": urls
            })

        # Sort descending by priority_score
        ranked_candidates.sort(key=lambda x: x["priority_score"], reverse=True)

        items: List[StockWatchItem] = []
        for rank_idx, cand in enumerate(ranked_candidates, start=1):
            cand["rank"] = rank_idx
            items.append(StockWatchItem(**cand))

        return items
