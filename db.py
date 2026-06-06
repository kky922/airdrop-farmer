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
                project_name TEXT DEFAULT '',
                owner TEXT DEFAULT 'me',
                activity_type TEXT NOT NULL,
                tx_hash TEXT,
                amount REAL,
                gas_used REAL,
                status TEXT DEFAULT 'pending',
                error_msg TEXT DEFAULT '',
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
            CREATE INDEX IF NOT EXISTS idx_activities_owner ON activities(owner);
            CREATE INDEX IF NOT EXISTS idx_activities_project ON activities(project_name);
            CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(created_at);
            CREATE INDEX IF NOT EXISTS idx_balances_wallet ON balances(wallet_index);
            CREATE INDEX IF NOT EXISTS idx_airdrops_chain ON airdrops(chain);
        """)
        self.conn.commit()
        logger.info("DB 초기화 완료: %s", self.db_path)

    def log_activity(self, wallet_index: int, wallet_address: str, chain: str,
                     activity_type: str, tx_hash: str = "", amount: float = 0,
                     gas_used: float = 0, status: str = "success",
                     project_name: str = "", owner: str = "me",
                     error_msg: str = ""):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO activities (wallet_index, wallet_address, chain, project_name, owner,
                                   activity_type, tx_hash, amount, gas_used, status, error_msg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (wallet_index, wallet_address, chain, project_name, owner,
              activity_type, tx_hash, amount, gas_used, status, error_msg))
        self.conn.commit()

    def log_farming_result(self, project_name: str, wallet_address: str,
                           owner: str, chain: str, wallet_index: int,
                           result: dict):
        """파밍 결과를 한번에 기록 (성공/실패 모두)."""
        actions = result.get("actions", [])
        tx_hashes = result.get("tx_hashes", [])
        status = "success" if result.get("success") else "failed"
        error_msg = result.get("error", "")

        # 대표 TX 해시 (첫 번째 또는 빈 문자열)
        tx_hash = tx_hashes[0] if tx_hashes else ""

        # 총 가스 / 금액
        total_gas = sum(a.get("gas_used", 0) for a in actions if isinstance(a, dict))
        total_amount = sum(a.get("amount", 0) for a in actions if isinstance(a, dict))

        self.log_activity(
            wallet_index=wallet_index,
            wallet_address=wallet_address,
            chain=chain,
            project_name=project_name,
            owner=owner,
            activity_type="farming",
            tx_hash=tx_hash,
            amount=total_amount,
            gas_used=total_gas,
            status=status,
            error_msg=error_msg[:500] if error_msg else "",
        )

    def get_daily_summary(self, date_str: str = None) -> dict:
        """
        일일 파밍 요약 (Telegram 리포트용).
        date_str: 'YYYY-MM-DD' 형식 (기본값: 오늘)
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        cursor = self.conn.cursor()

        # 프로젝트×소유자별 성공/실패
        cursor.execute("""
            SELECT project_name, owner, status, COUNT(*) as cnt,
                   COALESCE(SUM(gas_used), 0) as total_gas
            FROM activities
            WHERE created_at >= ? AND created_at < ? || ' 23:59:59'
            GROUP BY project_name, owner, status
            ORDER BY project_name, owner
        """, (date_str, date_str))

        summary = {"date": date_str, "projects": {}, "total_success": 0, "total_failed": 0}
        for row in cursor.fetchall():
            proj = row["project_name"] or "unknown"
            owner = row["owner"] or "me"
            if proj not in summary["projects"]:
                summary["projects"][proj] = {}
            if owner not in summary["projects"][proj]:
                summary["projects"][proj][owner] = {"success": 0, "failed": 0, "gas": 0.0}
            entry = summary["projects"][proj][owner]
            if row["status"] == "success":
                entry["success"] = row["cnt"]
                summary["total_success"] += row["cnt"]
            else:
                entry["failed"] = row["cnt"]
                summary["total_failed"] += row["cnt"]
            entry["gas"] += row["total_gas"]

        return summary

    def get_owner_stats(self, owner: str = "me", days: int = 7) -> dict:
        """소유자(me/wife)별 N일간 통계."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DATE(created_at) as day, status, COUNT(*) as cnt,
                   COALESCE(SUM(gas_used), 0) as daily_gas
            FROM activities
            WHERE owner = ? AND created_at >= datetime('now', ? || ' days')
            GROUP BY day, status
            ORDER BY day DESC
        """, (owner, f"-{days}"))
        stats = {}
        for row in cursor.fetchall():
            day = row["day"]
            if day not in stats:
                stats[day] = {"success": 0, "failed": 0, "gas": 0.0}
            if row["status"] == "success":
                stats[day]["success"] = row["cnt"]
            else:
                stats[day]["failed"] = row["cnt"]
            stats[day]["gas"] += row["daily_gas"]
        return stats

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
