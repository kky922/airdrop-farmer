"""
anti_sybil/fingerprint_manager.py — 브라우저 핑거프린트 독립 관리

ADD- INFORMATION2: 디바이스 핑거프린트 탐지 (화면 해상도, OS, 폰트) 회피.
지갑별 고정 핑거프린트 + 세션별 소폭 변형.
"""
import hashlib
import random
import logging

logger = logging.getLogger(__name__)

FONTS = [
    "Arial", "Helvetica", "Times New Roman", "Courier New",
    "Verdana", "Georgia", "Palatino", "Garamond", "Bookman",
]

WEBGL_VENDORS = ["Google Inc.", "Intel Inc.", "NVIDIA Corporation", "AMD"]
WEBGL_RENDERERS = [
    "ANGLE (Intel, Intel(R) UHD Graphics 620)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060)",
    "ANGLE (AMD, AMD Radeon RX 580)",
    "Mesa/X.org",
]


class FingerprintManager:
    def __init__(self):
        self._cache: dict[str, dict] = {}

    def get_fingerprint(self, wallet_address: str) -> dict:
        """지갑별 고정 핑거프린트 반환 (캐시됨)."""
        if wallet_address in self._cache:
            return self._cache[wallet_address]

        seed = int(hashlib.sha256(wallet_address.encode()).hexdigest()[:16], 16)
        rng = random.Random(seed)

        fp = {
            "screen_width": rng.choice([1920, 1366, 1440, 1536, 1280, 2560]),
            "screen_height": rng.choice([1080, 768, 900, 864, 720, 1440]),
            "color_depth": rng.choice([24, 30, 32]),
            "device_memory": rng.choice([4, 8, 16]),
            "hardware_concurrency": rng.choice([2, 4, 6, 8]),
            "timezone_offset": rng.choice([-540, -480, -420, 0, 60, 120]),
            "language": rng.choice(["ko-KR", "en-US", "ja-JP"]),
            "platform": rng.choice(["Win32", "MacIntel", "Linux x86_64"]),
            "webgl_vendor": rng.choice(WEBGL_VENDORS),
            "webgl_renderer": rng.choice(WEBGL_RENDERERS),
            "fonts": rng.sample(FONTS, rng.randint(4, 7)),
        }
        self._cache[wallet_address] = fp
        return fp

    def generate_canvas_noise_script(self, wallet_address: str) -> str:
        """캔버스 핑거프린트 노이즈 주입 스크립트."""
        seed = int(hashlib.md5(wallet_address.encode()).hexdigest()[:8], 16)
        noise = (seed % 10) / 1000.0
        return f"""
const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {{
    const canvas = document.createElement('canvas');
    canvas.width = this.width;
    canvas.height = this.height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(this, 0, 0);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < imageData.data.length; i += 4) {{
        imageData.data[i] = Math.min(255, imageData.data[i] + {seed % 3});
    }}
    ctx.putImageData(imageData, 0, 0);
    return origToDataURL.apply(canvas, arguments);
}};
"""

    def get_init_scripts(self, wallet_address: str) -> list[str]:
        """Playwright context.add_init_script()에 전달할 스크립트 목록."""
        fp = self.get_fingerprint(wallet_address)
        scripts = [
            f"Object.defineProperty(screen, 'width', {{get: () => {fp['screen_width']}}});",
            f"Object.defineProperty(screen, 'height', {{get: () => {fp['screen_height']}}});",
            f"Object.defineProperty(navigator, 'deviceMemory', {{get: () => {fp['device_memory']}}});",
            f"Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {fp['hardware_concurrency']}}});",
            f"Object.defineProperty(navigator, 'platform', {{get: () => '{fp['platform']}'}});",
            self.generate_canvas_noise_script(wallet_address),
        ]
        return scripts
