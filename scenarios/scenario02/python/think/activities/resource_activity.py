"""자원수집 → 보관 공통 핸들러

도구 없이 자원을 수집하여 보관소에 저장하는 활동 패턴.
Phase flow: idle → going_to_work → storing

cfg dict keys:
    activity_name: str      - 활동 이름 ("채집", "물자수집", "난방 연료 수집")
    check_need: callable    - (optional) callable(agent) -> bool, True=필요, False=충분
    resolve_target: callable - callable(agent) -> target_dict | None
    do_work: callable       - callable(agent, target) -> None
    action_key: str         - ACTION_DURATION 키 ("gather", "scavenge", "gather_branch")
    work_label: str         - 이동/작업 시 표시명
    store_categories: list  - 저장 카테고리
    store_resolve: list     - 저장소 탐색 카테고리 순서
    store_label: str        - 저장 행동 이름
"""
from .tool_activity import phase_storing


def handle_resource_activity(agent, entry, cfg):
    """자원수집 → 보관 공통 루프"""
    phase = agent._activity_phase

    if phase == "idle":
        _phase_idle(agent, entry, cfg)
    elif phase == "going_to_work":
        _phase_going_to_work(agent, cfg)
    elif phase == "storing":
        phase_storing(agent, cfg["store_categories"], cfg["store_resolve"],
                      cfg["store_label"], next_phase="idle")


def _phase_idle(agent, entry, cfg):
    # 충분성 체크 (optional)
    check_need = cfg.get("check_need")
    if check_need and not check_need(agent):
        remaining = agent._remaining_millis_in_entry(entry)
        agent._insert_idle_job(cfg["activity_name"], max(remaining, 1))
        agent._action_taken = True
        return

    # 작업 대상 탐색
    target = cfg["resolve_target"](agent)
    if not target:
        return  # target 없음 → 디스패치 루프가 "할 일 없음" 폴백

    agent._activity_state["work_target"] = target
    agent._activity_phase = "going_to_work"


def _phase_going_to_work(agent, cfg):
    target = agent._activity_state.get("work_target")
    if not target:
        agent._activity_phase = "idle"
        return

    if agent._is_at(target):
        cfg["do_work"](agent, target)
        agent._activity_phase = "storing"
        agent._do_instant_action(cfg["work_label"], cfg["action_key"])
    else:
        agent._move_to(target, cfg["work_label"])
