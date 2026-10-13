"""Technical indicator calculations including SMA, EMA, RSI, MACD, and Bollinger Bands."""
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd
from app.models.schemas import TechnicalIndicators
from app.utils.logging_config import logger


class TechnicalIndicatorCalculator:
    """Calculates technical indicators on OHLCV price series."""

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> Optional[float]:
        """Calculates Relative Strength Index (RSI) using Wilder's smoothing."""
        if len(series) < period + 1:
            return None
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        val = rsi.iloc[-1]
        return round(float(val), 2) if not np.isnan(val) else None

    @staticmethod
    def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal_span: int = 9) -> Dict[str, Optional[float]]:
        """Calculates MACD line, signal line, and histogram."""
        if len(series) < slow + signal_span:
            return {"macd": None, "signal": None, "hist": None}

        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_span, adjust=False).mean()
        hist = macd_line - signal_line

        return {
            "macd": round(float(macd_line.iloc[-1]), 3) if not np.isnan(macd_line.iloc[-1]) else None,
            "signal": round(float(signal_line.iloc[-1]), 3) if not np.isnan(signal_line.iloc[-1]) else None,
            "hist": round(float(hist.iloc[-1]), 3) if not np.isnan(hist.iloc[-1]) else None
        }

    @staticmethod
    def calculate_bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0) -> Dict[str, Optional[float]]:
        """Calculates Bollinger Bands (Upper, Middle, Lower)."""
        if len(series) < period:
            return {"upper": None, "middle": None, "lower": None}

        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)

        return {
            "upper": round(float(upper.iloc[-1]), 2) if not np.isnan(upper.iloc[-1]) else None,
            "middle": round(float(sma.iloc[-1]), 2) if not np.isnan(sma.iloc[-1]) else None,
            "lower": round(float(lower.iloc[-1]), 2) if not np.isnan(lower.iloc[-1]) else None
        }

    def compute_all(self, df: pd.DataFrame, symbol: str) -> TechnicalIndicators:
        """Computes full suite of indicators from an OHLCV DataFrame."""
        if df.empty or "Close" not in df.columns or len(df) < 5:
            logger.warning(f"Insufficient candle count for symbol {symbol} to compute technical indicators.")
            return TechnicalIndicators(symbol=symbol, signal_summary="Insufficient Data")

        close = df["Close"]
        volume = df["Volume"] if "Volume" in df.columns else pd.Series(dtype=float)

        # SMAs
        sma_20 = round(float(close.rolling(window=20).mean().iloc[-1]), 2) if len(close) >= 20 else None
        sma_50 = round(float(close.rolling(window=50).mean().iloc[-1]), 2) if len(close) >= 50 else None

        # EMAs
        ema_12 = round(float(close.ewm(span=12, adjust=False).mean().iloc[-1]), 2) if len(close) >= 12 else None
        ema_26 = round(float(close.ewm(span=26, adjust=False).mean().iloc[-1]), 2) if len(close) >= 26 else None

        # RSI
        rsi_14 = self.calculate_rsi(close, period=14)

        # MACD
        macd_dict = self.calculate_macd(close)

        # Bollinger Bands
        bb_dict = self.calculate_bollinger_bands(close)

        # Volume SMA
        vol_sma_20 = round(float(volume.rolling(window=20).mean().iloc[-1]), 0) if len(volume) >= 20 else None

        # Derive Technical Bias Summary
        signals = []
        if rsi_14 is not None:
            if rsi_14 < 30:
                signals.append("Oversold (RSI < 30)")
            elif rsi_14 > 70:
                signals.append("Overbought (RSI > 70)")
            else:
                signals.append("RSI Neutral")

        curr_price = float(close.iloc[-1])
        if sma_20 and curr_price > sma_20:
            signals.append("Above 20-SMA")
        elif sma_20 and curr_price < sma_20:
            signals.append("Below 20-SMA")

        if macd_dict["hist"] is not None:
            if macd_dict["hist"] > 0:
                signals.append("Positive MACD Histogram")
            else:
                signals.append("Negative MACD Histogram")

        summary_text = " | ".join(signals) if signals else "Neutral"

        return TechnicalIndicators(
            symbol=symbol,
            sma_20=sma_20,
            sma_50=sma_50,
            ema_12=ema_12,
            ema_26=ema_26,
            rsi_14=rsi_14,
            macd_line=macd_dict["macd"],
            macd_signal=macd_dict["signal"],
            macd_histogram=macd_dict["hist"],
            bb_upper=bb_dict["upper"],
            bb_middle=bb_dict["middle"],
            bb_lower=bb_dict["lower"],
            volume_sma_20=vol_sma_20,
            signal_summary=summary_text
        )
