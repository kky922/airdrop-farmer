"""
ai_engine/glm_decision_maker.py — GLM5-1 AI 의사결정 엔진

GLM-4-Flash API를 활용해 파밍 전략, 프로젝트 분석, 시빌 위험도를 결정.
API 키 없으면 기본값을 반환하므로 API 없이도 동작 가능.
"""
import json
import logging
import os
from datetime import datetime
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_MODEL = "glm-4-flash"


class GLMDecisionMaker:
    def __init__(self, config=None):
        self.config = config
        self._api_key = os.getenv("GLM_API_KEY", "")
        self._timeout = aiohttp.ClientTimeout(total=30)

    async def analyze_project(self, project_data: dict) -> dict:
        """
        프로젝트 에어드랍 분석.

        Returns:
            airdrop_probability (0.0~1.0), estimated_value_usd,
            sybil_risk, farming_priority, recommended_actions,
            key_risks, summary
        """
        default = {
            "airdrop_probability": 0.5,
            "estimated_value_usd": 1000,
            "sybil_risk": "MEDIUM",
            "farming_priority": 5,
            "recommended_actions": ["swap", "lend", "bridge"],
            "key_risks": ["sybil detection", "gas cost"],
            "summary": "분석 불가 (API 키 없음)",
        }
        if not self._api_key:
            return default

        prompt = f"""
에어드랍 파밍 전략가로서 아래 프로젝트를 분석해줘.
프로젝트 데이터: {json.dumps(project_data, ensure_ascii=False)}

JSON으로 응답해줘 (다른 텍스트 없이):
{{
  "airdrop_probability": 0.0~1.0,
  "estimated_value_usd": 예상 에어드랍 가치(USD),
  "sybil_risk": "LOW|MEDIUM|HIGH",
  "farming_priority": 1~10,
  "recommended_actions": ["액션1", "액션2"],
  "key_risks": ["위험1", "위험2"],
  "summary": "한국어 요약 1문장"
}}
"""
        response = await self._call_glm_api(prompt)
        return self._parse_json(response, default)

    async def decide_farming_strategy(
        self,
        project_name: str,
        wallet_history: list,
        current_gas: float,
        market_conditions: dict,
    ) -> dict:
        """
        지금 파밍할지 AI가 결정.

        Returns:
            should_farm_now (bool), reason, recommended_delay_hours,
            tx_amount_multiplier, actions_to_skip, priority_actions
        """
        default = {
            "should_farm_now": True,
            "reason": "기본 전략 적용 (API 키 없음)",
            "recommended_delay_hours": 0,
            "tx_amount_multiplier": 1.0,
            "actions_to_skip": [],
            "priority_actions": ["swap", "lend"],
        }
        if not self._api_key:
            # 가스비 높으면 대기
            if current_gas > 30:
                default["should_farm_now"] = False
                default["reason"] = f"가스비 높음: {current_gas} Gwei"
                default["recommended_delay_hours"] = 2
            return default

        prompt = f"""
에어드랍 파밍 전략가로서 지금 파밍 여부를 결정해줘.
프로젝트: {project_name}
현재 가스비: {current_gas} Gwei
최근 지갑 히스토리 (마지막 5개): {json.dumps(wallet_history[-5:], ensure_ascii=False)}
시장 상황: {json.dumps(market_conditions, ensure_ascii=False)}

JSON으로만 응답:
{{
  "should_farm_now": true/false,
  "reason": "한국어 이유",
  "recommended_delay_hours": 0~24,
  "tx_amount_multiplier": 0.5~2.0,
  "actions_to_skip": [],
  "priority_actions": []
}}
"""
        response = await self._call_glm_api(prompt)
        return self._parse_json(response, default)

    async def assess_sybil_risk(
        self,
        wallet_addresses: list,
        recent_actions: list,
    ) -> dict:
        """
        현재 패턴의 시빌 탐지 위험도 평가.

        Returns:
            risk_level (LOW/MEDIUM/HIGH/CRITICAL), risk_score (0~100),
            detected_patterns, recommendations, should_pause
        """
        default = {
            "risk_level": "LOW",
            "risk_score": 20,
            "detected_patterns": [],
            "recommendations": ["정상적인 딜레이 유지"],
            "should_pause": False,
        }
        if not self._api_key:
            return default

        prompt = f"""
시빌 탐지 전문가로서 아래 패턴의 위험도를 평가해줘.
지갑 수: {len(wallet_addresses)}
최근 액션 (마지막 10개): {json.dumps(recent_actions[-10:], ensure_ascii=False)}

JSON으로만 응답:
{{
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "risk_score": 0~100,
  "detected_patterns": ["패턴1"],
  "recommendations": ["권고사항1"],
  "should_pause": true/false
}}
"""
        response = await self._call_glm_api(prompt)
        return self._parse_json(response, default)

    async def generate_weekly_insight(
        self,
        farming_results: dict,
        new_projects: list,
        market_data: dict,
    ) -> str:
        """주간 파밍 인사이트 한국어 생성 (텔레그램 리포트용)."""
        if not self._api_key:
            success = farming_results.get("success", 0)
            failed = farming_results.get("failed", 0)
            return (
                f"📊 주간 인사이트\n"
                f"✅ 성공: {success}개 | ❌ 실패: {failed}개\n"
                f"🆕 신규 프로젝트: {len(new_projects)}개"
            )

        prompt = f"""
에어드랍 파밍 전략가로서 아래 데이터를 바탕으로 주간 인사이트를 한국어로 작성해줘.
파밍 결과: {json.dumps(farming_results, ensure_ascii=False)}
신규 프로젝트: {json.dumps(new_projects[:5], ensure_ascii=False)}
시장 데이터: {json.dumps(market_data, ensure_ascii=False)}

텔레그램 메시지 형식으로 이모지 포함해서 300자 이내로 작성.
"""
        return await self._call_glm_api(prompt) or "주간 인사이트 생성 실패"

    async def _call_glm_api(self, prompt: str) -> Optional[str]:
        """GLM-4-Flash API 공통 호출 함수."""
        if not self._api_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": GLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            }
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(
                    GLM_API_URL, headers=headers, json=payload
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"[GLM API] HTTP {resp.status}")
                        return None
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"[GLM API] 호출 실패: {e}")
            return None

    @staticmethod
    def _parse_json(text: Optional[str], default: dict) -> dict:
        """JSON 파싱 실패 시 기본값 반환."""
        if not text:
            return default
        try:
            # 코드 블록 제거
            cleaned = text.strip().strip("```json").strip("```").strip()
            return json.loads(cleaned)
        except Exception:
            logger.warning("[GLM API] JSON 파싱 실패 — 기본값 사용")
            return default
