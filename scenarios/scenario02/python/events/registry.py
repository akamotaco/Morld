# events/registry.py - 이벤트 자동 수집 및 라우팅
#
# 이벤트 클래스 등록 및 타입별 핸들링

from .base import GameEvent, GameStartEvent, ReachEvent, MeetEvent

# 이벤트 저장소
_game_start_events = []
_reach_events = []
_meet_events = []

# 일회성 이벤트 추적
_triggered = set()


def register(event_class):
    """이벤트 클래스 등록 (데코레이터)"""
    instance = event_class()

    if isinstance(instance, GameStartEvent):
        _game_start_events.append(instance)
        _game_start_events.sort(key=lambda e: -e.priority)
    elif isinstance(instance, ReachEvent):
        _reach_events.append(instance)
        _reach_events.sort(key=lambda e: -e.priority)
    elif isinstance(instance, MeetEvent):
        _meet_events.append(instance)
        _meet_events.sort(key=lambda e: -e.priority)

    return event_class


def _get_event_id(event, prefix):
    """이벤트 고유 ID 생성"""
    return f"{prefix}:{event.__class__.__name__}"


def handle_game_start():
    """게임 시작 이벤트 처리"""
    for event in _game_start_events:
        event_id = _get_event_id(event, "game_start")

        if event.once and event_id in _triggered:
            continue

        if event.should_trigger():
            result = event.handle()
            if result:
                if event.once:
                    _triggered.add(event_id)
                return result

    return None


def handle_reach(player_id, region_id, location_id):
    """위치 도착 이벤트 처리"""
    for event in _reach_events:
        event_id = _get_event_id(event, "reach")

        if event.once and event_id in _triggered:
            continue

        if event.should_trigger(region_id=region_id, location_id=location_id):
            result = event.handle(
                player_id=player_id,
                region_id=region_id,
                location_id=location_id
            )
            if result:
                if event.once:
                    _triggered.add(event_id)
                return result

    return None


def handle_meet(player_id, unit_ids):
    """만남 이벤트 처리"""
    import morld

    # 플레이어가 수면 중이면 만남 이벤트 무시
    player_info = morld.get_unit_info(player_id)
    if player_info and player_info.get("activity") == "수면":
        return None

    for event in _meet_events:
        event_id = _get_event_id(event, "meet")

        if event.once and event_id in _triggered:
            continue

        if event.should_trigger(unit_ids=unit_ids, player_id=player_id):
            result = event.handle(player_id=player_id, unit_ids=unit_ids)
            if result:
                if event.once:
                    _triggered.add(event_id)
                return result

    return None


def reset_triggered():
    """트리거 기록 초기화 (새 게임 시 호출)"""
    _triggered.clear()
