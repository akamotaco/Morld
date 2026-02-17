"""벌목 활동 핸들러"""
import morld


def handle_chop(agent, entry):
    """벌목: 도구 탐색(can:chop) → 가져오기 → 나무 이동 → 벌목 → 저장 → 반납"""
    phase = agent._activity_phase

    if phase == "idle":
        # 충분성 체크
        if not agent._check_storage_need("material", "log", 5):
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("벌목", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            agent._action_taken = True
            return

        # capability 기반 도구 탐색 (소유권 우선)
        tool = agent._find_tool_by_capability("can:chop")
        if not tool:
            agent._set_tool_missing_flag("can:chop")
            agent._skip_dynamic_activity(entry)  # dynamic이면 다음 candidate
            return  # non-dynamic이면 "할 일 없음" 폴백

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
                # 나무 없음 + 도구 미소지 → "할 일 없음" 폴백
                return
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
            agent._do_instant_action("대기", "abort")
            return

        if agent._is_at(target):
            container_id = tool.get("container_id") or target.get("object_id")
            item_id = tool["item_id"]
            if morld.has_item(container_id, item_id):
                morld.remove_item(container_id, item_id, 1)
                morld.give_item(agent.unit_id, item_id, 1)
                agent._activity_phase = "going_to_tree"
                agent._do_instant_action("도구 준비", "take_item")
            else:
                # 경합으로 사라짐 → 재탐색
                agent._activity_state.pop("tool", None)
                agent._activity_phase = "idle"
                agent._do_instant_action("대기", "abort")
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
            agent._activity_phase = "storing_logs"
            agent._do_instant_action("벌목", "chop")
        else:
            agent._move_to(target, "벌목")

    elif phase == "storing_logs":
        target = agent._activity_state.get("storage_target")
        if not target:
            from .helpers import resolve_storage_container
            target = resolve_storage_container(agent, "material")
            if not target:
                agent._activity_phase = "returning_tool"
                agent._do_instant_action("대기", "abort")
                return
            agent._activity_state["storage_target"] = target

        if agent._is_at(target):
            from .helpers import store_npc_items
            store_npc_items(agent, categories=["material"])
            agent._activity_phase = "returning_tool"
            agent._do_instant_action("통나무 저장", "store_item")
        else:
            agent._move_to(target, "통나무 저장")

    elif phase == "returning_tool":
        tool = agent._activity_state.get("tool")
        item_id = tool["item_id"] if tool else None

        from .helpers import resolve_storage_container
        target = resolve_storage_container(agent, "tool")
        if not target:
            agent._do_instant_action("대기", "abort")
            return
        container_id = target["object_id"]

        if agent._is_at(target):
            if item_id and container_id:
                morld.remove_item(agent.unit_id, item_id, 1)
                morld.give_item(container_id, item_id, 1)
            agent._activity_phase = "idle"
            agent._do_instant_action("도구 반납", "store_item")
        else:
            agent._move_to(target, "도구 반납")
