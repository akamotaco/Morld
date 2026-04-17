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
    # 발소리 (stance 기반: walk/crouch/run)
    try:
        import sound
        sound.emit_footstep(unit_id, location=(region_id, location_id))
    except (ImportError, Exception):
        pass

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

    # engine event_core dispatch (부수효과 콜백만 처리; generator는 on_single_event에서)
    # — 여기서는 generator를 반환할 수 없으므로, side-effect 전용 경로는 사용하지 않음.
    # 실제 dispatch는 on_single_event에서 수행.

    # 리더 이동 시 파티원 follow (임시 텔레포트)
    # 플레이어든 NPC 리더든 동일하게 동작 — party_group.is_party_leader로 일반화
    try:
        import morld
        from engine import party_group as _pg
        if _pg.is_party_leader(unit_id):
            p = _pg.get_party_of(unit_id)
            for member_id in p.get_members():
                if member_id == unit_id:
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
        uid, region, loc = event[1], event[2], event[3]
        on_reach(uid, region, loc)
        # engine event_core의 location handler dispatch (generator 지원)
        try:
            import morld
            from engine import event_core
            player_id = morld.get_player_id()
            gen = event_core.dispatch_on_reach(uid, region, loc, is_player=(uid == player_id))
            if gen is not None:
                return gen
        except Exception as e:
            print(f"[events] on_reach dispatch error: {e}")
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
