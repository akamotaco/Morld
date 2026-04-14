# faint_timer.py — 실신 상태 추적 + 치료/방치 사망
#
# 실신 유닛 추적:
#   - 구호소 안 + 의사 영업중 → 즉시 치료 (깨어남)
#   - 구호소 안 + 의사 없음 → '수면' 취급, 자연 회복 시간 후 깨어남
#   - 구호소 밖 → 타임아웃 경과 시 handle_death(cause="neglect")
#
# 사용:
#   faint_timer.register(unit_id)   — 실신 발생 시 (party._on_faint)
#   faint_timer.unregister(unit_id) — 사망 확정/완전 부활 시

import morld
from events import subscribe_time_elapsed


# 방치 사망 타임아웃 (구호소 밖)
TIMEOUT_HOURS = 24
FAINT_TIMEOUT_MILLIS = TIMEOUT_HOURS * 3600 * 1000

# 구호소 안 + 의사 없을 때 자연 회복 시간 (수면 취급)
NATURAL_RECOVERY_HOURS = 8
NATURAL_RECOVERY_MILLIS = NATURAL_RECOVERY_HOURS * 3600 * 1000

# 체크 주기 (1시간)
CHECK_INTERVAL = 3600000

# 구호소 위치
INFIRMARY_REGION = 0
INFIRMARY_LOCATION = 5


# unit_id → {"faint_time": ms, "infirmary_since": ms | None}
_fainted = {}


def reset():
    """챕터 전환 시 리셋 + 이벤트 재구독"""
    _fainted.clear()
    subscribe_time_elapsed(_on_time_elapsed, min_interval=CHECK_INTERVAL)


def register(unit_id: int):
    """실신 유닛 등록 — 현재 게임 시간을 기록."""
    now = morld.get_game_time()
    _fainted[unit_id] = {"faint_time": now, "infirmary_since": None}
    morld.set_unit_prop(unit_id, "실신:시각", now)


def unregister(unit_id: int):
    """사망 확정/부활 시 타이머에서 제거."""
    _fainted.pop(unit_id, None)
    morld.set_unit_prop(unit_id, "실신:시각", 0)


def _is_in_infirmary(unit_id):
    loc = morld.get_unit_location(unit_id)
    return (
        loc is not None
        and isinstance(loc, (tuple, list))
        and len(loc) >= 2
        and loc[0] == INFIRMARY_REGION
        and loc[1] == INFIRMARY_LOCATION
    )


def _is_doctor_active():
    """구호소 의사가 현재 영업 중인지."""
    try:
        import village_schedule
        doctor_id = village_schedule.get_village_npc_id("구호소의사")
        if doctor_id is None:
            return False
        return bool(morld.get_unit_prop(doctor_id, "영업중"))
    except ImportError:
        return False


def _treat(unit_id, reason):
    """실신 해제 — 깨어남."""
    _fainted.pop(unit_id, None)
    morld.set_unit_prop(unit_id, "실신:시각", 0)
    morld.set_unit_prop(unit_id, "상태:실신", 0)
    print(f"[faint_timer] {unit_id} 깨어남 ({reason})")


def _on_time_elapsed(millis: int):
    """1시간마다 실신 유닛 상태 체크."""
    if not _fainted:
        return

    now = morld.get_game_time()
    doctor_active = _is_doctor_active()

    treated = []          # (uid, reason)
    expired = []          # 구호소 밖 방치 타임아웃

    for uid in list(_fainted.keys()):
        info = _fainted[uid]

        if _is_in_infirmary(uid):
            # 구호소 안 — 타임아웃 일시정지, infirmary_since 기록
            if info["infirmary_since"] is None:
                info["infirmary_since"] = now

            if doctor_active:
                # 의사 치료: 즉시 깨어남
                treated.append((uid, "doctor"))
                continue

            # 의사 없음 → 수면 취급, 자연 회복 체크
            if now - info["infirmary_since"] >= NATURAL_RECOVERY_MILLIS:
                treated.append((uid, "natural_recovery"))
                continue

            # 구호소 안 + 회복 전 → 타임아웃 카운트 정지
            info["faint_time"] = now
            morld.set_unit_prop(uid, "실신:시각", now)
            continue

        # 구호소 밖 — 체류 기록 리셋 + 타임아웃 체크
        info["infirmary_since"] = None
        if now - info["faint_time"] >= FAINT_TIMEOUT_MILLIS:
            expired.append(uid)

    # 치료 처리
    for uid, reason in treated:
        _treat(uid, reason)

    # 방치 사망 처리
    if expired:
        from engine import party_group as _pg
        for uid in expired:
            _fainted.pop(uid, None)
            morld.set_unit_prop(uid, "실신:시각", 0)
            print(f"[faint_timer] Timeout expired for {uid} → handle_death(neglect)")
            _pg.handle_death(uid, cause="neglect")


# 초기 구독
subscribe_time_elapsed(_on_time_elapsed, min_interval=CHECK_INTERVAL)
