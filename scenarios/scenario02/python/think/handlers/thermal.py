"""체온 관련 핸들러 (Tier 3 인터럽트)

추위: 인벤토리 확인 → 옷장 이동 → 보온/방수 아이템 꺼내기 → 장착
더위: 보온 의류 벗기 → (옷장 위치면) 저장
착의: 나체/반나체 → 옷장 이동 → 상의/하의 꺼내기 → 장착
"""
import morld


# ========================================
# 추위 핸들러 (방한 인터럽트)
# ========================================

def _handle_cold(agent):
    """추위: 인벤토리 확인 → 옷장 이동 → 옷 가져오기 → 장착"""
    phase = agent._memory["cold_phase"]

    if phase == "idle":
        # 인벤토리에 보온/방수 아이템이 있으면 바로 장착
        if _has_warm_items_in_inventory(agent.unit_id):
            agent._memory["cold_phase"] = "equipping"
            _handle_cold(agent)
            return
        # 없으면 옷장으로 이동
        agent._memory["cold_phase"] = "going"
        _handle_cold(agent)
        return

    elif phase == "going":
        from think.facility_resolver import resolve_wardrobe
        target = resolve_wardrobe(agent)
        if target is None:
            agent._memory["cold_phase"] = None
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(target):
            agent._memory["cold_phase"] = "taking"
            agent._do_instant_action("대기", "brief")
        else:
            agent._move_to(target, "방한")

    elif phase == "taking":
        wardrobe_id = agent._find_wardrobe_id()
        if wardrobe_id:
            # 보온 아이템 꺼내기
            _take_warm_items_from_container(agent, wardrobe_id)
            # 방수 아이템도 꺼내기
            _take_waterproof_items_from_container(agent, wardrobe_id)
        agent._memory["cold_phase"] = "equipping"
        agent._do_instant_action("옷 꺼내기", "take_item")

    elif phase == "equipping":
        _equip_warm_items(agent.unit_id)
        agent._memory["cold_phase"] = None
        agent._memory["cold_last_attempt"] = morld.get_game_time()
        agent._do_instant_action("방한", "equip")


def _has_warm_items_in_inventory(unit_id):
    """인벤토리에 미장착 보온/방수 아이템이 있는지"""
    import equipment
    inv = morld.get_unit_inventory(unit_id)
    if not inv:
        return False
    equipped = set(equipment.get_equipped_items(unit_id))
    for item_id, count in inv.items():
        if count <= 0 or item_id in equipped:
            continue
        try:
            info = morld.get_item_info(item_id)
            if info:
                ep = info.get("equip_props", {})
                if ep.get("보온", 0) > 0 or ep.get("방수", 0) > 0:
                    return True
        except Exception:
            pass
    return False


def _take_warm_items_from_container(agent, container_id):
    """컨테이너에서 보온 아이템을 NPC 인벤토리로 이동"""
    inv = morld.get_unit_inventory(container_id)
    if not inv:
        return
    for item_id, count in list(inv.items()):
        if count <= 0:
            continue
        try:
            info = morld.get_item_info(item_id)
            if info and info.get("equip_props", {}).get("보온", 0) > 0:
                morld.remove_item(container_id, item_id, 1)
                import inventory as inv_module
                inv_module.safe_give_item(agent.unit_id, item_id, 1)
        except Exception:
            pass


def _take_waterproof_items_from_container(agent, container_id):
    """컨테이너에서 방수 아이템을 NPC 인벤토리로 이동"""
    inv = morld.get_unit_inventory(container_id)
    if not inv:
        return
    for item_id, count in list(inv.items()):
        if count <= 0:
            continue
        try:
            info = morld.get_item_info(item_id)
            if info and info.get("equip_props", {}).get("방수", 0) > 0:
                morld.remove_item(container_id, item_id, 1)
                import inventory as inv_module
                inv_module.safe_give_item(agent.unit_id, item_id, 1)
        except Exception:
            pass


