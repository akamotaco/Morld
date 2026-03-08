# events/first_mission.py - 첫 임무 이벤트 (Step 8~13)
#
# handle_mission_briefing: 비서의 임무 브리핑 (건설 완료 후)
# start_expedition: 분대 편성 후 탐사 출발
# handle_room_entered: 방 진입 시 전투/전리품 처리
# retreat_expedition: 귀환 명령
# handle_mission_complete: 귀환 후 임무 완료 보고

import morld
import ui


def handle_mission_briefing():
    """Step 8: 첫 임무 브리핑

    트리거: 기본 플랫폼 건설 완료 (임시 막사 + 보관소)
    """
    state = {"result": None}

    def handle_choice(action):
        if action == "init":
            return None
        state["result"] = action
        return True

    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "기본 시설이 갖춰졌습니다. 첫 임무를 시작하겠습니다.\n"
        "인근 구역에서 보수 자재를 수집해야 합니다.\n"
        "분대를 편성하여 탐사를 진행하세요.\n\n"
        "[url=@proc:detail]자세히 알려줘[/url]\n"
        "[url=@proc:accept]알겠다[/url]",
        autofill="off",
        proc=handle_choice,
        result=state,
    )

    if state["result"] == "detail":
        yield ui.dialog(
            "[b]비서[/b]\n\n"
            "금속 파이프 5개, 콘크리트 블록 3개가 필요합니다.\n"
            "탐사 지역에서 수집하여 귀환하세요.\n\n"
            "CRT 콘솔에서 분대를 편성할 수 있습니다.",
        )
    else:
        yield ui.dialog(
            "[b]비서[/b]\n\n"
            "CRT 콘솔에서 분대를 편성하세요.\n"
            "행운을 빕니다.",
        )

    print("[first_mission] Mission briefing complete.")


def start_expedition(squad_id):
    """Step 10: 탐사 출발 시퀀스

    분대 편성 완료 후 호출.
    원정 준비 → 맵 생성 → 분대 배치 → 탐사 시작.

    Args:
        squad_id: 분대 ID

    Returns:
        generator (대화 시퀀스) or None
    """
    import expedition as exp_module

    state = exp_module.prepare_expedition(squad_id, "easy")
    if not state:
        print("[first_mission] Failed to prepare expedition")
        return None

    success, msg = exp_module.start_expedition(state.expedition_id)
    if not success:
        print(f"[first_mission] Failed to start expedition: {msg}")
        return None

    print(f"[first_mission] Expedition started: "
          f"{len(state.rooms)} rooms, region={state.region_id}")

    return _expedition_departure_dialog(state)


def _expedition_departure_dialog(state):
    """탐사 출발 대화 시퀀스"""
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "분대가 출발합니다.\n"
        f"+탐사 구역: {len(state.rooms)}개 구역 탐지됨\n"
        "+CRT 콘솔에서 분대를 지휘하세요.",
    )


def handle_room_entered(expedition_id, room_id):
    """방 진입 시 전투/전리품 처리

    Args:
        expedition_id: 원정 ID
        room_id: 진입한 방 ID

    Returns:
        generator (대화 시퀀스) or None
    """
    import expedition as exp_module
    from combat import resolve_room_combat

    state = exp_module.get_expedition(expedition_id)
    if not state:
        return None

    room = exp_module._find_room(state, room_id)
    if not room:
        return None

    result = resolve_room_combat(state.squad_id, room)
    if result.occurred:
        state.combat_log.extend(result.log)

    return _room_event_dialog(room, result)


def _room_event_dialog(room, combat_result):
    """방 이벤트 대화"""
    from mapgen import ROOM_NAMES

    room_name = ROOM_NAMES.get(room["type"], f"구역-{room['id']}")

    if combat_result.occurred:
        yield ui.dialog(
            f"[b]{room_name} 진입[/b]\n\n"
            + "\n".join(combat_result.log),
        )
        if not combat_result.victory:
            yield ui.dialog(
                "[b]비서[/b]\n\n"
                "전투에서 밀렸습니다. 후퇴를 고려하세요.",
            )
    else:
        yield ui.dialog(
            f"[b]{room_name} 진입[/b]\n\n"
            "위협 없음. 안전합니다.",
        )

    if room.get("has_loot"):
        yield ui.dialog(
            f"+{room_name}에서 자재를 발견했습니다.",
        )


def retreat_expedition(squad_id):
    """Step 12: 귀환 명령

    Returns:
        generator (대화 시퀀스) or None
    """
    import expedition as exp_module

    state = exp_module.get_expedition_by_squad(squad_id)
    if not state:
        print("[first_mission] No active expedition for retreat")
        return None

    explored = len(state.explored_rooms)
    total = len(state.rooms)
    combat_count = len(state.combat_log)

    success, msg = exp_module.retreat_expedition(state.expedition_id)
    if not success:
        print(f"[first_mission] Retreat failed: {msg}")
        return None

    return _retreat_dialog(explored, total, combat_count)


def _retreat_dialog(explored, total, combat_count):
    """귀환 대화 시퀀스"""
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "분대가 귀환합니다.\n"
        f"+탐사 현황: {explored}/{total} 구역 탐색\n"
        f"+전투 기록: {combat_count}건",
    )


def handle_mission_complete():
    """Step 13: 임무 완료 보고

    트리거: 귀환 완료 후 자동
    """
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "탐사 임무가 완료되었습니다.\n"
        "+수집된 자재를 확인하겠습니다.",
    )

    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "수고하셨습니다.\n"
        "+수집된 자재는 보관소로 이동됩니다.",
    )

    print("[first_mission] Mission complete.")
