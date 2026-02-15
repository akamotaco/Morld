"""정원 활동 핸들러

텃밭(GardenBed) 관리: 수확 → 물주기 → 씨 심기 (우선순위 순)
수확물은 storage:food_ingredient 컨테이너에 동적 보관.
물주기는 can:water 도구 필요 (도구함에서 수거 → 사용 → 반납).

Phase: idle → (getting_tool) → going_to_garden → working → working_wait
       → (storing_harvest → going_to_garden) → returning_tool → idle
"""
import morld
from .helpers import find_garden_location, resolve_storage_container, store_npc_items
from assets.objects import get_instance


def handle_garden(agent, entry):
    """정원: 텃밭 이동 → 수확/물주기/심기 → 수확물 보관 → 도구 반납"""
    phase = agent._activity_phase

    if phase == "idle":
        _handle_idle(agent, entry)

    elif phase == "getting_tool":
        _handle_getting_tool(agent)

    elif phase == "going_to_garden":
        _handle_going_to_garden(agent)

    elif phase == "working":
        _handle_working(agent, entry)

    elif phase == "working_wait":
        _handle_working_wait(agent)

    elif phase == "storing_harvest":
        _handle_storing_harvest(agent)

    elif phase == "returning_tool":
        _handle_returning_tool(agent, entry)


# ========================================
# Phase 핸들러
# ========================================

def _handle_idle(agent, entry):
    """idle: 텃밭 탐색 → 작업 판단 → 도구 확보 또는 직행"""
    garden = find_garden_location(agent)
    if not garden:
        return  # 텃밭 없음 → "할 일 없음" 폴백

    obj = get_instance(garden["object_id"])
    if not obj:
        return

    agent._activity_state["garden"] = garden

    # 작업 판단: 수확 > 물주기 > 씨 심기
    if obj.has_harvestable():
        agent._activity_phase = "going_to_garden"
        return

    if obj.needs_water():
        tool = agent._find_tool_by_capability("can:water")
        if not tool:
            agent._set_tool_missing_flag("can:water")
            agent._skip_dynamic_activity(entry)
            return  # 도구 없음 → "할 일 없음" 폴백
        agent._clear_tool_missing_flag("can:water")
        agent._activity_state["tool"] = tool
        if tool["source"] == "inventory":
            agent._activity_phase = "going_to_garden"
        else:
            agent._activity_phase = "getting_tool"
        return

    if obj.has_empty_furrow():
        agent._activity_phase = "going_to_garden"
        return

    # 할 일 없음
    remaining = agent._remaining_millis_in_entry(entry)
    agent._insert_idle_job("정원", max(remaining, 1))
    agent._action_taken = True


def _handle_getting_tool(agent):
    """getting_tool: 도구 컨테이너로 이동 → 도구 집기"""
    tool = agent._activity_state.get("tool")
    if not tool:
        agent._activity_phase = "idle"
        return

    target = tool.get("location")
    if not target:
        target = resolve_storage_container(agent, "garden_tool")
        if not target:
            target = resolve_storage_container(agent, "tool")
    if not target:
        agent._activity_phase = "idle"
        agent._action_taken = True
        return

    if agent._is_at(target):
        container_id = tool.get("container_id") or target.get("object_id")
        item_id = tool["item_id"]
        if morld.has_item(container_id, item_id):
            morld.remove_item(container_id, item_id, 1)
            morld.give_item(agent.unit_id, item_id, 1)
            agent._activity_phase = "going_to_garden"
            agent._action_taken = True
        else:
            # 경합으로 사라짐 → 재탐색
            agent._activity_state.pop("tool", None)
            agent._activity_phase = "idle"
            agent._action_taken = True
    else:
        agent._move_to(target, "도구 찾기")


def _handle_going_to_garden(agent):
    """going_to_garden: 텃밭으로 이동"""
    target = agent._activity_state.get("garden")
    if not target:
        agent._activity_phase = "idle"
        return

    if agent._is_at(target):
        agent._activity_phase = "working"
    else:
        agent._move_to(target, "정원 가꾸기")


