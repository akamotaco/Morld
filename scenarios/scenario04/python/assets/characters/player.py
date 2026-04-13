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
    is_special = True  # 던전의 힘 사용 가능

    # 액션은 던전 상태에 따라 동적 (get_available_actions 참조)
    actions = []

    props = {
        "특수:존재": 1,
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
        """플레이어 셀프 focus 시 노출 액션. 던전 활성 시 노드 진행 액션."""
        import linear_dungeon as ld

        if not ld.is_active():
            return []

        node = ld.get_current_node()
        if node is None:
            return []

        t = node["type"]
        if t == ld.NODE_EXIT:
            return ["call:dungeon_proceed:던전 나가기"]
        if t == ld.NODE_BATTLE:
            label = "다음으로 진행" if node.get("cleared") else "전투!"
            return [f"call:dungeon_proceed:{label}"]
        if t == ld.NODE_REST:
            return ["call:dungeon_proceed:휴식하고 진행"]
        if t == ld.NODE_BRANCH:
            return ["call:dungeon_proceed:파티 회의 (다수결)"]
        return []

    def dungeon_proceed(self):
        """던전의 현재 노드를 처리하고 다음으로 진행."""
        import linear_dungeon as ld
        import ui

        if not ld.is_active():
            return

        node = ld.get_current_node()
        if node is None:
            return

        t = node["type"]

        # 마을 귀환
        if t == ld.NODE_EXIT:
            ld.exit_to_village(reason="cleared_end")
            yield ui.dialog("던전 출구를 통해 마을로 돌아왔다.")
            return

        # 노드 처리
        result = ld.process_current_node()
        node_result = result.get("result")

        # Battle: 결과별 처리
        if t == ld.NODE_BATTLE:
            if node_result == "victory":
                next_id = node["paths"][0] if node["paths"] else None
                if next_id is not None:
                    ld.advance(next_id)
                    yield ui.dialog("전투 승리. 다음으로 진행한다.")
                else:
                    yield ui.dialog("전투 승리. 막다른 길이다.")
            elif node_result == "defeat":
                yield ui.dialog("전투 패배...")
            else:
                yield ui.dialog("전투를 시도했지만 결판이 나지 않았다.")
            return

        # Rest: 회복 후 자동 진행
        if t == ld.NODE_REST:
            next_id = node["paths"][0] if node["paths"] else None
            if next_id is not None:
                ld.advance(next_id)
            yield ui.dialog("휴식했다. 다음으로 진행한다.")
            return

        # Branch: 다수결 자동 (플레이어는 첫 옵션 선택, 차후 dialog 추가)
        if t == ld.NODE_BRANCH:
            first_option = node["paths"][0]
            vote_result = ld.make_branch_decision(player_choice_id=first_option)
            action = vote_result.get("action")
            tallies = vote_result.get("tallies", {})

            if action == "return":
                yield ui.dialog(
                    f"파티 다수결로 마을로 돌아간다.\n득표: {tallies}"
                )
            elif action == "advanced":
                new_node = vote_result.get("new_node")
                yield ui.dialog(
                    f"파티가 길을 결정했다.\n득표: {tallies}\n"
                    f"다음 노드: {new_node['type'] if new_node else '?'}"
                )
            else:
                yield ui.dialog(f"분기 처리 실패: {vote_result.get('reason')}")
            return
