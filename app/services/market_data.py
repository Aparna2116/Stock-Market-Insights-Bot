"""Market data retrieval service with yfinance support and deterministic demo fallback."""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import numpy as np
import pandas as pd
import yfinance as yf

from app.config import settings
from app.models.schemas import MarketSnapshot, TechnicalIndicators
from app.services.technical_indicators import TechnicalIndicatorCalculator
from app.utils.logging_config import logger

# Deterministic baseline prices for watchlist demo mode
DEMO_BASELINES = {
    "AAPL": {"price": 232.50, "prev_close": 230.10, "high_52": 237.23, "low_52": 164.08, "vol": 48200000},
    "MSFT": {"price": 428.15, "prev_close": 425.80, "high_52": 468.35, "low_52": 366.50, "vol": 21500000},
    "GOOGL": {"price": 181.40, "prev_close": 179.90, "high_52": 193.31, "low_52": 129.40, "vol": 29800000},
    "AMZN": {"price": 194.80, "prev_close": 196.20, "high_52": 201.20, "low_52": 118.35, "vol": 38100000},
    "NVDA": {"price": 138.90, "prev_close": 134.25, "high_52": 140.76, "low_52": 39.23, "vol": 72400000},
    "TSLA": {"price": 221.30, "prev_close": 228.60, "high_52": 271.00, "low_52": 138.80, "vol": 64300000},
    "META": {"price": 592.70, "prev_close": 585.40, "high_52": 602.95, "low_52": 279.40, "vol": 14700000},
}


class MarketDataService:
    """Provides market snapshots and historical OHLCV series for stocks."""

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.indicator_calc = TechnicalIndicatorCalculator()

    def get_historical_data(self, symbol: str, period: str = "60d") -> pd.DataFrame:
        """Returns historical OHLCV candles as a pandas DataFrame."""
        if not self.demo_mode:
            try:
                logger.info(f"Retrieving live market candles from yfinance for {symbol}")
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period)
                if not df.empty and len(df) >= 10:
                    return df
                logger.warning(f"yfinance returned empty or insufficient history for {symbol}. Falling back to demo data.")
            except Exception as e:
                logger.warning(f"Error fetching live data for {symbol} ({e}). Falling back to demo data.")

        # Deterministic synthetic OHLCV generator for demo/offline use
        return self._generate_synthetic_candles(symbol)

    def _generate_synthetic_candles(self, symbol: str, num_days: int = 60) -> pd.DataFrame:
        """Generates realistic synthetic daily trading candles."""
        baseline = DEMO_BASELINES.get(symbol.upper(), {"price": 150.0, "prev_close": 149.0, "high_52": 180.0, "low_52": 110.0, "vol": 25000000})
        base_price = baseline["price"]

        np.random.seed(abs(hash(symbol)) % (2**31 - 1))
        dates = pd.date_range(end=datetime.now(timezone.utc), periods=num_days, freq="B")

        # Random walk for prices
        returns = np.random.normal(loc=0.001, scale=0.015, size=num_days)
        prices = base_price * np.exp(np.cumsum(returns) - np.sum(returns))

        open_p = prices * (1 + np.random.normal(0, 0.004, num_days))
        high_p = np.maximum(open_p, prices) * (1 + np.abs(np.random.normal(0, 0.008, num_days)))
        low_p = np.minimum(open_p, prices) * (1 - np.abs(np.random.normal(0, 0.008, num_days)))
        close_p = prices
        volumes = np.random.normal(baseline["vol"], baseline["vol"] * 0.2, num_days).astype(int)
        volumes = np.maximum(volumes, 1000000)

        df = pd.DataFrame({
            "Open": open_p,
            "High": high_p,
            "Low": low_p,
            "Close": close_p,
            "Volume": volumes
        }, index=dates)

        return df

    def get_market_snapshot(self, symbol: str) -> Tuple[MarketSnapshot, TechnicalIndicators]:
        """Retrieves latest snapshot and technical indicators for a given symbol."""
        df = self.get_historical_data(symbol, period="60d")
        indicators = self.indicator_calc.compute_all(df, symbol)

        if not self.demo_mode:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info if hasattr(ticker, "fast_info") else {}
                curr = getattr(info, "last_price", None)
                prev = getattr(info, "previous_close", None)
                vol = getattr(info, "last_volume", None)

                if curr and prev:
                    chg_amt = round(curr - prev, 2)
                    chg_pct = round((chg_amt / prev) * 100, 2)
                    snap = MarketSnapshot(
                        symbol=symbol.upper(),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        current_price=round(float(curr), 2),
                        previous_close=round(float(prev), 2),
                        change_amount=chg_amt,
                        change_percent=chg_pct,
                        volume=int(vol or df["Volume"].iloc[-1]),
                        avg_volume_10d=int(df["Volume"].tail(10).mean()) if len(df) >= 10 else None,
                        fifty_two_week_high=round(float(df["High"].max()), 2) if not df.empty else None,
                        fifty_two_week_low=round(float(df["Low"].min()), 2) if not df.empty else None,
                        data_source="Yahoo Finance (Live)",
                        is_demo_data=False
                    )
                    return snap, indicators
            except Exception as e:
                logger.warning(f"Fast info lookup failed for {symbol} ({e}). Using candle end values.")

        # Demo / Fallback snapshot from candle dataframe
        curr_p = round(float(df["Close"].iloc[-1]), 2)
        prev_p = round(float(df["Close"].iloc[-2]), 2) if len(df) >= 2 else curr_p
        chg_amt = round(curr_p - prev_p, 2)
        chg_pct = round((chg_amt / prev_p) * 100, 2) if prev_p else 0.0
        vol = int(df["Volume"].iloc[-1])

        snap = MarketSnapshot(
            symbol=symbol.upper(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            current_price=curr_p,
            previous_close=prev_p,
            change_amount=chg_amt,
            change_percent=chg_pct,
            volume=vol,
            avg_volume_10d=int(df["Volume"].tail(10).mean()) if len(df) >= 10 else vol,
            fifty_two_week_high=round(float(df["High"].max()), 2),
            fifty_two_week_low=round(float(df["Low"].min()), 2),
            data_source="Demo Data (Fixture)" if self.demo_mode else "Simulated Fallback",
            is_demo_data=True
        )
        return snap, indicators
