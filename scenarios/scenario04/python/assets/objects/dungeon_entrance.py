# assets/objects/dungeon_entrance.py — 던전 입구 오브젝트
#
# 마을의 던전 입구 location에 배치되어 "테스트 던전 진입" 액션 제공.
# 디버그/테스트 목적의 임시 입구. 정식 던전 시스템 정착 후 재구성 예정.

from assets.base import Object
from assets.registry import register_object


@register_object
class DungeonEntrance(Object):
    unique_id = "dungeon_entrance"
    name = "던전 입구"

    # actions는 던전 상태에 따라 동적 (get_available_actions 참조)
    actions = []

    def get_describe_text(self):
        return "어둠으로 통하는 던전의 입구가 보인다."

    def get_focus_text(self):
        return "검게 입을 벌린 던전의 입구. 안에서 차가운 바람이 불어온다."

    def get_available_actions(self):
        """던전 활성 상태에 따라 진입/진행 액션 노출."""
        import linear_dungeon as ld

        if not ld.is_active():
            return ["call:enter_test_dungeon:테스트 던전 진입"]

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

    def enter_test_dungeon(self):
        """일자형 테스트 던전 진입."""
        import linear_dungeon as ld
        import ui

        if ld.is_active():
            yield ui.dialog("이미 던전에 진입한 상태다.")
            return

        ld.enter(length=5, branch_count=1)
        node = ld.get_current_node()
        yield ui.dialog(
            f"테스트 던전에 진입했다.\n"
            f"첫 노드: {node['type']} (floor={node['floor']})\n\n"
            f"이 던전 입구를 다시 focus하면 진행 액션이 노출된다."
        )

    def dungeon_proceed(self):
        """현재 노드 진행 — Player의 동일 메서드로 위임 (generator return)."""
        import morld
        from assets import characters

        player_id = morld.get_player_id()
        if player_id is None:
            return None

        p = characters.get_instance(player_id)
        if p is None or not hasattr(p, 'dungeon_proceed'):
            return None

        # Player.dungeon_proceed는 generator → 그대로 반환
        return p.dungeon_proceed()
