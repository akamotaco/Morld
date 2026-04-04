# building.py - S04 건축 시스템
#
# 플레이어가 마을에 Location/Gate를 동적 추가.
# 건축 가능 시설: 여관, 상점, 조교소, 암시장 등.
# 건축 비용 + 자원 소비. 건축 후 경영 가능.
# 마을 지도 2D 좌표도 함께 부여.

import morld
import economy

# === 건축 가능 시설 ===

BUILDING_TEMPLATES = {
    "여관": {
        "cost": 100000,
        "length": 200,
        "indoor": True,
        "props": {"시설:유형": "여관", "시설:소유자": "player"},
        "desc": "모험가들이 쉬어갈 수 있는 숙소.",
    },
    "상점": {
        "cost": 80000,
        "length": 150,
        "indoor": True,
        "props": {"시설:유형": "상점", "시설:소유자": "player"},
        "desc": "아이템을 사�� 파는 가게.",
    },
    "조교소": {
        "cost": 150000,
        "length": 100,
        "indoor": True,
        "props": {"시설:유형": "조교소", "시설:소유자": "player", "시설:숨김": 1},
        "desc": "포획한 NPC를 조교하는 시설.",
    },
    "창고": {
        "cost": 50000,
        "length": 200,
        "indoor": True,
        "props": {"시설:유형": "창고", "시설:소유자": "player"},
        "desc": "물자를 보관하는 곳.",
    },
    "농장": {
        "cost": 70000,
        "length": 400,
        "indoor": False,
        "props": {"시설:유형": "농장", "시설:소유자": "player"},
        "desc": "식량을 재배하는 터.",
    },
}

# === 상태 ===

_built_facilities = {}  # loc_id -> {"name", "template", ...}
_next_loc_id = 100       # 동적 Location ID 시작


def reset():
    global _next_loc_id
    _built_facilities.clear()
    _next_loc_id = 100


def get_buildable_list() -> list:
    """건축 가능 시설 목록"""
    player_id = morld.get_player_id()
    money = economy.get_money(player_id) if player_id else 0

    result = []
    for name, template in BUILDING_TEMPLATES.items():
        result.append({
            "name": name,
            "cost": template["cost"],
            "affordable": money >= template["cost"],
            "desc": template["desc"],
        })
    return result


def build(template_name: str, map_x: int, map_y: int,
          custom_name: str = None) -> int:
    """
    시설 건축.

    Args:
        template_name: 건축 템플릿 이름 ("여관", "상점" 등)
        map_x, map_y: 마을 지도 2D 좌표
        custom_name: 시설 이름 (없으면 템플릿명 사용)

    Returns:
        location_id or -1 (실패)
    """
    global _next_loc_id

    template = BUILDING_TEMPLATES.get(template_name)
    if not template:
        print(f"[building] Unknown template: {template_name}")
        return -1

    player_id = morld.get_player_id()
    if not player_id:
        return -1

    # 비용 지불
    if not economy.spend_money(player_id, template["cost"]):
        print(f"[building] Not enough money: {template['cost']}")
        return -1

    # Location 생성
    loc_id = _next_loc_id
    _next_loc_id += 1

    region_id = 0  # 마을
    name = custom_name or template_name

    morld.add_location(region_id, loc_id, name,
                      length=template["length"],
                      indoor=template.get("indoor", True))

    # 2D 좌표 prop
    unit_id = morld.get_location_unit_id(region_id, loc_id)
    if unit_id:
        morld.set_unit_prop(unit_id, "map:x", map_x)
        morld.set_unit_prop(unit_id, "map:y", map_y)

    # 시설 props
    for key, value in template.get("props", {}).items():
        if unit_id:
            morld.set_unit_prop(unit_id, key, value)

    # 마을 광장(0)과 Gate 연결
    gate_id = loc_id  # 심플하게 loc_id를 gate_id로
    morld.add_gate(region_id, 0, gate_id, 150,
                  region_id, loc_id, 0)
    morld.add_gate(region_id, loc_id, 0, 0,
                  region_id, 0, 150)

    # 오염 시스템 등록 (마을이므로 오염도 0)
    import pollution
    pollution.register_location(region_id, loc_id, 0)

    # 경영 등록 (해당되는 시설만)
    if template_name in ("여관", "상점", "농장"):
        import business
        business.register_business(loc_id, template_name)

    # 등록
    _built_facilities[loc_id] = {
        "name": name,
        "template": template_name,
        "map_x": map_x,
        "map_y": map_y,
    }

    print(f"[building] Built '{name}' at ({map_x},{map_y}), loc_id={loc_id}, "
          f"cost={template['cost']}")

    return loc_id


def get_built_facilities() -> dict:
    return _built_facilities.copy()


def get_player_facilities(facility_type: str = None) -> list:
    """플레이어 소유 시설 목록 (유형 필터 가능)"""
    result = []
    for loc_id, info in _built_facilities.items():
        if facility_type and info["template"] != facility_type:
            continue
        result.append({"loc_id": loc_id, **info})
    return result
