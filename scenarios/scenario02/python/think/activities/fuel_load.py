"""연료장전 활동 핸들러

NPC가 보관소에서 연료(나무조각/나뭇가지/통나무)를 꺼내 열원에 장전하는 활동.
기존 연료수집(fuel.py)은 나뭇가지를 나무에서 직접 주워 열원에 투입하지만,
이 핸들러는 보관소에 비축된 연료를 열원으로 운반한다.
Phase flow: idle → going_to_storage → going_to_heat_source
"""
import morld
from .helpers import get_object_x_from_info


def handle_fuel_load(agent, entry):
    """연료장전: 열원 탐색 → 보관소에서 연료 가져오기 → 열원에 장전"""
    phase = agent._activity_phase

    if phase == "idle":
        # 1. 연료 필요한 열원 찾기
        target_source = _find_any_heat_source_needing_fuel(agent)
        if not target_source:
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("연료장전", max(remaining, 1))
            agent._action_taken = True
            return

        # 2. 연료 보관소 확인
        from .helpers import resolve_storage_container
        storage = resolve_storage_container(agent, "material")
        if not storage:
            return  # 보관소 없음 → 디스패치 루프가 "할 일 없음" 폴백

        # 보관소에 연료 아이템 있는지 확인
        from assets.objects import get_instance
        obj = get_instance(storage["object_id"])
        if not obj or not _has_fuel_items(obj):
            agent._skip_dynamic_activity(entry)
            return

        agent._activity_state["fuel_target"] = target_source
        agent._activity_state["storage_target"] = storage
        agent._activity_phase = "going_to_storage"

    elif phase == "going_to_storage":
        target = agent._activity_state.get("storage_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 보관소에서 연료 아이템 가져오기
            from assets.objects import get_instance
            obj = get_instance(target["object_id"])
            if obj:
                _take_fuel_items(agent, obj)
            agent._activity_phase = "going_to_heat_source"
            agent._do_instant_action("연료 꺼내기", "take_item")
        else:
            agent._move_to(target, "연료 가져오기")

    elif phase == "going_to_heat_source":
        target = agent._activity_state.get("fuel_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 열원에 연료 장전
            _load_all_fuel(agent, target["object_id"])
            agent._activity_phase = "idle"
            agent._do_instant_action("연료 투입", "load_fuel")
        else:
            agent._move_to(target, "연료 장전")


# ========================================
# 헬퍼 함수
# ========================================

# 우선 운반 순서: 나무조각 > 나뭇가지 > 통나무
_FUEL_ITEM_UIDS = ("wood_chip", "branch", "log")


def _find_any_heat_source_needing_fuel(agent):
    """거처 내 연료 필요한 열원 찾기 (종류 무관)"""
    import fuel
    from assets.objects import _location_objects

    home_region = agent._get_home_region()
    for (r, l), obj_ids in _location_objects.items():
        if r != home_region:
            continue
        for obj_id in obj_ids:
            if fuel.is_fuel_source(obj_id) and fuel.needs_fuel(obj_id):
                return {
                    "region_id": r,
                    "location_id": l,
                    "x": get_object_x_from_info(obj_id),
                    "object_id": obj_id,
                }
    return None


def _has_fuel_items(container_obj):
    """컨테이너에 연료 아이템이 있는지 확인"""
    for uid in _FUEL_ITEM_UIDS:
        if container_obj.get_item_count(uid) > 0:
            return True
    return False


def _take_fuel_items(agent, container_obj):
    """보관소에서 연료 아이템 가져오기 (우선순위: 나무조각 > 나뭇가지 > 통나무)"""
    for uid in _FUEL_ITEM_UIDS:
        count = container_obj.get_item_count(uid)
        if count > 0:
            take = min(count, 3)  # 최대 3개
            container_obj.npc_take_item(agent.unit_id, uid, take)
            return


def _load_all_fuel(agent, heat_source_id):
    """인벤토리의 모든 연료 아이템을 열원에 장전"""
    import fuel
    from assets.registry import get_unique_id

    inv = morld.get_unit_inventory(agent.unit_id)
    for item_id, count in list((inv or {}).items()):
        if count <= 0:
            continue
        uid = get_unique_id(item_id)
        if uid in _FUEL_ITEM_UIDS:
            fuel.npc_load_fuel(agent.unit_id, heat_source_id, uid, count)
