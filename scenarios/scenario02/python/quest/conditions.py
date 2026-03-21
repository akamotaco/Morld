# quest/conditions.py
"""
퀘스트 조건 정의 및 체크
"""

from typing import Dict, Any, Optional
import morld


# ============================================
# 조건 체크 함수
# ============================================

def check_condition(player_id: int, condition: dict, quest_id: str) -> bool:
    """
    퀘스트 조건 충족 여부 체크

    Args:
        player_id: 플레이어 ID
        condition: 조건 dict
        quest_id: 퀘스트 ID (조건별 상태 저장용)

    Returns:
        조건 충족 여부
    """
    cond_type = condition.get("type")

    if cond_type == "reach":
        return _check_reach(player_id, condition)
    elif cond_type == "meet":
        return _check_meet(player_id, condition, quest_id)
    elif cond_type == "collect":
        return _check_collect(player_id, condition)
    elif cond_type == "deliver":
        return _check_deliver(player_id, condition, quest_id)
    elif cond_type == "talk":
        return _check_talk(player_id, condition, quest_id)
    elif cond_type == "wait":
        return _check_wait(player_id, condition, quest_id)
    elif cond_type == "prop":
        return _check_prop(player_id, condition)
    elif cond_type == "all":
        return _check_all(player_id, condition, quest_id)
    elif cond_type == "any":
        return _check_any(player_id, condition, quest_id)
    elif cond_type == "quest_completed":
        return _check_quest_completed(condition)
    elif cond_type == "meet_anyone":
        return _check_meet_anyone(player_id, condition)

    return False


def get_condition_description(condition: dict) -> str:
    """
    조건의 사람이 읽을 수 있는 설명 반환

    Args:
        condition: 조건 dict

    Returns:
        설명 문자열
    """
    cond_type = condition.get("type")

    if cond_type == "reach":
        region_id = condition.get("region_id", 0)
        location_id = condition.get("location_id", 0)
        location_name = _get_location_name(region_id, location_id)
        return f"{location_name}에 도착"

    elif cond_type == "meet":
        target = condition.get("target", "???")
        target_name = _get_npc_name(target)
        return f"{target_name}와(과) 만나기"

    elif cond_type == "collect":
        item = condition.get("item", "???")
        count = condition.get("count", 1)
        item_name = _get_item_name(item)
        if count == 1:
            return f"{item_name} 수집"
        return f"{item_name} {count}개 수집"

    elif cond_type == "deliver":
        item = condition.get("item", "???")
        target = condition.get("target", "???")
        count = condition.get("count", 1)
        return f"{target}에게 {item} {count}개 전달"

    elif cond_type == "talk":
        target = condition.get("target", "???")
        return f"{target}와(과) 대화"

    elif cond_type == "wait":
        hours = condition.get("hours", 0)
        return f"{hours}시간 경과"

    elif cond_type == "prop":
        prop = condition.get("prop", "???")
        value = condition.get("value", 0)
        return f"{prop} >= {value}"

    elif cond_type == "all":
        sub_conditions = condition.get("conditions", [])
        return f"모든 조건 충족 ({len(sub_conditions)}개)"

    elif cond_type == "any":
        sub_conditions = condition.get("conditions", [])
        return f"조건 중 하나 충족 ({len(sub_conditions)}개)"

    elif cond_type == "quest_completed":
        quest = condition.get("quest", "???")
        return f"퀘스트 '{quest}' 완료"

    elif cond_type == "meet_anyone":
        return "누군가와 만나기"

    return "알 수 없는 조건"


# ============================================
# 개별 조건 체크
# ============================================