def _equip_warm_items(unit_id):
    """인벤토리의 보온/방수 아이템 전부 장착"""
    import equipment
    inv = morld.get_unit_inventory(unit_id)
    if not inv:
        return
    equipped = set(equipment.get_equipped_items(unit_id))
    for item_id, count in inv.items():
        if count <= 0 or item_id in equipped:
            continue
        try:
            info = morld.get_item_info(item_id)
            if info:
                ep = info.get("equip_props", {})
                if ep.get("보온", 0) > 0 or ep.get("방수", 0) > 0:
                    equipment.equip_item(unit_id, item_id)
        except Exception:
            pass


# ========================================
# 더위 핸들러 (보온 의류 벗기)
# ========================================

def _handle_hot(agent):
    """더위: 보온 의류 벗기 → (옷장 위치면) 저장"""
    phase = agent._memory["hot_phase"]

    if phase == "idle":
        agent._memory["hot_phase"] = "unequipping"
        _handle_hot(agent)
        return

    elif phase == "unequipping":
        _unequip_warm_items(agent.unit_id)
        # 현재 위치에 옷장이 있으면 저장
        from think.facility_resolver import resolve_wardrobe
        result = resolve_wardrobe(agent)
        if result and agent._is_at(result):
            agent._memory["hot_phase"] = "storing"
            agent._do_instant_action("옷 벗기", "unequip")
        else:
            agent._memory["hot_phase"] = None
            agent._do_instant_action("옷 벗기", "unequip")

    elif phase == "storing":
        wardrobe_id = agent._find_wardrobe_id()
        if wardrobe_id:
            _store_warm_items_to_container(agent, wardrobe_id)
        agent._memory["hot_phase"] = None
        agent._do_instant_action("옷 보관", "store_item")


def _unequip_warm_items(unit_id):
    """장착 중인 보온 아이템 전부 벗기"""
    import equipment
    equipped = equipment.get_equipped_items(unit_id)
    for item_id in equipped:
        try:
            info = morld.get_item_info(item_id)
            if info and info.get("equip_props", {}).get("보온", 0) > 0:
                equipment.unequip_item(unit_id, item_id)
        except Exception:
            pass


def _store_warm_items_to_container(agent, container_id):
    """인벤토리의 보온 아이템을 컨테이너에 저장"""
    import equipment
    inv = morld.get_unit_inventory(agent.unit_id)
    if not inv:
        return
    equipped = set(equipment.get_equipped_items(agent.unit_id))
    for item_id, count in list(inv.items()):
        if count <= 0 or item_id in equipped:
            continue
        try:
            info = morld.get_item_info(item_id)
            if info and info.get("equip_props", {}).get("보온", 0) > 0:
                morld.remove_item(agent.unit_id, item_id, 1)
                morld.give_item(container_id, item_id, 1)
        except Exception:
            pass


# ========================================
# 착의 핸들러 (나체/반나체 → 옷장 → 착의)
# ========================================

def _is_dressed(unit_id):
    """상의+하의 모두 착용 중인지"""
    import equipment
    equipped = equipment.get_equipped_items(unit_id)
    has_top = False
    has_bottom = False
    for item_id in equipped:
        try:
            info = morld.get_item_info(item_id)
            if info:
                ep = info.get("equip_props", {})
                if ep.get("착용:상의", 0) > 0:
                    has_top = True
                if ep.get("착용:하의", 0) > 0:
                    has_bottom = True
        except Exception:
            pass
    return has_top and has_bottom


