# event_core.py - 시간 경과 + 위치 도착 이벤트 구독 시스템
#
# Pi-World Engine의 이벤트 기반 업데이트 인프라.
#
# 시간 이벤트:
#   엔진/모듈: subscribe_time_elapsed(cb, min_interval=...)
#   시나리오 events: dispatch_time_elapsed(millis)
#
# 위치 이벤트 (on_reach):
#   시나리오/모듈: subscribe_on_reach(region, loc, cb, player_only=True)
#   시나리오 events: dispatch_on_reach(unit_id, region, loc) → generator or None
#
# 콜백이 generator를 반환하면 UI dialog chain으로 처리됨.

_time_elapsed_subscribers = []
_on_reach_subscribers = []  # [{region, loc, callback, player_only}]


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


def subscribe_on_reach(region, loc, callback, *, player_only=True):
    """특정 Location 도착 이벤트 구독.

    Args:
        region: Region id
        loc: Location id
        callback: (unit_id, region, loc) -> None | generator
                  generator 반환 시 UI dialog chain으로 처리됨.
        player_only: True면 플레이어 도착에만 발동. False면 모든 유닛.

    Example:
        def on_player_reach_shop(uid, region, loc):
            yield ui.dialog("상점에 들어왔다.")
        subscribe_on_reach(0, 3, on_player_reach_shop)
    """
    _on_reach_subscribers.append({
        "region": region,
        "loc": loc,
        "callback": callback,
        "player_only": player_only,
    })


def dispatch_on_reach(unit_id, region, loc, *, is_player=False):
    """위치 도착 이벤트 배포 — 매칭되는 구독자 중 첫 generator 반환.

    Args:
        unit_id: 도착한 유닛
        region / loc: 도착 위치
        is_player: 해당 유닛이 플레이어인지 (player_only 필터용)

    Returns:
        Generator (callback이 yield할 경우) 또는 None.
        여러 subscriber가 매칭되어도 **첫 번째 generator**만 반환 (뒤는 fire-and-forget).
    """
    first_generator = None
    for sub in _on_reach_subscribers:
        if sub["region"] != region or sub["loc"] != loc:
            continue
        if sub["player_only"] and not is_player:
            continue
        try:
            result = sub["callback"](unit_id, region, loc)
        except Exception as e:
            print(f"[event_core] on_reach callback error at ({region},{loc}): {e}")
            continue
        if result is None:
            continue
        if first_generator is None:
            first_generator = result
        # generator가 여러 개면 경고 (로직 오류 가능성)
        else:
            print(f"[event_core] WARNING: multiple generators at ({region},{loc}), using first")
    return first_generator


def reset():
    """챕터 전환 시 구독자 초기화"""
    _time_elapsed_subscribers.clear()
    _on_reach_subscribers.clear()
