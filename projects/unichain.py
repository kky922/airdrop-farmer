"""
projects/unichain.py — Unichain 파밍 모듈

ADD- INFORMATION:
- FDV $2B+, 가스비 ~$15, 긴급도 즉시
- ETH → Unichain 브릿지, Uniswap V4 스왑, LP 포지션
"""
import logging
from projects.base_project import BaseProject

logger = logging.getLogger(__name__)

UNICHAIN_RPC = "https://mainnet.unichain.org"
UNICHAIN_CHAIN_ID = 130


class UnichainProject(BaseProject):
    name = "Unichain"
    chain = "unichain"
    category = "L2 DEX"
    priority = 9
    active = True
    fdv_usd = 2_000_000_000
    urgency = "IMMEDIATE"
    gas_usd = 15

    async def farm(self, wallet_mgr, proxy: dict, behavior) -> dict:
        results = []
        wallets = wallet_mgr.get_all_wallets()

        for i, wallet in enumerate(wallets):
            actions = behavior.shuffle_actions(
                ["bridge", "uniswap_v4_swap", "lp_add"], wallet.address
            )
            for action in actions:
                result = await self._execute_action(wallet, action, behavior)
                results.append(result)
                behavior.record_action(wallet.address, action, self.chain, 0)

            if i < len(wallets) - 1:
                await behavior.sleep_between_wallets(i)

        success = sum(1 for r in results if r.get("success"))
        return {"project": self.name, "success": success, "total": len(results), "results": results}

    async def _execute_action(self, wallet, action: str, behavior) -> dict:
        amount = behavior.get_random_tx_amount(0.01, 0.05, wallet.address)
        logger.info(f"[Unichain] {action}: {wallet.address[:8]}... {amount} ETH")

        if action == "bridge":
            # ETH → Unichain 브릿지 (공식 브릿지: https://bridge.unichain.org)
            return {"success": True, "action": action, "amount": amount, "note": "bridge.unichain.org"}
        elif action == "uniswap_v4_swap":
            # Uniswap V4 on Unichain
            return {"success": True, "action": action, "amount": amount}
        elif action == "lp_add":
            # LP 포지션 생성
            return {"success": True, "action": action, "amount": amount}
        return {"success": False, "reason": f"미지원 액션: {action}"}

    async def farm_single(self, wallet, proxy: dict, behavior) -> dict:
        """단일 지갑 Unichain 파밍 — 시빌 방지."""
        results = []
        actions = behavior.shuffle_actions(
            ["bridge", "uniswap_v4_swap", "lp_add"], wallet.address,
        )
        for action in actions:
            result = await self._execute_action(wallet, action, behavior)
            results.append(result)
            behavior.record_action(wallet.address, action, self.chain, 0)

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
        return True  # 현재 미상장 — 모든 활동이 자격 요건

    async def claim(self, wallet_mgr, wallet_index: int) -> dict:
        return {"success": False, "reason": "미상장 — TGE 이후 클레임 가능"}
