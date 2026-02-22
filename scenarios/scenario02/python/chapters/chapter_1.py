# chapters/chapter_1.py - 정식 챕터 1
#
# 전체 맵: 저택 + 도시 + 차량 (모든 Region)
# 플레이어 + 모든 NPC
# world.initialize_world()로 전체 월드 초기화

import morld
import equipment
from world import mansion, city, initialize_world


def initialize():
    """챕터 1 초기화 (정식 맵)"""
    print("[chapter_1] Initializing main chapter...")

    # 1. 전체 월드 초기화 (모든 Region + RegionGate)
    initialize_world()

    # 2. 시간 설정 (아침으로 시작 - initialize_world의 시간 덮어쓰기)
    morld.set_time(1, 4, 2, 8, 0)  # 1년 4월 2일 아침 8시

    # 3. 플레이어 위치 설정 (현관에서 시작 - 프롤로그 종료 지점)
    _instantiate_player()

    # 4. NPC 인스턴스화 + Agent 등록
    mansion.instantiate_npcs()
    city.instantiate_npcs()  # 도심 NPC (유키, 엘라)

    # 5. 음식 아이템 등록 (자연 오브젝트보다 먼저)
    mansion.instantiate_food_items()

    # 6. 자연 오브젝트 인스턴스화 + Agent 등록
    mansion.instantiate_nature_objects()

    # 7. 잡동사니 아이템 배치
    _instantiate_collectibles()

    # 8. 소비 아이템 배치
    _instantiate_consumables()

    # 9. 전 맵 오염도 등록
    _register_pollution()

    # 10. 캐릭터 인벤토리 슬롯 초기화
    _init_inventory_slots()

    print("[chapter_1] Main chapter initialized: full map with NPCs and nature objects")


def post_restore():
    """
    챕터 전환 후 플레이어 데이터 복원 후 호출

    - 시간 정지 해제
    - UI 표시 (헤더/푸터)
    - 누더기 제거 및 일반 옷 지급
    - 챕터 1부터 생존 시스템 활성화
    - 챕터 1 시작 퀘스트 자동 부여
    """
    # 시간 정지 해제 + UI Lock 해제
    morld.set_time_frozen(False)

    import ui
    ui.set_ui_lock(False)  # 인벤토리/퀘스트/설정 메뉴 활성화

    player_id = morld.get_player_id()
    if player_id is None:
        return

    # 누더기 제거 + 일반 옷 지급
    _replace_ragged_clothes(player_id)

    # 생존 시스템 활성화
    morld.set_unit_prop(player_id, "생존:활성화", 1)
    print("[chapter_1] Survival system enabled")

    # 챕터 1 시작 퀘스트 자동 부여
    _start_chapter_quest()


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
                equipment.unequip_item(player_id, item_id)
                morld.lost_item(player_id, item_id, count)
                print(f"[chapter_1] Removed ragged clothes (id={item_id})")
                break

    # 일반 상의 지급 및 착용
    shirt = SimpleShirt()
    shirt_id = morld.create_id("item")
    shirt.instantiate(shirt_id)
    morld.give_item(player_id, shirt_id, 1)
    equipment.equip_item(player_id, shirt_id)

    # 일반 하의 지급 및 착용
    pants = SimplePants()
    pants_id = morld.create_id("item")
    pants.instantiate(pants_id)
    morld.give_item(player_id, pants_id, 1)
    equipment.equip_item(player_id, pants_id)

    print(f"[chapter_1] Player now wearing shirt (id={shirt_id}) and pants (id={pants_id})")


def _instantiate_player():
    """플레이어 인스턴스화 (주인공 방에서 시작 - 구조 후 깨어남)"""
    from assets.characters.player import Player

    player = Player()
    player_id = morld.create_id("unit")
    player.instantiate(player_id, mansion.REGION_ID, 6)  # 주인공 방에서 시작
    # 성별/체격/음경 등 플레이어 선택 속성은 persistence가 복원함


