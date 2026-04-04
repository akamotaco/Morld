# quirk.py - S04 기벽 (Quirk) 시스템
#
# 선천 기벽: NPC 생성 시 숨겨진 상태로 부여, 시간/상황에 따라 발각
# 후천 기벽: 침식 축적 또는 행동 패턴 반복으로 획득
# 플레이어도 후천 기벽 대상 (아우터 월드 2 식)

import morld
import random

# === 기벽 데이터 ===

def reset():
    """챕터 전환 시 리셋"""
    _player_action_counts.clear()


QUIRKS = {
    # 자잘한 (침식 50+)
    "잠꼬대":    {"grade": "minor",    "type": "negative", "effect": "긴 휴식 시 파티원 수면 방해"},
    "코골이":    {"grade": "minor",    "type": "negative", "effect": "긴 휴식 시 피로 회복 감소"},
    "편식":      {"grade": "minor",    "type": "negative", "effect": "특정 식량만 섭취"},
    "수집벽":    {"grade": "minor",    "type": "negative", "effect": "쓸모없는 아이템 줍기"},
    "혼잣말":    {"grade": "minor",    "type": "negative", "effect": "몬스터 조우 확률↑"},

    # 신경쓰이는 (침식 70+ 또는 선천)
    "도벽":      {"grade": "moderate", "type": "negative", "effect": "휴식 시 동료 아이템 훔침"},
    "대식":      {"grade": "moderate", "type": "negative", "effect": "식량 1.5~2배 소비"},
    "겁쟁이":    {"grade": "moderate", "type": "negative", "effect": "HP<30% 시 명령 무시/도주"},
    "의심병":    {"grade": "moderate", "type": "negative", "effect": "타 파티원 신뢰 하락 유발"},
    "과식":      {"grade": "moderate", "type": "negative", "effect": "식량 있으면 자동 소비"},
    "독백":      {"grade": "moderate", "type": "negative", "effect": "파티 침식 소폭 가속"},

    # 심각한 (침식 100+ 고질)
    "폭주":      {"grade": "severe",   "type": "affliction", "effect": "전투 중 아군 공격"},
    "피해망상":  {"grade": "severe",   "type": "affliction", "effect": "랜덤 파티원을 적으로 인식"},
    "탐욕":      {"grade": "severe",   "type": "affliction", "effect": "보물 독식, 공유 거부"},
    "배신":      {"grade": "severe",   "type": "affliction", "effect": "야영 중 아이템 훔치고 도주"},
    "바람기":    {"grade": "severe",   "type": "affliction", "effect": "타 파티에 정보 유출"},
    "난폭":      {"grade": "severe",   "type": "affliction", "effect": "NPC 도발, 원치 않는 대결"},

    # 성적 (침식 80+)
    "몽정":      {"grade": "sexual",   "type": "negative", "effect": "긴 휴식 시 성적 반응"},
    "노출증":    {"grade": "sexual",   "type": "negative", "effect": "장비 탈의 충동 (방어력↓)"},
    "성적집착":  {"grade": "sexual",   "type": "negative", "effect": "특정 파티원에 성적 관심"},

    # 성적 심각 (침식 100+)
    "무차별흥분": {"grade": "sexual_severe", "type": "affliction", "effect": "자발적 흥분"},
    "강제관계":   {"grade": "sexual_severe", "type": "affliction", "effect": "휴식 중 파티원 성적 접근"},
    "복종갈망":   {"grade": "sexual_severe", "type": "affliction", "effect": "과도한 순종"},

    # 긍정 (각성/선천)
    "충직":      {"grade": "positive", "type": "positive", "effect": "명령 불복 확률 감소"},
    "자기희생":  {"grade": "positive", "type": "positive", "effect": "동료 위기 시 자발적 방어"},
    "결의":      {"grade": "positive", "type": "positive", "effect": "침식 축적 속도 감소"},
    "집중":      {"grade": "positive", "type": "positive", "effect": "명중/회피율 상승"},
    "용맹":      {"grade": "positive", "type": "positive", "effect": "HP 낮을수록 공격력 상승"},
}

