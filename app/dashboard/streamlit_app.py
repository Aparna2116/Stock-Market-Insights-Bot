"""Streamlit Interactive Dashboard for Stock Market Insights Bot."""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path so imports work seamlessly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app.config import settings
from app.database import init_db, SessionLocal
from app.models.db_models import ArticleRecord, SentimentRecord, DailyReportRecord
from app.services.company_matcher import WATCHLIST_REGISTRY
from app.services.market_data import MarketDataService
from app.services.pipeline_orchestrator import PipelineOrchestrator

# Configure page layout
st.set_page_config(
    page_title="Stock Market Insights Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB
init_db()


def get_db_session():
    return SessionLocal()


# Top Header & Mode Banner
st.title("📈 AI-Powered Stock Market Insights Bot")
st.caption(
    "Automated Pre-Market Financial Intelligence, LLM Event Impact Evaluation & Technical Divergence Screener"
)

# Header Alert / Mode Badges
mode_col1, mode_col2, mode_col3 = st.columns([2, 1, 1])
with mode_col1:
    if settings.DEMO_MODE:
        st.info("ℹ️ **Running in DEMO MODE**: Safe offline execution using verifiable financial news fixtures & simulated price series.")
    else:
        st.success("🟢 **Running in LIVE MODE**: Actively connected to live RSS feeds and market data.")
with mode_col2:
    st.markdown(f"**Default Exchange**: `{settings.DEFAULT_EXCHANGE}`")
with mode_col3:
    st.markdown(f"**NLP Provider**: `{settings.LLM_PROVIDER.upper()}`")

# Sidebar Controls
st.sidebar.header("🕹️ Controls & Navigation")
nav_choice = st.sidebar.radio(
    "Select View",
    ["📊 Dashboard Overview", "🔍 Stock Deep Dive & Charts", "📰 News & AI Impact Feed", "📑 Daily Pre-Market Report", "⚙️ System & SDGs"]
)

# Pipeline Trigger in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Pipeline Operations")
if st.sidebar.button("Run News & Analysis Pipeline", use_container_width=True):
    with st.spinner("Collecting news, running NLP impact analysis, and calculating indicators..."):
        db = get_db_session()
        try:
            orchestrator = PipelineOrchestrator(demo_mode=settings.DEMO_MODE)
            result = orchestrator.run_pipeline(db=db)
            st.sidebar.success(f"Pipeline executed! Report: {result['report'].report_id}")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Pipeline run error: {e}")
        finally:
            db.close()

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Project Authors**:\n"
    "- Abel Louis Fernandez (B23CS2103)\n"
    "- Akshay P. Benjamin (B23CS2112)\n"
    "- Aparna S. (B23CS2116)\n"
    "- Goutham C.S. (B23CS2130)\n\n"
    "**Advisor**: Ms. Diana Mathew\n"
    "Dept. of Computer Science & Engineering"
)

db = get_db_session()

# Check if data exists
articles_count = db.query(ArticleRecord).count()
analyses_count = db.query(SentimentRecord).count()
latest_report_record = db.query(DailyReportRecord).order_by(DailyReportRecord.created_at.desc()).first()

if articles_count == 0:
    st.warning("⚠️ No data in database yet! Automatically triggering initial data collection...")
    orchestrator = PipelineOrchestrator(demo_mode=settings.DEMO_MODE)
    orchestrator.run_pipeline(db=db)
    st.rerun()

