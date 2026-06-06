# -*- coding: utf-8 -*-
"""
스케줄러 v2 — 100% 자동화, 10개 체인, 자격 기반 우선순위
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import config
from activity_engine import ActivityEngine
from balance_tracker import BalanceTracker
from discovery import AirdropDiscovery
from telegram_bot import AirdropTelegramBot
from checker import EligibilityChecker
from db import Database

logger = logging.getLogger(__name__)


class AirdropScheduler:
    """100% 자동 스케줄러"""

    def __init__(self, engine: ActivityEngine, tracker: BalanceTracker,
                 discovery: AirdropDiscovery, bot: AirdropTelegramBot, db: Database):
        self.engine = engine
        self.tracker = tracker
        self.discovery = discovery
        self.bot = bot
        self.db = db
        self.checker = EligibilityChecker(db)
        self.scheduler = AsyncIOScheduler()
        self._running = False

    def setup_jobs(self):
        """스케줄 잡 등록"""
        # 1. 정기 활동 — 자동 멀티체인 (8시간마다)
        self.scheduler.add_job(
            self._activity_job,
            IntervalTrigger(hours=config.ACTIVITY_INTERVAL_HOURS),
            id="activity_cycle",
            name="활동 사이클 (자동)",
            replace_existing=True,
        )

        # 2. 스마트 활동 — 자격 부족한 곳 집중 (12시간마다)
        self.scheduler.add_job(
            self._smart_activity_job,
            IntervalTrigger(hours=config.CHECKER_INTERVAL_HOURS),
            id="smart_activity",
            name="스마트 활동 (자격보완)",
            replace_existing=True,
        )

        # 3. 잔액 체크 (6시간마다)
        self.scheduler.add_job(
            self._balance_job,
            IntervalTrigger(hours=config.BALANCE_CHECK_INTERVAL_HOURS),
            id="balance_check",
            name="잔액 체크",
            replace_existing=True,
        )

        # 4. 에어드롭 탐색 (4시간마다)
        self.scheduler.add_job(
            self._discovery_job,
            IntervalTrigger(hours=config.DISCOVERY_INTERVAL_HOURS),
            id="discovery_scan",
            name="에어드롭 탐색",
            replace_existing=True,
        )

        # 5. 일일 리포트 + 자격 현황 (매일 21시)
        self.scheduler.add_job(
            self._daily_report_job,
            CronTrigger(hour=config.REPORT_HOUR, minute=0),
            id="daily_report",
            name="일일 리포트",
            replace_existing=True,
        )

        # 6. 아침 리포트 — 파밍 현황 + 다음 계획 (매일 오전 8시)
        self.scheduler.add_job(
            self._morning_report_job,
            CronTrigger(hour=8, minute=0),
            id="morning_report",
            name="🌅 아침 파밍 리포트",
            replace_existing=True,
        )

        logger.info("📅 스케줄 등록 완료 (%d개):", len(self.scheduler.get_jobs()))
        for job in self.scheduler.get_jobs():
            try:
                nrt = job.next_run_time
            except AttributeError:
                nrt = "pending"
            logger.info("  - %s: %s", job.name, nrt)

    async def _activity_job(self):
        """활동 사이클 — 모든 체인 자동"""
        if self.engine.is_running:
            logger.info("이미 활동 중 — 스킵")
            return
        logger.info("🔄 [스케줄] 자동 활동 사이클 시작")
        try:
            results = await self.engine.run_activity_cycle()
            if results:
                msg = f"✅ 활동 완료: {len(results)}건\n"
                chains_done = set(r["chain"] for r in results)
                msg += f"체인: {', '.join(chains_done)}"
                await self.bot.send_alert(msg)
        except Exception as e:
            logger.error("활동 사이클 실패: %s", e)

    async def _smart_activity_job(self):
        """스마트 활동 — 자격 부족한 체인/활동 집중"""
        if self.engine.is_running:
            return
        logger.info("🎯 [스케줄] 스마트 활동 (자격보완)")
        try:
            results = await self.engine.run_smart_activity()
            if results:
                msg = f"🎯 자격보완 완료: {len(results)}건"
                await self.bot.send_alert(msg)
        except Exception as e:
            logger.error("스마트 활동 실패: %s", e)

    async def _balance_job(self):
        """잔액 체크"""
        logger.info("💰 [스케줄] 잔액 체크")
        try:
            report = self.tracker.check_all_balances()
            low = self.tracker.get_low_balance_wallets()
            if low:
                msg = f"⚠️ 잔액 낮은 지갑 {len(low)}개:\n"
                for w in low[:5]:
                    msg += f"  #{w['wallet_index']} ({w['chain']}): {w['balance']:.6f}\n"
                await self.bot.send_alert(msg)
        except Exception as e:
            logger.error("잔액 체크 실패: %s", e)

    async def _discovery_job(self):
        """에어드롭 탐색"""
        logger.info("🔍 [스케줄] 에어드롭 탐색")
        try:
            findings = self.discovery.run_full_scan()
            if findings:
                msg = f"🆕 새 에어드롭 {len(findings)}개 발견!\n"
                for f in findings[:5]:
                    msg += f"  - {f.get('keyword', '?')} ({f.get('source', '?')})\n"
                await self.bot.send_alert(msg)
        except Exception as e:
            logger.error("에어드롭 탐색 실패: %s", e)

    async def _daily_report_job(self):
        """일일 리포트 — 잔액 + 활동 + 자격 현황"""
        logger.info("📋 [스케줄] 일일 리포트")
        try:
            # 잔액 리포트
            balance_msg = self.tracker.format_balance_report()
            await self.bot.send_alert(balance_msg)

            # 활동 요약
            summary = self.db.get_activity_summary()
            gas = self.db.get_total_gas_spent()
            msg = f"📋 **일일 활동 요약**\n⛽ 총 가스: {gas:.6f} ETH\n"
            for chain, acts in summary.items():
                total = sum(acts.values()) if isinstance(acts, dict) else acts
                msg += f"**{chain}**: {total}건\n"
            await self.bot.send_alert(msg)

            # 자격 현황 리포트
            addresses = [w.address for w in self.engine.wallet_mgr.wallets]
            eligibility_msg = self.checker.generate_report(addresses)
            await self.bot.send_alert(eligibility_msg)
        except Exception as e:
            logger.error("일일 리포트 실패: %s", e)

    async def _morning_report_job(self):
        """🌅 아침 리포트 — 전체 파밍 현황 + 다음 계획"""
        logger.info("🌅 [스케줄] 아침 파밍 리포트")
        try:
            now = datetime.now()
            date_str = now.strftime("%Y년 %m월 %d일 (%a)")

            # 전체 활동 요약
            summary = self.db.get_activity_summary()
            gas = self.db.get_total_gas_spent()

            # 자격 현황
            addresses = [w.address for w in self.engine.wallet_mgr.wallets]

            msg = f"🌅 **아침 파밍 리포트**\n📅 {date_str}\n\n"

            # ─── 전체 현황 ───
            total_tx = 0
            msg += "📊 **전체 파밍 현황**\n"
            msg += f"⛽ 총 가스 사용: {gas:.6f} ETH\n"
            msg += f"👛 활성 지갑: {len(addresses)}개\n\n"

            # 체인별 현황
            tier_emoji = {"S": "🟢", "A": "🟡", "B": "🔵"}
            msg += "🔗 **체인별 활동 현황**\n"
            for cn in config.get_active_chains():
                cfg = config.get_chain_config(cn)
                tier = cfg.get("tier", "?")
                emoji = tier_emoji.get(tier, "⚪")
                testnet = "🆓테스트넷" if cfg.get("is_testnet") else "💰메인넷"
                acts = summary.get(cn, {})
                tx_count = sum(acts.values()) if isinstance(acts, dict) else acts
                total_tx += tx_count
                status = f"✅ {tx_count}건" if tx_count > 0 else "⬜ 미시작"
                msg += f"  {emoji} {cn} ({testnet}): {status}\n"

            msg += f"\n📈 총 트랜잭션: {total_tx}건\n"

            # ─── 다음 파밍 계획 ───
            msg += "\n📅 **오늘 예정 파밍 계획**\n"

            # 현재 시간 기준 다음 활동 시간 계산
            next_activity = now.replace(hour=now.hour // 8 * 8 + 8, minute=0, second=0)
            if next_activity <= now:
                next_activity = now.replace(hour=(now.hour // 8 + 1) * 8, minute=0, second=0)
            next_smart = now.replace(hour=(now.hour // 12 + 1) * 12, minute=0, second=0)

            msg += f"  🔄 활동 사이클: 8시간마다 (다음: {next_activity.strftime('%H:%M')})\n"
            msg += f"  🎯 자격보완: 12시간마다\n"
            msg += f"  💰 잔액체크: 6시간마다\n"
            msg += f"  🔍 에어드롭 탐색: 4시간마다\n"
            msg += f"  📋 일일 리포트: 매일 21시\n"

            # 우선순위 추천
            msg += "\n🎯 **오늘 추천 우선순위**\n"
            # 자격 부족한 체인 추천
            priority_chains = []
            for cn in config.get_active_chains():
                cfg = config.get_chain_config(cn)
                acts = summary.get(cn, {})
                tx_count = sum(acts.values()) if isinstance(acts, dict) else acts
                if tx_count < 5:
                    priority_chains.append((cn, cfg.get("tier", "Z"), tx_count))

            # Tier 순으로 정렬
            tier_order = {"S": 0, "A": 1, "B": 2}
            priority_chains.sort(key=lambda x: (tier_order.get(x[1], 3), x[2]))

            for i, (cn, tier, tx) in enumerate(priority_chains[:5], 1):
                emoji = tier_emoji.get(tier, "⚪")
                msg += f"  {i}. {emoji} {cn} (Tier {tier}) — 현재 {tx}건\n"

            if not priority_chains:
                msg += "  ✅ 모든 체인 활동 양호!\n"

            # 에어드롭 정보
            airdrops = self.db.get_airdrops()
            if airdrops:
                msg += f"\n🎁 **추적 중인 에어드롭: {len(airdrops)}개**\n"
                for a in airdrops[:3]:
                    msg += f"  - {a.get('name', '?')}: {a.get('status', '?')}\n"

            msg += "\n💡 /status /eligibility /chains 로 상세 확인"

            await self.bot.send_alert(msg)
        except Exception as e:
            logger.error("아침 리포트 실패: %s", e)

    async def start(self):
        """스케줄러 시작"""
        self.setup_jobs()
        self.scheduler.start()
        self._running = True
        logger.info("📅 스케줄러 시작됨 — 100%% 자동화")

        # 초기 실행 (시작하자마자 체크)
        await self._balance_job()
        await self._discovery_job()

    async def stop(self):
        self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info("📅 스케줄러 정지됨")

    def get_status(self) -> dict:
        jobs = []
        for job in self.scheduler.get_jobs():
            try:
                nrt = str(job.next_run_time)
            except AttributeError:
                nrt = "pending"
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": nrt,
            })
        return {"running": self._running, "jobs": jobs}
