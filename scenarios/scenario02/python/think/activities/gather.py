"""채집→저장 활동 핸들러"""


def handle_gather_store(agent, entry):
    """채집→저장: 채집 대상 탐색 → 채집 → 저장소에 저장"""
    phase = agent._activity_phase

    if phase == "idle":
        from think.activity_resolver import resolve_activity_location
        target = resolve_activity_location(
            agent.unit_id, "채집", agent._get_home_region()
        )
        if target:
            agent._activity_state["gather_target"] = target
            agent._activity_phase = "going_to_resource"
        else:
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("채집", max(remaining, 1))
            agent._action_taken = True

    elif phase == "going_to_resource":
        target = agent._activity_state.get("gather_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            from assets.objects import get_instance
            obj_id = target.get("object_id")
            if obj_id:
                obj = get_instance(obj_id)
                if obj and hasattr(obj, "npc_take_resource"):
                    obj.npc_take_resource(agent.unit_id, count=1)
            agent._activity_phase = "going_to_storage"
            agent._action_taken = True
        else:
            agent._move_to(target, "채집")

    elif phase == "going_to_storage":
        target = agent._activity_state.get("storage_target")
        if not target:
            from .helpers import resolve_storage_container
            target = resolve_storage_container(agent, "food_ingredient")
            if not target:
                target = resolve_storage_container(agent, "food")
            if not target:
                agent._activity_phase = "idle"
                agent._action_taken = True
                return
            agent._activity_state["storage_target"] = target

        if agent._is_at(target):
            from .helpers import store_npc_items
            store_npc_items(agent, categories=["food", "food_ingredient", "drink_ingredient"])
            agent._activity_phase = "idle"
            agent._action_taken = True
        else:
            agent._move_to(target, "재료 저장")
