"""
web3/chain_configs.py — 체인별 설정

legacy/config.py의 CHAIN_REGISTRY + ADD- INFORMATION의 2026년 최신 프로젝트 체인 추가.
"""
import os

CHAIN_REGISTRY: dict[str, dict] = {
    # ─── TIER S (즉시 파밍) ──────────────────────────────────
    "megaeth": {
        "chain_id": 6342,
        "rpc": "https://rpc.megaeth.com",
        "explorer": "https://explorer.megaeth.com",
        "gas_usd": 0,
        "tier": "S",
        "project": "MegaETH",
        "actions": ["dapp_interact", "nft_mint", "dex_swap"],
    },
    "unichain": {
        "chain_id": 130,
        "rpc": os.getenv("UNICHAIN_RPC", "https://mainnet.unichain.org"),
        "explorer": "https://uniscan.xyz",
        "gas_usd": 15,
        "tier": "S",
        "project": "Unichain",
        "actions": ["bridge", "swap", "lp"],
        "contracts": {
            "uniswap_v4_router": "0x...",
        },
    },
    "abstract": {
        "chain_id": 2741,
        "rpc": os.getenv("ABSTRACT_RPC", "https://api.mainnet.abs.xyz"),
        "explorer": "https://explorer.abs.xyz",
        "gas_usd": 10,
        "tier": "S",
        "project": "Abstract",
        "actions": ["xp_earn", "badge_collect", "game_interact"],
    },
    "ink": {
        "chain_id": 57073,
        "rpc": os.getenv("INK_RPC", "https://rpc-gel.inkonchain.com"),
        "explorer": "https://explorer.inkonchain.com",
        "gas_usd": 8,
        "tier": "S",
        "project": "Ink",
        "actions": ["bridge", "aave_lend"],
        "contracts": {
            "aave_pool": "0x...",
        },
    },
    # ─── TIER A (빠른 파밍) ──────────────────────────────────
    "scroll": {
        "chain_id": 534352,
        "rpc": os.getenv("SCROLL_RPC_URL", "https://rpc.ankr.com/scroll"),
        "explorer": "https://scrollscan.com",
        "gas_usd": 5,
        "tier": "A",
        "project": "Scroll",
        "actions": ["bridge", "swap", "lend"],
    },
    "morph": {
        "chain_id": 2818,
        "rpc": os.getenv("MORPH_RPC", "https://rpc-quicknode-holesky.morphl2.io"),
        "explorer": "https://explorer.morphl2.io",
        "gas_usd": 5,
        "tier": "A",
        "project": "Morph",
        "actions": ["bridge", "swap", "lend"],
    },
    "soneium": {
        "chain_id": 1868,
        "rpc": os.getenv("SONEIUM_RPC", "https://rpc.soneium.org"),
        "explorer": "https://explorer.soneium.org",
        "gas_usd": 10,
        "tier": "A",
        "project": "Soneium",
        "actions": ["bridge", "swap", "nft"],
    },
    "berachain": {
        "chain_id": 80094,
        "rpc": os.getenv("BERACHAIN_RPC_URL", "https://rpc.ankr.com/berachain"),
        "explorer": "https://berascan.com",
        "gas_usd": 5,
        "tier": "A",
        "project": "Berachain",
        "actions": ["swap", "lend", "lp"],
    },
    "linea": {
        "chain_id": 59144,
        "rpc": os.getenv("LINEA_RPC", "https://rpc.linea.build"),
        "explorer": "https://lineascan.build",
        "gas_usd": 5,
        "tier": "A",
        "project": "Linea",
        "actions": ["bridge", "swap", "lend"],
    },
    "taiko": {
        "chain_id": 167000,
        "rpc": os.getenv("TAIKO_RPC", "https://rpc.taiko.xyz"),
        "explorer": "https://taikoscan.io",
        "gas_usd": 3,
        "tier": "A",
        "project": "Taiko",
        "actions": ["bridge", "swap"],
    },
    # ─── MAINNET (베이스) ────────────────────────────────────
    "ethereum": {
        "chain_id": 1,
        "rpc": os.getenv("ETHEREUM_RPC_URL", "https://rpc.ankr.com/eth"),
        "explorer": "https://etherscan.io",
        "gas_usd": 30,
        "tier": "mainnet",
        "actions": ["bridge", "swap", "nft"],
    },
    "base": {
        "chain_id": 8453,
        "rpc": os.getenv("BASE_RPC_URL", "https://rpc.ankr.com/base"),
        "explorer": "https://basescan.org",
        "gas_usd": 3,
        "tier": "mainnet",
        "actions": ["bridge", "swap", "lend"],
    },
    "polygon": {
        "chain_id": 137,
        "rpc": os.getenv("POLYGON_RPC", "https://rpc.ankr.com/polygon"),
        "explorer": "https://polygonscan.com",
        "gas_usd": 1,
        "tier": "mainnet",
        "actions": ["bridge", "swap", "predict"],
    },
}


def get_chain_config(chain_name: str) -> dict:
    return CHAIN_REGISTRY.get(chain_name.lower(), {})


def get_active_chains(tier_min: str = "A") -> list[str]:
    tier_order = {"S": 0, "A": 1, "B": 2, "mainnet": 3}
    min_val = tier_order.get(tier_min, 1)
    return [
        name for name, cfg in CHAIN_REGISTRY.items()
        if tier_order.get(cfg.get("tier", "B"), 2) <= min_val
    ]


def get_free_gas_chains() -> list[str]:
    return [n for n, c in CHAIN_REGISTRY.items() if c.get("gas_usd", 999) == 0]
