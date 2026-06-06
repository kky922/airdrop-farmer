"""
scanner/scorer.py — 프로젝트 종합 점수화

ADD 지시서 #2 스캐너 고도화:
FDV + VC 투자 + 커뮤니티 크기 + 가스비 효율 + 시빌 리스크 종합 점수.
ai_engine/project_analyzer.py와 연동.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 알려진 VC 투자자 목록 (점수 가산)
TOP_VCS = [
    "a16z", "paradigm", "polychain", "multicoin", "sequoia",
    "binance labs", "coinbase ventures", "pantera", "dragonfly",
    "framework ventures",
]


class ProjectScorer:
    def score(self, project: dict) -> float:
        """
        종합 가중 점수 (0~100).
        FDV(30) + VC(20) + 커뮤니티(20) + 가스효율(15) + 시빌리스크역(10) + 긴급도(5)
        """
        score = 0.0
        score += self._fdv_score(project.get("fdv_usd", 0))
        score += self._vc_score(project.get("investors", []))
        score += self._community_score(project.get("followers", 0), project.get("discord_members", 0))
        score += self._gas_score(project.get("gas_usd", 10))
        score += self._sybil_risk_score(project.get("sybil_risk", "MEDIUM"))
        score += self._urgency_score(project.get("urgency", "NORMAL"))
        return round(min(100, score), 1)

    def _fdv_score(self, fdv: float) -> float:
        """FDV 기반 점수 (0~30)."""
        if fdv >= 5_000_000_000:
            return 30
        elif fdv >= 2_000_000_000:
            return 25
        elif fdv >= 1_000_000_000:
            return 20
        elif fdv >= 500_000_000:
            return 15
        elif fdv >= 100_000_000:
            return 10
        return 5

    def _vc_score(self, investors: list) -> float:
        """VC 투자 점수 (0~20)."""
        if not investors:
            return 0
        matches = sum(1 for vc in TOP_VCS if any(vc in inv.lower() for inv in investors))
        return min(20, matches * 5)

    def _community_score(self, twitter_followers: int, discord_members: int) -> float:
        """커뮤니티 크기 점수 (0~20)."""
        score = 0.0
        total = twitter_followers + discord_members
        if total >= 1_000_000:
            score = 20
        elif total >= 500_000:
            score = 15
        elif total >= 100_000:
            score = 10
        elif total >= 10_000:
            score = 5
        return score

    def _gas_score(self, gas_usd: float) -> float:
        """가스비 효율 점수 (0~15). 무료가 최고."""
        if gas_usd == 0:
            return 15
        elif gas_usd <= 3:
            return 13
        elif gas_usd <= 8:
            return 10
        elif gas_usd <= 15:
            return 7
        elif gas_usd <= 30:
            return 4
        return 2

    def _sybil_risk_score(self, risk: str) -> float:
        """시빌 리스크 역점 (0~10). 낮을수록 좋음."""
        return {"LOW": 10, "MEDIUM": 6, "HIGH": 3, "CRITICAL": 0}.get(risk, 5)

    def _urgency_score(self, urgency: str) -> float:
        """긴급도 점수 (0~5)."""
        return {"IMMEDIATE": 5, "FAST": 4, "NORMAL": 3, "SLOW": 1}.get(urgency, 3)

    def rank(self, projects: list[dict]) -> list[dict]:
        """점수 내림차순 정렬 후 반환."""
        for p in projects:
            if "score" not in p:
                p["score"] = self.score(p)
        return sorted(projects, key=lambda x: x["score"], reverse=True)

    def top_n(self, projects: list[dict], n: int = 10) -> list[dict]:
        return self.rank(projects)[:n]
