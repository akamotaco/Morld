"""벌목 활동 핸들러"""
from .tool_activity import handle_tool_activity

_CHOP_CONFIG = {
    "capability": "can:chop",
    "activity_name": "벌목",
    "storage_need": ("material", "log", 5),
    "work_method": "npc_chop",
    "sound_id": "chop",
    "action_key": "chop",
    "store_categories": ["material"],
    "store_resolve": ["material"],
    "store_label": "통나무 저장",
    "eager_location": True,
}


def handle_chop(agent, entry):
    """벌목: 도구 탐색(can:chop) → 가져오기 → 나무 이동 → 벌목 → 저장 → 반납"""
    handle_tool_activity(agent, entry, _CHOP_CONFIG)
