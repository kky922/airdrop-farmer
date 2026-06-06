"""
projects/base_project.py — 모든 파밍 프로젝트의 기본 클래스

v2: farm_single() 추가 — 지갑별 독립 실행 (시빌 방지)
"""
from abc import ABC, abstractmethod
import asyncio
import logging
import random

logger = logging.getLogger(__name__)


class BaseProject(ABC):
    name: str = "BaseProject"
    chain: str = "ethereum"
    category: str = "defi"
    priority: int = 5
    active: bool = True
    fdv_usd: int = 0
    urgency: str = "NORMAL"  # IMMEDIATE / FAST / NORMAL / SLOW
    gas_usd: float = 10.0

    def __init__(self, config=None):
        self.config = config
        # config.yaml → bot.dry_run 에서 읽기 (기본값 True = 안전)
        self.dry_run = True
        if config and hasattr(config, "get"):
            self.dry_run = config.get("bot", {}).get("dry_run", True)
        elif config and hasattr(config, "dry_run"):
            self.dry_run = config.dry_run

    @abstractmethod
    async def farm(self, wallet_mgr, proxy: dict, behavior) -> dict:
        """파밍 실행 (레거시) — 각 프로젝트에서 구현."""
        pass

    async def farm_single(self, wallet, proxy: dict, behavior) -> dict:
        """
        단일 지갑 파밍 — 시빌 방지 핵심 메서드.

        각 지갑이 독립 proxy로 실행됨.
        서브클래스에서 오버라이드하여 실제 액션 구현.

        Args:
            wallet: Wallet 데이터클래스 (address, private_key, owner)
            proxy: 지갑 전용 프록시 설정
            behavior: BehaviorSimulator 인스턴스

        Returns:
            {"success": bool, "actions": list, "tx_hashes": list}
        """
        logger.info(
            f"[{self.name}] farm_single | {wallet.owner} #{wallet.index} | "
            f"{wallet.address[:10]}... | proxy={'O' if proxy else 'X'}"
        )
        # 기본 구현: 레거시 farm()에 위임
        # 서브클래스에서 개별 지갑 실행으로 오버라이드 권장
        from web3_tools.wallet_manager import WalletManager
        wm = WalletManager(self.config)
        return await self.farm(wm, proxy, behavior)

    @abstractmethod
    async def check_eligibility(self, wallet_address: str) -> bool:
        """에어드랍 자격 확인."""
        pass

    @abstractmethod
    async def claim(self, wallet_mgr, wallet_index: int) -> dict:
        """에어드랍 클레임."""
        pass

    def get_farming_schedule(self) -> dict:
        """권장 파밍 주기."""
        schedules = {
            "IMMEDIATE": {"interval_hours": 8, "max_gap_days": 1},
            "FAST": {"interval_hours": 12, "max_gap_days": 2},
            "NORMAL": {"interval_hours": 24, "max_gap_days": 3},
            "SLOW": {"interval_hours": 48, "max_gap_days": 7},
        }
        return schedules.get(self.urgency, schedules["NORMAL"])

    async def get_status(self) -> dict:
        return {
            "name": self.name,
            "chain": self.chain,
            "active": self.active,
            "priority": self.priority,
            "fdv_usd": self.fdv_usd,
            "urgency": self.urgency,
            "gas_usd": self.gas_usd,
        }

    def log_action(self, wallet_address: str, action: str, result: dict):
        logger.info(
            f"[{self.name}] 지갑 {wallet_address[:8]}... | "
            f"액션: {action} | 결과: {result}"
        )
