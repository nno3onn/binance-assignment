from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.repositories.interfaces import MarketDataRepository
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository


def get_repository(
    session: Annotated[Session, Depends(get_db_session)],
) -> Iterator[MarketDataRepository]:
    yield SqlAlchemyMarketDataRepository(session)
