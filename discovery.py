# -*- coding: utf-8 -*-
"""
에어드롭 탐지기 — 새로운 에어드롭 기회를 자동 탐지
- Twitter/X API 모니터링
- 웹 크롤링 (에어드롭 aggregator)
- 체인 활동 분석
"""
import logging
import json
import os
import re
import time
from datetime import datetime

import requests

import config
from db import Database

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class AirdropDiscovery:
    """에어드롭 탐지기"""

    # 에어드롭 정보 소스
    SOURCES = {
        "airdrops_io": "https://airdrops.io/api/airdrops",
        "coinmarketcap": "https://coinmarketcap.com/airdrops/",
        "defillama": "https://defillama.com/airdrops",
    }

    # 키워드 필터
    TARGET_KEYWORDS = [
        "scroll", "berachain", "monad", "abstract", "base",
        "layer2", "l2", "zk", "rollup", "modular",
        "airdrop", "token", "claim", "snapshot", "retroactive",
        "testnet", "mainnet", "incentivized",
    ]

    def __init__(self, db: Database):
        self.db = db
        self.discovered_file = os.path.join(DATA_DIR, "discovered_airdrops.json")
        self.discovered: list[dict] = []
        self._load_discovered()

    def _load_discovered(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(self.discovered_file):
            try:
                with open(self.discovered_file, "r") as f:
                    self.discovered = json.load(f)
                logger.info("탐지된 에어드롭 %d개 로드", len(self.discovered))
            except Exception:
                self.discovered = []

    def _save_discovered(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = self.discovered_file + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.discovered, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.discovered_file)

    def scan_twitter(self, query: str = "airdrop crypto") -> list[dict]:
        """Twitter/X에서 에어드롭 키워드 검색 (API 필요)"""
        # Twitter API v2 사용 (Bearer Token 필요)
        # 실제 구현은 API 키 설정 후 활성화
        logger.info("🐦 Twitter 스캔: '%s'", query)
        return []

    def scan_airdrops_io(self) -> list[dict]:
        """airdrops.io 크롤링"""
        airdrops = []
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            resp = requests.get("https://airdrops.io/", headers=headers, timeout=10)
            if resp.status_code == 200:
                # 간소화된 파싱 (실제로는 BeautifulSoup 사용 권장)
                for keyword in self.TARGET_KEYWORDS:
                    if keyword.lower() in resp.text.lower():
                        airdrops.append({
                            "source": "airdrops.io",
                            "keyword": keyword,
                            "found_at": datetime.now().isoformat(),
                        })
            logger.info("airdrops.io 스캔: %d개 발견", len(airdrops))
        except Exception as e:
            logger.error("airdrops.io 스캔 실패: %s", e)
        return airdrops

    def scan_chain_activity(self, chain_name: str) -> list[dict]:
        """체인상 활동 급증 감지 (에어드롭 신호)"""
        # 이상적으로는 Dune Analytics 또는 쿼리 사용
        # 여기서는 간소화
        logger.info("🔗 [%s] 체인 활동 분석...", chain_name)
        return []

    def run_full_scan(self) -> list[dict]:
        """전체 스캔 실행"""
        all_findings = []

        # 1. airdrops.io
        findings = self.scan_airdrops_io()
        all_findings.extend(findings)

        # 2. Twitter (API 설정 시 활성화)
        # findings = self.scan_twitter()
        # all_findings.extend(findings)

        # 3. 체인별 활동 분석
        for chain_name in ["scroll", "berachain", "base"]:
            findings = self.scan_chain_activity(chain_name)
            all_findings.extend(findings)

        # 새로운 에어드롭 저장
        new_count = 0
        for finding in all_findings:
            key = f"{finding.get('source')}_{finding.get('keyword', '')}"
            existing = any(
                f"{d.get('source')}_{d.get('keyword', '')}" == key
                for d in self.discovered
            )
            if not existing:
                self.discovered.append({
                    **finding,
                    "status": "new",
                })
                self.db.add_airdrop(
                    chain=finding.get("keyword", "unknown"),
                    project_name=finding.get("source", ""),
                    status="upcoming",
                    notes=json.dumps(finding),
                )
                new_count += 1

        if new_count > 0:
            self._save_discovered()
            logger.info("🆕 새로운 에어드롭 %d개 발견!", new_count)

        return all_findings

    def get_discovered(self, status: str = None) -> list[dict]:
        if status:
            return [d for d in self.discovered if d.get("status") == status]
        return self.discovered