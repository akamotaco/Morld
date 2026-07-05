# quest_reporter.py — 공용 퀘스트 보고 모듈
#
# 오브젝트/NPC/장소가 퀘스트 의뢰자(reporter)일 때 공통으로 쓰는 보고 UI/로직.
#
# 사용 패턴:
#   1. 퀘스트 정의에 reporter = "<key>" 설정 → 조건 충족 시 자동 완료되지 않고
#      COMPLETED 상태로 대기.
#   2. 보고 대상 오브젝트/NPC의 focus_text/available_actions에서 recheck()·has_reportable()
#      호출로 보고 가능 여부 확인.
#   3. "완료 보고" 액션에서 render_report_dialog(key, name) 실행 → 리스트 UI.
#   4. 플레이어가 "확인" 클릭 → confirm_quest(quest_id):
#        on_confirm 훅 액션 실행(consume_item 등) → claim_reward.
#
# 확인 액션 타입(on_confirm):
#   - consume_item: {"type":"consume_item", "item": unique_id, "count": N}
#   기본 제공. 신규 타입은 register_confirm_action(name, handler)로 확장.

import morld
from engine.quest import get_quest_manager, QuestStatus


# ============================================
# 확인 액션 레지스트리
# ============================================

_confirm_action_handlers = {}


def register_confirm_action(name, handler):
    """on_confirm 액션 타입 등록. handler(player_id, action, quest_id)."""
    _confirm_action_handlers[name] = handler


def _action_consume_item(player_id, action, quest_id):
    """조건에 쓰인 아이템을 인벤토리에서 제거.
    action = {"type":"consume_item", "item": unique_id, "count": N}
    """
    item_unique = action.get("item")
    count = int(action.get("count", 1))
    if not item_unique or count <= 0:
        return
    item_id = morld.get_item_id_by_unique(item_unique)
    if item_id is None:
        print("[quest_reporter] consume_item: unknown item " + str(item_unique))
        return
    morld.remove_item(player_id, item_id, count)


register_confirm_action("consume_item", _action_consume_item)


def reset():
    """확인 액션 레지스트리를 기본 상태로 복원 — pi-world reset 계약.

    챕터 전환/테스트 간 시나리오 등록 핸들러 잔존 방지.
    기본 제공 consume_item은 유지.
    """
    _confirm_action_handlers.clear()
    _confirm_action_handlers["consume_item"] = _action_consume_item


# ============================================
# 조회 + 재평가
# ============================================

def recheck(reporter_key):
    """이 reporter의 IN_PROGRESS 퀘스트 조건 재평가 → 충족 시 COMPLETED 승격."""
    mgr = get_quest_manager()
    for quest in list(mgr.get_active_quests()):
        if quest.reporter == reporter_key:
            mgr.check_quest_conditions(quest.unique_id)


def get_reportable(reporter_key):
    """보고 가능(=COMPLETED) 퀘스트 리스트."""
    mgr = get_quest_manager()
    return [q for q in mgr.get_quests_by_status(QuestStatus.COMPLETED)
            if q.reporter == reporter_key]


def get_pending(reporter_key):
    """아직 조건 미충족이지만 이 reporter가 받는 IN_PROGRESS 퀘스트."""
    mgr = get_quest_manager()
    return [q for q in mgr.get_active_quests()
            if q.reporter == reporter_key]


def has_reportable(reporter_key, *, recheck_first=True):
    """보고 가능 퀘스트가 있는가. recheck_first=True면 먼저 조건 재평가."""
    if recheck_first:
        recheck(reporter_key)
    return len(get_reportable(reporter_key)) > 0


# ============================================
# 확인 처리
# ============================================

def confirm_quest(quest_id):
    """COMPLETED 상태 퀘스트의 on_confirm 액션 실행 + claim_reward.

    Returns: True if successful.
    """
    mgr = get_quest_manager()
    quest = mgr._get_quest_instance(quest_id)
    if quest is None:
        return False
    if mgr.get_quest_status(quest_id) != QuestStatus.COMPLETED:
        return False

    player_id = morld.get_player_id()
    if player_id is None:
        return False

    # on_confirm 훅 실행 (consume_item 등)
    actions = getattr(quest, "on_confirm", []) or []
    for action in actions:
        atype = action.get("type")
        handler = _confirm_action_handlers.get(atype)
        if handler is None:
            print("[quest_reporter] Unknown confirm action: " + str(atype))
            continue
        handler(player_id, action, quest_id)

    # 보상 지급 + 상태 전환 (repeatable이면 AVAILABLE로 리셋)
    mgr.claim_reward(quest_id)
    return True


# ============================================
# 보고 UI (generator — morld.dialog/ui.dialog 사용)
# ============================================

def render_report_dialog(reporter_key, reporter_name="의뢰자"):
    """보고 UI generator.

    1. 진입 시 recheck → COMPLETED 승격
    2. 보고 가능 퀘스트 리스트 + 보고 대기(IN_PROGRESS) 표시
    3. COMPLETED 항목 "확인" 클릭 → confirm_quest
    """
    import ui

    recheck(reporter_key)

    state = {"result": None}

    def _render():
        reportable = get_reportable(reporter_key)
        pending = get_pending(reporter_key)

        lines = ["[b]" + reporter_name + " — 보고[/b]", ""]

        if reportable:
            lines.append("[완료 — 확인 대기]")
            for i, q in enumerate(reportable):
                lines.append("  [url=@proc:confirm:" + str(i) + "]"
                             + q.name + " (확인)[/url]")
            lines.append("")

        if pending:
            mgr = get_quest_manager()
            lines.append("[진행 중]")
            for q in pending:
                progress = mgr.get_quest_progress(q.unique_id)
                lines.append("  " + q.name + " ("
                             + str(progress["current"]) + "/"
                             + str(progress["total"]) + ")")
            lines.append("")

        if not reportable and not pending:
            lines.append("보고할 퀘스트가 없다.")
            lines.append("")

        lines.append("[url=@finish]닫기[/url]")
        return "\n".join(lines)

    def _handle(action):
        if action == "init":
            return _render()
        if action.startswith("confirm:"):
            idx = int(action.split(":")[1])
            reportable = get_reportable(reporter_key)
            if 0 <= idx < len(reportable):
                q = reportable[idx]
                ok = confirm_quest(q.unique_id)
                if ok:
                    state["result"] = "confirmed:" + q.name
                    return True
            return _render()
        return None

    yield morld.dialog("", autofill="off", proc=_handle, result=state)

    if state["result"] and state["result"].startswith("confirmed:"):
        qname = state["result"].split(":", 1)[1]
        yield ui.dialog("의뢰 '" + qname + "' 완료 보고.")
