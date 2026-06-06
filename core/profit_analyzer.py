"""
core/profit_analyzer.py — 프로젝트별 수익 분석 엔진

투자 가스비 vs 예상 에어드랍 보상을 추적하여
"계속 할지 말지" 자동 판단 근거 제공.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROFIT_DATA_FILE = "data/profit_tracking.json"


class ProfitAnalyzer:
    def __init__(self, config=None):
        self.config = config
        self._data = self._load()

    def _load(self) -> dict:
        path = Path(PROFIT_DATA_FILE)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return {"projects": {}, "total_invested": 0.0, "total_estimated": 0.0}

    def _save(self):
        os.makedirs("data", exist_ok=True)
        Path(PROFIT_DATA_FILE).write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False)
        )

    def record_farming_cost(
        self,
        project_name: str,
        wallet_address: str,
        gas_cost_usd: float,
        tx_count: int = 0,
        success: bool = True,
    ):
        """파밍 실행 후 가스비 기록."""
        projects = self._data.setdefault("projects", {})
        proj = projects.setdefault(project_name, {
            "total_gas_usd": 0.0,
            "total_tx": 0,
            "total_success": 0,
            "total_failed": 0,
            "wallets": {},
            "first_farm": None,
            "last_farm": None,
        })

        proj["total_gas_usd"] += gas_cost_usd
        proj["total_tx"] += tx_count
        if success:
            proj["total_success"] += 1
        else:
            proj["total_failed"] += 1

        now = datetime.now().isoformat()
        if not proj["first_farm"]:
            proj["first_farm"] = now
        proj["last_farm"] = now

        # 지갑별 기록
        wallet_data = proj["wallets"].setdefault(wallet_address, {
            "gas_usd": 0.0, "tx_count": 0, "farms": 0
        })
        wallet_data["gas_usd"] += gas_cost_usd
        wallet_data["tx_count"] += tx_count
        wallet_data["farms"] += 1

        self._data["total_invested"] = sum(
            p["total_gas_usd"] for p in projects.values()
        )
        self._save()

        logger.info(
            f"[ProfitAnalyzer] {project_name} | "
            f"가스 ${gas_cost_usd:.2f} | TX {tx_count}개 | "
            f"누적 ${proj['total_gas_usd']:.2f}"
        )

    def set_estimated_value(self, project_name: str, estimated_usd: float):
        """프로젝트 예상 에어드랍 가치 설정 (주간 스캔 시 업데이트)."""
        proj = self._data.setdefault("projects", {}).setdefault(
            project_name, {}
        )
        proj["estimated_value_usd"] = estimated_usd
        self._data["total_estimated"] = sum(
            p.get("estimated_value_usd", 0)
            for p in self._data["projects"].values()
        )
        self._save()

    def get_project_roi(self, project_name: str) -> dict:
        """프로젝트별 ROI 분석."""
        proj = self._data.get("projects", {}).get(project_name, {})
        invested = proj.get("total_gas_usd", 0)
        estimated = proj.get("estimated_value_usd", 0)
        roi_pct = ((estimated - invested) / invested * 100) if invested > 0 else 0

        return {
            "name": project_name,
            "invested_usd": round(invested, 2),
            "estimated_usd": round(estimated, 2),
            "roi_pct": round(roi_pct, 1),
            "tx_count": proj.get("total_tx", 0),
            "success_rate": self._calc_success_rate(proj),
            "farms_total": proj.get("total_success", 0) + proj.get("total_failed", 0),
            "recommendation": self._get_recommendation(invested, estimated, roi_pct),
        }

    def _calc_success_rate(self, proj: dict) -> float:
        total = proj.get("total_success", 0) + proj.get("total_failed", 0)
        if total == 0:
            return 0.0
        return round(proj.get("total_success", 0) / total * 100, 1)

    def _get_recommendation(self, invested: float, estimated: float, roi: float) -> str:
        """투자 계속 여부 권장."""
        if invested == 0:
            return "⏳ 데이터 부족"
        if roi > 200:
            return "🟢 강력 추천 — 높은 ROI"
        if roi > 50:
            return "🟢 추천 — 양호한 ROI"
        if roi > 0:
            return "🟡 보류 — 낮은 ROI"
        if estimated > 0:
            return "🟠 주의 — 손실 가능"
        return "🔴 중단 권장 — 수익성 없음"

    def get_full_report(self) -> dict:
        """전체 프로젝트 수익 리포트."""
        project_reports = {}
        for name in self._data.get("projects", {}):
            project_reports[name] = self.get_project_roi(name)

        return {
            "projects": project_reports,
            "total_invested_usd": round(self._data.get("total_invested", 0), 2),
            "total_estimated_usd": round(self._data.get("total_estimated", 0), 2),
            "overall_roi": round(
                (self._data.get("total_estimated", 0) - self._data.get("total_invested", 0))
                / max(self._data.get("total_invested", 0), 0.01) * 100, 1
            ),
            "generated_at": datetime.now().isoformat(),
        }

    def get_summary_text(self) -> str:
        """텔레그램 전송용 요약 텍스트."""
        report = self.get_full_report()
        lines = [
            f"💰 <b>수익 분석 리포트</b>",
            f"{'─' * 25}",
            f"💸 총 투자: ${report['total_invested_usd']:.2f}",
            f"💎 예상 수익: ${report['total_estimated_usd']:.2f}",
            f"📊 ROI: {report['overall_roi']:.1f}%",
            f"{'─' * 25}",
        ]
        for name, pr in sorted(
            report["projects"].items(),
            key=lambda x: x[1]["roi_pct"],
            reverse=True,
        ):
            lines.append(
                f"\n📦 <b>{name}</b>\n"
                f"  💸 ${pr['invested_usd']:.2f} → 💎 ${pr['estimated_usd']:.2f}\n"
                f"  📊 ROI {pr['roi_pct']:.1f}% | 성공률 {pr['success_rate']:.0f}%\n"
                f"  {pr['recommendation']}"
            )
        return "\n".join(lines)