"""
projects/__init__.py — 활성 프로젝트 레지스트리 + 자동 관리

v2: 주간 스캔 결과에 따라 자동 활성화/비활성화 지원
"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from projects.megaeth import MegaETHProject
from projects.unichain import UnichainProject
from projects.abstract import AbstractProject
from projects.metamask import MetaMaskProject
from projects.ink import InkProject

logger = logging.getLogger(__name__)

_REGISTRY = {
    "MegaETH": MegaETHProject,
    "Unichain": UnichainProject,
    "Abstract": AbstractProject,
    "MetaMask": MetaMaskProject,
    "Ink": InkProject,
}

_PROJECT_STATE_FILE = "data/project_state.json"


def _load_project_state() -> dict:
    """프로젝트 상태 파일 로드 (마지막 활동일, 스캔 점수 등)."""
    path = Path(_PROJECT_STATE_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"projects": {}, "last_scan": None}


def _save_project_state(state: dict):
    """프로젝트 상태 파일 저장."""
    os.makedirs("data", exist_ok=True)
    path = Path(_PROJECT_STATE_FILE)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def update_project_from_scan(project_name: str, score: float, metadata: dict = None):
    """주간 스캔 결과로 프로젝트 상태 업데이트."""
    state = _load_project_state()
    projects = state.setdefault("projects", {})
    projects[project_name] = {
        "last_score": score,
        "last_scan": datetime.now().isoformat(),
        "metadata": metadata or {},
    }
    state["last_scan"] = datetime.now().isoformat()
    _save_project_state(state)
    logger.info(f"[Projects] {project_name} 스캔 점수 업데이트: {score:.1f}")


def auto_manage_projects(config=None) -> dict:
    """
    자동 프로젝트 관리 — 주간 스캔 후 호출.
    - 고득점 프로젝트 자동 활성화
    - 비활성 프로젝트 자동 제거
    - 만료 프로젝트 비활성화

    Returns: {"activated": [...], "deactivated": [...], "expired": [...]}
    """
    mgmt_config = {}
    if config and hasattr(config, "get"):
        mgmt_config = config.get("project_management", {})

    threshold = mgmt_config.get("auto_activate_threshold", 70)
    max_active = mgmt_config.get("max_active_projects", 10)
    deactivate_days = mgmt_config.get("auto_deactivate_after_days", 30)
    auto_expire = mgmt_config.get("auto_expire_completed", True)

    state = _load_project_state()
    result = {"activated": [], "deactivated": [], "expired": []}

    # 현재 활성 목록
    active_names = []
    if config and hasattr(config, "get"):
        active_names = list(config.get("active_projects", []))
    if not active_names:
        active_names = list(_REGISTRY.keys())

    # 1. 비활성 기준 초과 프로젝트 제거
    now = datetime.now()
    for name in list(active_names):
        info = state.get("projects", {}).get(name, {})
        last_scan_str = info.get("last_scan")
        if last_scan_str:
            try:
                last_scan = datetime.fromisoformat(last_scan_str)
                if (now - last_scan).days > deactivate_days:
                    active_names.remove(name)
                    result["deactivated"].append(name)
                    logger.info(f"[Projects] 자동 비활성화: {name} (마지막 활동 {last_scan_str[:10]})")
            except (ValueError, TypeError):
                pass

    # 2. 만료된 프로젝트 (토큰 출시 완료 등)
    if auto_expire:
        for name in list(active_names):
            info = state.get("projects", {}).get(name, {})
            metadata = info.get("metadata", {})
            if metadata.get("token_launched") or metadata.get("airdrop_ended"):
                active_names.remove(name)
                result["expired"].append(name)
                logger.info(f"[Projects] 만료: {name}")

    # 3. 고득점 비활성 프로젝트 자동 활성화
    for name, info in state.get("projects", {}).items():
        if name not in active_names and name in _REGISTRY:
            score = info.get("last_score", 0)
            if score >= threshold and len(active_names) < max_active:
                active_names.append(name)
                result["activated"].append(name)
                logger.info(f"[Projects] 자동 활성화: {name} (점수: {score:.1f})")

    # config.yaml 업데이트
    if result["activated"] or result["deactivated"] or result["expired"]:
        _update_config_yaml(active_names)

    return result


def _update_config_yaml(new_active_list: list):
    """config.yaml의 active_projects 업데이트."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        return

    lines = config_path.read_text().split("\n")
    new_lines = []
    in_active = False
    active_written = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("active_projects:"):
            in_active = True
            new_lines.append(line)
            # 활성 프로젝트 목록 새로 작성
            for name in new_active_list:
                new_lines.append(f"  - {name}")
            active_written = True
            continue
        if in_active and stripped.startswith("- "):
            continue  # 기존 항목 스킵
        if in_active and not stripped.startswith("- ") and stripped and not stripped.startswith("#"):
            in_active = False
        if not (in_active and not active_written):
            new_lines.append(line)

    config_path.write_text("\n".join(new_lines))
    logger.info(f"[Projects] config.yaml 업데이트: {new_active_list}")


def get_active_projects(config=None) -> list:
    """config.yaml의 active_projects 목록에 따라 활성 프로젝트 인스턴스 반환."""
    active_names = []
    if config and hasattr(config, "get"):
        active_names = config.get("active_projects", [])
    if not active_names:
        active_names = list(_REGISTRY.keys())

    projects = []
    for name in active_names:
        cls = _REGISTRY.get(name)
        if cls:
            proj = cls(config)
            if proj.active:
                projects.append(proj)

    # 우선순위 내림차순 정렬
    projects.sort(key=lambda p: p.priority, reverse=True)
    return projects


def get_all_registered() -> list[str]:
    """레지스트리에 등록된 모든 프로젝트 이름 반환."""
    return list(_REGISTRY.keys())


def get_project(name: str, config=None):
    cls = _REGISTRY.get(name)
    return cls(config) if cls else None
