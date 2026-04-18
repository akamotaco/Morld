# assets/objects/quest_board.py — 퀘스트 게시판
#
# 던전 입구(L7)에 배치. 퀘스트 수락/확인/포기.

import morld
from assets.base import Object
from assets.registry import register_object


@register_object
class QuestBoard(Object):
    unique_id = "quest_board"
    name = "의뢰 게시판"

    # 동적 액션 — get_available_actions에서 보고 대기 퀘스트 유무에 따라 "완료 보고" 노출
    actions = ["call:browse_quests:의뢰 확인"]

    def get_available_actions(self):
        """기본 '의뢰 확인' + 보고 대기 퀘스트 있으면 '완료 보고' 추가."""
        from engine import quest_reporter
        acts = ["call:browse_quests:의뢰 확인"]
        # focus 시점 재평가 포함 (recheck_first=True)
        if quest_reporter.has_reportable("quest_board"):
            acts.append("call:report_quests:완료 보고")
        return acts

    def get_describe_text(self):
        return "던전 탐사 의뢰가 게시되어 있다."

    def get_focus_text(self):
        from engine.quest import get_quest_manager, QuestStatus
        from engine import quest_reporter
        mgr = get_quest_manager()

        # focus 시 조건 재평가 (보고 방식 퀘스트 COMPLETED 승격 기회)
        quest_reporter.recheck("quest_board")

        lines = ["[b]의뢰 게시판[/b]", ""]

        # 보고 대기 중인 퀘스트 먼저 표시
        reportable = quest_reporter.get_reportable("quest_board")
        if reportable:
            lines.append("[완료 — 확인 대기]")
            for q in reportable:
                lines.append("  " + q.name)
            lines.append("")

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

    def report_quests(self):
        """완료 보고 UI — 공용 quest_reporter 모듈 사용"""
        from engine import quest_reporter
        return quest_reporter.render_report_dialog("quest_board", "의뢰 게시판")

    def browse_quests(self):
        """의뢰 목록/진행 중 확인 — 단일 proc dialog로 처리"""
        import ui
        from engine.quest import get_quest_manager, QuestStatus, get_condition_description
        mgr = get_quest_manager()

        active = mgr.get_active_quests()
        board_active = [q for q in active if q.category == "board"]

        available = mgr.get_quests_by_status(QuestStatus.AVAILABLE)
        board_available = [q for q in available if q.category == "board"]

        state = {"page": "list", "selected_idx": None, "result": None}

        def _render():
            if state["page"] == "detail_available":
                return _render_detail_available(board_available, state["selected_idx"])
            if state["page"] == "detail_active":
                return _render_detail_active(mgr, board_active, state["selected_idx"])
            return _render_list(board_available, board_active)

        def _render_list(avail, active_list):
            lines = ["[b]의뢰 게시판[/b]", ""]
            if active_list:
                lines.append("[진행 중]")
                for i, q in enumerate(active_list):
                    progress = mgr.get_quest_progress(q.unique_id)
                    lines.append("  [url=@proc:active:" + str(i) + "]" + q.name
                                 + " (" + str(progress["current"]) + "/" + str(progress["total"]) + ")[/url]")
                lines.append("")
            if avail:
                lines.append("[수락 가능]")
                for i, q in enumerate(avail):
                    lines.append("  [url=@proc:avail:" + str(i) + "]" + q.name + "[/url]")
                lines.append("")
            if not active_list and not avail:
                lines.append("게시된 의뢰가 없다.")
                lines.append("")
            lines.append("[url=@finish]닫기[/url]")
            return "\n".join(lines)

        def _render_detail_available(avail, idx):
            q = avail[idx]
            lines = ["[b]" + q.name + "[/b]", ""]
            lines.append(q.description)
            lines.append("")
            lines.append("[url=@proc:accept:" + str(idx) + "]수락[/url]  [url=@proc:back]거절[/url]")
            return "\n".join(lines)

        def _render_detail_active(mgr_ref, active_list, idx):
            q = active_list[idx]
            progress = mgr_ref.get_quest_progress(q.unique_id)
            lines = ["[b]" + q.name + "[/b]", ""]
            lines.append(q.description)
            lines.append("")
            lines.append("[조건]")
            for ci in progress["conditions"]:
                mark = "✓" if ci["is_met"] else "○"
                lines.append("  " + mark + " " + ci["description"])
            lines.append("")

            # 남은 시간
            player_id = morld.get_player_id()
            if player_id:
                props = morld.get_unit_props(player_id) or {}
                accept_time = props.get("퀘스트:" + q.unique_id + ":수락시각", 0)
                if accept_time > 0:
                    import quest_board as qb
                    elapsed_h = (morld.get_game_time() - accept_time) / 3_600_000
                    remain_h = max(0, qb.QUEST_TIME_LIMIT_HOURS - elapsed_h)
                    remain_d = int(remain_h // 24)
                    remain_hr = int(remain_h % 24)
                    lines.append("기한: " + str(remain_d) + "일 " + str(remain_hr) + "시간 남음")
                    lines.append("")

            lines.append("[url=@proc:abandon:" + str(idx) + "]포기[/url]  [url=@proc:back]돌아가기[/url]")
            return "\n".join(lines)

        def _handle(action):
            if action == "init":
                return _render()

            # 목록 → 상세
            if action.startswith("avail:"):
                idx = int(action.split(":")[1])
                state["page"] = "detail_available"
                state["selected_idx"] = idx
                return _render()

            if action.startswith("active:"):
                idx = int(action.split(":")[1])
                state["page"] = "detail_active"
                state["selected_idx"] = idx
                return _render()

            # 수락
            if action.startswith("accept:"):
                idx = int(action.split(":")[1])
                q = board_available[idx]
                ok = mgr.accept_quest(q.unique_id)
                if ok:
                    state["result"] = "accepted"
                    return True  # dialog 종료
                state["page"] = "list"
                return _render()

            # 포기
            if action.startswith("abandon:"):
                idx = int(action.split(":")[1])
                q = board_active[idx]
                mgr.fail_quest(q.unique_id, reason="포기")
                state["result"] = "abandoned"
                return True  # dialog 종료

            # 돌아가기
            if action == "back":
                state["page"] = "list"
                state["selected_idx"] = None
                return _render()

            return None

        yield morld.dialog("", autofill="off", proc=_handle, result=state)

        # dialog 종료 후 메시지
        if state["result"] == "accepted":
            yield ui.dialog("의뢰를 수락했다.\n\n퀘스트 던전으로 이동하면 진입할 수 있다.")
        elif state["result"] == "abandoned":
            yield ui.dialog("의뢰를 포기했다.")
