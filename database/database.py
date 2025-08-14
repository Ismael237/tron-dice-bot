"""
Database configuration and session management 
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import config
from utils.logger import get_logger

# Initialize logger
logger = get_logger("database")

# Create engine and session factory (simple configuration)
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    echo=(config.LOG_LEVEL == "DEBUG"),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """Initialize the database and create all tables"""
    try:
        # Import models to ensure they are registered
        from database.models import Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions (no auto-commit)
    Caller is responsible for commit/rollback.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()