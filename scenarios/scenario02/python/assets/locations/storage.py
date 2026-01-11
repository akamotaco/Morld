# assets/locations/storage.py - 창고

import morld
from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import CraftingTable


class Toolbox(object):
    """
    도구함 - 낚시대 등 도구 보관

    컨테이너 오브젝트로 아이템을 가져갈 수 있음
    """

    def __new__(cls):
        # Object 클래스에서 상속받아 생성
        from assets.base import Object

        class ToolboxObject(Object):
            unique_id = "toolbox"
            name = "도구함"
            actions = ["container", "call:look:살펴보기", "call:debug_props:속성 보기"]
            focus_text = {"default": "여러 도구가 정리된 나무 상자. 열어서 도구를 꺼낼 수 있다."}

            def look(self):
                """도구함 살펴보기"""
                yield morld.dialog([
                    "여러 도구가 정리된 나무 상자다.",
                    "낚시대, 밧줄 등 야외 활동에 필요한 것들이 있다."
                ])
                morld.advance_time(1)

        return ToolboxObject()


class Storage(Location):
    unique_id = "storage"
    name = "창고"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "저택 2층에 있는 작은 창고. 사용하지 않는 물건들이 쌓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """창고 생성 + 바닥 + 제작대 + 도구함 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(CraftingTable())

        # 도구함 추가 및 도구 배치
        toolbox = Toolbox()
        toolbox_id = self.add_object(toolbox)

        # 낚시대를 도구함에 넣기
        from assets.items.tools import FishingRod, Axe
        fishing_rod = FishingRod()
        fishing_rod_id = morld.create_id("item")
        fishing_rod.instantiate(fishing_rod_id)
        morld.give_item(toolbox_id, fishing_rod_id, 1)

        # 도끼를 도구함에 넣기
        axe = Axe()
        axe_id = morld.create_id("item")
        axe.instantiate(axe_id)
        morld.give_item(toolbox_id, axe_id, 1)
