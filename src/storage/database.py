from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, DateTime, Float, Integer, String, create_engine, text
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import settings


class Base(DeclarativeBase):
    pass


class MinutePrice(Base):
    __tablename__ = "minute_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, unique=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)  # last traded price for the minute
    volume = Column(Float, nullable=False)
    symbol = Column(String(20), nullable=False, default="SILVER")

    def __repr__(self) -> str:
        return f"<MinutePrice {self.timestamp} close={self.close}>"


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sent_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    price = Column(Float, nullable=False)
    price_change = Column(Float, nullable=True)
    price_change_pct = Column(Float, nullable=True)
    message = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="sent")


class Database:
    def __init__(self, db_path: str = settings.DB_PATH) -> None:
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        self._Session = sessionmaker(bind=self.engine)
        self._init_db()

    def _init_db(self) -> None:
        Base.metadata.create_all(self.engine)
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()

    def session(self) -> Session:
        return self._Session()

    def upsert_minute_price(self, record: dict) -> None:
        with self.session() as session:
            existing = (
                session.query(MinutePrice)
                .filter_by(timestamp=record["timestamp"])
                .first()
            )
            if existing:
                for key, value in record.items():
                    setattr(existing, key, value)
            else:
                session.add(MinutePrice(**record))
            session.commit()

    def bulk_upsert(self, records: list[dict]) -> int:
        inserted = 0
        with self.session() as session:
            for rec in records:
                existing = (
                    session.query(MinutePrice)
                    .filter_by(timestamp=rec["timestamp"])
                    .first()
                )
                if not existing:
                    session.add(MinutePrice(**rec))
                    inserted += 1
            session.commit()
        return inserted

    def latest_price(self) -> Optional[MinutePrice]:
        with self.session() as session:
            return (
                session.query(MinutePrice)
                .order_by(MinutePrice.timestamp.desc())
                .first()
            )

    def price_n_minutes_ago(self, minutes: int) -> Optional[MinutePrice]:
        with self.session() as session:
            return (
                session.query(MinutePrice)
                .order_by(MinutePrice.timestamp.desc())
                .offset(minutes)
                .first()
            )

    def log_notification(self, record: dict) -> None:
        with self.session() as session:
            session.add(NotificationLog(**record))
            session.commit()

    def recent_prices(self, limit: int = 60) -> list[MinutePrice]:
        with self.session() as session:
            return (
                session.query(MinutePrice)
                .order_by(MinutePrice.timestamp.desc())
                .limit(limit)
                .all()
            )
