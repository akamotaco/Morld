# assets/objects/nature.py - 자연 오브젝트 (자원 생성)
#
# 주기적으로 음식/자원을 생성하는 자연 오브젝트
# - AppleTree: 사과나무
# - BerryBush: 산딸기 덤불
#
# Agent와 연동되어 think()에서 주기적으로 자원 생성
# 자원은 오브젝트의 인벤토리에 저장됨

import morld
from assets.base import Object


class ResourceObject(Object):
    """
    자원 생성 오브젝트 베이스 클래스

    Attributes:
        resource_item_unique_id: 생성할 아이템의 unique_id
        max_resources: 최대 보유 가능 개수
    """
    resource_item_unique_id = None
    max_resources = 3

    def get_resource_count(self):
        """현재 자원 개수 조회 (인벤토리 기반)"""
        if not self._instantiated:
            return 0

        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            return 0

        # resource_item_unique_id와 일치하는 아이템 개수 합산
        total = 0
        for item_id, count in inventory.items():
            item_info = morld.get_item_info(item_id)
            if item_info and item_info.get("unique_id") == self.resource_item_unique_id:
                total += count
        return total

    def can_spawn_resource(self):
        """자원 생성 가능 여부"""
        return self.get_resource_count() < self.max_resources

    def spawn_resource(self):
        """
        자원 하나 생성 (Agent에서 호출)

        Returns:
            bool: 생성 성공 여부
        """
        if not self.can_spawn_resource():
            return False

        item_id = morld.get_item_id_by_unique(self.resource_item_unique_id)
        if item_id is None:
            print(f"[ResourceObject] Item not found: {self.resource_item_unique_id}")
            return False

        morld.give_item(self.instance_id, item_id, 1)
        return True


class AppleTree(ResourceObject):
    """사과나무 - 사과 생성"""
    unique_id = "apple_tree"
    name = "사과나무"
    resource_item_unique_id = "apple"
    max_resources = 3
    actions = ["container"]  # 인벤토리 표시 (가져가기만, 넣기 불가)

    def get_focus_text(self):
        """현재 상태에 따른 묘사"""
        count = self.get_resource_count()
        if count >= 3:
            return "사과가 주렁주렁 열린 나무. 빨갛게 익은 사과가 탐스럽다."
        elif count > 0:
            return f"사과나무. 익은 사과가 {count}개 달려 있다."
        else:
            return "사과나무. 아직 익은 사과가 없다."


class BerryBush(ResourceObject):
    """산딸기 덤불 - 산딸기 생성"""
    unique_id = "berry_bush"
    name = "산딸기 덤불"
    resource_item_unique_id = "wild_berry"
    max_resources = 5
    actions = ["container"]  # 인벤토리 표시 (가져가기만, 넣기 불가)

    def get_focus_text(self):
        """현재 상태에 따른 묘사"""
        count = self.get_resource_count()
        if count >= 4:
            return "산딸기가 풍성하게 열린 덤불. 빨갛게 익은 열매가 가득하다."
        elif count > 0:
            return f"산딸기 덤불. 익은 산딸기가 {count}개 있다."
        else:
            return "산딸기 덤불. 아직 익은 산딸기가 없다."


class MushroomPatch(ResourceObject):
    """버섯 군락 - 버섯 생성"""
    unique_id = "mushroom_patch"
    name = "버섯 군락"
    resource_item_unique_id = "mushroom"
    max_resources = 4
    actions = ["container"]  # 인벤토리 표시 (가져가기만, 넣기 불가)

    def get_focus_text(self):
        """현재 상태에 따른 묘사"""
        count = self.get_resource_count()
        if count >= 3:
            return "버섯이 무성하게 자란 곳. 다양한 버섯이 보인다."
        elif count > 0:
            return f"버섯 군락. 버섯이 {count}개 있다."
        else:
            return "버섯 군락. 아직 버섯이 자라지 않았다."
