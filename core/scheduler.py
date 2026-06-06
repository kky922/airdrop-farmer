"""
core/scheduler.py — APScheduler 기반 작업 스케줄러 (v3)

v3 개선:
- ProfitAnalyzer 연동: 파밍 시 가스비 자동 기록
- 자동 프로젝트 관리: 주간 스캔 후 auto_manage_projects()
- 시빌 방지: 프로젝트/지갑 순서 셔플
- 재시도 큐: 실패한 조합 다음 실행시 우선 재시도
"""
import asyncio
import json
import logging
import random
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False
    logger.warning("[Scheduler] APScheduler 미설치")


class BotScheduler:
    def __init__(self, config, notifier):
        self.config = config
        self.notifier = notifier
        self._scheduler = None
        self._running = False

        if _HAS_APSCHEDULER:
            self._scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
            self._setup_jobs()

    def _setup_jobs(self):
        if not self._scheduler:
            return

        # 일별 파밍 (새벽 2~4시 랜덤)
        self._scheduler.add_job(
            self._farming_job,
            CronTrigger(hour="2-4", minute=str(random.randint(0, 59))),
            id="daily_farming",
            name="일별 에어드랍 파밍",
            misfire_grace_time=3600,
        )

        # 주별 전면 스캔 (월요일 09:00)
        self._scheduler.add_job(
            self._weekly_scan_job,
            CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="weekly_scan",
            name="주별 프로젝트 전면 스캔",
        )

        # 가스비 모니터링 (6시간마다)
        self._scheduler.add_job(
            self._gas_monitor_job,
            IntervalTrigger(hours=6),
            id="gas_monitor",
            name="가스비 모니터링",
        )

        # 클레임 체크 (1시간마다)
        self._scheduler.add_job(
            self._claim_check_job,
            IntervalTrigger(hours=1),
            id="claim_checker",
            name="클레임 체크",
        )

        logger.info("✅ 모든 스케줄 작업 등록 완료")

    async def start(self):
        """스케줄러 시작 및 무한 대기."""
        self._running = True
        if self._scheduler:
            self._scheduler.start()
            logger.info("🚀 스케줄러 시작!")
            await self.notifier.send("📅 스케줄러가 시작되었습니다.")
        else:
            logger.warning("[Scheduler] APScheduler 없음 — 수동 실행만 가능")
            await self.notifier.send("⚠️ APScheduler 미설치 — pip install APScheduler 실행 필요")

        try:
            while self._running:
                await asyncio.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            await self.stop()

    async def stop(self):
        self._running = False
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
        logger.info("[Scheduler] 종료")

    async def _farming_job(self):
        """
        일별 파밍 실행 (v3) — 지갑별 farm_single() 방식.
        개선: ProfitAnalyzer 기록, 프로젝트/지갑 셔플, 재시도 큐.
        """
        logger.info("🌾 일별 파밍 시작")
        await self.notifier.send("🌾 오늘의 에어드랍 파밍을 시작합니다!")
        try:
            from projects import get_active_projects
            from web3_tools.wallet_manager import WalletManager
            from anti_sybil.proxy_manager import ProxyManager
            from anti_sybil.behavior_simulator import BehaviorSimulator
            from core.profit_analyzer import ProfitAnalyzer

            wallet_mgr = WalletManager(self.config)
            wallets = wallet_mgr.get_all_wallets()
            proxy_mgr = ProxyManager(self.config)
            behavior = BehaviorSimulator(self.config)
            profit = ProfitAnalyzer(self.config)

            active_projects = get_active_projects(self.config)

            # ── 파밍 전 프록시 헬스체크 ──
            health = await proxy_mgr.pre_farming_check()
            if health.get("unhealthy", 0) > 0:
                await self.notifier.send_proxy_status(health)

            # ── 시빌 방지: 프로젝트 & 지갑 순서 셔플 ──
            random.shuffle(active_projects)
            shuffled_wallets = wallets.copy()
            random.shuffle(shuffled_wallets)

            # ── 재시도 큐 로드 ──
            retry_queue = self._load_retry_queue()

            MAX_RETRIES = 3
            all_results = []
            new_retry_queue = []

            # 재시도 큐 우선 실행
            if retry_queue:
                logger.info(f"🔄 재시도 큐: {len(retry_queue)}개 항목")
                await self.notifier.send(f"🔄 재시도 큐 {len(retry_queue)}개 실행 중...")

            for project in active_projects:
                project_success = 0
                project_total = len(shuffled_wallets)
                logger.info(f"📦 {project.name} 시작 (지갑 {project_total}개)")

                for wallet in shuffled_wallets:
                    proxy = await proxy_mgr.get_proxy_for_wallet(wallet.address)
                    label = "W" if wallet.owner == "wife" else f"#{wallet.index}"

                    # ── 에러 재시도 로직 ──
                    result = None
                    for attempt in range(1, MAX_RETRIES + 1):
                        try:
                            result = await project.farm_single(
                                wallet, proxy or {}, behavior
                            )
                            if result.get("success"):
                                break
                        except Exception as e:
                            logger.warning(
                                f"[Farm] {project.name} {label} "
                                f"시도 {attempt}/{MAX_RETRIES} 실패: {e}"
                            )
                            if attempt < MAX_RETRIES:
                                wait = random.randint(60, 180)
                                logger.info(f"   ↻ {wait}초 후 재시도...")
                                await asyncio.sleep(wait)
                            result = {"success": False, "error": str(e)}

                    all_results.append(result or {"success": False})
                    is_success = result and result.get("success")
                    if is_success:
                        project_success += 1
                    else:
                        # 실패 시 재시도 큐에 추가
                        new_retry_queue.append({
                            "project": project.name,
                            "wallet_index": wallet.index,
                            "wallet_owner": wallet.owner,
                            "error": (result or {}).get("error", "unknown"),
                            "queued_at": datetime.now().isoformat(),
                        })

                    # ── ProfitAnalyzer: 가스비 기록 ──
                    gas_cost = (result or {}).get("gas_cost_usd", project.gas_usd * 0.1)
                    tx_count = len((result or {}).get("tx_hashes", []))
                    profit.record_farming_cost(
                        project.name, wallet.address,
                        gas_cost_usd=gas_cost,
                        tx_count=tx_count,
                        success=is_success,
                    )

                    # ── 지갑간 랜덤 딜레이 (30~120초) ──
                    delay = random.randint(30, 120)
                    logger.info(
                        f"  💼 {label} 완료 → {delay}초 대기 "
                        f"({project_success}/{project_total})"
                    )
                    await asyncio.sleep(delay)

                logger.info(f"✅ {project.name} 완료: {project_success}/{project_total}")
                await self.notifier.send(
                    f"✅ {project.name}: {project_success}/{project_total}개 지갑 성공"
                )

            # 재시도 큐 저장
            self._save_retry_queue(new_retry_queue)

            # 일별 리포트
            total_success = sum(1 for r in all_results if r.get("success"))
            total_all = len(all_results)
            await self.notifier.send_daily_report({
                "success": total_success,
                "failed": total_all - total_success,
                "projects": len(active_projects),
                "wallets": len(shuffled_wallets),
            })

            # 수익 분석 리포트 전송
            await self.notifier.send(profit.get_summary_text())

            logger.info(
                f"📊 일별 파밍 완료: {total_success}/{total_all} 성공 "
                f"({len(active_projects)}개 프로젝트)"
            )

        except Exception as e:
            logger.error(f"[Scheduler] 파밍 잡 실패: {e}")
            await self.notifier.send_error("farming_job", str(e))

    # ── 재시도 큐 ──
    _RETRY_FILE = "data/retry_queue.json"

    def _load_retry_queue(self) -> list:
        path = Path(self._RETRY_FILE)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return []

    def _save_retry_queue(self, queue: list):
        import os
        os.makedirs("data", exist_ok=True)
        Path(self._RETRY_FILE).write_text(
            json.dumps(queue, indent=2, ensure_ascii=False)
        )

    async def _weekly_scan_job(self):
        """주별 전면 스캔 + 자동 프로젝트 관리."""
        logger.info("🔍 주별 프로젝트 스캔 시작")
        await self.notifier.send("🔍 주간 프로젝트 전면 스캔을 시작합니다!")
        try:
            from scanner.project_scanner import ProjectScanner
            from projects import auto_manage_projects, update_project_from_scan
            from core.profit_analyzer import ProfitAnalyzer

            scanner = ProjectScanner(self.config)
            report = await scanner.run_full_scan()
            await scanner.close()
            await self.notifier.send_weekly_report(report)

            # 스캔 결과로 프로젝트 상태 업데이트
            for proj in report.get("recommended", []):
                update_project_from_scan(
                    proj.get("name", "?"),
                    proj.get("score", 0),
                    metadata=proj.get("metadata", {}),
                )
                # 수익 분석에 예상 가치 업데이트
                profit = ProfitAnalyzer(self.config)
                est = proj.get("metadata", {}).get("estimated_value_usd", 0)
                if est > 0:
                    profit.set_estimated_value(proj.get("name", "?"), est)

            # 자동 프로젝트 관리 (활성화/비활성화/만료)
            mgmt_result = auto_manage_projects(self.config)
            if any(mgmt_result.values()):
                msg = (
                    f"🔄 <b>자동 프로젝트 관리 결과</b>\n"
                    f"{'─' * 25}\n"
                )
                if mgmt_result["activated"]:
                    msg += f"🟢 활성화: {', '.join(mgmt_result['activated'])}\n"
                if mgmt_result["deactivated"]:
                    msg += f"🟡 비활성화: {', '.join(mgmt_result['deactivated'])}\n"
                if mgmt_result["expired"]:
                    msg += f"🔴 만료: {', '.join(mgmt_result['expired'])}\n"
                await self.notifier.send(msg)

            # 수익 리포트도 함께 전송
            profit = ProfitAnalyzer(self.config)
            await self.notifier.send(profit.get_summary_text())

        except Exception as e:
            logger.error(f"[Scheduler] 주간 스캔 실패: {e}")

    async def _gas_monitor_job(self):
        """가스비 모니터링."""
        try:
            from web3_tools.gas_optimizer import GasOptimizer, LOW_GAS_THRESHOLD
            optimizer = GasOptimizer(self.config)
            stats = optimizer.get_gas_stats()
            current = stats.get("current", 0)
            if current > 0 and current <= LOW_GAS_THRESHOLD:
                await self.notifier.send_gas_alert(current)
        except Exception as e:
            logger.warning(f"[Scheduler] 가스 모니터링 실패: {e}")

    async def _claim_check_job(self):
        """클레임 체크."""
        try:
            from web3_tools.wallet_manager import WalletManager
            wm = WalletManager(self.config)
            claims = await wm.check_all_claims()
            if claims:
                await self.notifier.send_claim_alert(claims)
        except Exception as e:
            logger.warning(f"[Scheduler] 클레임 체크 실패: {e}")
