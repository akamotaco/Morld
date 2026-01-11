# chapters/persistence.py - 캐릭터 데이터 저장/복원
#
# 챕터 전환 시 플레이어 데이터를 유지하기 위한 모듈
#
# ID 할당 전략 (스택/힙 모델):
#   - 정상 할당 (create_id): 1, 2, 3, ... (아래에서 위로)
#   - 임시 할당 (저장용): MAX-1, MAX-2, ... (위에서 아래로)
#   - 복원 시: 임시 ID → create_id()로 새 정상 ID 할당
#
# 사용법:
#   from chapters.persistence import save_player_data, restore_player_data
#
#   # 챕터 종료 전
#   saved = save_player_data()
#
#   # 새 챕터 로드 후
#   restore_player_data(saved)
#
# 향후 확장 (아이템 인스턴스 상태 저장):
#   현재는 unique_id와 count만 저장하지만, 아이템별 상태가 필요하면 확장 가능
#
#   현재 구조:
#     "inventory": {"old_knife": 1, "apple": 3}
#
#   확장 구조 (아이템 props 저장 시):
#     "inventory": [
#         {"unique_id": "old_knife", "props": {"강화": 3, "내구도": 85}},
#         {"unique_id": "old_knife", "props": {"강화": 1}},  # 다른 인스턴스
#         {"unique_id": "apple", "count": 3},  # 스택 가능 아이템
#     ]
#
#   사용 예시:
#     - 아이템 강화에 의한 스펙 변화
#     - 아이템 사용에 의한 내구도 감소
#     - 스택 불가 아이템의 개별 상태 관리
#
# ========================================
# 전체 게임 저장/로드 시스템 설계 (향후 구현)
# ========================================
#
# ### 핵심 설계: C# + Python 이원화
#
# ┌─────────────────────────────────────────────────────────────┐
# │                     게임 세이브 파일                          │
# ├─────────────────────────────────────────────────────────────┤
# │  system_save.json (C# 영역)                                 │
# │  - 지형 데이터 (Region, Location, Edge)                      │
# │  - 유닛 데이터 (캐릭터, 오브젝트) - 위치, 이름, props         │
# │  - 아이템 데이터 (아이템 정의)                                │
# │  - 인벤토리 데이터 (소유, 장착)                               │
# │  - 게임 시간 (GameTime)                                      │
# ├─────────────────────────────────────────────────────────────┤
# │  script_save.json (Python 영역)                              │
# │  - 이벤트 플래그 (first_meet 등)                             │
# │  - 퀘스트 상태                                               │
# │  - Python 전용 변수들 (글로벌 상태)                           │
# │  - resource_agent 누적 시간                                   │
# │  - 기타 스크립트 상태                                         │
# └─────────────────────────────────────────────────────────────┘
#
# ### C# 저장 영역 (시스템)
#
# 이미 있는 기능 (IDataProvider):
# - UnitSystem - UpdateFromJson, ExportToData
# - ItemSystem - UpdateFromJson, ExportToData
# - InventorySystem - SaveData, LoadData
# - WorldSystem - Terrain (Region, Edge)
#
# 저장 대상:
# | 대상       | 저장 필드                         | 비고                |
# |------------|----------------------------------|---------------------|
# | 플레이어   | name, location, props, mood      | NPC와 동일 구조     |
# | NPC        | name, location, props, mood      | 위치 포함 저장      |
# | 오브젝트   | name, location, props            | 나무 자원 개수 등   |
# | 인벤토리   | {owner_key: {item_id: count}}    | 유닛/위치/컨테이너  |
# | 장착 상태  | {unit_id: [item_id, ...]}        | InventorySystem     |
# | GameTime   | year, month, day, hour, minute   | WorldSystem         |
#
# 저장하지 않는 것:
# - JobList (스케줄 기반으로 재생성)
# - PlannedRoute (경로 탐색으로 재계산)
# - CurrentEdge (저장 시점에 이동 완료 처리)
#
# ### Python 저장 영역 (스크립트)
#
# _script_state = {
#     # 이벤트 플래그
#     "first_meet": {
#         "sera": True,   # 세라 첫 만남 완료
#         "lina": False,  # 리나 아직 안 만남
#     },
#
#     # 퀘스트 상태 (향후 확장)
#     "quests": {
#         "tutorial": "completed",
#     },
#
#     # 글로벌 변수
#     "globals": {
#         "player_name_index": 0,
#         "player_body": 1,
#     },
#
#     # resource_agent 누적 시간
#     "resource_accumulated_time": {
#         # instance_id: minutes (인벤토리 기반 자원)
#         # instance_id: {"log": min, "branch": min} (나무 자원)
#     },
# }
#
# ### 필요한 morld API (향후 구현)
#
# C# 저장/로드 API:
#   morld.save_system_state(filepath)   # JSON 파일로 저장
#   morld.load_system_state(filepath)   # JSON 파일에서 로드
#   # 또는:
#   data = morld.export_system_state()  # dict 반환
#   morld.import_system_state(data)     # dict로 복원
#
# GameTime API (추가 필요):
#   morld.get_full_game_time()  # {"year": 1, "month": 4, ...}
#   morld.set_full_game_time(year, month, day, hour, minute)
#
# NPC 조회 API (추가 필요):
#   morld.get_all_npc_ids()           # 플레이어 제외 모든 캐릭터 ID
#   morld.get_unit_id_by_unique(uid)  # unique_id → unit_id
#   morld.get_unit_unique_id(unit_id) # unit_id → unique_id
#
# ### 통합 저장/로드 워크플로우 (설계)
#
# def save_game(slot_name: str):
#     """전체 게임 저장"""
#     save_dir = f"saves/{slot_name}/"
#
#     # 1. C# 시스템 상태 저장
#     morld.save_system_state(f"{save_dir}/system_save.json")
#
#     # 2. Python 스크립트 상태 저장
#     script_state = save_script_state()
#     with open(f"{save_dir}/script_save.json", "w") as f:
#         json.dump(script_state, f)
#
#     # 3. 메타데이터 저장 (챕터, 저장 시간 등)
#     meta = {
#         "chapter": get_current_chapter(),
#         "saved_at": datetime.now().isoformat(),
#         "game_time": morld.get_full_game_time(),
#     }
#     with open(f"{save_dir}/meta.json", "w") as f:
#         json.dump(meta, f)
#
# def load_game(slot_name: str):
#     """전체 게임 로드"""
#     save_dir = f"saves/{slot_name}/"
#
#     # 1. 메타데이터 읽기
#     with open(f"{save_dir}/meta.json", "r") as f:
#         meta = json.load(f)
#
#     # 2. 월드 초기화 (챕터 기반)
#     morld.clear_world()
#     # 챕터 모듈 로드하여 지형만 초기화 (유닛 생성 X)
#
#     # 3. C# 시스템 상태 로드
#     morld.load_system_state(f"{save_dir}/system_save.json")
#
#     # 4. Python 스크립트 상태 로드
#     with open(f"{save_dir}/script_save.json", "r") as f:
#         script_state = json.load(f)
#     load_script_state(script_state)
#
# ### C# 작업 TODO (향후)
#
# [ ] GameTime 저장/로드 API (get_full_game_time, set_full_game_time)
# [ ] NPC 조회 API (get_all_npc_ids, get_unit_id_by_unique, get_unit_unique_id)
# [ ] 전체 시스템 상태 저장 API (save_system_state, load_system_state)
# [ ] UnitSystem에 위치 저장 포함 확인
#
# ### Python 작업 TODO (향후)
#
# [ ] script_state 모듈 생성 (이벤트 플래그, 퀘스트 상태 관리)
# [ ] resource_agent 누적 시간 저장/복원
# [ ] save_game() / load_game() 통합 함수
# [ ] 세이브 슬롯 UI 연동
#
# ========================================

