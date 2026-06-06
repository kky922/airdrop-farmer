"""
에어드랍 파밍 자동화 봇 v2.0
메인 진입점

사용법:
  python main.py                # 스케줄러 모드 (자동 실행)
  python main.py --init         # HD 지갑 생성
  python main.py --status       # 현재 상태 출력
  python main.py --run          # 파밍 1회 즉시 실행
  python main.py --scan         # 프로젝트 스캔
  python main.py --dashboard    # 웹 대시보드만 실행

레거시 CLI 호환 (legacy/main.py 위임):
  python main.py --check        # 에어드랍 자격 확인
  python main.py --chains       # 체인 목록
  python main.py --smart        # 스마트 파밍
"""
import argparse
import asyncio
import getpass
import json
import logging
import os
import random
import signal
import sys
from datetime import datetime
from pathlib import Path

from eth_account import Account

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

Account.enable_unaudited_hdwallet_features()


def parse_args():
    parser = argparse.ArgumentParser(description="Airdrop Farming Bot v2")
    parser.add_argument("--init", action="store_true", help="HD 지갑 생성")
    parser.add_argument("--add-wife", action="store_true", help="와이프 지갑 등록")
    parser.add_argument("--status", action="store_true", help="현재 상태 출력")
    parser.add_argument("--run", action="store_true", help="파밍 1회 즉시 실행")
    parser.add_argument("--dry-run", action="store_true", help="실제 실행 없이 시뮬레이션")
    parser.add_argument("--scan", action="store_true", help="프로젝트 스캔")
    parser.add_argument("--dashboard", action="store_true", help="웹 대시보드 실행")
    # 레거시 호환
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--chains", action="store_true")
    parser.add_argument("--smart", action="store_true")
    parser.add_argument("--fund", action="store_true")
    return parser.parse_args()


async def cmd_init(config):
    from web3_tools.wallet_manager import WalletManager
    n = int(os.getenv("NUM_WALLETS", "5"))
    wife_n = int(os.getenv("WIFE_NUM_WALLETS", str(n)))
    wife_mnemonic = os.getenv("WIFE_WALLET_MNEMONIC", "").strip()
    wm = WalletManager(config)
    wm.create_wallets(n)
    me_count = n
    wife_count = 0
    if wife_mnemonic:
        wm.create_wife_wallets(wife_n, wife_mnemonic)
        wife_count = wife_n
    wallets = wm.get_all_wallets()
    print(f"\n✅ 지갑 생성 완료 (본인 {me_count}개 + 와이프 {wife_count}개 = 총 {len(wallets)}개)")
    for w in wallets:
        label = f"W#{w.index}" if w.owner == "wife" else f"#{w.index}"
        print(f"  {label}: {w.address} ({w.owner})")
    print("\n⚠️  니모닉은 절대 공유하지 마세요!")
    print("⚠️  ADD- INFORMATION2: 각 지갑은 독립 IP(프록시)를 사용하세요!")


def _upsert_wife_mnemonic_to_env(mnemonic: str) -> bool:
    """WIFE_WALLET_MNEMONIC을 .env에 append/overwrite."""
    env_path = Path(".env")
    target_key = "WIFE_WALLET_MNEMONIC"
    new_line = f"{target_key}={mnemonic}"

    if not env_path.exists():
        env_path.write_text(new_line + "\n", encoding="utf-8")
        return True

    lines = env_path.read_text(encoding="utf-8").splitlines()
    key_index = -1
    for i, line in enumerate(lines):
        if line.startswith(f"{target_key}="):
            key_index = i
            break

    if key_index == -1:
        append_prefix = "\n" if lines and lines[-1].strip() else ""
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"{append_prefix}{new_line}\n")
        return True

    overwrite = input("WIFE_WALLET_MNEMONIC이 이미 있습니다. 덮어쓸까요? (y/n): ").strip().lower()
    if overwrite != "y":
        print("저장을 취소했습니다.")
        return False

    lines[key_index] = new_line
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


