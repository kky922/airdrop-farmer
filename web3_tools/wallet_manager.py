"""
web3/wallet_manager.py — 멀티 지갑 관리자 (v2)

legacy/wallet_manager.py 기반 + check_all_claims() 추가.
ADD- INFORMATION2: HD Wallet이라도 각 지갑은 독립 IP 사용 필수.
보안: private_key Fernet(AES) 암호화 저장
"""
import asyncio
import base64
import hashlib
import json
import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from eth_account import Account
from eth_account.hdaccount import generate_mnemonic
from web3 import Web3

logger = logging.getLogger(__name__)

Account.enable_unaudited_hdwallet_features()

WALLETS_FILE = "data/wallets.json"
ENCRYPTION_KEY_FILE = "data/.wallet_key"


def _get_or_create_encryption_key() -> bytes:
    """암호화 키 로드 또는 생성 (Fernet 호환)."""
    key_path = Path(ENCRYPTION_KEY_FILE)
    if key_path.exists():
        return key_path.read_bytes().strip()

    # Fernet 키 생성: 32바이트 → base64url 인코딩
    raw_key = os.urandom(32)
    fernet_key = base64.urlsafe_b64encode(raw_key)
    key_path.write_bytes(fernet_key)
    key_path.chmod(0o600)  # 소유자만 읽기/쓰기
    logger.info("[WalletManager] 새 암호화 키 생성됨")
    return fernet_key


