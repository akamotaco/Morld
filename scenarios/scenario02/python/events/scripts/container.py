# events/scripts/container.py - 컨테이너(오브젝트) 아이템 가져오기/넣기 스크립트

import morld


@morld.register_script
def take_item(context_unit_id, item_id):
    """오브젝트에서 특정 아이템 하나 가져오기 (개별 아이템 메뉴용)"""
    player_id = morld.get_player_id()
    item_id = int(item_id)
    morld.lost_item(context_unit_id, item_id)
    morld.give_item(player_id, item_id)


@morld.register_script
def take_from_object(context_unit_id):
    """오브젝트에서 아이템 가져오기 (다이얼로그 방식)"""
    player_id = morld.get_player_id()
    inventory = morld.get_unit_inventory(context_unit_id)

    if not inventory:
        yield morld.dialog("가져올 아이템이 없다.")
        return

    # 아이템 목록 다이얼로그 생성
    unit_info = morld.get_unit_info(context_unit_id)
    unit_name = unit_info.get("name", "???") if unit_info else "???"

    lines = [f"[b]{unit_name}[/b]에서 가져오기\n"]

    for item_id, count in inventory.items():
        item = morld.get_item_info(item_id)
        if item:
            item_name = item.get("name", f"아이템#{item_id}")
            count_text = f" x{count}" if count > 1 else ""
            lines.append(f"[url=@ret:{item_id}]{item_name}{count_text}[/url]")

    lines.append("\n[url=@ret:cancel]취소[/url]")

    result = yield morld.dialog("\n".join(lines))

    if result and result != "cancel":
        item_id = int(result)
        morld.lost_item(context_unit_id, item_id)
        morld.give_item(player_id, item_id)
        # 로그는 InventorySystem이 자동 생성


@morld.register_script
def put_to_object(context_unit_id):
    """오브젝트에 아이템 넣기 (다이얼로그 방식)"""
    player_id = morld.get_player_id()
    inventory = morld.get_unit_inventory(player_id)

    if not inventory:
        yield morld.dialog("넣을 아이템이 없다.")
        return

    # 아이템 목록 다이얼로그 생성
    unit_info = morld.get_unit_info(context_unit_id)
    unit_name = unit_info.get("name", "???") if unit_info else "???"

    lines = [f"[b]{unit_name}[/b]에 넣기\n"]

    for item_id, count in inventory.items():
        item = morld.get_item_info(item_id)
        if item:
            item_name = item.get("name", f"아이템#{item_id}")
            count_text = f" x{count}" if count > 1 else ""
            lines.append(f"[url=@ret:{item_id}]{item_name}{count_text}[/url]")

    lines.append("\n[url=@ret:cancel]취소[/url]")

    result = yield morld.dialog("\n".join(lines))

    if result and result != "cancel":
        item_id = int(result)
        morld.lost_item(player_id, item_id)
        morld.give_item(context_unit_id, item_id)
