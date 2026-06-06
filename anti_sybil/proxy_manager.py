"""
anti_sybil/proxy_manager.py — 레지덴셜 프록시 로테이션 관리자

ADD- INFORMATION2 시빌 방지 가이드 핵심 원칙:
- 지갑별 고정 프록시 매핑 (같은 지갑 = 항상 같은 IP)
- 프록시 헬스체크
- 레지덴셜 프록시 권장 (4~10개 지갑 기준 $20~50/월)
"""
import asyncio
import logging
import random
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class ProxyManager:
    def __init__(self, config=None):
        self.config = config
        self._proxies: list[dict] = []
        self._wallet_proxy_map: dict[str, dict] = {}
        self._health_cache: dict[str, bool] = {}
        self._load_proxies()

    def _load_proxies(self):
        """config 또는 환경변수에서 프록시 로드."""
        if self.config and hasattr(self.config, "get_proxies"):
            self._proxies = self.config.get_proxies()
        if not self._proxies:
            logger.warning(
                "[ProxyManager] 프록시 없음 — ADD- INFORMATION2 참고: "
                "4~10개 지갑은 레지덴셜 프록시 $20~50/월 권장"
            )

    async def get_proxy_for_wallet(self, wallet_address: str) -> Optional[dict]:
        """
        지갑별 고정 프록시 반환.
        시빌 방지 핵심: 동일 지갑 = 항상 동일 IP.
        """
        if not self._proxies:
            return None
        if wallet_address not in self._wallet_proxy_map:
            proxy = await self._get_healthy_proxy()
            if proxy:
                self._wallet_proxy_map[wallet_address] = proxy
                logger.info(
                    f"[ProxyManager] 지갑 {wallet_address[:8]}... "
                    f"→ 프록시 {proxy['host']} 고정 매핑"
                )
            else:
                return None
        return self._wallet_proxy_map.get(wallet_address)

    async def get_next_proxy(self) -> Optional[dict]:
        return await self._get_healthy_proxy()

    async def _get_healthy_proxy(self) -> Optional[dict]:
        shuffled = self._proxies.copy()
        random.shuffle(shuffled)
        for proxy in shuffled:
            key = f"{proxy['host']}:{proxy['port']}"
            if self._health_cache.get(key) is False:
                continue
            if await self._health_check(proxy):
                return proxy
        logger.error("[ProxyManager] 사용 가능한 프록시 없음!")
        return None

    async def _health_check(self, proxy: dict) -> bool:
        key = f"{proxy['host']}:{proxy['port']}"
        try:
            proxy_url = (
                f"http://{proxy.get('username', '')}:{proxy.get('password', '')}"
                f"@{proxy['host']}:{proxy['port']}"
            )
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    "https://httpbin.org/ip",
                    proxy=proxy_url,
                ) as resp:
                    ok = resp.status == 200
                    self._health_cache[key] = ok
                    return ok
        except Exception:
            self._health_cache[key] = False
            return False

    def proxy_to_playwright(self, proxy: dict) -> dict:
        """Playwright 형식으로 변환."""
        return {
            "server": f"http://{proxy['host']}:{proxy['port']}",
            "username": proxy.get("username", ""),
            "password": proxy.get("password", ""),
        }

    async def pre_farming_check(self) -> dict:
        """
        파밍 전 전체 프록시 헬스체크.
        Returns: {"healthy": int, "unhealthy": int, "details": list}
        """
        result = {"healthy": 0, "unhealthy": 0, "details": []}

        if not self._proxies:
            logger.warning("[ProxyManager] 프록시 없음 — 헬스체크 스킵")
            return result

        for proxy in self._proxies:
            key = f"{proxy['host']}:{proxy['port']}"
            is_healthy = await self._health_check(proxy)
            if is_healthy:
                result["healthy"] += 1
                result["details"].append({"proxy": key, "status": "✅ 정상"})
            else:
                result["unhealthy"] += 1
                result["details"].append({"proxy": key, "status": "❌ 응답없음"})
                logger.warning(f"[ProxyManager] 프록시 불량: {key}")

        logger.info(
            f"[ProxyManager] 헬스체크: {result['healthy']}개 정상, "
            f"{result['unhealthy']}개 불량"
        )
        return result

    async def reset_sticky_mapping(self, wallet_address: str):
        """특정 지갑의 프록시 매핑 초기화 (프록시 불량 시)."""
        if wallet_address in self._wallet_proxy_map:
            old = self._wallet_proxy_map.pop(wallet_address)
            key = f"{old['host']}:{old['port']}"
            self._health_cache[key] = False  # 캐시도 무효화
            logger.info(
                f"[ProxyManager] 지갑 {wallet_address[:8]}... "
                f"프록시 리셋 ({key})"
            )

    def proxy_count(self) -> int:
        return len(self._proxies)
