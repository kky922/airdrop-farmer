# -*- coding: utf-8 -*-
"""
텔레그램 봇 — 원격 제어 및 모니터링
"""
import asyncio
import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import config
from activity_engine import ActivityEngine
from balance_tracker import BalanceTracker
from checker import EligibilityChecker
from discovery import AirdropDiscovery
from wallet_manager import WalletManager
from db import Database

logger = logging.getLogger(__name__)


class AirdropTelegramBot:
    """텔레그램 제어 봇"""

    def __init__(self, wallet_mgr: WalletManager, engine: ActivityEngine,
                 tracker: BalanceTracker, discovery: AirdropDiscovery, db: Database):
        self.wallet_mgr = wallet_mgr
        self.engine = engine
        self.tracker = tracker
        self.discovery = discovery
        self.db = db
        self.app: Optional[Application] = None

    async def start(self):
        """봇 시작"""
        if not config.TELEGRAM_BOT_TOKEN:
            logger.warning("텔레그램 봇 토큰 없음")
            return

        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("balance", self._cmd_balance))
        self.app.add_handler(CommandHandler("run", self._cmd_run))
        self.app.add_handler(CommandHandler("stop", self._cmd_stop))
        self.app.add_handler(CommandHandler("fund", self._cmd_fund))
        self.app.add_handler(CommandHandler("consolidate", self._cmd_consolidate))
        self.app.add_handler(CommandHandler("airdrop", self._cmd_airdrop))
        self.app.add_handler(CommandHandler("discover", self._cmd_discover))
        self.app.add_handler(CommandHandler("wallets", self._cmd_wallets))
        self.app.add_handler(CommandHandler("eligibility", self._cmd_eligibility))
        self.app.add_handler(CommandHandler("chains", self._cmd_chains))
        self.app.add_handler(CommandHandler("smart", self._cmd_smart))
        self.app.add_handler(CommandHandler("schedule", self._cmd_schedule))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CallbackQueryHandler(self._callback))

        logger.info("🤖 텔레그램 봇 시작")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self):
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    def _check_auth(self, update: Update) -> bool:
        """권한 확인"""
        chat_id = str(update.effective_chat.id)
        if config.TELEGRAM_CHAT_ID and chat_id != config.TELEGRAM_CHAT_ID:
            return False
        return True

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return
        keyboard = [
            [InlineKeyboardButton("📊 상태", callback_data="status"),
             InlineKeyboardButton("💰 잔액", callback_data="balance")],
            [InlineKeyboardButton("🚀 활동시작", callback_data="run"),
             InlineKeyboardButton("⏹ 정지", callback_data="stop")],
            [InlineKeyboardButton("📋 자격", callback_data="eligibility"),
             InlineKeyboardButton("🔗 체인", callback_data="chains")],
            [InlineKeyboardButton("🎯 스마트", callback_data="smart"),
             InlineKeyboardButton("🔍 탐색", callback_data="discover")],
            [InlineKeyboardButton("🎁 에어드롭", callback_data="airdrop"),
             InlineKeyboardButton("📅 스케줄", callback_data="schedule")],
        ]
        await update.message.reply_text(
            "🪂 **에어드롭 파밍 봇**\n\n원하는 작업을 선택하세요:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    async def _cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return
        status = self.engine.get_status()
        msg = (
            f"📊 **시스템 상태**\n\n"
            f"🔄 실행 중: {'✅' if status['is_running'] else '❌'}\n"
            f"👛 지갑 수: {status['total_wallets']}\n"
            f"🔗 체인: {', '.join(status['chains']) or '없음'}\n"
            f"⛽ 총 가스: {status['total_gas']:.6f} ETH\n"
        )
        for chain, acts in status["activity_summary"].items():
            msg += f"\n**{chain}**: {acts}"
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_balance(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return
        msg = self.tracker.format_balance_report()
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_run(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return
        chain = ctx.args[0] if ctx.args else None  # None = 자동 선택
        label = chain or "자동(전체)"
        await update.message.reply_text(f"🚀 {label} 활동 사이클 시작...")
        asyncio.create_task(self.engine.run_activity_cycle(chain))
        await update.message.reply_text(f"✅ {label} 사이클 백그라운드 실행 중")

    async def _cmd_stop(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        self.engine.is_running = False
        await update.message.reply_text("⏹ 활동 중지 요청됨")

    async def _cmd_fund(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return
        chain = ctx.args[0] if ctx.args else None
        if not chain:
            active = config.get_active_chains()
            chain = active[0] if active else "scroll"
        await update.message.reply_text(f"💰 {chain} 지갑 분배 시작...")
        results = await self.engine.fund_all_wallets(chain)
        msg = f"✅ {chain} 분배 완료: {len(results)}건"
        await update.message.reply_text(msg)

    async def _cmd_consolidate(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return
        chain = ctx.args[0] if ctx.args else None
        if not chain:
            active = config.get_active_chains()
            chain = active[0] if active else "scroll"
        await update.message.reply_text(f"💸 {chain} 자금 회수 시작...")
        results = await self.engine.consolidate_all(chain)
        msg = f"✅ {chain} 회수 완료: {len(results)}건"
        await update.message.reply_text(msg)

    async def _cmd_airdrop(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return
        results = self.engine.check_all_airdrops()
        if not results:
            await update.message.reply_text("🎁 확인된 에어드롭 없음")
            return
        msg = "🎁 **에어드롭 확인 결과**\n\n"
        for r in results[:10]:
            eligible = "✅" if r.get("likely_eligible") else "❌"
            msg += f"{eligible} #{r['wallet_index']} ({r['chain']}): TX {r.get('tx_count', 0)}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_discover(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return
        await update.message.reply_text("🔍 에어드롭 탐색 중...")
        findings = self.discovery.run_full_scan()
        msg = f"🔍 탐색 완료: {len(findings)}건 발견"
        await update.message.reply_text(msg)

    async def _cmd_wallets(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return
        msg = f"👛 **지갑 목록** ({self.wallet_mgr.count}개)\n\n"
        for w in self.wallet_mgr.wallets[:10]:
            msg += f"#{w.index}: `{w.address}`\n"
        if self.wallet_mgr.count > 10:
            msg += f"\n... 외 {self.wallet_mgr.count - 10}개"
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_eligibility(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """자격 현황 체크"""
        if not self._check_auth(update):
            return
        checker = EligibilityChecker(self.db)
        addresses = [w.address for w in self.wallet_mgr.wallets]
        msg = checker.generate_report(addresses)
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_chains(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """활성 체인 목록"""
        if not self._check_auth(update):
            return
        tier_emoji = {"S": "🟢", "A": "🟡", "B": "🔵"}
        msg = "🔗 **활성 체인 목록**\n\n"
        for cn in config.get_active_chains():
            cfg = config.get_chain_config(cn)
            tier = cfg.get("tier", "?")
            emoji = tier_emoji.get(tier, "⚪")
            testnet = "🆓" if cfg.get("is_testnet") else "💰"
            acts = ", ".join(cfg.get("supported_activities", []))
            msg += f"{emoji} **{cn}** {testnet} (Tier {tier})\n  활동: {acts}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_smart(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """스마트 활동 — 자격 부족한 곳 집중"""
        if not self._check_auth(update):
            return
        await update.message.reply_text("🎯 스마트 활동 시작 (자격 부족한 체인 집중)...")
        results = await self.engine.run_smart_activity()
        if results:
            msg = f"🎯 스마트 활동 완료: {len(results)}건\n"
            for r in results[:10]:
                msg += f"  #{r['wallet']} {r['chain']}: {r['activity']}\n"
        else:
            msg = "✅ 모든 자격 충족! 추가 활동 불필요"
        await update.message.reply_text(msg)

    async def _cmd_schedule(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """스케줄러 상태"""
        if not self._check_auth(update):
            return
        from scheduler import AirdropScheduler
        # 스케줄러 상태는 main에서 전달받아야 하지만, 간단히 안내
        msg = (
            "📅 **스케줄러 설정**\n\n"
            f"🔄 활동 사이클: {config.ACTIVITY_INTERVAL_HOURS}시간마다\n"
            f"🎯 자격보완: {config.CHECKER_INTERVAL_HOURS}시간마다\n"
            f"💰 잔액체크: {config.BALANCE_CHECK_INTERVAL_HOURS}시간마다\n"
            f"🔍 에어드롭 탐색: {config.DISCOVERY_INTERVAL_HOURS}시간마다\n"
            f"📋 일일 리포트: 매일 {config.REPORT_HOUR}시\n"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = (
            "🪂 **에어드롭 파밍 봇 v2 명령어**\n\n"
            "/start - 메인 메뉴\n"
            "/status - 시스템 상태\n"
            "/balance - 전체 잔액\n"
            "/run [chain] - 활동 실행 (체인 생략시 자동)\n"
            "/smart - 스마트 활동 (자격부족 집중)\n"
            "/stop - 활동 중지\n"
            "/fund [chain] - 자금 분배\n"
            "/consolidate [chain] - 자금 회수\n"
            "/eligibility - 자격 현황 리포트\n"
            "/chains - 활성 체인 목록\n"
            "/airdrop - 에어드롭 확인\n"
            "/discover - 에어드롭 탐색\n"
            "/schedule - 스케줄 현황\n"
            "/wallets - 지갑 목록\n"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        # 콜백 데이터에 따라 직접 응답 (Update.message 설정 불가하므로)
        if data == "status":
            status = self.engine.get_status()
            msg = (
                f"📊 **시스템 상태**\n\n"
                f"🔄 실행 중: {'✅' if status['is_running'] else '❌'}\n"
                f"👛 지갑 수: {status['total_wallets']}\n"
                f"🔗 체인: {', '.join(status['chains']) or '없음'}\n"
                f"⛽ 총 가스: {status['total_gas']:.6f} ETH\n"
            )
            for chain, acts in status["activity_summary"].items():
                msg += f"\n**{chain}**: {acts}"
            await query.message.reply_text(msg, parse_mode="Markdown")

        elif data == "balance":
            msg = self.tracker.format_balance_report()
            await query.message.reply_text(msg, parse_mode="Markdown")

        elif data == "run":
            await query.message.reply_text("🚀 자동 활동 사이클 시작...")
            asyncio.create_task(self.engine.run_activity_cycle())
            await query.message.reply_text("✅ 사이클 백그라운드 실행 중")

        elif data == "stop":
            self.engine.is_running = False
            await query.message.reply_text("⏹ 활동 중지 요청됨")

        elif data == "airdrop":
            results = self.engine.check_all_airdrops()
            if not results:
                await query.message.reply_text("🎁 확인된 에어드롭 없음")
            else:
                msg = "🎁 **에어드롭 확인 결과**\n\n"
                for r in results[:10]:
                    eligible = "✅" if r.get("likely_eligible") else "❌"
                    msg += f"{eligible} #{r['wallet_index']} ({r['chain']}): TX {r.get('tx_count', 0)}\n"
                await query.message.reply_text(msg, parse_mode="Markdown")

        elif data == "discover":
            await query.message.reply_text("🔍 에어드롭 탐색 중...")
            findings = self.discovery.run_full_scan()
            msg = f"🔍 탐색 완료: {len(findings)}건 발견"
            await query.message.reply_text(msg)

        elif data == "eligibility":
            checker = EligibilityChecker(self.db)
            addresses = [w.address for w in self.wallet_mgr.wallets]
            msg = checker.generate_report(addresses)
            await query.message.reply_text(msg, parse_mode="Markdown")

        elif data == "chains":
            tier_emoji = {"S": "🟢", "A": "🟡", "B": "🔵"}
            msg = "🔗 **활성 체인 목록**\n\n"
            for cn in config.get_active_chains():
                cfg = config.get_chain_config(cn)
                tier = cfg.get("tier", "?")
                emoji = tier_emoji.get(tier, "⚪")
                testnet = "🆓" if cfg.get("is_testnet") else "💰"
                msg += f"{emoji} **{cn}** {testnet} (Tier {tier})\n"
            await query.message.reply_text(msg, parse_mode="Markdown")

        elif data == "smart":
            await query.message.reply_text("🎯 스마트 활동 시작...")
            results = await self.engine.run_smart_activity()
            if results:
                msg = f"🎯 완료: {len(results)}건\n"
                for r in results[:10]:
                    msg += f"  #{r['wallet']} {r['chain']}: {r['activity']}\n"
            else:
                msg = "✅ 모든 자격 충족!"
            await query.message.reply_text(msg)

        elif data == "schedule":
            msg = (
                "📅 **스케줄러 설정**\n\n"
                f"🔄 활동 사이클: {config.ACTIVITY_INTERVAL_HOURS}시간마다\n"
                f"🎯 자격보완: {config.CHECKER_INTERVAL_HOURS}시간마다\n"
                f"💰 잔액체크: {config.BALANCE_CHECK_INTERVAL_HOURS}시간마다\n"
                f"🔍 에어드롭 탐색: {config.DISCOVERY_INTERVAL_HOURS}시간마다\n"
                f"📋 일일 리포트: 매일 {config.REPORT_HOUR}시\n"
            )
            await query.message.reply_text(msg, parse_mode="Markdown")

    async def send_alert(self, message: str):
        """알림 전송"""
        if self.app and config.TELEGRAM_CHAT_ID:
            try:
                await self.app.bot.send_message(
                    chat_id=config.TELEGRAM_CHAT_ID,
                    text=message,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error("텔레그램 전송 실패: %s", e)