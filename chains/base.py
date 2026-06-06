# -*- coding: utf-8 -*-
"""
체인 베이스 클래스 v2 — 7가지 활동 메서드 지원
모든 체인 모듈은 이 클래스를 상속받아 구현합니다.
"""
import logging
import time
from web3 import Web3

import config

logger = logging.getLogger(__name__)


class BaseChain:
    """체인 기본 클래스 — config.CHAIN_REGISTRY 기반으로 자동 설정"""

    def __init__(self, chain_name: str = None):
        # 인자가 없으면 클래스 속성에서 가져옴 (서브클래스용)
        if chain_name is None:
            chain_name = getattr(self.__class__, 'chain_name', None)
        if not chain_name:
            raise ValueError("chain_name이 필요합니다")
        self.chain_name = chain_name
        self.cfg = config.get_chain_config(chain_name)
        if not self.cfg:
            raise ValueError(f"알 수 없는 체인: {chain_name}")

        self.rpc_url = self.cfg["rpc"]
        self.chain_id = self.cfg["chain_id"]
        self.explorer = self.cfg["explorer"]
        self.is_testnet = self.cfg.get("is_testnet", False)
        self.currency = self.cfg.get("currency", "ETH")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 30}))

        # 지원 기능 플래그
        self.has_bridge = self.cfg.get("bridge_enabled", False)
        self.has_dex = bool(self.cfg.get("dex_routers"))
        self.has_lending = bool(self.cfg.get("lending"))
        self.has_nft = self.cfg.get("nft_marketplace", "0x0") != "0x0"

    def is_connected(self) -> bool:
        """RPC 연결 확인 — is_connected()가 실패해도 block_number로 확인"""
        try:
            if self.w3.is_connected():
                return True
            # 일부 체인(Unichain 등)은 is_connected()가 False여도 작동함
            self.w3.eth.block_number
            return True
        except Exception:
            return False

    def get_balance(self, address: str) -> float:
        """네이티브 잔액 (ETH/BERA/MON 등)"""
        try:
            wei = self.w3.eth.get_balance(address)
            return float(Web3.from_wei(wei, "ether"))
        except Exception:
            return 0.0

    def get_gas_price(self) -> float:
        """현재 가스 가격 (Gwei)"""
        try:
            return float(self.w3.from_wei(self.w3.eth.gas_price, "gwei"))
        except Exception:
            return 999.0

    def _build_tx(self, from_address: str, to: str = None, value: int = 0,
                  data: bytes = b"", gas: int = 200000) -> dict:
        """기본 트랜잭션 빌드"""
        nonce = self.w3.eth.get_transaction_count(from_address)
        gas_price = self.w3.eth.gas_price

        tx = {
            "from": from_address,
            "nonce": nonce,
            "gas": gas,
            "gasPrice": gas_price,
            "chainId": self.chain_id,
            "value": value,
        }
        if to:
            tx["to"] = Web3.to_checksum_address(to)
        if data:
            tx["data"] = data
        return tx

    def _send_tx(self, private_key: str, tx: dict) -> str | None:
        """트랜잭션 서명 및 전송"""
        try:
            signed = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                logger.info("✅ [%s] TX 성공: %s", self.chain_name, tx_hash.hex())
                return tx_hash.hex()
            else:
                logger.error("❌ [%s] TX 실패: %s", self.chain_name, tx_hash.hex())
                return None
        except Exception as e:
            logger.error("❌ [%s] TX 에러: %s", self.chain_name, e)
            return None

    def _get_address(self, private_key: str) -> str:
        """개인키에서 주소 추출"""
        return self.w3.eth.account.from_key(private_key).address

    # ═══════════════════════════════════════════════════════════════
    # 🎯 7가지 핵심 활동 메서드 (각 체인에서 오버라이드)
    # ═══════════════════════════════════════════════════════════════

    async def bridge(self, private_key: str, amount: float) -> str | None:
        """🌉 브릿지 — L1→L2 또는 L2→L1"""
        if not self.has_bridge:
            logger.debug("[%s] 브릿지 미지원, 스킵", self.chain_name)
            return None

        address = self._get_address(private_key)
        value_wei = Web3.to_wei(amount, "ether")

        # 간단한 셀프 전송으로 브릿지 활동 기록 (실제 브릿지 컨트랙트 호출은 서브클래스에서)
        tx = self._build_tx(address, value=value_wei)
        return self._send_tx(private_key, tx)

    async def swap(self, private_key: str, token_in: str, token_out: str, amount: float) -> str | None:
        """🔄 DEX 스왑"""
        if not self.has_dex:
            logger.debug("[%s] DEX 미지원, 스킵", self.chain_name)
            return None

        address = self._get_address(private_key)
        value_wei = Web3.to_wei(amount, "ether")

        # 기본: 네이티브 토큰으로 small swap (실제 DEX 라우터 호출은 서브클래스에서)
        tx = self._build_tx(address, to=address, value=value_wei)
        return self._send_tx(private_key, tx)

    async def lend(self, private_key: str, token: str, amount: float) -> str | None:
        """🏦 렌딩/예치"""
        if not self.has_lending:
            logger.debug("[%s] 렌딩 미지원, 스킵", self.chain_name)
            return None

        address = self._get_address(private_key)
        value_wei = Web3.to_wei(amount, "ether")
        tx = self._build_tx(address, value=value_wei)
        return self._send_tx(private_key, tx)

    async def add_liquidity(self, private_key: str, token_a: str, token_b: str, amount: float) -> str | None:
        """📊 유동성 공급 (LP)"""
        if not self.has_dex:
            logger.debug("[%s] LP 미지원, 스킵", self.chain_name)
            return None

        address = self._get_address(private_key)
        value_wei = Web3.to_wei(amount, "ether")
        tx = self._build_tx(address, value=value_wei)
        return self._send_tx(private_key, tx)

    async def mint_nft(self, private_key: str, max_price: float = 0) -> str | None:
        """🖼️ NFT 민팅"""
        if not self.has_nft:
            logger.debug("[%s] NFT 미지원, 스킵", self.chain_name)
            return None

        address = self._get_address(private_key)
        value_wei = Web3.to_wei(max_price, "ether")
        tx = self._build_tx(address, value=value_wei)
        return self._send_tx(private_key, tx)

    async def vote_governance(self, private_key: str, proposal_id: int = 0) -> str | None:
        """🗳️ 거버넌스 투표"""
        address = self._get_address(private_key)
        # 거버넌스 컨트랙트가 없으면 간단한 온체인 활동으로 대체
        value_wei = Web3.to_wei(0, "ether")
        tx = self._build_tx(address, to=address, value=value_wei)
        return self._send_tx(private_key, tx)

    async def transfer(self, private_key: str, to_address: str, amount: float) -> str | None:
        """💸 송금"""
        address = self._get_address(private_key)
        value_wei = Web3.to_wei(amount, "ether")
        tx = self._build_tx(address, to=to_address, value=value_wei)
        return self._send_tx(private_key, tx)

    # ═══════════════════════════════════════════════════════════════
    # 🔍 유틸리티
    # ═══════════════════════════════════════════════════════════════

    def check_airdrop(self, address: str) -> dict:
        """에어드롭 확인 (기본 — 서브클래스에서 오버라이드)"""
        return {
            "chain": self.chain_name,
            "address": address,
            "has_airdrop": False,
            "amount": 0,
            "claim_url": "",
        }

    def get_tx_count(self, address: str) -> int:
        """트랜잭션 수"""
        try:
            return self.w3.eth.get_transaction_count(address)
        except Exception:
            return 0

    def supports_activity(self, activity_type: str) -> bool:
        """활동 유형 지원 여부"""
        mapping = {
            "bridge": self.has_bridge,
            "swap": self.has_dex,
            "lend": self.has_lending,
            "lp": self.has_dex,
            "nft": self.has_nft,
            "governance": True,  # 항상 가능 (셀프 TX로 대체)
            "transfer": True,    # 항상 가능
        }
        return mapping.get(activity_type, False)

    def get_supported_activities(self) -> list[str]:
        """지원하는 활동 목록"""
        return [a for a in config.ACTIVITY_TYPES if self.supports_activity(a)]