def _instantiate_collectibles():
    """잡동사니 아이템 생성 및 배치"""
    from assets.items.collectibles import (
        WildFlower, DriedFlower,
        PrettyStone, OldPendant, WoodCarving, BrokenWatch, OldTeddyBear
    )

    # (아이템 클래스, region_id, location_id)
    placements = [
        (WildFlower,    0, 12),   # 들꽃 — 앞마당
        (WildFlower,    0, 22),   # 들꽃 — 강가
        (DriedFlower,   0, 10),   # 말린 꽃 — 빈 방 1
        (PrettyStone,   0, 22),   # 예쁜 돌멩이 — 강가
        (PrettyStone,   0, 23),   # 예쁜 돌멩이 — 채집터
        (OldPendant,    0, 11),   # 낡은 펜던트 — 빈 방 2
        (WoodCarving,   0, 14),   # 나무 조각 — 2층 복도
        (BrokenWatch,   2, 2),    # 고장난 시계 — 편의점
        (OldTeddyBear,  0, 10),   # 낡은 곰 인형 — 빈 방 1
    ]

    import ground as ground_module
    count = 0
    for item_cls, region_id, location_id in placements:
        item = item_cls()
        item_id = morld.create_id("item")
        item.instantiate(item_id)
        ground_id = ground_module.ensure_ground_at(region_id, location_id, 0)
        morld.give_item(ground_id, item_id, 1)
        count += 1

    print(f"[chapter_1] {count} collectible items placed")


def _instantiate_consumables():
    """소비 아이템 (피임약, 미약, 콘돔) 생성 및 배치"""
    from assets.items.consumables import ContraceptivePill, Aphrodisiac, Condom

    # (아이템 클래스, region_id, location_id)
    placements = [
        (ContraceptivePill, 0, 4),    # 피임약 — 욕실
        (ContraceptivePill, 2, 3),    # 피임약 — 약국
        (Condom,            0, 4),    # 콘돔 — 욕실
        (Condom,            2, 2),    # 콘돔 — 편의점
        (Condom,            2, 3),    # 콘돔 — 약국
        (Aphrodisiac,       0, 5),    # 미약 — 창고
    ]

    import ground as ground_module
    count = 0
    for item_cls, region_id, location_id in placements:
        item = item_cls()
        item_id = morld.create_id("item")
        item.instantiate(item_id)
        ground_id = ground_module.ensure_ground_at(region_id, location_id, 0)
        morld.give_item(ground_id, item_id, 1)
        count += 1

    print(f"[chapter_1] {count} consumable items placed")


def _register_pollution():
    """전 맵 location에 오염도 등록"""
    import pollution

    # Region 0: 저택 (실내 + 마당 + 숲)
    for loc_id in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                   20, 21, 22, 23, 24]:
        pollution.register_location(0, loc_id, max_pollution=20, rate=1)

    # Region 2: 도시 (0-9: 입구/주유소/편의점/약국/주차장/은신처/의류점/성인용품점/세탁소/경찰서)
    for loc_id in range(10):
        pollution.register_location(2, loc_id, max_pollution=20, rate=1)

    # Region 3: 숲
    for loc_id in range(6):
        pollution.register_location(3, loc_id, max_pollution=20, rate=1)

    # Region 4: 폐광산 (0-3: 입구/1층/2층/깊은갱도)
    for loc_id in range(4):
        pollution.register_location(4, loc_id, max_pollution=20, rate=1)

    print("[chapter_1] Pollution registered for all locations")


def _init_inventory_slots():
    """플레이어 + NPC 인벤토리 슬롯 초기화"""
    import inventory as inv_module
    import think

    # 플레이어
    player_id = morld.get_player_id()
    if player_id:
        inv_module.init_character_slots(player_id, base=5, multiplier=1.0)

    # 모든 NPC 에이전트
    for agent in think._agents.values():
        inv_module.init_character_slots(agent.unit_id, base=5, multiplier=1.0)

    print("[chapter_1] Inventory slots initialized")


def _start_chapter_quest():
    """챕터 1 시작 퀘스트 자동 부여"""
    from quest import quest_manager, QuestStatus

    quest_id = "main_understand_situation"
    status = quest_manager.get_quest_status(quest_id)

    # 아직 시작하지 않은 경우에만 부여
    # LOCKED 또는 AVAILABLE 상태일 때 accept_quest로 IN_PROGRESS로 전환
    if status in (QuestStatus.LOCKED, QuestStatus.AVAILABLE):
        if quest_manager.accept_quest(quest_id):
            print(f"[chapter_1] Starting quest: {quest_id}")
        else:
            print(f"[chapter_1] Failed to start quest: {quest_id}")
