"""Asset 베이스 클래스 (시나리오03 최소 구현)

시나리오02의 assets/base.py에서 필요한 인터페이스만 추출.
공용 코드 분리 전까지 독립 동작을 위한 최소 구현.
"""
import morld


class Asset:
    unique_id = None
    name = None
    actions = None

    def __init__(self):
        self.instance_id = None

    def instantiate(self, instance_id, **kwargs):
        self.instance_id = instance_id


class Unit(Asset):
    type = "object"
    props = None
    describe_text = None

    def __init__(self):
        super().__init__()
        self.region_id = None
        self.location_id = None


class Character(Unit):
    type = "male"
    DESCRIBE_RULES = None
    FOCUS_RULES = None

    def instantiate(self, instance_id, region_id, location_id):
        super().instantiate(instance_id)
        self.region_id = region_id
        self.location_id = location_id
        # Register with morld
        morld.add_unit(
            instance_id, self.name or self.unique_id,
            region_id, location_id,
            self.type, self.actions or [],
            [], self.unique_id,
        )
        if self.props:
            morld.set_unit_props(instance_id, dict(self.props))


class Object(Unit):
    type = "object"

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


class Item(Asset):
    equip_props = None
    category = None
    value = 0

    def instantiate(self, instance_id):
        super().instantiate(instance_id)
        morld.add_item(instance_id, self.name or self.unique_id,
                       equip_props=self.equip_props or {})


class Location(Asset):
    is_indoor = True
    stay_duration = 0
    geometry = "line"
    length = 0
    describe_text = None
    ground_type = None

    def __init__(self):
        super().__init__()
        self.location_id = None
        self.region_id = None

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
