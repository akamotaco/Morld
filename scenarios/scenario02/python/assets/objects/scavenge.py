# assets/objects/scavenge.py - 비충전 수집 가능 오브젝트
#
# ResourceObject와 유사하나 자원이 자동 보충되지 않는다.
# 초기 재고만 설정되며, NPC/플레이어가 가져가면 소진됨.

import morld
import ui
from assets.base import Object
from assets.registry import get_or_create_item_id


class ScavengeableObject(Object):
    """
    비충전 수집 오브젝트 베이스 클래스

    ResourceObject와 달리 자원이 자동 보충되지 않는다.
    instantiate() 시 initial_items를 기반으로 초기 재고 설정.

    Attributes:
        initial_items: 초기 아이템 dict {unique_id: count}
    """
    item_visible = True
    actions = ["container#", "call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    initial_items = {}  # {unique_id: count} — 서브클래스에서 오버라이드

    def instantiate(self, *args, **kwargs):
        instance_id = super().instantiate(*args, **kwargs)

        # 초기 재고 배치
        for unique_id, count in self.initial_items.items():
            item_id = get_or_create_item_id(unique_id)
            if item_id is not None:
                morld.give_item(instance_id, item_id, count)

        return instance_id

    def look(self):
        """살펴보기"""
        inventory = morld.get_unit_inventory(self.instance_id)
        if inventory and sum(inventory.values()) > 0:
            yield ui.dialog(["무언가 남아 있는 것 같다."])
        else:
            yield ui.dialog(["텅 비어 있다. 쓸 만한 것은 더 이상 없다."])
        morld.advance_time(1 * 60_000)


class GasStationStand(ScavengeableObject):
    """주유소 가판대 - 생수, 에너지음료"""
    unique_id = "gas_station_stand"
    name = "가판대"
    focus_text = {"default": "주유소 안에 남은 낡은 가판대. 몇 가지 물건이 보인다."}
    initial_items = {
        "drink_water": 2,
        "drink_energy": 1,
    }


class PharmacyShelf(ScavengeableObject):
    """약품 진열대 - 약초"""
    unique_id = "pharmacy_shelf"
    name = "약품 진열대"
    focus_text = {"default": "약국 진열대. 대부분 비었지만 약초 몇 묶음이 남아 있다."}
    initial_items = {
        "food_herb": 3,
    }


class BrokenVendingMachine(ScavengeableObject):
    """부서진 자판기 - 캔커피, 콜라"""
    unique_id = "broken_vending_machine"
    name = "부서진 자판기"
    focus_text = {"default": "주차장 한켠에 버려진 자판기. 부서져 있지만 안에 뭔가 남아 있다."}
    initial_items = {
        "drink_canned_coffee": 2,
        "drink_canned_cola": 1,
    }
