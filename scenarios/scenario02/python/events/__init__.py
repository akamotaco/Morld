# events/__init__.py - 이벤트 핸들러 패키지
#
# 역할:
# - 게임 이벤트 처리 (game_start, on_reach, on_meet)
# - 스크립트 함수 자동 등록 (@morld.register_script)
# - 캐릭터별 이벤트 핸들러 위임
# - 순차적 on_meet 이벤트 큐 관리

from . import registry

# 이벤트 클래스 import (자동 등록)
from . import game_start
from . import reach
from . import meet

# 스크립트 함수 import (@morld.register_script 자동 등록)
from . import scripts

# 캐릭터 이벤트 핸들러 (on_meet_player 등)
from assets.characters import get_character_event_handler


# ========================================
# on_meet 이벤트 큐 (순차 처리용)
# ========================================

# 대기 중인 meet 이벤트 목록
# 각 항목: {"type": "registry" | "character", "handler": ..., "unit_id": ...}
_pending_meet_events = []


def _collect_meet_events(player_id, unit_ids):
    """
    on_meet 이벤트 수집 - 조건에 맞는 모든 이벤트를 우선순위별로 정렬

    Args:
        player_id: 플레이어 유닛 ID
        unit_ids: 만남에 포함된 모든 유닛 ID

    Returns:
        수집된 이벤트 목록 (우선순위 순)
    """
    events = []
    other_ids = [uid for uid in unit_ids if uid != player_id]

    # 1. registry에 등록된 MeetEvent 수집
    for event in registry.get_meet_events():
        event_id = f"meet:{event.__class__.__name__}"

        # 일회성 이벤트 중복 체크
        if event.once and event_id in registry._triggered:
            continue

        if event.should_trigger(unit_ids=unit_ids, player_id=player_id):
            events.append({
                "type": "registry",
                "event": event,
                "event_id": event_id,
                "priority": event.priority,
            })

    # 2. 캐릭터별 on_meet_player 핸들러 수집
    for other_id in other_ids:
        handler = get_character_event_handler(other_id)
        if handler and hasattr(handler, "on_meet_player"):
            # 캐릭터 핸들러는 priority 0으로 취급 (registry 이벤트 후에 처리)
            events.append({
                "type": "character",
                "handler": handler,
                "unit_id": other_id,
                "priority": -1,  # registry 이벤트보다 낮은 우선순위
            })

    # 우선순위 내림차순 정렬 (높은 priority 먼저)
    events.sort(key=lambda e: -e["priority"])

    return events


def _pop_next_meet_event(player_id):
    """
    큐에서 다음 이벤트를 꺼내서 실행

    Returns:
        Generator 또는 None
    """
    global _pending_meet_events

    while _pending_meet_events:
        evt = _pending_meet_events.pop(0)

        if evt["type"] == "registry":
            event = evt["event"]
            event_id = evt["event_id"]

            # 이미 트리거됐으면 스킵
            if event.once and event_id in registry._triggered:
                continue

            result = event.handle(player_id=player_id, unit_ids=evt.get("unit_ids", []))
            if result is not None:
                if event.once:
                    registry._triggered.add(event_id)
                return result

        elif evt["type"] == "character":
            handler = evt["handler"]
            result = handler.on_meet_player(player_id)
            if result is not None:
                return result

    return None


def clear_pending_meet_events():
    """
    대기 중인 meet 이벤트 모두 제거 (ExcessTime > 0일 때 C#에서 호출)
    """
    global _pending_meet_events
    count = len(_pending_meet_events)
    _pending_meet_events = []
    if count > 0:
        print(f"[events] Cleared {count} pending meet events (ExcessTime > 0)")


def has_pending_meet_events():
    """대기 중인 meet 이벤트가 있는지 확인"""
    return len(_pending_meet_events) > 0


def on_single_event(event):
    """
    단일 이벤트 처리 (C#에서 순차 호출)

    Args:
        event: ["game_start"] 또는 ["on_reach", unit_id, region_id, location_id] 등

    Returns:
        Generator 또는 None
    """
    global _pending_meet_events
    import morld
    player_id = morld.get_player_id()

    event_type = event[0]

    if event_type == "game_start":
        return registry.handle_game_start()

    elif event_type == "on_reach":
        unit_id = event[1]
        region_id = event[2]
        location_id = event[3]

        if unit_id == player_id:
            return registry.handle_reach(player_id, region_id, location_id)

    elif event_type == "on_meet":
        unit_ids = event[1:]
        if player_id in unit_ids:
            # 플레이어 수면 중이면 이벤트 무시
            player_info = morld.get_unit_info(player_id)
            if player_info and player_info.get("activity") == "수면":
                return None

            # 이미 대기 중인 이벤트가 있으면 큐에서 다음 것 반환
            if _pending_meet_events:
                return _pop_next_meet_event(player_id)

            # 새 만남: 조건에 맞는 모든 이벤트 수집
            events = _collect_meet_events(player_id, unit_ids)

            if not events:
                return None

            # 이벤트에 unit_ids 정보 추가
            for evt in events:
                evt["unit_ids"] = unit_ids

            # 큐에 저장
            _pending_meet_events = events

            # 첫 번째 이벤트 실행
            return _pop_next_meet_event(player_id)
        else:
            # NPC 간 만남 이벤트 (플레이어 미포함)
            registry.handle_npc_meet(unit_ids)
            # NPC 간 이벤트는 다이얼로그 없음

    return None


def on_event_list(ev_list):
    """
    이벤트 리스트 처리 (C#에서 호출) - 레거시 호환용

    Note: 새 코드는 on_single_event()를 사용하여 순차 처리해야 함
    이 함수는 하위 호환을 위해 유지하며, 첫 번째 결과만 반환함

    Args:
        ev_list: [["game_start"], ["on_reach", 0, 0, 6], ["on_meet", 0, 1], ...]

    Returns:
        첫 번째 모놀로그 결과 또는 None
    """
    for event in ev_list:
        result = on_single_event(event)
        if result:
            return result

    return None


# C#에서 호출하는 메인 진입점
__all__ = [
    'on_event_list',
    'on_single_event',
    'clear_pending_meet_events',
    'has_pending_meet_events',
]
