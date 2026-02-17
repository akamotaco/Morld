# assets/locations/city.py - 황폐화된 도시 지역
#
# Location ID (Region 2 내부 ID)
# - 0: 도시 입구 (city_entrance)
# - 1: 주유소 (gas_station)
# - 2: 편의점 (convenience_store)
# - 3: 약국 (pharmacy)
# - 4: 주차장 (parking_lot)
# - 5: 은신처 (hideout) - 유키/엘라가 머무는 곳
# - 6: 의류점 (clothing_store) - 황폐화된 옷가게

import morld
from assets.base import Location
from assets.objects.grounds import GroundAsphalt, GroundConcrete


class CityEntrance(Location):
    """도시 입구 - 황폐한 도시로 가는 길목"""
    unique_id = "city_entrance"
    name = "도시 입구"
    is_indoor = False
    stay_duration = 5
    # Pi-World: 도시 허브, 여러 방향으로 분기
    geometry = 1  # line
    length = 600

    describe_text = {
        "default": "황폐화된 도시의 입구. 무너진 표지판이 서 있다.",
        "아침": "안개 사이로 버려진 건물들의 윤곽이 보인다.",
        "낮": "텅 빈 거리에 바람만 분다.",
        "저녁": "석양빛이 폐허를 붉게 물들인다.",
        "밤": "가로등 없는 거리가 칠흑같이 어둡다.",
        "날씨:비": "빗물이 금 간 도로 위로 흘러내린다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundAsphalt())

        # 버스 정류장 벤치
        from assets.objects.outdoor import StreetBench
        bench = StreetBench()
        bench.name = "버스 정류장 벤치"
        bench.focus_text = {"default": "버스 정류장에 남은 낡은 벤치. 버스는 더 이상 오지 않는다."}
        self.add_object(bench, x=200)

        # 도시 입구 가로수 (버려진 도시에 남은 나무)
        from assets.objects.trees import Tree
        from think.resource_agent import register_tree_object
        street_tree = Tree()
        street_tree.name = "가로수"
        street_tree.unique_id = "urban_tree"
        street_tree.max_logs = 1
        street_tree.max_branches = 4
        street_tree.initial_logs = 0
        street_tree.initial_branches = 3
        street_tree.focus_text = {"default": "도시 입구에 남은 가로수. 관리되지 않아 가지가 무성하다."}
        tree_id = self.add_object(street_tree, x=450)
        register_tree_object(tree_id, "urban_tree")


class GasStation(Location):
    """주유소 - 버려진 주유소"""
    unique_id = "gas_station"
    name = "주유소"
    is_indoor = False
    stay_duration = 3
    # Pi-World
    geometry = 1  # line
    length = 300

    describe_text = {
        "default": "버려진 주유소. 녹슨 주유기가 서 있다.",
        "낮": "햇살 아래 녹슨 철판이 반짝인다.",
        "밤": "어둠 속에서 주유소 지붕의 실루엣이 보인다.",
        "날씨:비": "빗물이 녹슨 주유기를 타고 흘러내린다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundAsphalt())

        # 가판대 (비충전 자원: 생수, 에너지음료)
        from assets.objects.scavenge import GasStationStand
        self.add_object(GasStationStand(), x=100)

        # 수도꼭지 (물 받기)
        from assets.objects.furniture import WaterTap
        tap = WaterTap()
        tap.focus_text = {"default": "주유소 뒤편의 녹슨 수도꼭지. 틀면 아직 물이 나온다."}
        self.add_object(tap, x=200)

        # 주유소 앞 벤치
        from assets.objects.outdoor import StreetBench
        bench = StreetBench()
        bench.name = "낡은 벤치"
        bench.focus_text = {"default": "주유소 처마 아래 놓인 낡은 벤치. 녹이 슬었지만 앉을 수 있다."}
        self.add_object(bench, x=150)


class ConvenienceStore(Location):
    """편의점 - 문 열린 편의점 (실내)"""
    unique_id = "convenience_store"
    name = "편의점"
    is_indoor = True
    stay_duration = 0
    # Pi-World
    geometry = 1  # line
    length = 180

    describe_text = {
        "default": "문이 열려 있는 편의점. 선반이 대부분 비어 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundConcrete())

        # 조명 (깨진 유리문으로 빛이 들어옴)
        from assets.objects.furniture import Window
        self.add_object(Window(), x=5)

        # 선반 추가 (카운터 뒤 선반 역할)
        from assets.objects.furniture import Shelf
        shelf = Shelf()
        shelf_id = self.add_object(shelf)

        # 도시 지도를 선반에 넣기 (도시 지역 전용)
        from assets.items.equipment import CityMap
        city_map = CityMap()
        city_map_id = morld.create_id("item")

        city_map.instantiate(city_map_id)
        morld.give_item(shelf_id, city_map_id, 1)

        # 냉장고들 추가 (편의점에는 냉장고가 많다)
        from assets.objects.furniture import Refrigerator
        from assets.items.food import (
            CannedCola, CannedCoffee, EnergyDrink,
            WaterBottle, SportsDrink, GreenTea
        )

        # 냉장고 1 - 탄산/커피
        fridge1 = Refrigerator()
        fridge1.name = "냉장고 (탄산/커피)"
        fridge1_id = self.add_object(fridge1)
        # 콜라 3개
        for _ in range(3):
            item = CannedCola(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(fridge1_id, item_id, 1)
        # 캔 커피 3개
        for _ in range(3):
            item = CannedCoffee(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(fridge1_id, item_id, 1)
        # 에너지 드링크 2개
        for _ in range(2):
            item = EnergyDrink(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(fridge1_id, item_id, 1)

        # 냉장고 2 - 생수/차
        fridge2 = Refrigerator()
        fridge2.name = "냉장고 (생수/차)"
        fridge2_id = self.add_object(fridge2)
        # 생수 4개
        for _ in range(4):
            item = WaterBottle(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(fridge2_id, item_id, 1)
        # 녹차 2개
        for _ in range(2):
            item = GreenTea(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(fridge2_id, item_id, 1)

        # 냉장고 3 - 스포츠 음료
        fridge3 = Refrigerator()
        fridge3.name = "냉장고 (스포츠 음료)"
        fridge3_id = self.add_object(fridge3)
        # 스포츠 음료 3개
        for _ in range(3):
            item = SportsDrink(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(fridge3_id, item_id, 1)
        # 에너지 드링크 1개
        item = EnergyDrink(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(fridge3_id, item_id, 1)

        # 수도꼭지 (편의점 뒤편)
        from assets.objects.furniture import WaterTap
        tap = WaterTap()
        tap.focus_text = {"default": "편의점 뒤편의 수도꼭지. 녹슬었지만 물은 나온다."}
        self.add_object(tap, x=170)


class Pharmacy(Location):
    """약국 - 약품 있을 수 있음 (실내)"""
    unique_id = "pharmacy"
    name = "약국"
    is_indoor = True
    stay_duration = 0
    # Pi-World
    geometry = 1  # line
    length = 180

    describe_text = {
        "default": "버려진 약국. 약품이 남아 있을지도 모른다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundConcrete())

        from assets.objects.furniture import Window
        self.add_object(Window(), x=90)

        # 약품 진열대 (비충전 자원: 약초)
        from assets.objects.scavenge import PharmacyShelf
        self.add_object(PharmacyShelf(), x=50)


class ParkingLot(Location):
    """주차장 - 차량 발견 장소"""
    unique_id = "parking_lot"
    name = "주차장"
    is_indoor = False
    stay_duration = 3
    # Pi-World
    geometry = 1  # line
    length = 360

    describe_text = {
        "default": "황량한 주차장. 버려진 차들이 몇 대 보인다.",
        "낮": "햇살 아래 녹슨 차량들이 줄지어 있다.",
        "밤": "어둠 속에 차량들의 검은 윤곽만 보인다.",
        "날씨:비": "빗물이 아스팔트 위에 고이고 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundAsphalt())

        # 부서진 자판기 (비충전 자원: 캔커피, 콜라)
        from assets.objects.scavenge import BrokenVendingMachine
        self.add_object(BrokenVendingMachine(), x=100)

        # 야생 식물 (충전 자원 - 도시 폐허에 자생)
        from assets.objects.nature import WildBerryBush, WildHerbPatch
        from think.resource_agent import register_resource_object

        wild_berry = WildBerryBush()
        berry_id = self.add_object(wild_berry, x=220)
        register_resource_object(berry_id, "wild_berry_bush")
        wild_berry.spawn_resource()  # 초기 자원 1개

        wild_herb = WildHerbPatch()
        herb_id = self.add_object(wild_herb, x=250)
        register_resource_object(herb_id, "wild_herb_patch")
        wild_herb.spawn_resource()  # 초기 자원 1개

        # 주차장 옆 벤치
        from assets.objects.outdoor import StreetBench
        bench = StreetBench()
        bench.name = "공원 벤치"
        bench.focus_text = {"default": "주차장 옆에 남은 공원 벤치. 페인트가 벗겨져 있다."}
        self.add_object(bench, x=180)

        # 도시 나무 (아스팔트 틈을 뚫고 자란 야생 나무)
        from assets.objects.trees import Tree
        from think.resource_agent import register_tree_object
        urban_tree = Tree()
        urban_tree.name = "야생 나무"
        urban_tree.unique_id = "urban_tree"
        urban_tree.max_logs = 1
        urban_tree.max_branches = 4
        urban_tree.initial_logs = 0
        urban_tree.initial_branches = 3
        urban_tree.focus_text = {"default": "아스팔트 틈을 뚫고 자란 야생 나무. 잎이 무성하다."}
        tree_id = self.add_object(urban_tree, x=300)
        register_tree_object(tree_id, "urban_tree")


class Hideout(Location):
    """은신처 - 도심 생존자들의 거처 (유키/엘라)"""
    unique_id = "hideout"
    name = "은신처"
    is_indoor = True
    stay_duration = 0
    # Pi-World
    geometry = 1  # line
    length = 180

    describe_text = {
        "default": "건물 지하에 마련된 은신처. 좁지만 안전해 보인다.",
        "밤": "희미한 촛불이 은신처를 비춘다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundConcrete())

        # 조명 (희미한 촛불)
        from assets.objects.furniture import OilLamp
        self.add_object(OilLamp(), x=90)

        # 낡은 소파 (은신처 거처용)
        from assets.objects.furniture import OldSofa
        sofa = OldSofa()
        sofa.name = "낡은 소파"
        sofa.focus_text = {"default": "어디서 주워온 듯한 낡은 소파. 스프링이 튀어나올 것 같지만 앉을 수 있다."}
        self.add_object(sofa, x=90)

        # 유키의 침낭 (유키/엘라 공용 - 소유는 유키)
        from assets.objects.furniture import SleepingBag
        sleeping_bag = SleepingBag()
        sleeping_bag.name = "유키의 침낭"
        sleeping_bag.bed_owner = ["yuki", "ella"]
        sleeping_bag.focus_text = {"default": "바닥에 펼쳐진 넓은 침낭. 두 사람이 겨우 들어갈 수 있는 크기다."}
        self.add_object(sleeping_bag, x=50)

        # 식량 보관함 (엘라/유키 식량 저장)
        from assets.objects.furniture import FoodStorage
        food_storage = FoodStorage()
        food_storage_id = self.add_object(food_storage, x=120)

        # 초기 식량: 생수 2개
        from assets.items.food import WaterBottle
        for _ in range(2):
            item = WaterBottle()
            item_id = morld.create_id("item")
            item.instantiate(item_id)
            morld.give_item(food_storage_id, item_id, 1)

        # 간이 화로 (간단한 조리 가능)
        from assets.objects.furniture import PortableStove
        self.add_object(PortableStove(), x=130)

        # 도구함 (정원 도구 보관)
        from assets.locations.storage import Toolbox
        toolbox_id = self.add_object(Toolbox(), x=125)

        # 간이 물병 → 도구함에 보관
        from assets.items.garden_items import SimpleWaterBottle
        water_bottle = SimpleWaterBottle()
        water_bottle_id = morld.create_id("item")
        water_bottle.instantiate(water_bottle_id)
        morld.give_item(toolbox_id, water_bottle_id, 1)

        # 간이 드럼통 욕조
        from assets.objects.furniture import DrumBath
        drum_bath = DrumBath()
        self.add_object(drum_bath, x=150)

        # 간이 텃밭 (이랑 2개)
        from assets.objects.garden import GardenBed
        self.add_object(GardenBed(furrow_count=2), x=160)

        # 디버그: 무한 씨앗 포대
        from assets.locations.storage import InfiniteSeedBag
        self.add_object(InfiniteSeedBag(), x=165)

        # 간이 화장실
        from assets.locations.toilet import PortableToilet
        self.add_object(PortableToilet(), x=170)


class ClothingStore(Location):
    """의류점 - 황폐화된 옷가게 (실내)"""
    unique_id = "clothing_store"
    name = "의류점"
    is_indoor = True
    stay_duration = 0
    # Pi-World
    geometry = 1  # line
    length = 240

    describe_text = {
        "default": "버려진 의류점. 진열대가 넘어져 있고 옷가지들이 여기저기 흩어져 있다.",
        "낮": "깨진 유리창으로 햇빛이 들어와 먼지가 보인다.",
        "밤": "어두운 매장 안. 마네킹들의 실루엣이 으스스하다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundConcrete())

        # 조명 (깨진 유리창으로 빛이 들어옴)
        from assets.objects.furniture import Window
        self.add_object(Window(), x=120)

        # 옷걸이 (옷장 역할)
        from assets.objects.furniture import Wardrobe
        wardrobe = Wardrobe()
        wardrobe.name = "옷걸이"
        wardrobe.wardrobe_owner = ["yuki", "ella"]
        wardrobe_id = self.add_object(wardrobe)

        from assets.items.clothes import (
            # 남성/유니섹스
            MensTShirt, MensJeans, MensHoodie, MensLeatherJacket,
            MensSneakers, MensCap, TornJeans, DirtyShirt,
            # 여성
            CropTop, MiniSkirt, HotPants, BlackStockings, HighHeels,
            # 황폐한 의류
            WornOutJacket, FadedDress, MilitaryBoots, TacticalVest, CamouflagePants,
            # 기타
            Sunglasses, DenimJacket, TrackSuit,
            # 방한/방수
            WarmCoat, MensBomberJacket, MensBeanie, WarmBoots,
            HoodedCloak, RainCoat,
        )
        from assets.items.equipment import Umbrella

        # 남성/유니섹스 의류
        item = MensTShirt(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MensJeans(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MensHoodie(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MensLeatherJacket(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MensSneakers(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MensCap(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = DenimJacket(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = TrackSuit(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        # 여성 의류
        item = CropTop(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MiniSkirt(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = HotPants(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = BlackStockings(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = HighHeels(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        # 황폐/서바이벌 의류
        item = TornJeans(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = DirtyShirt(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = WornOutJacket(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = FadedDress(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MilitaryBoots(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = TacticalVest(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = CamouflagePants(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        # 악세서리
        item = Sunglasses(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        # 방한/방수 의류
        item = WarmCoat(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MensBomberJacket(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = MensBeanie(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = WarmBoots(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = HoodedCloak(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = RainCoat(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
        item = Umbrella(); item_id = morld.create_id("item"); item.instantiate(item_id); morld.give_item(wardrobe_id, item_id, 1)
