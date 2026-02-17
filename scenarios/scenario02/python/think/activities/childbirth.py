"""출산 활동 핸들러

4-phase 구조: idle → going → laboring → recovery
Tier 4 인터럽트로 BaseAgent에서 호출.

모성 행동 핸들러도 포함:
3-phase 구조: idle → going → interacting
"""
import morld


# ============================================
# 출산 핸들러
# ============================================

def handle_childbirth(agent, entry):
    """출산: 침실 이동 → 출산(8h) → 회복(24h) → 아이 생성"""
    phase = agent._memory.get("childbirth_phase", "idle")

    if phase == "idle":
        # 출산 장소 = 소유 침대 위치
        target = None
        owner = getattr(agent, 'owner_unique_id', None)
        if owner:
            from think.facility_resolver import _find_facilities_by_prop
            beds = _find_facilities_by_prop(f"bed_owner:{owner}", 1)
            if beds:
                target = beds[0]
        if not target:
            target = {"region_id": 0, "location_id": 1}
        agent._memory["childbirth_target"] = target
        agent._memory["childbirth_phase"] = "going"
        handle_childbirth(agent, entry)
        return

    elif phase == "going":
        target = agent._memory.get("childbirth_target")
        if not target:
            agent._memory["childbirth_phase"] = None
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(target):
            agent._memory["childbirth_phase"] = "laboring"
            agent._do_instant_action("출산", "labor")
        else:
            agent._move_to(target, "출산")

    elif phase == "laboring":
        # 출산 완료 → 아이 생성
        import pregnancy
        child_id = pregnancy.spawn_child(agent)
        agent._memory["childbirth_child_id"] = child_id
        agent._memory["last_child_id"] = child_id
        agent._memory["childbirth_phase"] = "recovery"
        agent._do_instant_action("산후조리", "postpartum")

    elif phase == "recovery":
        # 회복 완료 → 상태 초기화
        import pregnancy
        pregnancy.reset_pregnancy(agent.unit_id)
        agent._memory["childbirth_phase"] = None
        agent._memory["childbirth_target"] = None
        # 기본 행동으로 복귀 (다음 think()에서 결정)
        agent._do_instant_action("회복완료", "brief")


# ============================================
# 모성 행동 핸들러
# ============================================

def handle_maternal(agent, entry):
    """모성: 아이 탐색 → 이동 → 대화/돌봄(30분)"""
    phase = agent._memory.get("maternal_phase", "idle")

    if phase == "idle":
        child_id = agent._memory.get("last_child_id")
        if not child_id:
            agent._memory["maternal_phase"] = None
            agent._do_instant_action("대기", "abort")
            return

        child_loc = morld.get_unit_location(child_id)
        if not child_loc:
            agent._memory["maternal_phase"] = None
            agent._do_instant_action("대기", "abort")
            return

        target = {"region_id": child_loc[0], "location_id": child_loc[1]}
        agent._memory["maternal_target"] = target
        agent._memory["maternal_phase"] = "going"
        handle_maternal(agent, entry)
        return

    elif phase == "going":
        target = agent._memory.get("maternal_target")
        if not target:
            agent._memory["maternal_phase"] = None
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(target):
            agent._memory["maternal_phase"] = "interacting"
            agent._do_instant_action("육아", "maternal")
        else:
            agent._move_to(target, "육아")

    elif phase == "interacting":
        # 돌봄 완료 → 모성 욕구 감소
        current = morld.get_unit_prop(agent.unit_id, "욕구:모성") or 0
        morld.set_unit_prop(agent.unit_id, "욕구:모성", max(0, current - 30))
        agent._memory["maternal_phase"] = None
        agent._memory["maternal_target"] = None
        # 다음 think에서 일반 행동 재개
        agent._do_instant_action("육아완료", "brief")
