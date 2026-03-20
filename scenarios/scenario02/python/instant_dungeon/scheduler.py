# scheduler.py — 인스턴트 던전 시간 기반 스케줄러
"""
매시간 subscribe_time_elapsed 콜백으로 던전 생성/삭제 관리.
09:00 생성, 22:00 이후 삭제 (내부에 캐릭터 없을 때만).

사용법:
    import instant_dungeon.scheduler  # 모듈 로드 시 자동 구독
"""

import morld
from . import manager

# ========================================
# 스케줄 설정
# ========================================

# 던전 활성 시간대
DUNGEON_OPEN_HOUR = 9    # 09:00에 생성
DUNGEON_CLOSE_HOUR = 22  # 22:00 이후 삭제 시도

# 테스트 던전 설정
TEST_DUNGEON_CONFIG = {
    "name": "숲속 동굴",
    "width": 400,
    "height": 400,
    "min_size": 60,
    "max_depth": 4,
    "floors": 3,  # 3층 던전
    # 입구: 뒷마당 (R0:L13)
    "entrance_gate": {
        "region_id": 0,
        "location_id": 13,
        "distance": 60,  # 1분 도보
    },
}

# 상태 추적
_scheduled_dungeon_id = None  # 현재 활성 스케줄 던전
_last_checked_day = -1        # 마지막 체크 날짜 (중복 생성 방지)
_pending_destroy = False      # 삭제 대기 상태


# ========================================
# 시간 콜백
# ========================================

def _on_time_elapsed(elapsed_millis):
    """매시간 호출 — 던전 생성/삭제 관리"""
    global _scheduled_dungeon_id, _last_checked_day, _pending_destroy

    time_info = morld.get_time_info()
    if not time_info:
        print("[dungeon_scheduler] WARNING: get_time_info() returned None")
        return

    current_hour = time_info.get("hour", 0)
    current_day = time_info.get("day", 0)
    print(f"[dungeon_scheduler] tick: day={current_day} hour={current_hour} dungeon={_scheduled_dungeon_id} last_day={_last_checked_day}")

    # ── 생성: 09:00 + 오늘 아직 안 만들었으면 ──
    if (current_hour >= DUNGEON_OPEN_HOUR
            and current_hour < DUNGEON_CLOSE_HOUR
            and current_day != _last_checked_day
            and _scheduled_dungeon_id is None):

        # 시드: 날짜 기반 (같은 날 같은 던전)
        seed = current_day * 1000 + 42

        try:
            did = manager.create_dungeon(
                name=TEST_DUNGEON_CONFIG["name"],
                width=TEST_DUNGEON_CONFIG["width"],
                height=TEST_DUNGEON_CONFIG["height"],
                min_size=TEST_DUNGEON_CONFIG["min_size"],
                max_depth=TEST_DUNGEON_CONFIG["max_depth"],
                seed=seed,
                entrance_gate=TEST_DUNGEON_CONFIG["entrance_gate"],
                floors=TEST_DUNGEON_CONFIG.get("floors", 1),
            )
            _scheduled_dungeon_id = did
            _last_checked_day = current_day
            _pending_destroy = False
            morld.add_action_log("[던전] 숲 근처에 동굴 입구가 발견되었다.")
            print(f"[dungeon_scheduler] Created dungeon: {did}")
        except Exception as e:
            print(f"[dungeon_scheduler] ERROR creating dungeon: {type(e).__name__}: {e}")
            import traceback
            try:
                traceback.print_exc()
            except Exception:
                pass

    # ── 삭제: 22:00 이후 + 던전 존재 + 내부에 아무도 없으면 ──
    if (current_hour >= DUNGEON_CLOSE_HOUR
            and _scheduled_dungeon_id is not None):

        if manager.is_dungeon_occupied(_scheduled_dungeon_id):
            if not _pending_destroy:
                _pending_destroy = True
                morld.add_action_log("[던전] 동굴이 불안정해지고 있다...")
            # 내부에 캐릭터 있음 → 다음 시간에 다시 체크
            return

        manager.destroy_dungeon(_scheduled_dungeon_id)
        _scheduled_dungeon_id = None
        _pending_destroy = False
        morld.add_action_log("[던전] 동굴 입구가 사라졌다.")


def get_active_dungeon_id():
    """현재 활성 스케줄 던전 ID (없으면 None)"""
    return _scheduled_dungeon_id


def reset():
    """챕터 전환 시 리셋"""
    global _scheduled_dungeon_id, _last_checked_day, _pending_destroy
    if _scheduled_dungeon_id:
        manager.destroy_dungeon(_scheduled_dungeon_id)
    _scheduled_dungeon_id = None
    _last_checked_day = -1
    _pending_destroy = False


# ── 시간 구독 등록 (모듈 로드 시) ──
try:
    from events import subscribe_time_elapsed
    subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)  # 1시간
    print("[dungeon_scheduler] Registered time_elapsed subscriber (1h interval)")
except ImportError:
    print("[dungeon_scheduler] WARNING: events module not available (test env?)")
except Exception as e:
    print(f"[dungeon_scheduler] ERROR registering subscriber: {e}")
