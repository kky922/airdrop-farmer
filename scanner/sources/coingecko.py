"""
scanner/sources/coingecko.py — CoinGecko API 스캐너 (async)

미상장 + 에어드랍 예정 코인 필터링, FDV/투자자 정보 수집.
Rate limit: 검색 1.2초 간격.
"""
import asyncio
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
LAYER2_CATEGORY = "layer-2"
ZK_CATEGORY = "zero-knowledge-zk"

TARGET_CATEGORIES = [LAYER2_CATEGORY, ZK_CATEGORY, "ethereum-ecosystem"]

# ADD- INFORMATION 미상장 프로젝트 키워드
UNLISTED_KEYWORDS = [
    "unichain", "abstract", "megaeth", "ink", "morph", "metamask",
    "opensea", "polymarket", "meteora", "sahara", "kaito",
    "humanity", "soneium", "sophon", "rivalz", "nillion",
    "initia", "starknet", "fuel", "corn", "berachain",
]


class CoinGeckoScanner:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._coin_list: list = []

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def scan_layer2_projects(self) -> list[dict]:
        """Layer-2 카테고리 코인 조회 — FDV 기준 정렬."""
        projects = []
        try:
            session = await self._get_session()
            for category in TARGET_CATEGORIES[:2]:
                url = (
                    f"{COINGECKO_BASE}/coins/markets"
                    f"?vs_currency=usd&category={category}"
                    f"&order=market_cap_desc&per_page=50&sparkline=false"
                )
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for coin in data:
                            projects.append({
                                "name": coin["name"],
                                "symbol": coin["symbol"].upper(),
                                "source": "coingecko",
                                "fdv_usd": coin.get("fully_diluted_valuation") or coin.get("market_cap", 0),
                                "price": coin.get("current_price", 0),
                                "listed": True,  # CoinGecko에 있으면 상장됨
                                "url": f"https://coingecko.com/en/coins/{coin['id']}",
                            })
                await asyncio.sleep(1.2)  # Rate limit
        except Exception as e:
            logger.error(f"[CoinGecko] Layer-2 스캔 실패: {e}")
        return projects

    async def search_project(self, keyword: str) -> Optional[dict]:
        """키워드로 프로젝트 검색."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{COINGECKO_BASE}/search?query={keyword}"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                coins = data.get("coins", [])
                if coins:
                    coin = coins[0]
                    return {
                        "name": coin["name"],
                        "symbol": coin.get("symbol", "").upper(),
                        "source": "coingecko_search",
                        "coingecko_id": coin.get("id"),
                        "listed": True,
                    }
        except Exception as e:
            logger.warning(f"[CoinGecko] 검색 실패 ({keyword}): {e}")
        return None

    async def find_unlisted_projects(self) -> list[dict]:
        """
        ADD- INFORMATION 미상장 프로젝트 상장 여부 확인.
        상장 안 된 것들 = 아직 파밍 기회 존재.
        """
        unlisted = []
        for keyword in UNLISTED_KEYWORDS:
            result = await self.search_project(keyword)
            if not result:
                unlisted.append({
                    "name": keyword.capitalize(),
                    "symbol": keyword.upper(),
                    "source": "coingecko_not_found",
                    "listed": False,
                    "note": "CoinGecko 미상장 — 에어드랍 기회 존재",
                })
            await asyncio.sleep(1.2)
        return unlisted

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
