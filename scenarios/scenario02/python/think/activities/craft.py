"""제작 활동 핸들러

NPC가 보관소에서 재료를 꺼내 제작대에서 나무조각을 만드는 활동.
CraftingTable과 IngredientStorage가 같은 location에 있으므로 이동 1회.
Phase flow: idle → going → crafting
"""


def handle_craft(agent, entry):
    """제작: 보관소(재료+제작대) 이동 → 재료 꺼내기 → 제작 → 결과 저장"""
    phase = agent._activity_phase

    if phase == "idle":
        # 충분성 체크
        if not agent._check_storage_need("material", "wood_chip", 8):
            remaining = agent._remaining_millis_in_entry(entry)
            agent._insert_idle_job("제작", max(remaining, 1))
            agent._action_taken = True
            return

        # 재료(통나무) 확인
        from .helpers import resolve_storage_container
        target = resolve_storage_container(agent, "material")
        if not target:
            return  # 보관소 없음 → 디스패치 루프가 "할 일 없음" 폴백

        from assets.objects import get_instance
        obj = get_instance(target["object_id"])
        if not obj or obj.get_item_count("log") < 1:
            # 통나무 없음 → 스킵
            agent._skip_dynamic_activity(entry)
            return

        agent._activity_state["storage_target"] = target
        agent._activity_phase = "going"

    elif phase == "going":
        target = agent._activity_state.get("storage_target")
        if not target:
            agent._activity_phase = "idle"
            return

        if agent._is_at(target):
            agent._activity_phase = "crafting"
            agent._do_instant_action("재료 준비", "take_item")
        else:
            agent._move_to(target, "제작대 이동")

    elif phase == "crafting":
        target = agent._activity_state.get("storage_target")
        if not target:
            agent._activity_phase = "idle"
            return

        from assets.objects import get_instance

        # 1. 보관소에서 통나무 꺼내기
        storage_obj = get_instance(target["object_id"])
        if storage_obj and storage_obj.get_item_count("log") >= 1:
            storage_obj.npc_take_item(agent.unit_id, "log", 1)

        # 2. 제작대에서 나무조각 제작
        crafting_table = _find_crafting_table_here(agent)
        if crafting_table and hasattr(crafting_table, "npc_craft"):
            crafting_table.npc_craft(agent.unit_id, "wood_chip")

        # 3. 결과물 저장
        from .helpers import store_npc_items
        store_npc_items(agent, categories=["material"])

        agent._activity_phase = "idle"
        agent._do_instant_action("나무조각 제작", "craft")


def _find_crafting_table_here(agent):
    """현재 위치에서 CraftingTable 찾기"""
    import morld
    from assets.objects import get_location_objects, get_instance
    from assets.objects.furniture import CraftingTable

    loc = morld.get_unit_location(agent.unit_id)
    if not loc:
        return None

    for obj_id in get_location_objects(loc[0], loc[1]):
        obj = get_instance(obj_id)
        if isinstance(obj, CraftingTable):
            return obj
    return None
