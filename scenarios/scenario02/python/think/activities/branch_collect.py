"""난방 연료 수집 활동 핸들러

나뭇가지를 나무에서 주워 모아서 material 저장소에 보관하는 활동.
연료수집(fuel.py)이 열원에 직접 장전하는 것과 달리, 보관소에 비축하는 역할.
Phase flow: idle → going_to_tree → going_to_storage
"""


def handle_branch_collect(agent, entry):
    """난방 연료 수집: 나무 탐색 → 나뭇가지 줍기 → 저장소에 보관"""
    phase = agent._activity_phase

    if phase == "idle":
        # 충분성 체크
        if (not agent._check_storage_need("material", "branch", 6) and
                not agent._check_storage_need("material", "log", 3)):
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("난방 연료 수집", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            agent._action_taken = True
            return

        from .helpers import resolve_branch_tree
        tree_target = resolve_branch_tree(agent, cross_region=False)
        if not tree_target:
            return  # 나무 없음 → 디스패치 루프가 "할 일 없음" 폴백

        agent._activity_state["tree_target"] = tree_target
        agent._activity_phase = "going_to_tree"

    elif phase == "going_to_tree":
        target = agent._activity_state.get("tree_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            from assets.objects import get_instance
            obj_id = target.get("object_id")
            if obj_id:
                obj = get_instance(obj_id)
                if obj and hasattr(obj, "npc_gather_branch"):
                    for _ in range(3):
                        if not obj.npc_gather_branch(agent.unit_id):
                            break
            agent._activity_phase = "going_to_storage"
            agent._do_instant_action("나뭇가지 줍기", "gather_branch")
        else:
            agent._move_to(target, "나뭇가지 줍기")

    elif phase == "going_to_storage":
        target = agent._activity_state.get("storage_target")
        if not target:
            from .helpers import resolve_storage_container
            target = resolve_storage_container(agent, "material")
            if not target:
                agent._do_instant_action("대기", "abort")
                return
            agent._activity_state["storage_target"] = target

        if agent._is_at(target):
            from .helpers import store_npc_items
            store_npc_items(agent, categories=["material"])
            agent._activity_phase = "idle"
            agent._do_instant_action("재료 저장", "store_item")
        else:
            agent._move_to(target, "재료 저장")
