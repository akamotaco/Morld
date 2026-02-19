# position.py - 체위 시스템
"""
체위 (Position) 시스템 — 애정 행위 중 체위 관리

핵심 특성:
- 8종 체위: 정상위/대면기승위/배면기승위/대면좌위/배면좌위/후배위/대면입위/배면입위
- facing: front(대면) / back(배면) — 배면 시 입 사용 행위 제한
- control: player/npc/shared — 주도권 구분
- 전이 그래프: 양방향 전이 가능 여부 정의
- NPC 선호: 선호 체위/부위 → stim 배율 보너스
"""

import random

# ============================================
# 체위 정의
# ============================================

POSITIONS = {
    "missionary":       {"name": "정상위",     "facing": "front", "control": "player"},
    "cowgirl":          {"name": "대면기승위", "facing": "front", "control": "npc"},
    "reverse_cowgirl":  {"name": "배면기승위", "facing": "back",  "control": "npc"},
    "face_sitting":     {"name": "대면좌위",   "facing": "front", "control": "shared"},
    "reverse_sitting":  {"name": "배면좌위",   "facing": "back",  "control": "shared"},
    "doggy":            {"name": "후배위",     "facing": "back",  "control": "player"},
    "standing_face":    {"name": "대면입위",   "facing": "front", "control": "shared"},
    "standing_back":    {"name": "배면입위",   "facing": "back",  "control": "player"},
}

# ============================================
# 전이 그래프 (양방향)
# ============================================

TRANSITIONS = {
    "missionary":      {"cowgirl", "face_sitting", "doggy", "standing_face"},
    "cowgirl":         {"reverse_cowgirl", "face_sitting", "missionary"},
    "reverse_cowgirl": {"cowgirl", "doggy"},
    "face_sitting":    {"reverse_sitting", "standing_face", "missionary"},
    "reverse_sitting": {"face_sitting", "doggy"},
    "doggy":           {"reverse_sitting", "standing_back", "reverse_cowgirl"},
    "standing_face":   {"face_sitting", "missionary"},
    "standing_back":   {"doggy"},
}

# ============================================
# 초기 체위 풀
# ============================================

# 플레이어 주도: 기승위(NPC 위) 지양
PLAYER_INIT_POOL = ["missionary", "face_sitting", "standing_face", "doggy", "standing_back"]

# NPC 주도: 정상위/후배위(플레이어 위) 지양
NPC_INIT_POOL = ["cowgirl", "reverse_cowgirl", "face_sitting", "standing_face", "standing_back"]

# 의식불명: NPC 수동/와위 전용 (능동적 참여 불가)
UNCONSCIOUS_INIT_POOL = ["missionary", "doggy"]

# ============================================
# 선호 보너스
# ============================================

PREFERRED_POSITION_MULT = 1.2   # 선호 체위 → stim gain ×1.2
PREFERRED_PART_MULT = 1.15      # 선호 부위 → stim gain ×1.15


# ============================================
# 함수
# ============================================

def get_position_info(position_id):
    """체위 정보 반환"""
    return POSITIONS.get(position_id)


def get_facing(position_id):
    """현재 체위의 facing 반환 ("front" 또는 "back")"""
    pos = POSITIONS.get(position_id)
    return pos["facing"] if pos else "front"


def get_name(position_id):
    """체위 이름 반환"""
    pos = POSITIONS.get(position_id)
    return pos["name"] if pos else "알 수 없음"


def get_available_transitions(current):
    """현재 체위에서 전이 가능한 체위 목록"""
    return list(TRANSITIONS.get(current, set()))


def can_transition(from_pos, to_pos):
    """전이 가능 여부"""
    return to_pos in TRANSITIONS.get(from_pos, set())


def select_initial_position(is_npc_initiative, npc_prefs=None, mode=None):
    """세션 시작 시 초기 체위 선택

    Args:
        is_npc_initiative: NPC 주도 세션 여부
        npc_prefs: NPC SEXUAL_PREFERENCES dict (optional)
        mode: 모드 문자열 ("unconscious" 등, optional)

    Returns:
        str: 선택된 체위 ID
    """
    if mode == "unconscious":
        pool = UNCONSCIOUS_INIT_POOL
    elif is_npc_initiative:
        pool = NPC_INIT_POOL
    else:
        pool = PLAYER_INIT_POOL

    # 선호 체위가 풀에 있으면 가중치 부여
    preferred = []
    if npc_prefs:
        preferred = npc_prefs.get("preferred_positions", [])

    weights = []
    for pos_id in pool:
        if pos_id in preferred:
            weights.append(3)  # 선호 체위 3배 가중치
        else:
            weights.append(1)

    return random.choices(pool, weights=weights, k=1)[0]


def get_preference_mult(position_id, stim_category, npc_prefs):
    """NPC 선호에 따른 자극 배율 계산

    Args:
        position_id: 현재 체위 ID
        stim_category: 자극 카테고리 ("M", "B", "V", "C", "P", "A", "F")
        npc_prefs: NPC SEXUAL_PREFERENCES dict

    Returns:
        float: 배율 (1.0 = 보너스 없음)
    """
    if not npc_prefs:
        return 1.0

    mult = 1.0

    # 선호 체위 보너스
    if position_id in npc_prefs.get("preferred_positions", []):
        mult *= PREFERRED_POSITION_MULT

    # 선호 부위 보너스
    if stim_category in npc_prefs.get("preferred_parts", []):
        mult *= PREFERRED_PART_MULT

    return mult
