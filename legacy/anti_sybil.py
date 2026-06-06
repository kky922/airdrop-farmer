# -*- coding: utf-8 -*-
"""
시빌 공격 방지 모듈
- 지갑별 랜덤 딜레이
- 금액 변동
- 활동 패턴 다양화
"""
import random
import time
import logging
import hashlib
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)


class AntiSybilEngine:
    """시빌 방지 엔진"""

    def __init__(self):
        self.activity_history: dict[int, list[dict]] = {}  # wallet_index -> activities
        self._daily_patterns = {}  # wallet_index -> pattern

    def get_delay(self, wallet_index: int) -> int:
        """지갑별 랜덤 딜레이 (초)"""
        # 지갑 인덱스 기반 시드로 일관성 있지만 다른 딜레이
        base_seed = int(hashlib.md5(f"{wallet_index}".encode()).hexdigest(), 16) % 1000
        min_sec = config.DELAY_BETWEEN_WALLETS_MIN_SEC
        max_sec = config.DELAY_BETWEEN_WALLETS_MAX_SEC
        delay = random.randint(min_sec, max_sec) + base_seed % 300
        logger.debug("지갑 #%d 딜레이: %d초 (%.1f분)", wallet_index, delay, delay / 60)
        return delay

    def vary_amount(self, base_amount: float, wallet_index: int) -> float:
        """금액 변동 (±30%)"""
        variation = config.AMOUNT_VARIATION_PCT / 100.0
        # 지갑별로 다른 변동
        seed = int(hashlib.md5(f"{wallet_index}_{base_amount}".encode()).hexdigest(), 16) % 1000
        factor = 1.0 + (seed / 1000.0 * variation * 2 - variation)
        varied = base_amount * factor
        logger.debug("지갑 #%d 금액: %.6f → %.6f (x%.2f)", wallet_index, base_amount, varied, factor)
        return round(varied, 6)

    def get_random_time_window(self, wallet_index: int) -> tuple[datetime, datetime]:
        """지갑별 활동 시간대 (한국시간 08~24시 내 랜덤)"""
        today = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        start_offset = random.randint(0, 14 * 60)  # 0~14시간 범위
        duration = random.randint(30, 180)  # 30분~3시간
        start = today + timedelta(minutes=start_offset)
        end = start + timedelta(minutes=duration)
        return start, end

    def get_activity_pattern(self, wallet_index: int) -> list[str]:
        """지갑별 활동 패턴 생성 (순서 다양화)"""
        base_activities = ["bridge", "swap", "lend", "swap_back", "bridge_back"]
        # 지갑 인덱스로 시드 결정
        rng = random.Random(wallet_index * 42 + 7)
        pattern = base_activities.copy()
        rng.shuffle(pattern)
        # 일부 활동은 건너뛰기 (50% 확률)
        final = []
        for act in pattern:
            if rng.random() > 0.3:
                final.append(act)
        if not final:
            final = [rng.choice(base_activities)]
        return final

    def record_activity(self, wallet_index: int, activity: str, tx_hash: str = ""):
        """활동 기록"""
        if wallet_index not in self.activity_history:
            self.activity_history[wallet_index] = []
        self.activity_history[wallet_index].append({
            "activity": activity,
            "tx_hash": tx_hash,
            "timestamp": datetime.now().isoformat(),
        })

    def get_wallet_stats(self, wallet_index: int) -> dict:
        """지갑별 활동 통계"""
        history = self.activity_history.get(wallet_index, [])
        activity_types = {}
        for h in history:
            act = h["activity"]
            activity_types[act] = activity_types.get(act, 0) + 1
        return {
            "wallet_index": wallet_index,
            "total_activities": len(history),
            "activity_types": activity_types,
            "last_activity": history[-1]["timestamp"] if history else None,
        }

    def sleep_with_jitter(self, wallet_index: int):
        """지갑별 딜레이 적용"""
        delay = self.get_delay(wallet_index)
        logger.info("⏳ 지갑 #%d: %d초 (%.1f분) 대기...", wallet_index, delay, delay / 60)
        time.sleep(delay)