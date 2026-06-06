"""
web3/gas_optimizer.py — 가스비 최적화 (v2)

legacy/gas_optimizer.py 확장:
- EIP-1559 지원
- 저가스 시간대 예측 (새벽 2~6시 UTC)
- 체인별 가스 관리
- 가스비 알림 임계값
- web3.py 동기/비동기 호환 (asyncio.to_thread)
"""
import asyncio
import logging
import os
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from web3 import Web3

logger = logging.getLogger(__name__)

GAS_MAX_GWEI = float(os.getenv("GAS_MAX_GWEI", "30"))
LOW_GAS_THRESHOLD = 10.0
LOW_GAS_HOURS_UTC = (2, 6)  # 저가스 시간대 UTC 2~6시


class GasOptimizer:
    def __init__(self, config=None):
        self.config = config
        self._history: deque = deque(maxlen=100)

    async def get_current_gwei(self, w3) -> float:
        """현재 가스비 조회 (EIP-1559 지원)."""
        try:
            gas_price = await asyncio.to_thread(w3.eth.gas_price)
            gwei = float(Web3.from_wei(gas_price, "gwei"))
            self._history.append(gwei)
            return gwei
        except Exception as e:
            logger.error(f"[GasOptimizer] 가스비 조회 실패: {e}")
            return 0.0

    async def get_recommended_gas(self, w3) -> dict:
        """EIP-1559 권장 가스 파라미터."""
        try:
            latest = await asyncio.to_thread(w3.eth.get_block, "latest")
            base_fee = float(Web3.from_wei(
                latest.get("baseFeePerGas", 0), "gwei"
            ))
            priority_fee = 2.0  # 기본 팁
            max_fee = base_fee * 1.5 + priority_fee
            return {
                "base_fee_gwei": round(base_fee, 2),
                "priority_fee_gwei": priority_fee,
                "max_fee_gwei": round(max_fee, 2),
            }
        except Exception as e:
            logger.warning(f"[GasOptimizer] EIP-1559 실패, 레거시 가스 사용: {e}")
            return {"base_fee_gwei": 5, "priority_fee_gwei": 2, "max_fee_gwei": 10}

    async def is_gas_ok(self, w3) -> bool:
        gwei = await self.get_current_gwei(w3)
        return gwei <= GAS_MAX_GWEI

    def is_low_gas_time(self) -> bool:
        """현재가 저가스 시간대인지 확인 (UTC 2~6시)."""
        hour = datetime.now(timezone.utc).hour
        start, end = LOW_GAS_HOURS_UTC
        return start <= hour < end

    async def wait_for_low_gas(self, w3, timeout_sec: int = 3600) -> bool:
        """
        가스비가 임계값 이하로 떨어질 때까지 대기.
        Returns: True(성공) / False(타임아웃)
        """
        elapsed = 0
        interval = 60
        while elapsed < timeout_sec:
            gwei = await self.get_current_gwei(w3)
            if gwei <= GAS_MAX_GWEI:
                logger.info(f"[GasOptimizer] 가스비 OK: {gwei:.1f} Gwei")
                return True
            logger.info(
                f"[GasOptimizer] 가스비 높음 ({gwei:.1f} Gwei > {GAS_MAX_GWEI}) "
                f"— {interval}초 후 재확인"
            )
            await asyncio.sleep(interval)
            elapsed += interval
        return False

    def get_gas_stats(self) -> dict:
        if not self._history:
            return {"current": 0, "min": 0, "max": 0, "avg": 0}
        history = list(self._history)
        return {
            "current": round(history[-1], 2),
            "min": round(min(history), 2),
            "max": round(max(history), 2),
            "avg": round(sum(history) / len(history), 2),
            "is_low_time": self.is_low_gas_time(),
        }
