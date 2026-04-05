# event_core.py - 시간 경과 이벤트 구독 시스템
#
# Pi-World Engine의 시간 기반 업데이트 인프라.
# 각 엔진 모듈이 subscribe_time_elapsed()로 구독,
# 시나리오의 events 시스템이 dispatch_time_elapsed()로 배포.
#
# 사용법 (엔진 모듈):
#   from engine.event_core import subscribe_time_elapsed
#   subscribe_time_elapsed(my_callback, min_interval=3_600_000)
#
# 사용법 (시나리오 events):
#   from engine.event_core import dispatch_time_elapsed
#   dispatch_time_elapsed(millis)

_time_elapsed_subscribers = []


def subscribe_time_elapsed(callback, min_interval=None):
    """
    시간 경과 이벤트 구독

    Args:
        callback: 콜백 함수 (millis) -> None
        min_interval: 최소 호출 간격 (밀리초). None이면 매 호출마다 실행

    Example:
        # 매번 호출
        subscribe_time_elapsed(lambda ms: print(f"{ms}ms 경과"))

        # 60분(3,600,000ms)마다 호출
        subscribe_time_elapsed(my_hourly_callback, min_interval=3_600_000)
    """
    _time_elapsed_subscribers.append({
        "callback": callback,
        "min_interval": min_interval,
        "accumulated": 0,
    })


def dispatch_time_elapsed(millis):
    """
    시간 경과 이벤트 배포 — 모든 구독자에게 알림

    시나리오의 events 시스템이 on_time_elapsed 이벤트 수신 시 호출.

    Args:
        millis: 경과 시간 (밀리초)
    """
    for subscriber in _time_elapsed_subscribers:
        callback = subscriber["callback"]
        min_interval = subscriber["min_interval"]

        if min_interval is None:
            try:
                callback(millis)
            except Exception as e:
                print(f"[event_core] time_elapsed callback error: {e}")
        else:
            subscriber["accumulated"] += millis
            while subscriber["accumulated"] >= min_interval:
                subscriber["accumulated"] -= min_interval
                try:
                    callback(min_interval)
                except Exception as e:
                    print(f"[event_core] time_elapsed callback error: {e}")


def reset():
    """챕터 전환 시 구독자 초기화"""
    _time_elapsed_subscribers.clear()
