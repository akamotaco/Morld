# think/activities/build_activity.py - NPC 건설 활동 핸들러 (시나리오03)
#
# Phase flow: idle -> going_to_site -> building
#
# 시나리오02 build_activity.py와 동일 패턴이나 간소화:
# - 자재 체크 단순화 (NPC 인벤토리 미사용, 현장 자재 소비)
# - _find_construction_site(): 현재 Region 내 미완료 건설현장 탐색

import morld


def handle_build(agent, entry):
    """NPC 건설 활동 핸들러"""
    phase = agent._activity_phase

    if phase == "idle":
        _phase_idle(agent, entry)
    elif phase == "going_to_site":
        _phase_going_to_site(agent)
    elif phase == "building":
        _phase_building(agent, entry)


def _phase_idle(agent, entry):
    """건설현장 탐색 -> going_to_site 전환"""
    site_info = _find_construction_site(agent)
    if site_info is None:
        remaining = _remaining_millis(agent, entry)
        agent._insert_idle_job("건축 대기", max(remaining, 1))
        agent._action_taken = True
        return

    agent._activity_state["site_id"] = site_info["unit_id"]
    agent._activity_state["site_target"] = site_info["target"]
    agent._activity_phase = "going_to_site"
    agent._do_instant_action("건설현장 이동", "brief")


def _phase_going_to_site(agent):
    """건설현장으로 이동"""
    target = agent._activity_state.get("site_target")
    if not target:
        agent._activity_phase = "idle"
        return

    loc = agent.get_location()
    if loc and loc[0] == target["region_id"] and loc[1] == target["location_id"]:
        # 도착
        agent._activity_phase = "building"
        agent._do_instant_action("건설 준비", "brief")
    else:
        # 이동 (BaseAgent._move_to가 없으면 직접 텔레포트)
        if hasattr(agent, '_move_to'):
            agent._move_to(target, "건설현장 이동")
        else:
            morld.set_unit_location(
                agent.unit_id,
                target["region_id"],
                target["location_id"],
            )
            agent._activity_phase = "building"
            agent._do_instant_action("건설현장 도착", "brief")


def _phase_building(agent, entry):
    """건설 작업 수행"""
    site_id = agent._activity_state.get("site_id")
    if not site_id:
        agent._activity_phase = "idle"
        return

    import build as build_module

    if build_module.is_construction_complete(site_id):
        # 완료 -> idle
        agent._activity_phase = "idle"
        agent._activity_state.clear()
        agent._do_instant_action("건설 완료", "brief")
        return

    # 자재 소비 없이 진척도 증가 (데모 간소화)
    # TODO: NPC 인벤토리에서 자재 소비 구현
    success, new_progress, msg = build_module.build_location_progress(
        agent.unit_id, site_id, materials_used=None
    )

    if success:
        agent._do_instant_action("건설", "build")
    else:
        remaining = _remaining_millis(agent, entry)
        agent._insert_idle_job("건설 중단", max(remaining, 1))
        agent._action_taken = True


def _find_construction_site(agent):
    """현재 Region 내 미완료 건설현장 탐색

    Returns:
        {"unit_id": int, "target": {"region_id", "location_id"}} or None
    """
    loc = agent.get_location()
    if not loc:
        return None

    region_id = loc[0]

    # Region 내 모든 Location 순회
    for loc_id in range(100):
        info = morld.get_location_info(region_id, loc_id)
        if info is None:
            continue

        # 해당 Location의 유닛 중 construction_site 탐색
        units = morld.get_units_at_location(region_id, loc_id)
        for unit_id in units:
            unit_info = morld.get_unit_info(unit_id)
            if not unit_info:
                continue
            if unit_info.get("unique_id") == "construction_site":
                progress = morld.get_unit_prop(unit_id, "건설:진척도")
                if progress is not None and progress < 100:
                    return {
                        "unit_id": unit_id,
                        "target": {
                            "region_id": region_id,
                            "location_id": loc_id,
                        },
                    }
    return None


def _remaining_millis(agent, entry):
    """스케줄 엔트리 남은 시간 (간소화)"""
    if hasattr(agent, '_remaining_millis_in_entry'):
        return agent._remaining_millis_in_entry(entry)
    return 600_000  # fallback 10분
