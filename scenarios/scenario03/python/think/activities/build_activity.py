# think/activities/build_activity.py - NPC 건설 활동 핸들러 (시나리오03)
#
# 시나리오02와 동일한 패턴:
# Phase flow: idle -> going_to_site -> building
# - isinstance 기반 건설현장 탐색
# - NPC 인벤토리 자재 체크 (_check_npc_materials)
# - 재귀적 phase 전환

import morld


def handle_build(agent, entry):
    """건축: 건설현장 탐색 -> 이동 -> 재료 투입 -> 진척도 상승"""
    phase = agent._activity_phase

    if phase == "idle":
        # 건설현장 탐색
        site_info = _find_construction_site(agent)
        if site_info is None:
            remaining = _remaining_millis(agent, entry)
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
            agent._move_to_target(target, "건설현장 이동")

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

        # 재료 확인 -> 투입
        recipe_id = morld.get_unit_prop(site_id, "건설:레시피") or ""
        recipe = build_module.get_recipe(recipe_id)
        if not recipe:
            agent._activity_phase = "idle"
            agent._do_instant_action("대기", "abort")
            return

        # NPC 인벤토리에서 재료 확인
        materials = _check_npc_materials(agent, recipe)
        if not materials:
            # 재료 부족 -> 무자재 진행 (데모 간소화)
            # 실제 구현에서는 agent._skip_dynamic_activity(entry) 사용
            materials = None

        success, new_progress, msg = build_module.build_location_progress(
            agent.unit_id, site_id, materials
        )

        if success:
            agent._do_instant_action("건설", "build")
        else:
            agent._activity_phase = "idle"
            agent._do_instant_action("대기", "abort")


def _find_construction_site(agent):
    """현재 Region 내 미완료 건설현장 탐색

    Returns: {"unit_id": int, "target": {"region_id", "location_id"}} or None
    """
    from assets.objects.construction import ConstructionSite
    import build as build_module

    loc = agent.get_location()
    if not loc:
        return None

    region_id = loc[0]

    # Region 내 모든 Location 순회
    region_info = morld.get_region_info(region_id)
    if region_info and region_info.get("locations"):
        location_ids = [l["id"] for l in region_info["locations"]]
    else:
        # fallback: iterate
        location_ids = []
        for loc_id in range(100):
            info = morld.get_location_info(region_id, loc_id)
            if info is not None:
                location_ids.append(loc_id)

    for loc_id in location_ids:
        units = morld.get_units_at_location(region_id, loc_id)
        if not units:
            continue
        for uid in units:
            # isinstance 체크 (S02 패턴)
            from assets.objects import get_instance
            obj = get_instance(uid)
            if isinstance(obj, ConstructionSite):
                if not build_module.is_construction_complete(uid):
                    return {
                        "unit_id": uid,
                        "target": {
                            "region_id": region_id,
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


def _remaining_millis(agent, entry):
    """스케줄 엔트리 남은 시간"""
    if hasattr(agent, '_remaining_millis_in_entry'):
        return agent._remaining_millis_in_entry(entry)
    return 600_000  # fallback 10분
