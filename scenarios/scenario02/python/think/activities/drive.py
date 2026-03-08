"""NPC 운전 활동 핸들러

스케줄에 목적지가 지정된 경우, 차량을 찾아 탑승 → 운전 → 하차.

Phase flow:
  idle → going_to_vehicle → mounting → driving → dismounting → idle

Schedule entry 형식:
  {"activity": "운전", "dest_region": int, "dest_location": int, "distance": float}
"""
import morld
import vehicle as veh


def handle_drive(agent, entry):
    phase = agent._activity_phase

    if phase == "idle":
        _phase_idle(agent, entry)
    elif phase == "going_to_vehicle":
        _phase_going_to_vehicle(agent)
    elif phase == "mounting":
        _phase_mounting(agent)
    elif phase == "driving":
        _phase_driving(agent, entry)
    elif phase == "dismounting":
        _phase_dismounting(agent)


def _phase_idle(agent, entry):
    """목적지 확인 → 차량 탐색 → going_to_vehicle 전환"""
    dest_region = entry.get("dest_region")
    dest_location = entry.get("dest_location")
    if dest_region is None or dest_location is None:
        # 목적지 없음 → 대기
        remaining = agent._remaining_millis_in_entry(entry)
        agent._insert_idle_job("운전 대기", max(remaining, 1))
        agent._action_taken = True
        return

    # 이미 목적지에 있으면 대기
    loc = morld.get_unit_location(agent.unit_id)
    if loc and loc[0] == dest_region and loc[1] == dest_location:
        remaining = agent._remaining_millis_in_entry(entry)
        agent._insert_idle_job("도착 대기", max(remaining, 1))
        agent._action_taken = True
        return

    # 차량 탐색 (같은 location)
    vehicle_id = veh.find_nearby_vehicle(agent.unit_id)
    if not vehicle_id:
        # 차량 없음 → 도보 fallback (일반 이동)
        dest = {"region_id": dest_region, "location_id": dest_location}
        agent._move_to(dest, "이동")
        agent._action_taken = True
        return

    # 차량 상태 확인
    status = morld.get_unit_prop(vehicle_id, "vehicle:status")
    if status in ("disabled", "wrecked"):
        # 고장 → 도보
        dest = {"region_id": dest_region, "location_id": dest_location}
        agent._move_to(dest, "이동")
        agent._action_taken = True
        return

    # 연료 확인
    distance = entry.get("distance", 10)
    ok, reason = veh.can_travel(vehicle_id, distance)
    if not ok:
        # 연료 부족 → 도보
        dest = {"region_id": dest_region, "location_id": dest_location}
        agent._move_to(dest, "이동")
        agent._action_taken = True
        return

    # 차량 사용 결정
    agent._activity_state["vehicle_id"] = vehicle_id
    agent._activity_state["dest_region"] = dest_region
    agent._activity_state["dest_location"] = dest_location
    agent._activity_state["distance"] = distance

    # 차량 위치로 이동 (같은 location이면 즉시 mounting)
    v_loc = morld.get_unit_location(vehicle_id)
    if loc and v_loc and loc[0] == v_loc[0] and loc[1] == v_loc[1]:
        agent._activity_phase = "mounting"
        # action_taken 미설정 → 즉시 mounting 진입
    else:
        v_target = {"region_id": v_loc[0], "location_id": v_loc[1]}
        agent._activity_state["vehicle_target"] = v_target
        agent._activity_phase = "going_to_vehicle"
        agent._move_to(v_target, "차량으로 이동")
        agent._action_taken = True


def _phase_going_to_vehicle(agent):
    """차량 위치로 이동"""
    target = agent._activity_state.get("vehicle_target")
    if not target:
        agent._activity_phase = "idle"
        return

    if agent._is_at(target):
        agent._activity_phase = "mounting"
        # action_taken 미설정 → 즉시 mounting 진입
    else:
        agent._move_to(target, "차량으로 이동")
        agent._action_taken = True


def _phase_mounting(agent):
    """차량 탑승 (운전석)"""
    vehicle_id = agent._activity_state.get("vehicle_id")
    if not vehicle_id:
        agent._activity_phase = "idle"
        return

    ok, result = veh.mount(agent.unit_id, vehicle_id, "driver")
    if ok:
        agent._activity_phase = "driving"
        agent._do_instant_action("탑승", "brief")
    else:
        # 탑승 실패 (운전석 점유 등) → idle로 복귀
        agent._activity_phase = "idle"
        agent._do_instant_action("대기", "brief")


def _phase_driving(agent, entry):
    """vehicle_move_to 실행 → 이동 시간만큼 대기 → dismounting"""
    vehicle_id = agent._activity_state.get("vehicle_id")
    dest_region = agent._activity_state.get("dest_region")
    dest_location = agent._activity_state.get("dest_location")
    distance = agent._activity_state.get("distance", 10)

    if not vehicle_id or dest_region is None:
        agent._activity_phase = "idle"
        agent._do_instant_action("대기", "brief")
        return

    result = veh.vehicle_move_to(vehicle_id, dest_region, dest_location, distance)
    if result["success"]:
        travel_ms = result.get("travel_time_ms", 5 * 60_000)
        agent._activity_phase = "dismounting"
        agent._insert_idle_job("운전 중", max(travel_ms, 1))
        agent._action_taken = True
    else:
        # 이동 실패 → 하차 후 idle
        agent._activity_phase = "dismounting"
        agent._do_instant_action("대기", "brief")


def _phase_dismounting(agent):
    """하차"""
    vehicle_id = agent._activity_state.get("vehicle_id")
    if vehicle_id:
        veh.dismount(agent.unit_id, vehicle_id)

    agent._activity_phase = "idle"
    agent._activity_state.clear()
    agent._do_instant_action("하차", "brief")
