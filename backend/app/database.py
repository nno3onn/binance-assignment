from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def build_engine() -> Engine:
    return create_engine(get_settings().database_url)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
