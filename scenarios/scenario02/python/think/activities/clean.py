"""청소 활동 핸들러"""
from .helpers import find_indoor_room


def handle_clean(agent, entry):
    """청소: 거처 실내 방을 순회"""
    phase = agent._activity_phase

    if phase == "idle":
        room = find_indoor_room(agent)
        if room:
            agent._activity_state["clean_target"] = room
            agent._activity_phase = "going"
        else:
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("청소", max(remaining, 1))
            agent._action_taken = True

    elif phase == "going":
        target = agent._activity_state.get("clean_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 도착 → 청소 완료
            agent._activity_state["cleaned"] = agent._activity_state.get("cleaned", set())
            agent._activity_state["cleaned"].add(target["location_id"])
            agent._activity_phase = "idle"
            agent._action_taken = True
        else:
            agent._move_to(target, "청소")
