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


class GasStation(Location):
    """주유소 - 버려진 주유소"""
    unique_id = "gas_station"
    name = "주유소"
    is_indoor = False
    stay_duration = 3
    describe_text = {
        "default": "버려진 주유소. 녹슨 주유기가 서 있다.",
        "낮": "햇살 아래 녹슨 철판이 반짝인다.",
        "밤": "어둠 속에서 주유소 지붕의 실루엣이 보인다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundAsphalt())


class ConvenienceStore(Location):
    """편의점 - 문 열린 편의점 (실내)"""
    unique_id = "convenience_store"
    name = "편의점"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "문이 열려 있는 편의점. 선반이 대부분 비어 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundConcrete())


class Pharmacy(Location):
    """약국 - 약품 있을 수 있음 (실내)"""
    unique_id = "pharmacy"
    name = "약국"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "버려진 약국. 약품이 남아 있을지도 모른다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundConcrete())


class ParkingLot(Location):
    """주차장 - 차량 발견 장소"""
    unique_id = "parking_lot"
    name = "주차장"
    is_indoor = False
    stay_duration = 3
    describe_text = {
        "default": "황량한 주차장. 버려진 차들이 몇 대 보인다.",
        "낮": "햇살 아래 녹슨 차량들이 줄지어 있다.",
        "밤": "어둠 속에 차량들의 검은 윤곽만 보인다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundAsphalt())


class Hideout(Location):
    """은신처 - 도심 생존자들의 거처 (유키/엘라)"""
    unique_id = "hideout"
    name = "은신처"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "건물 지하에 마련된 은신처. 좁지만 안전해 보인다.",
        "밤": "희미한 촛불이 은신처를 비춘다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundConcrete())


class ClothingStore(Location):
    """의류점 - 황폐화된 옷가게 (실내)"""
    unique_id = "clothing_store"
    name = "의류점"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "버려진 의류점. 진열대가 넘어져 있고 옷가지들이 여기저기 흩어져 있다.",
        "낮": "깨진 유리창으로 햇빛이 들어와 먼지가 보인다.",
        "밤": "어두운 매장 안. 마네킹들의 실루엣이 으스스하다."
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)
        self.add_ground(GroundConcrete())

        # 옷걸이 (옷장 역할)
        from assets.objects.furniture import Wardrobe
        wardrobe = Wardrobe()
        wardrobe.name = "옷걸이"
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
            Sunglasses, DenimJacket, TrackSuit
        )

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
