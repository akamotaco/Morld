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
        "can:enter_test_dungeon": 1,    # 던전 입구 오브젝트의 진입 액션 (Player가 actor)
        "can:dungeon_proceed": 1,       # 던전 노드 진행
    }

    def get_describe_text(self) -> str:
        return ""  # 플레이어는 묘사 없음

    def get_focus_text(self) -> str:
        return "나 자신이다."

    def get_available_actions(self):
        """플레이어 셀프 focus 시 노출 액션. 던전 활성 시 항상 진행 액션 노출
        (auto_run이 대부분 처리하지만 fallback 용도)."""
        import linear_dungeon as ld

        if not ld.is_active():
            return []
        if ld.get_current_node() is None:
            return []
        return ["call:dungeon_proceed:진행"]

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

        # 1. 이벤트 텍스트
        event_text = ""
        if t == ld.NODE_START:
            event_text = "던전에 들어섰다."
        elif t == ld.NODE_BATTLE:
            result = ld.process_current_node()
            r = result.get("result")
            if r == "victory":
                event_text = "전투 승리."
            elif r == "defeat":
                # 패배: 노드가 cleared 안 되어 advance 차단 → 무한 루프 방지
                # 던전 포기하고 입구로 귀환
                yield ui.dialog("전투 패배... 던전을 빠져나간다.")
                ld.exit_to_village(reason="defeated")
                return
            else:
                # 결판 안 남 (무승부/중단) — 패배와 동일하게 귀환 처리
                yield ui.dialog("전투를 시도했지만 결판이 나지 않았다. 물러난다.")
                ld.exit_to_village(reason="battle_inconclusive")
                return
        elif t == ld.NODE_REST:
            ld.process_current_node()
            event_text = "휴식했다."
        elif t == ld.NODE_EXIT:
            event_text = "던전 끝에 도달했다."

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

        # 3. NPC 선호 + 대사
        preferences = {npc_id: random.choice(options) for npc_id in npcs}

        lines = [event_text]
        if options:
            lines.append("")
            lines.append("선택지:")
            for i, opt in enumerate(options):
                lines.append(f"  - {labels[i]}")
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
        yield ui.dialog("\n".join(lines))

        # 4. 플레이어 선택 (UI 미구현: 첫 옵션)
        player_choice = options[0]

        # 5. Flip + 집계
        result = party_vote.resolve_with_player_influence(
            preferences, player_id, player_choice, options
        )
        winner = result["winner"]
        winner_idx = options.index(winner)
        winner_label = labels[winner_idx]
        flipped = result["flipped"]
        flip_note = f" ({len(flipped)}명이 너의 결정을 따른다.)" if flipped else ""

        yield ui.dialog(f"파티는 {winner_label}으로 결정했다.{flip_note}")

        target = advance_map[winner]
        if target == "__exit__":
            ld.exit_to_village(reason="cleared_end")
        else:
            ld.advance(target)
        return
