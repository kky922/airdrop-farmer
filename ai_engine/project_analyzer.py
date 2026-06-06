"""
ai_engine/project_analyzer.py — 프로젝트 점수화 및 순위 분석

ADD- INFORMATION (2026년 4월 기준) 최신 데이터 기반.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# 2026년 4월 최신 프로젝트 데이터 (ADD- INFORMATION 기준)
KNOWN_PROJECTS: list[dict] = [
    # TIER S — 초대형 기대 수익
    {
        "name": "MetaMask", "symbol": "MASK", "tier": "S",
        "fdv_usd": 10_000_000_000, "airdrop_pct": 10,
        "gas_usd": 30, "difficulty": 2, "urgency": "IMMEDIATE",
        "listed": False, "actions": ["swap_volume_5000usd", "portfolio", "staking", "bridge"],
        "chain": "ethereum", "sybil_risk": "LOW",
    },
    {
        "name": "OpenSea", "symbol": "OPEN", "tier": "S",
        "fdv_usd": 3_000_000_000, "airdrop_pct": 10,
        "gas_usd": 20, "difficulty": 1, "urgency": "FAST",
        "listed": False, "actions": ["nft_trade_500usd", "multi_chain", "create_collection"],
        "chain": "ethereum", "sybil_risk": "LOW",
    },
    # TIER A — 고수익 기대
    {
        "name": "MegaETH", "symbol": "MEGA", "tier": "A",
        "fdv_usd": 3_000_000_000, "airdrop_pct": 5,
        "gas_usd": 0, "difficulty": 1, "urgency": "IMMEDIATE",
        "listed": True, "tge_done": True,  # TGE 2025-11 완료, 배포 진행 중
        "actions": ["dapp_interact", "nft_mint", "dex_swap", "social_tasks"],
        "chain": "megaeth", "sybil_risk": "LOW",
    },
    {
        "name": "Unichain", "symbol": "UNI", "tier": "A",
        "fdv_usd": 2_000_000_000, "airdrop_pct": 10,
        "gas_usd": 15, "difficulty": 2, "urgency": "IMMEDIATE",
        "listed": False,
        "actions": ["bridge_eth", "uniswap_v4_swap", "lp_position"],
        "chain": "unichain", "sybil_risk": "MEDIUM",
    },
    {
        "name": "Abstract", "symbol": "ABS", "tier": "A",
        "fdv_usd": 3_000_000_000, "airdrop_pct": 10,
        "gas_usd": 10, "difficulty": 2, "urgency": "IMMEDIATE",
        "listed": False,
        "actions": ["xp_earn", "badge_collect", "game_interact", "social"],
        "chain": "abstract", "sybil_risk": "MEDIUM",
    },
    {
        "name": "Ink", "symbol": "INK", "tier": "A",
        "fdv_usd": 1_000_000_000, "airdrop_pct": 10,
        "gas_usd": 8, "difficulty": 2, "urgency": "IMMEDIATE",
        "listed": False,
        "actions": ["bridge", "aave_lend", "kraken_link"],
        "chain": "ink", "sybil_risk": "LOW",
    },
    {
        "name": "Morph", "symbol": "MORPH", "tier": "A",
        "fdv_usd": 200_000_000, "airdrop_pct": 15,
        "gas_usd": 5, "difficulty": 1, "urgency": "FAST",
        "listed": False,
        "actions": ["bridge", "swap", "lend"],
        "chain": "morph", "sybil_risk": "LOW",
    },
    {
        "name": "Polymarket", "symbol": "POLY", "tier": "A",
        "fdv_usd": 2_000_000_000, "airdrop_pct": 15,
        "gas_usd": 10, "difficulty": 2, "urgency": "FAST",
        "listed": False,
        "actions": ["predict", "trade_volume"],
        "chain": "polygon", "sybil_risk": "LOW",
    },
    {
        "name": "Meteora", "symbol": "MET", "tier": "A",
        "fdv_usd": 1_000_000_000, "airdrop_pct": 10,
        "gas_usd": 1, "difficulty": 2, "urgency": "IMMEDIATE",
        "listed": False,
        "actions": ["lp_provide", "swap"],
        "chain": "solana", "sybil_risk": "LOW",
    },
    # TIER B
    {
        "name": "Sahara AI", "symbol": "SAH", "tier": "B",
        "fdv_usd": 2_000_000_000, "airdrop_pct": 12,
        "gas_usd": 5, "difficulty": 2, "urgency": "FAST",
        "listed": False,
        "actions": ["testnet_tasks", "social"],
        "chain": "sahara", "sybil_risk": "MEDIUM",
    },
    {
        "name": "Kaito AI", "symbol": "KAITO", "tier": "B",
        "fdv_usd": 500_000_000, "airdrop_pct": 20,
        "gas_usd": 0, "difficulty": 1, "urgency": "IMMEDIATE",
        "listed": False,
        "actions": ["social_engage", "yap_score"],
        "chain": "none", "sybil_risk": "LOW",
    },
    {
        "name": "Humanity Protocol", "symbol": "HP", "tier": "B",
        "fdv_usd": 1_000_000_000, "airdrop_pct": 25,
        "gas_usd": 0, "difficulty": 1, "urgency": "IMMEDIATE",
        "listed": False,
        "actions": ["kyc_palm_scan", "testnet"],
        "chain": "none", "sybil_risk": "LOW",
    },
    {
        "name": "Soneium", "symbol": "SON", "tier": "B",
        "fdv_usd": 2_000_000_000, "airdrop_pct": 10,
        "gas_usd": 10, "difficulty": 2, "urgency": "FAST",
        "listed": False,
        "actions": ["bridge", "swap", "nft"],
        "chain": "soneium", "sybil_risk": "MEDIUM",
    },
    {
        "name": "Initia", "symbol": "INIT", "tier": "B",
        "fdv_usd": 1_500_000_000, "airdrop_pct": 10,
        "gas_usd": 5, "difficulty": 2, "urgency": "FAST",
        "listed": False,
        "actions": ["testnet", "stake", "bridge"],
        "chain": "initia", "sybil_risk": "MEDIUM",
    },
    {
        "name": "Fuel Network", "symbol": "FUEL", "tier": "B",
        "fdv_usd": 1_800_000_000, "airdrop_pct": 12,
        "gas_usd": 15, "difficulty": 3, "urgency": "NORMAL",
        "listed": False,
        "actions": ["testnet", "bridge", "swap"],
        "chain": "fuel", "sybil_risk": "HIGH",
    },
]


class ProjectAnalyzer:
    def __init__(self):
        self._cache: dict[str, float] = {}

    def score_project(self, data: dict) -> float:
        """
        프로젝트 0~100점 점수화.

        기준: FDV(30) + 에어드랍%(20) + 긴급도(20) + 가스효율(15) + 난이도 역점(10) + 미상장(5)
        """
        score = 0.0

        # FDV 점수 (0~30)
        fdv = data.get("fdv_usd", 0)
        if fdv >= 5_000_000_000:
            score += 30
        elif fdv >= 2_000_000_000:
            score += 25
        elif fdv >= 1_000_000_000:
            score += 20
        elif fdv >= 500_000_000:
            score += 15
        elif fdv >= 100_000_000:
            score += 10
        else:
            score += 5

        # 에어드랍 배정 % (0~20)
        airdrop_pct = data.get("airdrop_pct", 0)
        score += min(20, airdrop_pct * 1.5)

        # 긴급도 (0~20)
        urgency_map = {"IMMEDIATE": 20, "FAST": 15, "NORMAL": 10, "SLOW": 5}
        score += urgency_map.get(data.get("urgency", "NORMAL"), 10)

        # 가스비 효율 (0~15): 무료=15, $5=12, $10=9, $20=6, $30+=3
        gas = data.get("gas_usd", 10)
        if gas == 0:
            score += 15
        elif gas <= 5:
            score += 12
        elif gas <= 10:
            score += 9
        elif gas <= 20:
            score += 6
        else:
            score += 3

        # 난이도 역점 (쉬울수록 높은 점수, 0~10)
        difficulty = data.get("difficulty", 2)
        score += max(0, (4 - difficulty) * 3.3)

        # 미상장 보너스 (5)
        if not data.get("listed", False):
            score += 5

        return round(min(100, score), 1)

    def rank_projects(self, projects: list[dict] = None) -> list[dict]:
        """점수 내림차순 정렬."""
        targets = projects or KNOWN_PROJECTS
        scored = []
        for p in targets:
            s = self.score_project(p)
            scored.append({**p, "score": s})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def filter_by_grade(self, grade: str, projects: list[dict] = None) -> list[dict]:
        """등급별 필터 (S/A/B/IMMEDIATE)."""
        ranked = self.rank_projects(projects)
        if grade in ("S", "A", "B"):
            return [p for p in ranked if p.get("tier") == grade]
        elif grade == "IMMEDIATE":
            return [p for p in ranked if p.get("urgency") == "IMMEDIATE"]
        return ranked

    def get_top_projects(self, n: int = 5, exclude_listed: bool = True) -> list[dict]:
        """상위 N개 프로젝트."""
        ranked = self.rank_projects()
        if exclude_listed:
            ranked = [p for p in ranked if not p.get("listed", False)]
        return ranked[:n]

    def get_free_gas_projects(self) -> list[dict]:
        """무료 가스 프로젝트만."""
        return [p for p in self.rank_projects() if p.get("gas_usd", 1) == 0]
