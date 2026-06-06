"""
monitor/telegram_bot.py — TelegramNotifier (aiohttp 기반)

ADD 설계서 3-8 기반. 실시간 알림 전용.
대화형 명령어 봇은 legacy/telegram_bot.py (AirdropTelegramBot) 유지.
"""
import logging
from datetime import datetime
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self._base = f"https://api.telegram.org/bot{token}"
        self._timeout = aiohttp.ClientTimeout(total=15)

    async def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """메시지 전송."""
        if not self.token or not self.chat_id:
            logger.warning("[Telegram] 토큰/chat_id 미설정")
            return False
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(
                    f"{self._base}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": parse_mode,
                    },
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"[Telegram] 전송 실패: {resp.status}")
                        return False
                    return True
        except Exception as e:
            logger.error(f"[Telegram] 오류: {e}")
            return False

    async def send_daily_report(self, results: dict):
        """일별 파밍 리포트."""
        msg = (
            f"📊 <b>일별 파밍 리포트</b>\n"
            f"{'─' * 25}\n"
            f"📅 날짜: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"✅ 성공: {results.get('success', 0)}개\n"
            f"❌ 실패: {results.get('failed', 0)}개\n"
            f"⛽ 총 가스비: ${results.get('gas_cost', 0):.2f}\n"
            f"💰 예상 수익: ${results.get('expected_value', 0):,.0f}\n"
        )
        await self.send(msg)

    async def send_weekly_report(self, report: dict):
        """주간 프로젝트 스캔 리포트."""
        new_projects = report.get("recommended", [])
        top_list = "\n".join([
            f"  {i + 1}. {p.get('name', '?')} (점수: {p.get('score', 0):.1f})"
            for i, p in enumerate(new_projects[:5])
        ])
        msg = (
            f"📊 <b>주간 프로젝트 스캔 리포트</b>\n"
            f"{'─' * 25}\n"
            f"🔄 기존 프로젝트: {report.get('existing_count', 0)}개 체크\n"
            f"🆕 신규 발견: {report.get('new_count', 0)}개\n"
            f"\n⭐ 추천 신규 프로젝트:\n{top_list}\n"
        )
        await self.send(msg)

    async def send_claim_alert(self, claims: list):
        """클레임 가능 알림."""
        claim_list = "\n".join([f"  • {c}" for c in claims])
        msg = (
            f"🎁 <b>클레임 가능한 에어드랍 발견!</b>\n"
            f"{'─' * 25}\n"
            f"{claim_list}\n\n"
            f"⚡ 포털에서 직접 클레임하세요!"
        )
        await self.send(msg)

    async def send_gas_alert(self, gwei: float):
        """저가스 알림."""
        await self.send(
            f"⛽ <b>가스비 낮음 감지!</b>\n"
            f"현재: {gwei:.1f} Gwei\n"
            f"지금 TX 실행 권장!"
        )

    async def send_farming_result(self, project_name: str, wallet_address: str,
                                  owner: str, result: dict):
        """지갑별 파밍 결과 실시간 알림."""
        status_emoji = "✅" if result.get("success") else "❌"
        owner_label = "👨 나" if owner == "me" else "👩 와이프"
        addr_short = wallet_address[:10] + "..."

        actions = result.get("actions", [])
        tx_hashes = result.get("tx_hashes", [])
        error = result.get("error", "")

        action_count = len(actions) if actions else 0
        tx_count = len(tx_hashes) if tx_hashes else 0

        msg = (
            f"{status_emoji} <b>파밍 결과</b>\n"
            f"{'─' * 25}\n"
            f"📦 프로젝트: {project_name}\n"
            f"{owner_label} | {addr_short}\n"
            f"🎯 액션: {action_count}개 | TX: {tx_count}개\n"
        )
        if error:
            msg += f"⚠️ 오류: {error[:150]}\n"
        if tx_hashes:
            msg += f"🔗 TX: <code>{tx_hashes[0][:20]}...</code>\n"

        await self.send(msg)

    async def send_daily_summary(self, db_summary: dict):
        """DB 기반 일일 파밍 요약 (me + wife 통합)."""
        date = db_summary.get("date", "?")
        projects = db_summary.get("projects", {})
        total_ok = db_summary.get("total_success", 0)
        total_fail = db_summary.get("total_failed", 0)

        msg = (
            f"📊 <b>일일 파밍 요약</b>\n"
            f"{'─' * 25}\n"
            f"📅 {date}\n"
            f"✅ 성공: {total_ok} | ❌ 실패: {total_fail}\n"
            f"{'─' * 25}\n"
        )

        for proj, owners in projects.items():
            msg += f"\n📁 <b>{proj}</b>\n"
            for owner, stats in owners.items():
                label = "👨" if owner == "me" else "👩"
                ok = stats.get("success", 0)
                fail = stats.get("failed", 0)
                gas = stats.get("gas", 0.0)
                msg += f"  {label} ✅{ok} ❌{fail} ⛽${gas:.2f}\n"

        await self.send(msg)

    async def send_project_progress(self, project_name: str, completed: int,
                                    total: int, success: int, failed: int):
        """프로젝트별 진행 상황 (파밍 도중)."""
        bar_len = 20
        filled = int(bar_len * completed / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        pct = (completed / total * 100) if total > 0 else 0

        msg = (
            f"🔄 <b>{project_name}</b> 진행 중\n"
            f"<code>[{bar}]</code> {pct:.0f}%\n"
            f"✅ {success} | ❌ {failed} | 📋 {completed}/{total}\n"
        )
        await self.send(msg)

    async def send_proxy_status(self, health: dict):
        """프록시 헬스체크 결과 알림."""
        lines = [
            f"🌐 <b>프록시 헬스체크</b>",
            f"{'─' * 25}",
            f"✅ 정상: {health.get('healthy', 0)}개",
            f"❌ 불량: {health.get('unhealthy', 0)}개",
        ]
        for detail in health.get("details", []):
            lines.append(f"  {detail['status']} {detail['proxy']}")
        await self.send("\n".join(lines))

    async def send_retry_queue(self, queue: list):
        """재시도 큐 상태 알림."""
        if not queue:
            return
        lines = [
            f"🔄 <b>재시도 큐</b> ({len(queue)}개)",
            f"{'─' * 25}",
        ]
        for item in queue[:10]:  # 최대 10개까지만 표시
            proj = item.get("project", "?")
            owner = "W" if item.get("wallet_owner") == "wife" else f"#{item.get('wallet_index', '?')}"
            err = item.get("error", "")[:50]
            lines.append(f"  📦 {proj} | 💼 {owner} | ⚠️ {err}")
        await self.send("\n".join(lines))

    async def send_error(self, module: str, error: str):
        """에러 알림."""
        await self.send(
            f"🚨 <b>오류 발생</b>\n"
            f"모듈: {module}\n"
            f"오류: {error[:200]}"
        )
