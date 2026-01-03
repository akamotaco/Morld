# characters/__init__.py - 모든 캐릭터 모듈 집합

import morld

from characters.player import data as player_data
from characters.lina import data as lina_data
from characters.sera import data as sera_data
from characters.mila import data as mila_data
from characters.yuki import data as yuki_data
from characters.ella import data as ella_data

# 플레이어 데이터
PLAYER_DATA = player_data.CHARACTER_DATA

# NPC 데이터 리스트 (플레이어 제외)
NPC_CHARACTERS = [
    lina_data.CHARACTER_DATA,
    sera_data.CHARACTER_DATA,
    mila_data.CHARACTER_DATA,
    yuki_data.CHARACTER_DATA,
    ella_data.CHARACTER_DATA,
]

# 모든 캐릭터 데이터 리스트 (플레이어 + NPC)
ALL_CHARACTERS = [PLAYER_DATA] + NPC_CHARACTERS

# 캐릭터별 이벤트 핸들러 등록
from characters.player import events as player_events
from characters.lina import events as lina_events
from characters.sera import events as sera_events
from characters.mila import events as mila_events
from characters.yuki import events as yuki_events
from characters.ella import events as ella_events

CHARACTER_EVENTS = {
    player_data.CHARACTER_ID: player_events,
    lina_data.CHARACTER_ID: lina_events,
    sera_data.CHARACTER_ID: sera_events,
    mila_data.CHARACTER_ID: mila_events,
    yuki_data.CHARACTER_ID: yuki_events,
    ella_data.CHARACTER_ID: ella_events,
}

# 캐릭터별 PRESENCE_TEXT 매핑
CHARACTER_PRESENCE = {
    lina_data.CHARACTER_ID: lina_data.PRESENCE_TEXT,
    sera_data.CHARACTER_ID: sera_data.PRESENCE_TEXT,
    mila_data.CHARACTER_ID: mila_data.PRESENCE_TEXT,
    yuki_data.CHARACTER_ID: yuki_data.PRESENCE_TEXT,
    ella_data.CHARACTER_ID: ella_data.PRESENCE_TEXT,
}


def initialize_characters():
    """morld API를 사용하여 모든 캐릭터 데이터 등록 (플레이어 + NPC)"""
    for char_data in ALL_CHARACTERS:
        _register_unit(char_data)
    print(f"[characters] {len(ALL_CHARACTERS)} characters initialized via morld API")


def initialize_player():
    """플레이어만 등록 (챕터 0용)"""
    _register_unit(PLAYER_DATA)
    print("[characters] Player initialized via morld API")


def initialize_npcs():
    """NPC들만 등록 (챕터 1 전환 시)"""
    for char_data in NPC_CHARACTERS:
        _register_unit(char_data)
    print(f"[characters] {len(NPC_CHARACTERS)} NPCs initialized via morld API")


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

    morld.add_unit(unit_id, name, region_id, location_id, unit_type, actions, appearance, mood)

    tags = data.get("tags")
    if tags:
        morld.set_unit_tags(unit_id, tags)

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


def get_presence_text(unit_id, region_id, location_id):
    """특정 캐릭터의 현재 상태에 맞는 presence text 반환"""
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
    """여러 캐릭터의 presence text를 한 번에 반환 (C#에서 호출)"""
    result = []
    for unit_id in unit_ids:
        text = get_presence_text(unit_id, region_id, location_id)
        if text:
            result.append(text)
    return result