# 침식 구간별 발현 가능 등급
EROSION_QUIRK_GRADES = {
    50: ["minor"],
    70: ["minor", "moderate"],
    80: ["minor", "moderate", "sexual"],
    100: ["severe", "sexual_severe"],  # 고질 판정 시
}


# === 기벽 관리 ===

def get_quirks(unit_id: int) -> list:
    """캐릭터의 모든 기벽 (발각/미발각 포함)"""
    quirks = []
    i = 0
    while True:
        # 선천
        q = morld.get_unit_prop(unit_id, f"기벽:선천:{i}")
        if q is None:
            break
        discovered = morld.get_unit_prop(unit_id, f"기벽:발각:{i}")
        quirks.append({"name": q, "origin": "선천", "discovered": bool(discovered), "index": i})
        i += 1

    # 후천
    j = 0
    while True:
        q = morld.get_unit_prop(unit_id, f"기벽:후천:{j}")
        if q is None:
            break
        quirks.append({"name": q, "origin": "후천", "discovered": True, "index": j})
        j += 1

    return quirks


def get_visible_quirks(unit_id: int) -> list:
    """발각된 기벽만"""
    return [q for q in get_quirks(unit_id) if q["discovered"]]


def add_quirk(unit_id: int, quirk_name: str, origin: str = "후천"):
    """기벽 추가"""
    existing = get_quirks(unit_id)
    existing_names = {q["name"] for q in existing}
    if quirk_name in existing_names:
        return  # 중복 방지

    if origin == "후천":
        idx = sum(1 for q in existing if q["origin"] == "후천")
        morld.set_unit_prop(unit_id, f"기벽:후천:{idx}", quirk_name)
        print(f"[quirk] {unit_id} acquired quirk: {quirk_name}")


def discover_quirk(unit_id: int, index: int):
    """선천 기벽 발각"""
    morld.set_unit_prop(unit_id, f"기벽:발각:{index}", 1)
    q = morld.get_unit_prop(unit_id, f"기벽:선천:{index}")
    if q:
        print(f"[quirk] {unit_id} quirk discovered: {q}")


# === 침식 기반 기벽 발현 ===

def check_erosion_quirk(unit_id: int, erosion: int) -> str:
    """
    침식 수준에 따른 기벽 발현 체크.

    Returns:
        발현된 기벽 이름 or None
    """
    # 해당 침식 구간에서 발현 가능한 등급
    available_grades = []
    for threshold, grades in sorted(EROSION_QUIRK_GRADES.items()):
        if erosion >= threshold:
            available_grades = grades

    if not available_grades:
        return None

    # 발현 확률 (침식 높을수록 증가)
    chance = min(0.3, erosion * 0.002)  # 최대 30%
    if random.random() > chance:
        return None

    # 해당 등급의 기벽 중 랜덤 선택
    candidates = [name for name, data in QUIRKS.items()
                  if data["grade"] in available_grades]

    if not candidates:
        return None

    # 이미 보유한 기벽 제외
    existing_names = {q["name"] for q in get_quirks(unit_id)}
    candidates = [c for c in candidates if c not in existing_names]

    if not candidates:
        return None

    quirk_name = random.choice(candidates)
    add_quirk(unit_id, quirk_name)
    return quirk_name


# === 플레이어 행동 패턴 기벽 (아우터 월드 2 식) ===

# 행동 카운터
_player_action_counts = {}

PLAYER_QUIRK_THRESHOLDS = {
    "소매치기": ("도벽", 10),
    "성추행": ("변태", 8),
    "약탈": ("약탈자", 10),
    "구출": ("영웅심", 10),
    "방관": ("냉혈", 8),
    "던전의힘": ("심연친화", 15),
}


def record_player_action(action: str):
    """플레이어 행동 기록. 임계치 도달 시 기벽 획득 알림."""
    _player_action_counts[action] = _player_action_counts.get(action, 0) + 1

    if action in PLAYER_QUIRK_THRESHOLDS:
        quirk_name, threshold = PLAYER_QUIRK_THRESHOLDS[action]
        if _player_action_counts[action] == threshold:
            player_id = morld.get_player_id()
            if player_id:
                # TODO: 아우터 월드 2처럼 "이 기벽을 받을래?" 선택지 표시
                print(f"[quirk] Player quirk available: {quirk_name} ({action} x{threshold})")
