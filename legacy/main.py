# -*- coding: utf-8 -*-
"""
🪂 에어드롭 파밍 봇 v2 — 메인 실행
직장인을 위한 100% 자동 에어드롭 파밍 (10개 체인, 7가지 활동)

사용법:
    python main.py              # 전체 시스템 시작 (100% 자동)
    python main.py --init       # 초기 설정 (지갑 생성)
    python main.py --fund       # 자금 분배
    python main.py --status     # 상태 확인
    python main.py --check      # 자격 현황 체크
    python main.py --chains     # 활성 체인 목록
    python main.py --run        # 1회 활동 실행
    python main.py --smart      # 스마트 활동 (자격부족 집중)
"""
import asyncio
import argparse
import logging
import os
import sys
import signal

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from db import Database
from wallet_manager import WalletManager
from activity_engine import ActivityEngine
from balance_tracker import BalanceTracker
from checker import EligibilityChecker
from discovery import AirdropDiscovery
from telegram_bot import AirdropTelegramBot
from scheduler import AirdropScheduler

# ─── 로깅 설정 ────────────────────────────────────────────────────
os.makedirs(config.LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(config.LOG_DIR, "airdrop_farmer.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


def init_system():
    """초기 설정"""
    print("🪂 에어드롭 파밍 봇 — 초기 설정\n")

    db = Database()
    wm = WalletManager()

    if wm.wallets:
        print(f"⚠️ 이미 {wm.count}개 지갑이 존재합니다.")
        confirm = input("다시 생성하시겠습니까? (y/N): ")
        if confirm.lower() != "y":
            print("기존 지갑을 사용합니다.")
            return

    mnemonic = input("HD 니모닉 입력 (12/24단어): ").strip()
    if not mnemonic:
        print("❌ 니모닉이 필요합니다.")
        return

    n = input(f"생성할 지갑 수 (기본 {config.NUM_WALLETS}): ").strip()
    n = int(n) if n else config.NUM_WALLETS

    wm.create_wallets(n=n, mnemonic=mnemonic)
    print(f"\n✅ {wm.count}개 지갑 생성 완료!")
    for w in wm.wallets:
        print(f"  #{w.index}: {w.address}")

    print("\n다음 단계:")
    print("  1. .env 파일에 MASTER_PRIVATE_KEY, MASTER_ADDRESS 설정")
    print("  2. python main.py --fund 으로 자금 분배")
    print("  3. python main.py 로 자동 실행 시작")


async def run_main():
    """메인 실행 루프"""
    logger.info("=" * 60)
    logger.info("🪂 에어드롭 파밍 봇 시작")
    logger.info("=" * 60)

    # 컴포넌트 초기화
    db = Database()
    wm = WalletManager()

    if not wm.wallets:
        logger.error("지갑이 없습니다. python main.py --init 으로 먼저 생성하세요.")
        return

    logger.info("👛 지갑 %d개 로드됨", wm.count)

    engine = ActivityEngine(wm, db)
    tracker = BalanceTracker(wm, db)
    discovery = AirdropDiscovery(db)
    bot = AirdropTelegramBot(wm, engine, tracker, discovery, db)
    scheduler = AirdropScheduler(engine, tracker, discovery, bot, db)

    # 시그널 핸들러
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info("⛔ 종료 신호 수신")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler, sig, None)

    # 텔레그램 봇 시작
    await bot.start()

    # 스케줄러 시작
    await scheduler.start()

    logger.info("✅ 시스템 시작 완료. Ctrl+C로 종료.")

    # 메인 루프 대기
    try:
        await shutdown_event.wait()
    except KeyboardInterrupt:
        pass

    # 정리
    logger.info("🛑 시스템 종료 중...")
    await scheduler.stop()
    await bot.stop()
    db.close()
    logger.info("👋 종료 완료")


def show_status():
    """상태 표시"""
    db = Database()
    wm = WalletManager()

    print("🪂 에어드롭 파밍 봇 v2 상태\n")
    print(f"👛 지갑: {wm.count}개")
    print(f"🔗 활성 체인: {len(config.get_active_chains())}개")

    tier_emoji = {"S": "🟢", "A": "🟡", "B": "🔵"}
    for cn in config.get_active_chains():
        cfg = config.get_chain_config(cn)
        tier = cfg.get("tier", "?")
        emoji = tier_emoji.get(tier, "⚪")
        testnet = "🆓" if cfg.get("is_testnet") else "💰"
        print(f"  {emoji} {cn} {testnet} (Tier {tier})")

    summary = db.get_activity_summary()
    gas = db.get_total_gas_spent()
    print(f"\n⛽ 총 가스 사용: {gas:.6f} ETH")

    for chain, acts in summary.items():
        total = sum(acts.values()) if isinstance(acts, dict) else acts
        print(f"  {chain}: {total}건")

    airdrops = db.get_airdrops()
    print(f"🎁 발견된 에어드롭: {len(airdrops)}개")

    db.close()


def show_chains():
    """체인 목록"""
    print("🔗 활성 체인 목록\n")
    tier_emoji = {"S": "🟢", "A": "🟡", "B": "🔵"}
    for cn in config.get_active_chains():
        cfg = config.get_chain_config(cn)
        tier = cfg.get("tier", "?")
        emoji = tier_emoji.get(tier, "⚪")
        testnet = "🆓테스트넷" if cfg.get("is_testnet") else "💰메인넷"
        acts = cfg.get("supported_activities", [])
        print(f"  {emoji} {cn} — Tier {tier} {testnet}")
        print(f"     활동: {', '.join(acts)}")
    print(f"\n총 {len(config.get_active_chains())}개 체인")


def check_eligibility():
    """자격 현황 체크"""
    db = Database()
    wm = WalletManager()
    if not wm.wallets:
        print("❌ 지갑이 없습니다. --init 으로 먼저 생성하세요.")
        return
    checker = EligibilityChecker(db)
    addresses = [w.address for w in wm.wallets]
    report = checker.generate_report(addresses)
    print(report)
    db.close()


def main():
    parser = argparse.ArgumentParser(description="🪂 에어드롭 파밍 봇 v2")
    parser.add_argument("--init", action="store_true", help="초기 설정 (지갑 생성)")
    parser.add_argument("--fund", action="store_true", help="자금 분배")
    parser.add_argument("--status", action="store_true", help="상태 확인")
    parser.add_argument("--check", action="store_true", help="자격 현황 체크")
    parser.add_argument("--chains", action="store_true", help="활성 체인 목록")
    parser.add_argument("--run", action="store_true", help="1회 활동 실행")
    parser.add_argument("--smart", action="store_true", help="스마트 활동 (자격부족 집중)")
    args = parser.parse_args()

    if args.init:
        init_system()
    elif args.status:
        show_status()
    elif args.chains:
        show_chains()
    elif args.check:
        check_eligibility()
    elif args.fund:
        asyncio.run(_fund_wallets())
    elif args.run:
        asyncio.run(_run_once())
    elif args.smart:
        asyncio.run(_run_smart())
    else:
        asyncio.run(run_main())


async def _fund_wallets():
    """자금 분배"""
    db = Database()
    wm = WalletManager()
    engine = ActivityEngine(wm, db)

    active = config.get_active_chains()
    print(f"활성 체인: {', '.join(active)}")
    chain = input("체인: ").strip() or (active[0] if active else "scroll")
    amount = input(f"지갑당 금액 ETH (기본 {config.FUND_AMOUNT_PER_WALLET_ETH}): ").strip()
    amount = float(amount) if amount else config.FUND_AMOUNT_PER_WALLET_ETH

    print(f"💰 {chain}에 {wm.count}개 지갑으로 {amount} ETH 분배 중...")
    results = await engine.fund_all_wallets(chain)
    print(f"✅ 완료: {len(results)}건")
    db.close()


async def _run_once():
    """1회 활동 실행"""
    db = Database()
    wm = WalletManager()
    if not wm.wallets:
        print("❌ 지갑이 없습니다.")
        return
    engine = ActivityEngine(wm, db)
    print("🔄 활동 사이클 1회 실행 중...")
    results = await engine.run_activity_cycle()
    print(f"✅ 완료: {len(results)}건")
    for r in results[:10]:
        print(f"  #{r['wallet']} {r['chain']}: {r['activity']} ({r.get('tx_hash', 'N/A')[:16]}...)")
    db.close()


async def _run_smart():
    """스마트 활동"""
    db = Database()
    wm = WalletManager()
    if not wm.wallets:
        print("❌ 지갑이 없습니다.")
        return
    engine = ActivityEngine(wm, db)
    print("🎯 스마트 활동 (자격 부족한 체인 집중)...")
    results = await engine.run_smart_activity()
    if results:
        print(f"✅ 완료: {len(results)}건")
        for r in results[:10]:
            print(f"  #{r['wallet']} {r['chain']}: {r['activity']}")
    else:
        print("✅ 모든 자격 충족!")
    db.close()


if __name__ == "__main__":
    main()