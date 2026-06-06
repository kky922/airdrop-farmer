# -*- coding: utf-8 -*-
"""잔액 추적 — 모든 체인/지갑 잔액 모니터링"""
import logging
from datetime import datetime
from db import Database
from wallet_manager import WalletManager
from chains import get_chain
import config

logger = logging.getLogger(__name__)


class BalanceTracker:
    """멀티체인 잔액 추적기"""

    def __init__(self, wallet_mgr: WalletManager, db: Database):
        self.wallet_mgr = wallet_mgr
        self.db = db
        self._chain_instances = {}

    def _get_chain(self, chain_name: str):
        if chain_name not in self._chain_instances:
            try:
                self._chain_instances[chain_name] = get_chain(chain_name)
            except Exception as e:
                logger.error("체인 생성 실패 %s: %s", chain_name, e)
        return self._chain_instances.get(chain_name)

    def check_all_balances(self) -> dict:
        """모든 체인/지갑 잔액 조회"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "chains": {},
            "total_eth": 0.0,
        }

        for chain_name in config.get_active_chains():
            chain = self._get_chain(chain_name)
            if not chain or not chain.is_connected():
                continue

            chain_balances = []
            chain_total = 0.0

            for wallet in self.wallet_mgr.wallets:
                bal = chain.get_balance(wallet.address)
                chain_balances.append({
                    "wallet_index": wallet.index,
                    "address": wallet.address,
                    "balance": bal,
                })
                chain_total += bal

                # DB 저장
                self.db.update_balance(wallet.index, wallet.address, chain_name, bal)

            report["chains"][chain_name] = {
                "wallets": chain_balances,
                "total": chain_total,
            }
            report["total_eth"] += chain_total

        logger.info("💰 총 잔액: %.4f ETH", report["total_eth"])
        return report

    def get_low_balance_wallets(self, threshold: float = 0.002) -> list[dict]:
        """잔액이 낮은 지갑 감지"""
        low = []
        for chain_name in config.get_active_chains():
            chain = self._get_chain(chain_name)
            if not chain or not chain.is_connected():
                continue
            for wallet in self.wallet_mgr.wallets:
                bal = chain.get_balance(wallet.address)
                if bal < threshold:
                    low.append({
                        "chain": chain_name,
                        "wallet_index": wallet.index,
                        "address": wallet.address,
                        "balance": bal,
                    })
        return low

    def format_balance_report(self) -> str:
        """텔레그램용 잔액 리포트"""
        report = self.check_all_balances()
        lines = ["📊 **잔액 리포트**", f"⏰ {report['timestamp'][:19]}", ""]

        for chain_name, data in report["chains"].items():
            lines.append(f"**{chain_name.upper()}** (총: {data['total']:.4f} ETH)")
            for w in data["wallets"]:
                emoji = "✅" if w["balance"] > 0.002 else "⚠️"
                lines.append(f"  {emoji} #{w['wallet_index']}: {w['balance']:.6f} ETH")
            lines.append("")

        lines.append(f"💎 **총합: {report['total_eth']:.4f} ETH**")
        return "\n".join(lines)