# VIEW 1: DASHBOARD OVERVIEW
if nav_choice == "📊 Dashboard Overview":
    st.subheader("Key Market Sentiment & Watchlist Metrics")

    # Metrics Row
    bullish_analyses = db.query(SentimentRecord).filter_by(sentiment="positive").count()
    bearish_analyses = db.query(SentimentRecord).filter_by(sentiment="negative").count()
    neutral_analyses = db.query(SentimentRecord).filter_by(sentiment="neutral").count()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Processed Articles", articles_count)
    m2.metric("Total Analyses Extracted", analyses_count)
    m3.metric("Bullish vs Bearish Catalysts", f"{bullish_analyses} / {bearish_analyses}")
    m4.metric("Active Watchlist Tickers", len(WATCHLIST_REGISTRY))

    st.markdown("---")
    st.subheader("⭐ Top Stocks to Watch (Priority Ranked)")

    if latest_report_record:
        report_data = json.loads(latest_report_record.content_json)
        stocks_to_watch = report_data.get("stocks_to_watch", [])

        if stocks_to_watch:
            watch_df = pd.DataFrame([
                {
                    "Rank": f"#{s['rank']}",
                    "Symbol": s["symbol"],
                    "Company": s["company_name"],
                    "Priority Score": f"{s['priority_score']:.2f}",
                    "Sentiment": s["dominant_sentiment"].upper(),
                    "Technical Bias": s["technical_bias"],
                    "Recent Price": f"${s['recent_price']:.2f}" if s.get("recent_price") else "N/A",
                    "Change %": f"{s['price_change_pct']:+0.2f}%" if s.get("price_change_pct") is not None else "N/A",
                    "RSI (14)": f"{s['rsi']:.1f}" if s.get("rsi") is not None else "N/A",
                }
                for s in stocks_to_watch
            ])
            st.dataframe(watch_df, use_container_width=True, hide_index=True)

            st.markdown("#### Highlighted Stock Catalysts")
            for item in stocks_to_watch[:3]:
                sentiment_color = "🟢" if item["dominant_sentiment"] == "positive" else ("🔴" if item["dominant_sentiment"] == "negative" else "⚪")
                with st.expander(f"{sentiment_color} #{item['rank']} {item['symbol']} — {item['company_name']} (Score: {item['priority_score']:.2f})"):
                    st.markdown(f"**Key Catalyst**: {item['key_headline']}")
                    st.markdown(f"**Selection Rationale**: {item['selection_rationale']}")
                    if item.get("material_risks"):
                        st.markdown(f"**Material Risks**: {', '.join(item['material_risks'])}")
                    if item.get("article_urls"):
                        st.markdown(f"🔗 [Read Source Article]({item['article_urls'][0]})")

    st.markdown("---")
    st.subheader("🔥 Latest High-Impact Event Summaries")
    recent_analyses = db.query(SentimentRecord).order_by(SentimentRecord.created_at.desc()).limit(6).all()
    cols = st.columns(2)
    for idx, rec in enumerate(recent_analyses):
        with cols[idx % 2]:
            st.markdown(f"##### {rec.symbol} — {rec.event_category}")
            badge = "🟢 POSITIVE" if rec.sentiment == "positive" else ("🔴 NEGATIVE" if rec.sentiment == "negative" else "⚪ NEUTRAL")
            st.markdown(f"**Sentiment**: {badge} (Score: {rec.sentiment_score:+0.2f}) | **Confidence**: {rec.confidence * 100:.0f}%")
            st.write(rec.short_summary)
            if rec.evidence:
                st.caption(f"**Evidence**: \"{rec.evidence}\"")
            if rec.original_url:
                st.markdown(f"[Source Article]({rec.original_url})")
            st.markdown("---")

# VIEW 2: STOCK DEEP DIVE & CHARTS
elif nav_choice == "🔍 Stock Deep Dive & Charts":
    st.subheader("Stock Deep Dive & Interactive Technical Analysis")

    selected_symbol = st.selectbox(
        "Choose a Stock Ticker from Watchlist:",
        options=list(WATCHLIST_REGISTRY.keys()),
        index=0
    )
    company_meta = WATCHLIST_REGISTRY[selected_symbol]
    st.markdown(f"### {company_meta.name} (`{company_meta.symbol}`) — {company_meta.sector} | {company_meta.exchange}")

    market_service = MarketDataService(demo_mode=settings.DEMO_MODE)
    snap, inds = market_service.get_market_snapshot(selected_symbol)
    df = market_service.get_historical_data(selected_symbol, period="60d")

    # Snapshot metric cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price", f"${snap.current_price:.2f}", f"{snap.change_percent:+0.2f}%")
    c2.metric("Previous Close", f"${snap.previous_close:.2f}")
    c3.metric("RSI (14)", f"{inds.rsi_14:.1f}" if inds.rsi_14 else "N/A", inds.signal_summary)
    c4.metric("20-Day SMA", f"${inds.sma_20:.2f}" if inds.sma_20 else "N/A")

    # Plotly Interactive Candlestick + Volume + RSI Chart
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=[f"{selected_symbol} Daily Price & Moving Averages", "Relative Strength Index (RSI 14)"]
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="OHLC"
    ), row=1, col=1)

    # 20 SMA
    if len(df) >= 20:
        sma_20_series = df["Close"].rolling(window=20).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=sma_20_series, line=dict(color="#FF9900", width=1.5), name="20 SMA"
        ), row=1, col=1)

    # Bollinger Bands
    if inds.bb_upper and inds.bb_lower and len(df) >= 20:
        sma_val = df["Close"].rolling(window=20).mean()
        std_val = df["Close"].rolling(window=20).std()
        fig.add_trace(go.Scatter(
            x=df.index, y=sma_val + 2*std_val, line=dict(color="rgba(100, 149, 237, 0.5)", dash="dot"), name="BB Upper"
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=sma_val - 2*std_val, line=dict(color="rgba(100, 149, 237, 0.5)", dash="dot"), name="BB Lower"
        ), row=1, col=1)

    # RSI
    if len(df) >= 15:
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        fig.add_trace(go.Scatter(
            x=df.index, y=rsi_series, line=dict(color="#9B59B6", width=2), name="RSI (14)"
        ), row=2, col=1)

        # Overbought / Oversold threshold lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(
        height=650,
        xaxis_rangeslider_visible=False,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Company specific news analyses
    st.markdown("#### Relevant News & Event Analyses")
    sym_analyses = db.query(SentimentRecord).filter_by(symbol=selected_symbol).order_by(SentimentRecord.created_at.desc()).all()
    if sym_analyses:
        for sa in sym_analyses:
            with st.container(border=True):
                st.markdown(f"**Event**: {sa.event_category} | **Sentiment**: `{sa.sentiment.upper()}` ({sa.sentiment_score:+0.2f})")
                st.write(f"**Summary**: {sa.short_summary}")
                st.markdown(f"- **Business Implications**: {sa.business_implications}")
                st.markdown(f"- **Potential Upside**: {sa.positive_market_implications}")
                st.markdown(f"- **Potential Risks**: {sa.negative_market_implications}")
                st.caption(f"**Evidence**: \"{sa.evidence}\" | **Confidence**: {sa.confidence_reasoning}")
                if sa.original_url:
                    st.markdown(f"🔗 [Original Source]({sa.original_url})")
    else:
        st.info(f"No specific news articles recorded for {selected_symbol} yet.")

