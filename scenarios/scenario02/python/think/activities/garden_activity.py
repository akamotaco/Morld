"""정원 활동 핸들러

텃밭(GardenBed) 관리: 수확 → 물주기 → 씨 심기 (우선순위 순)
수확물은 음식 저장소(kitchen_fridge)에 보관.

Phase: idle → going_to_garden → working → (storing_harvest → going_to_garden) → ...
"""
from .helpers import find_garden_location, find_npc_food
from assets.objects import get_instance


def handle_garden(agent, entry):
    """정원: 텃밭 이동 → 수확/물주기/심기 → 수확물 보관"""
    phase = agent._activity_phase

    if phase == "idle":
        garden = find_garden_location(agent)
        if not garden:
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("정원", max(remaining, 1))
            agent._action_taken = True
            return

        agent._activity_state["garden"] = garden
        agent._activity_phase = "going_to_garden"

    elif phase == "going_to_garden":
        target = agent._activity_state.get("garden")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            agent._activity_phase = "working"
        else:
            agent._move_to(target, "정원 가꾸기")

    elif phase == "working":
        garden_info = agent._activity_state.get("garden")
        if not garden_info:
            agent._activity_phase = "idle"
            return

        obj = get_instance(garden_info["object_id"])
        if not obj:
            agent._activity_phase = "idle"
            return

        # 우선순위: 수확 → 물주기 → 씨 심기
        if obj.has_harvestable():
            count = obj.npc_harvest(agent.unit_id)
            if count > 0:
                agent._insert_idle_job("수확", 20 * 60_000)
                agent._activity_phase = "storing_harvest"
                agent._action_taken = True
                return

        if obj.needs_water():
            obj.npc_water(agent.unit_id)
            agent._insert_idle_job("물주기", 10 * 60_000)
            agent._action_taken = True
            return

        if obj.has_empty_furrow():
            import random
            import garden as garden_mod
            codes = list(garden_mod.SEED_REGISTRY.keys())
            random.shuffle(codes)
            for code in codes:
                if obj.npc_plant(agent.unit_id, code):
                    agent._insert_idle_job("씨 심기", 10 * 60_000)
                    agent._action_taken = True
                    return

        # 할 일 없음 → 잔여 시간 대기
        remaining = agent._remaining_millis_in_entry(entry)
        agent._insert_idle_job("정원", max(remaining, 1))
        agent._action_taken = True

    elif phase == "storing_harvest":
        # 수확물을 음식 저장소에 보관
        target = agent.food_storage_location
        if agent._is_at(target):
            from assets.registry import get_instance_id
            storage_id = get_instance_id(agent.food_storage_unique_id)
            if storage_id:
                obj = get_instance(storage_id)
                if obj:
                    food = find_npc_food(agent.unit_id)
                    while food:
                        obj.npc_store_item(agent.unit_id, food["unique_id"])
                        food = find_npc_food(agent.unit_id)
            agent._insert_idle_job("정리", 5 * 60_000)
            agent._activity_phase = "going_to_garden"
            agent._action_taken = True
        else:
            agent._move_to(target, "수확물 보관")
