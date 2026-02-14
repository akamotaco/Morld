"""벌목 활동 핸들러"""
import morld


def handle_chop(agent, entry):
    """벌목: 도구 탐색(can:chop) → 가져오기 → 나무 이동 → 벌목 → 반납"""
    phase = agent._activity_phase

    if phase == "idle":
        # capability 기반 도구 탐색 (소유권 우선)
        tool = agent._find_tool_by_capability("can:chop")
        if not tool:
            agent._set_tool_missing_flag("can:chop")
            if agent._skip_dynamic_activity(entry):
                return  # 루프가 즉시 다음 candidate 시도
            else:
                remaining = agent._remaining_millis_in_entry(entry)
                agent._insert_idle_job("벌목", max(remaining, 1))
                agent._action_taken = True
                return

        agent._clear_tool_missing_flag("can:chop")
        agent._activity_state["tool"] = tool

        # 벌목 대상 탐색
        from think.activity_resolver import resolve_activity_location
        target = resolve_activity_location(
            agent.unit_id, "벌목", agent._get_home_region()
        )
        if not target:
            if tool["source"] == "inventory":
                # 나무 없음 + 도구 소지 → 반납
                agent._activity_phase = "returning_tool"
            else:
                # 나무 없음 + 도구 미소지 → 대기
                remaining = agent._remaining_millis_in_entry(entry)
                agent._insert_idle_job("벌목", max(remaining, 1))
                agent._action_taken = True
            return
        agent._activity_state["chop_target"] = target

        if tool["source"] == "inventory":
            agent._activity_phase = "going_to_tree"
        else:
            agent._activity_phase = "getting_tool"

    elif phase == "getting_tool":
        tool = agent._activity_state.get("tool")
        if not tool:
            agent._activity_phase = "idle"
            return

        target = tool.get("location")
        if not target:
            from .helpers import resolve_storage_container
            target = resolve_storage_container(agent, "tool")
        if not target:
            agent._activity_phase = "idle"
            agent._action_taken = True
            return

        if agent._is_at(target):
            container_id = tool.get("container_id") or target.get("object_id")
            item_id = tool["item_id"]
            if morld.has_item(container_id, item_id):
                morld.remove_item(container_id, item_id, 1)
                morld.give_item(agent.unit_id, item_id, 1)
                # 원래 위치 기억 (반납용)
                agent._memory["tool"][item_id] = {
                    "container_id": container_id,
                    "location": target,
                }
                agent._activity_phase = "going_to_tree"
                agent._action_taken = True
            else:
                # 경합으로 사라짐 → 재탐색
                agent._activity_state.pop("tool", None)
                agent._activity_phase = "idle"
                agent._action_taken = True
        else:
            agent._move_to(target, "도구 찾기")

    elif phase == "going_to_tree":
        target = agent._activity_state.get("chop_target")
        if not target:
            agent._activity_phase = "returning_tool"
            return

        if agent._is_at(target):
            # 도착 → 벌목 실행
            from assets.objects import get_instance
            obj_id = target.get("object_id")
            if obj_id:
                obj = get_instance(obj_id)
                if obj and hasattr(obj, "npc_chop"):
                    obj.npc_chop(agent.unit_id)
                    import sound
                    sound.emit_sound(agent.unit_id, "chop")
            agent._activity_phase = "returning_tool"
            agent._action_taken = True
        else:
            agent._move_to(target, "벌목")

    elif phase == "returning_tool":
        tool = agent._activity_state.get("tool")
        item_id = tool["item_id"] if tool else None
        memory = agent._memory["tool"].pop(item_id, None) if item_id else None

        if memory:
            target = memory["location"]
            container_id = memory["container_id"]
        else:
            from .helpers import resolve_storage_container
            fallback = resolve_storage_container(agent, "tool")
            if not fallback:
                agent._activity_phase = "idle"
                agent._action_taken = True
                return
            target = fallback
            container_id = fallback["object_id"]

        if agent._is_at(target):
            if item_id and container_id:
                morld.remove_item(agent.unit_id, item_id, 1)
                morld.give_item(container_id, item_id, 1)
            agent._activity_phase = "idle"
            agent._action_taken = True
        else:
            agent._move_to(target, "도구 반납")
