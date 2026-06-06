# -*- coding: utf-8 -*-
"""
매일 오전 9시 진행률 리포트 — DB 조회 → 텔레그램 전송
cron 독립 실행 + 스케줄러에서도 호출 가능
"""
import sqlite3
import json
import urllib.request
import os
import sys
from datetime import datetime

# ─── 설정 ──────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "airdrop_farmer.db")
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

def load_env():
    """간단 .env 로더"""
    env = {}
    if not os.path.exists(ENV_PATH):
        return env
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip()
    return env


def get_progress_data():
    """DB에서 진행률 데이터 조회"""
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    data = {
        "chains": {},
        "wallets": {},
        "total_success": 0,
        "total_failed": 0,
        "total_tx": 0,
        "first_date": None,
        "last_date": None,
    }

    # 체인별/활동별 요약
    cur.execute("""
        SELECT chain, activity_type, 
               COUNT(*) as cnt,
               SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
               SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
        FROM activities 
        GROUP BY chain, activity_type 
        ORDER BY chain, activity_type
    """)
    for row in cur.fetchall():
        cn = row["chain"]
        if cn not in data["chains"]:
            data["chains"][cn] = {"activities": {}, "success": 0, "failed": 0, "total": 0}
        data["chains"][cn]["activities"][row["activity_type"]] = {
            "total": row["cnt"],
            "success": row["success"],
            "failed": row["failed"],
        }
        data["chains"][cn]["success"] += row["success"]
        data["chains"][cn]["failed"] += row["failed"]
        data["chains"][cn]["total"] += row["cnt"]
        data["total_success"] += row["success"]
        data["total_failed"] += row["failed"]
        data["total_tx"] += row["cnt"]

    # 지갑별 요약
    cur.execute("""
        SELECT wallet_index, chain,
               COUNT(*) as cnt,
               SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success
        FROM activities 
        GROUP BY wallet_index, chain
        ORDER BY wallet_index
    """)
    for row in cur.fetchall():
        wi = row["wallet_index"]
        if wi not in data["wallets"]:
            data["wallets"][wi] = {"success": 0, "total": 0, "chains": []}
        data["wallets"][wi]["success"] += row["success"]
        data["wallets"][wi]["total"] += row["cnt"]
        if row["chain"] not in data["wallets"][wi]["chains"]:
            data["wallets"][wi]["chains"].append(row["chain"])

    # 활동 기간
    cur.execute("SELECT MIN(created_at), MAX(created_at) FROM activities")
    row = cur.fetchone()
    data["first_date"] = row[0]
    data["last_date"] = row[1]

    # 활동 일수
    cur.execute("SELECT COUNT(DISTINCT DATE(created_at)) as days FROM activities")
    data["active_days"] = cur.fetchone()[0]

    conn.close()
    return data


def build_report(data: dict) -> str:
    """텔레그램 메시지 생성"""
    if not data or not data["chains"]:
        return "📊 아직 활동 데이터가 없습니다."

    now = datetime.now()
    date_str = now.strftime("%Y년 %m월 %d일 %H:%M")

    # 자격 요건 기준
    min_tx = 10
    min_days = 5

    msg = f"📊 <b>에어드롭 파밍 진행률 리포트</b>\n"
    msg += f"⏰ 기준: {date_str}\n\n"

    # ─── 전체 현황 ───
    msg += f"<b>📈 전체 현황</b>\n"
    msg += f"• 총 성공: {data['total_success']}건\n"
    msg += f"• 총 실패: {data['total_failed']}건\n"
    msg += f"• 활동 일수: {data['active_days']}/{min_days}일\n"
    msg += f"• 활동 체인: {len(data['chains'])}개\n\n"

    # ─── 체인별 진행률 ───
    tier_map = {
        "monad": "🟢S", "berachain": "🟢S", "story": "🟢S",
        "abstract": "🟡A", "megaeth": "🟡A", "unichain": "🟡A", "ink": "🟡A",
        "scroll": "🔵B", "base": "🔵B", "linea": "🔵B",
    }
    testnet_chains = {"monad", "megaeth"}

    msg += f"<b>🔗 체인별 현황</b>\n"
    for cn, info in data["chains"].items():
        tier = tier_map.get(cn, "⚪?")
        net = "🆓" if cn in testnet_chains else "💰"
        bar_len = 10
        filled = min(int(info["success"] / min_tx * bar_len), bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        pct = min(int(info["success"] / min_tx * 100), 100)
        msg += f"  {tier} {cn} ({net}): {info['success']}건 {bar} {pct}%\n"

    # 아직 시작 안한 체인
    all_chains = ["monad", "berachain", "story", "abstract", "megaeth", "unichain", "ink", "scroll", "base", "linea"]
    inactive = [c for c in all_chains if c not in data["chains"]]
    if inactive:
        msg += f"\n<b>⬜ 미시작 체인</b>\n"
        for cn in inactive:
            tier = tier_map.get(cn, "⚪?")
            net = "🆓" if cn in testnet_chains else "💰"
            msg += f"  {tier} {cn} ({net}): 대기중\n"

    # ─── 지갑별 현황 ───
    msg += f"\n<b>👛 지갑별 현황</b>\n"
    for wi, info in sorted(data["wallets"].items()):
        bar_len = 10
        filled = min(int(info["success"] / min_tx * bar_len), bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        pct = min(int(info["success"] / min_tx * 100), 100)
        chains_str = ", ".join(info["chains"])
        msg += f"  #{wi}: {info['success']}건 {bar} {pct}% ({chains_str})\n"

    # ─── 자격 달성률 ───
    best_wallet = max(data["wallets"].values(), key=lambda x: x["success"]) if data["wallets"] else None
    if best_wallet:
        tx_pct = min(int(best_wallet["success"] / min_tx * 100), 100)
        day_pct = min(int(data["active_days"] / min_days * 100), 100)
        msg += f"\n<b>🎯 자격 달성률 (최고 지갑 기준)</b>\n"
        msg += f"  트랜잭션: {best_wallet['success']}/{min_tx}건 ({tx_pct}%)\n"
        msg += f"  활동일수: {data['active_days']}/{min_days}일 ({day_pct}%)\n"

        # 예상 완료일
        if data["active_days"] > 0:
            avg_tx_per_day = best_wallet["success"] / data["active_days"]
            if avg_tx_per_day > 0:
                remaining_tx = max(0, min_tx - best_wallet["success"])
                days_to_complete = remaining_tx / avg_tx_per_day if avg_tx_per_day > 0 else 0
                remaining_days = max(0, min_days - data["active_days"])
                total_remaining = max(days_to_complete, remaining_days)
                est_date = now.strftime("%m월 %d일")
                msg += f"  예상 완료: 약 {int(total_remaining)}일 후\n"

    msg += f"\n💡 8시간마다 자동 활동 진행 중"
    return msg


def send_telegram(msg: str, token: str, chat_id: str) -> bool:
    """텔레그램 메시지 전송"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "parse_mode": "HTML",
        "text": msg,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")
        return False


def main():
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 없습니다.")
        sys.exit(1)

    data = get_progress_data()
    if not data:
        print("DB 데이터 없음")
        sys.exit(1)

    msg = build_report(data)
    print(msg.replace("<b>", "**").replace("</b>", "**"))

    ok = send_telegram(msg, token, chat_id)
    if ok:
        print("\n✅ 텔레그램 전송 성공")
    else:
        print("\n❌ 텔레그램 전송 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()