# semen.py - 정액 게이지 시스템
#
# P anatomy 캐릭터(남성/후타나리)의 정액 축적/소모 관리.
# 매 시간 자동 회복, 사정/자위/몽정 시 소모.
#
# DES 호환: subscribe_time_elapsed(min_interval=1h)

import morld
try:
    from events import subscribe_time_elapsed
except (ImportError, AttributeError):
    subscribe_time_elapsed = None


# ========================================
# 상수
# ========================================

PROP_SEMEN = "상태:정액"

SEMEN_MAX = 100
SEMEN_REGEN_RATE = 5          # 시간당 회복 (0→100: 20시간)
SEMEN_MIN_ERECTION = 5        # 발기 최소치 (미만 → 삽입 불가)
SEMEN_MIN_EJACULATION = 10    # 사정 최소치 (미만 → 사정 불가)
EJACULATION_COST = 20         # 사정 1회 기본 소모
WET_DREAM_COST = 30           # 몽정 시 소모
MASTURBATION_COST = 15        # 자위 사정 시 소모
WET_DREAM_AROUSAL_DROP = 20   # 몽정 시 성욕 감소

# 시간 상수
MILLIS_PER_HOUR = 3_600_000

# 등록된 캐릭터
_registry = set()
_accumulated = {}  # unit_id -> 밀리초 누적


# ========================================
# 등록/리셋
# ========================================

def register_character(unit_id):
    """P anatomy 캐릭터 등록.

    gender.has_natural_anatomy(id, 'P') 체크.
    등록 시 정액 최대치로 초기화.
    """
    try:
        import gender as gender_mod
        if not gender_mod.has_natural_anatomy(unit_id, "P"):
            return
    except ImportError:
        return

    _registry.add(unit_id)
    _accumulated[unit_id] = 0
    # 초기값: 가득 찬 상태
    current = morld.get_unit_prop(unit_id, PROP_SEMEN)
    if current is None:
        morld.set_unit_prop(unit_id, PROP_SEMEN, SEMEN_MAX)


def reset():
    """챕터 전환 리셋"""
    _registry.clear()
    _accumulated.clear()


# ========================================
# 조회 API
# ========================================

def get_semen(unit_id):
    """현재 정액 조회 (0-100). 미등록 시 SEMEN_MAX 반환."""
    if unit_id not in _registry:
        # 미등록 캐릭터는 제한 없음
        return SEMEN_MAX
    return morld.get_unit_prop(unit_id, PROP_SEMEN) or 0


def can_erect(unit_id):
    """발기 가능 여부 (정액 >= SEMEN_MIN_ERECTION)"""
    return get_semen(unit_id) >= SEMEN_MIN_ERECTION


def can_ejaculate(unit_id):
    """사정 가능 여부 (정액 >= SEMEN_MIN_EJACULATION)"""
    return get_semen(unit_id) >= SEMEN_MIN_EJACULATION


# ========================================
# 수정 API
# ========================================

def consume_semen(unit_id, amount):
    """정액 소모. 실제 소모량 반환.

    미등록 캐릭터는 소모하지 않고 amount 반환.
    """
    if unit_id not in _registry:
        return amount
    current = morld.get_unit_prop(unit_id, PROP_SEMEN) or 0
    actual = min(current, amount)
    morld.set_unit_prop(unit_id, PROP_SEMEN, max(0, current - actual))
    return actual


def add_semen(unit_id, amount):
    """정액 회복 (SEMEN_MAX 상한)"""
    if unit_id not in _registry:
        return
    current = morld.get_unit_prop(unit_id, PROP_SEMEN) or 0
    morld.set_unit_prop(unit_id, PROP_SEMEN, min(SEMEN_MAX, current + amount))


# ========================================
# 몽정
# ========================================

def process_wet_dream(unit_id):
    """몽정 처리: 정액 소모 + 성욕 감소 + 외부 정액 적용"""
    consume_semen(unit_id, WET_DREAM_COST)

    # 성욕 감소
    arousal = morld.get_unit_prop(unit_id, "상태:성욕") or 0
    if arousal > 0:
        morld.set_unit_prop(unit_id, "상태:성욕",
                            max(0, arousal - WET_DREAM_AROUSAL_DROP))

    # 외부 정액 적용 (하의 오염)
    ext_val = morld.get_unit_prop(unit_id, "오염물:정액:음부") or 0
    morld.set_unit_prop(unit_id, "오염물:정액:음부",
                        min(100, ext_val + 20))


# ========================================
# 매시간 업데이트
# ========================================

def _regen_hourly(unit_id):
    """시간당 정액 회복"""
    current = morld.get_unit_prop(unit_id, PROP_SEMEN) or 0
    if current < SEMEN_MAX:
        morld.set_unit_prop(unit_id, PROP_SEMEN,
                            min(SEMEN_MAX, current + SEMEN_REGEN_RATE))


def _process_accumulated(unit_id, millis):
    """시간 누적 후 1시간 단위로 처리"""
    _accumulated[unit_id] = _accumulated.get(unit_id, 0) + millis
    if _accumulated[unit_id] >= MILLIS_PER_HOUR:
        hours = _accumulated[unit_id] // MILLIS_PER_HOUR
        _accumulated[unit_id] %= MILLIS_PER_HOUR
        for _ in range(int(hours)):
            _regen_hourly(unit_id)


def _on_time_elapsed(millis):
    """on_time_elapsed 핸들러 (1시간 간격)"""
    import settings
    if not settings.is_romance_enabled():
        return

    # 플레이어 처리
    player_id = morld.get_player_id()
    if player_id is not None:
        # 플레이어 P anatomy 자동 등록 (lazy)
        if player_id not in _registry:
            register_character(player_id)
        if player_id in _registry:
            _process_accumulated(player_id, millis)

    # 등록된 NPC 처리
    for unit_id in _registry:
        if unit_id == player_id:
            continue
        _process_accumulated(unit_id, millis)


# 모듈 로드 시 이벤트 구독 (1시간 간격)
if subscribe_time_elapsed is not None:
    subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)
