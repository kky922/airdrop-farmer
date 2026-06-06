"""
anti_sybil/behavior_simulator.py — 인간 행동 시뮬레이션

ADD- INFORMATION2 시빌 탐지 회피:
- TX 타이밍 클러스터링 방지 → 지갑별 랜덤 딜레이
- 거래 금액 패턴 방지 → ±30% 변동
- 컨트랙트 상호작용 순서 다변화
기존 legacy/anti_sybil.py 기능 확장 버전.
"""
import asyncio
import hashlib
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)


class BehaviorSimulator:
    def __init__(self, config=None):
        self.config = config
        self._action_history: dict[str, list] = {}

    # ── 활동 프로필 (시간대별 확률 분포) ──
    PROFILES = {
        "morning":   {"peak_hours": (7, 11),  "weight": 0.3},
        "afternoon": {"peak_hours": (12, 17), "weight": 0.35},
        "evening":   {"peak_hours": (18, 22), "weight": 0.2},
        "night":     {"peak_hours": (23, 6),  "weight": 0.15},
    }

    def assign_profile(self, wallet_address: str) -> str:
        """지갑별 고정 활동 프로필 할당 (시빌 방지)."""
        seed = int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        profiles = list(self.PROFILES.keys())
        weights = [self.PROFILES[p]["weight"] for p in profiles]
        chosen = rng.choices(profiles, weights=weights, k=1)[0]
        return chosen

    def is_active_time(self, wallet_address: str) -> bool:
        """
        현재 시간이 해당 지갑의 프로필 활성 시간대인지 확인.
        비활성 시간대면 실행 보류 → 자연스러운 패턴.
        """
        profile_name = self.assign_profile(wallet_address)
        profile = self.PROFILES[profile_name]
        start, end = profile["peak_hours"]
        now_hour = datetime.now().hour

        if start <= end:
            in_range = start <= now_hour < end
        else:  # night: 23~6 (자정 넘어감)
            in_range = now_hour >= start or now_hour < end

        # 70% 확률로 활성 시간에만 실행, 30%는 예외 허용
        rng = random.Random(
            int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16)
            + datetime.now().day
        )
        return in_range or rng.random() < 0.3

    async def random_delay(
        self,
        wallet_address: str = "",
        min_sec: int = 300,
        max_sec: int = 1800,
    ):
        """
        지갑별 시드 기반 랜덤 딜레이.
        TX 타이밍 클러스터링 방지 핵심.
        """
        # 지갑 주소로 시드 추가 → 지갑마다 다른 타이밍
        seed = int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16) if wallet_address else 0
        rng = random.Random(seed + int(datetime.now().timestamp()) // 60)
        delay = rng.uniform(min_sec, max_sec)
        logger.info(
            f"[Behavior] {wallet_address[:8] if wallet_address else '?'}... "
            f"딜레이 {delay:.0f}초 ({delay/60:.1f}분)"
        )
        await asyncio.sleep(delay)

    async def simulate_reading(self, page=None, min_sec: float = 2.0, max_sec: float = 8.0):
        """페이지 읽기 시뮬레이션 (Playwright 사용 시)."""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
        if page:
            # 스크롤 시뮬레이션
            try:
                await page.evaluate(
                    f"window.scrollTo(0, {random.randint(100, 500)})"
                )
                await asyncio.sleep(random.uniform(0.5, 1.5))
            except Exception:
                pass

    def get_random_tx_amount(
        self,
        base_min: float,
        base_max: float,
        wallet_address: str = "",
    ) -> float:
        """
        거래 금액 랜덤화 — 금액 패턴 탐지 방지.
        ADD- INFORMATION2: 모든 지갑 동일 금액 = 즉시 탐지.
        """
        seed = int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16) if wallet_address else 0
        rng = random.Random(seed ^ int(datetime.now().timestamp()) // 3600)

        base = rng.uniform(base_min, base_max)
        # ±30% 변동 + 소수점 불규칙화
        variance = base * rng.uniform(-0.3, 0.3)
        amount = base + variance
        decimals = rng.randint(3, 6)
        return round(max(base_min * 0.5, amount), decimals)

    def shuffle_actions(self, actions: list, wallet_address: str = "") -> list:
        """
        액션 순서 랜덤화 — 동일 순서 반복 방지.
        ADD- INFORMATION2: 컨트랙트 상호작용 패턴 탐지 회피.
        """
        shuffled = actions.copy()
        seed = int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16) if wallet_address else 0
        rng = random.Random(seed + int(datetime.now().timestamp()) // 86400)
        rng.shuffle(shuffled)
        return shuffled

    def get_wallet_delay_hours(self, wallet_index: int) -> float:
        """
        지갑별 권장 딜레이 시간 (시간 단위).
        ADD- INFORMATION2 기준: 지갑 간 최소 2~6시간.
        """
        rng = random.Random(wallet_index * 42 + 7)
        return rng.uniform(2, 6)

    def record_action(self, wallet_address: str, action_type: str, chain: str, amount: float = 0):
        """액션 기록 (RiskAssessor 연동용)."""
        self._action_history.setdefault(wallet_address, []).append({
            "type": action_type,
            "chain": chain,
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_action_history(self, wallet_address: str) -> list:
        return self._action_history.get(wallet_address, [])

    async def sleep_between_wallets(self, wallet_index: int):
        """
        지갑 간 대기 — ADD- INFORMATION2 권장 2~6시간.
        실제 운영 시에는 이 딜레이를 반드시 지켜야 함.
        """
        hours = self.get_wallet_delay_hours(wallet_index)
        seconds = hours * 3600
        logger.info(f"[Behavior] 지갑 #{wallet_index} 다음 지갑까지 {hours:.1f}시간 대기")
        await asyncio.sleep(seconds)
