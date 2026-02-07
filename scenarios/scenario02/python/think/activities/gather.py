"""채집→저장 활동 핸들러"""
from .helpers import find_npc_food


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
        target = agent.food_storage_location
        if agent._is_at(target):
            # 인벤토리의 채집물을 저장소에 넣기
            from assets.registry import get_instance_id
            from assets.objects import get_instance
            storage_id = get_instance_id(agent.food_storage_unique_id)
            if storage_id:
                obj = get_instance(storage_id)
                if obj:
                    # 모든 음식 아이템 저장
                    food = find_npc_food(agent.unit_id)
                    while food:
                        obj.npc_store_item(agent.unit_id, food["unique_id"])
                        food = find_npc_food(agent.unit_id)
            agent._activity_phase = "idle"
            agent._action_taken = True
        else:
            agent._move_to(target, "재료 저장")
