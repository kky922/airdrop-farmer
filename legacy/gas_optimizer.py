# -*- coding: utf-8 -*-
"""
가스 최적화 모듈
- 가스 가격 모니터링
- 저가스 시간대 감지
- EIP-1559 가스 추천
"""
import time
import logging
from typing import Optional
from web3 import Web3

import config

logger = logging.getLogger(__name__)


class GasOptimizer:
    """가스 최적화"""

    def __init__(self, w3: Web3):
        self.w3 = w3
        self.gas_history: list[float] = []
        self.max_history = 100

    def get_current_gwei(self) -> float:
        """현재 가스 가격 (Gwei)"""
        try:
            gas_price = self.w3.eth.gas_price
            gwei = float(Web3.from_wei(gas_price, "gwei"))
            self.gas_history.append(gwei)
            if len(self.gas_history) > self.max_history:
                self.gas_history.pop(0)
            return gwei
        except Exception as e:
            logger.error("가스 가격 조회 실패: %s", e)
            return 999.0

    def is_gas_ok(self) -> bool:
        """현재 가스가 기준 이하인지"""
        gwei = self.get_current_gwei()
        ok = gwei <= config.GAS_MAX_GWEI
        if not ok:
            logger.warning("⛽ 가스 높음: %.1f Gwei (기준: %.1f)", gwei, config.GAS_MAX_GWEI)
        return ok

    def wait_for_low_gas(self, max_wait_sec: int = 3600) -> bool:
        """가스가 낮아질 때까지 대기"""
        start = time.time()
        while time.time() - start < max_wait_sec:
            if self.is_gas_ok():
                return True
            gwei = self.get_current_gwei()
            logger.info("⏳ 가스 대기 중... %.1f Gwei (기준: %.1f)", gwei, config.GAS_MAX_GWEI)
            time.sleep(config.GAS_CHECK_INTERVAL)
        logger.warning("가스 대기 시간 초과 (%d초)", max_wait_sec)
        return False

    def get_recommended_gas(self) -> dict:
        """EIP-1559 가스 추천"""
        try:
            block = self.w3.eth.get_block("latest")
            base_fee = float(Web3.from_wei(block["baseFeePerGas"], "gwei"))
            priority_fee = 1.5  # 기본 우선수수료
            max_fee = base_fee * 2 + priority_fee
            return {
                "base_fee_gwei": round(base_fee, 2),
                "priority_fee_gwei": priority_fee,
                "max_fee_gwei": round(max_fee, 2),
                "estimated_total_gwei": round(base_fee + priority_fee, 2),
            }
        except Exception as e:
            gwei = self.get_current_gwei()
            return {
                "base_fee_gwei": gwei,
                "priority_fee_gwei": 1.5,
                "max_fee_gwei": gwei * 1.5,
                "estimated_total_gwei": gwei,
            }

    def get_gas_stats(self) -> dict:
        """가스 통계"""
        if not self.gas_history:
            return {"samples": 0}
        return {
            "samples": len(self.gas_history),
            "current": self.gas_history[-1],
            "min": min(self.gas_history),
            "max": max(self.gas_history),
            "avg": round(sum(self.gas_history) / len(self.gas_history), 2),
        }