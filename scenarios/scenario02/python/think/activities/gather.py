"""채집→저장 활동 핸들러"""
from .resource_activity import handle_resource_activity


def _resolve_target(agent):
    from think.activity_resolver import resolve_activity_location
    return resolve_activity_location(
        agent.unit_id, "채집", agent._get_home_region()
    )


def _do_work(agent, target):
    from assets.objects import get_instance
    obj_id = target.get("object_id")
    if obj_id:
        obj = get_instance(obj_id)
        if obj and hasattr(obj, "npc_take_resource"):
            obj.npc_take_resource(agent.unit_id, count=1)


_GATHER_CONFIG = {
    "activity_name": "채집",
    "resolve_target": _resolve_target,
    "do_work": _do_work,
    "action_key": "gather",
    "work_label": "채집",
    "store_categories": ["food", "food_ingredient", "drink_ingredient"],
    "store_resolve": ["food_ingredient", "food"],
    "store_label": "재료 저장",
}


def handle_gather_store(agent, entry):
    """채집→저장: 채집 대상 탐색 → 채집 → 저장소에 저장"""
    handle_resource_activity(agent, entry, _GATHER_CONFIG)
