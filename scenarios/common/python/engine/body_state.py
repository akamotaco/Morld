# body_state.py — 부위 상태 시스템 공용 상수/레이아웃
#
# 부위는 자유 문자열 (왼팔/오른팔/머리/촉수1 등). 표준 anatomy는 강제하지 않음.
# 능력↔부위 매핑은 layout이 정의 — 종족별 다를 수 있음.
#
# Sparse prop 모델:
#   부상:{part}:정도 = 1~∞   # 0 도달 시 prop 정리
#   부상:{part}:종류 = 자유 문자열
#   결손:{part} = 1
#   결손:{part}:종류 = 자유 문자열
#   결손:{part}:보조구 = item_uid
#
# 차단(binary)은 결박(외부) + 결손(영구) 만. 부상은 multiplier(factor)로만 표현.

import morld


# === 임계/상수 ===
INJURY_BLOCK = 50  # 차후 활용 — 현재 구조 단계에서는 미참조

# 표준 부위 (자유 문자열이지만 일관성 위해 상수 제공)
PART_LEFT_ARM = "왼팔"
PART_RIGHT_ARM = "오른팔"
PART_LEFT_LEG = "왼다리"
PART_RIGHT_LEG = "오른다리"
PART_TORSO = "몸통"
PART_HEAD = "머리"


# === Body Layout — 능력 → 부위 매핑 ===
# 1 부위가 다중 능력에 등장 가능 (예: 머리 → speech/vision/hearing).
# 몸통은 능력 미매핑 — 데이터 누적만, 효과는 시나리오 책임.
DEFAULT_HUMAN_LAYOUT = {
    "hands":    [PART_LEFT_ARM, PART_RIGHT_ARM],
    "mobility": [PART_LEFT_LEG, PART_RIGHT_LEG],
    "speech":   [PART_HEAD],
    "vision":   [PART_HEAD],
    "hearing":  [PART_HEAD],
}

# 종족 → layout 레지스트리. register_layout()로 확장.
_LAYOUTS = {
    "human": DEFAULT_HUMAN_LAYOUT,
}


# === Aggregation 룰 — 능력 종합 방식 ===
# "any" (default): 한 부위라도 살아있으면 능력 유지 — gate=max factor
# "all":           모든 부위 살아있어야 능력 유지 — gate=min factor
# 향후 능력별 override (예: 다리 한쪽 결손도 차단 → mobility="all")
DEFAULT_AGGREGATION = "any"
ABILITY_AGGREGATION = {
    # "mobility": "all",
}


# === API ===

def get_body_layout(uid) -> dict:
    """유닛의 종족 prop으로 layout 조회. 없으면 human default."""
    species = morld.get_unit_prop(uid, "종족") or "human"
    return _LAYOUTS.get(species, DEFAULT_HUMAN_LAYOUT)


def get_aggregation(ability: str) -> str:
    """능력 종합 규칙."""
    return ABILITY_AGGREGATION.get(ability, DEFAULT_AGGREGATION)


def register_layout(species: str, layout: dict):
    """종족별 layout 등록 — 시나리오 초기화에서 호출."""
    _LAYOUTS[species] = layout


def reset():
    """시나리오 등록 layout 제거, 기본(human)만 유지 — pi-world reset 계약"""
    for species in [s for s in _LAYOUTS if s != "human"]:
        del _LAYOUTS[species]
