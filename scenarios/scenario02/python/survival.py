# survival.py - 생존 시스템 (체력, 포만감, 기절)
#
# 시간 경과 시 호출되어 포만감 감소, 체력 증감, 기절 처리
# on_time_elapsed 이벤트 구독 방식으로 동작 (1시간 간격)
#
# 기절 규칙:
# - 만복도 0 → 체력 감소 (2/시간)
# - 체력 0 → 기절 상태 (8시간)
# - 기절 중 → 체력 서서히 회복 (최대체력/2까지), 만복도 0 유지
# - 기절 종료 → 만복도 0, 체력 = 최대체력/2
#
# DES 호환 (v0.2.2):
# - get_faint_remaining_millis(): think()에서 기절 job duration 결정에 사용
# - min_interval=1h: DES에서 큰 시간 단위가 넘어와도 내부 누적으로 1시간 단위 처리

import morld
from events import subscribe_time_elapsed


# === 상수 ===
SATIETY_DECAY_RATE = 1        # 1시간당 포만감 감소량
HEALTH_REGEN_RATE = 1         # 포만감 50 이상일 때 1시간당 체력 회복
HEALTH_DECAY_RATE = 2         # 포만감 0일 때 1시간당 체력 감소

SATIETY_THRESHOLD_HUNGRY = 30     # 배고픔 경고
SATIETY_THRESHOLD_STARVING = 10   # 굶주림 경고
HEALTH_THRESHOLD_DANGER = 20      # 위험 체력

FAINT_DURATION_HOURS = 8          # 기절 지속시간 (시간)
FAINT_RECOVERY_RATIO = 0.5       # 기절 후 체력 회복 비율 (최대체력의 절반)

# 시간 누적 (1시간 미만의 시간 경과 누적, 밀리초)
_accumulated_millis = 0

# NPC 만복도 추적
_npc_registry = set()          # 등록된 NPC unit_id 집합
_npc_accumulated = {}          # unit_id -> 누적 밀리초

# NPC 기절 상태: npc_id -> remaining_hours (남은 기절 시간)
_fainted_npcs = {}

# 플레이어 기절 상태
_player_fainted = False          # 현재 기절 중
_player_faint_pending = False    # 기절 다이얼로그 대기

# 시간 상수 (밀리초)
MILLIS_PER_HOUR = 3_600_000


def get_survival_stats(unit_id: int) -> dict:
    """
    유닛의 생존 스탯 조회

    Returns:
        dict: {health, max_health, satiety, max_satiety}
    """
    return {
        "health": morld.get_unit_prop(unit_id, "생존:체력") or 0,
        "max_health": morld.get_unit_prop(unit_id, "생존:최대체력") or 100,
        "satiety": morld.get_unit_prop(unit_id, "생존:포만감") or 0,
        "max_satiety": morld.get_unit_prop(unit_id, "생존:최대포만감") or 100,
    }


def set_health(unit_id: int, value: int):
    """체력 설정 (범위 제한: 0 ~ 최대체력)"""
    max_health = morld.get_unit_prop(unit_id, "생존:최대체력") or 100
    clamped = max(0, min(value, max_health))
    morld.set_unit_prop(unit_id, "생존:체력", clamped)


def set_satiety(unit_id: int, value: int):
    """포만감 설정 (범위 제한: 0 ~ 최대포만감)"""
    max_satiety = morld.get_unit_prop(unit_id, "생존:최대포만감") or 100
    clamped = max(0, min(value, max_satiety))
    morld.set_unit_prop(unit_id, "생존:포만감", clamped)


