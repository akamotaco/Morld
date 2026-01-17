# assets/characters/yuki.py - 유키 캐릭터 Asset
#
# Rule-based 텍스트 선택 시스템 사용
# - TALK_RULES: 대화 규칙
# - DESCRIBE_RULES: 장소에서 보이는 묘사 규칙
# - FOCUS_RULES: 클릭했을 때 상세 묘사 규칙

import morld
from assets.base import Character
from think import BaseAgent, register_agent_class


class Yuki(Character):
    unique_id = "yuki"
    name = "유키"
    type = "female"
    props = {
        "외모:은발": 1, "외모:장발": 1, "외모:붉은눈": 1,
        "성격:수줍음": 1, "성격:얌전함": 1,
        "관계:엘라:의지": 1,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 5,
    }
    actions = ["call:talk:대화", "call:debug_props:속성 보기"]
    mood = []

    # ========================================
    # 대화 규칙 (조건 → 대사 또는 메서드명)
    # ========================================
    TALK_RULES = [
        # 특수 상황 (최우선)
        ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

        # Activity 기반
        ({"activity": "청소"}, {"pages": ["...청소 중이에요...", "..."]}),
        ({"activity": "빨래"}, {"pages": ["...빨래를 널고 있어요...", "...조금만 기다려 주세요..."]}),
        ({"activity": "식사"}, {"pages": ["(조용히 먹고 있다)", "...맛있어요..."]}),
        ({"activity": "휴식"}, {"pages": ["(책을 읽고 있다)", "...아, 네..."]}),
        ({"activity": "준비"}, {"pages": ["...지금 준비 중이에요...", "..."]}),

        # 호감도 기반
        ({"호감": 70}, {"pages": ["...안녕하세요...", "...기다리고 있었어요..."]}),
        ({"호감": 50}, {"pages": ["...안녕하세요...", "...뭔가 필요하세요...?"]}),

        # mood 기반
        ({"mood": "기쁨"}, {"pages": ["...네...", "...(희미하게 웃는다)"]}),
        ({"mood": "슬픔"}, {"pages": ["............", "..."]}),

        # 기본값
        ({}, {"pages": ["...네?", "...무슨 일이세요...?"]}),
    ]

    # ========================================
    # Describe 규칙 (장소에서 보이는 묘사)
    # ========================================
    DESCRIBE_RULES = [
        # 이동 중
        ({"is_traveling": True}, "{name}(이)가 조용히 어딘가로 향하고 있다."),

        # Activity 기반
        ({"activity": "청소"}, "{name}가 조용히 청소하고 있다."),
        ({"activity": "빨래"}, "{name}가 빨래를 널고 있다."),
        ({"activity": "식사"}, "{name}가 조용히 식사 중이다."),
        ({"activity": "수면"}, "{name}가 새근새근 잠들어 있다."),
        ({"activity": "휴식"}, "{name}가 책을 읽고 있다."),

        # 위치 기반
        ({"location": (0, 4)}, "{name}가 욕실을 청소하고 있다."),
        ({"location": (0, 1)}, "{name}가 소파 구석에 앉아 책을 읽고 있다."),
        ({"location": (2, 5)}, "{name}가 조용히 앉아 있다."),  # 도심 은신처

        # 기본값
        ({}, "{name}가 조용히 서 있다."),
    ]

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = [
        # Activity 기반
        ({"activity": "청소"}, "열심히 청소하고 있다."),
        ({"activity": "빨래"}, "빨래를 정성스럽게 널고 있다."),
        ({"activity": "식사"}, "조용히 음식을 먹고 있다."),
        ({"activity": "수면"}, "새근새근 잠들어 있다. 인형 같다."),
        ({"activity": "휴식"}, "조용히 책을 읽고 있다."),

        # mood 기반
        ({"mood": "기쁨"}, "살짝 볼이 붉어지며 희미하게 웃는다."),
        ({"mood": "슬픔"}, "고개를 숙이고 있다. 말을 걸기 어려워 보인다."),

        # 호감도 기반
        ({"호감": 70}, "당신을 보고 살짝 미소 짓는다."),

        # 기본값
        ({}, "은빛 긴 머리의 조용한 소녀. 붉은 눈이 신비로운 느낌을 준다."),
    ]

    # ========================================
    # 이벤트 다이얼로그 정의
    # ========================================
    EVENT_DIALOGS = {
        "first_meet": {
            "pages": [
                "은빛 머리카락의 소녀가 있다.",
                "낯선 이의 등장에 경계하는 눈빛을 보낸다.",
                "붉은 눈동자가 차갑게 빛난다.",
                "입술을 굳게 다문 채 한 발짝 뒤로 물러선다.",
                "엘라 뒤에 숨듯 서서, 여전히 경계를 풀지 않는다."
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

@register_agent_class("yuki")
class YukiAgent(BaseAgent):
    """
    유키 AI - 도심 은신처 생활

    특징:
    - 수줍고 얌전함
    - 은신처에서 조용히 지냄
    - 엘라를 의지함
    """

    # 도심 은신처 스케줄 (region_id=2, location_id=5=은신처)
    SCHEDULE = [
        {"name": "기상", "region_id": 2, "location_id": 5, "start": 420, "end": 480, "activity": "준비"},
        {"name": "아침식사", "region_id": 2, "location_id": 5, "start": 480, "end": 540, "activity": "식사"},
        {"name": "청소", "region_id": 2, "location_id": 5, "start": 540, "end": 660, "activity": "청소"},
        {"name": "독서", "region_id": 2, "location_id": 5, "start": 660, "end": 720, "activity": "휴식"},
        {"name": "점심식사", "region_id": 2, "location_id": 5, "start": 720, "end": 780, "activity": "식사"},
        {"name": "휴식", "region_id": 2, "location_id": 5, "start": 780, "end": 1020, "activity": "휴식"},
        {"name": "저녁식사", "region_id": 2, "location_id": 5, "start": 1080, "end": 1140, "activity": "식사"},
        {"name": "독서", "region_id": 2, "location_id": 5, "start": 1140, "end": 1320, "activity": "휴식"},
        {"name": "수면", "region_id": 2, "location_id": 5, "start": 1320, "end": 420, "activity": "수면"},
    ]

    def think(self):
        """유키의 행동 결정 - 스케줄 기반 Job 채우기"""
        # 스케줄 기반으로 JobList 채우기
        self.fill_schedule_jobs_from(self.SCHEDULE)
        return None
