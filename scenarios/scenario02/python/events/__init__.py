# events/__init__.py - 이벤트 핸들러 패키지
#
# 역할:
# - 게임 이벤트 처리 (game_start, on_reach, on_meet, on_contact, on_time_elapsed)
# - 스크립트 함수 자동 등록 (@morld.register_script)
# - 캐릭터별 이벤트 핸들러 위임
# - 순차적 on_meet 이벤트 큐 관리
# - on_contact: 2D 충돌 반경 내 접촉 이벤트
# - 시간 경과 이벤트 구독 시스템
# - 장비 변경 이벤트 처리

from . import registry

# ========================================
# 시간 경과 이벤트 구독 시스템
# ========================================
# NOTE: subscribe_time_elapsed는 다른 모듈에서 모듈 로드 시점에
# from events import subscribe_time_elapsed 로 사용하므로,
# 순환 import를 피하기 위해 서브모듈 import보다 먼저 정의해야 함.

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


# 이벤트 클래스 import (자동 등록)
from . import game_start
from . import reach
from . import meet

# 스크립트 함수 import (@morld.register_script 자동 등록)
from . import scripts

# 캐릭터 이벤트 핸들러 (on_meet_player 등)
from assets.characters import get_character_event_handler

# 은신 판정 시스템
import stealth


def _handle_time_elapsed(millis):
    """
    시간 경과 이벤트 처리 - 모든 구독자에게 알림

    Args:
        millis: 경과 시간 (밀리초)
    """
    for subscriber in _time_elapsed_subscribers:
        callback = subscriber["callback"]
        min_interval = subscriber["min_interval"]

        if min_interval is None:
            # 매번 호출
            try:
                callback(millis)
            except Exception as e:
                print(f"[events] time_elapsed callback error: {e}")
        else:
            # 누적 시간 기반 호출
            subscriber["accumulated"] += millis
            while subscriber["accumulated"] >= min_interval:
                subscriber["accumulated"] -= min_interval
                try:
                    callback(min_interval)
                except Exception as e:
                    print(f"[events] time_elapsed callback error: {e}")



# ========================================
# C# 통합 이벤트 큐용 API
# ========================================

def collect_event_handlers(event_type, player_id, unit_ids):
    """
    이벤트 타입별 핸들러 목록 반환 (C#이 큐로 관리)

    Args:
        event_type: "meet" | "contact" | "npc_meet"
        player_id: 플레이어 ID (npc_meet이면 None)
        unit_ids: 관련 유닛 목록

    Returns:
        list of dict: [{"source": "registry"|"character", "event_type": ...,
                        "unit_id": ..., "event_id": ..., "priority": ..., "once": ...}]
    """
    handlers = []

    if event_type == "meet":
        handlers = _collect_meet_handlers(player_id, unit_ids)
    elif event_type == "contact":
        handlers = _collect_contact_handlers(player_id, unit_ids)
    elif event_type == "npc_meet":
        handlers = _collect_npc_meet_handlers(unit_ids)

    return handlers


def _collect_meet_handlers(player_id, unit_ids):
    """on_meet 핸들러 수집"""
    handlers = []
    other_ids = [uid for uid in unit_ids if uid != player_id]

    # 1. registry에 등록된 MeetEvent 수집
    for event in registry.get_meet_events():
        event_id = f"meet:{event.__class__.__name__}"

        # 일회성 이벤트 중복 체크
        if event.once and registry.is_event_triggered(event_id):
            continue

        if event.should_trigger(unit_ids=unit_ids, player_id=player_id):
            handlers.append({
                "source": "registry",
                "event_type": "meet",
                "event_id": event_id,
                "priority": event.priority,
                "once": event.once,
            })

    # 2. 캐릭터별 on_meet_player 핸들러 수집
    for other_id in other_ids:
        # 은신 NPC는 이벤트에서 제외
        if stealth.is_unit_stealthed(other_id):
            continue
        handler = get_character_event_handler(other_id)
        if handler and hasattr(handler, "on_meet_player"):
            handlers.append({
                "source": "character",
                "event_type": "meet",
                "unit_id": other_id,
                "priority": -1,
                "once": False,
            })

    # 우선순위 내림차순 정렬 (높은 priority 먼저)
    handlers.sort(key=lambda h: -h["priority"])
    return handlers


