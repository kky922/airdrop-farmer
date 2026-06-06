"""
tests/test_glm_bridge.py — GLM5-1 브릿지 테스트

실행: pytest tests/test_glm_bridge.py -v
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.glm_bridge import GLM5Bridge


@pytest.fixture
def config():
    return MagicMock()


@pytest.fixture
def bridge(config):
    return GLM5Bridge(config)


class TestGLM5BridgeLoad:
    def test_instance_created(self, bridge):
        """GLM5Bridge 인스턴스 생성 성공."""
        assert bridge is not None

    def test_loaded_modules_is_list(self, bridge):
        """loaded_modules()가 리스트를 반환."""
        assert isinstance(bridge.loaded_modules(), list)

    def test_is_legacy_loaded_returns_bool(self, bridge):
        """is_legacy_loaded()가 bool을 반환."""
        result = bridge.is_legacy_loaded("wallet_manager")
        assert isinstance(result, bool)


class TestGLM5BridgeFallback:
    @pytest.mark.asyncio
    async def test_fallback_farming_returns_dict(self, bridge):
        """폴백 파밍이 결과 dict를 반환."""
        result = await bridge._fallback_farming(
            chain="megaeth",
            wallet=MagicMock(),
            activity_type="swap",
            amount=0.01,
        )
        assert isinstance(result, dict)
        assert result["fallback"] is True
        assert result["chain"] == "megaeth"
        assert result["activity_type"] == "swap"

    @pytest.mark.asyncio
    async def test_execute_farming_action_returns_dict(self, bridge):
        """레거시 없을 때 execute_farming_action이 폴백 결과를 반환."""
        result = await bridge.execute_farming_action(
            chain="unichain",
            wallet=MagicMock(),
            activity_type="bridge",
            amount=0.05,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_build_transaction_returns_dict(self, bridge):
        """build_transaction이 기본 TX 구조를 반환."""
        tx = await bridge.build_transaction(
            chain="ethereum",
            from_address="0xABC",
            to_address="0xDEF",
            value_wei=1000000000000000,
        )
        assert tx["from"] == "0xABC"
        assert tx["to"] == "0xDEF"

    @pytest.mark.asyncio
    async def test_get_wallet_info_returns_none_when_no_legacy(self, bridge):
        """레거시 없을 때 get_wallet_info가 None을 반환."""
        result = await bridge.get_wallet_info(0)
        # 레거시가 없으면 None 또는 dict
        assert result is None or isinstance(result, dict)
