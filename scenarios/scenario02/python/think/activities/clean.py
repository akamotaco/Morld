"""청소 활동 핸들러 (도구 기반)

빗자루(can:clean)를 사용하여 거처 내 오염된 방을 청소.
Phase flow: idle → getting_tool → going_to_room → returning_tool
"""
import morld
from .helpers import find_polluted_room
from .tool_activity import phase_getting_tool, phase_returning_tool


def handle_clean(agent, entry):
    """청소: 도구 탐색 → 가져오기 → 오염 방 이동 → 청소 → 반납"""
    phase = agent._activity_phase

    if phase == "idle":
        # 1. capability 기반 도구 탐색
        tool = agent._find_tool_by_capability("can:clean")
        if not tool:
            agent._set_tool_missing_flag("can:clean")
            agent._skip_dynamic_activity(entry)  # dynamic이면 다음 candidate
            return  # non-dynamic이면 "할 일 없음" 폴백

        agent._clear_tool_missing_flag("can:clean")
        agent._activity_state["tool"] = tool

        # 2. 오염된 방 탐색
        room = find_polluted_room(agent)
        if not room:
            if tool["source"] == "inventory":
                agent._activity_phase = "returning_tool"
            return

        agent._activity_state["clean_target"] = room

        if tool["source"] == "inventory":
            agent._activity_phase = "going_to_room"
        else:
            agent._activity_phase = "getting_tool"

    elif phase == "getting_tool":
        phase_getting_tool(agent, next_phase="going_to_room")

    elif phase == "going_to_room":
        target = agent._activity_state.get("clean_target")
        if not target:
            agent._activity_phase = "returning_tool"
            return

        if agent._is_at(target):
            # 도착 → 청소 실행
            import pollution

            tool = agent._activity_state.get("tool")
            item_id = tool["item_id"] if tool else None
            clean_power = morld.get_unit_prop(item_id, "청소력") or 5 if item_id else 5

            r = target["region_id"]
            l = target["location_id"]
            pollution.clean_location(r, l, clean_power)

            # cleaned set에 추가
            cleaned = agent._activity_state.get("cleaned", set())
            cleaned.add(l)
            agent._activity_state["cleaned"] = cleaned

            # 청소 시간 (10분)
            agent._insert_idle_job("청소", agent._get_action_duration("clean_room"))

            # 다음 오염 방 탐색
            next_room = find_polluted_room(agent)
            if next_room:
                agent._activity_state["clean_target"] = next_room
            else:
                agent._activity_phase = "returning_tool"
            agent._action_taken = True
        else:
            agent._move_to(target, "청소")

    elif phase == "returning_tool":
        phase_returning_tool(agent)