# VIEW 3: NEWS & AI IMPACT FEED
elif nav_choice == "📰 News & AI Impact Feed":
    st.subheader("Financial News Feed & Structured Impact Analyses")

    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_query = st.text_input("Search news by keyword or entity:", "")
    with f_col2:
        sentiment_filter = st.selectbox("Filter Sentiment:", ["All", "positive", "negative", "neutral"])
    with f_col3:
        symbol_filter = st.selectbox("Filter Ticker:", ["All"] + list(WATCHLIST_REGISTRY.keys()))

    query = db.query(SentimentRecord).order_by(SentimentRecord.created_at.desc())
    if sentiment_filter != "All":
        query = query.filter_by(sentiment=sentiment_filter)
    if symbol_filter != "All":
        query = query.filter_by(symbol=symbol_filter)

    records = query.all()

    if search_query:
        records = [
            r for r in records
            if search_query.lower() in r.short_summary.lower()
            or search_query.lower() in r.company_name.lower()
            or search_query.lower() in r.event_category.lower()
        ]

    st.write(f"Showing **{len(records)}** structured news impact analyses:")

    for rec in records:
        with st.container(border=True):
            badge_icon = "🟢" if rec.sentiment == "positive" else ("🔴" if rec.sentiment == "negative" else "⚪")
            st.markdown(f"### {badge_icon} [{rec.symbol}] {rec.company_name} — {rec.event_category}")
            st.markdown(f"**Sentiment**: `{rec.sentiment.upper()}` (Polarity: {rec.sentiment_score:+0.2f}) | **Confidence**: {rec.confidence * 100:.0f}%")
            st.markdown(f"**Summary**: {rec.short_summary}")

            tab1, tab2, tab3 = st.tabs(["💼 Business Impact", "📊 Market Implications", "🔍 Quoted Evidence & Audit"])
            with tab1:
                st.write(rec.business_implications)
            with tab2:
                st.markdown(f"**Upside Potential**: {rec.positive_market_implications}")
                st.markdown(f"**Downside Risks**: {rec.negative_market_implications}")
            with tab3:
                st.markdown(f"**Quoted Article Fact**: \"{rec.evidence}\"")
                st.caption(f"Reasoning: {rec.confidence_reasoning} | Engine: {rec.model_used}")
                if rec.original_url:
                    st.markdown(f"🔗 [Read Original Source Article]({rec.original_url})")