def _fernet_encrypt(data: str, key: bytes) -> str:
    """간이 Fernet 호환 AES 암호화 (XOR + HMAC)."""
    # 실제 Fernet이 없으면 간이 대체
    raw = data.encode("utf-8")
    key_bytes = base64.urlsafe_b64decode(key)
    # 키를 데이터 길이만큼 확장 (XOR)
    extended_key = (key_bytes * (len(raw) // len(key_bytes) + 1))[: len(raw)]
    encrypted = bytes(a ^ b for a, b in zip(raw, extended_key))
    # HMAC 태그
    tag = hashlib.sha256(key_bytes + encrypted).digest()[:16]
    return base64.urlsafe_b64encode(tag + encrypted).decode("ascii")


def _fernet_decrypt(token: str, key: bytes) -> str:
    """간이 Fernet 호환 복호화."""
    raw = base64.urlsafe_b64decode(token)
    tag, encrypted = raw[:16], raw[16:]
    key_bytes = base64.urlsafe_b64decode(key)
    # HMAC 검증
    expected_tag = hashlib.sha256(key_bytes + encrypted).digest()[:16]
    if tag != expected_tag:
        raise ValueError("복호화 실패: HMAC 불일치 (잘못된 키)")
    extended_key = (key_bytes * (len(encrypted) // len(key_bytes) + 1))[: len(encrypted)]
    decrypted = bytes(a ^ b for a, b in zip(encrypted, extended_key))
    return decrypted.decode("utf-8")


# cryptography 라이브러리 사용 가능하면 진짜 Fernet 사용
try:
    from cryptography.fernet import Fernet

    def _encrypt(data: str, key: bytes) -> str:
        return Fernet(key).encrypt(data.encode()).decode()

    def _decrypt(token: str, key: bytes) -> str:
        return Fernet(key).decrypt(token.encode()).decode()

    logger.debug("[WalletManager] cryptography.Fernet 사용 가능 — 강력한 암호화")
except ImportError:
    _encrypt = _fernet_encrypt
    _decrypt = _fernet_decrypt
    logger.warning(
        "[WalletManager] cryptography 미설치 — 간이 암호화 사용 중. "
        "`pip install cryptography` 권장"
    )


@dataclass
class Wallet:
    index: int
    address: str
    private_key: str  # 메모리에는 평문 유지
    owner: str = "me"

    def to_dict(self) -> dict:
        return asdict(self)


class WalletManager:
    def __init__(self, config=None):
        self.config = config
        self._wallets: list[Wallet] = []
        self._enc_key: bytes = _get_or_create_encryption_key()
        self._load()

    def _load(self):
        path = Path(WALLETS_FILE)
        if not path.exists():
            return
        try:
            with open(path) as f:
                data = json.load(f)
            wallets = []
            for w in data:
                pk = w["private_key"]
                # 암호화된 필드 감지 및 복호화
                if w.get("_encrypted"):
                    try:
                        pk = _decrypt(pk, self._enc_key)
                    except Exception as e:
                        logger.error(
                            f"[WalletManager] 지갑 {w['address'][:8]} 복호화 실패: {e}"
                        )
                        continue
                wallets.append(
                    Wallet(
                        index=w["index"],
                        address=w["address"],
                        private_key=pk,
                        owner=w.get("owner", "me"),
                    )
                )
            self._wallets = wallets
            logger.info(f"[WalletManager] {len(self._wallets)}개 지갑 로드 (암호화 저장)")
        except Exception as e:
            logger.error(f"[WalletManager] 지갑 로드 실패: {e}")

    def create_wallets(self, n: int = 5, mnemonic: str = "") -> list[Wallet]:
        """HD 니모닉으로 N개 지갑 파생."""
        if not mnemonic:
            mnemonic = os.getenv("WALLET_MNEMONIC", "") or os.getenv("MNEMONIC", "")
        if not mnemonic:
            mnemonic = generate_mnemonic(num_words=12, lang="english")
            logger.warning(f"[WalletManager] 새 니모닉 생성됨 — 반드시 백업: {mnemonic}")

        wallets = []
        for i in range(n):
            acct = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}")
            wallets.append(Wallet(index=i, address=acct.address, private_key=acct.key.hex()))

        self._wallets = wallets
        self._save()
        return wallets

    def add_wife_wallet(self, mnemonic: str) -> Wallet:
        """wife 니모닉으로 첫 번째 지갑 파생 후 저장 (레거시 호환)."""
        wallets = self.create_wife_wallets(1, mnemonic)
        return wallets[0]

    def create_wife_wallets(self, n: int = 5, mnemonic: str = "") -> list[Wallet]:
        """wife 니모닉으로 N개 파밍 지갑 파생 후 저장."""
        if not mnemonic:
            mnemonic = os.getenv("WIFE_WALLET_MNEMONIC", "").strip()
        if not mnemonic:
            raise ValueError("Wife mnemonic is required (WIFE_WALLET_MNEMONIC)")

        # 기존 와이프 지갑 제거
        self._wallets = [w for w in self._wallets if w.owner != "wife"]

        wife_wallets = []
        for i in range(n):
            acct = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}")
            wife_wallets.append(
                Wallet(
                    index=i,
                    address=acct.address,
                    private_key=acct.key.hex(),
                    owner="wife",
                )
            )

        self._wallets.extend(wife_wallets)
        self._save()
        logger.info(f"[WalletManager] 와이프 지갑 {n}개 생성 완료")
        return wife_wallets

    def _save(self):
        """암호화하여 저장."""
        os.makedirs("data", exist_ok=True)
        encrypted_list = []
        for w in self._wallets:
            d = w.to_dict()
            d["private_key"] = _encrypt(d["private_key"], self._enc_key)
            d["_encrypted"] = True
            encrypted_list.append(d)

        tmp = WALLETS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(encrypted_list, f, indent=2)
        os.replace(tmp, WALLETS_FILE)

    def get_wallet(self, index: int) -> Optional[Wallet]:
        for w in self._wallets:
            if w.index == index:
                return w
        return None

    def get_all_wallets(self) -> list[Wallet]:
        return self._wallets.copy()

    def get_wallets_by_owner(self, owner: str) -> list[Wallet]:
        return [w for w in self._wallets if w.owner == owner]

    def get_wife_wallet(self) -> Optional[Wallet]:
        wife_wallets = self.get_wallets_by_owner("wife")
        if wife_wallets:
            return wife_wallets[0]
        return None

    def wallet_count(self) -> int:
        return len(self._wallets)

    async def get_eth_balance(self, w3, wallet_address: str) -> float:
        """ETH 잔액 조회 (동기 web3 → asyncio.to_thread)."""
        try:
            balance_wei = await asyncio.to_thread(w3.eth.get_balance, wallet_address)
            return float(Web3.from_wei(balance_wei, "ether"))
        except Exception as e:
            logger.error(f"[WalletManager] 잔액 조회 실패 {wallet_address[:8]}: {e}")
            return 0.0

    async def check_all_claims(self) -> list[str]:
        """
        미클레임 에어드랍 체크 (ClaimManager 연동).
        Returns: 클레임 가능한 설명 문자열 목록.
        """
        try:
            from web3_tools.claim_manager import ClaimManager
            cm = ClaimManager()
            claims = []
            for wallet in self._wallets:
                wallet_claims = await cm.check_claimable(wallet.address)
                claims.extend(wallet_claims)
            return claims
        except ImportError:
            return []
        except Exception as e:
            logger.error(f"[WalletManager] 클레임 체크 실패: {e}")
            return []
