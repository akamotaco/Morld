"""도구 기반 활동 공통 핸들러 + 공용 phase 함수

공용 Phase 함수 (다른 핸들러에서 import 가능):
    phase_getting_tool  — 도구 획득 (clean, garden 등)
    phase_returning_tool — 도구 반납 (clean, garden 등)
    phase_storing       — 보관소 저장 (resource_activity 등)

도구 활동 핸들러:
    handle_tool_activity — idle → getting_tool → going_to_work → storing → returning_tool

cfg dict keys (handle_tool_activity 용):
    capability: str         - 도구 capability ("can:chop", "can:fish")
    activity_name: str      - 활동 이름 ("벌목", "낚시")
    storage_need: tuple     - (category, item_uid, threshold)
    work_method: str        - 오브젝트 메서드명 ("npc_chop", "npc_fish")
    sound_id: str           - 효과음 ID ("chop", "splash")
    action_key: str         - ACTION_DURATION 키 ("chop", "fish")
    store_categories: list  - 저장 카테고리 (["material"], ["food", ...])
    store_resolve: list     - 저장소 탐색 카테고리 순서
    store_label: str        - 저장 행동 이름 ("통나무 저장", "물고기 저장")
    eager_location: bool    - idle에서 위치 선 탐색 (True=벌목, False=낚시)
"""
import morld


# ========================================
# 공용 Phase 함수
# ========================================

def phase_getting_tool(agent, next_phase="going_to_work",
                       tool_categories=("tool",)):
    """도구 획득 공용 phase

    Requires: agent._activity_state["tool"] set by idle phase.
    On success: transitions to next_phase.
    On race condition (item gone): resets to idle.
    """
    tool = agent._activity_state.get("tool")
    if not tool:
        agent._activity_phase = "idle"
        return

    target = tool.get("location")
    if not target:
        from .helpers import resolve_storage_container
        for cat in tool_categories:
            target = resolve_storage_container(agent, cat)
            if target:
                break
    if not target:
        agent._do_instant_action("대기", "abort")
        return

    if agent._is_at(target):
        container_id = tool.get("container_id") or target.get("object_id")
        item_id = tool["item_id"]
        if morld.has_item(container_id, item_id):
            morld.remove_item(container_id, item_id, 1)
            import inventory as inv_module
            inv_module.safe_give_item(agent.unit_id, item_id, 1)
            agent._activity_phase = next_phase
            agent._do_instant_action("도구 준비", "take_item")
        else:
            # 경합으로 사라짐 → 재탐색
            agent._activity_state.pop("tool", None)
            agent._activity_phase = "idle"
            agent._do_instant_action("대기", "abort")
    else:
        agent._move_to(target, "도구 찾기")


def phase_returning_tool(agent, tool_categories=("tool",)):
    """도구 반납 공용 phase

    Requires: agent._activity_state["tool"].
    On completion: transitions to idle.
    """
    tool = agent._activity_state.get("tool")
    item_id = tool["item_id"] if tool else None

    from .helpers import resolve_storage_container
    target = None
    for cat in tool_categories:
        target = resolve_storage_container(agent, cat)
        if target:
            break
    if not target:
        agent._do_instant_action("대기", "abort")
        return
    container_id = target["object_id"]

    if agent._is_at(target):
        if item_id and container_id:
            morld.remove_item(agent.unit_id, item_id, 1)
            morld.give_item(container_id, item_id, 1)
        agent._activity_phase = "idle"
        agent._do_instant_action("도구 반납", "store_item")
    else:
        agent._move_to(target, "도구 반납")


def phase_storing(agent, store_categories, store_resolve, store_label,
                  next_phase="idle"):
    """보관소 저장 공용 phase

    NPC 인벤토리의 아이템을 보관소에 저장.
    store_resolve: 저장소 탐색 카테고리 순서 (첫 번째 발견된 것 사용).
    """
    target = agent._activity_state.get("storage_target")
    if not target:
        from .helpers import resolve_storage_container
        for cat in store_resolve:
            target = resolve_storage_container(agent, cat)
            if target:
                break
        if not target:
            agent._activity_phase = next_phase
            agent._do_instant_action("대기", "abort")
            return
        agent._activity_state["storage_target"] = target

    if agent._is_at(target):
        from .helpers import store_npc_items
        store_npc_items(agent, categories=store_categories)
        agent._activity_phase = next_phase
        agent._do_instant_action(store_label, "store_item")
    else:
        agent._move_to(target, store_label)


# ========================================
# 도구 기반 활동 핸들러
# ========================================

def handle_tool_activity(agent, entry, cfg):
    """도구 → 작업 → 보관 → 반납 공통 루프"""
    phase = agent._activity_phase

    if phase == "idle":
        _phase_idle(agent, entry, cfg)
    elif phase == "getting_tool":
        phase_getting_tool(agent, next_phase="going_to_work")
    elif phase == "going_to_work":
        _phase_going_to_work(agent, cfg)
    elif phase == "storing":
        if cfg.get("mode") == "hobby":
            # 취미 모드: 수확물은 인벤토리에 유지 → 도구 반납으로 직행
            agent._activity_phase = "returning_tool"
            agent._do_instant_action(cfg["activity_name"], "brief")
        else:
            phase_storing(agent, cfg["store_categories"], cfg["store_resolve"],
                          cfg["store_label"], next_phase="returning_tool")
    elif phase == "returning_tool":
        phase_returning_tool(agent)


def _phase_idle(agent, entry, cfg):
    # hobby 모드에서는 storage_need 체크 스킵
    if cfg.get("mode") != "hobby":
        cat, uid, threshold = cfg["storage_need"]
        if not agent._check_storage_need(cat, uid, threshold):
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job(cfg["activity_name"], max(remaining, 1))
            agent._action_taken = True
            return

    # 도구 탐색
    capability = cfg["capability"]
    tool = agent._find_tool_by_capability(capability)
    if not tool:
        agent._set_tool_missing_flag(capability)
        agent._skip_dynamic_activity(entry)
        return

    agent._clear_tool_missing_flag(capability)
    agent._activity_state["tool"] = tool

    # 위치 선 탐색 (eager)
    if cfg.get("eager_location", False):
        from think.activity_resolver import resolve_activity_location
        target = resolve_activity_location(
            agent.unit_id, cfg["activity_name"], agent._get_home_region()
        )
        if not target:
            if tool["source"] == "inventory":
                agent._activity_phase = "returning_tool"
            # else: "할 일 없음" 폴백
            return
        agent._activity_state["work_target"] = target

    if tool["source"] == "inventory":
        agent._activity_phase = "going_to_work"
    else:
        agent._activity_phase = "getting_tool"


def _phase_going_to_work(agent, cfg):
    target = agent._activity_state.get("work_target")
    if not target:
        # lazy resolution (eager_location=False인 경우)
        from think.activity_resolver import resolve_activity_location
        target = resolve_activity_location(
            agent.unit_id, cfg["activity_name"], agent._get_home_region()
        )
        if not target:
            agent._activity_phase = "returning_tool"
            return
        agent._activity_state["work_target"] = target

    if agent._is_at(target):
        from assets.objects import get_instance
        obj_id = target.get("object_id")
        if obj_id:
            obj = get_instance(obj_id)
            method = cfg["work_method"]
            if obj and hasattr(obj, method):
                getattr(obj, method)(agent.unit_id)
                import sound
                sound.emit_sound(agent.unit_id, cfg["sound_id"])
        agent._activity_phase = "storing"
        agent._do_instant_action(cfg["activity_name"], cfg["action_key"])
    else:
        agent._move_to(target, cfg["activity_name"])