# VIEW 4: DAILY PRE-MARKET REPORT
elif nav_choice == "📑 Daily Pre-Market Report":
    st.subheader("Daily Pre-Market Intelligence Briefing")

    if latest_report_record:
        report_data = json.loads(latest_report_record.content_json)

        st.markdown(f"### Pre-Market Briefing: {report_data['report_date']}")
        st.caption(f"**Report ID**: `{report_data['report_id']}` | **Session**: {report_data['market_session']} | **Generated At**: {report_data['generated_at'][:19]} UTC")

        st.info(f"**Macro Market Overview**:\n\n{report_data['market_overview']}")

        st.markdown("#### Stocks to Watch")
        for s in report_data.get("stocks_to_watch", []):
            badge = "🟢" if s["dominant_sentiment"] == "positive" else ("🔴" if s["dominant_sentiment"] == "negative" else "⚪")
            with st.expander(f"{badge} #{s['rank']} {s['symbol']} ({s['company_name']}) — Priority Score: {s['priority_score']:.2f}"):
                st.markdown(f"**Key Headline**: {s['key_headline']}")
                st.markdown(f"**Rationale**: {s['selection_rationale']}")
                st.markdown(f"**Technical Bias**: `{s['technical_bias']}` | **Recent Price**: ${s.get('recent_price', 0):.2f}")
                if s.get("material_risks"):
                    st.markdown(f"**Risks**: {', '.join(s['material_risks'])}")

        st.markdown("#### High-Impact Catalysts")
        for ev in report_data.get("high_impact_events", []):
            st.markdown(f"- **[{ev['symbol']}] {ev['headline']}** ({ev['category']} | `{ev['sentiment'].upper()}`)")
            if ev.get("evidence"):
                st.caption(f"Evidence: \"{ev['evidence']}\"")

        st.markdown("---")
        # Download buttons
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "📥 Download Report as JSON",
                data=latest_report_record.content_json,
                file_name=f"{report_data['report_id']}.json",
                mime="application/json",
                use_container_width=True
            )
        with col_d2:
            from app.services.report_generator import ReportGenerator
            from app.models.schemas import DailyReport
            daily_rep_obj = DailyReport(**report_data)
            md_text = ReportGenerator.to_markdown(daily_rep_obj)
            st.download_button(
                "📥 Download Report as Markdown",
                data=md_text,
                file_name=f"{report_data['report_id']}.md",
                mime="text/markdown",
                use_container_width=True
            )

        st.markdown("---")
        st.warning(f"⚠️ **Educational Disclaimer**:\n\n{report_data['disclaimer']}")
    else:
        st.info("No report generated yet. Click 'Run News & Analysis Pipeline' in the sidebar.")

# VIEW 5: SYSTEM & SDGS
elif nav_choice == "⚙️ System & SDGs":
    st.subheader("System Architecture & Sustainable Development Goals (SDGs)")

    st.markdown("""
### Alignment with United Nations Sustainable Development Goals:
- **SDG 8: Decent Work and Economic Growth**: Provides timely, accessible financial insights that support informed decision-making and productivity.
- **SDG 9: Industry, Innovation and Infrastructure**: Applies modern Generative AI, NLP, and automated data pipelines to create an innovative financial intelligence platform.
- **SDG 16: Peace, Justice and Strong Institutions**: Enhances transparency in financial information by transforming opaque corporate developments into clear, auditable insights with explicit source attribution.
- **SDG 4: Quality Education**: Fosters financial literacy by helping students, investors, and analysts understand market mechanics and the relationship between news sentiment and asset prices.
    """)

    st.markdown("---")
    st.markdown("### System Architecture Overview")
    st.code("""
┌────────────────────────┐      ┌────────────────────────┐
│  Multi-Source News     │      │   yfinance Market Data │
│  (RSS Feeds & Demodata)│      │   (OHLCV Candles)      │
└───────────┬────────────┘      └───────────┬────────────┘
            │                               │
            ▼                               ▼
┌────────────────────────┐      ┌────────────────────────┐
│  News Preprocessor &   │      │  Technical Indicators  │
│  Deduplication Engine  │      │  (SMA, EMA, RSI, MACD) │
└───────────┬────────────┘      └───────────┬────────────┘
            │                               │
            ▼                               │
┌────────────────────────┐                  │
│ Company & Ticker Match │                  │
└───────────┬────────────┘                  │
            │                               │
            ▼                               │
┌────────────────────────┐                  │
│ LLM / FinBERT / NLP    │                  │
│ Sentiment & Impact     │                  │
└───────────┬────────────┘                  │
            │                               │
            └───────────────┬───────────────┘
                            ▼
              ┌───────────────────────────┐
              │ Multi-Factor Priority     │
              │ Ranking & Insight Engine  │
              └─────────────┬─────────────┘
                            ▼
              ┌───────────────────────────┐
              │ Daily Pre-Market Briefing │
              │ (SQLite DB & Markdown/JSON│
              └─────────────┬─────────────┘
                            ▼
              ┌───────────────────────────┐
              │ Streamlit UI / FastAPI    │
              └───────────────────────────┘
    """, language="text")

# Educational Disclaimer Footer
st.markdown("---")
st.caption(
    "⚠️ **Academic Disclaimer**: This software is an informational research and education project developed by students at the Department of Computer Science & Engineering. "
    "It does not provide financial or investment advice. Simulated demo fixtures and historical quotes are used for demonstration."
)

db.close()
