# pregnancy.py - 임신/출산 시스템
#
# 월경 주기 → 수정 판정 → 임신 기간(40주) → 출산 → 아이 NPC 생성
# 매 시간 업데이트 (subscribe_time_elapsed, 자정에 일일 처리)
#
# Prop:
#   생식:주기일     — 현재 주기 일수 (1~주기길이)
#   생식:주기길이   — 개인별 주기 길이 (25-35)
#   상태:임신       — 0/1
#   상태:임신주차   — 0-42
#   상태:수정일     — 수정된 게임 일수
#   상태:아이아버지  — 아버지 이름
#   상태:아이아버지id — 아버지 unit_id
#
# DES 호환: subscribe_time_elapsed(min_interval=1h)

import morld
import random

# ============================================
# 시간 스케일
# ============================================

PREGNANCY_TIME_SCALE = 1.0  # 기본 배율 (디버그에서 수정 가능)
MILLIS_PER_HOUR = 3_600_000
LACTATION_DURATION_DAYS = 180  # 수유 지속 기간 (출산 후 6개월)

# ============================================
# 상수
# ============================================

# 임신 3분기 효과
PREGNANCY_EFFECTS = {
    "trimester_1": {
        "morning_sickness_chance": 0.2,
        "fatigue_bonus": 0,
        "speed_modifier": 1.0,
    },
    "trimester_2": {
        "morning_sickness_chance": 0.0,
        "fatigue_bonus": 0,
        "speed_modifier": 1.0,
    },
    "trimester_3": {
        "morning_sickness_chance": 0.0,
        "fatigue_bonus": 2,
        "speed_modifier": 0.7,
    },
}

# 아이 이름 후보
CHILD_NAMES_MALE = ["카이", "레오", "유진", "하루", "소라"]
CHILD_NAMES_FEMALE = ["하나", "미유", "유리", "사쿠라", "린"]

# ============================================
# 레지스트리
# ============================================

_registry = set()  # V 보유 캐릭터 ID
_child_registry = {}  # mother_id -> [child_id, ...]


def register_character(unit_id):
    """임신 시스템에 캐릭터 등록 (V 보유자만)"""
    import gender as gender_mod
    if not gender_mod.has_anatomy(unit_id, "V"):
        return

    _registry.add(unit_id)

    # 이미 주기일이 있으면 스킵 (챕터 전환 복원)
    if morld.get_unit_prop(unit_id, "생식:주기일") is not None:
        return

    cycle_len = random.randint(25, 35)
    morld.set_unit_prop(unit_id, "생식:주기길이", cycle_len)
    morld.set_unit_prop(unit_id, "생식:주기일", random.randint(1, cycle_len))


def reset():
    """챕터 전환 시 리셋"""
    _registry.clear()
    _child_registry.clear()


# ============================================
# 월경 주기
# ============================================

def _get_fertility_chance(unit_id):
    """현재 주기 기반 가임 확률"""
    cycle_day = morld.get_unit_prop(unit_id, "생식:주기일") or 1
    cycle_len = morld.get_unit_prop(unit_id, "생식:주기길이") or 28

    ovulation_day = cycle_len // 2
    diff = abs(cycle_day - ovulation_day)

    if diff == 0:
        return 0.30  # 배란일
    elif diff <= 3:
        return 0.15  # 배란기
    else:
        return 0.0   # 비가임기


def get_cycle_phase(unit_id):
    """현재 주기 단계 반환 (UI/디버그용)"""
    cycle_day = morld.get_unit_prop(unit_id, "생식:주기일") or 1
    cycle_len = morld.get_unit_prop(unit_id, "생식:주기길이") or 28

    if cycle_day <= 5:
        return "월경기"
    elif cycle_day <= 10:
        return "여포기"
    else:
        ovulation_day = cycle_len // 2
        if abs(cycle_day - ovulation_day) <= 3:
            return "배란기"
        elif cycle_day > ovulation_day + 3:
            return "황체기"
        else:
            return "여포기"


# ============================================
# 수정 판정
# ============================================

