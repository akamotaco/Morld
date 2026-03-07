"""점검 활동 핸들러

NPC가 보관소 위치에서 같은 세력 오브젝트의 need를 스캔.
성격(responsibility) 확률로 수집 결정.
인벤토리에 이미 있으면 즉시 반납, 없으면 수집 → 반납.

Phase flow:
  idle → (스캔 → 확률 체크)
    → 인벤에 있으면: supply_delivering
    → 도구 활동: supply_getting_tool → supply_going → supply_delivering → supply_returning
    → 자원 활동: supply_going → supply_delivering
    → need 없거나 확률 미통과: idle 대기
"""
import random
import morld
from .helpers import (scan_faction_needs, reserve_need, release_need,
                      store_npc_items, get_object_x_from_info)
from .tool_activity import phase_getting_tool, phase_returning_tool


# item_uid → 수집에 필요한 정보 매핑
_COLLECT_CONFIGS = {
    "food_fish": {
        "type": "tool",
        "capability": "can:fish",
        "activity_name": "낚시",
        "work_method": "npc_fish",
        "sound_id": "splash",
        "action_key": "fish",
        "resolve": "낚시",
    },
    "log": {
        "type": "tool",
        "capability": "can:chop",
        "activity_name": "벌목",
        "work_method": "npc_chop",
        "sound_id": "chop",
        "action_key": "chop",
        "resolve": "벌목",
    },
    "branch": {
        "type": "resource",
        "activity_name": "난방 연료 수집",
        "action_key": "gather_branch",
        "resolve_target": "_resolve_branch",
    },
    "wood_chip": {
        "type": "craft",
        "activity_name": "제작",
        "action_key": "craft",
    },
}


def handle_inspect(agent, entry):
    """점검: 세력 need 스캔 → 수집/반납"""
    phase = agent._activity_phase

    if phase == "idle":
        _phase_idle(agent, entry)
    elif phase == "supply_getting_tool":
        phase_getting_tool(agent, next_phase="supply_going")
    elif phase == "supply_going":
        _phase_supply_going(agent)
    elif phase == "supply_delivering":
        _phase_supply_delivering(agent)
    elif phase == "supply_returning":
        phase_returning_tool(agent)


def _phase_idle(agent, entry):
    """세력 need 스캔 → 성격 확률 → 반응 결정"""
    needs = scan_faction_needs(agent)
    if not needs:
        remaining = agent._remaining_millis_in_entry(entry)
        agent._insert_idle_job("점검", max(remaining, 1))
        agent._action_taken = True
        return

    responsibility = getattr(agent, '_responsibility', 0.7)
    if random.random() > responsibility:
        remaining = agent._remaining_millis_in_entry(entry)
        agent._insert_idle_job("점검", max(remaining, 1))
        agent._action_taken = True
        return

    # 부족률이 높은 것부터 (greedy)
    needs.sort(key=lambda n: n["current"] / max(n["threshold"], 1))

    for need in needs:
        cfg = _COLLECT_CONFIGS.get(need["item_uid"])
        if not cfg:
            continue

        # NPC가 이 수집을 할 수 있는지 체크
        collectible = getattr(agent, '_collectible_items', None)
        if collectible is not None and need["item_uid"] not in collectible:
            continue

        # 예약
        reserve_need(need["object_id"], need["item_uid"], agent.unit_id)
        agent._activity_state["supply_target"] = need
        agent._activity_state["supply_cfg"] = cfg

        # 인벤토리에 이미 있으면 즉시 반납
        if _has_item(agent, need["item_uid"]):
            agent._activity_phase = "supply_delivering"
            agent._do_instant_action("점검", "brief")
            return

        # 수집 시작
        if cfg["type"] == "tool":
            tool = agent._find_tool_by_capability(cfg["capability"])
            if not tool:
                release_need(need["object_id"], need["item_uid"])
                continue
            agent._activity_state["tool"] = tool
            if tool["source"] == "inventory":
                agent._activity_phase = "supply_going"
            else:
                agent._activity_phase = "supply_getting_tool"
            agent._do_instant_action("점검", "brief")
            return

        elif cfg["type"] == "resource":
            target = _resolve_work_target(agent, cfg)
            if not target:
                release_need(need["object_id"], need["item_uid"])
                continue
            agent._activity_state["work_target"] = target
            agent._activity_phase = "supply_going"
            agent._do_instant_action("점검", "brief")
            return

        elif cfg["type"] == "craft":
            from .helpers import resolve_storage_container
            craft_target = resolve_storage_container(agent, "tool")
            if not craft_target:
                release_need(need["object_id"], need["item_uid"])
                continue
            agent._activity_state["work_target"] = craft_target
            agent._activity_phase = "supply_going"
            agent._do_instant_action("점검", "brief")
            return

    # 모든 need 처리 불가 → 대기
    remaining = agent._remaining_millis_in_entry(entry)
    agent._insert_idle_job("점검", max(remaining, 1))
    agent._action_taken = True


