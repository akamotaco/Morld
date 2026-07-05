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
    import npc_dialogue

    text = (
        "[b]비서[/b]\n\n"
        "분대가 출발합니다.\n"
        f"+탐사 구역: {len(state.rooms)}개 구역 탐지됨\n"
        "+CRT 콘솔에서 분대를 지휘하세요."
    )
    # 출발 한마디 (주변 대사)
    speaker = _pick_speaker(state.squad_id, len(state.rooms))
    if speaker is not None:
        line = npc_dialogue.member_dungeon_line(speaker, "floor_descent")
        if line:
            text += "\n\n" + line
    yield ui.dialog(text)


def handle_room_entered(expedition_id, room_id):
    """방 진입 시 전투/결번/전리품 처리

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
    death_records = []
    if result.occurred:
        state.combat_count += 1
        if result.victory:
            state.victory_count += 1
        state.combat_log.extend(result.log)

        # 결번 처리 (운영/데모 공통 — cycle이 분대/유닛 정리)
        if result.deaths:
            import cycle
            death_records = cycle.process_casualties(state.squad_id, result.deaths)
            state.casualties.extend(death_records)

    # 위협이 해소된 방의 전리품 자동 수집
    collected = exp_module.collect_room_loot(expedition_id, room_id)

    return _room_event_dialog(state, room, result, death_records, collected)


def _survivor_ids(squad_id):
    import squad as squad_module
    return squad_module.get_all_unit_ids(squad_id)


def _pick_speaker(squad_id, salt=0):
    """주변 대사 화자 선택 (방 번호 기반 순환 — 특정 대원 독점 방지)"""
    ids = _survivor_ids(squad_id)
    if not ids:
        return None
    return ids[salt % len(ids)]


def _room_event_dialog(state, room, combat_result, death_records, collected):
    """방 이벤트 대화 — 핵심 정보는 고정 텍스트, 주변 대사는 hybrid 동적 생성"""
    import npc_dialogue
    from mapgen import ROOM_NAMES

    room_name = ROOM_NAMES.get(room["type"], f"구역-{room['id']}")
    salt = room["id"]

    if combat_result.occurred:
        lines = [f"[b]{room_name} 진입[/b]\n"]
        # 교전 개시 외침 (주변 대사)
        speaker = _pick_speaker(state.squad_id, salt)
        if speaker is not None:
            shout = npc_dialogue.member_combat_line(speaker, "combat_engage")
            if shout:
                lines.append(shout)
        lines.extend(combat_result.log)
        # 승리/패배 소감 (주변 대사)
        speaker2 = _pick_speaker(state.squad_id, salt + 1)
        if speaker2 is not None:
            intent = "combat_victory" if combat_result.victory else "combat_defeat"
            after = npc_dialogue.member_combat_line(speaker2, intent)
            if after:
                lines.append(after)
        yield ui.dialog("\n".join(lines))

        if death_records:
            mourn_lines = ["[b]결번 발생[/b]\n"]
            for rec in death_records:
                mourn_lines.append(f"  {rec['name']} — 신호 두절. 결번 처리.")
            speaker3 = _pick_speaker(state.squad_id, salt + 2)
            if speaker3 is not None:
                cry = npc_dialogue.member_combat_line(speaker3, "combat_ally_down")
                if cry:
                    mourn_lines.append("\n" + cry)
            yield ui.dialog("\n".join(mourn_lines))

        if not combat_result.victory:
            yield ui.dialog(
                "[b]비서[/b]\n\n"
                "전투에서 밀렸습니다. 후퇴를 고려하세요.",
            )
    else:
        lines = [f"[b]{room_name} 진입[/b]\n", "위협 없음. 안전합니다."]
        # 탐사 중얼거림 (주변 대사)
        speaker = _pick_speaker(state.squad_id, salt)
        if speaker is not None:
            murmur = npc_dialogue.member_dungeon_line(speaker, "dungeon_ambient")
            if murmur:
                lines.append("\n" + murmur)
        yield ui.dialog("\n".join(lines))

    if collected:
        loot_text = ", ".join(f"{u} x{c}" for u, c in collected.items())
        yield ui.dialog(f"+{room_name}에서 자재 수집: {loot_text}")
    elif room.get("has_loot"):
        yield ui.dialog(
            f"+{room_name}에 자재가 있지만 위협이 남아 있어 수집할 수 없습니다.",
        )

    # 전멸 확인 — 분대가 비었으면 원정 강제 종료 안내
    if not _survivor_ids(state.squad_id):
        yield ui.dialog(
            "[b]비서[/b]\n\n"
            "...모든 개체의 신호가 두절되었습니다.\n"
            "+원정을 종료합니다. 회수 절차를 시작합니다.",
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
    combat_count = state.combat_count

    # 귀환 소감 (주변 대사) — 유닛 이동/맵 정리 전에 생성
    import npc_dialogue
    farewell = ""
    speaker = _pick_speaker(state.squad_id, explored)
    if speaker is not None:
        farewell = npc_dialogue.member_party_line(speaker, "vote_return")

    success, msg = exp_module.retreat_expedition(state.expedition_id)
    if not success:
        print(f"[first_mission] Retreat failed: {msg}")
        return None

    return _retreat_dialog(explored, total, combat_count, farewell)


def _retreat_dialog(explored, total, combat_count, farewell=""):
    """귀환 대화 시퀀스"""
    text = (
        "[b]비서[/b]\n\n"
        "분대가 귀환합니다.\n"
        f"+탐사 현황: {explored}/{total} 구역 탐색\n"
        f"+전투 기록: {combat_count}건"
    )
    if farewell:
        text += "\n\n" + farewell
    yield ui.dialog(text)


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
