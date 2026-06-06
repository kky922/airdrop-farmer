"""
scanner/project_scanner.py — 신규 에어드랍 프로젝트 탐색 오케스트레이터

ADD 지시서 #2:
- CoinGecko + AirdropBuzz + Twitter 통합 스캔
- scorer.py 기반 점수화 및 추천
- 주 1회 전면 스캔 (월요일 09:00)
"""
import logging
from typing import Optional

from scanner.sources.coingecko import CoinGeckoScanner
from scanner.sources.airdropbuzz import AirdropBuzzScanner
from scanner.sources.twitter import TwitterScanner
from scanner.scorer import ProjectScorer
from ai_engine.project_analyzer import KNOWN_PROJECTS

logger = logging.getLogger(__name__)


class ProjectScanner:
    def __init__(self, config=None):
        self.config = config
        self.coingecko = CoinGeckoScanner()
        self.airdropbuzz = AirdropBuzzScanner(config)
        self.twitter = TwitterScanner()
        self.scorer = ProjectScorer()

    async def check_existing_projects(self) -> list[dict]:
        """기존 파밍 대상 프로젝트 상장 여부 재확인."""
        results = []
        for project in KNOWN_PROJECTS:
            if project.get("listed"):
                results.append({**project, "status": "already_listed"})
                continue

            found = await self.coingecko.search_project(project["name"])
            status = "listed" if found else "still_unlisted"
            results.append({
                **project,
                "status": status,
                "note": "TGE 완료!" if status == "listed" else "아직 미상장 — 파밍 계속",
            })

        logger.info(
            f"[Scanner] 기존 프로젝트 체크: {len(results)}개 | "
            f"상장됨: {sum(1 for r in results if r['status'] == 'listed')}개"
        )
        return results

    async def discover_new_projects(self) -> list[dict]:
        """신규 에어드랍 프로젝트 발굴."""
        all_projects = []

        # CoinGecko Layer-2 스캔
        cg_projects = await self.coingecko.scan_layer2_projects()
        all_projects.extend(cg_projects)
        logger.info(f"[Scanner] CoinGecko: {len(cg_projects)}개")

        # AirdropBuzz 스크래핑
        ab_projects = await self.airdropbuzz.scan()
        if not ab_projects:
            ab_projects = await self.airdropbuzz.scan_airdrops_io()
        all_projects.extend(ab_projects)
        logger.info(f"[Scanner] AirdropBuzz: {len(ab_projects)}개")

        # Twitter 트렌드
        tw_results = await self.twitter.scan_all_keywords()
        # Twitter 결과를 프로젝트 형식으로 변환
        for tw in tw_results:
            all_projects.append({
                "name": "Twitter 트렌드",
                "source": "twitter",
                "text": tw.get("text", "")[:100],
                "credibility": tw.get("credibility_score", 0),
                "followers": tw.get("followers", 0),
            })

        # 중복 제거
        seen = set()
        unique = []
        for p in all_projects:
            key = p.get("name", "").lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(p)

        logger.info(f"[Scanner] 총 신규 프로젝트 {len(unique)}개 발견")
        return unique

    async def score_and_recommend(self, projects: list[dict]) -> list[dict]:
        """점수화 후 상위 10개 추천."""
        scored = self.scorer.rank(projects)
        top10 = scored[:10]
        logger.info(
            "[Scanner] 추천 프로젝트 상위 5:\n"
            + "\n".join(f"  {i+1}. {p.get('name')} (점수: {p.get('score', 0):.1f})"
                        for i, p in enumerate(top10[:5]))
        )
        return top10

    async def run_full_scan(self) -> dict:
        """전체 스캔 실행 (주 1회)."""
        logger.info("[Scanner] 주간 전체 스캔 시작")
        existing = await self.check_existing_projects()
        new_projects = await self.discover_new_projects()
        recommended = await self.score_and_recommend(new_projects)
        return {
            "existing_count": len(existing),
            "new_count": len(new_projects),
            "recommended": recommended,
            "existing": existing,
        }

    async def close(self):
        await self.coingecko.close()
