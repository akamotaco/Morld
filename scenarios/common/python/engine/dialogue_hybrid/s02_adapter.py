"""S02 romance_line_generator / romance_reaction_generator 호환 adapter.

Phase 2 목표: 기존 S02 호출 코드 변경 없이 Hybrid 엔진 위에 올리기.

예:
    # 기존 코드 (변경 없음)
    from engine.dialogue_hybrid.s02_adapter import LineGenerator
    gen = LineGenerator(profile)
    text = gen.generate(action_id="hug", state={"호감": 80, "성욕": 30, ...})

내부:
    - profile (S02 형식) → HybridEngine 인스턴스 (캐시)
    - state (S02 축) → Hybrid state_bias (affinity/arousal/climax)
    - action_id → Hybrid intent (fallback 자동)

데이터 위치:
    scenarios/common/python/dialogues/
      archetype_dialogues/{archetype}/{context}.yaml
      characters/{name}.yaml (옵션 — 없으면 adapter가 임시 프로필 사용)
"""
from __future__ import annotations
import random
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from engine.dialogue_hybrid.engine import HybridEngine, ACTION_TO_CATEGORY


# 기본 dialogues 루트 (패키지 기준 상대경로)
_DEFAULT_DIALOGUE_ROOT = Path(__file__).resolve().parent.parent.parent / "dialogues"


# S02 상태 축 → Hybrid state 축 매핑
# S02 좌표식: X = 호감 - 반발*0.8, Y = (성욕+욕망)/2 - 순수도/2, Z = gauge*0.6 + min(total,4)*10
def _s02_state_to_bias(state: Dict[str, Any]) -> Dict[str, float]:
    """S02 state dict → Hybrid state_bias (affinity/arousal/climax, [-1,1])."""
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


class _EngineCache:
    """(archetype, context_tuple) → HybridEngine 인스턴스 캐시."""
    def __init__(self, dialogue_root: Path):
        self.root = Path(dialogue_root)
        self._cache: Dict[Tuple[str, str, Tuple[str, ...]], HybridEngine] = {}

    def get(self, archetype: str, character_name: str,
            contexts: Tuple[str, ...]) -> HybridEngine:
        key = (archetype, character_name, contexts)
        if key in self._cache:
            return self._cache[key]

        # Character yaml 있으면 load_composite, 없으면 임시 프로필로 생성
        char_path = self.root / "characters" / f"{character_name}.yaml"
        if char_path.exists():
            eng = HybridEngine.load_composite(
                character=character_name, contexts=list(contexts),
                dialogue_root=self.root)
        else:
            # 임시 프로필 (아키타입만 유효, 프로필 비어도 state_bias 매칭은 동작)
            import yaml
            import copy
            all_intents = {}
            for ctx in contexts:
                arch_path = self.root / "archetype_dialogues" / archetype / f"{ctx}.yaml"
                if not arch_path.exists():
                    continue
                arch_data = yaml.safe_load(arch_path.read_text(encoding="utf-8"))
                for intent_name, intent_data in (arch_data.get("intents", {}) or {}).items():
                    if intent_name in all_intents:
                        all_intents[intent_name].setdefault("templates", []).extend(
                            intent_data.get("templates", []) or [])
                    else:
                        all_intents[intent_name] = copy.deepcopy(intent_data)
            merged_data = {
                "character": character_name,
                "archetype": archetype,
                "outer_profile": {},
                "inner_profile": {},
                "intents": all_intents,
            }
            eng = HybridEngine(merged_data)

        self._cache[key] = eng
        return eng


# 전역 캐시 (dialogue_root 바뀌지 않는 전제)
_global_cache: Optional[_EngineCache] = None


def _get_cache(dialogue_root: Optional[Path] = None) -> _EngineCache:
    global _global_cache
    root = dialogue_root or _DEFAULT_DIALOGUE_ROOT
    if _global_cache is None or _global_cache.root != root:
        _global_cache = _EngineCache(root)
    return _global_cache


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
        self._contexts = ("romance", "action_lines")

    def generate(self, action_id: str, state: Dict[str, Any]) -> Optional[str]:
        """S02 호환 1인칭 대사 생성."""
        cache = _get_cache(self._dialogue_root)
        eng = cache.get(self.archetype, self.name, self._contexts)
        bias = _s02_state_to_bias(state)
        out = eng.generate(action_id, bias, context={"name": self.name})
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
        self._contexts = ("romance_reactions", "action_reactions")

    def generate(self, action_id: str, timing: str,
                 state: Dict[str, Any]) -> Optional[str]:
        """S02 호환 3인칭 묘사 생성. timing 은 현재 adapter에서 참고만."""
        cache = _get_cache(self._dialogue_root)
        eng = cache.get(self.archetype, self.name, self._contexts)
        bias = _s02_state_to_bias(state)
        out = eng.generate(action_id, bias, context={"name": self.name})
        return out if out else None
