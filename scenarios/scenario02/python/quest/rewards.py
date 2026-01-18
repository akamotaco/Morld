# quest/rewards.py
"""
퀘스트 보상 처리
"""

from typing import Dict, Any
import morld


def apply_reward(player_id: int, reward: dict) -> bool:
    """
    보상 지급

    Args:
        player_id: 플레이어 ID
        reward: 보상 dict

    Returns:
        성공 여부
    """
    reward_type = reward.get("type")

    if reward_type == "item":
        return _apply_item_reward(player_id, reward)
    elif reward_type == "prop":
        return _apply_prop_reward(player_id, reward)
    elif reward_type == "unlock_quest":
        return _apply_unlock_quest_reward(reward)
    elif reward_type == "unlock_location":
        return _apply_unlock_location_reward(player_id, reward)

    return False


def get_reward_description(reward: dict) -> str:
    """
    보상 설명 반환

    Args:
        reward: 보상 dict

    Returns:
        설명 문자열
    """
    reward_type = reward.get("type")

    if reward_type == "item":
        item = reward.get("item", "???")
        count = reward.get("count", 1)
        return f"{item} x{count}"

    elif reward_type == "prop":
        prop = reward.get("prop", "???")
        value = reward.get("value", 0)
        sign = "+" if value >= 0 else ""
        return f"{prop} {sign}{value}"

    elif reward_type == "unlock_quest":
        quest = reward.get("quest", "???")
        return f"퀘스트 해금: {quest}"

    elif reward_type == "unlock_location":
        region_id = reward.get("region_id", 0)
        location_id = reward.get("location_id", 0)
        return f"장소 해금: {region_id}-{location_id}"

    return "알 수 없는 보상"


# ============================================
# 개별 보상 처리
# ============================================

def _apply_item_reward(player_id: int, reward: dict) -> bool:
    """아이템 지급 보상"""
    item_unique_id = reward.get("item")
    count = reward.get("count", 1)

    if not item_unique_id:
        return False

    # unique_id로 item_id 조회
    item_id = morld.find_item_by_unique_id(item_unique_id)
    if item_id is None:
        print(f"[Quest Reward] Unknown item: {item_unique_id}")
        return False

    morld.give_item(player_id, item_id, count)
    return True


def _apply_prop_reward(player_id: int, reward: dict) -> bool:
    """속성 변경 보상"""
    target = reward.get("target")  # None 또는 "player"면 플레이어
    prop_name = reward.get("prop")
    value = reward.get("value", 0)

    if not prop_name:
        return False

    # 대상 결정
    if target and target != "player":
        target_id = morld.find_unit_by_unique_id(target)
        if not target_id:
            print(f"[Quest Reward] Unknown target: {target}")
            return False
    else:
        target_id = player_id

    # 상대값 적용 (modify)
    morld.modify_prop(target_id, prop_name, value)
    return True


def _apply_unlock_quest_reward(reward: dict) -> bool:
    """퀘스트 해금 보상"""
    quest_id = reward.get("quest")

    if not quest_id:
        return False

    # 해금은 자동으로 처리됨 (선행 조건 체크에서)
    # 여기서는 로그만 남김
    print(f"[Quest Reward] Quest unlocked: {quest_id}")
    return True


def _apply_unlock_location_reward(player_id: int, reward: dict) -> bool:
    """장소 해금 보상"""
    region_id = reward.get("region_id")
    location_id = reward.get("location_id")

    if region_id is None or location_id is None:
        return False

    # 장소 해금 prop 설정
    unlock_key = f"장소:{region_id}:{location_id}:해금"
    morld.set_unit_prop(player_id, unlock_key, 1)
    return True
