# chapters/chapter_1.py - 정식 챕터 1
#
# 전체 맵: 저택 + 도시 + 차량 (모든 Region)
# 플레이어 + 모든 NPC
# world.initialize_world()로 전체 월드 초기화

import morld
import equipment
from world import mansion, city, mine, forest, initialize_world


def _register_scenario_data():
    """시나리오02 전용 데이터 등록 (씨앗/세력/아이이름)"""
    import garden
    # 기존 5종 (계절 추가)
    garden.register_seed(1, "감자",   "seed_potato",  "food_potato",  3, 2, 4, 0.30, seasons=["봄", "가을"])
    garden.register_seed(2, "토마토", "seed_tomato",  "food_tomato",  2, 3, 5, 0.25, seasons=["여름"])
    garden.register_seed(3, "당근",   "seed_carrot",  "food_carrot",  4, 2, 3, 0.20, seasons=["봄", "가을"])
    garden.register_seed(4, "약초",   "seed_herb",    "food_herb",    3, 1, 3, 0.35)  # 사계절
    garden.register_seed(5, "양배추", "seed_cabbage", "food_cabbage", 2, 1, 2, 0.40, seasons=["봄", "가을"])
    # 신규 5종
    garden.register_seed(6,  "고구마", "seed_sweet_potato", "food_sweet_potato", 2, 2, 4, 0.35, seasons=["여름", "가을"])
    garden.register_seed(7,  "옥수수", "seed_corn",         "food_corn",         2, 2, 4, 0.25, seasons=["여름"])
    garden.register_seed(8,  "마늘",   "seed_garlic",       "food_garlic",       3, 2, 5, 0.40, seasons=["봄", "가을"])
    garden.register_seed(9,  "양파",   "seed_onion",        "food_onion",        2, 2, 4, 0.35, seasons=["봄", "가을"])
    garden.register_seed(10, "호박",   "seed_pumpkin",      "food_pumpkin",      1, 1, 2, 0.30, seasons=["여름", "가을"])

    import combat

    # ── 세력 구조 ──
    # 방문자  : 플레이어
    # 숲속 저택: 밀라, 리나, 세라 (저택 주민/경비)
    #   └ 세라는 "숲속 저택" 소속이지만 개인 override로 방문자와 중립
    # 도시    : 유키, 엘라 (도시 거주자)
    # 야생 동물: 늑대, 박쥐 (야생 생물 통합)
    # 거미    : 거미 (야생 동물과 별도 — 늑대↔거미 적대)
    # 유적    : 유적 생물
    # 기생    : 기생체

    # 생물 세력 → 인간 세력 전체 적대 (전역)
    _human_factions = ("방문자", "숲속 저택", "도시")
    for _cf in ("야생 동물", "거미", "유적", "기생"):
        for _hf in _human_factions:
            combat.register_faction_relation(_cf, _hf, -1)
    combat.register_faction_relation("야생 동물", "거미", -1)  # 늑대 ↔ 거미 적대

    # 방문자(플레이어) ↔ NPC 세력 관계 (전역)
    # 세라의 방문자 중립은 sera.props의 개인 override로 처리
    combat.register_faction_relation("방문자", "숲속 저택", 1)  # 밀라/리나: 우호
    combat.register_faction_relation("방문자", "도시", 1)       # 유키/엘라: 우호

    # NPC 세력 간 관계 (전역)
    combat.register_faction_relation("숲속 저택", "도시", 1)    # 저택 ↔ 도시: 우호

    import pregnancy
    pregnancy.register_child_names(
        male_names=["카이", "레오", "유진", "하루", "소라"],
        female_names=["하나", "미유", "유리", "사쿠라", "린"],
    )


def initialize():
    """챕터 1 초기화 (정식 맵)"""
    print("[chapter_1] Initializing main chapter...")

    # 0. 시나리오 전용 데이터 등록
    _register_scenario_data()

    # 1. 전체 월드 초기화 (모든 Region + RegionGate)
    initialize_world()

    # 1.5. 생물 스폰 등록 (광산 + 숲)
    mine.register_spawn_sources()
    forest.register_spawn_sources()

    # 2. 시간 설정 (아침으로 시작 - initialize_world의 시간 덮어쓰기)
    morld.set_time(1, 4, 2, 8, 0)  # 1년 4월 2일 아침 8시

    # 3. 플레이어 위치 설정 (현관에서 시작 - 프롤로그 종료 지점)
    _instantiate_player()

    # 4. NPC 인스턴스화 + Agent 등록
    mansion.instantiate_npcs()
    city.instantiate_npcs()  # 도심 NPC (유키, 엘라)
    _instantiate_faye()      # 행상 NPC (페이)

    # 5. 음식 아이템 등록 (자연 오브젝트보다 먼저)
    mansion.instantiate_food_items()

    # 6. 자연 오브젝트 인스턴스화 + Agent 등록
    mansion.instantiate_nature_objects()

    # 7. 잡동사니 아이템 배치
    _instantiate_collectibles()

    # 8. 소비 아이템 배치
    _instantiate_consumables()

    # 9. 분대 관련 아이템 배치
    _instantiate_squad_items()

    # 10. 전 맵 오염도 등록
    _register_pollution()

    # 11. 캐릭터 인벤토리 슬롯 초기화
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

    # 시작 소지금 (처음 챕터 1 진입 시에만 100G 지급)
    if morld.get_unit_prop(player_id, "소지금") is None:
        morld.set_unit_prop(player_id, "소지금", 100)
        print("[chapter_1] Player given starting gold: 100G")

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


def _instantiate_faye():
    """페이(행상) NPC 인스턴스화 + Agent 등록 + 옷 착용"""
    from assets.characters.faye import Faye
    from assets.items.clothes import MerchantJacket, SimplePants, SimpleBra, SimplePanties
    from think import register_agent, create_agent_for

    npc = Faye()
    instance_id = morld.create_id("unit")
    npc.instantiate(instance_id, city.REGION_ID, 0)  # 도시 입구에서 시작

    agent = create_agent_for("faye", instance_id)
    if agent:
        register_agent(instance_id, agent)

    # 의상 착용
    def _equip(clothes_class):
        item = clothes_class()
        item_id = morld.create_id("item")
        item.instantiate(item_id)
        morld.give_item(instance_id, item_id, 1)
        equipment.equip_item(instance_id, item_id)

    _equip(MerchantJacket)
    _equip(SimplePants)
    _equip(SimpleBra)
    _equip(SimplePanties)

    print(f"[chapter_1] Faye instantiated (id={instance_id})")


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
    # 도시(R2) 성인용품 배치 제거 — 페이(행상) NPC가 대체 판매
    placements = [
        (ContraceptivePill, 0, 4),    # 피임약 — 욕실
        (Condom,            0, 4),    # 콘돔 — 욕실
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


def _instantiate_squad_items():
    """분대 관련 아이템 (지휘관의뱃지, 무전기) 생성 및 배치 — 2층 창고(R0,L5)"""
    from assets.items.tools import CommanderBadge, Radio

    import ground as ground_module
    ground_id = ground_module.ensure_ground_at(0, 5, 0)

    for item_cls in [CommanderBadge, Radio]:
        item = item_cls()
        item_id = morld.create_id("item")
        item.instantiate(item_id)
        morld.give_item(ground_id, item_id, 1)

    print("[chapter_1] Squad items placed at 2F storage (R0,L5)")


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
