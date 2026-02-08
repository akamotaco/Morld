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
#   loc = BackYard()                           # 인스턴스 생성
#   loc.instantiate(location_id, REGION_ID)    # morld에 등록 (location_id는 수동 지정)
#   loc.ground.add_item(herb)                  # 바닥에 아이템 추가
#
#   npc = Sera()
#   npc_id = morld.create_id("unit")           # ID 자동 생성
#   npc.instantiate(npc_id, REGION_ID, loc_id)
#
# 텍스트 시스템:
#   - get_describe_text(): 장소에 있을 때 보이는 묘사 (Character, Location)
#   - get_focus_text(): Focus 상태(클릭)일 때 보이는 묘사 (Character, Object, Item)
#   - 각 클래스에서 메서드를 오버라이드하여 구현
#
# 액션 시스템:
#   - actions 리스트에 "액션@context" 형식으로 정의
#   - @context: 아이템 위치에 따라 액션 표시 여부 결정 (필터링)
#     예) "take@container" → 컨테이너에 있을 때만 "가져가기" 표시
#         "call:use:마시기@inventory" → 인벤토리에 있을 때만 표시
#   - call: 패턴과 조합 가능: "call:메서드명:표시명@context"

import morld
import ui
from typing import Optional


class TextSelector:
    """
    조건 기반 텍스트 선택기

    규칙 리스트에서 첫 번째 매칭되는 결과를 반환합니다.
    규칙은 (조건 dict, 결과) 튜플의 리스트입니다.

    조건 매칭 규칙:
    - 빈 dict {}: 항상 매칭 (기본값)
    - 문자열 값: 정확히 일치 (activity == "사냥")
    - 숫자 값: >= 비교 (호감 >= 50)
    - 리스트 context에 문자열 조건: in 체크 (mood에 "기쁨" 포함)

    사용 예:
        RULES = [
            ({"activity": "사냥", "호감": 50}, "같이 사냥할래?"),
            ({"activity": "사냥"}, "조용히 해."),
            ({"mood": "기쁨"}, "기분 좋아 보인다."),
            ({}, "......"),  # 기본값
        ]
        result = TextSelector.select(RULES, context)
    """

    @staticmethod
    def select(rules: list, context: dict):
        """
        규칙 리스트에서 첫 번째 매칭 결과 반환

        Args:
            rules: [(conditions, result), ...] 형식의 규칙 리스트
            context: 현재 상태 dict (activity, mood, 호감, weather 등)

        Returns:
            첫 번째 매칭된 result, 없으면 None
        """
        for conditions, result in rules:
            if TextSelector.match(conditions, context):
                return result
        return None

    @staticmethod
    def match(conditions: dict, context: dict) -> bool:
        """
        모든 조건이 충족되는지 확인

        Args:
            conditions: 조건 dict (빈 dict면 항상 True)
            context: 현재 상태 dict

        Returns:
            모든 조건 충족 시 True
        """
        if not conditions:
            return True  # 빈 조건은 항상 매칭

        for key, expected in conditions.items():
            actual = context.get(key)

            # actual이 리스트인 경우 (mood 등): expected가 리스트에 포함되어야 함
            if isinstance(actual, list):
                if expected not in actual:
                    return False
            # expected가 숫자인 경우: >= 비교
            elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                if actual < expected:
                    return False
            # 그 외: 정확히 일치
            elif actual != expected:
                return False

        return True

    @staticmethod
    def format_result(result, context: dict):
        """
        result가 문자열이면 context로 포맷팅

        Args:
            result: 텍스트 또는 dict
            context: 포맷팅용 context (name 등)

        Returns:
            포맷팅된 결과
        """
        if isinstance(result, str):
            try:
                return result.format(**context)
            except KeyError:
                return result
        return result


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
    - owner: 소유자 unique_id (예: "sera") - None이면 공용

    인스턴스 속성:
    - region_id, location_id: 배치 위치
    """

    type: str = "object"
    mood: list = None
    props: dict = None
    owner: str = None

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
            yield ui.dialog(f"[b]{self.name}[/b]\n\n속성이 없습니다.")
            return
        lines = [f"[b]{self.name}[/b]\n"]
        for key, value in props.items():
            lines.append(f"  {key}: {value}")
        yield ui.dialog("\n".join(lines))

    def debug_self_props(self):
        """플레이어 자신의 속성 확인 (거울 등에서 사용)"""
        player_id = morld.get_player_id()
        props = morld.get_unit_props(player_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "???") if player_info else "???"

        if not props:
            yield ui.dialog(f"[b]{player_name}[/b]\n\n아직 알 수 있는 것이 없다.")
            return

        lines = [f"[b]{player_name}[/b]\n"]
        for key, value in props.items():
            lines.append(f"  {key}: {value}")
        yield ui.dialog("\n".join(lines))


class Character(Unit):
    """
    캐릭터 클래스 (NPC, 플레이어)

    Rule 기반 텍스트 선택 시스템:
    - DESCRIBE_RULES: 장소에서 보이는 묘사 규칙
    - FOCUS_RULES: 클릭했을 때 상세 묘사 규칙
    - TALK_RULES: 대화 규칙 (dict 또는 메서드명 문자열)
    - TALK_TOPICS: 대화 주제 목록 (있으면 주제 선택 메뉴 표시)

    규칙 형식:
        RULES = [
            ({"조건키": 조건값, ...}, 결과),
            ...
            ({}, 기본값),  # 빈 조건 = 항상 매칭
        ]

    조건 매칭:
    - 문자열: 정확히 일치 (activity == "사냥")
    - 숫자: >= 비교 (호감 >= 50)
    - 리스트 context: in 체크 (mood에 "기쁨" 포함)
    - bool: 정확히 일치 (is_traveling == True)

    TALK_RULES 결과 형식:
    - {"pages": ["대사1", "대사2"]}: 간단한 대화
    - "_메서드명": 복잡한 대화 처리 메서드로 위임

    TALK_TOPICS + TALK_RULES (주제 기반 대화):
        TALK_TOPICS = ["잡담", "본인에 대해", "낚시 방법"]
        TALK_RULES = {
            "잡담": [
                ({"mood": "기쁨"}, {"pages": ["좋은 날이야."]}),
                ({}, {"pages": ["뭐야?"]}),
            ],
            "본인에 대해": [
                ({"호감": 50}, {"pages": ["내 이름은..."]}),
                ({}, {"pages": ["왜 궁금해?"]}),
            ],
        }

    context 키:
    - name: 캐릭터 이름
    - activity: 현재 활동 (Job.Name)
    - mood: 감정 상태 리스트
    - is_traveling: 이동 중 여부
    - region_id, location_id: 현재 위치
    - location: (region_id, location_id) 튜플
    - weather: 현재 날씨
    - is_indoor: 실내 여부
    - 호감: 호감도 (props에서)
    """

    type: str = "male"

    # Rule 기반 텍스트 선택 (서브클래스에서 정의)
    DESCRIBE_RULES: list = None
    FOCUS_RULES: list = None
    TALK_TOPICS: list = None  # 대화 주제 목록 (있으면 주제 선택 메뉴 표시)
    TALK_RULES = None  # list (기존 방식) 또는 dict (주제별 규칙)

    # ========================================
    # 연애 반응 시스템
    # ========================================
    # 서브클래스에서 오버라이드하여 캐릭터별 반응 정의
    # 형식: "action:timing" → [(conditions, [texts]), ...]
    #
    # 예시:
    #   ROMANCE_REACTIONS = {
    #       "hug:start": [
    #           ({"애정": 50}, ["...안아줘...", "...이대로..."]),
    #           ({}, ["......", "...뭐냐."]),
    #       ],
    #       "hug:during": [
    #           ({}, ["상대가 가만히 있다."]),
    #       ],
    #   }
    ROMANCE_REACTIONS: dict = {
        # 토글 액션 (ON 상태 진행 중 묘사)
        "hug:during": [({}, ["상대가 당신을 안고 있다."])],
        "deep_kiss:during": [({}, ["상대와 깊은 키스를 나누고 있다."])],
        "breast_touch:during": [({}, ["상대의 가슴에 손을 대고 있다."])],
        # 즉시 액션
        "head_pat:start": [({}, ["상대의 머리를 쓰다듬는다."])],
        "cheek_caress:start": [({}, ["상대의 볼을 어루만진다."])],
        "cheek_pinch:start": [({}, ["상대의 볼을 꼬집는다."])],
        "ear_touch:start": [({}, ["상대의 귀를 만진다."])],
        "french_kiss:start": [({}, ["상대와 프렌치 키스를 한다."])],
        "butt_caress:start": [({}, ["상대의 엉덩이를 쓰다듬는다."])],
        # 절정
        "ecstasy:start": [({}, ["......!"])],
    }

    # ========================================
    # 은신 성공 반응 시스템
    # ========================================
    # 서브클래스에서 오버라이드하여 캐릭터별 은신 성공 시 반응 정의
    #
    # STEALTH_REACTIONS: 은신 성공 시 반응 및 파라미터 변화
    #   {
    #       "text": [({조건}, [대사들]), ...],  # 조건부 대사
    #       "effects": {                         # 파라미터 변화
    #           "성욕": 5,                       # 스릴에 더 흥분 (세라 등)
    #           "애정": -1,                      # 부끄러워서 애정 감소 (밀라 등)
    #       },
    #   }
    #
    # 예시 (세라):
    #   STEALTH_REACTIONS = {
    #       "text": [
    #           ({"성욕": 50}, ["...위험했어...", "...(숨을 몰아쉰다)"]),
    #           ({}, ["......", "...조심해."]),
    #       ],
    #       "effects": {"성욕": 5},  # 스릴에 더 흥분
    #   }

    STEALTH_REACTIONS: dict = None

    # EQUIP_CHANGE_REACTIONS: 플레이어 장비 변경 시 반응 텍스트
    #   EQUIP_CHANGE_REACTIONS = {
    #       "equip": "세라가 무기를 힐끗 보더니 고개를 끄덕인다.",
    #       "unequip": "세라가 빈 손을 보고 살짝 고개를 갸웃한다.",
    #   }

    EQUIP_CHANGE_REACTIONS: dict = None

    # PROGRESS_DIALOGS: 진척도별 대화 (일회성 플래그)
    #   PROGRESS_DIALOGS = {
    #       1: {"fallback": ["......", "...무슨 일이야?"], "dialog": ["......", "...내 이름은 세라.", ...]},
    #       2: {"fallback": [...], "dialog": [...]},
    #       3: {"fallback": [...], "dialog": [...]},
    #   }
    # dialog 내 "{player_name}" 은 자동 치환됨

    PROGRESS_DIALOGS: dict = None

    # FRIENDLY_TALK_CONFIG: 친밀도별 대화 (진척도 증가)
    #   FRIENDLY_TALK_CONFIG = {
    #       "high": {"dialog": [...], "progress_cap": 3},
    #       "mid":  {"dialog": [...], "progress_cap": 3},
    #   }

    FRIENDLY_TALK_CONFIG: dict = None

    # ROOM_PRIVACY_CONFIG: 수면/목욕 시 프라이버시 이벤트
    #   ROOM_PRIVACY_CONFIG = {
    #       "수면": {
    #           "threshold": 50,
    #           "high": {"dialog": ["[세라]", "..."]},
    #           "low":  {"dialog": ["[세라]", "..."], "teleport": 1, "after": "세라의 방에서 나왔다."},
    #       },
    #       "목욕": {...},
    #   }

    ROOM_PRIVACY_CONFIG: dict = None

    def get_stealth_success_reaction(self, player_id: int) -> Optional[str]:
        """
        은신 성공 시 반응 텍스트 반환

        Args:
            player_id: 플레이어 유닛 ID

        Returns:
            반응 텍스트 또는 None
        """
        if not self.STEALTH_REACTIONS:
            return None

        text_rules = self.STEALTH_REACTIONS.get("text")
        if not text_rules:
            return None

        # context 구성
        props = morld.get_unit_props(self.instance_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        context = {
            "성욕": props.get("상태:성욕", 0) if props else 0,
            "호감": props.get(f"관계:{player_name}:호감", 0) if props else 0,
            "애정": props.get(f"관계:{player_name}:애정", 0) if props else 0,
        }

        # 규칙 매칭
        import random
        for conditions, texts in text_rules:
            if TextSelector.match(conditions, context):
                if isinstance(texts, list):
                    return random.choice(texts)
                return texts

        return None

    def apply_stealth_success_effects(self, player_id: int):
        """
        은신 성공 시 파라미터 변화 적용

        Args:
            player_id: 플레이어 유닛 ID

        Returns:
            적용된 효과 dict 또는 None
        """
        if not self.STEALTH_REACTIONS:
            return None

        effects = self.STEALTH_REACTIONS.get("effects")
        if not effects:
            return None

        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        applied = {}
        for stat, value in effects.items():
            if stat in ("성욕", "성적절정"):
                prop_key = f"상태:{stat}"
            else:
                prop_key = f"관계:{player_name}:{stat}"

            morld.modify_prop(self.instance_id, prop_key, value)
            applied[stat] = value

        return applied

    # ========================================
    # 상태 기반 액션 필터링 시스템
    # ========================================
    # NPC의 현재 상태(activity, mood 등)에 따라 가능한 액션을 동적으로 필터링
    #
    # ACTION_AVAILABILITY: 상태별 허용/차단 액션 정의
    #   {
    #       "수면": {
    #           "allowed": ["talk", "debug_props", "wake_up"],  # 허용 액션만 표시
    #           "blocked_message": "자고 있다...",  # 차단 시 메시지 (선택)
    #       },
    #       "식사": {
    #           "blocked": ["romance", "date"],  # 차단 액션만 숨김
    #       },
    #   }
    #
    # 우선순위: allowed > blocked
    # - allowed가 정의되면 해당 액션만 표시 (화이트리스트)
    # - blocked가 정의되면 해당 액션만 숨김 (블랙리스트)

    ACTION_AVAILABILITY: dict = {
        # 기본 수면 상태 처리 (모든 캐릭터 공통)
        "수면": {
            "allowed": ["talk", "debug_props", "wake_up"],
            "blocked_message": "자고 있다...",
        },
    }

    def get_available_actions(self) -> list:
        """
        현재 상태에서 사용 가능한 액션 목록 반환

        NPC의 activity, mood 등을 기반으로 actions 리스트를 필터링합니다.
        ACTION_AVAILABILITY에 정의된 규칙에 따라 숨김 처리됩니다.

        Returns:
            필터링된 액션 문자열 리스트
        """
        if not self.actions:
            return []

        # 현재 상태 조회
        info = morld.get_unit_info(self.instance_id)
        if not info:
            return list(self.actions)

        activity = info.get("activity")
        mood = info.get("mood", [])

        # ACTION_AVAILABILITY에서 현재 상태에 맞는 규칙 찾기
        availability = getattr(self, 'ACTION_AVAILABILITY', {})
        rules = None

        # activity 기반 규칙 체크
        if activity and activity in availability:
            rules = availability[activity]

        # mood 기반 규칙 체크 (activity 규칙이 없을 때)
        if rules is None:
            for m in mood:
                if m in availability:
                    rules = availability[m]
                    break

        # 규칙이 없으면 모든 액션 허용
        if rules is None:
            return self._apply_dynamic_action_labels(list(self.actions), info)

        # 필터링 적용
        allowed = rules.get("allowed")
        blocked = rules.get("blocked")

        result = []
        for action in self.actions:
            # 액션 이름 추출 (call:method:label → method)
            action_name = self._extract_action_name(action)

            if allowed is not None:
                # 화이트리스트 모드: allowed에 있는 액션만 표시
                if action_name in allowed:
                    result.append(action)
            elif blocked is not None:
                # 블랙리스트 모드: blocked에 없는 액션만 표시
                if action_name not in blocked:
                    result.append(action)
            else:
                result.append(action)

        return self._apply_dynamic_action_labels(result, info)

    def _apply_dynamic_action_labels(self, actions, info):
        """동적 라벨 적용 (작업지시에 현재 활동 표시 등)"""
        activity = info.get("activity", "") if info else ""
        if not activity:
            return actions
        updated = []
        for action in actions:
            if "debug_work_order" in action:
                updated.append(f"call:debug_work_order:(디버그) 작업지시 [{activity}]#")
            else:
                updated.append(action)
        return updated

    def _extract_action_name(self, action: str) -> str:
        """
        액션 문자열에서 액션 이름 추출

        Examples:
            "call:talk:대화" → "talk"
            "call:sit:front:앉기" → "sit"
            "call:romance:스킨십#" → "romance"
            "take@container" → "take"
            "rest" → "rest"
        """
        # '#' 마커 제거
        if action.endswith("#"):
            action = action[:-1]

        # '@' context 제거
        if "@" in action:
            action = action.split("@")[0]

        # call: 패턴 처리
        if action.startswith("call:"):
            parts = action.split(":")
            if len(parts) >= 2:
                return parts[1]  # method 이름

        return action

    def get_action_blocked_message(self) -> str:
        """
        현재 상태의 차단 메시지 반환

        Returns:
            차단 메시지 또는 None
        """
        info = morld.get_unit_info(self.instance_id)
        if not info:
            return None

        activity = info.get("activity")
        availability = getattr(self, 'ACTION_AVAILABILITY', {})

        if activity and activity in availability:
            return availability[activity].get("blocked_message")

        return None

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
            self.unique_id,  # unique_id 전달
            None,            # action_props
            self.owner       # owner 전달
        )

        # Prop 설정
        if self.props:
            morld.set_unit_props(instance_id, self.props)

        # 인스턴스 캐시 등록 (describe_text/focus_text 조회용)
        from assets.characters import register_instance
        register_instance(instance_id, self)

    # ========================================
    # Context 빌드
    # ========================================

    def _build_context(self) -> dict:
        """
        현재 상태를 context dict로 변환

        서브클래스에서 오버라이드하여 추가 context 제공 가능.
        """
        info = morld.get_unit_info(self.instance_id)
        if not info:
            return {"name": self.name}

        # 기본 정보
        context = {
            "name": info.get("name", self.name),
            "activity": info.get("activity"),
            "mood": info.get("mood", []),
            "is_traveling": info.get("is_traveling", False),
            "region_id": info.get("region_id"),
            "location_id": info.get("location_id"),
        }

        # 위치 튜플 (조건에서 사용)
        context["location"] = (context["region_id"], context["location_id"])

        # Props에서 호감도, 진척도 등 가져오기
        props = morld.get_unit_props(self.instance_id)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        if props:
            context["호감"] = props.get(f"관계:{player_name}:호감", 0)
            context["진척도"] = props.get(f"관계:{player_name}:진척도", 0)
            # 도구 분실 플래그
            for key, value in props.items():
                if key.startswith("도구분실:"):
                    context[key] = value

        # 위치 정보에서 날씨, 실내 여부 가져오기
        location_info = morld.get_location_info(
            context["region_id"],
            context["location_id"]
        )
        if location_info:
            context["weather"] = location_info.get("weather")
            context["is_indoor"] = location_info.get("is_indoor", True)

        # 데이트 상태 확인
        from date import is_on_date, get_date_partner
        if is_on_date(player_id) and get_date_partner(player_id) == self.instance_id:
            context["on_date"] = True
        else:
            context["on_date"] = False

        return context

    # ========================================
    # Rule 기반 텍스트 선택
    # ========================================

    def get_describe_text(self) -> str:
        """
        Describe 텍스트 - Rule 기반

        DESCRIBE_RULES가 정의되어 있으면 규칙 매칭,
        없으면 빈 문자열 반환.
        """
        if not self.DESCRIBE_RULES:
            return ""

        context = self._build_context()
        text = TextSelector.select(self.DESCRIBE_RULES, context)
        if text:
            return TextSelector.format_result(text, context)

        # 기본값: 이동 중이면 패턴화된 텍스트
        if context.get("is_traveling"):
            return f"{context['name']}(이)가 어딘가로 향하고 있다."
        return ""

    def get_focus_text(self) -> str:
        """
        Focus 텍스트 - Rule 기반

        FOCUS_RULES가 정의되어 있으면 규칙 매칭,
        없으면 빈 문자열 반환.
        """
        if not self.FOCUS_RULES:
            return ""

        context = self._build_context()
        text = TextSelector.select(self.FOCUS_RULES, context)
        if text:
            return TextSelector.format_result(text, context)
        return ""

    # ========================================
    # 연애 반응 메서드
    # ========================================

    def get_romance_reaction(self, action_id: str, timing: str = "during") -> Optional[str]:
        """
        연애 액션에 대한 반응 텍스트 반환

        Args:
            action_id: 액션 ID ("hug", "deep_kiss" 등)
            timing: 타이밍 ("start", "during")

        Returns:
            반응 텍스트 또는 None (랜덤 선택)

        ROMANCE_REACTIONS 구조:
            {
                "action:timing": [
                    (conditions, [texts]),
                    ({}, [default_texts]),  # 기본값
                ],
            }

        예시:
            ROMANCE_REACTIONS = {
                "hug:start": [
                    ({"애정": 50}, ["...안아줘...", "...이대로..."]),
                    ({}, ["......", "...뭐냐."]),
                ],
                "hug:during": [
                    ({"성욕": 50}, ["세라가 숨을 몰아쉬고 있다."]),
                    ({}, ["세라가 가만히 있다."]),
                ],
            }
        """
        import random

        reactions = getattr(self, 'ROMANCE_REACTIONS', {})
        if not reactions:
            return None

        # 새 구조: "action:timing" 키
        key = f"{action_id}:{timing}"
        rules = reactions.get(key)

        if not rules:
            return None

        # 조건 매칭 및 텍스트 선택
        props = morld.get_unit_props(self.instance_id)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get('name', '주인공') if player_info else '주인공'

        candidates = []
        for item in rules:
            if isinstance(item, tuple) and len(item) == 2:
                condition, texts = item
                if self._check_reaction_condition(condition, props, player_name):
                    if isinstance(texts, list):
                        candidates.extend(texts)
                    else:
                        candidates.append(texts)

        if not candidates:
            return None

        return random.choice(candidates)

    def _check_reaction_condition(self, condition: dict, props: dict, player_name: str) -> bool:
        """
        리액션 조건 체크 (ROMANCE_REACTIONS, STEALTH_REACTIONS 등에서 공통 사용)

        조건 키 매핑:
        - "호감", "애정" → "관계:{player_name}:{key}"
        - "성욕", "성적절정" → "상태:{key}"
        - 그 외 → 그대로 사용
        """
        if not condition:
            return True

        for key, required_value in condition.items():
            if key in ("호감", "애정"):
                prop_key = f"관계:{player_name}:{key}"
            elif key in ("성욕", "성적절정"):
                prop_key = f"상태:{key}"
            else:
                prop_key = key

            actual_value = props.get(prop_key, 0) if props else 0
            if actual_value < required_value:
                return False

        return True

    def romance(self):
        """연애 모드 시작"""
        self._check_instantiated()
        from romance import start_romance
        player_id = morld.get_player_id()
        yield from start_romance(player_id, self.instance_id)

    def date(self):
        """데이트 요청"""
        self._check_instantiated()
        from date import request_date
        player_id = morld.get_player_id()
        yield from request_date(player_id, self.instance_id)

    # ========================================
    # 깨우기 시스템
    # ========================================

    def wake_up(self):
        """
        수면 중인 캐릭터 깨우기

        호감도에 따라 성공/실패 확률이 달라집니다.
        실패 시 호감도가 감소합니다.

        서브클래스에서 get_wake_up_reaction()을 오버라이드하여
        캐릭터별 반응을 정의할 수 있습니다.
        """
        self._check_instantiated()
        import random

        # 현재 상태 확인
        info = morld.get_unit_info(self.instance_id)
        activity = info.get("activity") if info else None

        if activity != "수면":
            yield ui.dialog(f"[{self.name}]\n\"...무슨 일이야?\"")
            return

        # 호감도 기반 성공 확률 계산
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        props = morld.get_unit_props(self.instance_id)
        affection = props.get(f"관계:{player_name}:호감", 0) if props else 0

        # 기본 성공률 30%, 호감도 1당 +0.5% (최대 80%)
        success_chance = min(0.3 + affection * 0.005, 0.8)

        # 성공/실패 판정
        if random.random() < success_chance:
            # 성공: 깨어남
            reaction = self.get_wake_up_success_reaction()
            yield ui.dialog(reaction)
            # activity 변경은 NPC 스케줄에 맡김 (여기서 직접 변경하지 않음)
        else:
            # 실패: 계속 자고, 호감도 감소
            affection_loss = -3
            morld.modify_prop(self.instance_id, f"관계:{player_name}:호감", affection_loss)
            reaction = self.get_wake_up_fail_reaction()
            yield ui.dialog(reaction)

    def get_wake_up_success_reaction(self) -> str:
        """깨우기 성공 반응 - 서브클래스에서 오버라이드"""
        return f"[{self.name}]\n\"...으응... 뭐야...\"\n\n{self.name}(이)가 졸린 눈을 비비며 일어난다."

    def get_wake_up_fail_reaction(self) -> str:
        """깨우기 실패 반응 - 서브클래스에서 오버라이드"""
        return f"[{self.name}]\n\"...으응...\"\n\n{self.name}(이)가 돌아눕는다. 귀찮아하는 것 같다."

    def end_date(self):
        """데이트 종료"""
        self._check_instantiated()
        from date import end_date
        player_id = morld.get_player_id()
        yield from end_date(player_id)

    # ========================================
    # 데이트 반응 메서드 (서브클래스에서 오버라이드)
    # ========================================

    def get_date_accept_text(self):
        """데이트 수락 텍스트 - 서브클래스에서 오버라이드"""
        return f"[{self.name}]\n\"좋아.\""

    def get_date_reject_text(self, reason):
        """데이트 거절 텍스트 - 서브클래스에서 오버라이드"""
        return f"[{self.name}]\n\"{reason}\""

    def get_date_end_text(self):
        """데이트 종료 텍스트 - 서브클래스에서 오버라이드"""
        return f"[{self.name}]\n\"...또 보자.\""

    def get_date_action_reaction(self, action_id):
        """데이트 중 애정 표현 반응 - 서브클래스에서 오버라이드"""
        return None

    def get_date_action_reject(self, action_id):
        """데이트 중 애정 표현 거부 반응 - 서브클래스에서 오버라이드"""
        return f"[{self.name}]\n\"...아직은...\""

    # ========================================
    # 데이트 외 애정 표현 반응 (서브클래스에서 오버라이드)
    # ========================================

    def get_casual_action_reaction(self, action_id):
        """데이트 외 애정 표현 반응 - 서브클래스에서 오버라이드"""
        return None

    def get_casual_action_reject(self, action_id):
        """데이트 외 애정 표현 거부 반응 - 서브클래스에서 오버라이드"""
        return f"[{self.name}]\n\"...뭐 하는 거야?\""

    # ========================================
    # NPC 주도 스킨십 시스템
    # ========================================
    # 서브클래스에서 오버라이드하여 캐릭터별 설정 정의
    #
    # INITIATIVE_CONFIG: 트리거 조건 설정
    #   {
    #       "arousal_threshold": 70,    # 성욕 임계값
    #       "affection_threshold": 60,  # 호감도 임계값
    #       "cooldown_millis": 480,    # 쿨다운 (분)
    #   }
    #
    # NPC_INITIATIVE_ACTIONS: 조건별 액션 시퀀스
    #   [
    #       ({"성욕": 90, "호감": 50}, [
    #           {"action": "hug", "duration": 10},
    #           {"action": "deep_kiss", "duration": 15},
    #       ]),
    #       ({}, [  # 기본값
    #           {"action": "hug", "duration": 15},
    #       ]),
    #   ]
    #
    # INITIATIVE_REACTIONS: 주도 중 반응 텍스트
    #   {
    #       "start": [({}, ["...가만히 있어."])],
    #       "during_hug": [({}, ["강하게 안고 있다."])],
    #       "escape_fail": [({}, ["...도망가려고?"])],
    #       "satisfied": [({}, ["...끝이다."])],
    #   }

    INITIATIVE_CONFIG: dict = None
    NPC_INITIATIVE_ACTIONS: list = None
    INITIATIVE_REACTIONS: dict = None

    def should_initiate_skinship(self, player_id: int) -> bool:
        """
        NPC 주도 스킨십 트리거 여부 판단

        Args:
            player_id: 플레이어 유닛 ID

        Returns:
            True면 NPC 주도 스킨십 시작
        """
        if not self.INITIATIVE_CONFIG:
            return False

        # 쿨다운 체크
        props = morld.get_unit_props(self.instance_id)
        if props:
            last_initiative = props.get("상태:마지막_주도_시각", -99999)
            cooldown = self.INITIATIVE_CONFIG.get("cooldown_millis", 480 * 60_000)
            current_time = morld.get_game_time()
            if current_time - last_initiative < cooldown:
                return False

        # 성욕 체크
        arousal_threshold = self.INITIATIVE_CONFIG.get("arousal_threshold", 70)
        arousal = props.get("상태:성욕", 0) if props else 0
        if arousal < arousal_threshold:
            return False

        # 호감도 체크
        affection_threshold = self.INITIATIVE_CONFIG.get("affection_threshold", 60)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"
        affection = props.get(f"관계:{player_name}:호감", 0) if props else 0
        if affection < affection_threshold:
            return False

        # 단둘이 체크 (플레이어와 NPC 둘만 있어야 함)
        npc_loc = morld.get_unit_location(self.instance_id)
        if npc_loc:
            units_at_loc = morld.get_units_at_location(npc_loc[0], npc_loc[1])
            if units_at_loc:
                # 플레이어와 자신 외에 다른 캐릭터가 있으면 시작 안 함
                other_chars = [u for u in units_at_loc if u != player_id and u != self.instance_id]
                if other_chars:
                    return False

        return True

    def get_initiative_actions(self, player_id: int) -> list:
        """
        NPC 주도 액션 시퀀스 선택

        Args:
            player_id: 플레이어 유닛 ID

        Returns:
            액션 dict 리스트 [{"action": "hug", "duration": 10}, ...]
        """
        if not self.NPC_INITIATIVE_ACTIONS:
            return [{"action": "hug", "duration": 10}]  # 기본값

        # context 구성
        props = morld.get_unit_props(self.instance_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        context = {
            "성욕": props.get("상태:성욕", 0) if props else 0,
            "호감": props.get(f"관계:{player_name}:호감", 0) if props else 0,
        }

        # 조건 매칭
        for conditions, actions in self.NPC_INITIATIVE_ACTIONS:
            if TextSelector.match(conditions, context):
                return list(actions)  # 복사본 반환

        # 기본값
        return [{"action": "hug", "duration": 10}]

    def get_initiative_reaction(self, timing: str) -> str:
        """
        NPC 주도 중 반응 텍스트 반환

        Args:
            timing: "start", "during_hug", "escape_fail", "satisfied" 등

        Returns:
            반응 텍스트 또는 None
        """
        if not self.INITIATIVE_REACTIONS:
            return None

        rules = self.INITIATIVE_REACTIONS.get(timing)
        if not rules:
            return None

        # context 구성 (간단히)
        context = {}

        # 규칙에서 선택
        import random
        for conditions, texts in rules:
            if TextSelector.match(conditions, context):
                if isinstance(texts, list):
                    return random.choice(texts)
                return texts

        return None

    def mark_initiative_cooldown(self):
        """NPC 주도 쿨다운 시각 기록"""
        current_time = morld.get_game_time()
        morld.set_unit_prop(self.instance_id, "상태:마지막_주도_시각", current_time)

    # ========================================
    # NPC 주도 행위 필터링 시스템
    # ========================================
    # 서브클래스에서 오버라이드하여 캐릭터별/진척도별 행위 제한
    #
    # INITIATIVE_ACTION_FILTERS: 조건별 허용 액션 목록
    #   [
    #       ({"애정": 80}, ["hug", "deep_kiss", "breast_touch"]),  # 애정 80 이상: 모든 행위
    #       ({"애정": 50}, ["hug", "deep_kiss"]),                  # 애정 50 이상: 키스까지
    #       ({}, ["hug"]),                                         # 기본: 포옹만
    #   ]
    #
    # 조건은 위에서부터 순서대로 체크, 첫 번째 매칭 사용

    INITIATIVE_ACTION_FILTERS: list = None

    def get_allowed_initiative_actions(self, player_id: int) -> list:
        """
        NPC 주도 시 허용되는 액션 목록 반환

        캐릭터별/진척도별로 NPC가 선택할 수 있는 행위를 제한합니다.
        INITIATIVE_ACTION_FILTERS가 정의되지 않으면 모든 행위가 허용됩니다.

        Args:
            player_id: 플레이어 유닛 ID

        Returns:
            허용되는 액션 ID 리스트 (예: ["hug", "deep_kiss"])
            None이면 제한 없음 (모든 행위 허용)
        """
        if not self.INITIATIVE_ACTION_FILTERS:
            return None  # 제한 없음

        # context 구성
        props = morld.get_unit_props(self.instance_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        context = {
            "성욕": props.get("상태:성욕", 0) if props else 0,
            "호감": props.get(f"관계:{player_name}:호감", 0) if props else 0,
            "애정": props.get(f"관계:{player_name}:애정", 0) if props else 0,
        }

        # 조건 매칭
        for conditions, allowed_actions in self.INITIATIVE_ACTION_FILTERS:
            if TextSelector.match(conditions, context):
                return list(allowed_actions)

        # 기본값: 제한 없음
        return None

    # ========================================
    # 애정 표현 메서드 (데이트 중/외 자동 분기)
    # ========================================

    def hold_hands(self):
        """손 잡기 - 데이트 중/외 자동 분기"""
        self._check_instantiated()
        from date import is_on_date, do_date_action, do_casual_action
        player_id = morld.get_player_id()
        if is_on_date(player_id):
            yield from do_date_action(player_id, self.instance_id, "hold_hands")
        else:
            yield from do_casual_action(player_id, self.instance_id, "hold_hands")

    def date_hug(self):
        """안아주기 - 데이트 중/외 자동 분기"""
        self._check_instantiated()
        from date import is_on_date, do_date_action, do_casual_action
        player_id = morld.get_player_id()
        if is_on_date(player_id):
            yield from do_date_action(player_id, self.instance_id, "hug")
        else:
            yield from do_casual_action(player_id, self.instance_id, "hug")

    def date_kiss(self):
        """키스 - 데이트 중/외 자동 분기"""
        self._check_instantiated()
        from date import is_on_date, do_date_action, do_casual_action
        player_id = morld.get_player_id()
        if is_on_date(player_id):
            yield from do_date_action(player_id, self.instance_id, "kiss")
        else:
            yield from do_casual_action(player_id, self.instance_id, "kiss")

    def talk(self):
        """
        대화 - 주제 선택 + Rule 기반 (메서드 위임 지원)

        TALK_TOPICS가 정의되어 있으면:
        1. 주제 선택 메뉴 표시
        2. 선택한 주제의 TALK_RULES[주제] 규칙 적용

        TALK_TOPICS가 없고 TALK_RULES가 list면:
        - 기존 방식 (단일 규칙 리스트)

        규칙 결과 처리:
        - dict 결과: {"pages": [...]} 형태의 간단한 대사
        - str 결과: "_"로 시작하는 메서드명 → 복잡한 대화 처리
        """
        context = self._build_context()

        # TALK_TOPICS가 있으면 주제 선택 메뉴 표시
        if self.TALK_TOPICS and isinstance(self.TALK_RULES, dict):
            topic = yield from self._select_talk_topic(context)
            if topic is None:
                return  # 뒤로가기
            rules = self.TALK_RULES.get(topic, [])
        elif self.TALK_RULES and isinstance(self.TALK_RULES, list):
            # 기존 방식: 단일 규칙 리스트
            rules = self.TALK_RULES
        else:
            yield ui.dialog(f"[{self.name}]\n...")
            return

        # 규칙 매칭
        result = TextSelector.select(rules, context)

        if result is None:
            result = {"pages": ["......"]}

        # 문자열이면 메서드명으로 위임
        if isinstance(result, str) and result.startswith("_"):
            method = getattr(self, result, None)
            if method:
                yield from method(context)
                return
            # 메서드를 찾지 못하면 기본 대사
            result = {"pages": ["......"]}

        # dict면 간단한 대사
        # name = context.get("name", self.name)
        # pages = [f"[{name}]"] + result.get("pages", ["......"])
        pages = result.get("pages", ["......"])
        yield ui.dialog(pages)

    def _select_talk_topic(self, context):
        """
        대화 주제 선택 메뉴 표시

        Returns:
            str: 선택한 주제 (TALK_TOPICS의 항목)
            None: 뒤로가기 선택
        """
        name = context.get("name", self.name)

        # 주제 선택 메뉴 생성
        lines = [f"[{name}]"]
        lines.append("")
        for topic in self.TALK_TOPICS:
            lines.append(f"[url=@ret:{topic}]{topic}[/url]")
        lines.append("")
        lines.append("[url=@ret:]뒤로[/url]")

        choice = yield ui.dialog("\n".join(lines), autofill="off")

        if not choice:
            return None
        return choice

    def errand(self):
        """
        심부름 - NPC에게서 퀘스트를 받는 메뉴

        이 NPC가 giver로 설정된 AVAILABLE 상태의 퀘스트를 보여주고
        플레이어가 선택하면 퀘스트를 수락합니다.
        """
        from quest import quest_manager

        # 이 NPC에게서 받을 수 있는 퀘스트 조회
        available_quests = quest_manager.get_available_quests_from(self.unique_id)

        if not available_quests:
            yield ui.dialog(f"[{self.name}]\n\"...부탁할 일은 없어.\"")
            return

        # 퀘스트 목록 표시
        lines = [f"[b]{self.name}[/b]의 심부름", ""]

        for quest in available_quests:
            lines.append(f"[url=@ret:{quest.unique_id}]{quest.name}[/url]")
            if quest.description:
                lines.append(f"  [color=gray]{quest.description[:30]}...[/color]" if len(quest.description) > 30 else f"  [color=gray]{quest.description}[/color]")

        lines.append("")
        lines.append("[url=@ret:cancel]취소[/url]")

        result = yield ui.dialog("\n".join(lines), autofill="off")

        if result and result != "cancel":
            quest_id = result
            quest = quest_manager._get_quest_instance(quest_id)
            if quest:
                # 퀘스트 제안 다이얼로그 실행
                accept_result = yield from quest.offer_dialog()
                if accept_result == "accept":
                    quest_manager.accept_quest(quest_id)

    # ========================================
    # 호감도 테스트 메서드 (디버그용)
    # ========================================

    def debug_affection_up(self):
        """호감도 +10 테스트"""
        self._check_instantiated()
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get('name', '주인공') if player_info else '주인공'
        prop_name = f"관계:{player_name}:호감"
        new_value = morld.modify_prop(self.instance_id, prop_name, 10)
        yield ui.dialog(f"[b]{self.name}[/b]\n\n{prop_name} +10\n현재: {new_value}")

    def debug_affection_down(self):
        """호감도 -10 테스트"""
        self._check_instantiated()
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get('name', '주인공') if player_info else '주인공'
        prop_name = f"관계:{player_name}:호감"
        new_value = morld.modify_prop(self.instance_id, prop_name, -10)
        yield ui.dialog(f"[b]{self.name}[/b]\n\n{prop_name} -10\n현재: {new_value}")

    def debug_arousal_up(self):
        """성욕 +20 테스트 (NPC 주도 트리거 테스트용)"""
        self._check_instantiated()
        prop_name = "상태:성욕"
        new_value = morld.modify_prop(self.instance_id, prop_name, 20)
        yield ui.dialog(f"[b]{self.name}[/b]\n\n{prop_name} +20\n현재: {new_value}")

    def debug_arousal_down(self):
        """성욕 -20 테스트"""
        self._check_instantiated()
        prop_name = "상태:성욕"
        new_value = morld.modify_prop(self.instance_id, prop_name, -20)
        yield ui.dialog(f"[b]{self.name}[/b]\n\n{prop_name} -20\n현재: {new_value}")

    def debug_work_order(self):
        """디버그: NPC에게 작업 지시 (임시 스케줄 push)"""
        self._check_instantiated()
        from think import get_agent
        from think.activities import ACTIVITY_HANDLERS

        agent = get_agent(self.instance_id)
        if not agent:
            yield ui.dialog(f"[b]{self.name}[/b]\n\nAI Agent가 없습니다.")
            return

        # 선택지 구성
        activities = list(ACTIVITY_HANDLERS.keys())
        has_order = len(agent.schedule_stack) > 1

        lines = [f"[b]{self.name}[/b]", ""]
        if has_order:
            current = agent.get_current_schedule()
            current_name = current[0].get("activity", "?") if current else "?"
            lines.append(f"현재 작업지시: [b]{current_name}[/b]")
            lines.append("")

        lines.append("작업을 선택하세요:")
        lines.append("")
        for act in activities:
            lines.append(f"[url=@ret:{act}]{act}[/url]")

        if has_order:
            lines.append("")
            lines.append("[url=@ret:__cancel__]작업지시 해제[/url]")

        lines.append("")
        lines.append("[url=@ret:]뒤로[/url]")

        choice = yield ui.dialog("\n".join(lines), autofill="off")
        if not choice:
            return

        if choice == "__cancel__":
            agent.pop_schedule()
            yield ui.dialog(f"[b]{self.name}[/b]\n\n작업지시를 해제했습니다.\n원래 스케줄로 복원됩니다.")
            return

        # 기존 작업지시가 있으면 먼저 pop
        if has_order:
            agent.pop_schedule()

        # 임시 스케줄 push (24시간 = 항상 매칭)
        work_order = [{
            "name": f"DEBUG: {choice}",
            "activity": choice,
            "start": 0,
            "end": 86_400_000,
        }]
        agent.push_schedule(work_order)

        yield ui.dialog(f"[b]{self.name}[/b]\n\n'{choice}' 작업을 지시했습니다.")

    # ========================================
    # 이벤트 다이얼로그 시스템
    # ========================================

    # 이벤트별 대화 정의 (서브클래스에서 오버라이드)
    # 형식:
    #   EVENT_DIALOGS = {
    #       "이벤트명": {
    #           "pages": ["대사1", "대사2", ...],
    #           "time_consume": 60000,       # 대화로 경과하는 게임 시간 (밀리초)
    #           "stay_duration": 120000,     # 대화 후 NPC가 현재 위치에 머무는 시간 (밀리초)
    #           # time_consume과 stay_duration은 항상 함께 설정해야 함
    #       },
    #       "복잡한_이벤트": "_handle_complex_event",  # 메서드로 위임
    #   }
    EVENT_DIALOGS: dict = None

    # ========================================
    # 캐릭터 개인 퀘스트 시스템
    # ========================================
    # 캐릭터와 깊이 연관된 퀘스트를 캐릭터 파일 내에서 직접 정의
    #
    # 형식:
    #   CHARACTER_QUESTS = [
    #       {
    #           "unique_id": "sera_trust_1",
    #           "name": "세라의 신뢰 I",
    #           "description": "세라와 더 친해지자.",
    #           "category": "personal",
    #           "prerequisites": ["main_find_sera"],
    #           "giver": "sera",
    #           "reporter": "sera",
    #           "conditions": [
    #               {"type": "prop", "target": "player", "prop": "관계:세라:호감", "min_value": 30},
    #           ],
    #           "rewards": [
    #               {"type": "item", "item": "sera_pendant", "count": 1},
    #           ],
    #           "dialogs": {
    #               "offer": ["..."],
    #               "accept": ["..."],
    #               "complete": ["..."],
    #           },
    #       },
    #   ]
    #
    # 장점:
    # - 캐릭터 파일 하나만 보면 그 캐릭터의 모든 것을 알 수 있음
    # - 캐릭터 삭제 시 관련 퀘스트도 자동으로 제거됨
    # - 대화, 조건, 보상이 캐릭터와 함께 관리됨
    CHARACTER_QUESTS: list = []

    @classmethod
    def get_character_quests(cls) -> list:
        """캐릭터 개인 퀘스트 목록 반환"""
        return cls.CHARACTER_QUESTS

    # ========================================
    # First Meet 판정 시스템
    # ========================================
    # 관계:XX:진척도 <= 0 이면 first meet
    # first meet 이벤트 후 진척도를 1로 설정

    def is_first_meet(self, player_id: int) -> bool:
        """
        플레이어와의 첫 만남 여부 판정

        관계:{캐릭터이름}:진척도 가 0 이하이면 True

        Args:
            player_id: 플레이어 유닛 ID

        Returns:
            첫 만남이면 True
        """
        props = morld.get_unit_props(player_id)
        if not props:
            return True  # props가 없으면 첫 만남으로 간주

        progress_key = f"관계:{self.name}:진척도"
        progress = props.get(progress_key, 0)
        return progress <= 0

    def mark_first_meet_done(self, player_id: int):
        """
        첫 만남 완료 처리 - 진척도를 1로 설정

        Args:
            player_id: 플레이어 유닛 ID
        """
        progress_key = f"관계:{self.name}:진척도"
        morld.set_unit_prop(player_id, progress_key, 1)

        # 퀘스트 조건 즉시 체크 (시간 경과로 이벤트 핸들러가 스킵될 수 있으므로)
        from quest import quest_manager
        quest_manager.check_meet_conditions(player_id, self.instance_id)

    def on_meet_player(self, player_id):
        """플레이어와 만났을 때 - Generator 기반"""
        unit_info = morld.get_unit_info(self.instance_id)

        # 수면 중이면 반응 없음
        if unit_info and unit_info.get("activity") == "수면":
            return None

        # 프라이버시 체크 (수면 목적으로 자기 방 도착 시)
        privacy = self._check_room_privacy(player_id)
        if privacy is not None:
            return privacy

        # 첫 만남 여부 판정
        if not self.is_first_meet(player_id):
            # NPC 주도 스킨십 체크 (첫 만남 이후에만)
            if self.should_initiate_skinship(player_id):
                self.mark_initiative_cooldown()
                from npc_initiative import start_npc_initiative
                return start_npc_initiative(player_id, self.instance_id)
            return None

        # 첫 만남 이벤트 - 완료 후 진척도 1로 설정
        return self._first_meet_handler(player_id)

    def on_equip_change(self, player_id, item_id, is_equip):
        """플레이어 장비 변경 시 반응 - EQUIP_CHANGE_REACTIONS 기반"""
        if not self.EQUIP_CHANGE_REACTIONS:
            return None

        item_info = morld.get_item_info(item_id)
        if not item_info:
            return None

        equip_props = item_info.get("equip_props", {})
        if not equip_props.get("장착:손"):
            return None  # 무기가 아니면 무시

        key = "equip" if is_equip else "unequip"
        text = self.EQUIP_CHANGE_REACTIONS.get(key)
        if text:
            morld.add_action_log(text)

        return None

    # ========================================
    # 진척도/친밀 대화 (PROGRESS_DIALOGS / FRIENDLY_TALK_CONFIG)
    # ========================================

    def _talk_progress(self, level, context):
        """진척도 대화 - PROGRESS_DIALOGS 기반 (일회성 플래그)"""
        if not self.PROGRESS_DIALOGS or level not in self.PROGRESS_DIALOGS:
            yield ui.dialog(f"[{self.name}]\n......")
            return

        config = self.PROGRESS_DIALOGS[level]
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        flag_key = f"대화:{player_name}:진척도{level}"
        props = morld.get_unit_props(self.instance_id)
        if props and props.get(flag_key):
            yield ui.dialog([f"[{name}]"] + config["fallback"])
            return

        morld.set_unit_prop(self.instance_id, flag_key, 1)
        dialog = [line.format(player_name=player_name) if "{player_name}" in line else line
                  for line in config["dialog"]]
        yield ui.dialog([f"[{name}]"] + dialog)

    def _talk_progress_1(self, context):
        return self._talk_progress(1, context)

    def _talk_progress_2(self, context):
        return self._talk_progress(2, context)

    def _talk_progress_3(self, context):
        return self._talk_progress(3, context)

    def _talk_friendly(self, level, context):
        """친밀 대화 - FRIENDLY_TALK_CONFIG 기반 (진척도 증가)"""
        if not self.FRIENDLY_TALK_CONFIG or level not in self.FRIENDLY_TALK_CONFIG:
            yield ui.dialog(f"[{self.name}]\n......")
            return

        config = self.FRIENDLY_TALK_CONFIG[level]
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        props = morld.get_unit_props(self.instance_id)
        progress_key = f"관계:{player_name}:진척도"
        current = props.get(progress_key, 0) if props else 0
        if current < config.get("progress_cap", 3):
            morld.modify_prop(self.instance_id, progress_key, 1)

        dialog = [line.format(player_name=player_name) if "{player_name}" in line else line
                  for line in config["dialog"]]
        yield ui.dialog([f"[{name}]"] + dialog)

    def _talk_friendly_high(self, context):
        return self._talk_friendly("high", context)

    def _talk_friendly_mid(self, context):
        return self._talk_friendly("mid", context)

    def get_initiative_event(self, player_id: int):
        """
        NPC 주도 이벤트 조회 - Focus 시점에서 호출

        NPC가 먼저 시작하는 이벤트가 있으면 Generator 반환.
        이동 중인 NPC와의 만남은 on_meet이 발생하지 않으므로,
        플레이어가 NPC를 클릭(focus)할 때 이 메서드로 이벤트를 체크합니다.

        체크 순서:
        1. First Meet (첫 만남)
        2. NPC 주도 스킨십
        3. 기타 NPC 주도 이벤트 (서브클래스에서 확장)

        Args:
            player_id: 플레이어 유닛 ID

        Returns:
            Generator (이벤트 있음) 또는 None (없음)
        """
        # 1. First Meet 체크
        if self.is_first_meet(player_id):
            handler = getattr(self, '_first_meet_handler', None)
            if handler:
                return handler(player_id)

        # 2. NPC 주도 스킨십 체크
        if self.should_initiate_skinship(player_id):
            self.mark_initiative_cooldown()
            try:
                from npc_initiative import start_npc_initiative
                return start_npc_initiative(player_id, self.instance_id)
            except ImportError:
                pass  # npc_initiative 모듈이 없으면 스킵

        # 3. 기타 NPC 주도 이벤트 (서브클래스에서 오버라이드 가능)
        return None

    # ========================================
    # 프라이버시 이벤트 (수면/목욕 시 방 퇴출)
    # ========================================

    def _check_room_privacy(self, player_id: int):
        """
        수면/목욕 목적으로 자기 방에 도착했는데 플레이어가 있으면 이벤트 반환

        on_meet_player()에서 호출. NPC가 해당 location에 도착하는 시점에
        1회 발동하므로 이 시점에서 한 번만 체크하면 충분.

        Args:
            player_id: 플레이어 유닛 ID

        Returns:
            Generator (이벤트 있음) 또는 None (없음)
        """
        # 1. 현재 Job이 프라이버시 활동인지
        job = morld.get_current_job(self.instance_id)
        if not job:
            return None
        job_name = job.get("name", "")
        if job_name not in ("수면", "목욕"):
            return None

        info = morld.get_unit_info(self.instance_id)
        if not info:
            return None

        # 2. 수면: 내 방인지 체크 필요 / 목욕: owner 체크 없음 (공유 욕실)
        if job_name == "수면":
            loc_info = morld.get_location_info(info["region_id"], info["location_id"])
            if not loc_info or loc_info.get("owner") != self.unique_id:
                return None

        # 3. 이벤트 반환 (서브클래스에서 구현)
        return self._on_room_privacy(player_id, job_name)

    def _on_room_privacy(self, player_id: int, activity: str):
        """
        프라이버시 이벤트 - ROOM_PRIVACY_CONFIG 기반

        Args:
            player_id: 플레이어 유닛 ID
            activity: 활동 종류 ("수면", "목욕" 등)

        Returns:
            Generator 또는 None
        """
        if not self.ROOM_PRIVACY_CONFIG:
            return None
        config = self.ROOM_PRIVACY_CONFIG.get(activity)
        if not config:
            return None

        props = morld.get_unit_props(self.instance_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"
        affection = props.get(f"관계:{player_name}:호감", 0) if props else 0
        info = morld.get_unit_info(self.instance_id)

        threshold = config.get("threshold", 50)
        tier = config["high"] if affection >= threshold else config["low"]

        def handler():
            yield ui.dialog(tier["dialog"])
            teleport_loc = tier.get("teleport")
            if teleport_loc is not None:
                morld.stand_up(player_id)
                if info:
                    morld.set_unit_location(player_id, info["region_id"], teleport_loc, 120)
                after = tier.get("after")
                if after:
                    yield ui.dialog([after])
        return handler()

    def _run_event_dialog(self, event_name: str, **kwargs):
        """
        이벤트 다이얼로그 실행 - Generator 반환

        Args:
            event_name: 이벤트 이름 (EVENT_DIALOGS 키)
            **kwargs: 추가 컨텍스트 (player_id 등)

        Returns:
            Generator 또는 None
        """
        if not self.EVENT_DIALOGS:
            return None

        dialog_data = self.EVENT_DIALOGS.get(event_name)
        if not dialog_data:
            return None

        # 문자열이면 메서드명으로 위임
        if isinstance(dialog_data, str) and dialog_data.startswith("_"):
            method = getattr(self, dialog_data, None)
            if method:
                return method(**kwargs)
            return None

        # dict면 표준 처리
        return self._create_event_handler(dialog_data, **kwargs)

    def _create_event_handler(self, dialog_data: dict, **kwargs):
        """
        이벤트 핸들러 Generator 생성

        Args:
            dialog_data: {"pages": [...], "time_consume": N(밀리초), "stay_duration": N(밀리초), ...}
            **kwargs: player_id 등

        Returns:
            Generator
        """
        pages = dialog_data.get("pages", [])
        time_consume = dialog_data.get("time_consume")
        stay_duration = dialog_data.get("stay_duration")
        instance_id = self.instance_id

        # time_consume과 stay_duration은 항상 페어로 설정해야 함
        if time_consume and not stay_duration:
            raise ValueError(f"EVENT_DIALOGS: time_consume이 설정되었지만 stay_duration이 없습니다 (instance={instance_id})")
        if stay_duration and not time_consume:
            raise ValueError(f"EVENT_DIALOGS: stay_duration이 설정되었지만 time_consume이 없습니다 (instance={instance_id})")

        def handler():
            yield ui.dialog(pages)
            # 대화 시간 경과 + NPC 현재 위치에 머무르기
            if time_consume:
                # set_npc_time_consume: Job 설정 + dialogTimeConsumed 누적
                # "stay"는 target_id 불필요
                morld.set_npc_time_consume(instance_id, "stay", time_consume)
                # stay_duration이 time_consume과 다르면 Job 기간만 별도 설정
                if stay_duration != time_consume:
                    morld.set_npc_job(instance_id, "stay", stay_duration)

        return handler()


class Object(Unit):
    """
    오브젝트 클래스 (가구, 바닥 등)

    메서드 오버라이드:
    - get_focus_text(): Focus 상태일 때 묘사 (클릭했을 때)

    액션 패턴:
    - call:메서드명:표시명 → 인스턴스 메서드 호출 (OOP 다형성)

    공통 메서드 (Unit에서 상속):
    - debug_props(): 속성 디버그 출력

    컨테이너 메서드 (인벤토리가 있는 오브젝트):
    - take(item_id): 오브젝트에서 아이템 가져가기
    - put(): 오브젝트에 아이템 넣기 (다이얼로그)

    필터링 속성:
    - put_filter: 넣기 가능한 아이템 카테고리 리스트
      예) ["food_ingredient"] → 음식 재료만 넣기 가능
      None이면 제한 없음 (모든 아이템 넣기 가능)
    """

    type: str = "object"
    put_filter: list = None  # 넣기 가능한 카테고리 리스트
    item_visible: bool = False  # True면 오브젝트 리스트에서 아이템 개수 표시

    # Pi-World: Object의 Location 내 위치 (instantiate 시 설정)
    position_x: float = 0
    position_y: float = 0

    # ========================================
    # 앉기/눕기 (Posture) 시스템
    # ========================================

    def _find_empty_slot(self) -> str | None:
        """빈 좌석 슬롯 찾기 (seated_by:* 중 값이 -1인 것)"""
        seated_by = morld.get_unit_props_by_type(self.instance_id, "seated_by")
        for slot_name, occupant_id in seated_by.items():
            if occupant_id == -1:
                return slot_name
        return None

    def _count_occupants(self) -> int:
        """현재 점유자 수"""
        seated_by = morld.get_unit_props_by_type(self.instance_id, "seated_by")
        return sum(1 for v in seated_by.values() if v != -1)

    def sit(self):
        """앉기 (자동 빈 슬롯 선택)"""
        player_id = morld.get_player_id()
        slot = self._find_empty_slot()
        if slot is None:
            yield ui.dialog(["자리가 없다."])
            return
        success = morld.sit_on(player_id, self.instance_id, slot)
        if success:
            # posture는 C# sit_on API에서 자동 설정됨
            yield ui.dialog([f"{self.name}에 앉았다."])

    def lie_down(self):
        """눕기 (자동 빈 슬롯 선택)"""
        player_id = morld.get_player_id()
        slot = self._find_empty_slot()
        if slot is None:
            yield ui.dialog(["자리가 없다."])
            return
        success = morld.sit_on(player_id, self.instance_id, slot)
        if success:
            # posture는 C# sit_on API에서 자동 설정됨
            yield ui.dialog([f"{self.name}에 누웠다."])

    def stand_up(self):
        """일어나기"""
        player_id = morld.get_player_id()
        # posture는 C# stand_up API에서 자동 초기화됨
        morld.stand_up(player_id)

    # ========================================
    # 컨테이너 시스템
    # ========================================

    def take(self, item_id):
        """오브젝트에서 특정 아이템 하나 가져가기"""
        player_id = morld.get_player_id()
        item_id = int(item_id)
        morld.lost_item(self.instance_id, item_id)
        morld.give_item(player_id, item_id)

    def _can_put_item(self, item_id: int) -> bool:
        """아이템을 이 오브젝트에 넣을 수 있는지 확인"""
        if self.put_filter is None:
            return True  # 필터 없으면 모든 아이템 허용

        # 아이템 인스턴스에서 category 확인
        from assets.items import get_instance
        item_instance = get_instance(item_id)
        if item_instance is None:
            return False

        item_category = getattr(item_instance, 'category', None)
        if item_category is None:
            return False  # 카테고리 없는 아이템은 필터가 있으면 제외

        return item_category in self.put_filter

    def _can_put_by_action_props(self, item_id):
        """아이템의 ActionProps "put"이 활성화되어 있는지 확인"""
        # ActionProps에 "put"이 명시적으로 1 이상이어야 허용
        # 0 이하면 비활성화 (get_item_action_prop은 키 없으면 0 반환)
        put_value = morld.get_item_action_prop(item_id, "put")
        return put_value >= 1

    def put(self):
        """오브젝트에 아이템 넣기 (다이얼로그 방식, 필터 적용)"""
        player_id = morld.get_player_id()
        inventory = morld.get_unit_inventory(player_id)

        if not inventory:
            yield ui.dialog("넣을 아이템이 없다.")
            return

        # 필터 적용하여 아이템 목록 생성
        lines = [f"[b]{self.name}[/b]에 넣기\n"]
        has_valid_item = False

        for item_id, count in inventory.items():
            # 카테고리 필터 확인
            if not self._can_put_item(item_id):
                continue

            # ActionProps "put" 필터 확인 (장착 중인 아이템 제외)
            if not self._can_put_by_action_props(item_id):
                continue

            item = morld.get_item_info(item_id)
            if item:
                has_valid_item = True
                item_name = item.get("name", f"아이템#{item_id}")
                count_text = f" x{count}" if count > 1 else ""
                lines.append(f"[url=@ret:{item_id}]{item_name}{count_text}[/url]")

        if not has_valid_item:
            filter_desc = ", ".join(self.put_filter) if self.put_filter else ""
            yield ui.dialog(f"넣을 수 있는 아이템이 없다.")
            return

        lines.append("\n[url=@ret:cancel]취소[/url]")

        result = yield ui.dialog("\n".join(lines), autofill="off")

        if result and result != "cancel":
            item_id = int(result)
            morld.lost_item(player_id, item_id)
            morld.give_item(self.instance_id, item_id)

    # ========================================
    # NPC 컨테이너 조작 (think 시스템용, non-generator)
    # ========================================

    def npc_store_item(self, npc_id, item_unique_id, count=1):
        """NPC 인벤토리 → 이 컨테이너로 아이템 이동"""
        from assets.registry import get_or_create_item_id
        item_id = get_or_create_item_id(item_unique_id)
        if item_id and morld.has_item(npc_id, item_id):
            morld.remove_item(npc_id, item_id, count)
            morld.give_item(self.instance_id, item_id, count)
            return True
        return False

    def npc_take_item(self, npc_id, item_unique_id, count=1):
        """이 컨테이너 → NPC 인벤토리로 아이템 이동"""
        from assets.registry import get_or_create_item_id
        item_id = get_or_create_item_id(item_unique_id)
        if item_id is None:
            return False
        inventory = morld.get_unit_inventory(self.instance_id)
        if inventory and inventory.get(item_id, 0) >= count:
            morld.remove_item(self.instance_id, item_id, count)
            morld.give_item(npc_id, item_id, count)
            return True
        return False

    def get_item_count(self, item_unique_id=None):
        """아이템 수 조회 (None이면 전체 합계)"""
        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            return 0
        if item_unique_id is None:
            return sum(inventory.values())
        from assets.registry import get_or_create_item_id
        item_id = get_or_create_item_id(item_unique_id)
        if item_id is None:
            return 0
        return inventory.get(item_id, 0)

    def instantiate(self, instance_id: int, region_id: int, location_id: int, x: float = None, y: float = None):
        """
        오브젝트를 morld에 등록

        Args:
            instance_id: 유닛 ID
            region_id: Region ID
            location_id: Location ID
            x: Location 내 X 좌표 (None이면 self.position_x 사용)
            y: Location 내 Y 좌표 (None이면 self.position_y 사용)
        """
        super().instantiate(instance_id)
        self.region_id = region_id
        self.location_id = location_id

        # 위치 결정 (인자 > 클래스 속성)
        pos_x = x if x is not None else self.position_x
        pos_y = y if y is not None else self.position_y

        morld.add_unit(
            instance_id,
            self.name,
            region_id,
            location_id,
            "object",
            self.actions or [],
            [],          # mood
            self.unique_id,  # unique_id 전달
            None,            # action_props
            self.owner,      # owner 전달
            self.item_visible  # item_visible 전달
        )

        # Pi-World: Location 내 위치 설정
        if pos_x != 0 or pos_y != 0:
            morld.set_unit_position(instance_id, pos_x, pos_y)

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
    - category: 아이템 카테고리 (필터링용)
      예) "food_ingredient", "drink_ingredient", "equipment", "material"
    - action_props: 액션별 활성화 상태 (0 이하면 비활성화)
      예) {"put": 1, "equip": 1} → 장착 시 {"put": 0}으로 변경하여 놓기 비활성화

    액션 패턴:
    - call:메서드명:표시명 → 인스턴스 메서드 호출 (OOP 다형성)

    장비 슬롯 시스템:
    - equip_props에 "장착:{슬롯}" 형식으로 정의 (예: "장착:손": 1)
    - 같은 슬롯 키를 가진 아이템이 장착되어 있으면 자동 해제 후 장착
    - C#의 HandleEquipAction에서 처리
    """

    passive_props: dict = None
    equip_props: dict = None
    # action_props: dict = None  # 액션별 활성화 상태
    action_props: dict = {"put": 1} # 기본적으로 아이템은 모두 콘테이너에 너허을 수 있음
    value: int = 0
    owner: str = None  # 소유자 unique_id (예: "sera", "mila")
    category: str = None  # 아이템 카테고리 (필터링용)

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
            self.owner,  # 소유자 정보 전달
            self.unique_id,  # Python unique_id 전달
            self.action_props or {}  # 액션별 활성화 상태
        )

        # 인스턴스 캐시 등록 (call: 액션용)
        from assets.items import register_instance
        register_instance(instance_id, self)

    def debug_item_props(self):
        """아이템의 속성(props) 디버그 출력"""
        self._check_instantiated()
        item_info = morld.get_item_info(self.instance_id)
        if not item_info:
            yield ui.dialog("[debug_item_props] 아이템 정보를 찾을 수 없습니다.")
            return

        lines = [f"[b]{self.name}[/b] (id={self.instance_id})"]
        lines.append("")

        # Passive Props
        passive_props = item_info.get("passive_props", {})
        if passive_props:
            lines.append("[color=cyan]Passive Props:[/color]")
            for key, value in passive_props.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append("[color=gray]Passive Props: 없음[/color]")

        lines.append("")

        # Equip Props
        equip_props = item_info.get("equip_props", {})
        if equip_props:
            lines.append("[color=lime]Equip Props:[/color]")
            for key, value in equip_props.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append("[color=gray]Equip Props: 없음[/color]")

        lines.append("")

        # Action Props
        action_props = item_info.get("action_props", {})
        if action_props:
            lines.append("[color=yellow]Action Props:[/color]")
            for key, value in action_props.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append("[color=gray]Action Props: 없음[/color]")

        yield ui.dialog("\n".join(lines))


