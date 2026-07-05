# assets/base.py — engine.asset_base 상속 (시나리오03)
#
# U2 (infra-unification §2-4): 과거 "공용 코드 분리 전까지 임시" 자체 최소 구현을
# engine 정본 상속으로 전환. Rule 셀렉터/talk 골격/Context 빌더를 엔진에서 획득.
# instantiate의 morld 호출 시그니처는 기존 S03 방식 유지.

import morld

from engine.asset_base import (  # noqa: F401
    Asset, Unit, CharacterBase, ObjectBase, ItemBase, LocationBase,
    TextSelector, select_text,
)


class Character(CharacterBase):
    """S03 캐릭터 — 프레임워크(묘사/talk/context)는 엔진 상속"""

    describe_text = None  # 레거시 슬롯 (기존 S03 캐릭터 정의 호환)

    def instantiate(self, instance_id, region_id, location_id):
        super().instantiate(instance_id)
        self.region_id = region_id
        self.location_id = location_id
        morld.add_unit(
            instance_id, self.name or self.unique_id,
            region_id, location_id,
            self.type, self.actions or [],
            [], self.unique_id,
        )
        if self.props:
            morld.set_unit_props(instance_id, dict(self.props))


class Object(ObjectBase):
    """S03 오브젝트"""

    describe_text = None

    def instantiate(self, instance_id, region_id, location_id, x=0, y=0):
        super().instantiate(instance_id)
        self.region_id = region_id
        self.location_id = location_id
        morld.add_unit(
            instance_id, self.name or self.unique_id,
            region_id, location_id,
            self.type, self.actions or [],
            [], self.unique_id,
        )
        if self.props:
            morld.set_unit_props(instance_id, dict(self.props))
        if x:
            morld.set_unit_position(instance_id, x)


class Item(ItemBase):
    """S03 아이템"""

    def instantiate(self, instance_id):
        super().instantiate(instance_id)
        morld.add_item(instance_id, self.name or self.unique_id,
                       equip_props=self.equip_props or {})


class Location(LocationBase):
    """S03 장소"""

    stay_duration = 0

    def instantiate(self, location_id, region_id):
        super().instantiate(location_id)
        self.location_id = location_id
        self.region_id = region_id
        morld.add_location(
            region_id, location_id,
            self.name or self.unique_id,
            is_indoor=self.is_indoor,
            stay_duration=self.stay_duration,
            geometry=self.geometry,
            length=self.length,
        )

    def add_object(self, obj, instance_id=None, x=0, y=0):
        if instance_id is None:
            instance_id = morld.create_id("unit")
        obj.instantiate(instance_id, self.region_id, self.location_id, x=x, y=y)
        return instance_id
