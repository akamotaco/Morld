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
#
# describe_text 시스템:
#   - 모든 Asset은 describe_text() 메서드를 가짐
#   - Unit/Location은 현재 상태에 맞는 묘사 텍스트 반환
#   - describe_text 딕셔너리의 키 우선순위:
#     - Unit: activity:{활동} > {region}:{location} > mood:{감정} > default
#     - Location: appearance 딕셔너리 기반 (C# DescribeSystem에서 처리)

import morld
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass


def _select_text(text_dict: dict, tags: list, name: str = None) -> str:
    """
    태그 리스트와 가장 잘 매칭되는 텍스트 선택

    Args:
        text_dict: {"tag1,tag2": "텍스트", "default": "기본"} 형식
        tags: 현재 활성 태그 리스트 ["activity:식사", "0:3", "mood:기쁨"]
        name: {name} 포맷 치환용 이름

    Returns:
        매칭된 텍스트 (없으면 빈 문자열)
    """
    if not text_dict:
        return ""

    tag_set = set(tags)
    best_match = None
    best_count = 0

    for key, text in text_dict.items():
        if key == "default":
            continue

        # 키를 쉼표로 분리하여 태그 집합으로
        key_tags = set(k.strip() for k in key.split(","))

        # 모든 키 태그가 현재 태그에 포함되어야 함
        if key_tags <= tag_set:
            match_count = len(key_tags)
            if match_count > best_count:
                best_count = match_count
                best_match = text

    # 매칭된 것이 없으면 default 사용
    if best_match is None:
        best_match = text_dict.get("default", "")

    # {name} 치환
    if name and best_match:
        best_match = best_match.format(name=name)

    return best_match


class Asset:
    """
    모든 Asset의 베이스 클래스

    클래스 속성 (Asset 정의):
    - unique_id: Asset 식별자
    - name: 표시 이름
    - describe_text: 상황별 묘사 텍스트 딕셔너리

    인스턴스 속성 (생성 후):
    - instance_id: 시스템에서 사용하는 고유 ID
    - _instantiated: instantiate() 호출 여부
    """

    # 클래스 속성 (서브클래스에서 정의)
    unique_id: str = None
    name: str = None
    appearance: dict = None
    actions: list = None
    describe_text: dict = None  # 상황별 묘사 텍스트

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

    def get_describe_text(self) -> str:
        """
        현재 상태에 맞는 묘사 텍스트 반환

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
    캐릭터 클래스 (NPC, 플레이어)

    클래스 속성:
    - schedule_stack: 스케줄 스택 정의
    - describe_text: 상황별 묘사 (presence text 역할)
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

        # 인스턴스 캐시 등록 (describe_text 조회용)
        from assets.characters import register_instance
        register_instance(instance_id, self)


class Object(Unit):
    """
    오브젝트 클래스 (가구, 바닥 등)

    클래스 속성:
    - is_visible: 인벤토리 가시성 (바닥은 True)
    - describe_text: 상황별 묘사 (선택적)
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
    - describe_text: 상황별 추가 묘사 (appearance와 별도)

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

    def get_describe_text(self) -> str:
        """
        Location의 추가 묘사 텍스트 반환

        appearance와는 별개로, describe_text가 정의되어 있으면
        현재 시간/날씨 태그를 기반으로 추가 묘사 반환.
        """
        if not self.describe_text:
            return ""

        self._check_instantiated()

        # morld API로 현재 시간/날씨 태그 조회
        time_tags = morld.get_time_tags() if hasattr(morld, 'get_time_tags') else []

        return _select_text(self.describe_text, time_tags)

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