class Location(Asset):
    """
    Location 클래스

    클래스 속성:
    - is_indoor: 실내 여부
    - stay_duration: 경유 시 지체 시간
    - describe_text: 장소 묘사 텍스트 딕셔너리 (태그 기반 선택용)
    - owner: 소유자 unique_id (None이면 공용)

    Pi-World 2D 속성:
    - geometry: "line" (선형) 또는 "ring" (원형), 기본값 "line"
    - length: Location의 길이 (0이면 레거시 모드 - 점 형태)

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

    # Pi-World 2D 속성
    geometry: str = "line"  # "line" 또는 "ring"
    length: float = 0  # 0 = 레거시 모드 (점 형태)

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

        # Location 등록 (Pi-World 2D 속성 포함)
        morld.add_location(
            region_id,
            location_id,
            self.name,
            self.stay_duration,
            self.is_indoor,
            self.owner,  # 소유자 정보 전달
            self.describe_text,  # 묘사 텍스트 전달
            None,  # ground_id (나중에 설정)
            self.geometry,  # Pi-World: geometry
            self.length,  # Pi-World: length
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
            ground_instance_id: 바닥 ID (None이면 create_id로 자동 생성)
        """
        self._check_instantiated()

        if ground_instance_id is None:
            ground_instance_id = morld.create_id("unit")

        ground.instantiate(ground_instance_id, self.region_id, self.location_id)
        self.ground = ground

        # Location에 ground_id 설정
        morld.set_location_ground_id(self.region_id, self.location_id, ground_instance_id)

    def add_object(self, obj: Object, instance_id: int = None, owner: str = None, x: float = None, y: float = None) -> int:
        """
        이 Location에 오브젝트 배치

        Args:
            obj: Object 인스턴스
            instance_id: 유닛 ID (None이면 create_id로 자동 생성)
            owner: 소유자 unique_id (None이면 obj.owner 사용)
            x: Location 내 X 좌표 (Pi-World)
            y: Location 내 Y 좌표 (Pi-World)

        Returns:
            생성된 오브젝트의 instance_id
        """
        self._check_instantiated()
        if instance_id is None:
            instance_id = morld.create_id("unit")
        # owner 파라미터가 주어지면 인스턴스의 owner 오버라이드
        if owner is not None:
            obj.owner = owner
        obj.instantiate(instance_id, self.region_id, self.location_id, x, y)
        # NPC 행동용 location 인덱스에 등록
        from assets.objects import register_location_object
        register_location_object(self.region_id, self.location_id, instance_id)
        return instance_id

    def add_item_to_ground(self, item: Item, count: int = 1):
        """바닥에 아이템 추가 (ground의 인벤토리에 추가)"""
        self._check_instantiated()
        if self.ground is None:
            raise RuntimeError(f"Location {self.name} has no ground object")
        self.ground.add_item(item, count)
