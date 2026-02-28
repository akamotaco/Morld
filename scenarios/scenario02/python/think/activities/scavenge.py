"""물자수집 활동 핸들러"""
import morld
from .resource_activity import handle_resource_activity


def _resolve_target(agent):
    from think.activity_resolver import resolve_activity_location
    return resolve_activity_location(
        agent.unit_id, "물자수집", agent._get_home_region()
    )


def _do_work(agent, target):
    from assets.objects import get_instance
    obj_id = target.get("object_id")
    if obj_id:
        obj = get_instance(obj_id)
        if obj:
            inventory = morld.get_unit_inventory(obj_id)
            if inventory:
                from assets.registry import get_unique_id
                for item_id, count in inventory.items():
                    if count > 0:
                        uid = get_unique_id(item_id)
                        if uid:
                            obj.npc_take_item(agent.unit_id, uid, 1)
                            import sound
                            sound.emit_sound(agent.unit_id, "crash")
                            break


_SCAVENGE_CONFIG = {
    "activity_name": "물자수집",
    "resolve_target": _resolve_target,
    "do_work": _do_work,
    "action_key": "scavenge",
    "work_label": "물자수집",
    "store_categories": ["food", "food_ingredient", "drink_ingredient"],
    "store_resolve": ["food_ingredient", "food"],
    "store_label": "물자 저장",
}


def handle_scavenge(agent, entry):
    """물자수집: ScavengeableObject에서 아이템 수집 → 은신처 저장"""
    handle_resource_activity(agent, entry, _SCAVENGE_CONFIG)
