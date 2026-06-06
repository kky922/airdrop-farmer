# -*- coding: utf-8 -*-
"""
SQLite DB 모듈 — 활동 로그, 잔액, 에어드롭 상태 저장
"""
import sqlite3
import os
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


class Database:
    """SQLite 데이터베이스 관리"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_index INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                chain TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                tx_hash TEXT,
                amount REAL,
                gas_used REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_index INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                chain TEXT NOT NULL,
                balance_eth REAL DEFAULT 0,
                checked_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS airdrops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain TEXT NOT NULL,
                project_name TEXT,
                status TEXT DEFAULT 'upcoming',
                announcement_url TEXT,
                snapshot_date TEXT,
                claim_date TEXT,
                estimated_value_usd REAL,
                notes TEXT,
                discovered_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS gas_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain TEXT NOT NULL,
                gas_gwei REAL,
                recorded_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_activities_wallet ON activities(wallet_index);
            CREATE INDEX IF NOT EXISTS idx_activities_chain ON activities(chain);
            CREATE INDEX IF NOT EXISTS idx_balances_wallet ON balances(wallet_index);
            CREATE INDEX IF NOT EXISTS idx_airdrops_chain ON airdrops(chain);
        """)
        self.conn.commit()
        logger.info("DB 초기화 완료: %s", self.db_path)

    def log_activity(self, wallet_index: int, wallet_address: str, chain: str,
                     activity_type: str, tx_hash: str = "", amount: float = 0,
                     gas_used: float = 0, status: str = "success"):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO activities (wallet_index, wallet_address, chain, activity_type, tx_hash, amount, gas_used, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (wallet_index, wallet_address, chain, activity_type, tx_hash, amount, gas_used, status))
        self.conn.commit()

    def update_balance(self, wallet_index: int, wallet_address: str, chain: str, balance_eth: float):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO balances (wallet_index, wallet_address, chain, balance_eth)
            VALUES (?, ?, ?, ?)
        """, (wallet_index, wallet_address, chain, balance_eth))
        self.conn.commit()

    def add_airdrop(self, chain: str, project_name: str, status: str = "upcoming",
                    announcement_url: str = "", snapshot_date: str = "",
                    claim_date: str = "", estimated_value_usd: float = 0, notes: str = ""):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO airdrops (chain, project_name, status, announcement_url, snapshot_date, claim_date, estimated_value_usd, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (chain, project_name, status, announcement_url, snapshot_date, claim_date, estimated_value_usd, notes))
        self.conn.commit()

    def get_activities(self, wallet_index: int = None, chain: str = None, limit: int = 50) -> list[dict]:
        query = "SELECT * FROM activities WHERE 1=1"
        params = []
        if wallet_index is not None:
            query += " AND wallet_index = ?"
            params.append(wallet_index)
        if chain:
            query += " AND chain = ?"
            params.append(chain)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_latest_balances(self) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT b.* FROM balances b
            INNER JOIN (
                SELECT wallet_index, chain, MAX(checked_at) as max_date
                FROM balances GROUP BY wallet_index, chain
            ) latest ON b.wallet_index = latest.wallet_index 
                     AND b.chain = latest.chain 
                     AND b.checked_at = latest.max_date
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_airdrops(self, status: str = None) -> list[dict]:
        query = "SELECT * FROM airdrops WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY discovered_at DESC"
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_activity_summary(self) -> dict:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as total, chain, activity_type FROM activities GROUP BY chain, activity_type")
        summary = {}
        for row in cursor.fetchall():
            chain = row["chain"]
            if chain not in summary:
                summary[chain] = {}
            summary[chain][row["activity_type"]] = row["total"]
        return summary

    def get_total_gas_spent(self, wallet_index: int = None) -> float:
        cursor = self.conn.cursor()
        if wallet_index is not None:
            cursor.execute("SELECT COALESCE(SUM(gas_used), 0) as total FROM activities WHERE wallet_index = ?", (wallet_index,))
        else:
            cursor.execute("SELECT COALESCE(SUM(gas_used), 0) as total FROM activities")
        return cursor.fetchone()["total"]

    def get_activities_by_wallet_chain(self, wallet_address: str, chain: str) -> list[dict]:
        """특정 지갑+체인의 활동 목록"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM activities WHERE wallet_address = ? AND chain = ? ORDER BY created_at DESC",
            (wallet_address, chain),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
