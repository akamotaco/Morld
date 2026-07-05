# asset_base.py - Pi-World Engine 에셋 프레임워크
#
# 모든 시나리오의 Asset 클래스 기반.
# 시나리오는 이 클래스들을 상속하여 콘텐츠를 추가한다.
#
# 구조:
#   Asset (기본)
#   ├── Unit (캐릭터/오브젝트 공통)
#   │   ├── CharacterBase (캐릭터 프레임워크)
#   │   └── ObjectBase (오브젝트 프레임워크)
#   ├── ItemBase (아이템)
#   └── LocationBase (장소)

import random

import morld


class DialogueCoverageError(LookupError):
    """대사 커버리지 누락 — 해당 action:timing 에 대한 rule 이 없거나,
    있어도 매치되는 rule 이 없고 catch-all 도 없는 경우.

    작가는 명시적으로 아래 중 하나를 추가해야 함:
        ({}, ["...고정 대사..."])           # default value: 고정 텍스트
        ({}, "_generate_dialogue")        # default value: Hybrid 호출
        ({}, "_custom_method_name")       # default value: 커스텀 메서드
    """
    pass


# ========================================
# TextSelector — 조건 기반 텍스트 선택
# ========================================

class TextSelector:
    """
    조건 기반 텍스트 선택기

    규칙 리스트에서 첫 번째 매칭되는 결과를 반환.
    규칙은 (조건 dict, 결과) 튜플의 리스트.

    조건 매칭:
    - 빈 dict {}: 항상 매칭 (기본값)
    - 문자열 값: 정확히 일치
    - 숫자 값: >= 비교
    - 리스트 context에 문자열 조건: in 체크
    """

    @staticmethod
    def select(rules, context):
        """규칙 리스트에서 첫 번째 매칭 결과 반환"""
        for conditions, result in rules:
            if TextSelector.match(conditions, context):
                return result
        return None

    @staticmethod
    def match(conditions, context):
        """모든 조건이 충족되는지 확인"""
        if not conditions:
            return True
        for key, expected in conditions.items():
            actual = context.get(key)
            if isinstance(actual, list):
                if expected not in actual:
                    return False
            elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                if actual < expected:
                    return False
            elif actual != expected:
                return False
        return True

    @staticmethod
    def format_result(result, context):
        """result가 문자열이면 context로 포맷팅. 리스트면 random.choice 후 포맷."""
        if isinstance(result, list) and result:
            result = random.choice(result)
        if isinstance(result, str):
            try:
                return result.format(**context)
            except KeyError:
                return result
        return result


def select_text(text_dict, time_tags, name=None):
    """시간/날씨 태그 기반 텍스트 선택 (Location 묘사용)"""
    if not text_dict:
        return ""
    tag_set = set(time_tags)
    best_match = None
    best_count = 0
    for key, text in text_dict.items():
        if key == "default":
            continue
        key_tags = set(k.strip() for k in key.split(","))
        if key_tags <= tag_set:
            match_count = len(key_tags)
            if match_count > best_count:
                best_count = match_count
                best_match = text
    if best_match is None:
        best_match = text_dict.get("default", "")
    if name and best_match:
        best_match = best_match.format(name=name)
    return best_match


# ========================================
# Asset — 모든 에셋의 베이스
# ========================================

class Asset:
    """모든 Asset의 베이스 클래스"""

    unique_id = None
    name = None
    actions = None

    def __init__(self):
        self.instance_id = None
        self._instantiated = False

    def instantiate(self, instance_id, **kwargs):
        """Asset을 morld에 등록 — 서브클래스에서 super() 호출 필수"""
        self.instance_id = instance_id
        self._instantiated = True

    def _check_instantiated(self):
        if not self._instantiated:
            raise RuntimeError(f"{self.__class__.__name__} is not instantiated yet.")

    def get_describe_text(self):
        """장소에 있을 때 묘사 텍스트"""
        return ""

    def get_focus_text(self):
        """Focus 상태일 때 묘사 텍스트"""
        return ""