def check_conception(player_id, partner_id):
    """P 보유자 절정 시 호출 — 수정 가능 여부 판정

    romance.py / npc_initiative.py의 절정 처리 블록에서 호출.
    삽입 행위(pregnancy_check=True)가 활성 토글일 때 + P 보유자 절정 시에만.
    """
    import gender as gender_mod

    if gender_mod.has_anatomy(player_id, "P") and gender_mod.has_anatomy(partner_id, "V"):
        _try_conceive(partner_id, player_id)

    if gender_mod.has_anatomy(partner_id, "P") and gender_mod.has_anatomy(player_id, "V"):
        _try_conceive(player_id, partner_id)


def _try_conceive(receiver_id, inseminator_id):
    """수정 시도"""
    if morld.get_unit_prop(receiver_id, "상태:임신"):
        return

    chance = _get_fertility_chance(receiver_id)
    if chance <= 0:
        return

    if random.random() < chance:
        _conceive(receiver_id, inseminator_id)


def _conceive(receiver_id, inseminator_id):
    """수정 성공 — 임신 시작"""
    morld.set_unit_prop(receiver_id, "상태:임신", 1)
    morld.set_unit_prop(receiver_id, "상태:임신주차", 0)

    time_info = morld.get_time_info()
    conception_day = time_info.get("day", 0)
    morld.set_unit_prop(receiver_id, "상태:수정일", conception_day)

    insem_info = morld.get_unit_info(inseminator_id)
    insem_name = insem_info.get("name", "???") if insem_info else "???"
    morld.set_unit_prop(receiver_id, "상태:아이아버지", insem_name)
    morld.set_unit_prop(receiver_id, "상태:아이아버지id", inseminator_id)


# ============================================
# 임신 기간 관리
# ============================================

def get_trimester(unit_id):
    """현재 임신 분기 반환"""
    if not morld.get_unit_prop(unit_id, "상태:임신"):
        return None
    week = morld.get_unit_prop(unit_id, "상태:임신주차") or 0
    if week <= 12:
        return "trimester_1"
    elif week <= 27:
        return "trimester_2"
    else:
        return "trimester_3"


def get_pregnancy_week(unit_id):
    """임신 주차 반환 (비임신 시 None)"""
    if not morld.get_unit_prop(unit_id, "상태:임신"):
        return None
    return morld.get_unit_prop(unit_id, "상태:임신주차") or 0


def is_pregnant(unit_id):
    """임신 여부"""
    return bool(morld.get_unit_prop(unit_id, "상태:임신"))


def is_intercourse_blocked(unit_id):
    """삽입 행위 차단 여부 (임신 28주+)"""
    week = get_pregnancy_week(unit_id)
    if week is None:
        return False
    return week >= 28


def is_romance_blocked(unit_id):
    """연애 행위 전체 차단 여부 (임신 40주+)"""
    week = get_pregnancy_week(unit_id)
    if week is None:
        return False
    return week >= 40


def is_lactating(unit_id):
    """수유 여부 (임신 20주+ 또는 출산 후 수유 지속)"""
    return bool(morld.get_unit_prop(unit_id, "상태:수유"))


def _pregnancy_daily(unit_id):
    """임신 중 매일 업데이트 — 주차 계산 + 수유 시작"""
    conception_day = morld.get_unit_prop(unit_id, "상태:수정일") or 0
    current_day = morld.get_time_info().get("day", 0)

    elapsed_days = current_day - conception_day
    scaled = round(elapsed_days * PREGNANCY_TIME_SCALE)
    week = scaled // 7

    morld.set_unit_prop(unit_id, "상태:임신주차", min(week, 42))

    # 임신 20주+ → 수유 시작 + 가슴 크기 증가
    if week >= 20 and not morld.get_unit_prop(unit_id, "상태:수유"):
        morld.set_unit_prop(unit_id, "상태:수유", 1)
        morld.set_unit_prop(unit_id, "상태:수유시작일",
                            morld.get_time_info().get("day", 0))
        # 가슴 크기 +1 (최대 3)
        import gender as gender_mod
        current_breast = gender_mod.get_breast_size(unit_id)
        if current_breast < 3:
            morld.set_unit_prop(unit_id, "가슴:크기", current_breast + 1)


