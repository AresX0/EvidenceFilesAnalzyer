"""Initialize the SQLite database for the case agent."""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from .models import Base
from ..config import DEFAULT_DB_PATH

logger = logging.getLogger("case_agent.db")

_engine = None
_Session = None


def init_db(db_path: str | Path = DEFAULT_DB_PATH):
    global _engine, _Session
    db_path = Path(db_path)
    db_url = f"sqlite:///{db_path}" if not str(db_path).startswith("sqlite:") else str(db_path)
    logger.info("Initializing DB at %s", db_path)
    _engine = create_engine(db_url, echo=False, future=True)
    Base.metadata.create_all(_engine)
    _Session = sessionmaker(bind=_engine)
    return _engine


def get_session():
    if _Session is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _Session()
