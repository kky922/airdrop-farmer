# -*- coding: utf-8 -*-
"""
주간 에어드롭 리포트 — 테스트넷 진행 상황 + 에어드롭 가능성 평가
매주 일요일 21시 자동 실행 → 텔레그램 알림
"""
import json
import os
import logging
from datetime import datetime, timedelta

import requests
from web3 import Web3

import config

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
REPORT_DIR = os.path.join(DATA_DIR, "reports")

# ─── 체인별 에어드롭 가능성 데이터베이스 ─────────────────────────
AIRDROP_INTEL = {
    "monad": {
        "name": "Monad",
        "type": "testnet",
        "phase": "테스트넷 활성",
        "token_exists": False,
        "tvl": "$0 (테스트넷)",
        "funding": "$225M (Paradigm-led)",
        "twitter_followers": "~500K",
        "airdrop_probability": 85,
        "reason": "Paradigm 대규모 투자, 토큰 미발행, 테스트넷 인센티브 프로그램 진행",
        "expected_value": "$500~$5,000",
        "action": "🔥 집중 활동 — 테스트넷 Faucet 매일 클레임",
        "faucet_urls": [
            "https://faucet.monad.xyz",
            "https://testnet.monad.xyz/faucet",
        ],
        "gas_cost_eth": 0,
        "priority": 1,
    },
    "megaeth": {
        "name": "MegaETH",
        "type": "testnet",
        "phase": "테스트넷 활성",
        "token_exists": False,
        "tvl": "$0 (테스트넷)",
        "funding": "$30M+",
        "twitter_followers": "~100K",
        "airdrop_probability": 60,
        "reason": "초기 테스트넷, 토큰 미발행, but 펀딩 규모 작음",
        "expected_value": "$100~$1,000",
        "action": "⚡ 활동 권장 — 가스비 무료",
        "faucet_urls": [
            "https://testnet.megaeth.com/faucet",
            "https://carrot.megaeth.com/faucet",
        ],
        "gas_cost_eth": 0,
        "priority": 2,
    },
    "berachain": {
        "name": "Berachain",
        "type": "mainnet",
        "phase": "메인넷 런칭",
        "token_exists": True,  # BERA 토큰 발행됨
        "tvl": "$3B+",
        "funding": "$100M+",
        "twitter_followers": "~400K",
        "airdrop_probability": 30,
        "reason": "이미 1차 에어드롭 완료, 추가 에어드롭 불확실",
        "expected_value": "$50~$300 (2차)",
        "action": "⚠️ 대기 — 추가 인센티브 확인 후 결정",
        "faucet_urls": [],
        "gas_cost_eth": 0.005,
        "priority": 5,
    },
    "scroll": {
        "name": "Scroll",
        "type": "mainnet",
        "phase": "메인넷",
        "token_exists": True,  # SCR 토큰 발행됨
        "tvl": "$800M+",
        "funding": "$80M+",
        "twitter_followers": "~300K",
        "airdrop_probability": 20,
        "reason": "이미 SCR 에어드롭 완료, 추가 분배 가능성 낮음",
        "expected_value": "$0~$100",
        "action": "❌ 우선순위 낮음",
        "faucet_urls": [],
        "gas_cost_eth": 0.01,
        "priority": 8,
    },
    "base": {
        "name": "Base",
        "type": "mainnet",
        "phase": "메인넷",
        "token_exists": False,
        "tvl": "$10B+",
        "funding": "Coinbase (내부)",
        "twitter_followers": "~500K",
        "airdrop_probability": 15,
        "reason": "Coinbase가 토큰 발행 안 함 공식 발표, 가능성 매우 낮음",
        "expected_value": "$0",
        "action": "❌ 에어드롭 없음 — 가스비만 소모",
        "faucet_urls": [],
        "gas_cost_eth": 0.005,
        "priority": 10,
    },
    "linea": {
        "name": "Linea",
        "type": "mainnet",
        "phase": "메인넷",
        "token_exists": False,
        "tvl": "$500M+",
        "funding": "ConsenSys",
        "twitter_followers": "~200K",
        "airdrop_probability": 50,
        "reason": "ConsenSys 지원, 토큰 미발행, XP 포인트 프로그램 진행 중",
        "expected_value": "$200~$2,000",
        "action": "🔥 LXP 포인트 적립 진행 중 — 메인넷 소액 필요",
        "faucet_urls": [],
        "gas_cost_eth": 0.008,
        "priority": 3,
    },
    "unichain": {
        "name": "Unichain",
        "type": "mainnet",
        "phase": "메인넷 런칭",
        "token_exists": True,  # UNI 존재
        "tvl": "$1B+",
        "funding": "Uniswap Labs",
        "twitter_followers": "~300K",
        "airdrop_probability": 25,
        "reason": "UNI 토큰 이미 존재, 별도 에어드롭 가능성 불확실",
        "expected_value": "$0~$500",
        "action": "⚠️ 관찰 — Uniswap 생태계 동향 모니터링",
        "faucet_urls": [],
        "gas_cost_eth": 0.005,
        "priority": 6,
    },
    "ink": {
        "name": "Ink (by Kraken)",
        "type": "mainnet",
        "phase": "초기 메인넷",
        "token_exists": False,
        "tvl": "$100M+",
        "funding": "Kraken",
        "twitter_followers": "~50K",
        "airdrop_probability": 40,
        "reason": "Kraken 거래소 백업, 토큰 미발행, 초기 단계",
        "expected_value": "$100~$1,500",
        "action": "⚡ 활동 권장 — Kraken 생태계 성장 기대",
        "faucet_urls": [],
        "gas_cost_eth": 0.003,
        "priority": 4,
    },
    "abstract": {
        "name": "Abstract",
        "type": "mainnet",
        "phase": "메인넷",
        "token_exists": False,
        "tvl": "$500M+",
        "funding": "$150M+",
        "twitter_followers": "~200K",
        "airdrop_probability": 45,
        "reason": "대규모 펀딩, 토큰 미발행, NFT 기반 생태계",
        "expected_value": "$200~$2,000",
        "action": "⚡ 활동 권장 — 메인넷 소액 필요",
        "faucet_urls": [],
        "gas_cost_eth": 0.003,
        "priority": 4,
    },
    "story": {
        "name": "Story Protocol",
        "type": "mainnet",
        "phase": "메인넷",
        "token_exists": True,  # IP 토큰 발행됨
        "tvl": "$200M+",
        "funding": "$140M+",
        "twitter_followers": "~100K",
        "airdrop_probability": 15,
        "reason": "이미 IP 토큰 발행, 1차 에어드롭 완료",
        "expected_value": "$0~$100",
        "action": "❌ 우선순위 낮음",
        "faucet_urls": [],
        "gas_cost_eth": 0.005,
        "priority": 9,
    },
}