async def cmd_add_wife(config):
    from web3_tools.wallet_manager import WalletManager

    mnemonic = getpass.getpass("와이프 니모닉 입력 (입력 시 화면에 표시 안 됨): ").strip()
    if not mnemonic:
        print("니모닉이 비어 있습니다. 다시 시도하세요.")
        return

    try:
        acct = Account.from_mnemonic(mnemonic, account_path="m/44'/60'/0'/0/0")
    except Exception:
        print("유효하지 않은 니모닉입니다. MetaMask 비밀 복구 구문을 확인하세요.")
        return

    print(f"✅ 와이프 지갑 주소: {acct.address}")
    confirm = input("❓ MetaMask에서 보이는 주소와 일치합니까? (y/n): ").strip().lower()
    if confirm != "y":
        print("MetaMask 앱 → 설정 → 보안 → 비밀 복구 구문 확인 후 재시도하세요")
        return

    if not _upsert_wife_mnemonic_to_env(mnemonic):
        return

    wm = WalletManager(config)
    wm.add_wife_wallet(mnemonic)
    print("✅ 와이프 지갑 등록 완료!")


async def cmd_status(config):
    from web3_tools.wallet_manager import WalletManager
    from ai_engine.project_analyzer import ProjectAnalyzer
    from web3_tools.chain_configs import get_free_gas_chains

    wm = WalletManager(config)
    me_wallets = wm.get_wallets_by_owner("me")
    wife_wallets = wm.get_wallets_by_owner("wife")
    print(f"\n📊 Airdrop Farming Bot v2 상태")
    print(f"{'─' * 40}")
    print(f"💼 지갑 수: {wm.wallet_count()}개 (본인 {len(me_wallets)}개 + 와이프 {len(wife_wallets)}개)")
    if wife_wallets:
        print(f"  👤 본인: {', '.join(w.address[:10]+'...' for w in me_wallets)}")
        print(f"  💕 와이프: {', '.join(w.address[:10]+'...' for w in wife_wallets)}")

    analyzer = ProjectAnalyzer()
    top5 = analyzer.get_top_projects(5)
    print(f"\n🔥 추천 파밍 대상 상위 5:")
    for i, p in enumerate(top5):
        gas_str = "무료!" if p.get("gas_usd") == 0 else f"${p.get('gas_usd')}"
        print(
            f"  {i+1}. {p['name']} "
            f"(FDV ${p.get('fdv_usd', 0) / 1e9:.1f}B, "
            f"가스:{gas_str}, 긴급도:{p.get('urgency')})"
        )

    free = get_free_gas_chains()
    print(f"\n⛽ 무료 가스 체인: {', '.join(free)}")


def _get_project_actions_planned(project_name: str) -> list[str]:
    actions_map = {
        "megaeth": ["dex_swap", "nft_mint", "dapp_interact"],
        "unichain": ["bridge", "uniswap_v4_swap", "lp_add"],
        "ink": ["bridge", "aave_deposit", "aave_borrow"],
        "abstract": ["xp_earn", "badge_collect", "game_interact", "social_task"],
        "metamask": ["portfolio_swap"],
    }
    return actions_map.get(project_name.lower(), ["farm_action"])


def _build_dry_run_report(wallets, projects) -> dict:
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    project_reports = []
    total_gas = 0.0
    total_minutes = 0

    for project in projects:
        project.dry_run = True
        actions_planned = _get_project_actions_planned(project.name)
        wallet_count = len(wallets)
        estimated_gas_usd = float(getattr(project, "gas_usd", 0)) * wallet_count
        estimated_time_min = len(actions_planned) * wallet_count * 3
        project_reports.append(
            {
                "name": project.name,
                "actions_planned": actions_planned,
                "estimated_gas_usd": round(estimated_gas_usd, 2),
                "estimated_time_min": estimated_time_min,
                "wallet_count": wallet_count,
            }
        )
        total_gas += estimated_gas_usd
        total_minutes += estimated_time_min

    return {
        "timestamp": timestamp,
        "wallets": [w.address for w in wallets],
        "projects": project_reports,
        "total_estimated_gas_usd": round(total_gas, 2),
        "total_estimated_time_hours": round(total_minutes / 60, 2),
    }


