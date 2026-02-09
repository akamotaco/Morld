"""요리 활동 핸들러"""
from .helpers import find_food_in_container, find_npc_food, find_stove_location


def handle_cook(agent, entry):
    """요리: 냉장고 확인 → 재료 가져오기 → 화로/아궁이에서 조리 → 결과 저장"""
    phase = agent._activity_phase

    if phase == "idle":
        # 냉장고로 이동
        agent._activity_phase = "checking_fridge"

    elif phase == "checking_fridge":
        target = agent.food_storage_location
        if agent._is_at(target):
            # 냉장고에서 재료 가져오기
            from assets.registry import get_instance_id
            from assets.objects import get_instance
            storage_id = get_instance_id(agent.food_storage_unique_id)
            if storage_id:
                obj = get_instance(storage_id)
                if obj:
                    food_uid = find_food_in_container(storage_id)
                    if food_uid:
                        obj.npc_take_item(agent.unit_id, food_uid, 1)
                        agent._activity_phase = "going_to_stove"
                        agent._action_taken = True
                        return
            # 재료 없음 → 대기
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("요리", max(remaining, 1))
            agent._action_taken = True
        else:
            agent._move_to(target, "냉장고 확인")

    elif phase == "going_to_stove":
        # 아궁이/화로 위치 탐색
        stove_target = agent._activity_state.get("stove_target")
        if not stove_target:
            stove_target = find_stove_location(agent)
            if not stove_target:
                agent._activity_phase = "idle"
                agent._action_taken = True
                return
            agent._activity_state["stove_target"] = stove_target

        if agent._is_at(stove_target):
            # 도착 → 조리
            from assets.objects import get_instance
            obj_id = stove_target.get("object_id")
            if obj_id:
                obj = get_instance(obj_id)
                if obj and hasattr(obj, "npc_cook"):
                    obj.npc_cook(agent.unit_id)
                    import sound
                    sound.emit_sound(agent.unit_id, "cooking")
            agent._activity_phase = "storing_result"
            agent._action_taken = True
        else:
            agent._move_to(stove_target, "요리")

    elif phase == "storing_result":
        target = agent.food_storage_location
        if agent._is_at(target):
            from assets.registry import get_instance_id
            from assets.objects import get_instance
            storage_id = get_instance_id(agent.food_storage_unique_id)
            if storage_id:
                obj = get_instance(storage_id)
                if obj:
                    food = find_npc_food(agent.unit_id)
                    while food:
                        obj.npc_store_item(agent.unit_id, food["unique_id"])
                        food = find_npc_food(agent.unit_id)
            agent._activity_phase = "idle"
            agent._action_taken = True
        else:
            agent._move_to(target, "요리 저장")
