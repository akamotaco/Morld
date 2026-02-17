"""소등/점등 활동 핸들러

적극적 조명 관리: NPC가 거처 내 방을 순회하며 조명을 켜거나 끔.
3-phase 시간 패턴: 아침 소등(06:00~) → 저녁 점등(18:00~) → 밤 소등(21:00~)
열원(heat:output)은 토글 대상에서 제외.
"""
import morld


def handle_lights_off(agent, entry):
    """소등: 조명 켜진 실내 방을 순회하며 끄기 (열원 제외)"""
    phase = agent._activity_phase

    if phase == "idle":
        room = agent._find_lit_indoor_room(agent._get_home_region())
        if room:
            agent._activity_state["target_room"] = room
            agent._activity_phase = "going"
        else:
            # 소등 완료 (더 이상 켜진 방 없음) → 대기
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("소등", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            agent._action_taken = True

    elif phase == "going":
        target = agent._activity_state.get("target_room")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 도착 → 조명 끄기
            from assets.objects import get_instance
            for obj_id in target.get("light_ids", []):
                if morld.get_unit_prop(obj_id, "light:on") == 1:
                    obj = get_instance(obj_id)
                    if obj and hasattr(obj, "npc_toggle_switch"):
                        obj.npc_toggle_switch(agent.unit_id, target_state=0)
            # 다음 방 탐색으로 복귀
            agent._activity_phase = "idle"
            agent._do_instant_action("소등", "toggle_light")
        else:
            agent._move_to(target, "소등")


def handle_lights_on(agent, entry):
    """점등: 조명 꺼진 실내 방을 순회하며 켜기 (열원 제외)"""
    phase = agent._activity_phase

    if phase == "idle":
        room = agent._find_unlit_indoor_room(agent._get_home_region())
        if room:
            agent._activity_state["target_room"] = room
            agent._activity_phase = "going"
        else:
            # 점등 완료 (더 이상 꺼진 방 없음) → 대기
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("점등", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            agent._action_taken = True

    elif phase == "going":
        target = agent._activity_state.get("target_room")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            # 도착 → 조명 켜기
            from assets.objects import get_instance
            for obj_id in target.get("light_ids", []):
                if morld.get_unit_prop(obj_id, "light:on") != 1:
                    obj = get_instance(obj_id)
                    if obj and hasattr(obj, "npc_toggle_switch"):
                        obj.npc_toggle_switch(agent.unit_id, target_state=1)
            # 다음 방 탐색으로 복귀
            agent._activity_phase = "idle"
            agent._do_instant_action("점등", "toggle_light")
        else:
            agent._move_to(target, "점등")
