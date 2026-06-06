# -*- coding: utf-8 -*-
"""체인 모듈 레지스트리"""
from chains.base import BaseChain

# 모든 체인은 BaseChain을 상속 → 체인별 오버라이드
# 새 체인 추가 시 여기에 import만 추가하면 됨

CHAIN_CLASSES = {}

def _register():
    """설정에 있는 모든 체인을 자동 등록"""
    import config
    for chain_name in config.CHAIN_REGISTRY:
        try:
            if chain_name == "scroll":
                from chains.scroll import ScrollChain
                CHAIN_CLASSES[chain_name] = ScrollChain
            elif chain_name == "berachain":
                from chains.berachain import BerachainChain
                CHAIN_CLASSES[chain_name] = BerachainChain
            elif chain_name == "base":
                from chains.base_chain import BaseChainImpl
                CHAIN_CLASSES[chain_name] = BaseChainImpl
            elif chain_name == "monad":
                from chains.monad import MonadChain
                CHAIN_CLASSES[chain_name] = MonadChain
            elif chain_name == "abstract":
                from chains.abstract import AbstractChain
                CHAIN_CLASSES[chain_name] = AbstractChain
            elif chain_name == "story":
                from chains.story import StoryChain
                CHAIN_CLASSES[chain_name] = StoryChain
            elif chain_name == "megaeth":
                from chains.megaeth import MegaETHChain
                CHAIN_CLASSES[chain_name] = MegaETHChain
            elif chain_name == "unichain":
                from chains.unichain import UnichainChain
                CHAIN_CLASSES[chain_name] = UnichainChain
            elif chain_name == "ink":
                from chains.ink import InkChain
                CHAIN_CLASSES[chain_name] = InkChain
            elif chain_name == "linea":
                from chains.linea import LineaChain
                CHAIN_CLASSES[chain_name] = LineaChain
            elif chain_name == "eclipse":
                from chains.eclipse import EclipseChain
                CHAIN_CLASSES[chain_name] = EclipseChain
            elif chain_name == "fuel":
                from chains.fuel import FuelChain
                CHAIN_CLASSES[chain_name] = FuelChain
            else:
                # 기본 BaseChain 사용 (람다 대신 팩토리 함수)
                CHAIN_CLASSES[chain_name] = _make_factory(chain_name)
        except ImportError:
            # 서브클래스 없으면 기본 BaseChain 사용
            CHAIN_CLASSES[chain_name] = _make_factory(chain_name)

def _make_factory(chain_name: str):
    """BaseChain 팩토리 생성"""
    def factory():
        return BaseChain(chain_name)
    return factory

_register()

def list_chains():
    """등록된 체인 이름 목록"""
    return list(CHAIN_CLASSES.keys())


def get_chain(chain_name: str) -> BaseChain:
    """체인 인스턴스 생성"""
    cls = CHAIN_CLASSES.get(chain_name)
    if cls:
        return cls()
    return BaseChain(chain_name)