# chapters/persistence.py - 캐릭터 데이터 저장/복원
#
# 챕터 전환 시 플레이어 데이터를 유지하기 위한 모듈
#
# 사용법:
#   from chapters.persistence import save_player_data, restore_player_data
#
#   # 챕터 종료 전
#   saved = save_player_data()
#
#   # 새 챕터 로드 후
#   restore_player_data(saved)

import morld


def _instantiate_item_by_unique(unique_id: str):
    """
    unique_id로 아이템을 동적 생성

    새 챕터에 해당 아이템이 등록되지 않았을 때 사용

    Returns:
        item_id 또는 None
    """
    # 아이템 클래스 모듈 import (데코레이터 실행을 위해)
    # 순서: equipment 먼저 (장비 아이템), 그 다음 food
    from assets.items import equipment, food

    # 아이템 클래스 레지스트리에서 조회
    from assets.registry import get_item_class

    item_cls = get_item_class(unique_id)
    if item_cls is None:
        print(f"[persistence] Item class not found: {unique_id}")
        return None

    # 동적으로 instantiate
    item = item_cls()
    item_id = morld.create_id()

    item.instantiate(item_id)
    print(f"[persistence] Dynamically instantiated item: {unique_id} (id={item_id})")
    return item_id


def _get_all_unit_props_flat(unit_id):
    """
    유닛의 모든 props를 flat dict로 반환
    {"타입:이름": value, ...} 형식
    """
    all_props = {}
    prop_types = morld.get_unit_prop_types(unit_id)

    for prop_type in prop_types:
        props = morld.get_unit_props_by_type(unit_id, prop_type)
        if props:
            for name, value in props.items():
                # "타입:이름" 형식으로 저장
                full_name = f"{prop_type}:{name}"
                all_props[full_name] = value

    return all_props


def save_player_data():
    """
    플레이어 데이터를 dict로 저장

    Returns:
        dict: 저장된 플레이어 데이터
        {
            "name": str,
            "props": {"타입:이름": value, ...},
            "mood": [str, ...],
            "inventory": {item_id: count, ...}
        }
    """
    player_id = morld.get_player_id()
    if player_id is None:
        print("[persistence] WARNING: No player found")
        return None

    unit_info = morld.get_unit_info(player_id)
    if not unit_info:
        print("[persistence] WARNING: Player info not found")
        return None

    # 1. 기본 정보
    data = {
        "name": unit_info.get("name", "???"),
    }

    # 2. Props (모든 속성)
    data["props"] = _get_all_unit_props_flat(player_id)

    # 3. Mood (감정 상태)
    # get_unit_info에 mood가 없으므로 별도 API 필요할 수 있음
    # 현재는 빈 리스트로 처리
    data["mood"] = []

    # 4. Inventory (소지품) - unique_id 기반으로 저장 (챕터 간 item_id 충돌 방지)
    inventory = morld.get_unit_inventory(player_id)
    inventory_by_unique = {}
    if inventory:
        for item_id, count in inventory.items():
            item_info = morld.get_item_info(int(item_id))
            if item_info and item_info.get("unique_id"):
                unique_id = item_info["unique_id"]
                inventory_by_unique[unique_id] = int(count)
            else:
                print(f"[persistence] WARNING: Item {item_id} has no unique_id, skipping")
    data["inventory"] = inventory_by_unique

    print(f"[persistence] Saved player data: name={data['name']}, "
          f"props={len(data['props'])}, inventory={list(data['inventory'].keys())}")

    return data


def restore_player_data(data):
    """
    저장된 데이터로 플레이어 정보 복원

    Args:
        data: save_player_data()로 저장된 dict

    Note:
        - 위치(location)는 복원하지 않음 (챕터별로 다르게 배치)
        - 새 챕터에서 플레이어가 이미 생성된 후 호출해야 함
    """
    if not data:
        print("[persistence] WARNING: No data to restore")
        return False

    player_id = morld.get_player_id()
    if player_id is None:
        print("[persistence] WARNING: No player found for restore")
        return False

    # 1. 이름 복원
    if "name" in data:
        morld.set_unit(player_id, "name", data["name"])
        print(f"[persistence] Restored name: {data['name']}")

    # 2. Props 복원
    if "props" in data and data["props"]:
        for prop_name, value in data["props"].items():
            morld.set_unit_prop(player_id, prop_name, value)
        print(f"[persistence] Restored {len(data['props'])} props")

    # 3. Mood 복원
    if "mood" in data and data["mood"]:
        morld.set_unit_mood(player_id, data["mood"])
        print(f"[persistence] Restored mood: {data['mood']}")

    # 4. Inventory 복원 - unique_id 기반
    if "inventory" in data and data["inventory"]:
        restored_count = 0
        for unique_id, count in data["inventory"].items():
            # unique_id로 item_id 조회
            item_id = morld.get_item_id_by_unique(unique_id)
            if item_id is not None:
                morld.give_item(player_id, item_id, int(count))
                restored_count += 1
            else:
                # 새 챕터에 해당 아이템이 없으면 동적 생성 시도
                item_id = _instantiate_item_by_unique(unique_id)
                if item_id is not None:
                    morld.give_item(player_id, item_id, int(count))
                    restored_count += 1
                else:
                    print(f"[persistence] WARNING: Could not restore item '{unique_id}'")
        print(f"[persistence] Restored {restored_count} inventory items")

    # 5. 복원 과정에서 생긴 행동 로그를 모두 읽음 처리
    morld.mark_all_logs_read()

    print("[persistence] Player data restored successfully")
    return True


# 모듈 레벨 저장소 (챕터 전환 중 데이터 유지)
_saved_player_data = None


def save_for_chapter_transition():
    """챕터 전환을 위해 플레이어 데이터 저장 (모듈 변수에 보관)"""
    global _saved_player_data
    _saved_player_data = save_player_data()
    return _saved_player_data


def restore_after_chapter_transition():
    """챕터 전환 후 저장된 플레이어 데이터 복원"""
    global _saved_player_data
    if _saved_player_data:
        result = restore_player_data(_saved_player_data)
        _saved_player_data = None  # 복원 후 초기화
        return result
    return False


def has_saved_data():
    """저장된 데이터가 있는지 확인"""
    return _saved_player_data is not None
