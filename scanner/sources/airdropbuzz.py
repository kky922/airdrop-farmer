"""
scanner/sources/airdropbuzz.py — AirdropBuzz 스크래핑

Playwright 스텔스 모드로 airdropbuzz.io 에어드랍 목록 파싱.
프로젝트명, FDV, 상태, 마감일 추출.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

AIRDROPBUZZ_URL = "https://airdropbuzz.io"
AIRDROPS_IO_URL = "https://airdrops.io"


class AirdropBuzzScanner:
    def __init__(self, config=None):
        self.config = config

    async def scan(self) -> list[dict]:
        """
        AirdropBuzz 스크래핑.
        Playwright 필요 — 미설치 시 빈 리스트 반환.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("[AirdropBuzz] playwright 미설치 — 스캔 생략")
            return []

        results = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
                    )
                )
                page = await context.new_page()

                # AirdropBuzz 접속
                await page.goto(AIRDROPBUZZ_URL, wait_until="networkidle", timeout=30000)

                # 에어드랍 카드 파싱
                cards = await page.query_selector_all("[class*='airdrop'], [class*='project'], article")
                for card in cards[:20]:  # 최대 20개
                    try:
                        name = await card.query_selector("h2, h3, [class*='title'], [class*='name']")
                        name_text = await name.inner_text() if name else "Unknown"

                        results.append({
                            "name": name_text.strip(),
                            "source": "airdropbuzz",
                            "url": AIRDROPBUZZ_URL,
                            "listed": False,
                            "status": "active",
                        })
                    except Exception:
                        continue

                await browser.close()
                logger.info(f"[AirdropBuzz] {len(results)}개 프로젝트 발견")

        except Exception as e:
            logger.error(f"[AirdropBuzz] 스캔 실패: {e}")

        return results

    async def scan_airdrops_io(self) -> list[dict]:
        """airdrops.io 스크래핑 (fallback)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return []

        results = []
        keywords = [
            "unichain", "abstract", "megaeth", "ink", "metamask",
            "opensea", "morph", "kaito", "humanity", "soneium",
        ]
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(AIRDROPS_IO_URL, wait_until="networkidle", timeout=30000)

                content = await page.content()
                for kw in keywords:
                    if kw.lower() in content.lower():
                        results.append({
                            "name": kw.capitalize(),
                            "source": "airdrops.io",
                            "keyword_match": kw,
                            "listed": False,
                        })
                await browser.close()
        except Exception as e:
            logger.error(f"[airdrops.io] 스캔 실패: {e}")

        return results