# ========================================
# Unit — 캐릭터/오브젝트 공통
# ========================================

class Unit(Asset):
    """Unit 베이스 클래스 (캐릭터/오브젝트 공통)"""

    type = "object"
    mood = None
    props = None
    owner = None

    def __init__(self):
        super().__init__()
        self.region_id = None
        self.location_id = None

    def add_item(self, item, count=1):
        """이 유닛의 인벤토리에 아이템 추가"""
        self._check_instantiated()
        item._check_instantiated()
        morld.give_item(self.instance_id, item.instance_id, count)


# ========================================
# CharacterBase — 캐릭터 프레임워크
# ========================================

class CharacterBase(Unit):
    """
    캐릭터 프레임워크 (엔진)

    Rule 기반 텍스트 선택 + 액션 필터링 + Context 빌더.
    시나리오에서 상속하여 콘텐츠(데이터 슬롯 + 오버라이드 메서드) 추가.

    데이터 슬롯 (시나리오에서 채움):
    - DESCRIBE_RULES: 묘사 규칙
    - FOCUS_RULES: Focus 묘사 규칙
    - TALK_RULES: 대화 규칙
    - TALK_TOPICS: 대화 주제 목록
    - EVENT_DIALOGS: 이벤트별 대화 정의
    - CHARACTER_QUESTS: 캐릭터 개인 퀘스트
    """

    type = "male"

    # === 데이터 슬롯 (시나리오에서 오버라이드) ===
    DESCRIBE_RULES = None
    FOCUS_RULES = None
    TALK_TOPICS = None
    TALK_RULES = None
    EVENT_DIALOGS = None
    CHARACTER_QUESTS = []

    # === 프레임워크 메서드 ===

    def _build_context(self):
        """상태 context dict 구축 (Rule 매칭용)

        서브클래스에서 super()._build_context() 후 확장 가능.
        """
        self._check_instantiated()
        context = {"name": self.name}

        info = morld.get_unit_info(self.instance_id)
        if info:
            context["activity"] = info.get("activity", "")
            context["is_traveling"] = info.get("is_moving", False)
            context["region_id"] = info.get("region_id")
            context["location_id"] = info.get("location_id")
            context["location"] = (info.get("region_id"), info.get("location_id"))

        # mood
        mood = morld.get_unit_props_by_type(self.instance_id, "mood")
        context["mood"] = list(mood.keys()) if mood else []

        # 날씨
        time_info = morld.get_time_info()
        if time_info:
            context["weather"] = time_info.get("weather", "")
            context["hour"] = time_info.get("hour", 0)

        # 실내 여부
        if context.get("region_id") is not None and context.get("location_id") is not None:
            loc_info = morld.get_location_info(context["region_id"], context["location_id"])
            context["is_indoor"] = loc_info.get("indoor", False) if loc_info else False

        # 관계 props → context에 병합 (호감, 반발, 복종 등)
        player_id = morld.get_player_id()
        if player_id:
            props = morld.get_unit_props(player_id) or {}
            for key, val in props.items():
                if key.startswith(f"관계:{self.name}:"):
                    rel_type = key.split(":")[-1]
                    context[rel_type] = val

        return context

    def get_describe_text(self):
        """Rule 기반 묘사 텍스트"""
        if not self.DESCRIBE_RULES:
            return f"{self.name}이(가) 있다."
        context = self._build_context()
        result = TextSelector.select(self.DESCRIBE_RULES, context)
        if result is None:
            return f"{self.name}이(가) 있다."
        return TextSelector.format_result(result, context)

    def get_focus_text(self):
        """Rule 기반 Focus 묘사 텍스트"""
        if not self.FOCUS_RULES:
            return f"{self.name}."
        context = self._build_context()
        result = TextSelector.select(self.FOCUS_RULES, context)
        if result is None:
            return f"{self.name}."
        return TextSelector.format_result(result, context)

    def talk(self):
        """대화 프레임워크 — Rule 기반 주제 선택 + 텍스트

        서브클래스에서 오버라이드 가능.
        """
        import ui
        context = self._build_context()

        if self.TALK_TOPICS and isinstance(self.TALK_RULES, dict):
            topic = yield from self._select_talk_topic(context)
            if topic is None:
                return
            rules = self.TALK_RULES.get(topic, [])
        elif self.TALK_RULES and isinstance(self.TALK_RULES, list):
            rules = self.TALK_RULES
        else:
            yield ui.dialog(f"[{self.name}]\n...")
            return

        result = TextSelector.select(rules, context)
        if result is None:
            result = {"pages": ["......"]}

        if isinstance(result, str) and result.startswith("_"):
            method = getattr(self, result, None)
            if method:
                yield from method(context)
                return
            result = {"pages": ["......"]}

        pages = result.get("pages", ["......"])
        yield ui.dialog(pages)

    def _select_talk_topic(self, context):
        """대화 주제 선택 메뉴"""
        import ui
        name = context.get("name", self.name)
        lines = [f"[{name}]", ""]
        for topic in self.TALK_TOPICS:
            lines.append(f"[url=@ret:{topic}]{topic}[/url]")
        lines.append("")
        lines.append("[url=@ret:]뒤로[/url]")
        choice = yield ui.dialog("\n".join(lines), autofill="off")
        if not choice:
            return None
        return choice

    def is_first_meet(self, player_id):
        """첫 만남 여부 판정"""
        props = morld.get_unit_props(player_id) or {}
        progress_key = f"관계:{self.name}:진척도"
        return props.get(progress_key, 0) <= 0

    def mark_first_meet_done(self, player_id):
        """첫 만남 완료 처리"""
        progress_key = f"관계:{self.name}:진척도"
        morld.set_unit_prop(player_id, progress_key, 1)

    @classmethod
    def get_character_quests(cls):
        """캐릭터 개인 퀘스트 목록"""
        return cls.CHARACTER_QUESTS

    def _run_event_dialog(self, event_name, **kwargs):
        """이벤트 다이얼로그 실행 프레임워크"""
        import ui
        if not self.EVENT_DIALOGS:
            return None
        dialog_data = self.EVENT_DIALOGS.get(event_name)
        if dialog_data is None:
            return None
        if isinstance(dialog_data, str) and dialog_data.startswith("_"):
            method = getattr(self, dialog_data, None)
            if method:
                return method(**kwargs)
            return None
        return self._create_event_handler(dialog_data, **kwargs)

    def _create_event_handler(self, dialog_data, **kwargs):
        """이벤트 핸들러 생성"""
        import ui
        pages = dialog_data.get("pages", [])
        if not pages:
            return None
        time_consume = dialog_data.get("time_consume", 0)

        def handler():
            yield ui.dialog(pages)
            if time_consume > 0:
                morld.advance_time_des(time_consume)

        return handler


