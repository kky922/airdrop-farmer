# -*- coding: utf-8 -*-
"""
자격 검증 시스템 — 각 체인별 에어드롭 자격을 자동 체크하고 부족 활동 보완
"""
import logging
from datetime import datetime, timedelta

import config
from db import Database

logger = logging.getLogger(__name__)


class EligibilityChecker:
    """에어드롭 자격 검증기"""

    def __init__(self, db: Database):
        self.db = db

    def check_wallet_chain(self, wallet_address: str, chain_name: str) -> dict:
        """특정 지갑의 체인별 자격 체크"""
        chain_cfg = config.get_chain_config(chain_name)
        if not chain_cfg:
            return {"error": f"Unknown chain: {chain_name}"}

        # DB에서 활동 기록 조회
        activities = self.db.get_activities_by_wallet_chain(wallet_address, chain_name)

        # 통계 계산
        total_tx = len(activities)
        unique_days = len(set(
            a["timestamp"][:10] for a in activities if a.get("timestamp")
        ))
        total_volume = sum(
            float(a.get("amount", 0)) for a in activities
        )
        activity_types = set(a["activity_type"] for a in activities)

        # 자격 판정
        eligibility = config.DEFAULT_ELIGIBILITY.copy()
        score = 0
        max_score = 0
        missing = []

        # 필수 활동 체크
        for act in eligibility["required_activities"]:
            max_score += 30
            if act in activity_types:
                score += 30
            else:
                missing.append(act)

        # 보너스 활동 체크
        for act in eligibility["bonus_activities"]:
            max_score += 10
            if act in activity_types:
                score += 10
            else:
                missing.append(act)

        # 거래 수 체크
        min_tx = eligibility["min_transactions"]
        if total_tx >= min_tx:
            score += 10
        else:
            missing.append(f"more_tx ({total_tx}/{min_tx})")
        max_score += 10

        # 고유 날짜 체크
        min_days = eligibility["min_unique_days"]
        if unique_days >= min_days:
            score += 10
        else:
            missing.append(f"more_days ({unique_days}/{min_days})")
        max_score += 10

        pct = int((score / max_score) * 100) if max_score > 0 else 0

        return {
            "chain": chain_name,
            "wallet": wallet_address[:10] + "...",
            "score": pct,
            "total_tx": total_tx,
            "unique_days": unique_days,
            "total_volume": round(total_volume, 6),
            "activities_done": list(activity_types),
            "missing": missing,
            "eligible": pct >= 70,
            "tier": chain_cfg.get("tier", "?"),
        }

    def check_all(self, wallet_addresses: list[str]) -> list[dict]:
        """모든 지갑 × 모든 체인 자격 체크"""
        results = []
        for chain_name in config.get_active_chains():
            for addr in wallet_addresses:
                result = self.check_wallet_chain(addr, chain_name)
                results.append(result)
        return results

    def get_missing_activities(self, wallet_address: str, chain_name: str) -> list[str]:
        """부족한 활동 목록 반환"""
        result = self.check_wallet_chain(wallet_address, chain_name)
        return result.get("missing", [])

    def get_priority_chains(self, wallet_address: str) -> list[dict]:
        """자격이 낮은 체인을 우선순위로 정렬"""
        results = []
        for chain_name in config.get_active_chains():
            check = self.check_wallet_chain(wallet_address, chain_name)
            if check["score"] < 100:  # 완벽하지 않은 체인만
                results.append({
                    "chain": chain_name,
                    "score": check["score"],
                    "missing": check["missing"],
                    "tier": check["tier"],
                })
        # 점수 낮은 순 정렬
        results.sort(key=lambda x: x["score"])
        return results

    def generate_report(self, wallet_addresses: list[str]) -> str:
        """자격 리포트 생성 (텔레그램용)"""
        results = self.check_all(wallet_addresses)
        lines = ["📋 **에어드롭 자격 현황**\n"]

        # 체인별로 그룹화
        by_chain = {}
        for r in results:
            chain = r["chain"]
            if chain not in by_chain:
                by_chain[chain] = []
            by_chain[chain].append(r)

        tier_emoji = {"S": "🟢", "A": "🟡", "B": "🔵"}

        for chain_name, chain_results in by_chain.items():
            chain_cfg = config.get_chain_config(chain_name)
            tier = chain_cfg.get("tier", "?")
            emoji = tier_emoji.get(tier, "⚪")
            is_testnet = "🆓" if chain_cfg.get("is_testnet") else ""

            avg_score = sum(r["score"] for r in chain_results) / len(chain_results)
            lines.append(f"{emoji} **{chain_name}** {is_testnet} — 평균 {avg_score:.0f}%")

            for r in chain_results:
                status = "✅" if r["eligible"] else "⚠️"
                lines.append(
                    f"  {status} {r['wallet']}: {r['score']}% "
                    f"({r['total_tx']}tx, {r['unique_days']}일)"
                )
                if r["missing"]:
                    lines.append(f"    부족: {', '.join(r['missing'][:3])}")
            lines.append("")

        return "\n".join(lines)