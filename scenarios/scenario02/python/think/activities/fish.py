"""낚시 활동 핸들러"""
import morld


def handle_fish(agent, entry):
    """낚시: 도구 탐색(can:fish) → 가져오기 → 낚시터 이동 → 낚시 → 저장 → 반납"""
    phase = agent._activity_phase

    if phase == "idle":
        # 충분성 체크
        if not agent._check_storage_need("food_ingredient", "food_fish", 3):
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("낚시", max(remaining, 1))
            agent._action_taken = True
            return

        # capability 기반 도구 탐색 (소유권 우선)
        tool = agent._find_tool_by_capability("can:fish")
        if not tool:
            agent._set_tool_missing_flag("can:fish")
            if agent._skip_dynamic_activity(entry):
                return  # 루프가 즉시 다음 candidate 시도
            else:
                remaining = agent._remaining_millis_in_entry(entry)
                agent._insert_idle_job("낚시", max(remaining, 1))
                agent._action_taken = True
                return

        agent._clear_tool_missing_flag("can:fish")
        agent._activity_state["tool"] = tool

        if tool["source"] == "inventory":
            agent._activity_phase = "going_to_spot"
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
                agent._activity_phase = "going_to_spot"
                agent._action_taken = True
            else:
                # 경합으로 사라짐 → 재탐색
                agent._activity_state.pop("tool", None)
                agent._activity_phase = "idle"
                agent._action_taken = True
        else:
            agent._move_to(target, "도구 찾기")

    elif phase == "going_to_spot":
        target = agent._activity_state.get("fish_target")
        if not target:
            from think.activity_resolver import resolve_activity_location
            target = resolve_activity_location(
                agent.unit_id, "낚시", agent._get_home_region()
            )
            if not target:
                agent._activity_phase = "returning_tool"
                return
            agent._activity_state["fish_target"] = target

        if agent._is_at(target):
            # 도착 → 낚시
            from assets.objects import get_instance
            obj_id = target.get("object_id")
            if obj_id:
                obj = get_instance(obj_id)
                if obj and hasattr(obj, "npc_fish"):
                    obj.npc_fish(agent.unit_id)
                    import sound
                    sound.emit_sound(agent.unit_id, "splash")
            agent._activity_phase = "storing_catch"
            agent._action_taken = True
        else:
            agent._move_to(target, "낚시")

    elif phase == "storing_catch":
        # 잡은 물고기를 보관소에 저장
        target = agent._activity_state.get("storage_target")
        if not target:
            from .helpers import resolve_storage_container
            target = resolve_storage_container(agent, "food_ingredient")
            if not target:
                target = resolve_storage_container(agent, "food")
            if not target:
                agent._activity_phase = "returning_tool"
                agent._action_taken = True
                return
            agent._activity_state["storage_target"] = target

        if agent._is_at(target):
            from .helpers import store_npc_items
            store_npc_items(agent, categories=["food", "food_ingredient", "drink_ingredient"])
            agent._activity_phase = "returning_tool"
            agent._action_taken = True
        else:
            agent._move_to(target, "물고기 저장")

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
