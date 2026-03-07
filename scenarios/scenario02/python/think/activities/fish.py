"""낚시 활동 핸들러"""
from .tool_activity import handle_tool_activity

_FISH_CONFIG = {
    "capability": "can:fish",
    "activity_name": "낚시",
    "storage_need": ("food_ingredient", "food_fish", 3),
    "work_method": "npc_fish",
    "sound_id": "splash",
    "action_key": "fish",
    "store_categories": ["food", "food_ingredient", "drink_ingredient"],
    "store_resolve": ["food_ingredient", "food"],
    "store_label": "물고기 저장",
    "eager_location": False,
}


def handle_fish(agent, entry):
    """낚시: 도구 탐색(can:fish) → 가져오기 → 낚시터 이동 → 낚시 → 저장 → 반납"""
    handle_tool_activity(agent, entry, _FISH_CONFIG)


_FISH_HOBBY_CONFIG = {**_FISH_CONFIG, "mode": "hobby"}


def handle_fish_hobby(agent, entry):
    """취미 낚시: 낚시 → 수확물 인벤토리 보관 → 도구 반납"""
    handle_tool_activity(agent, entry, _FISH_HOBBY_CONFIG)