# ============================================
# 출산
# ============================================

def reset_pregnancy(unit_id):
    """출산 후 임신 상태 초기화"""
    morld.set_unit_prop(unit_id, "상태:임신", 0)
    morld.set_unit_prop(unit_id, "상태:임신주차", 0)
    morld.set_unit_prop(unit_id, "상태:수정일", None)
    # 월경 주기 재시작
    morld.set_unit_prop(unit_id, "생식:주기일", 1)
    # 수유시작일이 없으면 현재 날짜로 설정 (기존 데이터 호환)
    if morld.get_unit_prop(unit_id, "상태:수유") and not morld.get_unit_prop(unit_id, "상태:수유시작일"):
        morld.set_unit_prop(unit_id, "상태:수유시작일",
                            morld.get_time_info().get("day", 0))


def spawn_child(mother_agent):
    """출산 시 아이 NPC 동적 생성

    Args:
        mother_agent: 어머니 BaseAgent 인스턴스

    Returns:
        child_id: 생성된 아이 unit_id
    """
    mother_id = mother_agent.unit_id
    mother_info = morld.get_unit_info(mother_id)
    mother_name = mother_info.get("name", "???") if mother_info else "???"
    father_name = morld.get_unit_prop(mother_id, "상태:아이아버지") or "???"

    # 성별 결정
    child_gender = "female" if random.random() < 0.5 else "male"

    # 이름 생성
    if child_gender == "female":
        child_name = random.choice(CHILD_NAMES_FEMALE)
    else:
        child_name = random.choice(CHILD_NAMES_MALE)

    # Asset 생성 및 인스턴스화
    from assets.characters.child import Child
    child = Child()
    child.name = child_name
    child.type = child_gender
    child.props = {
        "성별": child_gender,
        "나이": 0,
        "생존:체력": 50,
        "생존:최대체력": 50,
        "생존:포만감": 100,
        "부모:어머니": mother_name,
        "부모:아버지": father_name,
    }

    # 어머니 수면 위치에 배치
    loc = mother_agent.sleep_location
    if not loc:
        loc = {"region_id": 0, "location_id": 1}

    child_id = morld.create_id("unit")
    child.instantiate(child_id, loc["region_id"], loc["location_id"])

    # Agent 등록
    from think import register_agent
    from think.child_agent import ChildAgent
    agent = ChildAgent(child_id)
    agent.sleep_location = loc
    register_agent(child_id, agent)

    import needs
    needs.register_character(child_id)

    # 어머니-아이 연결 기록
    if mother_id not in _child_registry:
        _child_registry[mother_id] = []
    _child_registry[mother_id].append(child_id)

    return child_id


def get_children(mother_id):
    """어머니의 아이 목록 반환"""
    return list(_child_registry.get(mother_id, []))


def get_latest_child(mother_id):
    """어머니의 마지막 아이 ID (없으면 None)"""
    children = _child_registry.get(mother_id, [])
    return children[-1] if children else None


# ============================================
# UI
# ============================================

def get_pregnancy_status_text(unit_id):
    """NPC 포커스 시 임신 상태 텍스트"""
    if not morld.get_unit_prop(unit_id, "상태:임신"):
        return None

    week = morld.get_unit_prop(unit_id, "상태:임신주차") or 0
    trimester = get_trimester(unit_id)

    if week >= 40:
        return "[color=red]출산이 임박했다[/color]"
    elif trimester == "trimester_3":
        return f"[color=yellow]임신 {week}주차 — 만삭에 가까워지고 있다[/color]"
    elif trimester == "trimester_1":
        return f"임신 {week}주차 — 입덧 증상"
    else:
        return f"임신 {week}주차"


# ============================================
# 디버그 API
# ============================================

def set_time_scale(scale):
    """임신/월경 시간 배율 설정 (디버그 전용)"""
    global PREGNANCY_TIME_SCALE
    PREGNANCY_TIME_SCALE = max(0.1, scale)


def get_time_scale():
    return PREGNANCY_TIME_SCALE


def force_conceive(unit_id, father_id):
    """강제 임신 (디버그)"""
    _conceive(unit_id, father_id)


