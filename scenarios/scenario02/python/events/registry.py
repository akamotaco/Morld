# events/registry.py - 이벤트 자동 수집 및 라우팅
#
# 이벤트 클래스 등록 및 타입별 핸들링

from .base import GameEvent, GameStartEvent, ReachEvent, MeetEvent, DialogEvent, ContactEvent, ContactDialogEvent, NpcMeetEvent
from types import GeneratorType

# 이벤트 저장소
_game_start_events = []
_reach_events = []
_meet_events = []
_contact_events = []  # 2D 충돌 접촉 이벤트
_npc_meet_events = []  # NPC 간 만남 이벤트

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
    elif isinstance(instance, NpcMeetEvent):
        # NpcMeetEvent는 MeetEvent보다 먼저 체크 (더 구체적)
        _npc_meet_events.append(instance)
        _npc_meet_events.sort(key=lambda e: -e.priority)
    elif isinstance(instance, ContactEvent):
        _contact_events.append(instance)
        _contact_events.sort(key=lambda e: -e.priority)
    elif isinstance(instance, MeetEvent):
        # DialogEvent도 MeetEvent의 하위 클래스
        _meet_events.append(instance)
        _meet_events.sort(key=lambda e: -e.priority)

    return event_class


def _get_event_id(event, prefix):
    """이벤트 고유 ID 생성"""
    return f"{prefix}:{event.__class__.__name__}"


def _is_generator(obj):
    """Generator 여부 확인"""
    return isinstance(obj, GeneratorType)


def handle_game_start():
    """게임 시작 이벤트 처리 - Generator 반환"""
    for event in _game_start_events:
        event_id = _get_event_id(event, "game_start")

        if event.once and event_id in _triggered:
            continue

        if event.should_trigger():
            result = event.handle()
            # Generator도 결과로 간주 (truthy)
            if result is not None:
                if event.once:
                    _triggered.add(event_id)
                return result

    return None


def handle_reach(player_id, region_id, location_id):
    """위치 도착 이벤트 처리 - Generator 반환"""
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
            # Generator도 결과로 간주 (truthy)
            if result is not None:
                if event.once:
                    _triggered.add(event_id)
                return result

    return None


def handle_meet(player_id, unit_ids):
    """만남 이벤트 처리 - Generator 반환"""
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
            # Generator도 결과로 간주 (truthy)
            if result is not None:
                if event.once:
                    _triggered.add(event_id)
                return result

    return None


def handle_contact(player_id, unit_ids):
    """접촉 이벤트 처리 (2D 충돌 반경) - Generator 반환"""
    import morld

    # 플레이어가 수면 중이면 접촉 이벤트 무시
    player_info = morld.get_unit_info(player_id)
    if player_info and player_info.get("activity") == "수면":
        return None

    for event in _contact_events:
        event_id = _get_event_id(event, "contact")

        if event.once and event_id in _triggered:
            continue

        if event.should_trigger(unit_ids=unit_ids, player_id=player_id):
            result = event.handle(player_id=player_id, unit_ids=unit_ids)
            if result is not None:
                if event.once:
                    _triggered.add(event_id)
                return result

    return None


def handle_npc_meet(unit_ids):
    """NPC 간 만남 이벤트 처리 (플레이어 미포함)

    Args:
        unit_ids: 만난 유닛 ID 목록 (플레이어 미포함)

    Returns:
        처리 결과 또는 None
    """
    for event in _npc_meet_events:
        event_id = _get_event_id(event, "npc_meet")

        if event.once and event_id in _triggered:
            continue

        if event.should_trigger(unit_ids=unit_ids, player_id=None):
            result = event.handle(unit_ids=unit_ids)
            if result:
                if event.once:
                    _triggered.add(event_id)
                # NPC 간 이벤트는 시간 경과 없음 (is_dialog_event=False)
                # 결과가 있어도 다이얼로그 표시 안 함
                print(f"[NpcMeetEvent] {event.__class__.__name__} handled: {result}")
            return result

    return None


def reset_triggered():
    """트리거 기록 초기화 (새 게임 시 호출)"""
    _triggered.clear()


def get_reach_events():
    """등록된 ReachEvent 목록 반환 (EventPredictionSystem용)"""
    return _reach_events


def get_meet_events():
    """등록된 MeetEvent 목록 반환 (EventPredictionSystem용)"""
    return _meet_events


def get_contact_events():
    """등록된 ContactEvent 목록 반환"""
    return _contact_events


def get_npc_meet_events():
    """등록된 NpcMeetEvent 목록 반환"""
    return _npc_meet_events


# ========================================
# C# 통합 이벤트 큐용 API
# ========================================

def get_event_by_id(event_type, event_id):
    """
    event_id로 이벤트 인스턴스 조회

    Args:
        event_type: "meet" | "contact" | "npc_meet"
        event_id: "meet:ClassName" 형식의 이벤트 ID

    Returns:
        이벤트 인스턴스 또는 None
    """
    if event_type == "meet":
        events = _meet_events
        prefix = "meet"
    elif event_type == "contact":
        events = _contact_events
        prefix = "contact"
    elif event_type == "npc_meet":
        events = _npc_meet_events
        prefix = "npc_meet"
    else:
        return None

    for event in events:
        if _get_event_id(event, prefix) == event_id:
            return event
    return None


def mark_event_triggered(event_id):
    """
    이벤트를 트리거됨으로 표시 (C#에서 호출)

    Args:
        event_id: "meet:ClassName" 형식의 이벤트 ID
    """
    _triggered.add(event_id)


def is_event_triggered(event_id):
    """
    이벤트가 이미 트리거됐는지 확인

    Args:
        event_id: 이벤트 ID

    Returns:
        bool: 트리거됨 여부
    """
    return event_id in _triggered
