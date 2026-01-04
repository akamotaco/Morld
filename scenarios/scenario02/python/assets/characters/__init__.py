# assets/characters/__init__.py - 캐릭터 Asset 모듈

import morld
from assets import registry

from . import player
from . import lina
from . import sera
from . import mila
from . import yuki
from . import ella

# NPC 모듈 리스트 (플레이어 제외)
NPC_MODULES = [lina, sera, mila, yuki, ella]

# 캐릭터별 이벤트 핸들러 매핑
CHARACTER_EVENTS = {}

# 캐릭터별 PRESENCE_TEXT 매핑
CHARACTER_PRESENCE = {}


def register_all():
    """모든 캐릭터 Asset 등록"""
    # 플레이어 등록
    player.register()

    # NPC 등록
    for npc in NPC_MODULES:
        npc.register()

        # 이벤트 핸들러 등록
        if hasattr(npc, 'CHARACTER_ID') and hasattr(npc, 'events'):
            CHARACTER_EVENTS[npc.CHARACTER_ID] = npc.events

        # PRESENCE_TEXT 등록
        if hasattr(npc, 'CHARACTER_ID') and hasattr(npc, 'PRESENCE_TEXT'):
            CHARACTER_PRESENCE[npc.CHARACTER_ID] = npc.PRESENCE_TEXT

    print("[assets.characters] All character assets registered")


def get_character_event_handler(unit_id):
    """특정 캐릭터의 이벤트 핸들러 모듈 반환"""
    return CHARACTER_EVENTS.get(unit_id)


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
