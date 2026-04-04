# survival.py - S04 생존 시스템 (경량)
#
# S02 survival.py 기반, S04에 필요한 최소 기능만.
# 향후 공통 모듈로 추출 가능.
#
# 기능:
# - 포만감 감소 (1시간당)
# - 체력 증감 (포만감 연동)
# - 기절 (HP 0)
# - 피로 (향후)

import morld
from events import subscribe_time_elapsed

# === 상수 ===
SATIETY_DECAY_RATE = 1        # 1시간당 포만감 감소량
HEALTH_REGEN_RATE = 1         # 포만감 50+ 시 1시간당 체력 회복
HEALTH_DECAY_RATE = 2         # 포만감 0 시 1시간당 체력 감소

FAINT_DURATION_HOURS = 8      # 기절 지속시간

# 시간 누적
_accumulated_millis = 0

# 등록된 캐릭터
_characters = set()


def reset():
    """챕터 전환 시 리셋"""
    global _accumulated_millis
    _accumulated_millis = 0
    _characters.clear()


def register_character(unit_id: int):
    """생존 시스템에 캐릭터 등록"""
    _characters.add(unit_id)

    # 기본 prop 초기화 (없으면)
    if morld.get_unit_prop(unit_id, "생존:포만감") is None:
        morld.set_unit_prop(unit_id, "생존:포만감", 80)
    if morld.get_unit_prop(unit_id, "생존:체력") is None:
        morld.set_unit_prop(unit_id, "생존:체력", 100)
    if morld.get_unit_prop(unit_id, "생존:최대체력") is None:
        morld.set_unit_prop(unit_id, "생존:최대체력", 100)


def _on_time_elapsed(millis: int):
    """시간 경과 콜백 (1시간 단위 처리)"""
    global _accumulated_millis
    _accumulated_millis += millis

    hours = _accumulated_millis // 3600000
    if hours < 1:
        return
    _accumulated_millis %= 3600000

    for unit_id in list(_characters):
        for _ in range(hours):
            _update_character(unit_id)


def _update_character(unit_id: int):
    """캐릭터 1시간 업데이트"""
    satiety = morld.get_unit_prop(unit_id, "생존:포만감") or 0
    health = morld.get_unit_prop(unit_id, "생존:체력") or 0
    max_health = morld.get_unit_prop(unit_id, "생존:최대체력") or 100

    # 기절 중이면 스킵
    if morld.get_unit_prop(unit_id, "상태:기절"):
        return

    # 포만감 감소
    satiety = max(0, satiety - SATIETY_DECAY_RATE)
    morld.set_unit_prop(unit_id, "생존:포만감", satiety)

    # 체력 증감
    if satiety > 50:
        health = min(max_health, health + HEALTH_REGEN_RATE)
    elif satiety == 0:
        health = max(0, health - HEALTH_DECAY_RATE)

    morld.set_unit_prop(unit_id, "생존:체력", health)

    # 기절 판정
    if health <= 0:
        _trigger_faint(unit_id)


def _trigger_faint(unit_id: int):
    """기절 처리"""
    morld.set_unit_prop(unit_id, "상태:기절", 1)
    morld.set_unit_prop(unit_id, "상태:기절:남은시간", FAINT_DURATION_HOURS)
    print(f"[survival] Unit {unit_id} fainted!")


def get_health(unit_id: int) -> int:
    return morld.get_unit_prop(unit_id, "생존:체력") or 0


def get_satiety(unit_id: int) -> int:
    return morld.get_unit_prop(unit_id, "생존:포만감") or 0


def set_health(unit_id: int, value: int):
    max_hp = morld.get_unit_prop(unit_id, "생존:최대체력") or 100
    morld.set_unit_prop(unit_id, "생존:체력", max(0, min(max_hp, value)))


def set_satiety(unit_id: int, value: int):
    morld.set_unit_prop(unit_id, "생존:포만감", max(0, min(100, value)))


# 이벤트 구독
subscribe_time_elapsed(_on_time_elapsed, min_interval=3600000)