class WeeklyAirdropReport:
    """주간 에어드롭 리포트 생성기"""

    def __init__(self):
        os.makedirs(REPORT_DIR, exist_ok=True)

    def get_testnet_balances(self) -> dict:
        """테스트넷 잔액 확인"""
        balances = {}
        testnet_chains = {
            "monad": config.CHAIN_REGISTRY.get("monad", {}).get("rpc"),
            "megaeth": config.CHAIN_REGISTRY.get("megaeth", {}).get("rpc"),
        }
        master = config.MASTER_ADDRESS

        for name, rpc in testnet_chains.items():
            if not rpc:
                continue
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 5}))
                bal = w3.eth.get_balance(master)
                balances[name] = {
                    "balance_eth": float(w3.from_wei(bal, "ether")),
                    "address": master,
                }
            except Exception as e:
                balances[name] = {"error": str(e)[:50]}

        return balances

    def get_testnet_tx_count(self) -> dict:
        """테스트넷 트랜잭션 수 확인"""
        counts = {}
        testnet_chains = {
            "monad": config.CHAIN_REGISTRY.get("monad", {}).get("rpc"),
            "megaeth": config.CHAIN_REGISTRY.get("megaeth", {}).get("rpc"),
        }
        master = config.MASTER_ADDRESS

        for name, rpc in testnet_chains.items():
            if not rpc:
                continue
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 5}))
                # 마스터 + 파생 지갑 카운트
                total = 0
                from eth_account import Account
                Account.enable_unaudited_hdwallet_features()
                for i in range(config.NUM_WALLETS):
                    acct = Account.from_mnemonic(
                        config.HD_MNEMONIC,
                        account_path=f"m/44'/60'/0'/0/{i}"
                    )
                    total += w3.eth.get_transaction_count(acct.address)
                counts[name] = total
            except Exception as e:
                counts[name] = -1

        return counts

    def evaluate_testnet_readiness(self) -> list:
        """테스트넷 → 메인넷 전환 준비도 평가"""
        recommendations = []

        for chain_id, intel in AIRDROP_INTEL.items():
            if intel["type"] == "testnet":
                continue  # 테스트넷은 이미 무료

            if intel["airdrop_probability"] >= 40:
                recommendations.append({
                    "chain_id": chain_id,
                    "name": intel["name"],
                    "probability": intel["airdrop_probability"],
                    "expected_value": intel["expected_value"],
                    "gas_cost": intel["gas_cost_eth"],
                    "action": intel["action"],
                    "priority": intel["priority"],
                    "roi_estimate": self._estimate_roi(intel),
                })

        return sorted(recommendations, key=lambda x: x["priority"])

    def _estimate_roi(self, intel: dict) -> str:
        """ROI 추정"""
        try:
            ev_str = intel["expected_value"]
            if "$0" in ev_str:
                return "N/A"
            gas = intel["gas_cost_eth"]
            if gas == 0:
                return "∞ (무료)"
            # 간단 추정: ETH = $2,000 가정
            gas_usd = gas * 2000 * 5  # 5지갑
            ev_low = int(ev_str.split("~")[0].replace("$", "").replace(",", ""))
            roi = ev_low / gas_usd * 100
            return f"{roi:.0f}%"
        except Exception:
            return "N/A"

    def check_faucet_availability(self) -> dict:
        """Faucet 접근 가능 여부 확인"""
        results = {}
        for chain_id, intel in AIRDROP_INTEL.items():
            if not intel["faucet_urls"]:
                continue
            available = []
            for url in intel["faucet_urls"]:
                try:
                    resp = requests.get(url, timeout=5, allow_redirects=True)
                    available.append({
                        "url": url,
                        "status": resp.status_code == 200,
                    })
                except Exception:
                    available.append({"url": url, "status": False})
            results[chain_id] = available
        return results

    def generate_report(self) -> str:
        """주간 리포트 생성"""
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        report_lines = [
            f"📊 **주간 에어드롭 리포트**",
            f"📅 {now.strftime('%Y-%m-%d %H:%M')}",
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"",
        ]

        # 1. 테스트넷 현황
        report_lines.append("🧪 **테스트넷 현황 (무료)**")
        report_lines.append("")
        balances = self.get_testnet_balances()
        tx_counts = self.get_testnet_tx_count()

        for chain_id in ["monad", "megaeth"]:
            intel = AIRDROP_INTEL.get(chain_id, {})
            bal = balances.get(chain_id, {})
            tx = tx_counts.get(chain_id, 0)

            if "error" in bal:
                report_lines.append(f"  ❌ {intel.get('name', chain_id)}: RPC 오류")
                continue

            bal_eth = bal.get("balance_eth", 0)
            status = "✅" if bal_eth > 0.001 else "⚠️ Faucet 필요"

            report_lines.append(f"  {status} **{intel.get('name', chain_id)}**")
            report_lines.append(f"    잔액: {bal_eth:.4f} ETH (무료)")
            report_lines.append(f"    총 TX: {tx}건")
            report_lines.append(f"    에어드롭 확률: {intel.get('airdrop_probability', 0)}%")
            report_lines.append(f"    예상 가치: {intel.get('expected_value', 'N/A')}")
            report_lines.append(f"    가스비: $0 (무료)")
            report_lines.append("")

        # 2. Faucet 안내
        report_lines.append("🚰 **Faucet 링크**")
        faucets = self.check_faucet_availability()
        for chain_id, urls in faucets.items():
            name = AIRDROP_INTEL[chain_id]["name"]
            for f in urls:
                icon = "✅" if f["status"] else "❌"
                report_lines.append(f"  {icon} {name}: {f['url']}")
        report_lines.append("")

        # 3. 메인넷 진입 추천
        report_lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        report_lines.append("")
        report_lines.append("💰 **메인넷 진입 추천순위**")
        report_lines.append("")

        recommendations = self.evaluate_testnet_readiness()
        for i, rec in enumerate(recommendations, 1):
            report_lines.append(f"  {i}. **{rec['name']}** (우선순위 {rec['priority']})")
            report_lines.append(f"     에어드롭 확률: {rec['probability']}%")
            report_lines.append(f"     예상 가치: {rec['expected_value']}")
            report_lines.append(f"     예상 가스비: {rec['gas_cost']} ETH (5지갑)")
            report_lines.append(f"     ROI 추정: {rec['roi_estimate']}")
            report_lines.append(f"     액션: {rec['action']}")
            report_lines.append("")

        # 4. 이번 주 액션 플랜
        report_lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        report_lines.append("")
        report_lines.append("🎯 **이번 주 액션 플랜**")
        report_lines.append("")
        report_lines.append("  1. Monad Faucet에서 매일 MONAD 클레임")
        report_lines.append("  2. MegaETH Faucet에서 매일 ETH 클레임")
        report_lines.append("  3. 테스트넷에서 swap/bridge/lend 활동")
        report_lines.append("  4. (선택) Linea LXP 포인트 적립 — 0.02 ETH 필요")
        report_lines.append("  5. (선택) Ink/Abstract 소액 활동 — 0.01 ETH 필요")
        report_lines.append("")

        # 5. 리스크 알림
        report_lines.append("⚠️ **리스크 알림**")
        report_lines.append("")
        report_lines.append("  • 에어드롭은 보장되지 않습니다")
        report_lines.append("  • 메인넷 가스비는 돌려받을 수 없습니다")
        report_lines.append("  • 테스트넷은 $0 리스크입니다")
        report_lines.append("")

        report_text = "\n".join(report_lines)

        # 리포트 저장
        report_file = os.path.join(REPORT_DIR, f"report_{now.strftime('%Y%m%d')}.json")
        report_data = {
            "date": now.isoformat(),
            "balances": balances,
            "tx_counts": tx_counts,
            "recommendations": recommendations,
            "report_text": report_text,
        }
        tmp = report_file + ".tmp"
        with open(tmp, "w") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, report_file)

        logger.info("📊 주간 리포트 생성 완료: %s", report_file)
        return report_text

    def get_quick_status(self) -> str:
        """빠른 상태 요약 (매일 알림용)"""
        balances = self.get_testnet_balances()
        tx_counts = self.get_testnet_tx_count()

        lines = ["🧪 **테스트넷 일일 상태**", ""]

        total_tx = 0
        for chain_id in ["monad", "megaeth"]:
            intel = AIRDROP_INTEL.get(chain_id, {})
            bal = balances.get(chain_id, {})
            tx = tx_counts.get(chain_id, 0)
            total_tx += tx

            bal_eth = bal.get("balance_eth", 0) if "error" not in bal else 0
            icon = "✅" if bal_eth > 0.001 else "⚠️"

            lines.append(f"  {icon} {intel.get('name', chain_id)}: {bal_eth:.4f} ETH / {tx} TX")

        lines.append("")
        lines.append(f"  📊 총 TX: {total_tx}건")
        lines.append(f"  💰 총 가스비: $0 (무료)")
        lines.append(f"  🎯 목표: 체인당 50+ TX")

        return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    report = WeeklyAirdropReport()

    print("=" * 60)
    print(report.generate_report())
    print("=" * 60)