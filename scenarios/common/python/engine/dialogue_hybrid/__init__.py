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

SharpPy 런타임 대응 (2026-07-05):
    - pyyaml 톱레벨 의존 제거 — 모든 데이터 로드는 data_loader 경유
      (pyyaml 있으면 yaml 직독, 없으면 `dialogues_compiled` 빌드 산출물).
    - yaml 수정 후: `python scenarios/common/python/dialogues/compile_dialogues.py`
    - 문서: docs/dialogue-data-pipeline.md
"""
from engine.dialogue_hybrid.engine import (
    HybridEngine,
    ACTION_TO_CATEGORY,
)
from engine.dialogue_hybrid.stateless import (
    generate_line,
    generate_reaction,
    clear_cache,
)
from engine.dialogue_hybrid.s02_adapter import (
    LineGenerator,
    ReactionGenerator,
)

__all__ = [
    "HybridEngine", "ACTION_TO_CATEGORY",
    "generate_line", "generate_reaction", "clear_cache",  # stateless API
    "LineGenerator", "ReactionGenerator",  # S02 호환 어댑터
]
