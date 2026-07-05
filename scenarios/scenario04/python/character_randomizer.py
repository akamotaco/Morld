# character_randomizer.py — 캐릭터 속성 랜덤 생성 헬퍼
#
# npc_generator, 플레이어 초기화 등에서 공용으로 쓰는 랜덤 생성 로직.
# 순수 함수(roll_*) + 통합 적용 함수(apply_random_character)로 구성.
#
# 랜덤 메커니즘은 engine.character_gen 프리미티브로 통일한다
# (weighted_choice=가중 추첨, roll_range=범위, sample_distinct=중복 없는 다중
#  추첨, make_rng=시드 격리). S04 는 데이터 풀 + 조합만 소유한다.
# 모든 roll_* 는 rng(random.Random) 주입을 받는다 — 미지정 시 전역 random.
# 결정적 재현(세이브/재실행)이 필요하면 make_rng(고정 시드)를 주입할 것
# (S03 recruit_pool 이 참조 구현).

import random

import morld
import tags as tags_module
from engine import character_gen as cg


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

# 리더십 분포: [0=부하, 1=소규모 리더(본인+1), 2=고리더(본인+2)]
# 향후 밸런싱: 고정 NPC/플레이어 경로에 따라 조정 가능
LEADERSHIP_WEIGHTS = (70, 25, 5)


# ========================================
# 단위 롤 함수
# ========================================

def roll_gender(rng=None) -> bool:
    """True=남, False=여"""
    return (rng or random).random() < 0.5


def roll_name(is_male: bool, avoid: set = None, rng=None) -> str:
    """중복되지 않는 이름 선택. avoid에 기존 이름 set 전달.

    가용 이름이 모두 소진되면 avoid 무시하고 전체 풀에서 선택 (풀 고갈 폴백).
    """
    pool = NAME_POOL_MALE if is_male else NAME_POOL_FEMALE
    picked = cg.sample_distinct(pool, 1, rng=rng, avoid=avoid)
    if picked:
        return picked[0]
    return cg.weighted_choice(pool, rng=rng)  # 전부 avoid → 폴백


def roll_personality(rng=None) -> str:
    return cg.weighted_choice(PERSONALITY_POOL, rng=rng)


def roll_stats(min_val: int = 8, max_val: int = 15, rng=None) -> dict:
    """근력/민첩/체력/정신 랜덤 스탯."""
    bounds = (min_val, max_val)
    return {
        "str": cg.roll_range(bounds, rng),
        "agi": cg.roll_range(bounds, rng),
        "vit": cg.roll_range(bounds, rng),
        "mnd": cg.roll_range(bounds, rng),
    }


def roll_class(rare_chance: float = 0.05, rng=None) -> str:
    r = rng or random
    if r.random() < rare_chance:
        return cg.weighted_choice(CLASS_RARE, rng=r)
    return cg.weighted_choice(CLASS_POOL, rng=r)


def roll_leadership(rng=None) -> int:
    """리더십 수치(0/1/2) 롤. LEADERSHIP_WEIGHTS 분포 사용."""
    pool = [(i, w) for i, w in enumerate(LEADERSHIP_WEIGHTS)]
    return cg.weighted_choice(pool, rng=rng)


def roll_quirks(count_weights=(50, 35, 15), rng=None) -> list:
    """0~2개의 선천 기벽 선택. 기본 가중치: 50% 없음, 35% 1개, 15% 2개."""
    count_pool = [(i, w) for i, w in enumerate(count_weights)]
    count = cg.weighted_choice(count_pool, rng=rng)
    pool = QUIRK_POOL_MINOR + QUIRK_POOL_MODERATE + QUIRK_POOL_POSITIVE
    return cg.sample_distinct(pool, count, rng=rng)


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
    rng=None,
) -> dict:
    """unit에 랜덤 속성(성별/성격/스탯/기벽/태그)을 적용.

    Args:
        unit_id: 대상 유닛
        is_male: None이면 랜덤. True/False면 고정.
        avoid_names: 이름 중복 회피 set (랜덤 이름 반환용. 실제 적용은 caller)
        assign_class: 클래스 prop 부여 여부 (플레이어 false)
        assign_quirks: 기벽 prop 부여 여부
        stats_range: (min, max) 스탯 범위
        rng: 재현용 난수기 (미지정 시 전역 random). make_rng(seed)로 결정적 생성

    Returns:
        적용된 값의 dict (로깅용). {"name", "is_male", "personality",
        "stats", "class", "quirks"}.
    """
    r = rng or random
    if is_male is None:
        is_male = roll_gender(r)
    name = roll_name(is_male, avoid=avoid_names, rng=r)
    personality = roll_personality(r)
    stats = roll_stats(*stats_range, rng=r)
    npc_class = roll_class(rng=r) if assign_class else None
    quirks = roll_quirks(rng=r) if assign_quirks else []
    leadership = roll_leadership(r)

    # prop 적용
    morld.set_unit_prop(unit_id, "성격", personality)
    morld.set_unit_prop(unit_id, "성별", "남" if is_male else "여")
    morld.set_unit_prop(unit_id, "스탯:근력", stats["str"])
    morld.set_unit_prop(unit_id, "스탯:민첩", stats["agi"])
    morld.set_unit_prop(unit_id, "스탯:체력", stats["vit"])
    morld.set_unit_prop(unit_id, "스탯:정신", stats["mnd"])
    morld.set_unit_prop(unit_id, "리더십", leadership)
    # 동정심 (1~10, 기본 5) — 구출/파티 합류 등 NPC 판단에 영향
    compassion = cg.roll_range((1, 10), r)
    morld.set_unit_prop(unit_id, "동정심", compassion)
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
        "leadership": leadership,
        "compassion": compassion,
    }
