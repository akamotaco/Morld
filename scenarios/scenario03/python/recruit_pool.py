# recruit_pool.py — 분대원 랜덤 생성 (티어 로트 + 제조 편차)
#
# 테마: Echo 시리즈는 규격품이지만 로트마다 제조 편차가 있고, 운행 주기가
# 진행되면 본부가 개량형/시제품 로트를 내려보낸다 (재활용 테마의 연장 —
# 시제품은 성능이 좋은 대신 인간성이 불안정한 상태로 도착한다).
#
# 랜덤 축 3개:
#   - 아키타입: 역할별 후보 풀에서 가중 추첨 → 대사 톤(hybrid) 개체 차이
#   - 스탯 편차: vita/sapientia ± variance (티어가 클수록 편차·보정 큼)
#   - 티어: 운행 주기 연동 (1-2 standard / 3-4 improved / 5+ prototype)
#
# 재현성: 시드 = cycle*1000 + serial — 같은 주기의 같은 시리얼은 항상
# 같은 개체 (세이브/재실행/SharpPy 동일). rng 직접 주입도 가능.

from engine import character_gen as cg


# 티어 (운행 주기 연동 — cycle.difficulty_for_cycle 과 같은 구간)
TIER_STANDARD = "standard"     # 규격품
TIER_IMPROVED = "improved"     # 개량형
TIER_PROTOTYPE = "prototype"   # 시제품

TIER_LABELS = {
    TIER_STANDARD: "규격품",
    TIER_IMPROVED: "개량형",
    TIER_PROTOTYPE: "시제품",
}

# 스탯 클램프 (vita 상한 10은 전투 성장 상한과 동일)
STAT_MIN = 1
STAT_MAX = 10

SPEC = {
    "roles": {
        "assault": {
            "base_props": {"vita": 6, "sapientia": 3},
            "archetypes": [("fierce", 60), ("cheerful", 25), ("proud", 15)],
        },
        "support": {
            "base_props": {"vita": 5, "sapientia": 4},
            "archetypes": [("cheerful", 50), ("devoted", 30), ("fierce", 20)],
        },
        "sniper": {
            "base_props": {"vita": 4, "sapientia": 5},
            "archetypes": [("stoic", 60), ("cold", 30), ("proud", 10)],
        },
        "medic": {
            "base_props": {"vita": 3, "sapientia": 7},
            "archetypes": [("gentle", 50), ("timid", 25), ("devoted", 25)],
        },
    },
    "tiers": {
        TIER_STANDARD: {
            "variance": {"vita": (-1, 1), "sapientia": (-1, 1)},
        },
        TIER_IMPROVED: {
            "prop_bonus": {"vita": 1, "sapientia": 1},
            "variance": {"vita": (-1, 1), "sapientia": (-1, 1)},
        },
        TIER_PROTOTYPE: {
            "prop_bonus": {"vita": 2, "sapientia": 2},
            "variance": {"vita": (-2, 2), "sapientia": (-2, 2)},
            "archetype_extra": [("cold", 15), ("innocent", 10)],
            # 엔진이 읽지 않는 시나리오 자유 키 — 아래에서 직접 소비
            "humanity_mod": -20,
        },
    },
}


def tier_for_cycle(cycle):
    """운행 주기 → 보급 로트 티어 (difficulty_for_cycle 과 같은 구간)"""
    if cycle <= 2:
        return TIER_STANDARD
    if cycle <= 4:
        return TIER_IMPROVED
    return TIER_PROTOTYPE


def generate_member(role_key, serial, cycle=0, rng=None):
    """분대원 정체성 생성 — SquadMember.configure 인자 묶음.

    Args:
        role_key: "assault"/"support"/"sniper"/"medic"
        serial: 시리얼 번호 (이름/unique_id/시드에 사용)
        cycle: 운행 주기 (0=초기 편성 → standard)
        rng: 재현용 난수기 (미지정 시 cycle/serial 시드로 자동 생성)

    Returns dict:
        unique_id, name, role, tier, tier_label, archetype,
        stat_overrides({"vita","sapientia"}), humanity_mod
    """
    if rng is None:
        rng = cg.make_rng(cycle * 1000 + serial)
    tier = tier_for_cycle(cycle)
    identity = cg.roll_identity(SPEC, role_key, tier, rng=rng)

    stats = {}
    for prop, value in identity["props"].items():
        stats[prop] = max(STAT_MIN, min(STAT_MAX, value))

    tier_spec = SPEC["tiers"].get(tier) or {}
    return {
        "unique_id": f"echo_{serial:02d}",
        "name": f"Echo-{serial:02d}",
        "role": role_key,
        "tier": tier,
        "tier_label": TIER_LABELS.get(tier, tier),
        "archetype": identity["archetype"],
        "stat_overrides": stats,
        "humanity_mod": tier_spec.get("humanity_mod", 0),
    }


def reset():
    """pi-world reset 계약 — 상태 없음 (no-op)"""
    pass
