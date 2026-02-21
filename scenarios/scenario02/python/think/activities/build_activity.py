"""건축 활동 핸들러

NPC가 건설현장을 찾아가 재료를 투입하여 건설 진척도를 올리는 활동.
Phase flow: idle → going_to_site → building
"""
import morld


def handle_build(agent, entry):
    """건축: 건설현장 탐색 → 이동 → 재료 투입 → 진척도 상승"""
    phase = agent._activity_phase

    if phase == "idle":
        # 건설현장 탐색 (home_region 내, 미완성)
        site_info = _find_construction_site(agent)
        if site_info is None:
            # 건설할 곳 없음 → 남은 시간 대기
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("건축", max(remaining, 1))
            agent._action_taken = True
            return

        agent._activity_state["site_id"] = site_info["unit_id"]
        agent._activity_state["site_target"] = site_info["target"]
        agent._activity_phase = "going_to_site"
        handle_build(agent, entry)

    elif phase == "going_to_site":
        target = agent._activity_state.get("site_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            agent._activity_phase = "building"
            agent._do_instant_action("건설 준비", "prepare")
        else:
            agent._move_to(target, "건설현장 이동")

    elif phase == "building":
        site_id = agent._activity_state.get("site_id")
        if not site_id:
            agent._activity_phase = "idle"
            return

        import build as build_module

        # 진척도 확인
        if build_module.is_construction_complete(site_id):
            agent._activity_phase = "idle"
            agent._do_instant_action("건설 완료 확인", "brief")
            return

        # 재료 확인 → 투입
        recipe_id = morld.get_unit_prop(site_id, "건설:레시피") or ""
        recipe = build_module.get_recipe(recipe_id)
        if not recipe:
            agent._activity_phase = "idle"
            agent._do_instant_action("대기", "abort")
            return

        # NPC 인벤토리에서 재료 확인
        materials = _check_npc_materials(agent, recipe)
        if not materials:
            # 재료 부족 → 스킵
            agent._skip_dynamic_activity(entry)
            return

        success, new_progress, msg = build_module.build_location_progress(
            agent.unit_id, site_id, materials
        )

        if success:
            agent._do_instant_action("건설", "build")
        else:
            agent._activity_phase = "idle"
            agent._do_instant_action("대기", "abort")


def _find_construction_site(agent):
    """home_region 내 미완성 건설현장 탐색

    Returns: {"unit_id": int, "target": {"region_id", "location_id"}} or None
    """
    from assets.objects import get_instance
    from assets.objects.construction import ConstructionSite
    import build as build_module

    home_region = agent._home_region_id
    if home_region is None:
        return None

    region_info = morld.get_region_info(home_region)
    if not region_info:
        return None

    for loc_info in region_info.get("locations", []):
        loc_id = loc_info["id"]
        units = morld.get_units_at_location(home_region, loc_id, "object")
        if not units:
            continue
        for uid in units:
            obj = get_instance(uid)
            if isinstance(obj, ConstructionSite):
                if not build_module.is_construction_complete(uid):
                    return {
                        "unit_id": uid,
                        "target": {
                            "region_id": home_region,
                            "location_id": loc_id,
                        },
                    }
    return None


def _check_npc_materials(agent, recipe):
    """NPC 인벤토리에서 레시피 재료 보유 확인

    Returns: [(item_uid, count), ...] 실제 투입 가능한 재료, 또는 빈 리스트
    """
    from assets.registry import get_or_create_item_id

    for item_uid, count in recipe.materials:
        item_id = get_or_create_item_id(item_uid)
        if item_id is None or not morld.has_item(agent.unit_id, item_id, count):
            return []

    return list(recipe.materials)
