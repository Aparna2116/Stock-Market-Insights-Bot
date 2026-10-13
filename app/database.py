"""Database connection, engine configuration, and session management."""
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings, BASE_DIR
from app.models.db_models import Base
from app.utils.logging_config import logger

# Ensure the data directory exists
db_path_str = settings.DATABASE_URL.replace("sqlite:///", "")
db_path = Path(db_path_str)
db_dir = db_path.parent
if not db_dir.exists():
    db_dir.mkdir(parents=True, exist_ok=True)

# SQLite specific connect args
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)


# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialises all database tables if they do not exist."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database successfully initialised at: {settings.DATABASE_URL}")
    except Exception as e:
        logger.error(f"Error initialising database: {e}", exc_info=True)
        raise e


def get_db():
    """FastAPI dependency for obtaining a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
