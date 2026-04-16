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
            event_text = "던전에 들어섰다."
        elif t in (ld.NODE_BATTLE, ld.NODE_ELITE):
            result = ld.process_current_node()
            r = result.get("result")
            battle_label = "엘리트 전투" if t == ld.NODE_ELITE else "전투"
            if r == "victory":
                event_text = f"{battle_label} 승리."
            elif r == "defeat":
                yield ui.dialog(f"{unknown_prefix}{battle_label} 패배... 던전을 빠져나간다.")
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

        # 던전 ambient (50%): 파티원 랜덤 코멘트
        player_id = morld.get_player_id()
        party = _pg.get_party_of(player_id) if player_id else None
        members = party.get_members() if party else ([player_id] if player_id else [])
        npcs = [m for m in members if m != player_id]

        if npcs and random.random() >= 0.5 and t in (ld.NODE_BATTLE, ld.NODE_REST):
            npc_id = random.choice(npcs)
            name = morld.get_unit_name(npc_id) or f"id={npc_id}"
            ambient = npc_dialogue.get_line(npc_id, "dungeon_ambient")
            event_text += f"\n\n[{name}] \"{ambient}\""

        # 2. 선택지 결정
        if t == ld.NODE_EXIT:
            options = ["village"]
            labels = ["[마을로 돌아간다]"]
            # 대사 매핑용: 각 옵션 id → room_type_key
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
        else:
            ld.advance(target)
        return
