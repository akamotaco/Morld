# assets/characters/ella.py - 엘라 캐릭터 Asset
#
# Rule-based 텍스트 선택 시스템 사용
# - TALK_RULES: 대화 규칙
# - DESCRIBE_RULES: 장소에서 보이는 묘사 규칙
# - FOCUS_RULES: 클릭했을 때 상세 묘사 규칙

import morld
from assets.base import Character
from think import BaseAgent, register_agent_class


class Ella(Character):
    unique_id = "ella"
    name = "엘라"
    type = "female"
    props = {
        "외모:흑발": 1, "외모:올림머리": 1, "외모:보라색눈": 1,
        "성격:냉정함": 1, "성격:리더십": 1,
        "관계:유키:보호": 1,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 5,
    }
    actions = [
        "call:talk:대화",
        "call:debug_props:속성 보기",
        "call:debug_affection_up:호감도 +10",
        "call:debug_affection_down:호감도 -10",
    ]
    mood = []

    # ========================================
    # 대화 규칙 (조건 → 대사 또는 메서드명)
    # ========================================
    TALK_RULES = [
        # 특수 상황 (최우선)
        ({"mood": "분노"}, {"pages": ["......", "...가까이 오지 마라."]}),
        ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

        # Activity 기반
        ({"activity": "관리"}, {"pages": ["지금 바쁘다.", "...급한 일이 아니라면 나중에 와라."]}),
        ({"activity": "조회"}, {"pages": ["지금 조회 중이다.", "잠시 기다려라."]}),
        ({"activity": "순찰"}, {"pages": ["순찰 중이다.", "무슨 일이냐?"]}),
        ({"activity": "탐색"}, {"pages": ["물자를 찾고 있다.", "...방해하지 마라."]}),
        ({"activity": "식사"}, {"pages": ["(식사 중이다)", "...나중에 와라."]}),
        ({"activity": "휴식"}, {"pages": ["......", "무슨 일이냐?"]}),
        ({"activity": "준비"}, {"pages": ["지금 준비 중이다.", "잠시 후에 와라."]}),

        # 호감도 기반
        ({"호감": 70}, {"pages": ["......", "...무슨 일이냐?"]}),
        ({"호감": 50}, {"pages": ["......", "...할 말이 있으면 빨리 해라."]}),

        # mood 기반
        ({"mood": "기쁨"}, {"pages": ["......", "...특별한 일이라도 있었나?"]}),
        ({"mood": "슬픔"}, {"pages": ["............", "..."]}),

        # 기본값
        ({}, {"pages": ["무슨 용건이냐?", "...간단히 말해라."]}),
    ]

    # ========================================
    # Describe 규칙 (장소에서 보이는 묘사)
    # ========================================
    DESCRIBE_RULES = [
        # 이동 중
        ({"is_traveling": True, "activity": "순찰"}, "{name}가 정찰을 위해 이동 중이다."),
        ({"is_traveling": True, "activity": "탐색"}, "{name}가 물자를 찾으러 이동 중이다."),
        ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),

        # Activity 기반
        ({"activity": "관리"}, "{name}가 서류를 검토하고 있다."),
        ({"activity": "조회"}, "{name}가 모두에게 지시를 내리고 있다."),
        ({"activity": "순찰"}, "{name}가 주변을 경계하고 있다."),
        ({"activity": "탐색"}, "{name}가 물자를 찾고 있다."),
        ({"activity": "식사"}, "{name}가 우아하게 식사 중이다."),
        ({"activity": "수면"}, "{name}가 단정한 자세로 잠들어 있다."),
        ({"activity": "휴식"}, "{name}가 창밖을 바라보고 있다."),

        # 위치 기반
        ({"location": (0, 1)}, "{name}가 거실 중앙에 서서 상황을 파악하고 있다."),
        ({"location": (0, 11)}, "{name}가 책상에서 서류를 정리하고 있다."),
        ({"location": (2, 5)}, "{name}가 은신처에서 유키를 지키고 있다."),  # 도심 은신처

        # 기본값
        ({}, "{name}가 위엄있게 서 있다."),
    ]

    # ========================================
    # 연애 반응 (캐릭터별 커스텀)
    # ========================================
    ROMANCE_REACTIONS = {
        # 토글 액션
        "hug": {
            "during": "엘라가 무표정하게 당신을 안고 있다. 하지만 손끝에 미세한 떨림이 느껴진다.",
        },
        "deep_kiss": {
            "during": "엘라가 눈을 감고 당신의 입술을 받아들이고 있다.",
        },
        "breast_touch": {
            "during": "엘라가 얼굴을 돌리며 가만히 허용하고 있다.",
        },
        # 즉시 액션
        "head_pat": {
            "start": "엘라가 살짝 눈을 치뜬다. \"...뭐하는 거냐.\"",
        },
        "cheek_caress": {
            "start": "엘라가 당신의 손을 쳐내려다... 멈춘다.",
        },
        "cheek_pinch": {
            "start": "엘라가 미간을 찌푸린다. \"......\"",
        },
        "ear_touch": {
            "start": "엘라의 귀끝이 살짝 붉어진다.",
        },
        "french_kiss": {
            "start": "엘라가 잠시 망설이다 당신의 혀를 받아들인다.",
        },
        "butt_caress": {
            "start": "엘라가 당신을 날카롭게 노려본다. 하지만 거부하지 않는다.",
        },
    }

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = [
        # Activity 기반
        ({"activity": "관리"}, "서류를 검토하며 무언가 기록하고 있다."),
        ({"activity": "조회"}, "모두를 둘러보며 하루 일과를 지시하고 있다."),
        ({"activity": "순찰"}, "날카로운 눈으로 주변을 경계하고 있다."),
        ({"activity": "탐색"}, "주변을 살피며 쓸 만한 것을 찾고 있다."),
        ({"activity": "식사"}, "우아하게 식사 중이다."),
        ({"activity": "수면"}, "단정한 자세로 잠들어 있다."),
        ({"activity": "휴식"}, "창밖을 바라보며 생각에 잠겨 있다."),

        # mood 기반
        ({"mood": "기쁨"}, "표정 변화는 적지만, 눈빛이 부드러워졌다."),
        ({"mood": "슬픔"}, "평소보다 더 차가워 보인다. 무언가 생각에 잠겨 있다."),
        ({"mood": "분노"}, "눈빛이 날카롭다. 함부로 다가가기 어렵다."),

        # 호감도 기반
        ({"호감": 70}, "당신을 보고 살짝 고개를 끄덕인다."),

        # 기본값
        ({}, "단정하게 올린 흑발의 위엄있는 여성. 보라색 눈이 냉정해 보인다."),
    ]

    # ========================================
    # 이벤트 다이얼로그 정의
    # ========================================
    EVENT_DIALOGS = {
        "first_meet": {
            "pages": [
                "단정하게 올린 흑발의 여성이 있다.",
                "보라색 눈동자가 차갑게 당신을 훑어본다.",
                "본능적으로 유키를 등 뒤로 감싸며 한 걸음 앞으로 나선다.",
                "외부인에 대한 경계와 불신이 온몸에서 느껴진다.",
                "그녀의 눈빛은 '가까이 오지 마라'라고 말하고 있다.",
                "유키를 지키려는 듯, 굳건히 그 자리에 서 있다."
            ],
        },
    }

    # 이벤트 플래그 (인스턴스별)
    _event_flags: dict

    def __init__(self):
        super().__init__()
        self._event_flags = {}

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 처음 만났을 때 - Generator 기반 (묘사 형식)"""
        if self._event_flags.get("first_meet"):
            return None

        unit_info = morld.get_unit_info(self.instance_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        self._event_flags["first_meet"] = True
        return self._run_event_dialog("first_meet", player_id=player_id)


# ========================================
# AI Agent
# ========================================

@register_agent_class("ella")
class EllaAgent(BaseAgent):
    """
    엘라 AI - 도심 생존자 리더

    특징:
    - 냉정하고 리더십 있음
    - 유키를 보호하고 돌봄
    - 외부인에 대한 불신
    """

    # 도심 은신처 스케줄 (region_id=2)
    SCHEDULE = [
        {"name": "기상", "region_id": 2, "location_id": 5, "start": 360, "end": 420, "activity": "준비"},
        {"name": "아침식사", "region_id": 2, "location_id": 5, "start": 420, "end": 480, "activity": "식사"},
        {"name": "정찰", "region_id": 2, "location_id": 3, "start": 540, "end": 660, "activity": "순찰"},  # 약국
        {"name": "물자수집", "region_id": 2, "location_id": 2, "start": 660, "end": 720, "activity": "탐색"},  # 편의점
        {"name": "점심식사", "region_id": 2, "location_id": 5, "start": 720, "end": 780, "activity": "식사"},
        {"name": "관리", "region_id": 2, "location_id": 5, "start": 780, "end": 960, "activity": "관리"},
        {"name": "정찰", "region_id": 2, "location_id": 0, "start": 960, "end": 1020, "activity": "순찰"},  # 도시입구
        {"name": "저녁식사", "region_id": 2, "location_id": 5, "start": 1080, "end": 1140, "activity": "식사"},
        {"name": "휴식", "region_id": 2, "location_id": 5, "start": 1140, "end": 1320, "activity": "휴식"},
        {"name": "수면", "region_id": 2, "location_id": 5, "start": 1320, "end": 360, "activity": "수면"},
    ]

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self.SCHEDULE)

    def think(self):
        """엘라의 행동 결정 - 스케줄 기반 Job 채우기"""
        schedule = self.get_current_schedule()
        self.fill_schedule_jobs_from(schedule)
        return None
