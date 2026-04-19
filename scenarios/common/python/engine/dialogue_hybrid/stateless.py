"""Stateless Hybrid 대화 생성 — 인스턴스/히스토리 없이 매 호출 순수 함수.

설계:
    - Fallback 레이어 용도. Layer 1(ROMANCE_REACTIONS/TALK_RULES)이 미스한 경우만 호출됨
    - state 변화(호감/성욕 등)가 자연스러운 다양성을 주므로 anti-repetition 불필요
    - 시드/히스토리 관리 없음. RNG는 module-level random 기본, 테스트만 rng 주입

데이터 캐시:
    - (dialogue_root, character, archetype, contexts) → 파싱·병합된 merged_data
    - yaml 파싱은 1회, 병합도 1회. 이후 호출은 dict 조회만.

Public API:
    generate_line(archetype, character, action_id, state, ...)
    generate_reaction(archetype, character, action_id, timing, state, ...)
    clear_cache()
"""
from __future__ import annotations
import copy
import random as _random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from engine.dialogue_hybrid.engine import (
    ACTION_TO_CATEGORY,
    _SLOT_RE,
    _merge_intents,
    _softmax_sample,
    _state_distance,
)

# 튜닝 상수 (HybridEngine 기본값과 동일)
_TEMPLATE_SIGMA = 0.6
_TEMPLATE_TEMP = 0.5
_SLOT_SIGMA = 0.6
_SLOT_TEMP = 0.5

_LINE_CONTEXTS: Tuple[str, ...] = ("romance", "action_lines")
_REACTION_CONTEXTS: Tuple[str, ...] = ("romance_reactions", "action_reactions")

# (root_str, character, archetype, contexts) → merged data
_DATA_CACHE: Dict[Tuple[str, str, str, Tuple[str, ...]], Dict[str, Any]] = {}


def _default_root() -> Path:
    """dialogue_hybrid 패키지 기준 상대 경로의 dialogues 루트."""
    return Path(__file__).resolve().parent.parent.parent / "dialogues"


def _load_merged(root: Path, character: str, archetype: str,
                 contexts: Tuple[str, ...]) -> Dict[str, Any]:
    """캐시 히트 시 즉시 반환. 미스 시 yaml 로드 + 병합."""
    key = (str(root), character, archetype, contexts)
    if key in _DATA_CACHE:
        return _DATA_CACHE[key]

    char_path = root / "characters" / f"{character}.yaml"
    if char_path.exists():
        char_data = yaml.safe_load(char_path.read_text(encoding="utf-8")) or {}
        effective_archetype = char_data.get("archetype", archetype)
    else:
        char_data = {"character": character, "archetype": archetype}
        effective_archetype = archetype

    all_intents: Dict[str, Dict] = {}
    for ctx in contexts:
        arch_path = root / "archetype_dialogues" / effective_archetype / f"{ctx}.yaml"
        if not arch_path.exists():
            continue
        arch_data = yaml.safe_load(arch_path.read_text(encoding="utf-8")) or {}
        for intent_name, intent_data in (arch_data.get("intents", {}) or {}).items():
            if intent_name in all_intents:
                all_intents[intent_name].setdefault("templates", []).extend(
                    intent_data.get("templates", []) or [])
                for sn, sp in (intent_data.get("slots", {}) or {}).items():
                    all_intents[intent_name].setdefault("slots", {}) \
                        .setdefault(sn, []).extend(sp)
            else:
                all_intents[intent_name] = copy.deepcopy(intent_data)

    for ctx in contexts:
        overrides = ((char_data.get("dialogue_overrides") or {})
                     .get(ctx, {}) or {}).get("intents", {}) or {}
        all_intents = _merge_intents(all_intents, overrides)

    merged = {
        "character": char_data.get("character", character),
        "archetype": effective_archetype,
        "outer_profile": char_data.get("outer_profile", {}) or {},
        "inner_profile": char_data.get("inner_profile", {}) or {},
        "intents": all_intents,
    }
    _DATA_CACHE[key] = merged
    return merged


