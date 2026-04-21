# engine/persona.py — 아키타입 기반 페르소나 시스템 (공통 인프라)
#
# S02에서 정립된 10 아키타입을 표준으로, 시나리오별 성격/프로필 → 아키타입 매핑.
# S04 Tier-3 NPC는 `성격` prop에서 자동 유도 (PERSONALITY_TO_ARCHETYPE 매핑).
#
# 대사 풀은 시나리오가 개별 관리 (예: scenario04/npc_dialogue.py).
# Phase 2(성인 모드)에서 tone_templates/* 이식 시 동일 아키타입 이름으로 호환.

import morld


# ========================================
# 표준 아키타입 10종 (S02와 동일)
# ========================================

ARCHETYPES = [
    "stoic",       # 과묵/차분
    "cheerful",    # 호쾌/낙천
    "timid",       # 겁쟁이/조심
    "fierce",      # 신경질/용감
    "innocent",    # 순진
    "cold",        # 탐욕/의심/영악
    "gentle",      # (S04 Tier-3 미사용, Phase 2 고정 NPC용)
    "seductive",   # (Phase 2 전용)
    "proud",       # (Phase 2 전용)
    "devoted",     # 충직
    "tsundere",    # 츤데레 — inner_bias 이중 레이어 (표면 거칠음 + 내면 따뜻함)
]

DEFAULT_ARCHETYPE = "stoic"


# ========================================
# S04 성격 → 아키타입 매핑 (Tier-3 자동 유도)
# ========================================
# character_randomizer.PERSONALITY_POOL 의 14종을 기본 7 아키타입에 분산.

PERSONALITY_TO_ARCHETYPE = {
    "호쾌":     "cheerful",
    "낙천적":   "cheerful",
    "수다쟁이": "cheerful",
    "과묵":     "stoic",
    "차분":     "stoic",
    "신경질":   "fierce",
    "용감":     "fierce",
    "겁쟁이":   "timid",
    "조심성":   "timid",
    "순진":     "innocent",
    "충직":     "devoted",
    "의심많은": "cold",
    "탐욕":     "cold",
    "영악":     "cold",
}


# ========================================
# API
# ========================================

def get_archetype(unit_id):
    """유닛의 아키타입 조회.

    우선순위:
      1. `아키타입` prop (명시적 설정 — 고정 NPC가 사용)
      2. `성격` prop → PERSONALITY_TO_ARCHETYPE 매핑 (Tier-3 자동)
      3. DEFAULT_ARCHETYPE
    """
    explicit = morld.get_unit_prop(unit_id, "아키타입")
    if explicit and explicit in ARCHETYPES:
        return explicit

    personality = morld.get_unit_prop(unit_id, "성격")
    if personality:
        mapped = PERSONALITY_TO_ARCHETYPE.get(personality)
        if mapped:
            return mapped

    return DEFAULT_ARCHETYPE


def set_archetype(unit_id, archetype):
    """아키타입 명시 설정 (성격 매핑을 덮어씀)."""
    if archetype not in ARCHETYPES:
        print(f"[persona] WARNING: unknown archetype '{archetype}' for unit {unit_id}")
        return
    morld.set_unit_prop(unit_id, "아키타입", archetype)
