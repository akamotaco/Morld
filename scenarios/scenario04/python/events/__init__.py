# events/__init__.py - S04 이벤트 핸들러 패키지
#
# engine/event_core.py 기반. subscribe_time_elapsed를 re-export.

# engine event_core re-export (하위 호환)
from engine.event_core import subscribe_time_elapsed


def _handle_time_elapsed(millis):
    """시간 경과 이벤트 처리 — engine/event_core로 위임"""
    from engine.event_core import dispatch_time_elapsed
    dispatch_time_elapsed(millis)


# ========================================
# 이벤트 리치/미트
# ========================================

def on_reach(unit_id, region_id, location_id):
    """유닛이 Location에 도착했을 때"""
    try:
        import congestion
        congestion.on_unit_reach(unit_id, region_id, location_id)
    except Exception:
        pass

    # 던전 방 진입 → 적 존재 여부 등록 (플레이어만)
    # 실제 전투는 플레이어가 접근 선택 시 발동 (X 거리 기반)
    try:
        import morld
        player_id = morld.get_player_id()
        if unit_id == player_id:
            import dungeon
            dungeon.on_room_enter_prepare(region_id, location_id)
    except Exception as e:
        print(f"[events] on_reach dungeon error: {e}")

    # 플레이어가 테스트 리니어 던전 Location(R0/L12)에 도착 → 자동 입장
    try:
        import morld
        player_id = morld.get_player_id()
        if unit_id == player_id and region_id == 0 and location_id == 12:
            import linear_dungeon as ld
            if ld.try_auto_enter():
                node = ld.get_current_node()
                print(f"[events] Auto-entered linear dungeon — first node={node['type']}")
    except Exception as e:
        print(f"[events] on_reach linear_dungeon error: {e}")

    # 플레이어 이동 시 파티원 follow (임시 텔레포트)
    try:
        import morld
        player_id = morld.get_player_id()
        if unit_id == player_id:
            import party
            for member_id in party.get_members():
                if member_id == player_id:
                    continue
                morld.set_unit_location(member_id, region_id, location_id, x=0)
    except Exception as e:
        print(f"[events] on_reach party-follow error: {e}")


def on_leave(unit_id, region_id, location_id):
    """유닛이 Location을 떠날 때"""
    try:
        import congestion
        congestion.on_unit_leave(unit_id, region_id, location_id)
    except Exception:
        pass



def on_meet(unit_a, unit_b):
    """두 유닛이 만났을 때"""
    pass


def collect_event_handlers(event_type, player_id, unit_ids):
    """이벤트 핸들러 목록 (S04: 현재 비어 있음)"""
    return []


def on_single_event(event):
    """단일 이벤트 처리 (C#에서 순차 호출)"""
    event_type = event[0]

    if event_type == "game_start":
        print("[events] game_start")
        return None

    elif event_type == "on_reach":
        on_reach(event[1], event[2], event[3])
        # 플레이어가 리니어 던전 location(L12)에 도착 → 자동 진행 generator 반환
        try:
            import morld
            player_id = morld.get_player_id()
            uid, region, loc = event[1], event[2], event[3]
            if uid == player_id and region == 0 and loc == 12:
                import linear_dungeon as ld
                if ld.is_active():
                    return ld.auto_run()
        except Exception as e:
            print(f"[events] on_reach auto_run error: {e}")
        return None

    elif event_type == "on_leave":
        on_leave(event[1], event[2], event[3])
        return None

    elif event_type == "on_meet":
        if len(event) >= 3:
            on_meet(event[1], event[2])
        return None

    elif event_type == "on_time_elapsed":
        if len(event) >= 2:
            _handle_time_elapsed(event[1])
        return None

    return None
