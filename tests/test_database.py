"""Tests for SQLite database persistence and relationships."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.db_models import Base, ArticleRecord, SentimentRecord


@pytest.fixture
def db_session():
    # In-memory SQLite for isolated tests
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_article_persistence_and_relationships(db_session):
    art = ArticleRecord(
        title="Microsoft Wins Cloud Deal",
        source="Reuters",
        url="https://reuters.com/msft-deal",
        published_at="2026-10-13T08:00:00Z",
        clean_text="Microsoft wins $3B cloud deal.",
        matched_symbols="MSFT"
    )
    db_session.add(art)
    db_session.commit()

    assert art.id is not None

    sent = SentimentRecord(
        article_id=art.id,
        symbol="MSFT",
        company_name="Microsoft Corporation",
        sentiment="positive",
        sentiment_score=0.75,
        event_category="Contracts & Partnerships",
        short_summary="Wins $3B deal",
        model_used="rule_based"
    )
    db_session.add(sent)
    db_session.commit()

    retrieved = db_session.query(ArticleRecord).filter_by(id=art.id).first()
    assert len(retrieved.analyses) == 1
    assert retrieved.analyses[0].symbol == "MSFT"
