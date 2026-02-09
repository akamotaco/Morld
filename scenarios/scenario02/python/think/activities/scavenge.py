"""물자수집 활동 핸들러"""
import morld
from .helpers import store_food_items


def handle_scavenge(agent, entry):
    """물자수집: ScavengeableObject에서 아이템 수집 → 은신처 저장"""
    phase = agent._activity_phase

    if phase == "idle":
        from think.activity_resolver import resolve_activity_location
        target = resolve_activity_location(
            agent.unit_id, "물자수집", agent._get_home_region()
        )
        if target:
            agent._activity_state["scavenge_target"] = target
            agent._activity_phase = "going_to_resource"
        else:
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("물자수집", max(remaining, 1))
            agent._action_taken = True

    elif phase == "going_to_resource":
        target = agent._activity_state.get("scavenge_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 도착 → 아이템 수집
            from assets.objects import get_instance
            obj_id = target.get("object_id")
            if obj_id:
                obj = get_instance(obj_id)
                if obj:
                    # npc_take_item 사용 (base.py 헬퍼)
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
            agent._activity_phase = "going_to_storage"
            agent._action_taken = True
        else:
            agent._move_to(target, "물자수집")

    elif phase == "going_to_storage":
        target = agent.food_storage_location
        if agent._is_at(target):
            store_food_items(agent)
            agent._activity_phase = "idle"
            agent._action_taken = True
        else:
            agent._move_to(target, "물자 저장")
