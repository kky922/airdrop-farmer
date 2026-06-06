# -*- coding: utf-8 -*-
"""
chains/base_chain.py — Base (Coinbase L2) 체인 모듈

web3/chain_configs.py의 설정을 사용하여 Web3 인스턴스 생성.
legacy chains.base.BaseChain 의존성 제거 (v2 통합).
"""
import logging
from typing import Optional

from web3 import Web3
from web3_tools.chain_configs import get_chain_config

logger = logging.getLogger(__name__)


class BaseChainImpl:
    """Base (Coinbase L2) — web3/chain_configs.py 기반"""

    def __init__(self):
        config = get_chain_config("base")
        self.chain_name = "base"
        self.rpc = config.get("rpc", "https://rpc.ankr.com/base")
        self.chain_id = config.get("chain_id", 8453)
        self.w3 = Web3(Web3.HTTPProvider(self.rpc))

    async def bridge(self, private_key: str, amount: float) -> Optional[str]:
        logger.info("[Base] 🌉 브릿지 %.4f ETH (dry-run)", amount)
        return None

    async def swap(self, private_key: str, token_in: str, token_out: str, amount: float) -> Optional[str]:
        logger.info("[Base] 🔄 스왑 %s → %s | %.6f (dry-run)", token_in, token_out, amount)
        return None

    async def lend(self, private_key: str, token: str, amount: float) -> Optional[str]:
        logger.info("[Base] 🏦 예치 %s | %.6f (dry-run)", token, amount)
        return None

    def check_airdrop(self, address: str) -> dict:
        try:
            nonce = self.w3.eth.get_transaction_count(address)
        except Exception as e:
            logger.warning(f"[Base] TX 카운트 조회 실패: {e}")
            nonce = 0
        return {
            "chain": "base",
            "address": address,
            "tx_count": nonce,
            "likely_eligible": nonce > 10,
            "status": "check_basescan",
        }

    async def claim(self, private_key: str) -> Optional[str]:
        logger.info("[Base] 에어드롭 클레임 — 아직 배포 안됨")
        return None