def _check_reach(player_id: int, condition: dict) -> bool:
    """위치 도착 조건 체크

    조건 형태:
      {"type": "reach", "region_id": 0, "location_id": 5}  — 고정 위치
      {"type": "reach", "location_unique_id": "hunting_ground"}  — unique_id 기반 (이주 안전)
      {"type": "reach", "region_id": 0}  — region만 지정
    """
    player_loc = morld.get_unit_location(player_id)
    if not player_loc:
        return False

    current_region, current_location = player_loc

    # unique_id 기반 동적 탐색 — 기존 registry 활용
    location_uid = condition.get("location_unique_id")
    if location_uid:
        from assets.registry import get_instance_id
        loc_id = get_instance_id(location_uid)
        if loc_id is None:
            return False
        # registry는 location_id를 반환, region은 get_unit_location으로 비교
        return current_location == loc_id

    target_region = condition.get("region_id")
    target_location = condition.get("location_id")

    # region_id만 지정된 경우
    if target_location is None:
        return current_region == target_region

    return current_region == target_region and current_location == target_location


def _check_meet(player_id: int, condition: dict, quest_id: str) -> bool:
    """NPC 만남 조건 체크"""
    target_unique_id = condition.get("target")
    if not target_unique_id:
        return False

    # 퀘스트 진행 중 만났는지 기록 확인
    props = morld.get_unit_props(player_id)
    if not props:
        return False

    meet_key = f"퀘스트:{quest_id}:meet:{target_unique_id}"
    return props.get(meet_key, 0) >= 1


def _check_collect(player_id: int, condition: dict) -> bool:
    """아이템 수집 조건 체크"""
    item_unique_id = condition.get("item")
    required_count = condition.get("count", 1)

    if not item_unique_id:
        return False

    # 아이템 보유 개수 확인
    current_count = morld.get_item_count(player_id, item_unique_id)
    return current_count >= required_count


def _check_deliver(player_id: int, condition: dict, quest_id: str) -> bool:
    """아이템 전달 조건 체크"""
    target_unique_id = condition.get("target")
    item_unique_id = condition.get("item")
    required_count = condition.get("count", 1)

    if not target_unique_id or not item_unique_id:
        return False

    # 전달 기록 확인
    props = morld.get_unit_props(player_id)
    if not props:
        return False

    deliver_key = f"퀘스트:{quest_id}:deliver:{target_unique_id}:{item_unique_id}"
    delivered_count = props.get(deliver_key, 0)
    return delivered_count >= required_count


def _check_talk(player_id: int, condition: dict, quest_id: str) -> bool:
    """대화 조건 체크"""
    target_unique_id = condition.get("target")
    dialog_id = condition.get("dialog_id")

    if not target_unique_id:
        return False

    props = morld.get_unit_props(player_id)
    if not props:
        return False

    if dialog_id:
        talk_key = f"퀘스트:{quest_id}:talk:{target_unique_id}:{dialog_id}"
    else:
        talk_key = f"퀘스트:{quest_id}:talk:{target_unique_id}"

    return props.get(talk_key, 0) >= 1


def _check_wait(player_id: int, condition: dict, quest_id: str) -> bool:
    """시간 경과 조건 체크"""
    required_hours = condition.get("hours", 0)

    props = morld.get_unit_props(player_id)
    if not props:
        return False

    # 퀘스트 수락 시각 확인 (0 이하는 "없음"과 동등)
    accept_time_key = f"퀘스트:{quest_id}:수락시각"
    accept_time = props.get(accept_time_key, 0)
    if accept_time <= 0:
        return False

    current_time = morld.get_game_time()
    elapsed_millis = current_time - accept_time
    elapsed_hours = elapsed_millis / 3_600_000

    return elapsed_hours >= required_hours


def _check_prop(player_id: int, condition: dict) -> bool:
    """속성 값 조건 체크"""
    prop_name = condition.get("prop")
    required_value = condition.get("value", 0)
    target = condition.get("target")  # None이면 플레이어

    if not prop_name:
        return False

    if target:
        # 특정 유닛의 prop 체크
        target_id = morld.find_unit_by_unique_id(target)
        if not target_id:
            return False
        props = morld.get_unit_props(target_id)
    else:
        props = morld.get_unit_props(player_id)

    if not props:
        return False

    current_value = props.get(prop_name, 0)
    return current_value >= required_value


def _check_all(player_id: int, condition: dict, quest_id: str) -> bool:
    """모든 조건 충족 (AND)"""
    sub_conditions = condition.get("conditions", [])

    for sub_cond in sub_conditions:
        if not check_condition(player_id, sub_cond, quest_id):
            return False

    return True


