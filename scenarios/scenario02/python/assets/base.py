# assets/base.py - Asset 클래스 계층 구조
#
# 상속 구조:
#   Asset (base)
#   ├── Unit
#   │   ├── Character
#   │   └── Object
#   ├── Item
#   └── Location
#
# 사용법:
#   loc = BackYard()                    # 인스턴스 생성
#   loc.instantiate(12, REGION_ID)      # morld에 등록
#   loc.ground.add_item(herb)           # 바닥에 아이템 추가

import morld
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class Asset:
    """
    모든 Asset의 베이스 클래스

    클래스 속성 (Asset 정의):
    - unique_id: Asset 식별자
    - name: 표시 이름

    인스턴스 속성 (생성 후):
    - instance_id: 시스템에서 사용하는 고유 ID
    - _instantiated: instantiate() 호출 여부
    """

    # 클래스 속성 (서브클래스에서 정의)
    unique_id: str = None
    name: str = None
    appearance: dict = None
    actions: list = None

    def __init__(self):
        """인스턴스 생성 (아직 morld에 등록되지 않음)"""
        self.instance_id: Optional[int] = None
        self._instantiated: bool = False

    def instantiate(self, instance_id: int, **kwargs):
        """
        Asset을 morld에 등록

        서브클래스에서 오버라이드하여 구체적인 등록 로직 구현.
        반드시 super().instantiate()를 호출하여 instance_id 설정.
        """
        self.instance_id = instance_id
        self._instantiated = True

    def _check_instantiated(self):
        """instantiate() 호출 여부 확인"""
        if not self._instantiated:
            raise RuntimeError(f"{self.__class__.__name__} is not instantiated yet. Call instantiate() first.")


class Unit(Asset):
    """
    Unit 베이스 클래스 (캐릭터/오브젝트 공통)

    클래스 속성:
    - type: "male", "female", "object" 등
    - mood: 감정 상태 리스트
    - tags: 기본 태그/스탯

    인스턴스 속성:
    - region_id, location_id: 배치 위치
    """

    type: str = "object"
    mood: list = None
    tags: dict = None

    def __init__(self):
        super().__init__()
        self.region_id: Optional[int] = None
        self.location_id: Optional[int] = None

    def add_item(self, item: 'Item', count: int = 1):
        """이 유닛의 인벤토리에 아이템 추가"""
        self._check_instantiated()
        item._check_instantiated()
        morld.give_item(self.instance_id, item.instance_id, count)


class Character(Unit):
    """
    캐릭터 클래스 (NPC, 플레이어)

    클래스 속성:
    - schedule_stack: 스케줄 스택 정의
    """

    type: str = "male"
    schedule_stack: list = None

    def instantiate(self, instance_id: int, region_id: int, location_id: int):
        """캐릭터를 morld에 등록"""
        super().instantiate(instance_id)
        self.region_id = region_id
        self.location_id = location_id

        # 기본 유닛 생성
        morld.add_unit(
            instance_id,
            self.name,
            region_id,
            location_id,
            self.type,
            self.actions or [],
            self.appearance or {},
            self.mood or []
        )

        # 태그 설정
        if self.tags:
            morld.set_unit_tags(instance_id, self.tags)

        # 스케줄 스택 설정
        for layer in (self.schedule_stack or []):
            morld.push_schedule(
                instance_id,
                layer.get("name", ""),
                layer.get("endConditionType"),
                layer.get("endConditionParam"),
                layer.get("schedule")
            )


class Object(Unit):
    """
    오브젝트 클래스 (가구, 바닥 등)

    클래스 속성:
    - is_visible: 인벤토리 가시성 (바닥은 True)
    """

    type: str = "object"
    is_visible: bool = False

    def instantiate(self, instance_id: int, region_id: int, location_id: int):
        """오브젝트를 morld에 등록"""
        super().instantiate(instance_id)
        self.region_id = region_id
        self.location_id = location_id

        morld.add_unit(
            instance_id,
            self.name,
            region_id,
            location_id,
            "object",
            self.actions or [],
            self.appearance or {},
            []  # mood
        )

        # 가시성 설정
        if self.is_visible:
            morld.set_unit_visibility(instance_id, True)


class Item(Asset):
    """
    아이템 클래스

    클래스 속성:
    - passive_tags: 소유 효과
    - equip_tags: 장착 효과
    - value: 거래 가치
    """

    passive_tags: dict = None
    equip_tags: dict = None
    value: int = 0

    def instantiate(self, instance_id: int):
        """아이템을 morld에 등록"""
        super().instantiate(instance_id)

        morld.add_item(
            instance_id,
            self.name,
            self.passive_tags or {},
            self.equip_tags or {},
            self.value,
            self.actions or []
        )


class Location(Asset):
    """
    Location 클래스

    클래스 속성:
    - is_indoor: 실내 여부
    - stay_duration: 경유 시 지체 시간

    인스턴스 속성:
    - location_id, region_id: 위치 정보
    - ground: 바닥 오브젝트 인스턴스 (instantiate에서 생성)
    """

    is_indoor: bool = True
    stay_duration: int = 0

    def __init__(self):
        super().__init__()
        self.location_id: Optional[int] = None
        self.region_id: Optional[int] = None
        self.ground: Optional[Object] = None

    def instantiate(self, location_id: int, region_id: int):
        """
        Location을 morld에 등록

        서브클래스에서 오버라이드하여 ground 생성 등 추가 로직 구현.
        반드시 super().instantiate()를 먼저 호출.
        """
        super().instantiate(location_id)
        self.location_id = location_id
        self.region_id = region_id

        # Location 등록
        morld.add_location(
            region_id,
            location_id,
            self.name,
            self.appearance or {},
            self.stay_duration,
            self.is_indoor
        )

    def add_ground(self, ground: Object, ground_instance_id: int = None):
        """
        바닥 오브젝트 추가

        Args:
            ground: 바닥 Object 인스턴스
            ground_instance_id: 바닥 ID (None이면 1000 + location_id)
        """
        self._check_instantiated()

        if ground_instance_id is None:
            ground_instance_id = 1000 + self.location_id

        ground.instantiate(ground_instance_id, self.region_id, self.location_id)
        self.ground = ground

    def add_object(self, obj: Object, instance_id: int):
        """이 Location에 오브젝트 배치"""
        self._check_instantiated()
        obj.instantiate(instance_id, self.region_id, self.location_id)

    def add_item_to_ground(self, item: Item, count: int = 1):
        """바닥에 아이템 추가 (ground의 인벤토리에 추가)"""
        self._check_instantiated()
        if self.ground is None:
            raise RuntimeError(f"Location {self.name} has no ground object")
        self.ground.add_item(item, count)
