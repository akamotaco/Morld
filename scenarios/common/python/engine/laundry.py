# laundry.py - 세탁/건조 시간 관리 모듈
#
# 세탁기: 의류 오염도(오염:수치) 제거, 소요 60분
# 건조기: 의류 젖음(습도:젖음) 제거, 소요 30분
#
# 워크플로우:
#   1. register_machine() — 오브젝트 instantiate에서 호출
#   2. start_machine() — 플레이어 액션에서 호출
#   3. _on_time_elapsed() — 매시간 진행도 업데이트
#   4. _complete_machine() — 완료 시 효과 적용
#   5. reset_machine() — 빨래 꺼낸 후 초기화
#
# Props:
#   가전:상태 — 0=대기, 1=작동중, 2=완료
#   가전:남은시간 — 분 단위

import morld

MILLIS_PER_HOUR = 3_600_000

# prop 이름
PROP_STATE = "가전:상태"
PROP_REMAINING = "가전:남은시간"

# 소요 시간 (분)
WASH_DURATION = 60   # 세탁: 1시간
DRY_DURATION = 30    # 건조: 30분

# 상태값
STATE_IDLE = 0
STATE_PROCESSING = 1
STATE_DONE = 2


# ========================================
# Registry
# ========================================

_machines = {}  # {unit_id: {"type": "washer"|"dryer"}}
_initialized = False


def register_machine(unit_id, machine_type):
    """오브젝트 instantiate에서 호출"""
    _ensure_initialized()
    _machines[unit_id] = {"type": machine_type}


# ========================================
# Machine Control API
# ========================================

def start_machine(unit_id, machine_type):
    """세탁/건조 시작"""
    duration = WASH_DURATION if machine_type == "washer" else DRY_DURATION
    morld.set_unit_prop(unit_id, PROP_STATE, STATE_PROCESSING)
    morld.set_unit_prop(unit_id, PROP_REMAINING, duration)
    name = "세탁기" if machine_type == "washer" else "건조기"
    print(f"[laundry] {name} 시작 (unit_id={unit_id}, duration={duration}분)")


def is_machine_busy(unit_id):
    """작동 중인지 확인"""
    state = morld.get_unit_prop(unit_id, PROP_STATE)
    return state == STATE_PROCESSING


def get_machine_state(unit_id):
    """현재 상태 반환 (0=대기, 1=작동중, 2=완료)"""
    return morld.get_unit_prop(unit_id, PROP_STATE) or STATE_IDLE


def get_remaining_time(unit_id):
    """남은 시간 (분) 반환"""
    return morld.get_unit_prop(unit_id, PROP_REMAINING) or 0


def reset_machine(unit_id):
    """빨래 꺼낸 후 초기화"""
    morld.clear_prop(unit_id, PROP_STATE)
    morld.clear_prop(unit_id, PROP_REMAINING)


def get_machine_focus_text(unit_id, machine_type):
    """오브젝트 focus_text 반환"""
    state = get_machine_state(unit_id)
    name = "세탁기" if machine_type == "washer" else "건조기"

    if state == STATE_IDLE:
        inv = morld.get_unit_inventory(unit_id)
        if inv:
            return f"{name}에 빨래가 들어있다."
        return f"{name}."
    elif state == STATE_PROCESSING:
        remaining = get_remaining_time(unit_id)
        return f"{name}가 작동 중이다. (남은 시간: {remaining}분)"
    elif state == STATE_DONE:
        return f"{name} 작동이 완료되었다. 빨래를 꺼내야 한다."
    return f"{name}."


# ========================================
# 시간 구독
# ========================================

def _ensure_initialized():
    """lazy init — 매시간 구독 등록"""
    global _initialized
    if _initialized:
        return
    _initialized = True
    from engine.event_core import subscribe_time_elapsed
    subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
    print("[laundry] 시간 구독 등록")


def _on_time_elapsed(millis):
    """매시간: 작동 중인 기계 진행도 업데이트"""
    for unit_id in list(_machines.keys()):
        state = morld.get_unit_prop(unit_id, PROP_STATE)
        if state != STATE_PROCESSING:
            continue

        remaining = morld.get_unit_prop(unit_id, PROP_REMAINING) or 0
        remaining -= 60  # 1시간 = 60분 감소

        if remaining <= 0:
            _complete_machine(unit_id)
        else:
            morld.set_unit_prop(unit_id, PROP_REMAINING, remaining)


def _complete_machine(unit_id):
    """작동 완료 — 효과 적용"""
    machine = _machines.get(unit_id)
    if not machine:
        return

    morld.set_unit_prop(unit_id, PROP_STATE, STATE_DONE)
    morld.clear_prop(unit_id, PROP_REMAINING)

    # 인벤토리 아이템에 효과 적용
    inv = morld.get_unit_inventory(unit_id)
    if not inv:
        return

    if machine["type"] == "washer":
        import pollution
        for item_id in inv:
            pollution.set_unit_pollution(item_id, 0)
        print(f"[laundry] 세탁 완료 (unit_id={unit_id}), 오염도 제거")
    elif machine["type"] == "dryer":
        import humidity
        for item_id in inv:
            humidity.dry_unit(item_id, 999)
        print(f"[laundry] 건조 완료 (unit_id={unit_id}), 젖음 제거")


# ========================================
# 챕터 전환
# ========================================

def reset():
    """챕터 전환 초기화"""
    global _initialized, _machines
    _initialized = False
    _machines = {}
    print("[laundry] reset")
