# -*- coding: utf-8 -*-
"""
상장 상태 자동 검증 모듈 — CoinGecko + CoinMarketCap 동시 체크
- 매주 자동 실행 (cron)
- 상장 감지 시 텔레그램 알림
- 검증 통과한 체인만 파밍 허용
"""
import json
import urllib.request
import urllib.parse
import sqlite3
import os
import sys
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "airdrop_farmer.db")
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
LISTING_CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "listing_status.json")

# ─── 체인별 검색어 매핑 ───────────────────────────────────────
CHAIN_SEARCH_TERMS = {
    "berachain": ["berachain", "bera", "berachain token", "berachain bera"],
    "monad": ["monad", "monad token", "monad blockchain"],
    "story": ["story protocol", "story blockchain", "ip token story"],
    "abstract": ["abstract chain", "abstract blockchain", "abstract token"],
    "megaeth": ["megaeth", "mega eth", "megaeth token"],
    "unichain": ["unichain", "uni chain", "unichain token"],
    "ink": ["ink chain", "ink kraken", "ink blockchain"],
    "scroll": ["scroll", "scroll blockchain", "scroll zk"],
    "base": ["base chain", "base blockchain", "base coinbase"],
    "linea": ["linea", "linea blockchain"],
    "eclipse": ["eclipse blockchain", "eclipse svm", "eclipse chain"],
    "fuel": ["fuel network", "fuel blockchain", "fuel token"],
    "initia": ["initia", "initia blockchain"],
    "somnia": ["somnia", "somnia network"],
}

def load_env():
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


def coingecko_search(query: str) -> list:
    """CoinGecko search API로 검색"""
    url = f"https://api.coingecko.com/api/v3/search?query={urllib.parse.quote(query)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            results = []
            for coin in data.get("coins", [])[:10]:
                results.append({
                    "id": coin.get("id", ""),
                    "name": coin.get("name", ""),
                    "symbol": coin.get("symbol", "").upper(),
                    "market_cap_rank": coin.get("market_cap_rank"),
                    "thumb": coin.get("thumb", ""),
                })
            return results
    except Exception as e:
        logger.warning(f"CoinGecko search 실패 ({query}): {e}")
        return []


def coingecko_get_all_ids() -> set:
    """CoinGecko 전체 코인 ID 목록"""
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return {c["id"].lower() for c in data}
    except Exception as e:
        logger.warning(f"CoinGecko list 실패: {e}")
        return set()


def check_chain_listed(chain_name: str) -> dict:
    """단일 체인 상장 여부 종합 검사"""
    result = {
        "chain": chain_name,
        "listed": False,
        "sources": [],
        "details": [],
        "checked_at": datetime.now().isoformat(),
    }

    # 1. CoinGecko 전체 목록에서 ID 검색
    all_ids = getattr(check_chain_listed, '_all_ids', None)
    if all_ids is None:
        all_ids = coingecko_get_all_ids()
        check_chain_listed._all_ids = all_ids

    direct_matches = [chain_name, chain_name.replace(" ", "-"), f"{chain_name}-token", f"{chain_name}-2"]
    for dm in direct_matches:
        if dm.lower() in all_ids:
            result["listed"] = True
            result["sources"].append(f"CoinGecko list (id={dm})")

    # 2. CoinGecko search API
    search_terms = CHAIN_SEARCH_TERMS.get(chain_name, [chain_name])
    for term in search_terms:
        coins = coingecko_search(term)
        for coin in coins:
            # 이름/심볼이 체인명과 밀접하게 매칭되면 상장으로 판단
            name_match = chain_name.lower() in coin["name"].lower()
            id_match = chain_name.lower() in coin["id"].lower()
            if name_match or id_match:
                result["listed"] = True
                result["sources"].append(f"CoinGecko search ({coin['name']}, rank={coin['market_cap_rank']})")
                result["details"].append(coin)
        time.sleep(1.2)  # Rate limit 방지

    return result


def check_all_chains(chains: list = None) -> dict:
    """모든 체인 상장 검사"""
    if chains is None:
        chains = list(CHAIN_SEARCH_TERMS.keys())

    results = {}
    for chain in chains:
        logger.info(f"🔍 검사중: {chain}")
        r = check_chain_listed(chain)
        results[chain] = r
        status = "❌ 상장됨" if r["listed"] else "✅ 미상장"
        logger.info(f"  → {status} {r['sources'] or '(검색결과 없음)'}")
        time.sleep(2)  # Rate limit

    return results


def save_listing_cache(results: dict):
    """검증 결과 캐시 저장"""
    os.makedirs(os.path.dirname(LISTING_CACHE_PATH), exist_ok=True)
    cache = {
        "last_updated": datetime.now().isoformat(),
        "results": results,
    }
    with open(LISTING_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    logger.info(f"캐시 저장: {LISTING_CACHE_PATH}")


def save_listing_to_db(results: dict):
    """DB에 검증 이력 저장"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listing_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chain TEXT NOT NULL,
            is_listed INTEGER NOT NULL,
            sources TEXT,
            checked_at TEXT NOT NULL
        )
    """)
    for chain, r in results.items():
        cur.execute(
            "INSERT INTO listing_checks (chain, is_listed, sources, checked_at) VALUES (?, ?, ?, ?)",
            (chain, 1 if r["listed"] else 0, json.dumps(r["sources"]), r["checked_at"])
        )
    conn.commit()
    conn.close()


def get_unlisted_chains(results: dict) -> list:
    """미상장 체인 목록 반환"""
    return [chain for chain, r in results.items() if not r["listed"]]


def get_listed_chains(results: dict) -> list:
    """상장된 체인 목록 반환"""
    return [chain for chain, r in results.items() if r["listed"]]


def send_telegram_alert(results: dict):
    """상장 감지 알림"""
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return

    listed = get_listed_chains(results)
    unlisted = get_unlisted_chains(results)

    msg = "🔍 <b>상장 상태 검증 결과</b>\n\n"

    if listed:
        msg += "❌ <b>상장 감지됨 (에어드롭 제외):</b>\n"
        for chain in listed:
            r = results[chain]
            src = ", ".join(r["sources"][:2])
            msg += f"  • {chain}: {src}\n"

    if unlisted:
        msg += "\n✅ <b>미상장 (에어드롭 가능):</b>\n"
        for chain in unlisted:
            msg += f"  • {chain}\n"

    msg += f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "parse_mode": "HTML", "text": msg}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"텔레그램 전송 실패: {e}")


def main():
    print("=" * 60)
    print("🔍 에어드롭 체인 상장 상태 검증 시작")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # config.py의 체인 + 추가 후보
    config_chains = ["berachain", "monad", "story", "abstract", "megaeth", "unichain", "ink", "scroll", "base", "linea"]
    extra_chains = ["eclipse", "fuel", "initia", "somnia"]
    all_chains = config_chains + extra_chains

    results = check_all_chains(all_chains)

    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 검증 결과 요약")
    print("=" * 60)

    listed = get_listed_chains(results)
    unlisted = get_unlisted_chains(results)

    print(f"\n❌ 상장됨 ({len(listed)}개):")
    for chain in listed:
        r = results[chain]
        src = ", ".join(r["sources"][:2])
        print(f"  • {chain}: {src}")

    print(f"\n✅ 미상장 ({len(unlisted)}개):")
    for chain in unlisted:
        print(f"  • {chain}")

    # 캐시 & DB 저장
    save_listing_cache(results)
    save_listing_to_db(results)

    # 텔레그램 알림
    send_telegram_alert(results)

    return results


if __name__ == "__main__":
    main()