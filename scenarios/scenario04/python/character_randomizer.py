# character_randomizer.py — 캐릭터 속성 랜덤 생성 헬퍼
#
# npc_generator, 플레이어 초기화 등에서 공용으로 쓰는 랜덤 생성 로직.
# 순수 함수(roll_*) + 통합 적용 함수(apply_random_character)로 구성.

import random

import morld
import tags as tags_module


# ========================================
# 풀 (임시, 세계관 확정 후 교체)
# ========================================

NAME_POOL_MALE = [
    "카이", "렌", "아키", "진", "하루", "소라", "유진", "태호",
    "마루", "건우", "세진", "도윤", "현", "리오", "준",
]

NAME_POOL_FEMALE = [
    "미카", "사나", "유나", "하나", "리나", "세이", "아야", "나츠",
    "수아", "지안", "서연", "다은", "채원", "하윤", "예린",
]

PERSONALITY_POOL = [
    "호쾌", "과묵", "조심성", "낙천적", "신경질", "차분", "수다쟁이",
    "의심많은", "충직", "탐욕", "겁쟁이", "용감", "영악", "순진",
]

CLASS_POOL = ["척후", "타격수", "사수", "방패잡이", "약사", "기술자", "거간꾼"]
CLASS_RARE = ["오염술사"]

QUIRK_POOL_MINOR = ["잠꼬대", "코골이", "편식", "수집벽", "혼잣말"]
QUIRK_POOL_MODERATE = ["도벽", "대식", "겁쟁이", "의심병"]
QUIRK_POOL_POSITIVE = ["충직", "자기희생"]


# ========================================
# 단위 롤 함수
# ========================================

def roll_gender() -> bool:
    """True=남, False=여"""
    return random.random() < 0.5


def roll_name(is_male: bool, avoid: set = None) -> str:
    """중복되지 않는 이름 선택. avoid에 기존 이름 set 전달."""
    avoid = avoid or set()
    pool = NAME_POOL_MALE if is_male else NAME_POOL_FEMALE
    for _ in range(10):
        name = random.choice(pool)
        if name not in avoid:
            return name
    return random.choice(pool)


def roll_personality() -> str:
    return random.choice(PERSONALITY_POOL)


def roll_stats(min_val: int = 8, max_val: int = 15) -> dict:
    """근력/민첩/체력/정신 랜덤 스탯."""
    return {
        "str": random.randint(min_val, max_val),
        "agi": random.randint(min_val, max_val),
        "vit": random.randint(min_val, max_val),
        "mnd": random.randint(min_val, max_val),
    }


def roll_class(rare_chance: float = 0.05) -> str:
    if random.random() < rare_chance:
        return random.choice(CLASS_RARE)
    return random.choice(CLASS_POOL)


def roll_quirks(count_weights=(50, 35, 15)) -> list:
    """0~2개의 선천 기벽 선택. 기본 가중치: 50% 없음, 35% 1개, 15% 2개."""
    count = random.choices(list(range(len(count_weights))), weights=list(count_weights))[0]
    pool = QUIRK_POOL_MINOR + QUIRK_POOL_MODERATE + QUIRK_POOL_POSITIVE
    quirks = []
    for _ in range(count):
        q = random.choice(pool)
        if q not in quirks:
            quirks.append(q)
    return quirks


# ========================================
# 통합 적용
# ========================================

def apply_random_character(
    unit_id: int,
    *,
    is_male: bool = None,
    avoid_names: set = None,
    assign_class: bool = True,
    assign_quirks: bool = True,
    stats_range: tuple = (8, 15),
) -> dict:
    """unit에 랜덤 속성(성별/성격/스탯/기벽/태그)을 적용.

    Args:
        unit_id: 대상 유닛
        is_male: None이면 랜덤. True/False면 고정.
        avoid_names: 이름 중복 회피 set (랜덤 이름 반환용. 실제 적용은 caller)
        assign_class: 클래스 prop 부여 여부 (플레이어 false)
        assign_quirks: 기벽 prop 부여 여부
        stats_range: (min, max) 스탯 범위

    Returns:
        적용된 값의 dict (로깅용). {"name", "is_male", "personality",
        "stats", "class", "quirks"}.
    """
    if is_male is None:
        is_male = roll_gender()
    name = roll_name(is_male, avoid=avoid_names)
    personality = roll_personality()
    stats = roll_stats(*stats_range)
    npc_class = roll_class() if assign_class else None
    quirks = roll_quirks() if assign_quirks else []

    # prop 적용
    morld.set_unit_prop(unit_id, "성격", personality)
    morld.set_unit_prop(unit_id, "성별", "남" if is_male else "여")
    morld.set_unit_prop(unit_id, "스탯:근력", stats["str"])
    morld.set_unit_prop(unit_id, "스탯:민첩", stats["agi"])
    morld.set_unit_prop(unit_id, "스탯:체력", stats["vit"])
    morld.set_unit_prop(unit_id, "스탯:정신", stats["mnd"])
    if npc_class:
        morld.set_unit_prop(unit_id, "클래스", npc_class)
    for i, quirk in enumerate(quirks):
        morld.set_unit_prop(unit_id, f"기벽:선천:{i}", quirk)
        morld.set_unit_prop(unit_id, f"기벽:발각:{i}", 0)

    # 태그 시스템 자동 동기화 (self_tags에 성별 반영)
    sex_tag = "sex:male" if is_male else "sex:female"
    tags_module.add_self_tags(unit_id, sex_tag, "species:human", "age:adult")

    return {
        "name": name,
        "is_male": is_male,
        "personality": personality,
        "stats": stats,
        "class": npc_class,
        "quirks": quirks,
    }
