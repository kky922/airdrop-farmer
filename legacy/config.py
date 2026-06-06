# -*- coding: utf-8 -*-
"""
에어드롭 파밍 봇 v2 설정 모듈 — 10개 체인, 100% 자동화
"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ─── 마스터 지갑 ────────────────────────────────────────────────
MASTER_PRIVATE_KEY = os.getenv("MASTER_PRIVATE_KEY", "")
MASTER_ADDRESS = os.getenv("MASTER_ADDRESS", "")

# ─── HD 지갑 설정 ───────────────────────────────────────────────
HD_MNEMONIC = os.getenv("HD_MNEMONIC", os.getenv("MNEMONIC", ""))
NUM_WALLETS = int(os.getenv("NUM_WALLETS", "5"))
WALLET_DERIVATION_PATH = "m/44'/60'/0'/0/{}"  # {index}

# ─── 텔레그램 ────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ─── 가스 설정 ───────────────────────────────────────────────────
GAS_MAX_GWEI = float(os.getenv("GAS_MAX_GWEI", "30"))
GAS_CHECK_INTERVAL = 60
MAX_GAS_COST_USD = float(os.getenv("MAX_GAS_COST_USD", "0.05"))  # 트랜잭션당 최대 가스비

# ─── 활동 설정 ───────────────────────────────────────────────────
FUND_AMOUNT_PER_WALLET_ETH = float(os.getenv("FUND_AMOUNT_PER_WALLET_ETH", "0.005"))
SWAP_AMOUNT_MIN_ETH = float(os.getenv("SWAP_AMOUNT_MIN_ETH", "0.0005"))
SWAP_AMOUNT_MAX_ETH = float(os.getenv("SWAP_AMOUNT_MAX_ETH", "0.003"))
BRIDGE_AMOUNT_MIN_ETH = float(os.getenv("BRIDGE_AMOUNT_MIN_ETH", "0.002"))
BRIDGE_AMOUNT_MAX_ETH = float(os.getenv("BRIDGE_AMOUNT_MAX_ETH", "0.005"))
LP_AMOUNT_MIN_ETH = float(os.getenv("LP_AMOUNT_MIN_ETH", "0.001"))
LP_AMOUNT_MAX_ETH = float(os.getenv("LP_AMOUNT_MAX_ETH", "0.005"))
LEND_AMOUNT_MIN_ETH = float(os.getenv("LEND_AMOUNT_MIN_ETH", "0.001"))
LEND_AMOUNT_MAX_ETH = float(os.getenv("LEND_AMOUNT_MAX_ETH", "0.005"))
NFT_MAX_PRICE_ETH = float(os.getenv("NFT_MAX_PRICE_ETH", "0.0005"))  # 무료/저가 NFT만

# ─── 스케줄 ─────────────────────────────────────────────────────
ACTIVITY_INTERVAL_HOURS = int(os.getenv("ACTIVITY_INTERVAL_HOURS", "8"))
BALANCE_CHECK_INTERVAL_HOURS = int(os.getenv("BALANCE_CHECK_INTERVAL_HOURS", "6"))
DISCOVERY_INTERVAL_HOURS = int(os.getenv("DISCOVERY_INTERVAL_HOURS", "4"))
CHECKER_INTERVAL_HOURS = int(os.getenv("CHECKER_INTERVAL_HOURS", "12"))  # 자격 체크
REPORT_HOUR = int(os.getenv("REPORT_HOUR", "21"))  # KST

# ─── 시빌 방지 ───────────────────────────────────────────────────
DELAY_BETWEEN_WALLETS_MIN_SEC = int(os.getenv("DELAY_MIN_SEC", "300"))   # 5분
DELAY_BETWEEN_WALLETS_MAX_SEC = int(os.getenv("DELAY_MAX_SEC", "3600"))  # 60분
AMOUNT_VARIATION_PCT = float(os.getenv("AMOUNT_VARIATION_PCT", "30"))    # ±30%

# ─── DB ──────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "airdrop_farmer.db")

# ─── 로깅 ────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ═══════════════════════════════════════════════════════════════════
# 🌐 체인 설정 — JSON 기반, 코드 수정 없이 체인 추가 가능
# ═══════════════════════════════════════════════════════════════════

CHAIN_REGISTRY = {
    # ═══════════════════════════════════════════════════════════════════
    # 🎯 16개 EVM 체인 — RPC 연결 검증 완료
    # ═══════════════════════════════════════════════════════════════════

    # ─── Tier S: 에어드롭 가능성 높음 ────────────────────────────────
    "abstract": {
        "name": "Abstract",
        "rpc": os.getenv("RPC_ABSTRACT", "https://api.mainnet.abs.xyz"),
        "chain_id": 2741,
        "explorer": "https://abscan.org",
        "tier": "S",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {"USDC": "0x0", "WETH": "0x0"},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 3,
    },
    "unichain": {
        "name": "Unichain",
        "rpc": os.getenv("RPC_UNICHAIN", "https://mainnet.unichain.org"),
        "chain_id": 130,
        "explorer": "https://unichain.blockscout.com",
        "tier": "S",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {"UNI": "0x0", "USDC": "0x0", "WETH": "0x4200000000000000000000000000000000000006"},
        "dex_routers": {"uniswap_v3": "0x1F98431c8aD98523631AE4a59f267346ea31F984"},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 5,
    },
    "scroll": {
        "name": "Scroll",
        "rpc": os.getenv("RPC_SCROLL", "https://rpc.scroll.io"),
        "chain_id": 534352,
        "explorer": "https://scrollscan.com",
        "tier": "S",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {"USDC": "0x0", "WETH": "0x5300000000000000000000000000000000000004"},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },
    "berachain": {
        "name": "Berachain",
        "rpc": os.getenv("RPC_BERACHAIN", "https://rpc.berachain.com"),
        "chain_id": 80094,
        "explorer": "https://berascan.com",
        "tier": "S",
        "is_testnet": False,
        "currency": "BERA",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {"USDC": "0x0", "WETH": "0x0"},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 3,
    },
    "monad": {
        "name": "Monad",
        "rpc": os.getenv("RPC_MONAD", "https://testnet-rpc.monad.xyz"),
        "chain_id": 10143,
        "explorer": "https://testnet.monadexplorer.com",
        "tier": "S",
        "is_testnet": True,
        "currency": "MON",
        "bridge_enabled": False,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },

    # ─── Tier A: 메인넷 활성 ────────────────────────────────────────
    "linea": {
        "name": "Linea",
        "rpc": os.getenv("RPC_LINEA", "https://rpc.linea.build"),
        "chain_id": 59144,
        "explorer": "https://lineascan.build",
        "tier": "A",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {"USDC": "0x0", "WETH": "0x0"},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },
    "ink": {
        "name": "Ink",
        "rpc": os.getenv("RPC_INK", "https://rpc-gel.inkonchain.com"),
        "chain_id": 57073,
        "explorer": "https://explorer.inkonchain.com",
        "tier": "A",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },
    "story": {
        "name": "Story",
        "rpc": os.getenv("RPC_STORY", "https://mainnet.storyrpc.io"),
        "chain_id": 1514,
        "explorer": "https://storyscan.xyz",
        "tier": "A",
        "is_testnet": False,
        "currency": "IP",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 3,
    },
    "morph": {
        "name": "Morph",
        "rpc": os.getenv("RPC_MORPH", "https://rpc.morphl2.io"),
        "chain_id": 2818,
        "explorer": "https://explorer.morphl2.io",
        "tier": "A",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },
    "mode": {
        "name": "Mode",
        "rpc": os.getenv("RPC_MODE", "https://mainnet.mode.network"),
        "chain_id": 34443,
        "explorer": "https://explorer.mode.network",
        "tier": "A",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },
    "lisk": {
        "name": "Lisk",
        "rpc": os.getenv("RPC_LISK", "https://rpc.api.lisk.com"),
        "chain_id": 1135,
        "explorer": "https://blockscout.lisk.com",
        "tier": "A",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },
    "taiko": {
        "name": "Taiko",
        "rpc": os.getenv("RPC_TAIKO", "https://rpc.taiko.xyz"),
        "chain_id": 167000,
        "explorer": "https://taikoscan.io",
        "tier": "A",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 3,
    },
    "blast": {
        "name": "Blast",
        "rpc": os.getenv("RPC_BLAST", "https://rpc.blast.io"),
        "chain_id": 81457,
        "explorer": "https://blastscan.io",
        "tier": "A",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {"USDB": "0x4300000000000000000000000000000000000003", "WETH": "0x4300000000000000000000000000000000000004"},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },
    "zora": {
        "name": "Zora",
        "rpc": os.getenv("RPC_ZORA", "https://rpc.zora.energy"),
        "chain_id": 7777777,
        "explorer": "https://explorer.zora.energy",
        "tier": "A",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },
    "manta": {
        "name": "Manta Pacific",
        "rpc": os.getenv("RPC_MANTA", "https://pacific-rpc.manta.network/http"),
        "chain_id": 169,
        "explorer": "https://pacific-explorer.manta.network",
        "tier": "A",
        "is_testnet": False,
        "currency": "ETH",
        "bridge_enabled": True,
        "native_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "tokens": {},
        "dex_routers": {},
        "lending": {},
        "nft_marketplace": "0x0",
        "gas_estimate_gwei": 2,
    },
}

# ─── 활동 유형 정의 ──────────────────────────────────────────────
ACTIVITY_TYPES = ["bridge", "swap", "lend", "lp", "nft", "governance", "transfer"]

# ─── 자격 요건 기본값 (체인별 오버라이드 가능) ───────────────────
DEFAULT_ELIGIBILITY = {
    "min_transactions": 10,
    "min_unique_days": 5,
    "min_volume_eth": 0.01,
    "required_activities": ["swap", "lend"],  # 최소 이것은 해야 함
    "bonus_activities": ["bridge", "lp", "nft", "governance"],  # 보너스
}

# ─── 활동 사이클 (자동 순환) ─────────────────────────────────────
ACTIVITY_CYCLE = [
    # Day 1: 브릿지 + 스왑
    [{"type": "bridge", "weight": 3}, {"type": "swap", "weight": 2}],
    # Day 2-3: 스왑 + 렌딩
    [{"type": "swap", "weight": 2}, {"type": "lend", "weight": 2}],
    # Day 4-7: 렌딩 + LP
    [{"type": "lend", "weight": 1}, {"type": "lp", "weight": 2}],
    # Day 8-14: NFT + 거버넌스
    [{"type": "nft", "weight": 1}, {"type": "governance", "weight": 1}],
    # 유지: 주간 스왑
    [{"type": "swap", "weight": 1}, {"type": "transfer", "weight": 1}],
]

# ─── 이더리움 RPC (브릿지용) ─────────────────────────────────────
RPC_ETHEREUM = os.getenv("RPC_ETHEREUM", "https://eth.llamarpc.com")
RPC_ARBITRUM = os.getenv("RPC_ARBITRUM", "https://arb1.arbitrum.io/rpc")
RPC_OPTIMISM = os.getenv("RPC_OPTIMISM", "https://mainnet.optimism.io")


def get_active_chains(tier_min: str = "B") -> list[str]:
    """활성 체인 목록 반환 (tier 필터)"""
    tier_order = {"S": 0, "A": 1, "B": 2}
    min_level = tier_order.get(tier_min, 2)
    return [
        name for name, info in CHAIN_REGISTRY.items()
        if tier_order.get(info.get("tier", "B"), 2) <= min_level
    ]


def get_chain_config(chain_name: str) -> dict:
    """체인 설정 반환"""
    return CHAIN_REGISTRY.get(chain_name, {})


def is_testnet(chain_name: str) -> bool:
    """테스트넷 여부"""
    cfg = get_chain_config(chain_name)
    return cfg.get("is_testnet", False)