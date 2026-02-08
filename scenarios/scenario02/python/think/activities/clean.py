"""청소 활동 핸들러 (도구 기반)

빗자루(can:clean)를 사용하여 거처 내 오염된 방을 청소.
chop.py 패턴 기반 4-phase: idle → getting_tool → going_to_room → returning_tool
"""
import morld
from .helpers import find_polluted_room


def handle_clean(agent, entry):
    """청소: 도구 탐색 → 가져오기 → 오염 방 이동 → 청소 → 반납"""
    phase = agent._activity_phase

    if phase == "idle":
        # 1. capability 기반 도구 탐색
        tool = agent._find_tool_by_capability("can:clean")
        if not tool:
            agent._set_tool_missing_flag("can:clean")
            if agent._skip_dynamic_activity(entry):
                return
            else:
                remaining = agent._remaining_millis_in_entry(entry)
                agent._insert_idle_job("청소", max(remaining, 1))
                agent._action_taken = True
                return

        agent._clear_tool_missing_flag("can:clean")
        agent._activity_state["tool"] = tool

        # 2. 오염된 방 탐색
        room = find_polluted_room(agent)
        if not room:
            if tool["source"] == "inventory":
                # 오염 방 없음 + 도구 소지 → 반납
                agent._activity_phase = "returning_tool"
            else:
                # 오염 방 없음 + 도구 미소지 → 대기
                remaining = agent._remaining_millis_in_entry(entry)
                agent._insert_idle_job("청소", max(remaining, 1))
                agent._action_taken = True
            return

        agent._activity_state["clean_target"] = room

        if tool["source"] == "inventory":
            agent._activity_phase = "going_to_room"
        else:
            agent._activity_phase = "getting_tool"

    elif phase == "getting_tool":
        tool = agent._activity_state.get("tool")
        if not tool:
            agent._activity_phase = "idle"
            return

        target = tool.get("location") or agent.TOOL_STORAGE
        if agent._is_at(target):
            container_id = tool.get("container_id") or agent._get_toolbox_id()
            item_id = tool["item_id"]
            if morld.has_item(container_id, item_id):
                morld.remove_item(container_id, item_id, 1)
                morld.give_item(agent.unit_id, item_id, 1)
                # 원래 위치 기억 (반납용)
                agent._tool_memory[item_id] = {
                    "container_id": container_id,
                    "location": target,
                }
                agent._activity_phase = "going_to_room"
                agent._action_taken = True
            else:
                # 경합으로 사라짐 → 재탐색
                agent._activity_state.pop("tool", None)
                agent._activity_phase = "idle"
                agent._action_taken = True
        else:
            agent._move_to(target, "도구 찾기")

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
            agent._insert_idle_job("청소", 10 * 60_000)

            # 다음 오염 방 탐색
            next_room = find_polluted_room(agent)
            if next_room:
                agent._activity_state["clean_target"] = next_room
                # going_to_room 유지 → 다음 think()에서 이동
            else:
                agent._activity_phase = "returning_tool"
            agent._action_taken = True
        else:
            agent._move_to(target, "청소")

    elif phase == "returning_tool":
        tool = agent._activity_state.get("tool")
        item_id = tool["item_id"] if tool else None
        memory = agent._tool_memory.pop(item_id, None) if item_id else None

        if memory:
            target = memory["location"]
            container_id = memory["container_id"]
        else:
            target = agent.TOOL_STORAGE
            container_id = agent._get_toolbox_id()

        if agent._is_at(target):
            if item_id and container_id:
                morld.remove_item(agent.unit_id, item_id, 1)
                morld.give_item(container_id, item_id, 1)
            agent._activity_phase = "idle"
            agent._action_taken = True
        else:
            agent._move_to(target, "도구 반납")