def set_week(unit_id, week):
    """임신 주차 직접 설정 (디버그)"""
    if not morld.get_unit_prop(unit_id, "상태:임신"):
        # 임신 상태가 아니면 강제 설정
        morld.set_unit_prop(unit_id, "상태:임신", 1)
        time_info = morld.get_time_info()
        morld.set_unit_prop(unit_id, "상태:수정일", time_info.get("day", 0))
    morld.set_unit_prop(unit_id, "상태:임신주차", min(max(0, week), 42))


def force_birth(unit_id):
    """즉시 출산 트리거 (디버그) — 주차를 40으로 설정"""
    set_week(unit_id, 40)


def get_cycle_info(unit_id):
    """월경 주기 정보 출력 (디버그)"""
    cycle_day = morld.get_unit_prop(unit_id, "생식:주기일")
    cycle_len = morld.get_unit_prop(unit_id, "생식:주기길이")
    is_preg = morld.get_unit_prop(unit_id, "상태:임신")
    week = morld.get_unit_prop(unit_id, "상태:임신주차")

    info = morld.get_unit_info(unit_id)
    name = info.get("name", "???") if info else "???"

    lines = [f"[임신 시스템] {name} (ID: {unit_id})"]
    if cycle_day is not None:
        phase = get_cycle_phase(unit_id)
        fertility = _get_fertility_chance(unit_id)
        lines.append(f"  주기: {cycle_day}/{cycle_len}일 ({phase})")
        lines.append(f"  가임 확률: {fertility:.0%}")
    else:
        lines.append("  주기: 미등록")

    if is_preg:
        trimester = get_trimester(unit_id)
        father = morld.get_unit_prop(unit_id, "상태:아이아버지") or "???"
        lines.append(f"  임신: {week}주차 ({trimester})")
        lines.append(f"  아버지: {father}")
    else:
        lines.append("  임신: 아님")

    children = get_children(unit_id)
    if children:
        lines.append(f"  아이: {len(children)}명")

    return "\n".join(lines)


# ============================================
# 매일 업데이트 (subscribe_time_elapsed)
# ============================================

def _daily_update(unit_id):
    """매일 자정 업데이트"""
    # 임신 중이면 주기 정지, 임신 일일 업데이트
    if morld.get_unit_prop(unit_id, "상태:임신"):
        _pregnancy_daily(unit_id)
        return

    # 수유 종료 체크 (비임신 + 수유 중 → 출산 후 180일 경과)
    if morld.get_unit_prop(unit_id, "상태:수유"):
        start_day = morld.get_unit_prop(unit_id, "상태:수유시작일")
        if start_day is not None:
            current_day = morld.get_time_info().get("day", 0)
            if current_day - start_day >= LACTATION_DURATION_DAYS:
                morld.set_unit_prop(unit_id, "상태:수유", 0)
                morld.clear_prop(unit_id, "상태:수유시작일")
                # 가슴 크기 -1 (원래 값 이하로 내려가지 않도록)
                import gender as gender_mod
                current_breast = gender_mod.get_breast_size(unit_id)
                base_breast = gender_mod.BREAST_SIZE_DEFAULT.get(
                    gender_mod.get_gender(unit_id), 0)
                if current_breast > base_breast:
                    morld.set_unit_prop(unit_id, "가슴:크기",
                                        current_breast - 1)

    # 주기일 진행
    cycle_day = morld.get_unit_prop(unit_id, "생식:주기일") or 1
    cycle_len = morld.get_unit_prop(unit_id, "생식:주기길이") or 28

    cycle_day += 1
    if cycle_day > cycle_len:
        cycle_day = 1
    morld.set_unit_prop(unit_id, "생식:주기일", cycle_day)


def _on_time_elapsed(millis):
    """on_time_elapsed 핸들러 (1시간 간격) — 자정에만 처리"""
    hour = morld.get_time_info().get("hour", -1)
    if hour != 0:
        return

    for unit_id in _registry:
        _daily_update(unit_id)


# 모듈 로드 시 이벤트 구독 (1시간 간격)
from events import subscribe_time_elapsed
subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