async def cmd_run_once(config, notifier, dry_run: bool = False):
    from projects import get_active_projects
    from web3_tools.wallet_manager import WalletManager
    from anti_sybil.proxy_manager import ProxyManager
    from anti_sybil.behavior_simulator import BehaviorSimulator

    wm = WalletManager(config)
    wallets = wm.get_all_wallets()
    proxy_mgr = ProxyManager(config)
    behavior = BehaviorSimulator(config)

    projects = get_active_projects(config)
    if dry_run:
        report = _build_dry_run_report(wallets, projects)
        ts_for_file = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(f"logs/dryrun_{ts_for_file}.json")
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"\n🧪 DRY-RUN 리포트 — {len(projects)}개 프로젝트")
        for p in report["projects"]:
            print(
                f"  → {p['name']} | 액션:{len(p['actions_planned'])}개/지갑 "
                f"| 예상가스:${p['estimated_gas_usd']} | 예상시간:{p['estimated_time_min']}분"
            )
        print(f"\n총 예상 가스비: ${report['total_estimated_gas_usd']}")
        print(f"총 예상 시간: {report['total_estimated_time_hours']}시간")
        print(f"리포트 저장: {report_path}")
        return

    print(f"\n🌾 파밍 시작 — {len(projects)}개 프로젝트 × {len(wallets)}개 지갑")
    print(f"   시빌 방지: 지갑별 독립 프록시 + 랜덤 딜레이")

    for project in projects:
        print(f"\n  📦 {project.name} (긴급도: {project.urgency}, 가스: ${project.gas_usd})")
        project_success = 0
        project_total = len(wallets)

        for wallet in wallets:
            # ── 시빌 방지: 지갑 전용 프록시 (항상 같은 IP) ──
            proxy = await proxy_mgr.get_proxy_for_wallet(wallet.address)
            label = "W" if wallet.owner == "wife" else f"#{wallet.index}"
            proxy_str = proxy.get("host", "direct") if proxy else "direct"
            print(f"    💼 {label} {wallet.address[:10]}... → IP:{proxy_str}")

            try:
                result = await project.farm_single(wallet, proxy or {}, behavior)
                if result.get("success", False):
                    project_success += 1
                    print(f"       ✅ 성공")
                else:
                    print(f"       ⚠️  결과: {result}")
            except Exception as e:
                print(f"       ❌ 실패: {e}")
                logger.error(f"[Farm] {project.name} {label} 실패: {e}")

            # ── 시빌 방지: 지갑간 랜덤 딜레이 (30~120초) ──
            delay = random.randint(30, 120)
            print(f"       ⏳ {delay}초 대기...")
            await asyncio.sleep(delay)

        print(f"  📊 {project.name} 완료: {project_success}/{project_total}")
        await notifier.send(
            f"✅ {project.name} 완료: {project_success}/{project_total}개 지갑"
        )


async def cmd_scan(config):
    from scanner.project_scanner import ProjectScanner
    scanner = ProjectScanner(config)
    print("\n🔍 프로젝트 스캔 시작...")
    report = await scanner.run_full_scan()
    await scanner.close()
    print(f"\n기존 프로젝트: {report['existing_count']}개")
    print(f"신규 발견: {report['new_count']}개")
    print("\n⭐ 추천 상위 5:")
    for i, p in enumerate(report.get("recommended", [])[:5]):
        print(f"  {i+1}. {p.get('name', '?')} (점수: {p.get('score', 0):.1f})")


async def cmd_dashboard():
    try:
        import uvicorn
        from monitor.dashboard import app
        if app is None:
            print("❌ fastapi 미설치 — pip install fastapi uvicorn")
            return
        cfg = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(cfg)
        print("🌐 대시보드 시작: http://localhost:8080")
        await server.serve()
    except ImportError:
        print("❌ uvicorn 미설치 — pip install uvicorn")


async def main():
    args = parse_args()

    from core.config_manager import ConfigManager
    config = ConfigManager("config.yaml")

    from monitor.telegram_bot import TelegramNotifier
    notifier = TelegramNotifier(
        token=config.get("telegram.bot_token", ""),
        chat_id=config.get("telegram.chat_id", ""),
    )

    if args.init:
        await cmd_init(config)
    elif args.add_wife:
        await cmd_add_wife(config)
    elif args.status:
        await cmd_status(config)
    elif args.run:
        await cmd_run_once(config, notifier, dry_run=args.dry_run)
    elif args.scan:
        await cmd_scan(config)
    elif args.dashboard:
        await cmd_dashboard()
    elif args.check or args.chains or args.smart or args.fund:
        legacy_main = Path("legacy/main.py")
        if legacy_main.exists():
            import subprocess
            subprocess.run([sys.executable, str(legacy_main)] + sys.argv[1:])
        else:
            print("⚠️  레거시 모드 사용 불가: legacy/main.py 없음")
    else:
        print("🤖 Airdrop Farming Bot v2 시작!")
        print("   스케줄러 모드 — Ctrl+C로 종료")
        await notifier.send("🤖 Airdrop Farming Bot v2 시작되었습니다!")

        from core.scheduler import BotScheduler
        scheduler = BotScheduler(config, notifier)

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(scheduler.stop()))

        await scheduler.start()


if __name__ == "__main__":
    asyncio.run(main())
