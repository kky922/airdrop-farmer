# -*- coding: utf-8 -*-
"""Berachain 체인 모듈"""
import logging
from typing import Optional
from chains.base import BaseChain

logger = logging.getLogger(__name__)


class BerachainChain(BaseChain):
    chain_name = "berachain"
    chain_id = 80094
    native_token = "BERA"
    explorer_url = "https://berascan.com"
    is_testnet = False

    async def bridge(self, private_key: str, amount: float) -> Optional[str]:
        logger.info("[Berachain] 🌉 브릿지 %.4f BERA", amount)
        # Berachain은 자체 브릿지 사용
        return None

    async def swap(self, private_key: str, token_in: str, token_out: str, amount: float) -> Optional[str]:
        logger.info("[Berachain] 🔄 스왑 %s → %s | %.6f", token_in, token_out, amount)
        return None

    async def lend(self, private_key: str, token: str, amount: float) -> Optional[str]:
        logger.info("[Berachain] 🏦 예치 %s | %.6f", token, amount)
        return None

    def check_airdrop(self, address: str) -> dict:
        nonce = self.w3.eth.get_transaction_count(address)
        return {
            "chain": "berachain",
            "address": address,
            "tx_count": nonce,
            "likely_eligible": nonce > 5,
            "status": "berachain_testnet_rewards_active",
        }

    async def claim(self, private_key: str) -> Optional[str]:
        logger.info("[Berachain] 에어드롭 클레임 — 아직 배포 안됨")
        return None