"""Tests for FastAPI backend routes."""
import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "app_name" in data


def test_get_companies():
    resp = client.get("/api/companies")
    assert resp.status_code == 200
    companies = resp.json()
    assert len(companies) >= 5
    symbols = [c["symbol"] for c in companies]
    assert "AAPL" in symbols
    assert "NVDA" in symbols


def test_get_market_data():
    resp = client.get("/api/market-data/AAPL?period=60d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert "snapshot" in data
    assert "indicators" in data
    assert len(data["candles"]) >= 10
