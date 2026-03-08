# events/progression.py - 데모 진행 추적 시스템
#
# 14단계 데모 흐름을 추적하고 단계 전환 시 이벤트를 트리거한다.
# 단계 상태는 모듈 변수로 관리 (챕터 리로드 시 초기화).
#
# Step 1:  계약 (프롤로그)
# Step 2:  지저철 탑승
# Step 3:  플랫폼 도착
# Step 4:  플랫폼 탐색 (퀘스트)
# Step 5:  건축 튜토리얼
# Step 6:  에이전트 증원 도착
# Step 7:  기본 건설 (임시 막사 + 보관소)
# Step 8:  첫 임무 브리핑
# Step 9:  분대 편성
# Step 10: 탐사 출발
# Step 11: 탐사 (자유 탐색)
# Step 12: 귀환
# Step 13: 임무 완료
# Step 14: 엔딩

import morld

# 현재 단계 (0 = 시작 전)
_current_step = 0

# 단계별 메타데이터
STEPS = {
    1:  {"name": "계약",           "trigger": "auto"},
    2:  {"name": "지저철 탑승",    "trigger": "auto"},       # Step 1 완료 시 자동
    3:  {"name": "플랫폼 도착",    "trigger": "auto"},       # Step 2 완료 시 자동
    4:  {"name": "플랫폼 탐색",    "trigger": "quest"},      # 퀘스트 완료 대기
    5:  {"name": "건축 튜토리얼",  "trigger": "auto"},       # Step 4 완료 시 자동
    6:  {"name": "에이전트 증원",  "trigger": "auto"},       # Step 5 완료 시 자동
    7:  {"name": "기본 건설",      "trigger": "build"},      # 건설 완료 대기
    8:  {"name": "첫 임무 브리핑", "trigger": "auto"},       # Step 7 완료 시 자동
    9:  {"name": "분대 편성",      "trigger": "player"},     # 플레이어 조작 대기
    10: {"name": "탐사 출발",      "trigger": "auto"},       # Step 9 완료 시 자동
    11: {"name": "탐사",           "trigger": "player"},     # 자유 탐색
    12: {"name": "귀환",           "trigger": "player"},     # 귀환 명령 대기
    13: {"name": "임무 완료",      "trigger": "auto"},       # Step 12 완료 시 자동
    14: {"name": "엔딩",           "trigger": "auto"},       # Step 13 완료 시 자동
}

# 단계 전환 시 호출되는 콜백 (외부 등록용)
_step_callbacks = {}


def reset():
    """진행 상태 초기화 (챕터 로드 시)"""
    global _current_step
    _current_step = 0
    _step_callbacks.clear()


def get_current_step():
    """현재 단계 반환"""
    return _current_step


def get_step_name(step=None):
    """단계 이름 반환"""
    s = step if step is not None else _current_step
    info = STEPS.get(s)
    return info["name"] if info else f"Step {s}"


def is_step(step):
    """현재 단계가 지정 단계인지 확인"""
    return _current_step == step


def is_step_at_least(step):
    """현재 단계가 지정 단계 이상인지 확인"""
    return _current_step >= step


def advance_to(step):
    """지정 단계로 진행

    중간 단계를 건너뛸 수 있다 (디버그/테스트용).
    자동 트리거 단계는 연쇄 진행하지 않는다 (명시적 호출 필요).

    Args:
        step: 목표 단계 (1~14)

    Returns:
        bool: 진행 성공 여부
    """
    global _current_step

    if step < 1 or step > 14:
        print(f"[progression] Invalid step: {step}")
        return False

    if step <= _current_step:
        print(f"[progression] Already at step {_current_step}, cannot go back to {step}")
        return False

    old_step = _current_step
    _current_step = step

    step_name = get_step_name(step)
    print(f"[progression] Step {old_step} → {step}: {step_name}")

    # 콜백 실행
    callback = _step_callbacks.get(step)
    if callback:
        callback(step)

    return True


def complete_step(step=None):
    """현재 단계 완료 → 다음 단계로 진행

    Args:
        step: 완료할 단계 (None이면 현재 단계). 현재 단계가 아니면 무시.

    Returns:
        bool: 다음 단계로 진행했으면 True
    """
    if step is not None and step != _current_step:
        print(f"[progression] Step {step} is not current ({_current_step}), ignoring complete")
        return False

    if _current_step >= 14:
        print("[progression] Demo complete -no more steps")
        return False

    return advance_to(_current_step + 1)


def on_step(step, callback):
    """단계 전환 콜백 등록

    Args:
        step: 단계 번호
        callback: callback(step) -해당 단계 진입 시 호출
    """
    _step_callbacks[step] = callback


def trigger_step_event(step=None):
    """현재 단계의 이벤트 핸들러 실행 (generator 반환)

    이벤트 핸들러가 generator를 반환하면 C# 이벤트 시스템이 실행.
    generator가 아니면 즉시 실행.

    Returns:
        generator or None
    """
    s = step if step is not None else _current_step

    handler = _STEP_HANDLERS.get(s)
    if handler:
        return handler()
    return None


# === Step handlers (이벤트 연결) ===

def _handle_step_1():
    """Step 1: 계약"""
    from events.prologue import handle_contract
    return handle_contract()


def _handle_step_5():
    """Step 5: 건축 튜토리얼"""
    from events.tutorial import handle_build_tutorial
    return handle_build_tutorial()


def _handle_step_6():
    """Step 6: 에이전트 증원"""
    from events.tutorial import handle_reinforcement
    return handle_reinforcement()


def _handle_step_8():
    """Step 8: 첫 임무 브리핑"""
    from events.first_mission import handle_mission_briefing
    return handle_mission_briefing()


def _handle_step_10():
    """Step 10: 탐사 출발"""
    # TODO: squad_id 결정 로직
    from events.first_mission import start_expedition
    start_expedition(squad_id=0)
    return None


def _handle_step_13():
    """Step 13: 임무 완료"""
    from events.first_mission import handle_mission_complete
    return handle_mission_complete()


def _handle_step_14():
    """Step 14: 엔딩"""
    from events.ending import handle_ending
    return handle_ending()


# Step → handler 매핑
_STEP_HANDLERS = {
    1:  _handle_step_1,
    5:  _handle_step_5,
    6:  _handle_step_6,
    8:  _handle_step_8,
    10: _handle_step_10,
    13: _handle_step_13,
    14: _handle_step_14,
}


def get_demo_status():
    """데모 진행 상황 요약 (디버그/UI용)

    Returns:
        dict: {step, name, total, progress_pct}
    """
    return {
        "step": _current_step,
        "name": get_step_name(),
        "total": 14,
        "progress_pct": round(_current_step / 14 * 100),
    }
