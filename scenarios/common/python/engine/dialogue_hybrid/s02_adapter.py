"""S02 스타일 Line/Reaction 생성기 adapter.

Layer 2 fallback 전용. 내부는 stateless 함수 호출 (인스턴스/히스토리 없음).
(구 S02 romance_line_generator/romance_reaction_generator shim 은 U5에서 제거 —
 이 모듈을 직접 import 한다. 시나리오가 대화 정책 fixed 를 선언하면
 Character 게이트가 이 adapter 도달 전에 차단한다: engine.dialogue_policy)

예:
    from engine.dialogue_hybrid.s02_adapter import LineGenerator
    gen = LineGenerator(profile)
    text = gen.generate(action_id, state)

profile 은 name/archetype 만 있으면 충분.
데이터 루트는 기본값(scenarios/common/python/dialogues) 사용, 필요 시 dialogue_root 주입.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional

from engine.dialogue_hybrid.stateless import (
    generate_line as _generate_line,
    generate_reaction as _generate_reaction,
)


# S02 좌표식: X = 호감 - 반발*0.8, Y = (성욕+욕망)/2 - 순수도/2, Z = gauge*0.6 + min(total,4)*10
def _s02_state_to_bias(state: Dict[str, Any]) -> Dict[str, float]:
    """S02 state dict → Hybrid state_bias (affinity/arousal/climax, 정규화 범위)."""
    rep = state.get("호감", 0) - state.get("반발", 0) * 0.8
    desire = (state.get("성욕", 0) * 0.5 + state.get("욕망", 0) * 0.5
              - state.get("순수도", 0) * 0.5)
    gauge = state.get("climax_gauge", 0) * 0.6
    total = min(state.get("climax_total", 0), 4) * 10
    climax = min(100, gauge + total)
    return {
        "affinity": max(-1.0, min(1.0, rep / 100.0)),
        "arousal": max(-1.0, min(1.0, desire / 100.0)),
        "climax": max(0.0, min(1.0, climax / 100.0)),
    }


class LineGenerator:
    """S02 romance_line_generator.LineGenerator 와 signature 호환.

    기존 호출:
        gen = LineGenerator(profile)
        text = gen.generate(action_id, state)
    """

    def __init__(self, profile: Dict[str, Any],
                 dialogue_root: Optional[Path] = None):
        self.profile = profile
        self.name: str = profile.get("name", "anon")
        self.archetype: str = profile.get("archetype", "stoic")
        self._dialogue_root = dialogue_root

    def generate(self, action_id: str, state: Dict[str, Any]) -> Optional[str]:
        bias = _s02_state_to_bias(state)
        out = _generate_line(self.archetype, self.name, action_id, bias,
                             dialogue_root=self._dialogue_root)
        return out if out else None


class ReactionGenerator:
    """S02 romance_reaction_generator.ReactionGenerator 와 signature 호환.

    기존 호출:
        gen = ReactionGenerator(profile)
        text = gen.generate(action_id, "during", state)
    """

    def __init__(self, profile: Dict[str, Any],
                 dialogue_root: Optional[Path] = None):
        self.profile = profile
        self.name: str = profile.get("name", "anon")
        self.archetype: str = profile.get("archetype", "stoic")
        self._dialogue_root = dialogue_root

    def generate(self, action_id: str, timing: str,
                 state: Dict[str, Any]) -> Optional[str]:
        bias = _s02_state_to_bias(state)
        out = _generate_reaction(self.archetype, self.name, action_id,
                                 timing, bias,
                                 dialogue_root=self._dialogue_root)
        return out if out else None
