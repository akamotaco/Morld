# events/player_creation.py - 캐릭터 생성 이벤트
#
# 게임 시작 시 플레이어 이름/나이/체격/장비 선택 흐름

import morld
from assets.characters.player import (
    NAME_OPTIONS, AGE_OPTIONS, BODY_OPTIONS, EQUIPMENT_OPTIONS
)
from assets import registry

# 캐릭터 생성 임시 저장소
_creation_data = {
    "name": None,
    "age": None,
    "body": None,
    "equipment": None
}


def get_player_name():
    """플레이어 이름 반환 (Python 내부 저장소에서)"""
    return _creation_data.get("name") or "???"


def set_name(context_unit_id, name):
    """이름 설정"""
    _creation_data["name"] = name

    # 나이 선택 페이지
    age_options = "\n".join([
        f"[url=script:set_age:{opt['value']}]{opt['label']}[/url]"
        for opt in AGE_OPTIONS
    ])
    age_page = f"그래, 나는 {name}.\n\n내 나이는...?\n\n{age_options}"

    return {
        "type": "monologue",
        "pages": [age_page],
        "time_consumed": 0,
        "button_type": "none"
    }


def set_age(context_unit_id, age_str):
    """나이 설정"""
    age = int(age_str)
    _creation_data["age"] = age

    # 신체 선택 페이지
    body_options = "\n".join([
        f"[url=script:set_body:{opt['value']}]{opt['label']}[/url]"
        for opt in BODY_OPTIONS
    ])
    body_page = f"내 체격은...?\n\n{body_options}"

    return {
        "type": "monologue",
        "pages": [body_page],
        "time_consumed": 0,
        "button_type": "none"
    }


def set_body(context_unit_id, body_type):
    """신체 설정"""
    _creation_data["body"] = body_type

    # 장비 선택 페이지
    equip_options = "\n".join([
        f"[url=script:set_equipment:{opt['id']}]{opt['label']}[/url]\n  - {opt['desc']}"
        for opt in EQUIPMENT_OPTIONS
    ])
    equip_page = f"손에 뭔가 익숙한 감각이...\n\n{equip_options}"

    return {
        "type": "monologue",
        "pages": [equip_page],
        "time_consumed": 0,
        "button_type": "none"
    }


def set_equipment(context_unit_id, equip_id):
    """장비 설정 및 캐릭터 생성 완료"""
    _creation_data["equipment"] = equip_id

    # 플레이어 데이터 적용
    player_id = morld.get_player_id()

    # 나이는 정수로 저장 가능
    morld.set_flag("player_age", _creation_data["age"])

    # 신체 타입을 인덱스로 저장 (0=왜소, 1=보통, 2=장신, 3=거구)
    body_index = {"왜소": 0, "보통": 1, "장신": 2, "거구": 3}.get(_creation_data["body"], 1)
    morld.set_flag("player_body", body_index)

    # 이름을 인덱스로 저장 (NAME_OPTIONS 인덱스)
    name_index = NAME_OPTIONS.index(_creation_data["name"]) if _creation_data["name"] in NAME_OPTIONS else 0
    morld.set_flag("player_name_index", name_index)

    # 장비 지급 (unique_id 기반)
    for opt in EQUIPMENT_OPTIONS:
        if opt["id"] == equip_id:
            for unique_id, count in opt["items"]:
                item_id = registry.get_instance_id(unique_id)
                if item_id is not None:
                    morld.give_item(player_id, item_id, count)
            break

    # 완료 메시지 - 숲에서 방황 시작
    name = _creation_data["name"]

    completion_pages = [
        f"그래... 나는 {name}.",
        "기억은 아직 희미하지만...\n적어도 나 자신이 누구인지는 알겠다.",
        "...여기가 어디지? 깊은 숲 속인 것 같다.",
        "일단 움직여서 사람이 있는 곳을 찾아야겠다."
    ]

    return {
        "type": "monologue",
        "pages": completion_pages,
        "time_consumed": 5,
        "button_type": "ok"
    }