def _check_any(player_id: int, condition: dict, quest_id: str) -> bool:
    """하나라도 충족 (OR)"""
    sub_conditions = condition.get("conditions", [])

    for sub_cond in sub_conditions:
        if check_condition(player_id, sub_cond, quest_id):
            return True

    return False


def _check_quest_completed(condition: dict) -> bool:
    """다른 퀘스트 완료 여부 체크"""
    from quest import quest_manager, QuestStatus

    target_quest = condition.get("quest")
    if not target_quest:
        return False

    status = quest_manager.get_quest_status(target_quest)
    return status in (QuestStatus.COMPLETED, QuestStatus.FINISHED)


def _check_meet_anyone(player_id: int, condition: dict) -> bool:
    """
    아무 NPC와 만남 조건 체크

    관계:*:진척도 값들의 합산이 1 이상이면 True
    (first meet 이벤트 후 진척도가 1로 설정됨)
    """
    props = morld.get_unit_props(player_id)
    if not props:
        return False

    # "관계:*:진척도" 패턴의 prop 합산
    total_progress = 0
    for key, value in props.items():
        if key.startswith("관계:") and key.endswith(":진척도"):
            total_progress += value

    return total_progress >= 1


# ============================================
# 조건 기록 함수 (이벤트에서 호출)
# ============================================

def record_meet(player_id: int, target_unique_id: str, quest_id: str):
    """만남 조건 기록"""
    meet_key = f"퀘스트:{quest_id}:meet:{target_unique_id}"
    morld.set_unit_prop(player_id, meet_key, 1)


def record_talk(player_id: int, target_unique_id: str, quest_id: str, dialog_id: Optional[str] = None):
    """대화 조건 기록"""
    if dialog_id:
        talk_key = f"퀘스트:{quest_id}:talk:{target_unique_id}:{dialog_id}"
    else:
        talk_key = f"퀘스트:{quest_id}:talk:{target_unique_id}"
    morld.set_unit_prop(player_id, talk_key, 1)


def record_deliver(player_id: int, target_unique_id: str, item_unique_id: str, quest_id: str, count: int = 1):
    """전달 조건 기록"""
    deliver_key = f"퀘스트:{quest_id}:deliver:{target_unique_id}:{item_unique_id}"
    props = morld.get_unit_props(player_id)
    current = props.get(deliver_key, 0) if props else 0
    morld.set_unit_prop(player_id, deliver_key, current + count)


# ============================================
# 이름 조회 헬퍼 함수
# ============================================

def _get_location_name(region_id: int, location_id: int) -> str:
    """
    Region과 Location ID로 위치 이름 조회

    Returns:
        위치 이름 (예: "도시 입구", "저택 현관")
        조회 실패 시 "지역 {region_id}-{location_id}" 형태 반환
    """
    try:
        location_info = morld.get_location_info(region_id, location_id)
        if location_info and location_info.get("name"):
            return location_info["name"]
    except Exception:
        pass
    return f"지역 {region_id}-{location_id}"


def _get_npc_name(unique_id: str) -> str:
    """
    NPC unique_id로 이름 조회

    Returns:
        NPC 이름 (예: "밀라", "세라")
        조회 실패 시 unique_id 그대로 반환
    """
    try:
        unit_id = morld.find_unit_by_unique_id(unique_id)
        if unit_id:
            unit_info = morld.get_unit_info(unit_id)
            if unit_info and unit_info.get("name"):
                return unit_info["name"]
    except Exception:
        pass
    return unique_id


def _get_item_name(unique_id: str) -> str:
    """
    아이템 unique_id로 이름 조회

    Returns:
        아이템 이름 (예: "사과", "낚시대")
        조회 실패 시 unique_id 그대로 반환

    Note:
        현재 morld API에 unique_id로 아이템 조회 함수가 없으므로
        아이템 레지스트리에서 직접 조회
    """
    try:
        from assets.registry import get_item_class
        item_class = get_item_class(unique_id)
        if item_class and hasattr(item_class, "name"):
            return item_class.name
    except Exception:
        pass
    return unique_id
