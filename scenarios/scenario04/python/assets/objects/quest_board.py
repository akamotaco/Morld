# assets/objects/quest_board.py — 퀘스트 게시판
#
# 던전 입구(L7)에 배치. 퀘스트 수락 → 리니어 던전 생성.

import morld
from assets.base import Object
from assets.registry import register_object


@register_object
class QuestBoard(Object):
    unique_id = "quest_board"
    name = "의뢰 게시판"

    actions = ["call:browse_quests:의뢰 확인"]

    def get_describe_text(self):
        return "던전 탐사 의뢰가 게시되어 있다."

    def get_focus_text(self):
        from engine.quest import get_quest_manager, QuestStatus
        mgr = get_quest_manager()

        lines = ["[b]의뢰 게시판[/b]", ""]

        # 진행 중인 퀘스트
        active = mgr.get_active_quests()
        board_active = [q for q in active if q.category == "board"]
        if board_active:
            q = board_active[0]
            progress = mgr.get_quest_progress(q.unique_id)
            lines.append("현재 의뢰: " + q.name)
            lines.append("  " + q.description)
            lines.append("  진행: " + str(progress["current"]) + "/" + str(progress["total"]))
            return "\n".join(lines)

        lines.append("의뢰를 수락하면 던전에 진입할 수 있다.")
        return "\n".join(lines)

    def browse_quests(self):
        """의뢰 목록 표시 + 수락"""
        import ui
        from engine.quest import get_quest_manager, QuestStatus
        mgr = get_quest_manager()

        # 이미 진행 중인 게시판 퀘스트
        active = mgr.get_active_quests()
        board_active = [q for q in active if q.category == "board"]
        if board_active:
            q = board_active[0]
            yield ui.dialog("이미 수행 중인 의뢰가 있다: " + q.name)
            return

        # 수락 가능한 게시판 퀘스트
        available = mgr.get_quests_by_status(QuestStatus.AVAILABLE)
        board_available = [q for q in available if q.category == "board"]

        if not board_available:
            yield ui.dialog("현재 수락 가능한 의뢰가 없다.")
            return

        # 선택지 생성
        state = {"choice_idx": None}

        def _handle(action):
            if action == "init":
                return None
            try:
                idx = int(action)
            except (ValueError, TypeError):
                return None
            if 0 <= idx < len(board_available):
                state["choice_idx"] = idx
                return True
            return None

        lines = ["[b]의뢰 목록[/b]", ""]
        for i, q in enumerate(board_available):
            lines.append("[url=@proc:" + str(i) + "]" + q.name + "[/url]")
            lines.append("  " + q.description)
            lines.append("")

        yield morld.dialog(
            "\n".join(lines),
            autofill="off",
            proc=_handle,
            result=state,
        )

        if state["choice_idx"] is None:
            return

        quest = board_available[state["choice_idx"]]
        ok = mgr.accept_quest(quest.unique_id)
        if ok:
            yield ui.dialog("의뢰 '" + quest.name + "'을 수락했다.\n\n퀘스트 던전으로 이동하면 진입할 수 있다.")
        else:
            yield ui.dialog("의뢰를 수락할 수 없다.")
