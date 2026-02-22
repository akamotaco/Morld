# assets/locations/mine.py — 폐광산 지역
#
# Location ID (Region 4 내부 ID)
# - 0: 광산 입구 (mine_entrance)
# - 1: 1층 갱도 (mine_1f) - 구리광석, 박쥐
# - 2: 2층 갱도 (mine_2f) - 구리+철광석, 거미
# - 3: 깊은 갱도 (mine_deep) - 철광석, 거미(강)

import morld
from assets.base import Location


class MineEntrance(Location):
    """광산 입구 — 안전지대"""
    unique_id = "mine_entrance"
    name = "광산 입구"
    is_indoor = False
    ground_type = "GroundAsphalt"
    stay_duration = 3
    geometry = 1  # line
    length = 300

    describe_text = {
        "default": "폐광산 입구. 녹슨 레일과 무너진 갱도 입구가 보인다.",
        "낮": "햇빛 아래 폐광의 출입금지 표지판이 바래져 있다.",
        "밤": "어둠 속에 광산 입구가 검은 구멍처럼 보인다.",
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 벤치 (야외 휴식)
        from assets.objects.outdoor import StreetBench
        bench = StreetBench()
        bench.name = "나무 벤치"
        bench.focus_text = {"default": "광부들이 쉬던 낡은 벤치다."}
        self.add_object(bench, x=100)

        # 곡괭이 1개 바닥에 배치
        import ground as ground_mod
        from assets.items.weapons import Pickaxe
        pickaxe = Pickaxe()
        pickaxe_id = morld.create_id("item")
        pickaxe.instantiate(pickaxe_id)
        ground_id = ground_mod.ensure_ground_at(region_id, location_id, 0)
        morld.give_item(ground_id, pickaxe_id, 1)


class MineFloor1(Location):
    """1층 갱도 — 구리광석, 박쥐 서식"""
    unique_id = "mine_1f"
    name = "1층 갱도"
    is_indoor = True
    ground_type = "GroundConcrete"
    stay_duration = 0
    geometry = 1
    length = 500

    describe_text = {
        "default": "지하로 내려가는 넓은 갱도. 구리빛 광맥이 벽에 보인다.",
        "밤": "횃불 없이는 한 치 앞도 보이지 않는다.",
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        from assets.objects.mining import CopperOreNode
        self.add_object(CopperOreNode(), x=150)
        self.add_object(CopperOreNode(), x=350)


class MineFloor2(Location):
    """2층 갱도 — 구리+철광석, 거미 서식"""
    unique_id = "mine_2f"
    name = "2층 갱도"
    is_indoor = True
    ground_type = "GroundConcrete"
    stay_duration = 0
    geometry = 1
    length = 400

    describe_text = {
        "default": "더 깊은 갱도. 거미줄이 여기저기 걸려 있고, 광맥이 빛난다.",
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        from assets.objects.mining import CopperOreNode, IronOreNode
        self.add_object(CopperOreNode(), x=100)
        self.add_object(IronOreNode(), x=280)


class MineDeep(Location):
    """깊은 갱도 — 철광석, 거미(강) 서식"""
    unique_id = "mine_deep"
    name = "깊은 갱도"
    is_indoor = True
    ground_type = "GroundConcrete"
    stay_duration = 0
    geometry = 1
    length = 300

    describe_text = {
        "default": "광산의 가장 깊은 곳. 공기가 차갑고 습하다. 철광석이 벽면에 드러나 있다.",
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        from assets.objects.mining import IronOreNode
        self.add_object(IronOreNode(), x=80)
        self.add_object(IronOreNode(), x=220)
