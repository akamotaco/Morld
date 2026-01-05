# events/predict.py - 이벤트 예측 시스템
#
# 역할:
# - 시간 진행 전 이벤트 예측
# - 만남, 도착 등 시간을 중단해야 하는 이벤트 감지
# - EventPredictionSystem(C#)에서 호출
#
# 예측 함수는 미래 이벤트를 반환하고, C#에서 가장 빠른
# "interrupts_time=True" 이벤트까지만 시간을 진행합니다.

import morld


def predict_events(duration):
    """
    시간 진행 전 이벤트 예측

    Args:
        duration: 진행 예정 시간 (분)

    Returns:
        예측된 이벤트 리스트:
        [{
            "type": str,           # 이벤트 타입 (on_meet, on_reach, on_collision 등)
            "trigger_minutes": int, # 현재로부터 경과 시간 (분)
            "unit_ids": list,      # 관련 유닛 ID들
            "interrupts_time": bool, # True면 이 시점에서 시간 중단
            "data": dict           # 추가 데이터 (위치 등)
        }, ...]
    """
    events = []

    # 1. 만남 예측
    meet_events = _predict_meetings(duration)
    events.extend(meet_events)

    # 2. 도착 예측
    reach_events = _predict_arrivals(duration)
    events.extend(reach_events)

    # 3. 특수 이벤트 예측 (충돌, 조우전 등)
    # special_events = _predict_special_events(duration)
    # events.extend(special_events)

    return events


def _predict_meetings(duration):
    """
    만남 이벤트 예측

    플레이어와 NPC의 이동 경로를 분석하여
    같은 위치에 도달하는 시점을 계산합니다.
    """
    events = []
    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)

    if not player_info:
        return events

    # 플레이어 이동 경로 가져오기
    player_route = _get_movement_route(player_id, duration)
    if not player_route:
        return events

    # 모든 NPC 체크
    all_units = morld.get_all_unit_ids()
    for unit_id in all_units:
        if unit_id == player_id:
            continue

        unit_info = morld.get_unit_info(unit_id)
        if not unit_info:
            continue

        # 오브젝트는 스킵
        if unit_info.get("is_object", False):
            continue

        # NPC 이동 경로 가져오기
        npc_route = _get_movement_route(unit_id, duration)
        if not npc_route:
            continue

        # 만남 시점 계산
        meeting_time = _find_meeting_time(player_route, npc_route, duration)
        if meeting_time is not None and meeting_time < duration:
            events.append({
                "type": "on_meet",
                "trigger_minutes": meeting_time,
                "unit_ids": [player_id, unit_id],
                "interrupts_time": True,  # 만남은 시간을 중단
                "data": {
                    "npc_name": unit_info.get("name", "Unknown")
                }
            })

    return events


def _predict_arrivals(duration):
    """
    도착 이벤트 예측

    플레이어가 새 위치에 도착하는 시점을 예측합니다.
    중요한 위치 도착은 시간을 중단할 수 있습니다.
    """
    events = []
    player_id = morld.get_player_id()

    # 플레이어 이동 경로 가져오기
    player_route = _get_movement_route(player_id, duration)
    if not player_route:
        return events

    # 각 경유지 도착 시점 체크
    for waypoint in player_route:
        trigger_time = waypoint.get("arrival_time", 0)
        if trigger_time <= 0 or trigger_time >= duration:
            continue

        region_id = waypoint.get("region_id")
        location_id = waypoint.get("location_id")

        # 중요한 위치인지 체크 (이벤트 핸들러가 등록된 위치)
        if _is_important_location(region_id, location_id):
            events.append({
                "type": "on_reach",
                "trigger_minutes": trigger_time,
                "unit_ids": [player_id],
                "interrupts_time": True,  # 중요 위치 도착은 중단
                "data": {
                    "region_id": region_id,
                    "location_id": location_id
                }
            })

    return events


def _get_movement_route(unit_id, duration):
    """
    유닛의 이동 경로 계산

    Args:
        unit_id: 유닛 ID
        duration: 예측 시간 범위 (분)

    Returns:
        경유지 리스트:
        [{"region_id": int, "location_id": int, "arrival_time": int}, ...]
    """
    unit_info = morld.get_unit_info(unit_id)
    if not unit_info:
        return None

    # 현재 위치
    current_location = morld.get_unit_location(unit_id)
    if not current_location:
        return None

    region_id, location_id = current_location

    # 이동 중이 아니면 현재 위치만 반환
    edge_progress = unit_info.get("edge_progress")
    if not edge_progress:
        return [{
            "region_id": region_id,
            "location_id": location_id,
            "arrival_time": 0
        }]

    # 이동 경로 구성
    route = []

    # 현재 이동 중인 엣지의 도착 예정 시간
    remaining = edge_progress.get("remaining_time", 0)
    dest_region = edge_progress.get("dest_region_id", region_id)
    dest_location = edge_progress.get("dest_location_id", location_id)

    if remaining > 0 and remaining <= duration:
        route.append({
            "region_id": dest_region,
            "location_id": dest_location,
            "arrival_time": remaining
        })

    # JobList에서 추가 경로 예측 (선택적)
    # job_list = unit_info.get("job_list", [])
    # ... 추가 경로 계산 ...

    return route if route else None


def _find_meeting_time(player_route, npc_route, duration):
    """
    두 경로가 만나는 시점 계산

    간단한 구현: 도착 시점에서 위치가 같은지 체크
    고급 구현: 연속 시간대에서 위치 겹침 계산

    Returns:
        만남 시간 (분) 또는 None
    """
    # 간단한 구현: 각 경유지에서 위치 비교
    for player_wp in player_route:
        p_region = player_wp.get("region_id")
        p_location = player_wp.get("location_id")
        p_time = player_wp.get("arrival_time", 0)

        for npc_wp in npc_route:
            n_region = npc_wp.get("region_id")
            n_location = npc_wp.get("location_id")
            n_time = npc_wp.get("arrival_time", 0)

            # 같은 위치, 비슷한 시간대
            if p_region == n_region and p_location == n_location:
                # 도착 시간 차이가 작으면 만남으로 판정
                time_diff = abs(p_time - n_time)
                if time_diff <= 5:  # 5분 이내면 만남
                    return min(p_time, n_time)

    return None


def _is_important_location(region_id, location_id):
    """
    이벤트가 등록된 중요 위치인지 체크

    ReachEvent가 등록된 위치는 중요 위치로 간주합니다.
    """
    from events import registry

    # 등록된 ReachEvent 체크
    reach_events = registry.get_reach_events()
    for event in reach_events:
        event_region = getattr(event, 'region_id', None)
        event_location = getattr(event, 'location_id', None)

        # region_id가 None이면 모든 region과 매치
        if event_region is not None and event_region != region_id:
            continue

        # location_id가 None이면 모든 location과 매치
        if event_location is not None and event_location != location_id:
            continue

        return True

    return False


# 테스트/디버그용
def debug_predict(duration=60):
    """디버그용 예측 실행"""
    events = predict_events(duration)
    print(f"[predict] Predicted {len(events)} events for {duration} minutes:")
    for evt in events:
        print(f"  - {evt['type']} at +{evt['trigger_minutes']}min, interrupts={evt['interrupts_time']}")
    return events