# ========================================
# ObjectBase — 오브젝트 프레임워크
# ========================================

class ObjectBase(Unit):
    """오브젝트 프레임워크 (가구, 컨테이너, 바닥 등)

    instantiate()는 시나리오에서 오버라이드. 엔진은 공통 속성과 메서드만 제공.
    """

    type = "object"
    put_filter = None
    item_visible = False
    portable = False
    position_x = 0
    position_y = 0

    def sit(self):
        """앉기"""
        import ui
        player_id = morld.get_player_id()
        slot = self._find_empty_slot()
        if slot is None:
            yield ui.dialog(["자리가 없다."])
            return
        success = morld.sit_on(player_id, self.instance_id, slot)
        if success:
            yield ui.dialog([f"{self.name}에 앉았다."])

    def lie_down(self):
        """눕기"""
        import ui
        player_id = morld.get_player_id()
        slot = self._find_empty_slot()
        if slot is None:
            yield ui.dialog(["자리가 없다."])
            return
        success = morld.sit_on(player_id, self.instance_id, slot)
        if success:
            yield ui.dialog([f"{self.name}에 누웠다."])

    def stand_up(self):
        """일어나기"""
        player_id = morld.get_player_id()
        morld.stand_up(player_id)

    def _find_empty_slot(self):
        """빈 좌석 슬롯 찾기"""
        seated_by = morld.get_unit_props_by_type(self.instance_id, "seated_by")
        for slot_name, occupant_id in seated_by.items():
            if occupant_id == -1:
                return slot_name
        return None

    def _count_occupants(self):
        """현재 점유자 수"""
        seated_by = morld.get_unit_props_by_type(self.instance_id, "seated_by")
        return sum(1 for v in seated_by.values() if v != -1)

    def take(self, item_id):
        """오브젝트에서 아이템 가져가기"""
        player_id = morld.get_player_id()
        item_id = int(item_id)
        morld.lost_item(self.instance_id, item_id)
        morld.give_item(player_id, item_id)

    def npc_store_item(self, npc_id, item_unique_id, count=1):
        """NPC → 컨테이너로 아이템 이동"""
        from assets.registry import get_or_create_item_id
        item_id = get_or_create_item_id(item_unique_id)
        if item_id and morld.has_item(npc_id, item_id):
            morld.remove_item(npc_id, item_id, count)
            morld.give_item(self.instance_id, item_id, count)
            return True
        return False

    def npc_take_item(self, npc_id, item_unique_id, count=1):
        """컨테이너 → NPC로 아이템 이동"""
        from assets.registry import get_or_create_item_id
        item_id = get_or_create_item_id(item_unique_id)
        if item_id and morld.has_item(self.instance_id, item_id):
            morld.remove_item(self.instance_id, item_id, count)
            morld.give_item(npc_id, item_id, count)
            return True
        return False

    def get_item_count(self, item_unique_id=None):
        """인벤토리 아이템 수"""
        from assets.registry import get_or_create_item_id
        inv = morld.get_unit_inventory(self.instance_id)
        if not inv:
            return 0
        if item_unique_id:
            item_id = get_or_create_item_id(item_unique_id)
            return inv.get(str(item_id), 0) if item_id else 0
        return sum(inv.values())

    def get_category_item_count(self, category):
        """카테고리별 아이템 수"""
        from assets.registry import get_unique_id, get_item_class
        inv = morld.get_unit_inventory(self.instance_id)
        if not inv:
            return 0
        count = 0
        for item_id_str in inv:
            uid = get_unique_id(int(item_id_str))
            if uid:
                item_cls = get_item_class(uid)
                if item_cls and getattr(item_cls, 'category', None) == category:
                    count += inv[item_id_str]
        return count


