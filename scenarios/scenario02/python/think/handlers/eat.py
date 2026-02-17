"""식사/배변 핸들러 (Tier 3/4 인터럽트)

식사: 인벤토리 확인 → 식량 보관 이동 → 음식 가져오기 → 식사
배변: 화장실 탐색 → 이동 → 사용
"""
import morld
from think.activities.helpers import find_npc_food as _find_npc_food
from think.activities.helpers import find_food_in_container as _find_food_in_container


# ========================================
# 식사 핸들러 (배고픔 인터럽트)
# ========================================

def _handle_eat(agent):
    """식사: 인벤토리 확인 → 식량 보관 이동 → 음식 가져오기 → 식사"""
    phase = agent._memory["hunger_phase"]

    if phase == "idle":
        # 인벤토리에 음식이 있으면 바로 식사
        food = _find_npc_food(agent.unit_id)
        if food:
            agent._memory["hunger_phase"] = "eating"
            _handle_eat(agent)
            return
        # 없으면 식량 보관소로 이동
        agent._memory["hunger_phase"] = "going_to_storage"
        _handle_eat(agent)
        return

    elif phase == "going_to_storage":
        target = agent._memory.get("hunger_target")
        if not target:
            from think.activities.helpers import resolve_storage_container
            target = resolve_storage_container(agent, "food_ingredient")
            if not target:
                target = resolve_storage_container(agent, "food")
            if not target:
                agent._memory["hunger_phase"] = None
                agent._do_instant_action("대기", "abort")
                return
            agent._memory["hunger_target"] = target

        if agent._is_at(target):
            agent._memory["hunger_phase"] = "taking_food"
            agent._do_instant_action("음식 찾기", "take_item")
        else:
            agent._move_to(target, "식사")

    elif phase == "taking_food":
        target = agent._memory.get("hunger_target")
        if target:
            from assets.objects import get_instance
            obj = get_instance(target["object_id"])
            if obj:
                food_uid = _find_food_in_container(target["object_id"])
                if food_uid:
                    obj.npc_take_item(agent.unit_id, food_uid, 1)
                    agent._memory["hunger_phase"] = "eating"
                    agent._memory.pop("hunger_target", None)
                    agent._do_instant_action("음식 꺼내기", "take_item")
                    return
        # 음식 없음 → 포기
        agent._memory["hunger_phase"] = None
        agent._memory.pop("hunger_target", None)
        agent._do_instant_action("대기", "abort")

    elif phase == "eating":
        food = _find_npc_food(agent.unit_id)
        if food:
            import survival
            survival.npc_eat(agent.unit_id, food["satiety"])
            morld.remove_item(agent.unit_id, food["item_id"], 1)
        agent._memory["hunger_phase"] = None
        agent._memory.pop("hunger_target", None)
        agent._do_instant_action("식사", "eat")


# ========================================
# 배변 핸들러 (배변 인터럽트)
# ========================================

def _handle_excretion(agent):
    """배변: 화장실 이동 → 사용"""
    phase = agent._memory["excretion_phase"]

    if phase == "idle":
        # 화장실 타겟이 없으면 탐색
        if not agent._memory.get("excretion_target"):
            from think.facility_resolver import resolve_toilet
            toilet = resolve_toilet(agent)
            if not toilet:
                agent._memory["excretion_phase"] = None
                agent._do_instant_action("대기", "abort")
                return
            agent._memory["excretion_target"] = toilet
        agent._memory["excretion_phase"] = "going"
        _handle_excretion(agent)
        return

    elif phase == "going":
        target = agent._memory.get("excretion_target")
        if not target:
            agent._memory["excretion_phase"] = None
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(target):
            agent._memory["excretion_phase"] = "using"
            agent._do_instant_action("대기", "brief")
        else:
            agent._move_to(target, "화장실")

    elif phase == "using":
        try:
            import needs
            needs.set_excretion(agent.unit_id, 0)
        except ImportError:
            morld.set_unit_prop(agent.unit_id, "욕구:배변", 0)
        agent._memory["excretion_phase"] = None
        agent._memory.pop("excretion_target", None)
        agent._do_instant_action("화장실", "excretion")
