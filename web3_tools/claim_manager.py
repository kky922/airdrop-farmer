"""
web3/claim_manager.py — 에어드랍 클레임 자동화

ADD 지시서 #4 — 지원 프로젝트:
- MegaETH (MEGA): TGE 2025-11 완료, 배포 진행 중
- Taiko (TKO): trailblazers.taiko.xyz
- Linea (LINEA): 공식 클레임 컨트랙트
추가 프로젝트는 CLAIM_CONTRACTS에서 관리.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 클레임 컨트랙트 주소 관리 (주소 확정 시 업데이트)
CLAIM_CONTRACTS: dict[str, dict] = {
    "megaeth": {
        "symbol": "MEGA",
        "chain_id": 6342,
        "contract": "",  # 확정 후 업데이트
        "portal_url": "https://megaeth.com",
        "status": "distributing",  # TGE 완료, 배포 진행 중
    },
    "taiko": {
        "symbol": "TKO",
        "chain_id": 167000,
        "contract": "",
        "portal_url": "https://trailblazers.taiko.xyz",
        "status": "active",
    },
    "linea": {
        "symbol": "LINEA",
        "chain_id": 59144,
        "contract": "",
        "portal_url": "https://linea.build/claim",
        "status": "pending",
    },
}


class ClaimManager:
    def __init__(self, config=None):
        self.config = config
        self._contracts = CLAIM_CONTRACTS.copy()

    async def check_claimable(self, wallet_address: str) -> list[str]:
        """
        지갑의 클레임 가능 에어드랍 확인.
        현재는 온체인 조회 미구현 — 각 프로젝트 포털 URL 안내.
        """
        claimable = []
        for project, info in self._contracts.items():
            if info["status"] in ("active", "distributing"):
                claimable.append(
                    f"{info['symbol']} ({project}): {info['portal_url']}"
                )
        return claimable

    async def claim_token(
        self,
        project_name: str,
        wallet,
        w3=None,
    ) -> dict:
        """
        에어드랍 클레임 실행.
        컨트랙트 주소 미확정 시 포털 URL 안내로 대체.
        """
        info = self._contracts.get(project_name.lower())
        if not info:
            return {"success": False, "reason": f"미지원 프로젝트: {project_name}"}

        if not info.get("contract"):
            logger.info(
                f"[ClaimManager] {project_name} 클레임 컨트랙트 미확정 "
                f"→ 포털 수동 클레임: {info['portal_url']}"
            )
            return {
                "success": False,
                "manual_required": True,
                "portal_url": info["portal_url"],
                "reason": "컨트랙트 주소 미확정 — 포털에서 직접 클레임 필요",
            }

        # TODO: 컨트랙트 주소 확정 후 실제 TX 구현
        return {"success": False, "reason": "구현 예정"}

    def add_contract(self, project_name: str, info: dict):
        """새 클레임 컨트랙트 추가."""
        self._contracts[project_name.lower()] = info
        logger.info(f"[ClaimManager] 클레임 컨트랙트 추가: {project_name}")

    def get_active_claims(self) -> dict:
        return {k: v for k, v in self._contracts.items() if v["status"] == "active"}
