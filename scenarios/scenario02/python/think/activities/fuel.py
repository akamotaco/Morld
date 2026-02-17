"""연료 수집 활동 핸들러

NPC가 나뭇가지를 주워 모아서 열원에 장전하는 활동.
Phase flow: idle → going_to_tree → going_to_heat_source
"""
import morld
from .helpers import get_object_x_from_info


def handle_fuel(agent, entry):
    """연료수집: 나뭇가지 있는 나무 → 줍기 → 열원으로 이동 → 장전"""
    phase = agent._activity_phase

    if phase == "idle":
        # 1. 연료 필요한 열원 찾기
        target_source = find_heat_source_needing_fuel(agent)
        if not target_source:
            # 연료 충분 → 나머지 시간 대기
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("연료수집", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            agent._action_taken = True
            return

        # 2. 나뭇가지 있는 나무 찾기
        from .helpers import resolve_branch_tree
        tree_target = resolve_branch_tree(agent, cross_region=False)
        if not tree_target:
            return  # 나무 없음 → 디스패치 루프가 "할 일 없음" 폴백

        agent._activity_state["fuel_target"] = target_source
        agent._activity_state["tree_target"] = tree_target
        agent._activity_phase = "going_to_tree"

    elif phase == "going_to_tree":
        target = agent._activity_state.get("tree_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 도착 → 나뭇가지 줍기 (최대 3개)
            from assets.objects import get_instance
            obj_id = target.get("object_id")
            if obj_id:
                obj = get_instance(obj_id)
                if obj and hasattr(obj, "npc_gather_branch"):
                    for _ in range(3):
                        if not obj.npc_gather_branch(agent.unit_id):
                            break
            agent._activity_phase = "going_to_heat_source"
            agent._do_instant_action("나뭇가지 줍기", "gather_branch")
        else:
            agent._move_to(target, "나뭇가지 줍기")

    elif phase == "going_to_heat_source":
        target = agent._activity_state.get("fuel_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 도착 → 인벤토리의 branch/log를 열원에 장전
            _load_all_fuel(agent, target["object_id"])
            agent._activity_phase = "idle"
            agent._do_instant_action("연료 투입", "load_fuel")
        else:
            agent._move_to(target, "연료 장전")


# ========================================
# 헬퍼 함수
# ========================================

def find_heat_source_needing_fuel(agent):
    """거처 내 연료 필요한 열원 찾기"""
    import fuel
    from assets.objects import _location_objects, get_instance
    from assets.objects.furniture import PortableStove, DrumBath

    home_region = agent._get_home_region()
    for (r, l), obj_ids in _location_objects.items():
        if r != home_region:
            continue
        for obj_id in obj_ids:
            if fuel.is_fuel_source(obj_id) and fuel.needs_fuel(obj_id):
                obj = get_instance(obj_id)
                if isinstance(obj, (PortableStove, DrumBath)):
                    return {
                        "region_id": r,
                        "location_id": l,
                        "x": get_object_x_from_info(obj_id),
                        "object_id": obj_id,
                    }
    return None


def _load_all_fuel(agent, heat_source_id):
    """인벤토리의 모든 branch/log를 열원에 장전"""
    import fuel
    from assets.registry import get_unique_id

    inv = morld.get_unit_inventory(agent.unit_id)
    for item_id, count in list((inv or {}).items()):
        if count <= 0:
            continue
        uid = get_unique_id(item_id)
        if uid in ("branch", "log"):
            fuel.npc_load_fuel(agent.unit_id, heat_source_id, uid, count)
