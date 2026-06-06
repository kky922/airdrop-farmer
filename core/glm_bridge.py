"""
core/glm_bridge.py — GLM5-1 레거시 코드 통합 래퍼

레거시 모듈이 있으면 우선 사용하고, 없거나 실패하면 신규 로직으로 폴백.
레거시 코드는 절대 수정하지 않음.
"""
import importlib
import importlib.util
import sys
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

LEGACY_DIR = Path(__file__).parent.parent / "legacy"


class GLM5Bridge:
    """
    GLM5-1 레거시 모듈의 Decorator/Wrapper.

    동작 원칙:
      1. importlib으로 legacy/ 디렉토리에서 모듈을 동적 로드
      2. 로드 성공 시 레거시 함수 우선 호출
      3. 로드 실패 or 예외 발생 시 _fallback_*() 메서드로 자동 폴백
    """

    def __init__(self, config):
        self.config = config
        self._modules: dict[str, Any] = {}
        self._load_glm_modules()

    def _load_glm_modules(self):
        """legacy/ 폴더의 핵심 모듈을 importlib으로 동적 로드."""
        targets = {
            "wallet_manager": LEGACY_DIR / "wallet_manager.py",
            "activity_engine": LEGACY_DIR / "activity_engine.py",
            "gas_optimizer": LEGACY_DIR / "gas_optimizer.py",
            "db": LEGACY_DIR / "db.py",
            "config": LEGACY_DIR / "config.py",
        }

        for name, path in targets.items():
            if not path.exists():
                logger.warning(f"[GLM5Bridge] legacy/{name}.py 없음 — 폴백 사용")
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"legacy.{name}", path
                )
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f"legacy.{name}"] = mod
                spec.loader.exec_module(mod)
                self._modules[name] = mod
                logger.info(f"[GLM5Bridge] ✅ legacy/{name}.py 로드 성공")
            except Exception as e:
                logger.error(f"[GLM5Bridge] ❌ legacy/{name}.py 로드 실패: {e}")

    async def execute_farming_action(
        self,
        chain: str,
        wallet,
        activity_type: str,
        amount: float,
    ) -> dict:
        """
        파밍 액션 실행.
        레거시 ActivityEngine 우선 → 실패 시 폴백.
        """
        try:
            engine_mod = self._modules.get("activity_engine")
            if engine_mod and hasattr(engine_mod, "ActivityEngine"):
                # 레거시 엔진 인스턴스 생성 후 실행
                engine = engine_mod.ActivityEngine(
                    wallets=[], config=None
                )
                result = await engine._execute_activity(
                    chain=chain,
                    wallet=wallet,
                    activity_type=activity_type,
                    amount=amount,
                )
                return result
        except Exception as e:
            logger.warning(
                f"[GLM5Bridge] 레거시 ActivityEngine 실패: {e} — 폴백 전환"
            )
        return await self._fallback_farming(chain, wallet, activity_type, amount)

    async def get_wallet_info(self, wallet_index: int) -> Optional[dict]:
        """
        지갑 정보 조회.
        레거시 WalletManager 우선 → 실패 시 폴백.
        """
        try:
            wm_mod = self._modules.get("wallet_manager")
            if wm_mod and hasattr(wm_mod, "WalletManager"):
                wm = wm_mod.WalletManager()
                wallet = wm.get_wallet(wallet_index)
                if wallet:
                    return wallet.to_dict() if hasattr(wallet, "to_dict") else vars(wallet)
        except Exception as e:
            logger.warning(f"[GLM5Bridge] 레거시 WalletManager 실패: {e}")
        return None

    async def build_transaction(
        self,
        chain: str,
        from_address: str,
        to_address: str,
        value_wei: int,
        data: str = "0x",
    ) -> dict:
        """
        트랜잭션 빌드.
        레거시 모듈 없으면 기본 구조 반환.
        """
        try:
            cfg_mod = self._modules.get("config")
            if cfg_mod:
                chain_cfg = cfg_mod.get_chain_config(chain)
                return {
                    "chain": chain,
                    "from": from_address,
                    "to": to_address,
                    "value": value_wei,
                    "data": data,
                    "chainId": chain_cfg.get("chain_id") if chain_cfg else None,
                }
        except Exception as e:
            logger.warning(f"[GLM5Bridge] 레거시 TX 빌드 실패: {e}")

        return {
            "chain": chain,
            "from": from_address,
            "to": to_address,
            "value": value_wei,
            "data": data,
        }

    async def _fallback_farming(
        self,
        chain: str,
        wallet,
        activity_type: str,
        amount: float,
    ) -> dict:
        """
        레거시 실패 시 폴백 — 로그만 기록하고 dry-run 결과 반환.
        실제 TX를 보내려면 web3/ 모듈로 교체.
        """
        logger.info(
            f"[GLM5Bridge] 폴백 파밍 — chain={chain} type={activity_type} "
            f"amount={amount}"
        )
        return {
            "success": False,
            "fallback": True,
            "chain": chain,
            "activity_type": activity_type,
            "amount": amount,
            "reason": "legacy module unavailable",
        }

    def is_legacy_loaded(self, module_name: str) -> bool:
        """특정 레거시 모듈 로드 여부 확인."""
        return module_name in self._modules

    def loaded_modules(self) -> list[str]:
        """로드된 레거시 모듈 이름 목록."""
        return list(self._modules.keys())
