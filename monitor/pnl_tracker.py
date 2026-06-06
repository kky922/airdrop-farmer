"""
monitor/pnl_tracker.py — 수익 추적 (P&L Tracker)

가스비 지출 vs 예상 에어드랍 가치 추적.
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class PnLTracker:
    def __init__(self, db=None):
        self._db = db
        self._gas_spent: float = 0.0
        self._estimated_value: float = 0.0

    async def record_gas_spend(self, chain: str, gas_eth: float, eth_price_usd: float = 3000):
        """가스비 지출 기록."""
        gas_usd = gas_eth * eth_price_usd
        self._gas_spent += gas_usd
        logger.debug(f"[PnL] 가스비 지출: {chain} ${gas_usd:.3f}")

    def update_estimated_value(self, project_name: str, amount_tokens: float, token_price_usd: float):
        """예상 에어드랍 가치 업데이트."""
        value = amount_tokens * token_price_usd
        self._estimated_value += value
        logger.info(f"[PnL] 예상 가치 업데이트: {project_name} +${value:,.0f}")

    def get_summary(self) -> dict:
        """P&L 요약."""
        net = self._estimated_value - self._gas_spent
        roi = (net / self._gas_spent * 100) if self._gas_spent > 0 else 0
        return {
            "gas_spent_usd": round(self._gas_spent, 2),
            "estimated_value_usd": round(self._estimated_value, 2),
            "net_pnl_usd": round(net, 2),
            "roi_pct": round(roi, 1),
            "as_of": datetime.now().isoformat(),
        }

    def format_report(self) -> str:
        s = self.get_summary()
        emoji = "✅" if s["net_pnl_usd"] >= 0 else "❌"
        return (
            f"💰 <b>P&L 요약</b>\n"
            f"{'─' * 20}\n"
            f"⛽ 가스비 지출: ${s['gas_spent_usd']:,.2f}\n"
            f"🎁 예상 에어드랍: ${s['estimated_value_usd']:,.0f}\n"
            f"{emoji} 순수익: ${s['net_pnl_usd']:,.0f}\n"
            f"📈 ROI: {s['roi_pct']:.1f}%\n"
        )
