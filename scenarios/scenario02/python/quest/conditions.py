# quest/conditions.py — S02 전용 퀘스트 조건
#
# 엔진 기본 조건 (reach, prop, wait, all, any, quest_completed)은
# engine/quest.py에서 제공. 여기는 S02 전용 조건만 정의하고 플러그인 등록.

from typing import Optional
import morld
from engine.quest import register_condition_type, _check_reach as _engine_check_reach


# ============================================
# S02 전용 조건 체크
# ============================================

def _check_reach_s02(player_id, condition, quest_id):
    """위치 도착 조건 — S02 확장 (location_unique_id 지원)"""
    location_uid = condition.get("location_unique_id")
    if location_uid:
        from assets.registry import get_instance_id
        loc_id = get_instance_id(location_uid)
        if loc_id is None:
            return False
        player_loc = morld.get_unit_location(player_id)
        if not player_loc:
            return False
        return player_loc[1] == loc_id
    return _engine_check_reach(player_id, condition, quest_id)


def _desc_reach_s02(condition):
    location_uid = condition.get("location_unique_id")
    if location_uid:
        return location_uid + "에 도착"
    region_id = condition.get("region_id", 0)
    location_id = condition.get("location_id")
    location_name = _get_location_name(region_id, location_id)
    return location_name + "에 도착"


def _check_meet(player_id, condition, quest_id):
    """NPC 만남 조건"""
    target_unique_id = condition.get("target")
    if not target_unique_id:
        return False
    props = morld.get_unit_props(player_id)
    if not props:
        return False
    meet_key = "퀘스트:" + quest_id + ":meet:" + target_unique_id
    return props.get(meet_key, 0) >= 1


def _desc_meet(condition):
    target = condition.get("target", "???")
    return _get_npc_name(target) + "와(과) 만나기"


def _check_collect(player_id, condition, quest_id):
    """아이템 수집 조건"""
    item_unique_id = condition.get("item")
    required_count = condition.get("count", 1)
    if not item_unique_id:
        return False
    current_count = morld.get_item_count(player_id, item_unique_id)
    return current_count >= required_count


def _desc_collect(condition):
    item = condition.get("item", "???")
    count = condition.get("count", 1)
    item_name = _get_item_name(item)
    if count == 1:
        return item_name + " 수집"
    return item_name + " " + str(count) + "개 수집"


def _check_deliver(player_id, condition, quest_id):
    """아이템 전달 조건"""
    target_unique_id = condition.get("target")
    item_unique_id = condition.get("item")
    required_count = condition.get("count", 1)
    if not target_unique_id or not item_unique_id:
        return False
    props = morld.get_unit_props(player_id)
    if not props:
        return False
    deliver_key = "퀘스트:" + quest_id + ":deliver:" + target_unique_id + ":" + item_unique_id
    return props.get(deliver_key, 0) >= required_count


def _desc_deliver(condition):
    item = condition.get("item", "???")
    target = condition.get("target", "???")
    count = condition.get("count", 1)
    return target + "에게 " + item + " " + str(count) + "개 전달"


def _check_talk(player_id, condition, quest_id):
    """대화 조건"""
    target_unique_id = condition.get("target")
    dialog_id = condition.get("dialog_id")
    if not target_unique_id:
        return False
    props = morld.get_unit_props(player_id)
    if not props:
        return False
    if dialog_id:
        talk_key = "퀘스트:" + quest_id + ":talk:" + target_unique_id + ":" + dialog_id
    else:
        talk_key = "퀘스트:" + quest_id + ":talk:" + target_unique_id
    return props.get(talk_key, 0) >= 1


def _desc_talk(condition):
    target = condition.get("target", "???")
    return target + "와(과) 대화"


def _check_meet_anyone(player_id, condition, quest_id):
    """아무 NPC와 만남 조건 (관계:*:진척도 합산)"""
    props = morld.get_unit_props(player_id)
    if not props:
        return False
    total = 0
    for key, value in props.items():
        if key.startswith("관계:") and key.endswith(":진척도"):
            total += value
    return total >= 1


def _desc_meet_anyone(condition):
    return "누군가와 만나기"


# ============================================
# 조건 기록 함수 (이벤트에서 호출)
# ============================================

def record_meet(player_id, target_unique_id, quest_id):
    meet_key = "퀘스트:" + quest_id + ":meet:" + target_unique_id
    morld.set_unit_prop(player_id, meet_key, 1)


def record_talk(player_id, target_unique_id, quest_id, dialog_id=None):
    if dialog_id:
        talk_key = "퀘스트:" + quest_id + ":talk:" + target_unique_id + ":" + dialog_id
    else:
        talk_key = "퀘스트:" + quest_id + ":talk:" + target_unique_id
    morld.set_unit_prop(player_id, talk_key, 1)


def record_deliver(player_id, target_unique_id, item_unique_id, quest_id, count=1):
    deliver_key = "퀘스트:" + quest_id + ":deliver:" + target_unique_id + ":" + item_unique_id
    props = morld.get_unit_props(player_id)
    current = props.get(deliver_key, 0) if props else 0
    morld.set_unit_prop(player_id, deliver_key, current + count)


# ============================================
# 이름 조회 헬퍼
# ============================================

def _get_location_name(region_id, location_id):
    try:
        info = morld.get_location_info(region_id, location_id)
        if info and info.get("name"):
            return info["name"]
    except Exception:
        pass
    return "지역 " + str(region_id) + "-" + str(location_id)


def _get_npc_name(unique_id):
    try:
        unit_id = morld.find_unit_by_unique_id(unique_id)
        if unit_id:
            info = morld.get_unit_info(unit_id)
            if info and info.get("name"):
                return info["name"]
    except Exception:
        pass
    return unique_id


def _get_item_name(unique_id):
    try:
        item_id = morld.find_item_by_unique_id(unique_id)
        if item_id:
            info = morld.get_item_info(item_id)
            if info and info.get("name"):
                return info["name"]
    except Exception:
        pass
    return unique_id


# ============================================
# S02 조건 플러그인 등록
# ============================================

def register_s02_conditions():
    """S02 전용 조건 타입 등록. 초기화 시 호출."""
    # reach를 S02 확장판으로 덮어쓰기 (location_unique_id 지원)
    register_condition_type("reach", _check_reach_s02, _desc_reach_s02)
    register_condition_type("meet", _check_meet, _desc_meet)
    register_condition_type("collect", _check_collect, _desc_collect)
    register_condition_type("deliver", _check_deliver, _desc_deliver)
    register_condition_type("talk", _check_talk, _desc_talk)
    register_condition_type("meet_anyone", _check_meet_anyone, _desc_meet_anyone)
