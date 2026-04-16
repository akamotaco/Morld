# quest/rewards.py — S02 전용 퀘스트 보상
#
# 엔진 기본 보상 (prop, unlock_quest)은 engine/quest.py에서 제공.
# 여기는 S02 전용 보상만 정의하고 플러그인 등록.

import morld
from engine.quest import register_reward_type


# ============================================
# S02 전용 보상 처리
# ============================================

def _apply_item_reward(player_id, reward):
    """아이템 지급 보상"""
    item_unique_id = reward.get("item")
    count = reward.get("count", 1)
    if not item_unique_id:
        return False
    item_id = morld.find_item_by_unique_id(item_unique_id)
    if item_id is None:
        print("[Quest Reward] Unknown item: " + str(item_unique_id))
        return False
    import inventory as inv_module
    inv_module.safe_give_item(player_id, item_id, count)
    return True


def _desc_item_reward(reward):
    item = reward.get("item", "???")
    count = reward.get("count", 1)
    return item + " x" + str(count)


def _apply_coin_reward(player_id, reward):
    """코인 보상"""
    value = reward.get("value", 0)
    if value <= 0:
        return False
    try:
        from assets.registry import get_or_create_item_id
        import inventory as inv_module
        coin_id = get_or_create_item_id("coin")
        if coin_id is not None:
            inv_module.safe_give_item(player_id, coin_id, value)
            return True
    except Exception as e:
        print("[Quest Reward] Coin error: " + str(e))
    return False


def _desc_coin_reward(reward):
    value = reward.get("value", 0)
    return str(value) + "코인"


def _apply_unlock_location_reward(player_id, reward):
    """장소 해금 보상"""
    region_id = reward.get("region_id")
    location_id = reward.get("location_id")
    if region_id is None or location_id is None:
        return False
    unlock_key = "장소:" + str(region_id) + ":" + str(location_id) + ":해금"
    morld.set_unit_prop(player_id, unlock_key, 1)
    return True


def _desc_unlock_location_reward(reward):
    region_id = reward.get("region_id", 0)
    location_id = reward.get("location_id", 0)
    return "장소 해금: " + str(region_id) + "-" + str(location_id)


# ============================================
# S02 보상 플러그인 등록
# ============================================

def register_s02_rewards():
    """S02 전용 보상 타입 등록. 초기화 시 호출."""
    register_reward_type("item", _apply_item_reward, _desc_item_reward)
    register_reward_type("coin", _apply_coin_reward, _desc_coin_reward)
    register_reward_type("unlock_location", _apply_unlock_location_reward, _desc_unlock_location_reward)
