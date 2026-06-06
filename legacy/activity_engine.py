# -*- coding: utf-8 -*-
"""
활동 실행 엔진 v2 — 10개 체인, 7가지 활동, 100% 자동화
"""
import asyncio
import logging
import random
from datetime import datetime

from wallet_manager import WalletManager
from anti_sybil import AntiSybilEngine
from gas_optimizer import GasOptimizer
from db import Database
from chains import get_chain
from chains.base import BaseChain
from checker import EligibilityChecker
import config

logger = logging.getLogger(__name__)


class ActivityEngine:
    """에어드롭 파밍 활동 엔진 v2"""

    def __init__(self, wallet_mgr: WalletManager, db: Database):
        self.wallet_mgr = wallet_mgr
        self.db = db
        self.anti_sybil = AntiSybilEngine()
        self.checker = EligibilityChecker(db)
        self.is_running = False
        self._chain_instances: dict[str, BaseChain] = {}
        self._cycle_day = 0  # 활동 사이클 데이 카운터

    def _get_chain(self, chain_name: str) -> BaseChain | None:
        """체인 인스턴스 가져오기/생성"""
        if chain_name not in self._chain_instances:
            try:
                self._chain_instances[chain_name] = get_chain(chain_name)
            except Exception as e:
                logger.error("체인 생성 실패 %s: %s", chain_name, e)
                return None
        return self._chain_instances.get(chain_name)

    def _get_activity_cycle(self) -> list[dict]:
        """현재 사이클 단계의 활동 목록"""
        cycle = config.ACTIVITY_CYCLE
        idx = self._cycle_day % len(cycle)
        return cycle[idx]

    def _next_cycle(self):
        """다음 사이클로 이동"""
        self._cycle_day += 1
        logger.info("📅 활동 사이클 Day %d", self._cycle_day)

    # ═══════════════════════════════════════════════════════════════
    # 🎯 핵심: 7가지 활동 실행
    # ═══════════════════════════════════════════════════════════════

    async def _execute_activity(self, chain: BaseChain, wallet, activity_type: str, amount: float) -> str | None:
        """단일 활동 실행"""
        pk = wallet.private_key
        try:
            if activity_type == "bridge":
                return await chain.bridge(pk, amount)
            elif activity_type == "swap":
                tokens = list(chain.cfg.get("tokens", {}).keys())
                token_in = "ETH" if chain.currency == "ETH" else chain.currency
                token_out = tokens[1] if len(tokens) > 1 else "USDC"
                return await chain.swap(pk, token_in, token_out, amount)
            elif activity_type == "lend":
                return await chain.lend(pk, chain.currency, amount)
            elif activity_type == "lp":
                return await chain.add_liquidity(pk, chain.currency, "USDC", amount)
            elif activity_type == "nft":
                return await chain.mint_nft(pk, max_price=config.NFT_MAX_PRICE_ETH)
            elif activity_type == "governance":
                return await chain.vote_governance(pk)
            elif activity_type == "transfer":
                # 다음 지갑으로 소액 송금
                next_idx = (wallet.index + 1) % self.wallet_mgr.count
                to_addr = self.wallet_mgr.wallets[next_idx].address
                return await chain.transfer(pk, to_addr, amount * 0.5)
            else:
                logger.warning("알 수 없는 활동: %s", activity_type)
                return None
        except Exception as e:
            logger.error("[%s] %s 실패: %s", chain.chain_name, activity_type, e)
            return None

    async def run_activity_cycle(self, chain_name: str = None):
        """한 사이클 활동 실행 — 체인 미지정시 자격 낮은 체인 우선"""
        self.is_running = True
        results = []

        # 실행할 체인 결정
        if chain_name:
            chains_to_run = [chain_name]
        else:
            # 자격 낮은 체인 우선 + 테스트넷 항상 포함
            chains_to_run = self._get_priority_chains()

        for cn in chains_to_run:
            chain = self._get_chain(cn)
            if not chain or not chain.is_connected():
                logger.warning("[%s] 연결 안됨, 스킵", cn)
                continue

            # 가스 체크 (테스트넷은 스킵)
            if not chain.is_testnet:
                gas = chain.get_gas_price()
                if gas > config.GAS_MAX_GWEI:
                    logger.warning("[%s] 가스 %.1f gwei > %.1f, 스킵", cn, gas, config.GAS_MAX_GWEI)
                    continue

            # 활동 사이클에서 활동 선택
            cycle_activities = self._get_activity_cycle()

            for wallet in self.wallet_mgr.wallets:
                try:
                    # 자격 체크해서 부족한 활동 우선
                    missing = self.checker.get_missing_activities(wallet.address, cn)
                    priority_acts = [a for a in missing if a in config.ACTIVITY_TYPES]

                    # 우선순위 활동 + 사이클 활동
                    acts_to_do = priority_acts[:2] if priority_acts else []
                    for ca in cycle_activities:
                        act_type = ca["type"]
                        if act_type not in acts_to_do and chain.supports_activity(act_type):
                            acts_to_do.append(act_type)

                    # 최대 3개까지만 (과부하 방지)
                    acts_to_do = acts_to_do[:3]

                    logger.info("🎯 #%d %s [%s]: %s", wallet.index, wallet.address[:10], cn, acts_to_do)

                    for act in acts_to_do:
                        amount = self.anti_sybil.vary_amount(
                            random.uniform(config.SWAP_AMOUNT_MIN_ETH, config.SWAP_AMOUNT_MAX_ETH),
                            wallet.index,
                        )

                        tx_hash = await self._execute_activity(chain, wallet, act, amount)

                        # DB 기록
                        self.db.log_activity(
                            wallet_index=wallet.index,
                            wallet_address=wallet.address,
                            chain=cn,
                            activity_type=act,
                            tx_hash=tx_hash or "",
                            amount=amount,
                            status="success" if tx_hash else "failed",
                        )
                        self.anti_sybil.record_activity(wallet.index, act, tx_hash or "")

                        results.append({
                            "wallet": wallet.index,
                            "chain": cn,
                            "activity": act,
                            "tx_hash": tx_hash,
                            "amount": amount,
                        })

                    # 지갑 간 딜레이
                    if wallet.index < self.wallet_mgr.count - 1:
                        self.anti_sybil.sleep_with_jitter(wallet.index)

                except Exception as e:
                    logger.error("#%d %s 실패: %s", wallet.index, cn, e)

        self._next_cycle()
        self.is_running = False
        logger.info("✅ 활동 사이클 완료: %d건", len(results))
        return results

    def _get_priority_chains(self) -> list[str]:
        """우선순위 체인 목록 (테스트넷 + 자격낮은순)"""
        chains = []
        # 테스트넷 먼저 (무료)
        for cn in config.get_active_chains():
            cfg = config.get_chain_config(cn)
            if cfg.get("is_testnet"):
                chains.append(cn)
        # 메인넷은 자격낮은순
        if self.wallet_mgr.wallets:
            addr = self.wallet_mgr.wallets[0].address
            priority = self.checker.get_priority_chains(addr)
            for p in priority:
                if p["chain"] not in chains:
                    chains.append(p["chain"])
        return chains[:5]  # 한 사이클에 최대 5개 체인

    async def run_smart_activity(self):
        """스마트 활동 — 자격 부족한 곳만 집중 공략"""
        if not self.wallet_mgr.wallets:
            return []

        results = []
        for wallet in self.wallet_mgr.wallets:
            priority = self.checker.get_priority_chains(wallet.address)
            for p in priority[:3]:  # 상위 3개 체인만
                chain = self._get_chain(p["chain"])
                if not chain or not chain.is_connected():
                    continue

                missing = p.get("missing", [])
                for act in missing[:2]:
                    if act in config.ACTIVITY_TYPES and chain.supports_activity(act):
                        amount = self.anti_sybil.vary_amount(
                            random.uniform(config.SWAP_AMOUNT_MIN_ETH, config.SWAP_AMOUNT_MAX_ETH),
                            wallet.index,
                        )
                        tx_hash = await self._execute_activity(chain, wallet, act, amount)
                        self.db.log_activity(
                            wallet_index=wallet.index,
                            wallet_address=wallet.address,
                            chain=p["chain"],
                            activity_type=act,
                            tx_hash=tx_hash or "",
                            amount=amount,
                            status="success" if tx_hash else "failed",
                        )
                        results.append({"wallet": wallet.index, "chain": p["chain"], "activity": act, "tx_hash": tx_hash})

        return results

    async def fund_all_wallets(self, chain_name: str = "scroll"):
        chain = self._get_chain(chain_name)
        if not chain:
            return []
        return self.wallet_mgr.fund_wallets(chain.w3)

    async def consolidate_all(self, chain_name: str = "scroll"):
        chain = self._get_chain(chain_name)
        if not chain:
            return []
        return self.wallet_mgr.consolidate_to_master(chain.w3)

    def check_all_airdrops(self) -> list[dict]:
        results = []
        for chain_name in config.get_active_chains():
            chain = self._get_chain(chain_name)
            if not chain or not chain.is_connected():
                continue
            for wallet in self.wallet_mgr.wallets:
                info = chain.check_airdrop(wallet.address)
                info["wallet_index"] = wallet.index
                results.append(info)
        return results

    def get_status(self) -> dict:
        return {
            "is_running": self.is_running,
            "cycle_day": self._cycle_day,
            "total_wallets": self.wallet_mgr.count,
            "active_chains": list(self._chain_instances.keys()),
            "activity_summary": self.db.get_activity_summary(),
            "total_gas": self.db.get_total_gas_spent(),
        }