def _handle_working(agent, entry):
    """working: 텃밭에서 작업 실행 (수확 > 물주기 > 씨 심기)"""
    garden_info = agent._activity_state.get("garden")
    if not garden_info:
        agent._activity_phase = "returning_tool"
        return

    # 인터럽트 복귀 시 정원으로 재이동
    if not agent._is_at(garden_info):
        agent._activity_phase = "going_to_garden"
        return

    obj = get_instance(garden_info["object_id"])
    if not obj:
        agent._activity_phase = "returning_tool"
        return

    # 우선순위 1: 수확
    if obj.has_harvestable():
        count = obj.npc_harvest(agent.unit_id)
        if count > 0:
            _start_wait(agent, "수확", 20 * 60_000, "storing_harvest")
            return

    # 우선순위 2: 물주기 (도구 필요)
    if obj.needs_water():
        if _has_water_tool(agent):
            obj.npc_water(agent.unit_id)
            _start_wait(agent, "물주기", 10 * 60_000, "working")
            return
        else:
            # 도구 없이 도착 (수확 후 재평가 등) → 도구 가져오기
            agent._activity_phase = "idle"
            return

    # 우선순위 3: 씨 심기
    if obj.has_empty_furrow():
        import random
        import garden as garden_mod
        codes = list(garden_mod.SEED_REGISTRY.keys())
        random.shuffle(codes)
        for code in codes:
            if obj.npc_plant(agent.unit_id, code):
                _start_wait(agent, "씨 심기", 10 * 60_000, "working")
                return

    # 할 일 없음 → 도구 반납
    agent._activity_phase = "returning_tool"


def _handle_working_wait(agent):
    """working_wait: 작업 후 대기 — 시간 기반으로 Duration 감소 보장"""
    wait_until = agent._activity_state.get("wait_until", 0)
    remaining = wait_until - agent.get_time()
    if remaining > 0:
        wait_name = agent._activity_state.get("wait_name", "정원")
        agent._insert_idle_job(wait_name, remaining)
        agent._action_taken = True
    else:
        # 대기 완료 → 다음 단계
        next_phase = agent._activity_state.pop("next_phase", "working")
        agent._activity_phase = next_phase
        # action_taken 미설정 → _check_tier5_routine 폴백으로 1 step 후 재진입


def _handle_storing_harvest(agent):
    """storing_harvest: 수확물을 보관소에 저장 → 정원 복귀"""
    target = agent._activity_state.get("storage_target")
    if not target:
        target = resolve_storage_container(agent, "food_ingredient")
        if not target:
            target = resolve_storage_container(agent, "food")
        if not target:
            # 보관소 없음 → 정원 복귀
            agent._activity_phase = "going_to_garden"
            agent._action_taken = True
            return
        agent._activity_state["storage_target"] = target

    if agent._is_at(target):
        store_npc_items(agent, categories=["food", "food_ingredient", "drink_ingredient"])
        agent._activity_state.pop("storage_target", None)
        _start_wait(agent, "정리", 5 * 60_000, "going_to_garden")
    else:
        agent._move_to(target, "수확물 보관")


def _handle_returning_tool(agent, entry):
    """returning_tool: 도구를 보관소에 반납 → idle (재평가)"""
    tool = agent._activity_state.get("tool")
    if not tool:
        # 도구 없음 → 잔여 시간 대기
        remaining = agent._remaining_millis_in_entry(entry)
        agent._insert_idle_job("정원", max(remaining, 1))
        agent._action_taken = True
        return

    item_id = tool["item_id"]

    # 인벤토리에 도구가 없으면 반납 불필요
    if not morld.has_item(agent.unit_id, item_id):
        agent._activity_state.pop("tool", None)
        agent._activity_phase = "idle"
        agent._action_taken = True
        return

    target = resolve_storage_container(agent, "garden_tool")
    if not target:
        target = resolve_storage_container(agent, "tool")
    if not target:
        # 반납 불가 → 인벤토리에 보유한 채 대기
        agent._activity_state.pop("tool", None)
        remaining = agent._remaining_millis_in_entry(entry)
        agent._insert_idle_job("정원", max(remaining, 1))
        agent._action_taken = True
        return

    if agent._is_at(target):
        container_id = target["object_id"]
        morld.remove_item(agent.unit_id, item_id, 1)
        morld.give_item(container_id, item_id, 1)
        agent._activity_state.pop("tool", None)
        agent._activity_phase = "idle"
        agent._action_taken = True
    else:
        agent._move_to(target, "도구 반납")


# ========================================
# 유틸리티
# ========================================

def _start_wait(agent, name, duration_ms, next_phase):
    """대기 시작 — get_time() 기반 wait으로 Duration 감소 보장

    매 step마다 remaining = wait_until - now 로 계산하므로
    _insert_idle_job의 duration이 매 step 자연 감소함.
    """
    agent._activity_state["wait_until"] = agent.get_time() + duration_ms
    agent._activity_state["wait_name"] = name
    agent._activity_state["next_phase"] = next_phase
    agent._activity_phase = "working_wait"
    agent._insert_idle_job(name, duration_ms)
    agent._action_taken = True


def _has_water_tool(agent):
    """NPC 인벤토리에 물주기 도구(can:water)가 있는지 확인"""
    from assets.registry import get_unique_id, get_item_class

    inv = morld.get_unit_inventory(agent.unit_id)
    if not inv:
        return False
    for item_id, count in inv.items():
        if count <= 0:
            continue
        uid = get_unique_id(item_id)
        cls = get_item_class(uid) if uid else None
        if cls and agent._item_has_capability(cls, "can:water"):
            return True
    return False
