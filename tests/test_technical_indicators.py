"""Tests for Technical Indicators calculations."""
import numpy as np
import pandas as pd
import pytest
from app.services.technical_indicators import TechnicalIndicatorCalculator


def test_rsi_calculation():
    calc = TechnicalIndicatorCalculator()
    # Continuous upward trend -> RSI should be high (> 70)
    prices = pd.Series([100 + i * 2 for i in range(25)])
    rsi = calc.calculate_rsi(prices, period=14)
    assert rsi is not None
    assert rsi > 70.0


def test_macd_calculation():
    calc = TechnicalIndicatorCalculator()
    prices = pd.Series([100 + np.sin(i / 5) * 10 for i in range(40)])
    macd_res = calc.calculate_macd(prices)
    assert macd_res["macd"] is not None
    assert macd_res["signal"] is not None
    assert macd_res["hist"] is not None


def test_bollinger_bands():
    calc = TechnicalIndicatorCalculator()
    prices = pd.Series([150 + np.random.normal(0, 2) for _ in range(30)])
    bb = calc.calculate_bollinger_bands(prices, period=20)
    assert bb["upper"] is not None
    assert bb["lower"] is not None
    assert bb["upper"] > bb["middle"] > bb["lower"]


def test_insufficient_data_safety():
    calc = TechnicalIndicatorCalculator()
    tiny_series = pd.Series([100.0, 101.0, 102.0])
    rsi = calc.calculate_rsi(tiny_series, period=14)
    assert rsi is None
    macd_res = calc.calculate_macd(tiny_series)
    assert macd_res["macd"] is None
