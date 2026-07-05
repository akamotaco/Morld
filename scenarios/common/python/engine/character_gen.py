# character_gen.py - 랜덤 캐릭터 생성 프레임워크 (순수 함수, morld 미사용)
#
# 시나리오가 spec(순수 데이터)을 넘기면 엔진이 추첨 메커니즘을 제공한다.
# 참조 콘텐츠: S03 recruit_pool.py (티어 기반 분대원 로트),
#              S04 character_randomizer.py (마을 NPC — 이관 예정 후보)
#
# spec 스키마 (엔진이 읽는 키만 명세 — 시나리오는 자유롭게 키를 추가하고
# 직접 소비해도 된다. 예: S03의 humanity_mod):
#   {
#     "roles": {role_key: {
#         "base_props": {prop: value},     # 역할 기본 스탯
#         "archetypes": [...],             # 아키타입 후보 풀 (가중 표기 가능)
#     }},
#     "tiers": {tier_key: {
#         "prop_bonus": {prop: +n},        # 티어 보정 (덧셈)
#         "variance": {prop: (lo, hi)},    # 개체 편차 (폐구간 랜덤 덧셈)
#         "archetype_extra": [...],        # 티어에서 추가되는 아키타입 후보
#     }},
#   }
#
# 후보 풀 표기: ["a", "b"] (균등) 또는 [("a", 60), ("b", 40)] (가중치)
#
# 재현성: 모든 함수는 rng(random.Random 인스턴스)를 받는다. 시나리오는
# 세이브/재실행 재현이 필요하면 make_rng(고정 시드)로 만들어 주입할 것.

import random


def make_rng(seed=None):
    """독립 난수기 생성 — 전역 random 상태를 오염시키지 않는다"""
    return random.Random(seed)


def weighted_choice(pool, rng=None):
    """후보 풀에서 1개 추첨. pool: [값, ...] 또는 [(값, 가중치), ...] (혼합 허용).

    가중치 없는 항목은 1로 간주 — 역할 풀(균등)과 티어 추가 풀(가중)을
    이어붙여도 안전하다.
    """
    if not pool:
        return None
    r = rng or random
    values = []
    weights = []
    for item in pool:
        if isinstance(item, tuple) and len(item) == 2:
            values.append(item[0])
            weights.append(item[1])
        else:
            values.append(item)
            weights.append(1)
    return r.choices(values, weights=weights)[0]


def roll_range(bounds, rng=None):
    """(lo, hi) 폐구간 정수 랜덤. bounds가 정수면 그대로 반환"""
    if isinstance(bounds, int):
        return bounds
    lo, hi = bounds
    r = rng or random
    return r.randint(lo, hi)


def sample_distinct(pool, count, rng=None, avoid=None):
    """풀에서 중복 없이 최대 count개 추첨 (avoid에 든 값 제외).

    이름 풀(중복 회피)·기벽 풀(다중 선택) 등에 공용. 가용 후보가 count보다
    적으면 있는 만큼만 반환한다 (예외 없음).
    """
    r = rng or random
    avoid = set(avoid or ())
    candidates = [x for x in pool if x not in avoid]
    if count >= len(candidates):
        result = list(candidates)
        r.shuffle(result)
        return result
    return r.sample(candidates, count)


def roll_identity(spec, role_key, tier_key, rng=None):
    """spec 기반 랜덤 정체성 생성.

    props 계산 순서: 역할 base_props → 티어 variance(덧셈 랜덤) → 티어 prop_bonus.
    아키타입 후보 = 역할 archetypes + 티어 archetype_extra 에서 가중 추첨.

    Returns:
        {"role": role_key, "tier": tier_key, "archetype": str|None,
         "props": {prop: value}}
    """
    r = rng or random
    role_spec = (spec.get("roles") or {}).get(role_key) or {}
    tier_spec = (spec.get("tiers") or {}).get(tier_key) or {}

    props = dict(role_spec.get("base_props") or {})
    for prop, bounds in (tier_spec.get("variance") or {}).items():
        props[prop] = props.get(prop, 0) + roll_range(bounds, r)
    for prop, bonus in (tier_spec.get("prop_bonus") or {}).items():
        props[prop] = props.get(prop, 0) + bonus

    pool = list(role_spec.get("archetypes") or [])
    pool.extend(tier_spec.get("archetype_extra") or [])
    archetype = weighted_choice(pool, r)

    return {
        "role": role_key,
        "tier": tier_key,
        "archetype": archetype,
        "props": props,
    }


def reset():
    """pi-world reset 계약 — 순수 함수 모듈, 상태 없음 (no-op)"""
    pass
