# survival.py - 생존 시스템 (체력, 포만감)
#
# 시간 경과 시 호출되어 포만감 감소, 체력 증감 처리
# on_time_elapsed 이벤트 구독 방식으로 동작

import morld
from events import subscribe_time_elapsed


# === 상수 ===
SATIETY_DECAY_RATE = 1        # 1시간당 포만감 감소량
HEALTH_REGEN_RATE = 1         # 포만감 50 이상일 때 1시간당 체력 회복
HEALTH_DECAY_RATE = 2         # 포만감 0일 때 1시간당 체력 감소

SATIETY_THRESHOLD_HUNGRY = 30     # 배고픔 경고
SATIETY_THRESHOLD_STARVING = 10   # 굶주림 경고
HEALTH_THRESHOLD_DANGER = 20      # 위험 체력

# 시간 누적 (60분 미만의 시간 경과 누적)
_accumulated_minutes = 0


def is_enabled(unit_id: int) -> bool:
    """
    생존 시스템 활성화 여부 확인

    '생존:활성화' prop이 1 이상이면 활성화.
    챕터 0에서는 이 prop을 설정하지 않아 비활성화 상태.
    챕터 1에서 '생존:활성화': 1로 설정하면 활성화.
    """
    enabled = morld.get_unit_prop(unit_id, "생존:활성화")
    return enabled is not None and enabled >= 1


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


def add_health(unit_id: int, amount: int):
    """
    체력 추가/감소

    Args:
        unit_id: 유닛 ID
        amount: 변화량 (양수: 회복, 음수: 감소)
    """
    current = morld.get_unit_prop(unit_id, "생존:체력") or 0
    set_health(unit_id, current + amount)


def process_time_elapsed(unit_id: int, minutes: int):
    """
    시간 경과에 따른 생존 스탯 처리

    on_time_elapsed 이벤트에서 호출됨
    60분 미만의 시간은 누적하여 처리

    Args:
        unit_id: 유닛 ID
        minutes: 경과 시간 (분)
    """
    global _accumulated_minutes

    if minutes <= 0:
        return

    # 생존 시스템 비활성화 시 무시
    if not is_enabled(unit_id):
        return

    # 생존 스탯이 없는 유닛은 무시
    stats = get_survival_stats(unit_id)
    if stats["max_satiety"] == 0:
        return

    # 시간 누적 후 60분 단위로 처리
    _accumulated_minutes += minutes

    # 60분 이상 누적되면 처리
    if _accumulated_minutes < 60:
        return

    # 처리할 시간 (시간 단위)
    hours_to_process = _accumulated_minutes // 60
    _accumulated_minutes = _accumulated_minutes % 60

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


def get_status_message(unit_id: int) -> str:
    """
    현재 상태 메시지 반환 (UI 표시용)

    Returns:
        상태 이상 메시지 (BBCode 포함) 또는 빈 문자열
    """
    # 생존 시스템 비활성화 시 빈 문자열
    if not is_enabled(unit_id):
        return ""

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
    # 생존 시스템 비활성화 시 빈 문자열
    if not is_enabled(unit_id):
        return ""

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

def _on_time_elapsed(minutes: int):
    """
    on_time_elapsed 이벤트 핸들러

    EventSystem에서 시간 경과 시 자동 호출됨
    """
    player_id = morld.get_player_id()
    if player_id is not None:
        process_time_elapsed(player_id, minutes)


# 모듈 로드 시 이벤트 구독
subscribe_time_elapsed(_on_time_elapsed)
