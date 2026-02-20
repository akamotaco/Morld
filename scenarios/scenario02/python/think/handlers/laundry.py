"""세탁/건조 핸들러 (Tier 4 인터럽트)

오염된 의류 감지 → 세탁기 이동 → 빨래 넣기 → 대기 → 꺼내기
→ (건조기 있으면) 건조기 이동 → 넣기 → 대기 → 꺼내기 → 재장착

비차단 대기: waiting_wash/waiting_dry 상태에서 _check_laundry() → False
→ NPC가 다른 활동을 자유롭게 수행. 기계 완료(state==2) 감지 시 재개.
"""
import morld
import pollution


# ========================================
# 오염 의류 탐색
# ========================================

DIRTY_THRESHOLD = 5  # 오염:수치 > 5 인 의류만 세탁 대상


def _find_dirty_equipped_clothing(unit_id):
    """장착 중인 오염 의류 item_id 목록 반환

    Returns:
        list[int]: 오염된 의류 item_id 목록 (빈 리스트면 세탁 불필요)
    """
    import equipment

    equipped = equipment.get_equipped_items(unit_id)
    if not equipped:
        return []

    dirty = []
    for item_id in equipped:
        try:
            dirt = pollution.get_unit_pollution(item_id)
            if dirt > DIRTY_THRESHOLD:
                dirty.append(item_id)
        except Exception:
            pass
    return dirty


# ========================================
# 세탁 핸들러 — 페이즈 머신
# ========================================

def _handle_laundry(agent):
    """세탁/건조 페이즈 머신

    페이즈 흐름:
        going_to_washer → loading → waiting_wash → collecting_wash
        → going_to_dryer → loading_dry → waiting_dry → collecting_dry → done
    """
    from assets.objects import get_instance

    phase = agent._memory["laundry_phase"]

    # ------ 세탁기로 이동 ------
    if phase == "going_to_washer":
        washer = agent._memory["laundry_washer"]
        if not washer:
            _reset_laundry(agent)
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(washer):
            agent._memory["laundry_phase"] = "loading"
            agent._do_instant_action("대기", "brief")
        else:
            agent._move_to(washer, "빨래")

    # ------ 장비 해제 + 세탁기에 넣기 + 시작 ------
    elif phase == "loading":
        washer = agent._memory["laundry_washer"]
        if not washer:
            _reset_laundry(agent)
            agent._do_instant_action("대기", "abort")
            return
        if not agent._is_at(washer):
            agent._move_to(washer, "빨래")
            return

        import equipment
        dirty_items = agent._memory.get("laundry_items") or []
        actual_loaded = []
        for item_id in dirty_items:
            if morld.has_item(agent.unit_id, item_id):
                equipment.unequip_item(agent.unit_id, item_id)
                actual_loaded.append(item_id)

        obj = get_instance(washer["object_id"])
        if obj and hasattr(obj, "npc_load_laundry"):
            obj.npc_load_laundry(agent.unit_id, actual_loaded)
            obj.npc_start(agent.unit_id)

        agent._memory["laundry_phase"] = "waiting_wash"
        agent._memory["laundry_items"] = actual_loaded
        agent._do_instant_action("빨래 넣기", "load_laundry")

    # ------ 세탁 대기 (즉시 return — _check_laundry에서 False 반환) ------
    elif phase == "waiting_wash":
        # _check_laundry()에서 이미 처리됨 — 여기에 올 경우 대비
        agent._do_instant_action("대기", "brief")

    # ------ 세탁 완료 → 꺼내기 ------
    elif phase == "collecting_wash":
        washer = agent._memory["laundry_washer"]
        if not washer:
            _reset_laundry(agent)
            agent._do_instant_action("대기", "abort")
            return
        if not agent._is_at(washer):
            agent._move_to(washer, "빨래 찾기")
            return

        obj = get_instance(washer["object_id"])
        if obj and hasattr(obj, "npc_unload_laundry"):
            obj.npc_unload_laundry(agent.unit_id)

        # 건조기 탐색
        from think.facility_resolver import resolve_dryer
        dryer = resolve_dryer(agent)
        if dryer:
            agent._memory["laundry_phase"] = "going_to_dryer"
            agent._memory["laundry_dryer"] = dryer
            agent._do_instant_action("빨래 꺼내기", "unload_laundry")
        else:
            # 건조기 없음 → 바로 재장착 + 완료
            _reequip_items(agent)
            _reset_laundry(agent, set_cooldown=True)
            agent._do_instant_action("빨래 정리", "store_laundry")

    # ------ 건조기로 이동 ------
    elif phase == "going_to_dryer":
        dryer = agent._memory["laundry_dryer"]
        if not dryer:
            _reequip_items(agent)
            _reset_laundry(agent, set_cooldown=True)
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(dryer):
            agent._memory["laundry_phase"] = "loading_dry"
            agent._do_instant_action("대기", "brief")
        else:
            agent._move_to(dryer, "건조")

    # ------ 건조기에 넣기 + 시작 ------
    elif phase == "loading_dry":
        dryer = agent._memory["laundry_dryer"]
        if not dryer:
            _reequip_items(agent)
            _reset_laundry(agent, set_cooldown=True)
            agent._do_instant_action("대기", "abort")
            return
        if not agent._is_at(dryer):
            agent._move_to(dryer, "건조")
            return

        laundry_items = agent._memory.get("laundry_items") or []
        obj = get_instance(dryer["object_id"])
        if obj and hasattr(obj, "npc_load_laundry"):
            obj.npc_load_laundry(agent.unit_id, laundry_items)
            obj.npc_start(agent.unit_id)

        agent._memory["laundry_phase"] = "waiting_dry"
        agent._do_instant_action("건조 시작", "load_laundry")

    # ------ 건조 대기 (즉시 return — _check_laundry에서 False 반환) ------
    elif phase == "waiting_dry":
        agent._do_instant_action("대기", "brief")

    # ------ 건조 완료 → 꺼내기 + 재장착 ------
    elif phase == "collecting_dry":
        dryer = agent._memory["laundry_dryer"]
        if not dryer:
            _reequip_items(agent)
            _reset_laundry(agent, set_cooldown=True)
            agent._do_instant_action("대기", "abort")
            return
        if not agent._is_at(dryer):
            agent._move_to(dryer, "빨래 찾기")
            return

        obj = get_instance(dryer["object_id"])
        if obj and hasattr(obj, "npc_unload_laundry"):
            obj.npc_unload_laundry(agent.unit_id)

        _reequip_items(agent)
        _reset_laundry(agent, set_cooldown=True)
        agent._do_instant_action("빨래 정리", "store_laundry")


# ========================================
# 내부 헬퍼
# ========================================

def _reequip_items(agent):
    """세탁/건조 완료 후 아이템 재장착"""
    import equipment
    for item_id in (agent._memory.get("laundry_items") or []):
        if morld.has_item(agent.unit_id, item_id):
            equipment.equip_item(agent.unit_id, item_id)


def _reset_laundry(agent, set_cooldown=False):
    """세탁 상태 초기화"""
    agent._memory["laundry_phase"] = None
    agent._memory["laundry_washer"] = None
    agent._memory["laundry_dryer"] = None
    agent._memory["laundry_items"] = None
    if set_cooldown:
        agent._memory["laundry_cooldown"] = morld.get_game_time()
