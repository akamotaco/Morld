# assets/locations/storage.py - 창고

import morld
import ui
from assets.base import Location
from assets.objects.grounds import GroundWooden
from assets.objects.furniture import CraftingTable, WallLamp, IngredientStorage


class InfiniteSeedBag(object):
    """(디버그) 무한 씨앗 포대 — 모든 종류의 씨앗을 무한히 꺼낼 수 있다."""

    def __new__(cls):
        from assets.base import Object

        class _SeedBag(Object):
            unique_id = "debug_seed_bag"
            name = "(디버그) 씨앗 포대"
            actions = ["call:take_seed:씨앗 꺼내기", "call:debug_props:(디버그) 속성 보기#"]
            focus_text = {"default": "각종 씨앗이 가득 든 커다란 포대. 무한히 꺼낼 수 있다."}

            def take_seed(self):
                from assets.registry import get_or_create_item_id
                import garden

                player_id = morld.get_player_id()
                state = {"selected": None}

                def on_select(action):
                    if action == "init":
                        return None
                    if action.startswith("seed:"):
                        state["selected"] = int(action[5:])
                        return True
                    return None

                lines = ["어떤 씨앗을 꺼낼까?", ""]
                for code, info in garden.SEED_REGISTRY.items():
                    lines.append(f"  [url=@proc:seed:{code}]{info['name']} 씨앗[/url]")
                lines.append("")
                lines.append("[url=@ret:cancel]취소[/url]")

                yield ui.dialog("\n".join(lines), autofill="off", proc=on_select, result=state)

                if state["selected"]:
                    info = garden.SEED_REGISTRY[state["selected"]]
                    seed_id = get_or_create_item_id(info["seed_unique_id"])
                    if seed_id:
                        morld.give_item(player_id, seed_id, 5)
                        yield ui.dialog(f"{info['name']} 씨앗 5개를 꺼냈다.")

        return _SeedBag()


class InfiniteFertilizerBag(object):
    """(디버그) 무한 비료 포대 — 비료를 무한히 꺼낼 수 있다."""

    def __new__(cls):
        from assets.base import Object

        class _FertilizerBag(Object):
            unique_id = "debug_fertilizer_bag"
            name = "(디버그) 비료 포대"
            actions = ["call:take_fertilizer:비료 꺼내기", "call:debug_props:(디버그) 속성 보기#"]
            focus_text = {"default": "비료가 가득 든 커다란 포대. 무한히 꺼낼 수 있다."}

            def take_fertilizer(self):
                from assets.registry import get_or_create_item_id

                player_id = morld.get_player_id()
                fertilizer_id = get_or_create_item_id("fertilizer")
                if fertilizer_id:
                    morld.give_item(player_id, fertilizer_id, 5)
                    yield ui.dialog("비료 5개를 꺼냈다.")

        return _FertilizerBag()


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
            actions = ["container#", "call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
            focus_text = {"default": "여러 도구가 정리된 나무 상자. 열어서 도구를 꺼낼 수 있다."}

            def look(self):
                """도구함 살펴보기"""
                yield ui.dialog([
                    "여러 도구가 정리된 나무 상자다.",
                    "낚시대, 밧줄 등 야외 활동에 필요한 것들이 있다."
                ])
                morld.advance_time_des(1 * 60_000)

        return ToolboxObject()


class Storage(Location):
    unique_id = "storage"
    name = "창고"
    is_indoor = True
    stay_duration = 0
    length = 180  # Pi-World: 창고 길이
    describe_text = {
        "default": "저택 2층에 있는 작은 창고. 사용하지 않는 물건들이 쌓여 있다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """창고 생성 + 바닥 + 제작대 + 도구함 추가"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundWooden())
        self.add_object(CraftingTable(), x=10)  # 입구 쪽
        lamp_id = self.add_object(WallLamp(), x=90)
        morld.set_unit_prop(lamp_id, "light:on", 0)  # 창고는 어두운 상태로 시작

        self.add_object(IngredientStorage(), x=40)  # 재료 보관함

        # 도구함 추가 및 도구 배치
        toolbox = Toolbox()
        toolbox_id = self.add_object(toolbox, x=20)  # 안쪽

        # 낚시대를 도구함에 넣기
        from assets.items.tools import FishingRod, Axe, Saw
        fishing_rod = FishingRod()
        fishing_rod_id = morld.create_id("item")
        fishing_rod.instantiate(fishing_rod_id)
        morld.give_item(toolbox_id, fishing_rod_id, 1)

        # 도끼를 도구함에 넣기
        axe = Axe()
        axe_id = morld.create_id("item")
        axe.instantiate(axe_id)
        morld.give_item(toolbox_id, axe_id, 1)

        # 톱을 도구함에 넣기
        saw = Saw()
        saw_id = morld.create_id("item")
        saw.instantiate(saw_id)
        morld.give_item(toolbox_id, saw_id, 1)

        # 투박한 단검을 도구함에 넣기 (세라 소유)
        from assets.items.equipment import RusticDagger, Compass, MansionMap
        dagger = RusticDagger()
        dagger_id = morld.create_id("item")
        dagger.instantiate(dagger_id)
        morld.give_item(toolbox_id, dagger_id, 1)

        # 나침반을 도구함에 넣기 (전체 지역 지도 기능)
        compass = Compass()
        compass_id = morld.create_id("item")
        compass.instantiate(compass_id)
        morld.give_item(toolbox_id, compass_id, 1)

        # 저택 지도를 도구함에 넣기 (저택 지역 전용)
        mansion_map = MansionMap()
        mansion_map_id = morld.create_id("item")
        mansion_map.instantiate(mansion_map_id)
        morld.give_item(toolbox_id, mansion_map_id, 1)

        # 빗자루를 도구함에 넣기 (청소 도구)
        from assets.items.tools import Broom
        broom = Broom()
        broom_id = morld.create_id("item")
        broom.instantiate(broom_id)
        morld.give_item(toolbox_id, broom_id, 1)

        # 물뿌리개를 도구함에 넣기 (텃밭용)
        from assets.items.garden_items import WateringCan, WaterBucket
        watering_can = WateringCan()
        watering_can_id = morld.create_id("item")
        watering_can.instantiate(watering_can_id)
        morld.give_item(toolbox_id, watering_can_id, 1)

        # 물통을 도구함에 넣기 (텃밭용)
        water_bucket = WaterBucket()
        water_bucket_id = morld.create_id("item")
        water_bucket.instantiate(water_bucket_id)
        morld.give_item(toolbox_id, water_bucket_id, 1)

        # (디버그) 무한 씨앗 포대 + 무한 비료 포대
        self.add_object(InfiniteSeedBag(), x=60)
        self.add_object(InfiniteFertilizerBag(), x=70)
