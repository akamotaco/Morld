# assets/characters/player.py - 플레이어 캐릭터
#
# 특수 존재: 던전의 힘 사용 가능, 침식 내성 높음

from assets.base import Character
from assets.registry import register_character


@register_character
class Player(Character):
    unique_id = "player"
    name = "플레이어"

    # 기본 스탯 (특수 존재: 정신 높음)
    base_str = 12
    base_agi = 10
    base_vit = 11
    base_mnd = 15  # 침식 저항 높음

    character_class = None  # 플레이어 선택 (향후)
    # 능력은 props의 "침식:저항배수", "던전:힘사용" 등으로 표현 (is_special 단일 플래그 제거)

    # 액션은 던전 상태에 따라 동적 (get_available_actions 참조)
    actions = []

    props = {
        # 능력 (원자 props — 기존 "특수:존재" 단일 플래그 대체)
        "침식:저항배수": 0.5,           # 침식 50%만 축적
        "던전:힘사용": 1,               # 던전의 힘 사용 가능 (향후 시스템용)
        # 파티/액션
        "리더십": 3,                    # MAX_PARTY_SIZE(4)-1 — 파티 풀 가득 통솔 가능
        "can:invite_to_party": 1,       # NPC에게 "파티 초대" 액션 권한
        "can:dismiss_from_party": 1,    # 파티원 NPC에게 "파티 이탈" 액션 권한
        "can:browse_quests": 1,         # 게시판 의뢰 확인 액션
        "can:report_quests": 1,         # 게시판 완료 보고 액션
        "can:show_quests": 1,           # 셀프 focus '퀘스트 확인' 액션
        "can:dungeon_proceed": 1,       # 던전 노드 진행
    }

    def get_describe_text(self) -> str:
        return ""  # 플레이어는 묘사 없음

    def get_focus_text(self) -> str:
        return "나 자신이다."

    def get_available_actions(self):
        """플레이어 셀프 focus 시 노출 액션."""
        actions = ["call:show_quests:퀘스트 확인"]

        import linear_dungeon as ld
        if ld.is_active() and ld.get_current_node() is not None:
            actions.append("call:dungeon_proceed:진행")

        return actions

    def show_quests(self):
        """퀘스트 현황 UI (Generator)"""
        import morld
        import ui
        from engine.quest import get_quest_manager, QuestStatus, get_condition_description
        mgr = get_quest_manager()

        lines = ["[b]퀘스트[/b]", ""]

        # 진행 중
        active = mgr.get_active_quests()
        if active:
            for q in active:
                lines.append("[진행 중] " + q.name)
                lines.append("  " + q.description)
                progress = mgr.get_quest_progress(q.unique_id)
                for ci in progress["conditions"]:
                    mark = "✓" if ci["is_met"] else "○"
                    lines.append("  " + mark + " " + ci["description"])

                # 남은 시간 (시간 제한 퀘스트)
                props = morld.get_unit_props(morld.get_player_id()) or {}
                accept_time = props.get("퀘스트:" + q.unique_id + ":수락시각", 0)
                if accept_time > 0:
                    import quest_board
                    elapsed_h = (morld.get_game_time() - accept_time) / 3_600_000
                    remain_h = max(0, quest_board.QUEST_TIME_LIMIT_HOURS - elapsed_h)
                    remain_d = int(remain_h // 24)
                    remain_hr = int(remain_h % 24)
                    lines.append("  기한: " + str(remain_d) + "일 " + str(remain_hr) + "시간 남음")
                lines.append("")
        else:
            lines.append("진행 중인 퀘스트가 없다.")
            lines.append("")

        # 완료 대기
        completed = mgr.get_quests_by_status(QuestStatus.COMPLETED)
        if completed:
            for q in completed:
                lines.append("[완료] " + q.name)
            lines.append("")

        yield ui.dialog("\n".join(lines))

    def dungeon_proceed(self):
        """던전 현재 노드 이벤트 → 다음 선택(다수결) → advance.

        모든 노드는 동일 흐름:
          1. 이벤트 실행 (START/EXIT은 서술만, BATTLE/REST는 실행)
          2. 선택지 = node.paths (EXIT은 가상 option "village")
             라벨은 각 방 타입 ("[전투방]", "[휴식방]", "[마을로 돌아간다]")
          3. NPC 선호(랜덤) + 대사 출력 — 대사는 선호 방 타입별
          4. 플레이어 선택 (UI 미구현: 첫 옵션)
          5. 호감도 flip → winner → advance (winner == "village"면 exit)
        """
        import morld
        import linear_dungeon as ld
        import npc_dialogue
        import party_vote
        import random
        import ui
        from engine import party_group as _pg

        if not ld.is_active():
            return
        node = ld.get_current_node()
        if node is None:
            return

        player_id = morld.get_player_id()
        t = node["type"]

        # UNKNOWN 방 공개: 진입 시 실제 타입으로 변환 후 그 타입으로 처리
        unknown_prefix = ""
        if t == ld.NODE_UNKNOWN:
            revealed = ld.reveal_unknown_node()
            t = revealed
            label = ld.NODE_LABELS.get(t, "?")
            unknown_prefix = f"미지의 방이었다. 실제로는 [{label}]이다.\n\n"

        # 1. 이벤트 텍스트
        event_text = ""
        if t == ld.NODE_START:
            cur_floor, total_floors = ld.get_floor_info()
            if total_floors > 1:
                event_text = f"던전 {cur_floor}층에 들어섰다."
            else:
                event_text = "던전에 들어섰다."
        elif t in (ld.NODE_BATTLE, ld.NODE_ELITE, ld.NODE_BOSS):
            result = ld.process_current_node()
            r = result.get("result")
            if t == ld.NODE_BOSS:
                boss_cfg = node.get("boss_config") or {}
                battle_label = "최종 보스전" if boss_cfg.get("is_final") else "보스전"
            elif t == ld.NODE_ELITE:
                battle_label = "엘리트 전투"
            else:
                battle_label = "전투"
            if r == "victory":
                # 승리 후 실신 NPC 체크
                fainted_npcs = _get_fainted_party_npcs(player_id, _pg)
                if fainted_npcs:
                    names = ", ".join(morld.get_unit_name(uid) or str(uid) for uid in fainted_npcs)
                    event_text = f"{battle_label} 승리. 하지만 {names}이(가) 쓰러졌다."
                else:
                    event_text = f"{battle_label} 승리."
            elif r == "defeat":
                # 패배 정식 경로: 플레이어 실신 체크
                player_fainted = morld.get_unit_prop(player_id, "상태:실신")
                survivors = _get_surviving_party_npcs(player_id, _pg)
                if player_fainted and survivors:
                    # 생존 NPC가 구출
                    from engine import korean
                    rescuer = survivors[0]
                    rname = morld.get_unit_name(rescuer) or str(rescuer)
                    particle = korean.이_가(rname)
                    yield ui.dialog(
                        f"{unknown_prefix}{battle_label} 패배.\n\n"
                        f"의식이 흐려진다...\n"
                        f"{rname}{particle} 당신을 끌고 던전을 빠져나왔다.")
                    ld.exit_to_village(reason="rescued")
                    return
                elif player_fainted:
                    # 전원 실신
                    yield ui.dialog(
                        f"{unknown_prefix}{battle_label} 패배.\n\n"
                        f"의식이 흐려진다... 아무도 도와줄 수 없다.")
                    ld.exit_to_village(reason="all_fainted")
                    _trigger_player_death_event()
                    return
                else:
                    # 플레이어 생존, NPC 실신 — 플레이어가 판단
                    fainted = _get_fainted_party_npcs(player_id, _pg)
                    if fainted:
                        names = ", ".join(morld.get_unit_name(uid) or str(uid) for uid in fainted)
                        yield ui.dialog(
                            f"{unknown_prefix}{battle_label} 패배.\n\n"
                            f"{names}이(가) 쓰러졌다. 후퇴한다.")
                    else:
                        yield ui.dialog(f"{unknown_prefix}{battle_label} 패배... 후퇴한다.")
                    ld.exit_to_village(reason="defeated")
                    return
            else:
                yield ui.dialog(f"{unknown_prefix}{battle_label}의 결판이 나지 않았다. 물러난다.")
                ld.exit_to_village(reason="battle_inconclusive")
                return
        elif t == ld.NODE_REST:
            ld.process_current_node()
            event_text = "휴식했다."
        elif t == ld.NODE_CAMP:
            ld.process_current_node()
            event_text = "캠프에서 긴 휴식을 취했다."
        elif t == ld.NODE_TREASURE:
            ld.process_current_node()
            event_text = "보물의 방이다. 누군가 먼저 다녀간 듯, 텅 비어있다."
        elif t == ld.NODE_EVENT:
            ld.process_current_node()
            event_text = "이벤트 방이다. 아직은 아무 일도 일어나지 않는다."
        elif t == ld.NODE_EMPTY:
            ld.process_current_node()
            event_text = "빈 방이다. 지나친다."
        elif t == ld.NODE_EXIT:
            event_text = "던전 끝에 도달했다."

        event_text = unknown_prefix + event_text

        # 플레이어 실신 체크 (시간 경과에 의한 실신 — 전투 패배는 위에서 처리)
        if player_id is not None and morld.get_unit_prop(player_id, "상태:실신"):
            party = _pg.get_party_of(player_id) if player_id else None
            survivors = []
            if party:
                for uid in party.get_members():
                    if uid != player_id and not morld.get_unit_prop(uid, "상태:실신"):
                        if morld.get_unit_prop(uid, "dungeon:구출의사"):
                            survivors.append(uid)
            if survivors:
                # NPC가 구출 결정 (DungeonState.update에서 판정됨)
                from engine import korean
                rescuer_id = survivors[0]
                rescuer_name = morld.get_unit_name(rescuer_id) or str(rescuer_id)
                particle = korean.이_가(rescuer_name)
                yield ui.dialog(
                    "의식이 흐려진다...\n\n"
                    + rescuer_name + particle + " 당신을 끌고 던전을 빠져나왔다.")
                ld.exit_to_village(reason="rescued")
                return
            else:
                # 구출자 없음 — 전원 실신
                yield ui.dialog("의식이 흐려진다... 아무도 도와줄 수 없다.")
                ld.exit_to_village(reason="all_fainted")
                return

        # 던전 ambient (50%): 파티원 랜덤 코멘트
        party = _pg.get_party_of(player_id) if player_id else None
        members = party.get_members() if party else ([player_id] if player_id else [])
        npcs = [m for m in members if m != player_id]

        if npcs and random.random() >= 0.5 and t in (ld.NODE_BATTLE, ld.NODE_REST):
            npc_id = random.choice(npcs)
            name = morld.get_unit_name(npc_id) or f"id={npc_id}"
            ambient = npc_dialogue.get_line(npc_id, "dungeon_ambient")
            event_text += f"\n\n[{name}] \"{ambient}\""

        # 2. 선택지 결정
        # 층 끝(EXIT / 클리어된 BOSS) → 다음 층 있으면 "다음 층 / 마을 귀환", 없으면 자동 귀환
        is_final_boss = (t == ld.NODE_BOSS
                         and (node.get("boss_config") or {}).get("is_final"))
        is_floor_end = (t == ld.NODE_EXIT
                        or (t == ld.NODE_BOSS and node.get("cleared")))

        # 마지막 층 EXIT(보스 아님) → 선택지 없이 자동 귀환 (UI 한 번으로 종료)
        if t == ld.NODE_EXIT and not ld.has_next_floor():
            yield ui.dialog(event_text)
            ld.exit_to_village(reason="cleared_end")
            return

        if is_final_boss:
            # 최종 보스 클리어 = 던전 클리어
            options = ["village"]
            labels = ["[마을로 개선한다]"]
            option_room_type = {"village": "exit"}
            advance_map = {"village": "__exit__"}
        elif is_floor_end and ld.has_next_floor():
            # 다음 층 있음 → 투표
            cur_floor, total_floors = ld.get_floor_info()
            options = ["next_floor", "village"]
            labels = [f"[다음 층({cur_floor + 1}/{total_floors})으로 내려간다]",
                      "[마을로 돌아간다]"]
            option_room_type = {"next_floor": "battle", "village": "exit"}
            advance_map = {"next_floor": "__next_floor__", "village": "__exit__"}
        elif is_floor_end:
            # 마지막 층 종료 (EXIT 또는 보스 중간형이지만 다음 층 없음)
            options = ["village"]
            labels = ["[마을로 돌아간다]"]
            option_room_type = {"village": "exit"}
            advance_map = {"village": "__exit__"}
        else:
            paths = node["paths"]
            if not paths:
                yield ui.dialog(f"{event_text}\n\n(갈 곳이 없다.)")
                return
            options = [str(p) for p in paths]
            labels = list(node["labels"])
            option_room_type = {
                str(p): ld._state["nodes"][p]["type"] for p in paths
            }
            advance_map = {str(p): p for p in paths}

            # 캠프 노드: 마을 귀환 옵션 추가 (후퇴 — 던전 리셋)
            if t == ld.NODE_CAMP:
                options.append("retreat")
                labels.append("[마을로 후퇴한다]")
                option_room_type["retreat"] = "exit"
                advance_map["retreat"] = "__retreat__"

        # 3. NPC 선호 + 대사 (Agent 경유 — 모든 NPC는 Agent 필수)
        from engine import think as _think
        preferences = {}
        for npc_id in npcs:
            agent = _think.get_agent(npc_id)
            if agent is None:
                raise RuntimeError(
                    "[dungeon_proceed] NPC id=" + str(npc_id)
                    + " (" + str(morld.get_unit_name(npc_id))
                    + ") has no registered Agent")
            preferences[npc_id] = agent.dungeon_choose(options)

        lines = [event_text]
        if npcs:
            lines.append("")
            lines.append("파티원 의견:")
            for npc_id in npcs:
                pref_opt = preferences[npc_id]
                pref_idx = options.index(pref_opt)
                pref_label = labels[pref_idx]
                room_type = option_room_type[pref_opt]
                situation_key = {
                    ld.NODE_BATTLE: "room_pref_battle",
                    ld.NODE_REST:   "room_pref_rest",
                    ld.NODE_EXIT:   "room_pref_exit",
                }.get(room_type, "room_pref_battle")
                name = morld.get_unit_name(npc_id) or f"id={npc_id}"
                line = npc_dialogue.get_line(npc_id, situation_key)
                lines.append(f"  [{name}] {pref_label} — \"{line}\"")

        # 4. 선택지 (실제 클릭)
        lines.append("")
        lines.append("선택:")
        for i, label in enumerate(labels):
            lines.append(f"  [url=@proc:{i}]{label}[/url]")

        choice_state = {"idx": None}

        def _handle_choice(action):
            if action == "init":
                return None
            try:
                idx = int(action)
            except (ValueError, TypeError):
                return None
            if 0 <= idx < len(options):
                choice_state["idx"] = idx
                return True
            return None

        yield morld.dialog(
            "\n".join(lines),
            autofill="off",
            proc=_handle_choice,
            result=choice_state,
        )

        chosen_idx = choice_state["idx"] if choice_state["idx"] is not None else 0
        player_choice = options[chosen_idx]

        # 5. Flip + 집계
        result = party_vote.resolve_with_player_influence(
            preferences, player_id, player_choice, options
        )
        winner = result["winner"]
        winner_idx = options.index(winner)
        winner_label = labels[winner_idx]

        # 플레이어와 동일한 최종 선택을 한 NPC 이름 목록
        from engine import korean
        votes = result.get("votes", {})
        aligned_names = []
        for npc_id in npcs:
            if votes.get(npc_id) == player_choice:
                name = morld.get_unit_name(npc_id) or f"id={npc_id}"
                aligned_names.append(name)
        if aligned_names:
            joined = ", ".join(aligned_names)
            particle = korean.이_가(aligned_names[-1])
            align_note = f" ({joined}{particle} 너의 결정을 따른다.)"
        else:
            align_note = ""

        yield ui.dialog(f"파티는 {winner_label}으로 결정했다.{align_note}")

        target = advance_map[winner]
        if target == "__exit__":
            ld.exit_to_village(reason="cleared_end")
        elif target == "__next_floor__":
            ld.advance_to_next_floor()
        elif target == "__retreat__":
            _handle_camp_retreat(player_id, _pg, ld, ui)
        else:
            ld.advance(target)
        return


# ============================================
# 던전 전투 헬퍼 (모듈 레벨)
# ============================================

def _get_fainted_party_npcs(player_id, _pg):
    """파티 내 실신 NPC 목록 (플레이어 제외)"""
    import morld
    party = _pg.get_party_of(player_id)
    if party is None:
        return []
    result = []
    for uid in party.get_members():
        if uid == player_id:
            continue
        if morld.get_unit_prop(uid, "상태:실신"):
            result.append(uid)
    return result


def _get_surviving_party_npcs(player_id, _pg):
    """파티 내 생존 NPC 목록 (플레이어 제외, 실신 아닌)"""
    import morld
    party = _pg.get_party_of(player_id)
    if party is None:
        return []
    result = []
    for uid in party.get_members():
        if uid == player_id:
            continue
        if not morld.get_unit_prop(uid, "상태:실신"):
            result.append(uid)
    return result


def _handle_camp_retreat(player_id, _pg, ld, ui):
    """캠프에서 마을 후퇴 — 던전 리셋 + 구호소/던전입구로 이동"""
    import morld

    # 실신 멤버 확인
    fainted = _get_fainted_party_npcs(player_id, _pg)

    # 던전 리셋 (후퇴 = 처음부터 다시)
    ld.exit_to_village(reason="retreat")

    # 귀환 목적지: 구호소 존재 시 구호소, 아니면 던전 입구
    try:
        import facility
        has_infirmary = facility.has_infirmary()
    except (ImportError, Exception):
        has_infirmary = False

    party = _pg.get_party_of(player_id)
    members = party.get_members() if party else [player_id]

    if has_infirmary and fainted:
        # 실신 멤버 포함 → 구호소로
        INFIRMARY_REGION = 0
        INFIRMARY_LOCATION = 5
        for uid in members:
            morld.set_unit_location(uid, INFIRMARY_REGION, INFIRMARY_LOCATION, x=50)
        print("[player] Camp retreat → infirmary (fainted members)")
    # 실신 없거나 구호소 없으면 기본 위치 (exit_to_village가 이미 L7으로 이동)


def _trigger_player_death_event():
    """플레이어 사망 이벤트 (임시 — 로그라이크 리셋용)

    게임 오버가 아님. 던전 실패 → 마을 귀환 → 페널티 후 계속.
    향후: 침식 누적, 아이템 손실, 시간 경과 등.
    """
    import morld
    player_id = morld.get_player_id()
    if player_id is None:
        return

    # 임시: 실신 해제 + 체력 절반 회복
    try:
        import survival
        morld.set_unit_prop(player_id, "상태:실신", 0)
        max_hp = survival.get_max_health(player_id)
        survival.set_health(player_id, max(1, max_hp // 2))
    except (ImportError, Exception):
        pass

    print("[player] Death event triggered — roguelike reset (temp)")
