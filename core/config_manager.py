"""
core/config_manager.py — 통합 설정 관리자

config.yaml + .env 파일을 통합 로드하고 점(.) 경로로 접근 가능하게 래핑.
"""
import os
import yaml
from dotenv import load_dotenv
from typing import Any


class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()
        self._data = self._load(config_path)

    def _load(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            return self._resolve_env(raw)
        except FileNotFoundError:
            return {}

    def _resolve_env(self, obj: Any) -> Any:
        """${VAR} 형식을 환경변수로 치환."""
        if isinstance(obj, str):
            if obj.startswith("${") and obj.endswith("}"):
                key = obj[2:-1]
                return os.getenv(key, "")
            return obj
        if isinstance(obj, dict):
            return {k: self._resolve_env(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._resolve_env(i) for i in obj]
        return obj

    def get(self, path: str, default: Any = None) -> Any:
        """점 구분 경로로 값 조회. 예: config.get('telegram.bot_token')"""
        keys = path.split(".")
        node = self._data
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k)
            if node is None:
                return default
        return node

    def get_proxies(self) -> list:
        """환경변수에서 PROXY_HOST_N / PROXY_USER_N / PROXY_PASS_N 로드."""
        proxies = []
        i = 1
        while True:
            host = os.getenv(f"PROXY_HOST_{i}")
            if not host:
                break
            proxies.append({
                "host": host,
                "port": int(os.getenv(f"PROXY_PORT_{i}", "10000")),
                "username": os.getenv(f"PROXY_USER_{i}", ""),
                "password": os.getenv(f"PROXY_PASS_{i}", ""),
            })
            i += 1
        return proxies