def _handle_clothing(agent):
    """착의: 인벤토리 확인 → 옷장 이동 → 옷 가져오기 → 장착"""
    phase = agent._memory["clothing_phase"]

    if phase == "idle":
        # 상체 결박 중이면 착의 불가
        import restraint
        if not restraint.can_use_hands(agent.unit_id):
            agent._memory["clothing_phase"] = None
            agent._do_instant_action("대기", "abort")
            return
        # 인벤토리에 착용 가능한 옷이 있으면 바로 장착
        if _has_clothing_in_inventory(agent.unit_id):
            agent._memory["clothing_phase"] = "equipping"
            _handle_clothing(agent)
            return
        # 없으면 옷장으로 이동
        agent._memory["clothing_phase"] = "going"
        _handle_clothing(agent)
        return

    elif phase == "going":
        from think.facility_resolver import resolve_wardrobe
        target = resolve_wardrobe(agent)
        if target is None:
            agent._memory["clothing_phase"] = None
            agent._memory["clothing_last_attempt"] = morld.get_game_time()
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(target):
            agent._memory["clothing_phase"] = "taking"
            agent._do_instant_action("대기", "brief")
        else:
            agent._move_to(target, "착의")

    elif phase == "taking":
        wardrobe_id = agent._find_wardrobe_id()
        if wardrobe_id:
            import temperature
            avoid_warm = temperature.is_hot(agent.unit_id)
            _take_clothing_from_container(agent, wardrobe_id, avoid_warm)
        agent._memory["clothing_phase"] = "equipping"
        agent._do_instant_action("옷 꺼내기", "take_item")

    elif phase == "equipping":
        _equip_clothing_items(agent.unit_id)
        agent._memory["clothing_phase"] = None
        agent._memory["clothing_last_attempt"] = morld.get_game_time()
        agent._do_instant_action("착의", "equip")


def _has_clothing_in_inventory(unit_id):
    """인벤토리에 미장착 상의/하의 아이템이 있는지"""
    import equipment
    inv = morld.get_unit_inventory(unit_id)
    if not inv:
        return False
    equipped = set(equipment.get_equipped_items(unit_id))
    for item_id, count in inv.items():
        if count <= 0 or item_id in equipped:
            continue
        try:
            info = morld.get_item_info(item_id)
            if info:
                ep = info.get("equip_props", {})
                if ep.get("착용:상의", 0) > 0 or ep.get("착용:하의", 0) > 0:
                    return True
        except Exception:
            pass
    return False


def _take_clothing_from_container(agent, container_id, avoid_warm=False):
    """옷장에서 부족 슬롯 의류 꺼내기"""
    import equipment
    # 현재 부족한 슬롯 확인
    equipped = equipment.get_equipped_items(agent.unit_id)
    need_top = True
    need_bottom = True
    for item_id in equipped:
        try:
            info = morld.get_item_info(item_id)
            if info:
                ep = info.get("equip_props", {})
                if ep.get("착용:상의", 0) > 0:
                    need_top = False
                if ep.get("착용:하의", 0) > 0:
                    need_bottom = False
        except Exception:
            pass

    if not need_top and not need_bottom:
        return

    inv = morld.get_unit_inventory(container_id)
    if not inv:
        return
    for item_id, count in list(inv.items()):
        if count <= 0:
            continue
        try:
            info = morld.get_item_info(item_id)
            if not info:
                continue
            ep = info.get("equip_props", {})
            # 더울 때 보온 아이템 스킵
            if avoid_warm and ep.get("보온", 0) > 0:
                continue
            fills_top = ep.get("착용:상의", 0) > 0
            fills_bottom = ep.get("착용:하의", 0) > 0
            if (need_top and fills_top) or (need_bottom and fills_bottom):
                morld.remove_item(container_id, item_id, 1)
                import inventory as inv_module
                inv_module.safe_give_item(agent.unit_id, item_id, 1)
                if fills_top:
                    need_top = False
                if fills_bottom:
                    need_bottom = False
            if not need_top and not need_bottom:
                break
        except Exception:
            pass


def _equip_clothing_items(unit_id):
    """인벤토리의 미장착 상의/하의 아이템 장착"""
    import equipment
    inv = morld.get_unit_inventory(unit_id)
    if not inv:
        return
    equipped = set(equipment.get_equipped_items(unit_id))
    for item_id, count in inv.items():
        if count <= 0 or item_id in equipped:
            continue
        try:
            info = morld.get_item_info(item_id)
            if info:
                ep = info.get("equip_props", {})
                if ep.get("착용:상의", 0) > 0 or ep.get("착용:하의", 0) > 0:
                    equipment.equip_item(unit_id, item_id)
        except Exception:
            pass
