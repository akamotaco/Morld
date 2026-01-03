# characters/__init__.py - 모든 캐릭터 모듈 집합

import morld

from characters.player import data as player_data
from characters.cheolsu import data as cheolsu_data
from characters.younghee import data as younghee_data
from characters.minsu import data as minsu_data

# 모든 캐릭터 데이터 리스트
ALL_CHARACTERS = [
    player_data.CHARACTER_DATA,
    cheolsu_data.CHARACTER_DATA,
    younghee_data.CHARACTER_DATA,
    minsu_data.CHARACTER_DATA,
]

# 캐릭터별 이벤트 핸들러 등록
from characters.player import events as player_events
from characters.cheolsu import events as cheolsu_events
from characters.younghee import events as younghee_events
from characters.minsu import events as minsu_events

CHARACTER_EVENTS = {
    player_data.CHARACTER_ID: player_events,
    cheolsu_data.CHARACTER_ID: cheolsu_events,
    younghee_data.CHARACTER_ID: younghee_events,
    minsu_data.CHARACTER_ID: minsu_events,
}


def initialize_characters():
    """morld API를 사용하여 모든 캐릭터 데이터 등록"""
    for char_data in ALL_CHARACTERS:
        _register_unit(char_data)
    print(f"[characters] {len(ALL_CHARACTERS)} characters initialized via morld API")


def _register_unit(data):
    """단일 유닛 데이터를 morld API로 등록"""
    unit_id = data["id"]
    name = data["name"]
    region_id = data.get("regionId", 0)
    location_id = data.get("locationId", 0)
    unit_type = data.get("type", "male")
    actions = data.get("actions")
    appearance = data.get("appearance")
    mood = data.get("mood")

    # 유닛 추가
    morld.add_unit(unit_id, name, region_id, location_id, unit_type, actions, appearance, mood)

    # 태그 설정
    tags = data.get("tags")
    if tags:
        morld.set_unit_tags(unit_id, tags)

    # 스케줄 스택 설정 (역순으로 push - 첫 요소가 베이스)
    schedule_stack = data.get("scheduleStack", [])
    for layer in schedule_stack:
        schedule_entries = layer.get("schedule")
        morld.push_schedule(
            unit_id,
            layer.get("name", ""),
            layer.get("endConditionType"),
            layer.get("endConditionParam"),
            schedule_entries
        )


def get_character_event_handler(unit_id):
    """특정 캐릭터의 이벤트 핸들러 모듈 반환"""
    return CHARACTER_EVENTS.get(unit_id)


def get_all_character_data():
    """캐릭터 데이터만 반환 (Python 내부용)"""
    return ALL_CHARACTERS


# 캐릭터별 PRESENCE_TEXT 매핑
CHARACTER_PRESENCE = {
    cheolsu_data.CHARACTER_ID: cheolsu_data.PRESENCE_TEXT,
    younghee_data.CHARACTER_ID: younghee_data.PRESENCE_TEXT,
    minsu_data.CHARACTER_ID: minsu_data.PRESENCE_TEXT,
}


def get_presence_text(unit_id, region_id, location_id):
    """
    특정 캐릭터의 현재 상태에 맞는 presence text 반환

    우선순위:
    1. activity 기반 (activity:식사 등)
    2. 장소 기반 (0:1 등)
    3. mood 기반 (mood:기쁨 등)
    4. default

    Args:
        unit_id: 캐릭터 ID
        region_id: 현재 위치 region
        location_id: 현재 위치 location

    Returns:
        presence text 문자열 또는 None
    """
    presence_dict = CHARACTER_PRESENCE.get(unit_id)
    if not presence_dict:
        return None

    unit_info = morld.get_unit_info(unit_id)
    if not unit_info:
        return None

    name = unit_info.get("name", "???")
    activity = unit_info.get("activity")
    moods = unit_info.get("mood", [])

    # 우선순위 1: activity
    if activity:
        key = f"activity:{activity}"
        if key in presence_dict:
            return presence_dict[key].format(name=name)

    # 우선순위 2: 장소
    loc_key = f"{region_id}:{location_id}"
    if loc_key in presence_dict:
        return presence_dict[loc_key].format(name=name)

    # 우선순위 3: mood
    if moods:
        for mood in moods:
            key = f"mood:{mood}"
            if key in presence_dict:
                return presence_dict[key].format(name=name)

    # 우선순위 4: 기본값
    if "default" in presence_dict:
        return presence_dict["default"].format(name=name)

    return None


def get_all_presence_texts(unit_ids, region_id, location_id):
    """
    여러 캐릭터의 presence text를 한 번에 반환 (C#에서 호출)

    Args:
        unit_ids: 캐릭터 ID 리스트
        region_id: 현재 위치 region
        location_id: 현재 위치 location

    Returns:
        presence text 리스트 (None인 항목은 제외)
    """
    result = []
    for unit_id in unit_ids:
        text = get_presence_text(unit_id, region_id, location_id)
        if text:
            result.append(text)
    return result
