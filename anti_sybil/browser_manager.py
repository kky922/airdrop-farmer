"""
anti_sybil/browser_manager.py — Playwright 스텔스 브라우저

ADD- INFORMATION2 오프체인 탐지 회피:
- 브라우저 핑거프린트 랜덤화 (지갑별 고정)
- webdriver 속성 숨기기
- 지갑별 독립 프록시 연동
ADD 설계서 3-5 코드 기반.
"""
import random
import logging

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) "
    "Gecko/20100101 Firefox/123.0",
]

SCREEN_RESOLUTIONS = [
    (1920, 1080), (1366, 768), (1440, 900),
    (1536, 864), (1280, 720), (2560, 1440),
]

TIMEZONES = [
    "Asia/Seoul", "Asia/Tokyo", "America/New_York",
    "Europe/London", "America/Los_Angeles",
]

# 봇 탐지 우회 스크립트
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US', 'en'] });
"""


class BrowserManager:
    def __init__(self, config=None):
        self.config = config
        self.playwright = None
        self._browsers: dict = {}

    async def get_stealth_browser(
        self,
        wallet_address: str,
        proxy: dict = None,
    ) -> tuple:
        """
        스텔스 브라우저 인스턴스 반환.
        지갑별 고정 핑거프린트 — 일관성 유지 (ADD- INFORMATION2 핵심 원칙).
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "playwright 미설치. pip install playwright && playwright install chromium"
            )

        fingerprint = self._get_wallet_fingerprint(wallet_address)

        if not self.playwright:
            self.playwright = await async_playwright().start()

        proxy_config = None
        if proxy:
            server = f"http://{proxy['host']}:{proxy['port']}"
            proxy_config = {
                "server": server,
                "username": proxy.get("username", ""),
                "password": proxy.get("password", ""),
            }

        browser = await self.playwright.chromium.launch(
            headless=True,
            proxy=proxy_config,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                f"--window-size={fingerprint['width']},{fingerprint['height']}",
            ],
        )

        context = await browser.new_context(
            user_agent=fingerprint["user_agent"],
            viewport={"width": fingerprint["width"], "height": fingerprint["height"]},
            locale="ko-KR",
            timezone_id=fingerprint["timezone"],
            permissions=["notifications"],
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )

        await context.add_init_script(STEALTH_SCRIPT)

        page = await context.new_page()
        await page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
        })

        # 열린 브라우저 추적 → close_all()에서 정리 가능
        self._browsers[wallet_address] = browser

        logger.info(
            f"[Browser] 스텔스 브라우저 생성: "
            f"지갑 {wallet_address[:8]}... | "
            f"UA: {fingerprint['user_agent'][:50]}... | "
            f"총 {len(self._browsers)}개 활성"
        )

        return browser, context, page

    async def close_browser(self, wallet_address: str):
        """특정 지갑의 브라우저만 종료 (메모리 관리)."""
        browser = self._browsers.pop(wallet_address, None)
        if browser:
            try:
                await browser.close()
                logger.info(f"[Browser] 종료: {wallet_address[:8]}...")
            except Exception as e:
                logger.warning(f"[Browser] 종료 실패 {wallet_address[:8]}: {e}")

    def _get_wallet_fingerprint(self, wallet_address: str) -> dict:
        """지갑 주소 기반 고정 핑거프린트 — 항상 동일 지갑 = 동일 핑거프린트."""
        seed = int(wallet_address[-8:], 16) % (2 ** 32) if len(wallet_address) >= 8 else 0
        rng = random.Random(seed)
        resolution = rng.choice(SCREEN_RESOLUTIONS)
        return {
            "user_agent": rng.choice(USER_AGENTS),
            "width": resolution[0],
            "height": resolution[1],
            "timezone": rng.choice(TIMEZONES),
        }

    async def close_all(self):
        for browser in self._browsers.values():
            try:
                await browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
        self.playwright = None
        self._browsers.clear()
