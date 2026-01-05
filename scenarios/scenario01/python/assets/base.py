# assets/base.py - Asset 클래스 계층 구조 (방 탈출 시나리오)
#
# 상속 구조:
#   Asset (base)
#   ├── Unit
#   │   ├── Character
#   │   └── Object
#   └── Item
#
# 사용법:
#   player = Player()
#   player.instantiate(0, 0, 0)  # instance_id, region_id, location_id
#
# 텍스트 시스템:
#   - get_focus_text(): Focus 상태(클릭)일 때 보이는 묘사

import morld
from typing import Optional


class Asset:
    """
    모든 Asset의 베이스 클래스

    클래스 속성 (Asset 정의):
    - unique_id: Asset 식별자
    - name: 표시 이름
    - actions: 가능한 액션 리스트

    인스턴스 속성 (생성 후):
    - instance_id: 시스템에서 사용하는 고유 ID
    - _instantiated: instantiate() 호출 여부
    """

    # 클래스 속성 (서브클래스에서 정의)
    unique_id: str = None
    name: str = None
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

    def get_focus_text(self) -> str:
        """
        Focus 상태일 때 묘사 텍스트 반환

        기본 구현은 빈 문자열 반환.
        서브클래스에서 오버라이드하여 구체적인 묘사 반환.
        """
        return ""


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
    캐릭터 클래스 (플레이어)

    방 탈출 시나리오에서는 플레이어만 존재.
    """

    type: str = "male"

    def instantiate(self, instance_id: int, region_id: int, location_id: int):
        """캐릭터를 morld에 등록"""
        super().instantiate(instance_id)
        self.region_id = region_id
        self.location_id = location_id

        morld.add_unit(
            instance_id,
            self.name,
            region_id,
            location_id,
            self.type,
            self.actions or [],
            self.mood or []
        )

        # 태그 설정
        if self.tags:
            morld.set_unit_tags(instance_id, self.tags)


class Object(Unit):
    """
    오브젝트 클래스 (가구, 문, 상자 등)

    클래스 속성:
    - focus_text: Focus 상태일 때 묘사 (dict 또는 str)

    메서드 오버라이드:
    - get_focus_text(): 클릭했을 때 묘사
    """

    type: str = "object"
    focus_text: dict = None  # {"default": "묘사"} 또는 단순 문자열

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
            []  # mood
        )

    def get_focus_text(self) -> str:
        """Focus 상태일 때 묘사"""
        if self.focus_text is None:
            return ""
        if isinstance(self.focus_text, str):
            return self.focus_text
        return self.focus_text.get("default", "")


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
