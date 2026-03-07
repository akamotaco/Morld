"""요리 활동 핸들러"""
from .helpers import (find_food_in_container, find_npc_food,
                      find_stove_location, resolve_storage_container,
                      store_npc_items)


def handle_cook(agent, entry):
    """요리: 보관소 확인 → 재료 가져오기 → 화로/아궁이에서 조리 → 결과 저장"""
    phase = agent._activity_phase

    if phase == "idle":
        # 식재료 보관소로 이동
        agent._activity_phase = "checking_fridge"
        agent._do_instant_action("요리 준비", "brief")

    elif phase == "checking_fridge":
        target = agent._activity_state.get("fridge_target")
        if not target:
            target = resolve_storage_container(agent, "food_ingredient")
            if not target:
                return  # 보관소 없음 → 디스패치 루프가 "할 일 없음" 폴백
            agent._activity_state["fridge_target"] = target

        if agent._is_at(target):
            # 보관소에서 재료 가져오기
            from assets.objects import get_instance
            obj = get_instance(target["object_id"])
            if obj:
                food_uid = find_food_in_container(target["object_id"])
                if food_uid:
                    obj.npc_take_item(agent.unit_id, food_uid, 1)
                    agent._activity_phase = "going_to_stove"
                    agent._do_instant_action("재료 꺼내기", "take_item")
                    return
            # 재료 없음 → 디스패치 루프가 "할 일 없음" 폴백
            return
        else:
            agent._move_to(target, "냉장고 확인")

    elif phase == "going_to_stove":
        # 아궁이/화로 위치 탐색
        stove_target = agent._activity_state.get("stove_target")
        if not stove_target:
            stove_target = find_stove_location(agent)
            if not stove_target:
                agent._do_instant_action("대기", "abort")
                return
            agent._activity_state["stove_target"] = stove_target

        if agent._is_at(stove_target):
            # 도착 → 조리
            from assets.objects import get_instance
            obj_id = stove_target.get("object_id")
            cook_ok = False
            if obj_id:
                obj = get_instance(obj_id)
                if obj and hasattr(obj, "npc_cook"):
                    cook_ok = obj.npc_cook(agent.unit_id)
                    if cook_ok:
                        import sound
                        sound.emit_sound(agent.unit_id, "cooking")
            if cook_ok:
                agent._activity_phase = "storing_result"
                agent._do_instant_action("요리", "cook")
            else:
                # 불 꺼짐 등으로 요리 실패 → 재료 반납 후 idle
                agent._activity_phase = "storing_result"
                agent._do_instant_action("대기", "abort")
        else:
            agent._move_to(stove_target, "요리")

    elif phase == "storing_result":
        target = agent._activity_state.get("storage_target")
        if not target:
            target = resolve_storage_container(agent, "food_ingredient")
            if not target:
                target = resolve_storage_container(agent, "food")
            if not target:
                agent._do_instant_action("대기", "abort")
                return
            agent._activity_state["storage_target"] = target

        if agent._is_at(target):
            store_npc_items(agent, categories=["food", "food_ingredient", "drink_ingredient"])
            agent._activity_phase = "idle"
            agent._do_instant_action("요리 저장", "store_item")
        else:
            agent._move_to(target, "요리 저장")
