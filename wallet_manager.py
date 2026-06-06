# -*- coding: utf-8 -*-
"""
HD 지갑 생성/관리 모듈
- 니모닉에서 N개 지갑 파생
- 잔액 조회
- 자금 분배/회수
"""
import json
import os
import logging
from typing import Optional

from eth_account import Account
from web3 import Web3

import config

logger = logging.getLogger(__name__)

WALLETS_FILE = os.path.join(os.path.dirname(__file__), "data", "wallets.json")

# HD 지갑 파생을 위한 니모닉 활성화
Account.enable_unaudited_hdwallet_features()


class Wallet:
    """개별 지갑 정보"""
    def __init__(self, index: int, address: str, private_key: str):
        self.index = index
        self.address = address
        self.private_key = private_key

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "address": self.address,
            "private_key": self.private_key,
        }

    def __repr__(self):
        return f"Wallet(#{self.index}, {self.address[:10]}...)"


class WalletManager:
    """다중 지갑 관리자"""

    def __init__(self):
        self.wallets: list[Wallet] = []
        self.master_key: Optional[str] = None
        self.master_address: Optional[str] = None
        self._load_or_create()

    def _load_or_create(self):
        """저장된 지갑 로드 또는 새로 생성"""
        if os.path.exists(WALLETS_FILE):
            self._load_from_file()
        else:
            logger.info("저장된 지갑 없음. 새로 생성 필요합니다.")
            self.master_key = config.MASTER_PRIVATE_KEY
            self.master_address = config.MASTER_ADDRESS

    def _load_from_file(self):
        """wallets.json에서 지갑 로드"""
        try:
            with open(WALLETS_FILE, "r") as f:
                data = json.load(f)
            self.master_address = data.get("master_address", "")
            self.master_key = config.MASTER_PRIVATE_KEY  # 키는 .env에서
            for w_data in data.get("wallets", []):
                self.wallets.append(Wallet(
                    index=w_data["index"],
                    address=w_data["address"],
                    private_key=w_data["private_key"],
                ))
            logger.info("지갑 %d개 로드 완료 (마스터: %s)", len(self.wallets), self.master_address[:10])
        except Exception as e:
            logger.error("지갑 로드 실패: %s", e)

    def _save_to_file(self):
        """wallets.json에 저장"""
        os.makedirs(os.path.dirname(WALLETS_FILE), exist_ok=True)
        data = {
            "master_address": self.master_address,
            "wallets": [w.to_dict() for w in self.wallets],
        }
        tmp = WALLETS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, WALLETS_FILE)
        logger.info("지갑 %d개 저장 완료", len(self.wallets))

    def create_wallets(self, n: int = None, mnemonic: str = None) -> list[Wallet]:
        """HD 니모닉에서 N개 지갑 파생"""
        n = n or config.NUM_WALLETS
        mnemonic = mnemonic or config.HD_MNEMONIC

        if not mnemonic:
            raise ValueError("HD_MNEMONIC이 설정되지 않았습니다. .env를 확인하세요.")

        self.wallets = []
        for i in range(n):
            path = config.WALLET_DERIVATION_PATH.format(i)
            acct = Account.from_mnemonic(mnemonic, account_path=path)
            wallet = Wallet(index=i, address=acct.address, private_key=acct.key.hex())
            self.wallets.append(wallet)
            logger.info("지갑 #%d 생성: %s", i, acct.address)

        self._save_to_file()
        return self.wallets

    def fund_wallets(self, w3: Web3, amount_eth: float = None):
        """마스터 지갑에서 각 지갑으로 자금 분배"""
        if not self.master_key:
            raise ValueError("마스터 프라이빗키가 없습니다.")

        amount_eth = amount_eth or config.FUND_AMOUNT_PER_WALLET_ETH
        amount_wei = w3.to_wei(amount_eth, "ether")
        nonce = w3.eth.get_transaction_count(self.master_address)

        results = []
        for wallet in self.wallets:
            try:
                balance = w3.eth.get_balance(wallet.address)
                if balance > w3.to_wei(0.001, "ether"):
                    logger.info("지갑 #%d 이미 잔액 있음: %.4f ETH", wallet.index, w3.from_wei(balance, "ether"))
                    continue

                tx = {
                    "to": wallet.address,
                    "value": amount_wei,
                    "gas": 21000,
                    "gasPrice": w3.eth.gas_price,
                    "nonce": nonce,
                    "chainId": w3.eth.chain_id,
                }
                signed = w3.eth.account.sign_transaction(tx, self.master_key)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                nonce += 1
                logger.info("💰 지갑 #%d에 %.4f ETH 전송: %s", wallet.index, amount_eth, tx_hash.hex())
                results.append({"wallet": wallet.index, "tx_hash": tx_hash.hex(), "amount": amount_eth})
            except Exception as e:
                logger.error("지갑 #%d 자금 분배 실패: %s", wallet.index, e)
                results.append({"wallet": wallet.index, "error": str(e)})

        return results

    def consolidate_to_master(self, w3: Web3):
        """모든 지갑의 잔액을 마스터로 회수"""
        if not self.master_address:
            raise ValueError("마스터 주소가 없습니다.")

        results = []
        for wallet in self.wallets:
            try:
                balance = w3.eth.get_balance(wallet.address)
                gas_cost = 21000 * w3.eth.gas_price
                if balance <= gas_cost:
                    logger.info("지갑 #%d 잔액 부족 (가스비만)", wallet.index)
                    continue

                amount = balance - gas_cost
                tx = {
                    "to": self.master_address,
                    "value": amount,
                    "gas": 21000,
                    "gasPrice": w3.eth.gas_price,
                    "nonce": w3.eth.get_transaction_count(wallet.address),
                    "chainId": w3.eth.chain_id,
                }
                signed = w3.eth.account.sign_transaction(tx, wallet.private_key)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                logger.info("💸 지갑 #%d → 마스터 %.4f ETH: %s", wallet.index, w3.from_wei(amount, "ether"), tx_hash.hex())
                results.append({"wallet": wallet.index, "tx_hash": tx_hash.hex()})
            except Exception as e:
                logger.error("지갑 #%d 회수 실패: %s", wallet.index, e)
                results.append({"wallet": wallet.index, "error": str(e)})

        return results

    def get_all_balances(self, w3: Web3) -> list[dict]:
        """모든 지갑 잔액 조회"""
        balances = []
        for wallet in self.wallets:
            try:
                balance_wei = w3.eth.get_balance(wallet.address)
                balance_eth = float(w3.from_wei(balance_wei, "ether"))
                balances.append({
                    "index": wallet.index,
                    "address": wallet.address,
                    "balance_eth": balance_eth,
                })
            except Exception as e:
                balances.append({
                    "index": wallet.index,
                    "address": wallet.address,
                    "balance_eth": 0.0,
                    "error": str(e),
                })
        return balances

    def get_wallet(self, index: int) -> Optional[Wallet]:
        """인덱스로 지갑 조회"""
        for w in self.wallets:
            if w.index == index:
                return w
        return None

    @property
    def count(self) -> int:
        return len(self.wallets)