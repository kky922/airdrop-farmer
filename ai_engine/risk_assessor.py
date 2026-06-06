"""
ai_engine/risk_assessor.py — 온체인 패턴 기반 시빌 위험도 평가
"""
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

RISK_THRESHOLDS = {
    "LOW": 30,
    "MEDIUM": 60,
    "HIGH": 80,
    "CRITICAL": 100,
}


class RiskAssessor:
    def __init__(self):
        self._wallet_actions: dict[str, list] = {}

    def record_action(self, wallet_address: str, action: dict):
        """액션 기록 (action: {type, chain, amount, timestamp})."""
        self._wallet_actions.setdefault(wallet_address, []).append(action)

    def calculate_pattern_risk(self, wallet_address: str) -> float:
        """TX 패턴 분석 — 동일 액션 반복, 동일 금액 반복 등."""
        actions = self._wallet_actions.get(wallet_address, [])
        if len(actions) < 2:
            return 0.0

        score = 0.0
        # 동일 액션 타입 연속 반복
        types = [a.get("type") for a in actions[-10:]]
        type_counts = Counter(types)
        most_common_pct = max(type_counts.values()) / len(types)
        if most_common_pct > 0.8:
            score += 30  # 80% 이상 동일 액션

        # 금액 분산 부족
        amounts = [a.get("amount", 0) for a in actions[-10:] if a.get("amount")]
        if amounts:
            avg = sum(amounts) / len(amounts)
            variance = sum((x - avg) ** 2 for x in amounts) / len(amounts)
            if variance < 0.0001:
                score += 20  # 금액 거의 동일

        return min(score, 100.0)

    def calculate_timing_risk(self, wallet_address: str) -> float:
        """타이밍 패턴 분석 — 너무 규칙적인 간격."""
        actions = self._wallet_actions.get(wallet_address, [])
        if len(actions) < 3:
            return 0.0

        intervals = []
        for i in range(1, len(actions)):
            t1 = actions[i - 1].get("timestamp")
            t2 = actions[i].get("timestamp")
            if t1 and t2:
                if isinstance(t1, str):
                    t1 = datetime.fromisoformat(t1)
                if isinstance(t2, str):
                    t2 = datetime.fromisoformat(t2)
                intervals.append(abs((t2 - t1).total_seconds()))

        if not intervals:
            return 0.0

        avg = sum(intervals) / len(intervals)
        if avg == 0:
            return 0.0
        variance = sum((x - avg) ** 2 for x in intervals) / len(intervals)
        cv = (variance ** 0.5) / avg  # 변동계수

        # CV < 0.05 이면 너무 규칙적
        return max(0.0, min(60.0, (0.1 - cv) * 600)) if cv < 0.1 else 0.0

    def calculate_amount_risk(self, wallet_address: str) -> float:
        """금액 패턴 분석 — 모든 지갑이 동일 금액."""
        all_amounts = []
        for addr, actions in self._wallet_actions.items():
            for a in actions:
                if a.get("amount"):
                    all_amounts.append(round(a["amount"], 4))

        if len(all_amounts) < 5:
            return 0.0

        counter = Counter(all_amounts)
        most_common_count = counter.most_common(1)[0][1]
        duplicate_ratio = most_common_count / len(all_amounts)

        return min(40.0, duplicate_ratio * 80)

    def get_overall_risk(self, wallet_address: str) -> dict:
        """종합 위험도 반환."""
        pattern = self.calculate_pattern_risk(wallet_address)
        timing = self.calculate_timing_risk(wallet_address)
        amount = self.calculate_amount_risk(wallet_address)

        # 가중 평균 (패턴 40%, 타이밍 35%, 금액 25%)
        score = pattern * 0.4 + timing * 0.35 + amount * 0.25

        level = "LOW"
        for lvl, threshold in reversed(list(RISK_THRESHOLDS.items())):
            if score >= threshold * 0.8:
                level = lvl
                break

        return {
            "risk_level": level,
            "risk_score": round(score, 1),
            "breakdown": {
                "pattern_risk": round(pattern, 1),
                "timing_risk": round(timing, 1),
                "amount_risk": round(amount, 1),
            },
            "should_pause": score >= 80,
        }