# ========================================
# ItemBase — 아이템 프레임워크
# ========================================

class ItemBase(Asset):
    """아이템 프레임워크

    instantiate()는 시나리오에서 오버라이드. 엔진은 공통 속성만 제공.
    """

    passive_props = None
    equip_props = None
    action_props = {"put": 1}
    value = 0
    owner = None
    category = None
    durability = None


# ========================================
# LocationBase — 장소 프레임워크
# ========================================

class LocationBase(Asset):
    """장소 프레임워크

    instantiate(), add_ground(), add_object()는 시나리오에서 오버라이드.
    엔진은 공통 속성과 get_describe_text()만 제공.
    """

    is_indoor = True
    stay_duration = 0
    describe_text = None
    owner = None
    ground_type = None
    geometry = "line"
    length = 0

    def __init__(self):
        super().__init__()
        self.location_id = None
        self.region_id = None
        self.ground = None

    def get_describe_text(self):
        """시간/날씨 태그 기반 장소 묘사"""
        if not self.describe_text:
            return ""
        self._check_instantiated()
        time_tags = morld.get_time_tags() if hasattr(morld, 'get_time_tags') else []
        return select_text(self.describe_text, time_tags)


def reset():
    """모듈 상태 초기화 — pi-world reset 계약 (가변 전역 없음, 규약 준수용)"""
    pass
