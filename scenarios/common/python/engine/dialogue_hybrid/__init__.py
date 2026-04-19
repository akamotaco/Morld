"""engine.dialogue_hybrid — 공용 Template + Slot 대화 엔진.

Phase 1: tmp/dialogue_multistage/ 프로토타입 이관.

Public API:
    from engine.dialogue_hybrid import HybridEngine, ACTION_TO_CATEGORY

    # 단일 context
    eng = HybridEngine.load(character="시호", context="daily",
                             dialogue_root="scenarios/common/python/dialogues")

    # 여러 context 병합 (action ↔ category fallback 가능)
    eng = HybridEngine.load_composite(
        character="린", contexts=["romance", "action_lines"],
        dialogue_root=...)

    text = eng.generate(intent="hug",
                        state={"affinity": 0.8, "arousal": 0.3},
                        context={"name": "린"})

특징:
    - Option C 구조: characters/{name}.yaml + archetype_dialogues/{arch}/{ctx}.yaml
    - 4 override 연산자: add_templates / replace_templates / disable_templates / add_slots
    - 3 prior 레이어: state-bias, slot feature, anti-repetition
    - Intent fallback: action → category (hug → light 등)
    - Dynamic slot 주입: {name} 등 런타임 치환

향후 (Phase 2-3):
    - S02 호환 adapter (romance_line_generator.LineGenerator → 내부 호출)
    - 데이터 본 엔진 dialogues/ 로 이관
    - SharpPy 런타임 대응 (현재 pyyaml 의존 — JSON 또는 pre-compiled dict 로 변환 예정)
"""
from engine.dialogue_hybrid.engine import (
    HybridEngine,
    ACTION_TO_CATEGORY,
)
from engine.dialogue_hybrid.s02_adapter import (
    LineGenerator,
    ReactionGenerator,
)

__all__ = [
    "HybridEngine", "ACTION_TO_CATEGORY",
    "LineGenerator", "ReactionGenerator",  # S02 호환 어댑터
]