def _collect_contact_handlers(player_id, unit_ids):
    """on_contact 핸들러 수집"""
    handlers = []
    other_ids = [uid for uid in unit_ids if uid != player_id]

    # 1. registry에 등록된 ContactEvent 수집
    for event in registry.get_contact_events():
        event_id = f"contact:{event.__class__.__name__}"

        if event.once and registry.is_event_triggered(event_id):
            continue

        if event.should_trigger(unit_ids=unit_ids, player_id=player_id):
            handlers.append({
                "source": "registry",
                "event_type": "contact",
                "event_id": event_id,
                "priority": event.priority,
                "once": event.once,
            })

    # 2. 캐릭터별 on_contact_player 핸들러 수집
    for other_id in other_ids:
        # 은신 NPC는 이벤트에서 제외
        if stealth.is_unit_stealthed(other_id):
            continue
        handler = get_character_event_handler(other_id)
        if handler and hasattr(handler, "on_contact_player"):
            handlers.append({
                "source": "character",
                "event_type": "contact",
                "unit_id": other_id,
                "priority": -1,
                "once": False,
            })

    handlers.sort(key=lambda h: -h["priority"])
    return handlers


def _collect_npc_meet_handlers(unit_ids):
    """npc_meet 핸들러 수집 (플레이어 미포함)"""
    handlers = []

    for event in registry.get_npc_meet_events():
        event_id = f"npc_meet:{event.__class__.__name__}"

        if event.once and registry.is_event_triggered(event_id):
            continue

        if event.should_trigger(unit_ids=unit_ids, player_id=None):
            handlers.append({
                "source": "registry",
                "event_type": "npc_meet",
                "event_id": event_id,
                "priority": event.priority,
                "once": event.once,
            })

    handlers.sort(key=lambda h: -h["priority"])
    return handlers