def add_satiety(unit_id: int, amount: int):
    """
    포만감 추가 (음식 먹기)

    Args:
        unit_id: 유닛 ID
        amount: 추가할 포만감 (양수)
    """
    current = morld.get_unit_prop(unit_id, "생존:포만감") or 0
    set_satiety(unit_id, current + amount)
    # 식사 → 배변욕 증가 (포만감 회복량에 비례)
    try:
        import needs
        needs.add_excretion(unit_id, max(5, amount // 2))
    except ImportError:
        pass


def add_health(unit_id: int, amount: int):
    """
    체력 추가/감소

    Args:
        unit_id: 유닛 ID
        amount: 변화량 (양수: 회복, 음수: 감소)
    """
    current = morld.get_unit_prop(unit_id, "생존:체력") or 0
    set_health(unit_id, current + amount)


# ========================================
# NPC 만복도/체력/기절 관리
# ========================================

def register_npc(unit_id: int):
    """NPC를 만복도 추적 대상에 등록 (Agent __init__에서 호출)"""
    _npc_registry.add(unit_id)
    _npc_accumulated[unit_id] = 0


def is_npc_hungry(unit_id: int, threshold: int = 30) -> bool:
    """NPC가 배고픈지 확인. 생존 prop이 없으면 False (배고프지 않음)."""
    if is_npc_fainted(unit_id):
        return False  # 기절 중에는 배고픔 인터럽트 안 함
    satiety = morld.get_unit_prop(unit_id, "생존:포만감")
    if satiety is None:
        return False
    return satiety <= threshold


def is_npc_fainted(unit_id: int) -> bool:
    """NPC가 기절 상태인지 확인"""
    return unit_id in _fainted_npcs


def get_faint_remaining_millis(npc_id: int) -> int:
    """기절 남은 시간 (밀리초). 기절 중이 아니면 0."""
    remaining_hours = _fainted_npcs.get(npc_id, 0)
    return max(0, remaining_hours * MILLIS_PER_HOUR)


def npc_eat(unit_id: int, satiety_amount: int):
    """NPC 식사 (포만감 추가)"""
    add_satiety(unit_id, satiety_amount)


def _enter_faint(npc_id: int):
    """NPC 기절 상태 진입"""
    _fainted_npcs[npc_id] = FAINT_DURATION_HOURS
    set_health(npc_id, 0)
    set_satiety(npc_id, 0)
    print(f"[survival] NPC {npc_id} fainted! (will recover in {FAINT_DURATION_HOURS}h)")


def _process_faint(npc_id: int, hours: int):
    """기절 중 NPC 처리 (체력 서서히 회복, 만복도 0 유지)"""
    if npc_id not in _fainted_npcs:
        return

    _fainted_npcs[npc_id] -= hours

    max_health = morld.get_unit_prop(npc_id, "생존:최대체력") or 100
    target_health = int(max_health * FAINT_RECOVERY_RATIO)

    if _fainted_npcs[npc_id] <= 0:
        # 기절 종료: 만복도 0, 체력 = 최대/2
        del _fainted_npcs[npc_id]
        set_health(npc_id, target_health)
        set_satiety(npc_id, 0)
        print(f"[survival] NPC {npc_id} recovered from faint (health={target_health})")
    else:
        # 서서히 회복: 경과 비율에 따라 체력 설정
        elapsed = FAINT_DURATION_HOURS - _fainted_npcs[npc_id]
        progress = elapsed / FAINT_DURATION_HOURS  # 0.0 ~ 1.0
        current_target = int(target_health * progress)
        set_health(npc_id, current_target)
        set_satiety(npc_id, 0)  # 만복도는 0 유지


# ========================================
# 플레이어 기절 관리
# ========================================

def _enter_player_faint():
    """플레이어 기절 상태 진입"""
    global _player_fainted, _player_faint_pending
    _player_fainted = True
    _player_faint_pending = True
    player_id = morld.get_player_id()
    set_health(player_id, 0)
    set_satiety(player_id, 0)
    print(f"[survival] Player fainted! (will recover in {FAINT_DURATION_HOURS}h)")


def is_player_faint_pending() -> bool:
    """플레이어 기절 다이얼로그가 대기 중인지"""
    return _player_faint_pending


def handle_player_faint():
    """플레이어 기절 다이얼로그 시퀀스 (generator)"""
    global _player_fainted, _player_faint_pending
    import ui
    _player_faint_pending = False

    yield ui.dialog([
        "눈앞이 흐려진다...",
        "몸에 힘이 빠진다...",
        "......",
        "(기절했다)"
    ])

    # 기절 시간 경과 (8시간) — NPC도 이 시간 동안 활동
    morld.advance_time_des(FAINT_DURATION_HOURS * MILLIS_PER_HOUR)

    # 회복
    _player_fainted = False
    player_id = morld.get_player_id()
    max_health = morld.get_unit_prop(player_id, "생존:최대체력") or 100
    set_health(player_id, int(max_health * FAINT_RECOVERY_RATIO))
    set_satiety(player_id, 0)

    yield ui.dialog([
        "......",
        "...정신이 돌아왔다.",
        "얼마나 쓰러져 있었던 거지...?",
        "몸이 아직 무겁지만, 움직일 수는 있다."
    ])


def _process_npc_time(npc_id: int, millis: int):
    """NPC 시간 경과 처리 (포만감 감소, 체력 증감, 기절)"""
    if millis <= 0:
        return

    # 기절 중이면 기절 회복 처리만
    if npc_id in _fainted_npcs:
        # millis → hours 변환 (min_interval=1h 이므로 보통 1)
        hours = max(1, millis // MILLIS_PER_HOUR)
        _process_faint(npc_id, hours)
        return

    # 생존 prop이 없으면 무시 (시나리오03 호환)
    satiety = morld.get_unit_prop(npc_id, "생존:포만감")
    if satiety is None:
        return

    _npc_accumulated[npc_id] = _npc_accumulated.get(npc_id, 0) + millis
    if _npc_accumulated[npc_id] < MILLIS_PER_HOUR:
        return

    hours = _npc_accumulated[npc_id] // MILLIS_PER_HOUR
    _npc_accumulated[npc_id] %= MILLIS_PER_HOUR

    # 1. 포만감 감소 (시간에 비례)
    loss = int(SATIETY_DECAY_RATE * hours)
    if loss > 0:
        set_satiety(npc_id, satiety - loss)
        satiety = morld.get_unit_prop(npc_id, "생존:포만감") or 0

    # 2. 체력 증감 (포만감에 따라)
    if satiety >= 50:
        # 포만감 충분: 체력 천천히 회복
        health_gain = int(HEALTH_REGEN_RATE * hours)
        if health_gain > 0:
            add_health(npc_id, health_gain)
    elif satiety <= 0:
        # 공복 상태: 체력 감소
        health_loss = int(HEALTH_DECAY_RATE * hours)
        if health_loss > 0:
            add_health(npc_id, -health_loss)
            # 체력 0 이하면 기절
            health = morld.get_unit_prop(npc_id, "생존:체력") or 0
            if health <= 0:
                _enter_faint(npc_id)


def process_time_elapsed(unit_id: int, millis: int):
    """
    시간 경과에 따른 생존 스탯 처리

    on_time_elapsed 이벤트에서 호출됨
    1시간 미만의 시간은 누적하여 처리

    Args:
        unit_id: 유닛 ID
        millis: 경과 시간 (밀리초)
    """
    global _accumulated_millis

    if millis <= 0:
        return

    # 플레이어 기절 중이면 스킵
    if _player_fainted:
        return

    # 생존 스탯이 없는 유닛은 무시
    stats = get_survival_stats(unit_id)
    if stats["max_satiety"] == 0:
        return

    # 시간 누적 후 1시간 단위로 처리
    _accumulated_millis += millis

    # 1시간 이상 누적되면 처리
    if _accumulated_millis < MILLIS_PER_HOUR:
        return

    # 처리할 시간 (시간 단위)
    hours_to_process = _accumulated_millis // MILLIS_PER_HOUR
    _accumulated_millis = _accumulated_millis % MILLIS_PER_HOUR

    satiety = stats["satiety"]

    # 1. 포만감 감소 (시간에 비례)
    satiety_loss = int(SATIETY_DECAY_RATE * hours_to_process)
    if satiety_loss > 0:
        set_satiety(unit_id, satiety - satiety_loss)
        satiety = morld.get_unit_prop(unit_id, "생존:포만감") or 0

    # 2. 체력 증감 (포만감에 따라)
    if satiety >= 50:
        # 포만감 충분: 체력 천천히 회복
        health_gain = int(HEALTH_REGEN_RATE * hours_to_process)
        if health_gain > 0:
            add_health(unit_id, health_gain)
    elif satiety <= 0:
        # 공복 상태: 체력 감소
        health_loss = int(HEALTH_DECAY_RATE * hours_to_process)
        if health_loss > 0:
            add_health(unit_id, -health_loss)
            # 체력 0 이하면 기절
            health = morld.get_unit_prop(unit_id, "생존:체력") or 0
            if health <= 0:
                _enter_player_faint()


def get_status_message(unit_id: int) -> str:
    """
    현재 상태 메시지 반환 (UI 표시용)

    Returns:
        상태 이상 메시지 (BBCode 포함) 또는 빈 문자열
    """
    stats = get_survival_stats(unit_id)
    satiety = stats["satiety"]
    health = stats["health"]

    messages = []

    # 포만감 상태 메시지
    if satiety <= 0:
        messages.append("[color=red]굶주리고 있다![/color]")
    elif satiety <= SATIETY_THRESHOLD_STARVING:
        messages.append("[color=orange]매우 배고프다.[/color]")
    elif satiety <= SATIETY_THRESHOLD_HUNGRY:
        messages.append("[color=yellow]배가 고프다.[/color]")

    # 체력 상태 메시지
    if health <= 0:
        messages.append("[color=red]쓰러질 것 같다...[/color]")
    elif health <= HEALTH_THRESHOLD_DANGER:
        messages.append("[color=red]몸이 너무 힘들다.[/color]")

    return "\n".join(messages)


def _make_bar(current: int, maximum: int, width: int = 10) -> str:
    """
    상태바 문자열 생성

    Args:
        current: 현재 값
        maximum: 최대 값
        width: 바 너비 (기본 10)

    Returns:
        "████░░░░░░" 형식 문자열
    """
    if maximum <= 0:
        maximum = 1
    ratio = max(0, min(1, current / maximum))
    filled = int(ratio * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def get_status_bar(unit_id: int) -> str:
    """
    상태바 BBCode 반환 (UI 헤더용)

    Returns:
        "체력: [color=green]████████░░[/color] 80  포만감: [color=cyan]██████░░░░[/color] 60"
    """
    stats = get_survival_stats(unit_id)

    health = stats["health"]
    max_health = stats["max_health"]
    satiety = stats["satiety"]
    max_satiety = stats["max_satiety"]

    # 체력 색상: 낮으면 빨간색, 중간 노란색, 높으면 녹색
    if health <= 20:
        health_color = "red"
    elif health <= 50:
        health_color = "yellow"
    else:
        health_color = "lime"

    # 포만감 색상: 낮으면 빨간색, 중간 주황색, 높으면 청록색
    if satiety <= 10:
        satiety_color = "red"
    elif satiety <= 30:
        satiety_color = "orange"
    else:
        satiety_color = "cyan"

    health_bar = _make_bar(health, max_health)
    satiety_bar = _make_bar(satiety, max_satiety)

    return (
        f"체력: [color={health_color}]{health_bar}[/color] {health}  "
        f"포만감: [color={satiety_color}]{satiety_bar}[/color] {satiety}"
    )


# ========================================
# 이벤트 구독 - 시간 경과 시 자동 호출
# ========================================

def _on_time_elapsed(millis: int):
    """
    on_time_elapsed 이벤트 핸들러

    EventSystem에서 시간 경과 시 자동 호출됨
    """
    player_id = morld.get_player_id()
    if player_id is not None:
        process_time_elapsed(player_id, millis)

    # 등록된 NPC들의 포만감 처리
    for npc_id in _npc_registry:
        _process_npc_time(npc_id, millis)


# 모듈 로드 시 이벤트 구독 (1시간 간격)
subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