import morld
import sys

# 임시 ID 할당용 상수 (int 최대값 - 1부터 거꾸로)
_TEMP_ID_MAX = sys.maxsize
_temp_id_counter = 0  # 다음 임시 ID 오프셋


def _reset_temp_id_counter():
    """임시 ID 카운터 리셋"""
    global _temp_id_counter
    _temp_id_counter = 0


def _next_temp_id():
    """다음 임시 ID 생성 (MAX에서 거꾸로)"""
    global _temp_id_counter
    _temp_id_counter += 1
    return _TEMP_ID_MAX - _temp_id_counter


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
            "inventory": {unique_id: count, ...},
            "equipped": [unique_id, ...]
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

    # 5. 장착 아이템 - unique_id 기반으로 저장
    equipped_items = morld.get_equipped_items(player_id)
    equipped_by_unique = []
    if equipped_items:
        for item_id in equipped_items:
            item_info = morld.get_item_info(int(item_id))
            if item_info and item_info.get("unique_id"):
                equipped_by_unique.append(item_info["unique_id"])
    data["equipped"] = equipped_by_unique

    print(f"[persistence] Saved player data: name={data['name']}, "
          f"props={len(data['props'])}, inventory={list(data['inventory'].keys())}, "
          f"equipped={data['equipped']}")

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
    # unique_id → 새 item_id 매핑 (장착 복원에 필요)
    unique_to_new_id = {}
    if "inventory" in data and data["inventory"]:
        restored_count = 0
        for unique_id, count in data["inventory"].items():
            # unique_id로 item_id 조회
            item_id = morld.get_item_id_by_unique(unique_id)
            if item_id is not None:
                morld.give_item(player_id, item_id, int(count))
                unique_to_new_id[unique_id] = item_id
                restored_count += 1
            else:
                # 새 챕터에 해당 아이템이 없으면 동적 생성 시도
                item_id = _instantiate_item_by_unique(unique_id)
                if item_id is not None:
                    morld.give_item(player_id, item_id, int(count))
                    unique_to_new_id[unique_id] = item_id
                    restored_count += 1
                else:
                    print(f"[persistence] WARNING: Could not restore item '{unique_id}'")
        print(f"[persistence] Restored {restored_count} inventory items")

    # 5. 장착 상태 복원 - unique_id 기반
    # equipment.equip_item()을 사용하여 ActionProps(put=0)도 함께 설정
    if "equipped" in data and data["equipped"]:
        from equipment import equip_item
        equipped_count = 0
        for unique_id in data["equipped"]:
            item_id = unique_to_new_id.get(unique_id)
            if item_id is not None:
                equip_item(player_id, item_id)
                equipped_count += 1
            else:
                print(f"[persistence] WARNING: Could not restore equipped item '{unique_id}'")
        print(f"[persistence] Restored {equipped_count} equipped items")

    # 6. 복원 과정에서 생긴 행동 로그를 모두 읽음 처리
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