def call_event_handler(handler_info, player_id, unit_ids):
    """
    개별 핸들러 실행 (C#에서 호출)

    Args:
        handler_info: {"source": ..., "event_type": ..., "unit_id": ..., "event_id": ...}
        player_id: 플레이어 ID
        unit_ids: 만남/접촉 참여자 전체 목록

    Returns:
        Generator (Dialog) 또는 None
        특수 반환값:
        - {"stealth_skip": True, "message": "..."}: 은신 성공으로 이벤트 스킵
    """
    source = handler_info.get("source")
    event_type = handler_info.get("event_type")
    event_id = handler_info.get("event_id")
    unit_id = handler_info.get("unit_id")
    once = handler_info.get("once", False)

    result = None

    # ========================================
    # 은신 판정 (meet/contact 이벤트)
    # ========================================
    # character 소스 + meet/contact 이벤트에서 은신 판정 수행
    # registry 이벤트는 조건 기반이므로 은신 판정 미적용 (TODO: forced 속성 지원 시 추가)
    if source == "character" and event_type in ("meet", "contact"):
        if unit_id and stealth.is_player_stealthed():
            # 은신 중 → 판정
            proceed, msg = stealth.resolve_event_with_stealth(unit_id, is_forced=False)
            if not proceed:
                # 은신 성공 → 이벤트 스킵 (C#에서 처리)
                return {"stealth_skip": True, "message": msg or "들키지 않은 것 같다."}
            # 발각됨 → 이벤트 진행 (msg는 set_detected에서 처리됨)

    if source == "registry":
        event = registry.get_event_by_id(event_type, event_id)
        if event:
            if event_type == "npc_meet":
                result = event.handle(unit_ids=unit_ids)
            else:
                result = event.handle(player_id=player_id, unit_ids=unit_ids)

            # 일회성 이벤트 트리거 표시
            if result is not None and once:
                registry.mark_event_triggered(event_id)

    elif source == "character":
        handler = get_character_event_handler(unit_id)
        if handler:
            if event_type == "meet" and hasattr(handler, "on_meet_player"):
                result = handler.on_meet_player(player_id)
            elif event_type == "contact" and hasattr(handler, "on_contact_player"):
                result = handler.on_contact_player(player_id)

    return result




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

        # 발소리 (캐릭터 이동 시 소리 전파)
        try:
            import sound
            sound.emit_sound(unit_id, "footstep", location=(region_id, location_id))
        except ImportError:
            pass

        # 오염 체크 (모든 unit에 대해)
        try:
            import pollution
            pollution.on_unit_reach(unit_id, region_id, location_id)
        except ImportError:
            pass

        # 습도 체크 (실외 비/눈 맞으면 즉시 젖음)
        try:
            import humidity
            humidity.on_unit_reach(unit_id, region_id, location_id)
        except ImportError:
            pass

        # 혼잡도 업데이트
        try:
            import congestion
            congestion.on_unit_reach(unit_id, region_id, location_id)
        except ImportError:
            pass

        if unit_id == player_id:
            # 던전 Fog of War 업데이트
            try:
                from instant_dungeon.manager import get_dungeon_for_region, get_floor_for_region
                dungeon_id, dungeon_info = get_dungeon_for_region(region_id)
                if dungeon_info:
                    from instant_dungeon import fog
                    # 다층: 현재 층 데이터 추출
                    floor_info = get_floor_for_region(dungeon_id, region_id)
                    if floor_info:
                        floor_locations = floor_info.get("locations", {})
                        floor_num = floor_info.get("floor")
                        fog_id = f"{dungeon_id}_F{floor_num}" if floor_num is not None else dungeon_id
                        for rid, lid in floor_locations.items():
                            if lid == location_id:
                                fog.update_fog(fog_id, rid)
                                break
            except ImportError:
                pass

            # 은신 가능 자세면 은신 진입 시도 (새 Location 도착 시)
            stealth_state = morld.get_unit_prop(player_id, "status:stealth")
            if not stealth_state:  # 통상 상태
                import ui
                if ui.is_stealth_posture():
                    ui.check_stealth_entry()

            # NPC 은신 감지 시도 + 30분 주기 구독 등록
            try:
                import stealth as stealth_mod
                stealth_mod._ensure_initialized()
                stealth_mod.detect_stealthed_npcs(region_id, location_id)
            except ImportError:
                pass

            return registry.handle_reach(player_id, region_id, location_id)

    elif event_type == "on_leave":
        unit_id = event[1]
        region_id = event[2]
        location_id = event[3]

        # 혼잡도 업데이트
        try:
            import congestion
            congestion.on_unit_leave(unit_id, region_id, location_id)
        except ImportError:
            pass

        # NPC on_leave 처리 (조명 끄기 등)
        import think
        agent = think.get_agent(unit_id)
        if agent and hasattr(agent, 'on_leave'):
            agent.on_leave(region_id, location_id)

    elif event_type == "on_time_elapsed":
        millis = event[1]
        _handle_time_elapsed(millis)

        # 플레이어 기절 체크 — 기절 시 다이얼로그 generator 반환
        import survival
        if survival.is_player_faint_pending():
            return survival.handle_player_faint()

        return None

    elif event_type == "on_contact":
        unit_ids = event[1:]
        if player_id in unit_ids:
            # 플레이어 수면 중이면 이벤트 무시
            player_info = morld.get_unit_info(player_id)
            if player_info and player_info.get("activity") == "수면":
                return None
            return registry.handle_contact(player_id, unit_ids)
        return None

    elif event_type == "on_meet":
        # NOTE: on_meet은 C# EventSystem에서 새 경로로 처리됨
        # collect_event_handlers() → call_event_handler()
        # 이 분기는 도달하지 않음 (데드 코드)
        pass

    return None


# C#에서 호출하는 메인 진입점
__all__ = [
    # C# 통합 이벤트 큐 API
    'collect_event_handlers',
    'call_event_handler',
    # 기존 API
    'on_single_event',
    'subscribe_time_elapsed',
]
