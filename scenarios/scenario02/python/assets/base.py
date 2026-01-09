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
# 텍스트 시스템:
#   - get_describe_text(): 장소에 있을 때 보이는 묘사 (Character, Location)
#   - get_focus_text(): Focus 상태(클릭)일 때 보이는 묘사 (Character, Object, Item)
#   - 각 클래스에서 메서드를 오버라이드하여 구현

import morld
from typing import Optional


def _select_text(text_dict: dict, time_tags: list, name: str = None) -> str:
    """
    시간/날씨 태그 리스트와 가장 잘 매칭되는 텍스트 선택

    Args:
        text_dict: {"tag1,tag2": "텍스트", "default": "기본"} 형식
        time_tags: 현재 활성 시간/날씨 태그 리스트 ["아침", "실외", "날씨:비"]
        name: {name} 포맷 치환용 이름

    Returns:
        매칭된 텍스트 (없으면 빈 문자열)
    """
    if not text_dict:
        return ""

    tag_set = set(time_tags)
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

    def get_describe_text(self) -> str:
        """
        장소에 있을 때 묘사 텍스트 반환

        기본 구현은 빈 문자열 반환.
        서브클래스에서 오버라이드하여 구체적인 묘사 반환.
        """
        return ""

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
    - props: 기본 Prop (스탯/상태 등)

    인스턴스 속성:
    - region_id, location_id: 배치 위치
    """

    type: str = "object"
    mood: list = None
    props: dict = None

    def __init__(self):
        super().__init__()
        self.region_id: Optional[int] = None
        self.location_id: Optional[int] = None

    def add_item(self, item: 'Item', count: int = 1):
        """이 유닛의 인벤토리에 아이템 추가"""
        self._check_instantiated()
        item._check_instantiated()
        morld.give_item(self.instance_id, item.instance_id, count)

    def debug_props(self):
        """유닛의 속성(props) 디버그 출력"""
        self._check_instantiated()
        props = morld.get_unit_props(self.instance_id)
        if not props:
            yield morld.dialog(f"[b]{self.name}[/b]\n\n속성이 없습니다.")
            return
        lines = [f"[b]{self.name}[/b]\n"]
        for key, value in props.items():
            lines.append(f"  {key}: {value}")
        yield morld.dialog("\n".join(lines))


class Character(Unit):
    """
    캐릭터 클래스 (NPC, 플레이어)

    메서드 오버라이드:
    - get_describe_text(): 장소에 있을 때 묘사 (플레이어와 같은 위치)
    - get_focus_text(): Focus 상태일 때 묘사 (클릭했을 때)
    """

    type: str = "male"

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
            self.mood or [],
            self.unique_id  # unique_id 전달
        )

        # Prop 설정
        if self.props:
            morld.set_unit_props(instance_id, self.props)

        # 인스턴스 캐시 등록 (describe_text/focus_text 조회용)
        from assets.characters import register_instance
        register_instance(instance_id, self)

    def talk(self):
        """
        NPC 대화 - 서브클래스에서 오버라이드

        기본 구현은 간단한 인사.
        각 캐릭터 클래스에서 오버라이드하여 고유 대화 구현.
        """
        yield morld.dialog(f"{self.name}: 안녕.")

    def debug_self_props(self):
        """플레이어 자신의 속성 확인 (거울 등에서 사용)"""
        player_id = morld.get_player_id()
        props = morld.get_unit_props(player_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "???") if player_info else "???"

        if not props:
            yield morld.dialog(f"[b]{player_name}[/b]\n\n아직 알 수 있는 것이 없다.")
            return

        lines = [f"[b]{player_name}[/b]\n"]
        for key, value in props.items():
            lines.append(f"  {key}: {value}")
        yield morld.dialog("\n".join(lines))


class Object(Unit):
    """
    오브젝트 클래스 (가구, 바닥 등)

    메서드 오버라이드:
    - get_focus_text(): Focus 상태일 때 묘사 (클릭했을 때)

    액션 패턴:
    - call:메서드명:표시명 → 인스턴스 메서드 호출 (OOP 다형성)

    공통 메서드 (Unit에서 상속):
    - debug_props(): 속성 디버그 출력
    """

    type: str = "object"

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

        # Prop 설정 (좌석 정보 등)
        if self.props:
            morld.set_unit_props(instance_id, self.props)

        # 인스턴스 캐시 등록 (call: 액션, focus_text 조회용)
        from assets.objects import register_instance
        register_instance(instance_id, self)


class Item(Asset):
    """
    아이템 클래스

    클래스 속성:
    - passive_props: 소유 효과
    - equip_props: 장착 효과
    - value: 거래 가치
    - owner: 소유자 unique_id (None이면 공용)

    액션 패턴:
    - call:메서드명:표시명 → 인스턴스 메서드 호출 (OOP 다형성)
    """

    passive_props: dict = None
    equip_props: dict = None
    value: int = 0
    owner: str = None  # 소유자 unique_id (예: "sera", "mila")

    def instantiate(self, instance_id: int):
        """아이템을 morld에 등록"""
        super().instantiate(instance_id)

        morld.add_item(
            instance_id,
            self.name,
            self.passive_props or {},
            self.equip_props or {},
            self.value,
            self.actions or [],
            self.owner  # 소유자 정보 전달
        )

        # 인스턴스 캐시 등록 (call: 액션용)
        from assets.items import register_instance
        register_instance(instance_id, self)


class Location(Asset):
    """
    Location 클래스

    클래스 속성:
    - is_indoor: 실내 여부
    - stay_duration: 경유 시 지체 시간
    - describe_text: 장소 묘사 텍스트 딕셔너리 (태그 기반 선택용)
    - owner: 소유자 unique_id (None이면 공용)

    인스턴스 속성:
    - location_id, region_id: 위치 정보
    - ground: 바닥 오브젝트 인스턴스 (instantiate에서 생성)

    메서드 오버라이드:
    - get_describe_text(): 시간/날씨 태그 기반 장소 묘사
    """

    is_indoor: bool = True
    stay_duration: int = 0
    describe_text: dict = None  # 태그 기반 묘사 텍스트
    owner: str = None  # 소유자 unique_id (예: "sera", "mila")

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
            self.stay_duration,
            self.is_indoor,
            self.owner  # 소유자 정보 전달
        )

    def get_describe_text(self) -> str:
        """
        Location의 묘사 텍스트 반환

        describe_text가 정의되어 있으면
        현재 시간/날씨 태그를 기반으로 묘사 반환.
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
