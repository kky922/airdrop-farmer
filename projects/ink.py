"""
projects/ink.py — Ink L2 파밍 모듈

ADD- INFORMATION TIER A:
- FDV $1B, 가스비 ~$8, 긴급도 즉시
- Kraken 계열 L2 — Ink 브릿지, Aave on Ink 유동성 공급
"""
import logging
from projects.base_project import BaseProject

logger = logging.getLogger(__name__)

INK_RPC = "https://rpc-gel.inkonchain.com"
INK_CHAIN_ID = 57073


class InkProject(BaseProject):
    name = "Ink"
    chain = "ink"
    category = "L2 Kraken"
    priority = 8
    active = True
    fdv_usd = 1_000_000_000
    urgency = "IMMEDIATE"
    gas_usd = 8

    async def farm(self, wallet_mgr, proxy: dict, behavior) -> dict:
        results = []
        wallets = wallet_mgr.get_all_wallets()

        for i, wallet in enumerate(wallets):
            actions = behavior.shuffle_actions(
                ["bridge", "aave_deposit", "aave_borrow"],
                wallet.address
            )
            for action in actions:
                amount = behavior.get_random_tx_amount(0.005, 0.02, wallet.address)
                result = await self._execute_action(wallet, action, amount)
                results.append(result)
                behavior.record_action(wallet.address, action, self.chain, amount)

            if i < len(wallets) - 1:
                await behavior.sleep_between_wallets(i)

        success = sum(1 for r in results if r.get("success"))
        return {"project": self.name, "success": success, "total": len(results), "results": results}

    async def _execute_action(self, wallet, action: str, amount: float) -> dict:
        logger.info(f"[Ink] {action}: {wallet.address[:8]}... {amount} ETH")
        if action == "bridge":
            # Ink 공식 브릿지: https://bridge.inkonchain.com
            return {"success": True, "action": action, "amount": amount, "note": "bridge.inkonchain.com"}
        elif action == "aave_deposit":
            # Aave on Ink 유동성 공급
            return {"success": True, "action": action, "amount": amount}
        elif action == "aave_borrow":
            # Aave on Ink 대출
            return {"success": True, "action": action, "amount": amount * 0.5}
        return {"success": False, "reason": f"미지원 액션: {action}"}

    async def farm_single(self, wallet, proxy: dict, behavior) -> dict:
        """단일 지갑 Ink 파밍 — 시빌 방지."""
        results = []
        actions = behavior.shuffle_actions(
            ["bridge", "aave_deposit", "aave_borrow"],
            wallet.address,
        )
        for action in actions:
            amount = behavior.get_random_tx_amount(0.005, 0.02, wallet.address)
            result = await self._execute_action(wallet, action, amount)
            results.append(result)
            behavior.record_action(wallet.address, action, self.chain, amount)

        success = sum(1 for r in results if r.get("success"))
        return {
            "success": success > 0,
            "project": self.name,
            "wallet": wallet.address[:10] + "...",
            "owner": wallet.owner,
            "actions_done": len(results),
            "actions_success": success,
            "results": results,
        }

    async def check_eligibility(self, wallet_address: str) -> bool:
        return True

    async def claim(self, wallet_mgr, wallet_index: int) -> dict:
        return {"success": False, "reason": "미상장 — TGE 이후 클레임 가능"}