def _phase_supply_going(agent):
    """작업 장소로 이동 → 작업 수행 → delivering 전환"""
    cfg = agent._activity_state.get("supply_cfg")
    target = agent._activity_state.get("work_target")

    if not cfg:
        _abort_supply(agent)
        return

    if cfg["type"] == "tool":
        # lazy resolution
        if not target:
            from think.activity_resolver import resolve_activity_location
            target = resolve_activity_location(
                agent.unit_id, cfg["resolve"], agent._get_home_region())
            if not target:
                _abort_supply(agent)
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
            agent._activity_phase = "supply_delivering"
            agent._do_instant_action(cfg["activity_name"], cfg["action_key"])
        else:
            agent._move_to(target, cfg["activity_name"])

    elif cfg["type"] == "resource":
        if not target:
            _abort_supply(agent)
            return
        if agent._is_at(target):
            _do_resource_work(agent, cfg, target)
            agent._activity_phase = "supply_delivering"
            agent._do_instant_action(cfg["activity_name"], cfg["action_key"])
        else:
            agent._move_to(target, cfg["activity_name"])

    elif cfg["type"] == "craft":
        if not target:
            _abort_supply(agent)
            return
        if agent._is_at(target):
            _do_craft_work(agent)
            agent._activity_phase = "supply_delivering"
            agent._do_instant_action(cfg["activity_name"], cfg["action_key"])
        else:
            agent._move_to(target, cfg["activity_name"])


def _phase_supply_delivering(agent):
    """trigger 오브젝트 위치로 이동 → 아이템 반납"""
    supply = agent._activity_state.get("supply_target")
    if not supply:
        agent._activity_phase = "idle"
        return

    dest = {"region_id": supply["region_id"],
            "location_id": supply["location_id"],
            "x": supply["x"]}

    if agent._is_at(dest):
        store_npc_items(agent, categories=None)
        release_need(supply["object_id"], supply["item_uid"])

        cfg = agent._activity_state.get("supply_cfg", {})
        if cfg.get("type") == "tool" and agent._activity_state.get("tool"):
            agent._activity_phase = "supply_returning"
        else:
            agent._activity_phase = "idle"
        agent._do_instant_action("물자 납품", "store_item")
    else:
        agent._move_to(dest, "물자 납품")


def _abort_supply(agent):
    """수집 중단 → 예약 해제 → idle"""
    supply = agent._activity_state.get("supply_target")
    if supply:
        release_need(supply["object_id"], supply["item_uid"])
    agent._activity_phase = "idle"
    agent._do_instant_action("대기", "abort")


def _has_item(agent, item_uid):
    """NPC 인벤토리에 해당 unique_id 아이템이 있는지"""
    from assets.registry import get_unique_id
    inv = morld.get_unit_inventory(agent.unit_id)
    if not inv:
        return False
    for item_id, count in inv.items():
        if count <= 0:
            continue
        if get_unique_id(item_id) == item_uid:
            return True
    return False


def _resolve_work_target(agent, cfg):
    """resource 타입의 작업 대상 탐색"""
    if cfg.get("resolve_target") == "_resolve_branch":
        from .helpers import resolve_branch_tree
        return resolve_branch_tree(agent, cross_region=False)
    return None


def _do_resource_work(agent, cfg, target):
    """resource 작업 수행"""
    if cfg.get("resolve_target") == "_resolve_branch":
        from assets.objects import get_instance
        obj = get_instance(target.get("object_id"))
        if obj and hasattr(obj, "npc_gather_branch"):
            for _ in range(3):
                if not obj.npc_gather_branch(agent.unit_id):
                    break


def _do_craft_work(agent):
    """제작 작업 수행"""
    from assets.objects import get_instance, _location_objects
    loc = morld.get_unit_location(agent.unit_id)
    if not loc:
        return
    obj_ids = _location_objects.get((loc[0], loc[1]), [])
    for obj_id in obj_ids:
        obj = get_instance(obj_id)
        if obj and hasattr(obj, "npc_craft"):
            obj.npc_craft(agent.unit_id)
            break
