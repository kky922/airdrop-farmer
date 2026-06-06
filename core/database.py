"""
core/database.py — SQLAlchemy 비동기 ORM 데이터베이스

기존 legacy/db.py의 sqlite3 스키마를 SQLAlchemy 2.x async 방식으로 마이그레이션.
테이블: activities, balances, airdrops, gas_snapshots
"""
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Index
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import select, func


DB_PATH = os.getenv("DB_PATH", "data/airdrop_farmer.db")


class Base(DeclarativeBase):
    pass


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_index = Column(Integer, nullable=False)
    wallet_address = Column(String(42), nullable=False)
    chain = Column(String(50), nullable=False)
    activity_type = Column(String(50), nullable=False)
    tx_hash = Column(String(66))
    amount = Column(Float, default=0.0)
    gas_used = Column(Float, default=0.0)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_activities_wallet", "wallet_index"),
        Index("ix_activities_chain", "chain"),
    )


class Balance(Base):
    __tablename__ = "balances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_index = Column(Integer, nullable=False)
    wallet_address = Column(String(42), nullable=False)
    chain = Column(String(50), nullable=False)
    balance_eth = Column(Float, default=0.0)
    checked_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_balances_wallet", "wallet_index"),
    )


class Airdrop(Base):
    __tablename__ = "airdrops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chain = Column(String(50), nullable=False)
    project_name = Column(String(100), nullable=False)
    status = Column(String(30), default="active")
    announcement_url = Column(Text)
    snapshot_date = Column(DateTime)
    claim_date = Column(DateTime)
    estimated_value_usd = Column(Float, default=0.0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class GasSnapshot(Base):
    __tablename__ = "gas_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chain = Column(String(50), nullable=False)
    gas_gwei = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class Database:
    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path) or "data", exist_ok=True)
        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}", echo=False
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init(self):
        """테이블 생성."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def session(self) -> AsyncSession:
        return self._session_factory()

    async def log_activity(
        self,
        wallet_index: int,
        wallet_address: str,
        chain: str,
        activity_type: str,
        tx_hash: Optional[str] = None,
        amount: float = 0.0,
        gas_used: float = 0.0,
        status: str = "success",
    ):
        async with self.session() as s:
            s.add(Activity(
                wallet_index=wallet_index,
                wallet_address=wallet_address,
                chain=chain,
                activity_type=activity_type,
                tx_hash=tx_hash,
                amount=amount,
                gas_used=gas_used,
                status=status,
            ))
            await s.commit()

    async def update_balance(
        self,
        wallet_index: int,
        wallet_address: str,
        chain: str,
        balance_eth: float,
    ):
        async with self.session() as s:
            s.add(Balance(
                wallet_index=wallet_index,
                wallet_address=wallet_address,
                chain=chain,
                balance_eth=balance_eth,
            ))
            await s.commit()

    async def add_airdrop(
        self,
        chain: str,
        project_name: str,
        status: str = "active",
        announcement_url: str = "",
        estimated_value_usd: float = 0.0,
        notes: str = "",
    ):
        async with self.session() as s:
            s.add(Airdrop(
                chain=chain,
                project_name=project_name,
                status=status,
                announcement_url=announcement_url,
                estimated_value_usd=estimated_value_usd,
                notes=notes,
            ))
            await s.commit()

    async def log_gas_snapshot(self, chain: str, gas_gwei: float):
        async with self.session() as s:
            s.add(GasSnapshot(chain=chain, gas_gwei=gas_gwei))
            await s.commit()

    async def get_activities(
        self,
        wallet_address: Optional[str] = None,
        chain: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        async with self.session() as s:
            q = select(Activity)
            if wallet_address:
                q = q.where(Activity.wallet_address == wallet_address)
            if chain:
                q = q.where(Activity.chain == chain)
            q = q.order_by(Activity.created_at.desc()).limit(limit)
            result = await s.execute(q)
            return result.scalars().all()

    async def get_activity_summary(self) -> list:
        """체인/유형별 활동 집계."""
        async with self.session() as s:
            q = (
                select(
                    Activity.chain,
                    Activity.activity_type,
                    func.count(Activity.id).label("count"),
                    func.sum(Activity.gas_used).label("total_gas"),
                )
                .group_by(Activity.chain, Activity.activity_type)
                .order_by(Activity.chain)
            )
            result = await s.execute(q)
            return result.all()

    async def get_total_gas_spent(self) -> float:
        async with self.session() as s:
            result = await s.execute(
                select(func.sum(Activity.gas_used)).where(Activity.status == "success")
            )
            return result.scalar() or 0.0

    async def get_latest_balances(self) -> list:
        """지갑별 최신 잔액 (체인 전체 합산 포함)."""
        async with self.session() as s:
            subq = (
                select(
                    Balance.wallet_index,
                    Balance.chain,
                    func.max(Balance.checked_at).label("latest")
                )
                .group_by(Balance.wallet_index, Balance.chain)
                .subquery()
            )
            q = select(Balance).join(
                subq,
                (Balance.wallet_index == subq.c.wallet_index)
                & (Balance.chain == subq.c.chain)
                & (Balance.checked_at == subq.c.latest),
            )
            result = await s.execute(q)
            return result.scalars().all()
