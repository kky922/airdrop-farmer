"""
monitor/dashboard.py — FastAPI 웹 대시보드

ADD 지시서 #3:
- / : 전체 지갑 잔액, 오늘 파밍 현황
- /projects : 활성 프로젝트 상태
- /wallets : 지갑별 잔액 및 TX 내역
- /reports : 주간 파밍 성과
- /api/status : JSON API

실행: uvicorn monitor.dashboard:app --host 0.0.0.0 --port 8080
"""
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False
    logger.warning("[Dashboard] fastapi 미설치 — 대시보드 비활성화")


def create_app():
    if not _HAS_FASTAPI:
        return None

    app = FastAPI(title="Airdrop Farming Bot Dashboard", version="2.0.0")

    # 간단한 인메모리 상태 (실제 운영에서는 DB 연동)
    _state = {
        "start_time": datetime.now().isoformat(),
        "farming_cycles": 0,
        "last_activity": None,
    }

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTMLResponse(_render_dashboard_html(_state))

    @app.get("/api/status")
    async def api_status():
        return JSONResponse({
            "status": "running",
            "start_time": _state["start_time"],
            "farming_cycles": _state["farming_cycles"],
            "last_activity": _state["last_activity"],
        })

    @app.get("/api/projects")
    async def api_projects():
        from ai_engine.project_analyzer import ProjectAnalyzer
        analyzer = ProjectAnalyzer()
        top = analyzer.get_top_projects(n=10)
        return JSONResponse({"projects": top})

    @app.get("/api/chains")
    async def api_chains():
        from web3_tools.chain_configs import CHAIN_REGISTRY
        return JSONResponse({"chains": list(CHAIN_REGISTRY.keys())})

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def _render_dashboard_html(state: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>Airdrop Farming Bot v2</title>
  <meta http-equiv="refresh" content="30">
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
    h1 {{ color: #58a6ff; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin: 12px 0; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
    .green {{ background: #1a4731; color: #3fb950; }}
    .yellow {{ background: #3d2b00; color: #e3b341; }}
    .red {{ background: #3d0000; color: #f85149; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; text-align: left; }}
    th {{ color: #8b949e; font-weight: normal; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>🤖 Airdrop Farming Bot v2</h1>
  <div class="card">
    <h3>📊 시스템 상태</h3>
    <p>시작: {state['start_time']}</p>
    <p>파밍 사이클: {state['farming_cycles']}회</p>
    <p>마지막 활동: {state['last_activity'] or '없음'}</p>
  </div>
  <div class="card">
    <h3>🔥 우선 파밍 대상 (2026년 4월 기준)</h3>
    <table>
      <tr><th>프로젝트</th><th>FDV</th><th>가스비</th><th>긴급도</th></tr>
      <tr><td>MetaMask</td><td>$10B+</td><td>$30</td><td><span class="badge red">즉시</span></td></tr>
      <tr><td>MegaETH</td><td>$3B</td><td><span class="badge green">무료</span></td><td><span class="badge red">즉시</span></td></tr>
      <tr><td>Abstract</td><td>$3B</td><td>$10</td><td><span class="badge red">즉시</span></td></tr>
      <tr><td>Unichain</td><td>$2B+</td><td>$15</td><td><span class="badge red">즉시</span></td></tr>
      <tr><td>Ink</td><td>$1B</td><td>$8</td><td><span class="badge red">즉시</span></td></tr>
    </table>
  </div>
  <div class="card">
    <h3>🔗 API 엔드포인트</h3>
    <ul>
      <li><a href="/api/status" style="color:#58a6ff">/api/status</a> — 시스템 상태</li>
      <li><a href="/api/projects" style="color:#58a6ff">/api/projects</a> — 추천 프로젝트</li>
      <li><a href="/api/chains" style="color:#58a6ff">/api/chains</a> — 지원 체인</li>
    </ul>
  </div>
  <p style="color:#8b949e; font-size:12px">30초마다 자동 갱신 | Airdrop Farming Bot v2.0.0</p>
</body>
</html>"""


# FastAPI app 인스턴스
app = create_app()
