"""
scanner/sources/twitter.py — Twitter/X API v2 모니터링

키워드: "airdrop", "TGE", "token launch"
팔로워 10만+ 계정 필터링, 신뢰도 점수 계산.
TWITTER_BEARER_TOKEN 환경변수 필요.
"""
import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

TWITTER_API_BASE = "https://api.twitter.com/2"
SEARCH_KEYWORDS = ["airdrop TGE", "token launch airdrop", "snapshot airdrop", "claim token"]
MIN_FOLLOWERS = 100_000


class TwitterScanner:
    def __init__(self):
        self._token = os.getenv("TWITTER_BEARER_TOKEN", "")
        if not self._token:
            logger.warning("[Twitter] TWITTER_BEARER_TOKEN 없음 — Twitter 스캔 비활성화")

    async def search_recent(self, query: str, max_results: int = 20) -> list[dict]:
        """Twitter API v2 최근 트윗 검색."""
        if not self._token:
            return []
        try:
            headers = {"Authorization": f"Bearer {self._token}"}
            params = {
                "query": f"{query} -is:retweet lang:en",
                "max_results": min(max_results, 100),
                "tweet.fields": "author_id,created_at,public_metrics",
                "expansions": "author_id",
                "user.fields": "public_metrics,username",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{TWITTER_API_BASE}/tweets/search/recent",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"[Twitter] API {resp.status}")
                        return []
                    data = await resp.json()
                    return self._parse_tweets(data)
        except Exception as e:
            logger.error(f"[Twitter] 검색 실패: {e}")
            return []

    def _parse_tweets(self, data: dict) -> list[dict]:
        tweets = data.get("data", [])
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

        results = []
        for tweet in tweets:
            user = users.get(tweet.get("author_id", ""), {})
            followers = user.get("public_metrics", {}).get("followers_count", 0)

            # 팔로워 10만+ 필터
            if followers < MIN_FOLLOWERS:
                continue

            results.append({
                "text": tweet.get("text", ""),
                "author": user.get("username", "unknown"),
                "followers": followers,
                "created_at": tweet.get("created_at"),
                "source": "twitter",
                "credibility_score": self._calc_credibility(followers, tweet),
            })
        return results

    def _calc_credibility(self, followers: int, tweet: dict) -> float:
        """신뢰도 점수 계산 (0~10)."""
        score = 0.0
        # 팔로워 기반
        if followers >= 1_000_000:
            score += 5
        elif followers >= 500_000:
            score += 4
        elif followers >= 100_000:
            score += 3

        # 인게이지먼트
        metrics = tweet.get("public_metrics", {})
        likes = metrics.get("like_count", 0)
        rt = metrics.get("retweet_count", 0)
        if likes + rt > 1000:
            score += 3
        elif likes + rt > 100:
            score += 1.5

        return min(10.0, score)

    async def scan_all_keywords(self) -> list[dict]:
        """모든 키워드 스캔 후 중복 제거."""
        if not self._token:
            return []

        all_results = []
        seen = set()
        for kw in SEARCH_KEYWORDS:
            results = await self.search_recent(kw, max_results=10)
            for r in results:
                key = r.get("text", "")[:50]
                if key not in seen:
                    seen.add(key)
                    all_results.append(r)
        return all_results