def _pick_template(rng, templates: List[Dict],
                   outer_state: Dict[str, float],
                   inner_state: Dict[str, float]) -> Dict:
    logits: List[float] = []
    sigma = max(_TEMPLATE_SIGMA, 1e-6)
    for t in templates:
        sb = t.get("state_bias") or {}
        ib = t.get("inner_bias") or {}
        d = 0.0
        if sb:
            d += _state_distance(outer_state, sb)
        if ib:
            d += _state_distance(inner_state, ib)
        logits.append(-d / sigma)
    idx = _softmax_sample(rng, templates, logits, _TEMPLATE_TEMP)
    return templates[idx]


def _pick_slot(rng, pool: List, state: Dict[str, float]) -> str:
    if not pool:
        return ""
    texts: List[str] = []
    logits: List[float] = []
    sigma = max(_SLOT_SIGMA, 1e-6)
    for item in pool:
        if isinstance(item, dict):
            text = item.get("token", "")
            feat = item.get("feature", {}) or {}
            base = -_state_distance(state, feat) / sigma if feat else 0.0
        else:
            text = str(item)
            base = 0.0
        texts.append(text)
        logits.append(base)
    idx = _softmax_sample(rng, texts, logits, _SLOT_TEMP)
    return texts[idx]


def _generate_intent(data: Dict[str, Any], intent: str,
                     state: Optional[Dict[str, float]],
                     context_vars: Optional[Dict[str, Any]],
                     rng) -> str:
    intents = data.get("intents") or {}
    intent_data = intents.get(intent)
    if not intent_data or not (intent_data.get("templates") or []):
        fallback = ACTION_TO_CATEGORY.get(intent)
        if fallback and fallback in intents:
            intent_data = intents[fallback]
    if not intent_data:
        return ""
    templates = intent_data.get("templates") or []
    slots: Dict[str, List] = intent_data.get("slots") or {}
    if not templates:
        return ""

    outer = dict(data.get("outer_profile", {}) or {})
    inner_base = data.get("inner_profile") or data.get("outer_profile") or {}
    inner = dict(inner_base)
    if state:
        outer.update(state)
        inner.update(state)

    tpl = _pick_template(rng, templates, outer, inner)
    pattern = tpl.get("pattern", "")

    def _fill(match):
        slot_name = match.group(1)
        if context_vars and slot_name in context_vars:
            return str(context_vars[slot_name])
        pool = slots.get(slot_name)
        if pool is None:
            return ""
        return _pick_slot(rng, pool, outer)

    return _SLOT_RE.sub(_fill, pattern)


# ==================== Public API ====================

def generate_line(archetype: str, character: str, action_id: str,
                  state: Optional[Dict[str, float]] = None,
                  *, dialogue_root: Optional[Path] = None,
                  rng=None) -> str:
    """1인칭 대사 fallback (LINES + ACTION_LINES 풀).

    archetype: 10종 중 하나 (stoic/gentle/cheerful/timid/cold/seductive/fierce/proud/innocent/devoted)
    character: 캐릭터 이름. characters/{name}.yaml 이 있으면 override 적용, 없으면 아키타입만 사용
    action_id: hug, deep_kiss 등. ACTION_TO_CATEGORY 로 fallback
    state: affinity/arousal/climax 가 포함된 dict (S02 어댑터가 변환)
    rng: 미지정 시 module-level random (비결정적)
    """
    root = Path(dialogue_root) if dialogue_root else _default_root()
    data = _load_merged(root, character, archetype, _LINE_CONTEXTS)
    rng = rng if rng is not None else _random
    return _generate_intent(data, action_id, state, {"name": character}, rng)


def generate_reaction(archetype: str, character: str, action_id: str,
                      timing: str, state: Optional[Dict[str, float]] = None,
                      *, dialogue_root: Optional[Path] = None,
                      rng=None) -> str:
    """3인칭 묘사 fallback (ROMANCE_REACTIONS + ACTION_REACTIONS 풀).

    timing: "start"/"during"/"end" — 현재 구분 없이 같은 풀 사용 (S02 원본 동작)
    """
    root = Path(dialogue_root) if dialogue_root else _default_root()
    data = _load_merged(root, character, archetype, _REACTION_CONTEXTS)
    rng = rng if rng is not None else _random
    return _generate_intent(data, action_id, state, {"name": character}, rng)


def clear_cache() -> None:
    """테스트/챕터 재로드 용. 파싱 캐시 전부 비움."""
    _DATA_CACHE.clear()
