# events/__init__.py - S04 이벤트 핸들러 패키지 (경량)
#
# S02 events 패키지 기반, S04에 필요한 최소 기능만.
# 핵심: 시간 경과 이벤트 구독 시스템

# ========================================
# 시간 경과 이벤��� 구독 시스템
# ========================================

_time_elapsed_subscribers = []


def subscribe_time_elapsed(callback, min_interval=None):
    """
    시간 경과 이벤트 구��

    Args:
        callback: 콜백 함수 (millis) -> None
        min_interval: 최소 호출 간격 (밀리초). None이면 매 호출마다 실행
    """
    _time_elapsed_subscribers.append({
        "callback": callback,
        "min_interval": min_interval,
        "accumulated": 0,
    })


def _handle_time_elapsed(millis):
    """시간 경과 이벤트 처리 - 모든 구독자에게 알림"""
    for subscriber in _time_elapsed_subscribers:
        callback = subscriber["callback"]
        min_interval = subscriber["min_interval"]

        if min_interval is None:
            try:
                callback(millis)
            except Exception as e:
                print(f"[events] time_elapsed callback error: {e}")
        else:
            subscriber["accumulated"] += millis
            if subscriber["accumulated"] >= min_interval:
                elapsed = subscriber["accumulated"]
                subscriber["accumulated"] = 0
                try:
                    callback(elapsed)
                except Exception as e:
                    print(f"[events] time_elapsed callback error: {e}")


# ========================================
# 이벤트 리치/미트 (향후 확장)
# ========================================

def on_reach(unit_id, region_id, location_id):
    """유닛이 Location에 도착했을 때"""
    # 에로 함정 체크
    try:
        import erotic_trap
        erotic_trap.check_trap(region_id, location_id)
    except ImportError:
        pass


def on_leave(unit_id, region_id, location_id):
    """유닛이 Location을 떠날 때"""
    pass


def on_meet(unit_a, unit_b):
    """두 유닛이 만났을 때"""
    pass


def collect_event_handlers(event_type, player_id, unit_ids):
    """
    이벤트 타입별 핸들러 목록 반환 (C#이 큐로 관리).
    S04: 현재 비어 있음 (향후 이벤트 핸들러 추가 시 확장).
    """
    return []


def on_single_event(event):
    """
    단일 이벤트 처리 (C#에서 순차 호출).
    S02 호환 인터페이스.

    Args:
        event: ["game_start"] 또는 ["on_reach", unit_id, region_id, location_id] 등

    Returns:
        None (S04는 Generator 미사용)
    """
    event_type = event[0]

    if event_type == "game_start":
        print("[events] game_start")
        return None

    elif event_type == "on_reach":
        unit_id = event[1]
        region_id = event[2]
        location_id = event[3]
        on_reach(unit_id, region_id, location_id)
        return None

    elif event_type == "on_leave":
        unit_id = event[1]
        region_id = event[2]
        location_id = event[3]
        on_leave(unit_id, region_id, location_id)
        return None

    elif event_type == "on_meet":
        if len(event) >= 3:
            on_meet(event[1], event[2])
        return None

    elif event_type == "on_time_elapsed":
        if len(event) >= 2:
            millis = event[1]
            _handle_time_elapsed(millis)
        return None

    return None
