# chapters/chapter_1.py - 정식 챕터 1
#
# 전체 맵: 저택 + 도시 + 차량 (모든 Region)
# 플레이어 + 모든 NPC
# world.initialize_world()로 전체 월드 초기화

import morld
from world import mansion, initialize_world


def initialize():
    """챕터 1 초기화 (정식 맵)"""
    print("[chapter_1] Initializing main chapter...")

    # 1. 전체 월드 초기화 (모든 Region + RegionEdge)
    initialize_world()

    # 2. 시간 설정 (아침으로 시작 - initialize_world의 시간 덮어쓰기)
    morld.set_time(1, 4, 2, 8, 0)  # 1년 4월 2일 아침 8시

    # 3. 플레이어 위치 설정 (현관에서 시작 - 프롤로그 종료 지점)
    _instantiate_player()

    # 4. NPC 인스턴스화 + Agent 등록
    mansion.instantiate_npcs()

    # 5. 음식 아이템 등록 (자연 오브젝트보다 먼저)
    mansion.instantiate_food_items()

    # 6. 자연 오브젝트 인스턴스화 + Agent 등록
    mansion.instantiate_nature_objects()

    print("[chapter_1] Main chapter initialized: full map with NPCs and nature objects")


def post_restore():
    """
    챕터 전환 후 플레이어 데이터 복원 후 호출

    - 누더기 제거 및 일반 옷 지급
    - 챕터 1부터 생존 시스템 활성화
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return

    # 누더기 제거 + 일반 옷 지급
    _replace_ragged_clothes(player_id)

    # 생존 시스템 활성화
    morld.set_unit_prop(player_id, "생존:활성화", 1)
    print("[chapter_1] Survival system enabled")


def _replace_ragged_clothes(player_id):
    """누더기를 벗기고 일반 옷으로 교체"""
    from assets.items.clothes import SimpleShirt, SimplePants

    # 플레이어 인벤토리에서 누더기 찾아서 제거
    inventory = morld.get_unit_inventory(player_id)
    if inventory:
        for item_id, count in list(inventory.items()):
            item_info = morld.get_item_info(item_id)
            if item_info and item_info.get("unique_id") == "ragged_clothes":
                # 장착 해제 후 제거
                morld.unequip_item_internal(player_id, item_id)
                morld.lost_item(player_id, item_id, count)
                print(f"[chapter_1] Removed ragged clothes (id={item_id})")
                break

    # 일반 상의 지급 및 착용
    shirt = SimpleShirt()
    shirt_id = morld.create_id("item")
    shirt.instantiate(shirt_id)
    morld.give_item(player_id, shirt_id, 1)
    morld.equip_item_internal(player_id, shirt_id)

    # 일반 하의 지급 및 착용
    pants = SimplePants()
    pants_id = morld.create_id("item")
    pants.instantiate(pants_id)
    morld.give_item(player_id, pants_id, 1)
    morld.equip_item_internal(player_id, pants_id)

    print(f"[chapter_1] Player now wearing shirt (id={shirt_id}) and pants (id={pants_id})")


def _instantiate_player():
    """플레이어 인스턴스화 (주인공 방에서 시작 - 구조 후 깨어남)"""
    from assets.characters.player import Player

    player = Player()
    player_id = morld.create_id("unit")
    player.instantiate(player_id, mansion.REGION_ID, 6)  # 주인공 방에서 시작
