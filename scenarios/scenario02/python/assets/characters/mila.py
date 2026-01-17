# assets/characters/mila.py - 밀라 캐릭터 Asset
#
# Rule-based 텍스트 선택 시스템 사용
# - TALK_RULES: 대화 규칙
# - DESCRIBE_RULES: 장소에서 보이는 묘사 규칙
# - FOCUS_RULES: 클릭했을 때 상세 묘사 규칙

import morld
from assets.base import Character
from think import BaseAgent, register_agent_class


class Mila(Character):
    unique_id = "mila"
    name = "밀라"
    type = "female"
    props = {
        "외모:갈색머리": 1, "외모:중간머리": 1, "외모:갈색눈": 1,
        "성격:다정함": 1, "성격:걱정많음": 1,
        "관계:세라:신뢰": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 6,
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
        ({"activity": "요리"}, {"pages": ["(요리 중이다)", "잠시만요, 지금 손을 뗄 수가 없어요!"]}),
        ({"activity": "식사"}, {"pages": ["맛있게 드셨으면 좋겠어요.", "더 필요하시면 말씀해 주세요!"]}),
        ({"activity": "설거지"}, {"pages": ["설거지 중이에요.", "금방 끝날 거예요~"]}),
        ({"activity": "청소"}, {"pages": ["청소 중이에요~", "깨끗한 집이 좋잖아요!"]}),
        ({"activity": "정리"}, {"pages": ["지금 정리 중이에요.", "조금만 기다려 주세요."]}),
        ({"activity": "휴식"}, {"pages": ["후~ 잠시 쉬고 있어요.", "오늘 뭐 드시고 싶은 거 있으세요?"]}),
        ({"activity": "준비"}, {"pages": ["지금 준비 중이에요~", "조금만 기다려 주세요!"]}),

        # 호감도 기반
        ({"호감": 70}, {"pages": ["오셨군요~", "...괜찮으세요? 뭔가 필요하신 거 있으세요?"]}),
        ({"호감": 50}, {"pages": ["안녕하세요!", "...뭐 드시고 싶은 거 있으세요?"]}),

        # mood 기반
        ({"mood": "기쁨"}, {"pages": ["안녕하세요~", "오늘 기분이 좋아요!"]}),
        ({"mood": "슬픔"}, {"pages": ["...안녕하세요.", "...아, 아무것도 아니에요."]}),

        # 기본값
        ({}, {"pages": ["안녕하세요!", "뭔가 필요하신 게 있으세요?"]}),
    ]

    # ========================================
    # Describe 규칙 (장소에서 보이는 묘사)
    # ========================================
    DESCRIBE_RULES = [
        # 이동 중
        ({"is_traveling": True, "activity": "요리"}, "{name}가 부엌으로 향하고 있다."),
        ({"is_traveling": True, "activity": "청소"}, "{name}가 청소를 하러 이동 중이다."),
        ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),

        # Activity 기반
        ({"activity": "요리"}, "{name}가 분주하게 요리하고 있다."),
        ({"activity": "청소"}, "{name}가 열심히 청소하고 있다."),
        ({"activity": "식사"}, "{name}가 다른 사람들이 먹는 모습을 흐뭇하게 바라본다."),
        ({"activity": "수면"}, "{name}가 포근하게 잠들어 있다."),
        ({"activity": "휴식"}, "{name}가 따뜻한 차를 마시고 있다."),
        ({"activity": "설거지"}, "{name}가 설거지를 하고 있다."),
        ({"activity": "정리"}, "{name}가 정리 중이다."),

        # 위치 기반
        ({"location": (0, 2)}, "{name}가 요리에 열중하고 있다."),
        ({"location": (0, 3)}, "{name}가 식탁을 정리하고 있다."),

        # 기본값
        ({}, "{name}가 다정한 눈으로 주변을 살핀다."),
    ]

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = [
        # Activity 기반
        ({"activity": "요리"}, "앞치마를 두르고 열심히 요리하고 있다."),
        ({"activity": "청소"}, "걸레를 들고 구석구석 닦고 있다."),
        ({"activity": "식사"}, "다른 사람들이 맛있게 먹는지 살피고 있다."),
        ({"activity": "수면"}, "평화롭게 잠들어 있다."),
        ({"activity": "설거지"}, "정성스럽게 설거지를 하고 있다."),
        ({"activity": "휴식"}, "따뜻한 차를 마시며 여유를 즐기고 있다."),

        # mood 기반
        ({"mood": "기쁨"}, "온화하게 웃고 있다. 보는 사람도 기분이 좋아진다."),
        ({"mood": "슬픔"}, "걱정스러운 표정이다. 무언가 마음에 걸리는 것 같다."),

        # 호감도 기반
        ({"호감": 70}, "따뜻한 눈빛으로 당신을 바라본다."),

        # 기본값
        ({}, "부드러운 갈색 머리의 다정한 여성. 따뜻한 갈색 눈이 편안함을 준다."),
    ]

    # ========================================
    # 이벤트 다이얼로그 정의
    # ========================================
    EVENT_DIALOGS = {
        "first_meet": {
            "pages": [
                "어머, 깨어나셨군요!",
                "저는 밀라예요. 여기서 요리를 맡고 있어요.",
                "많이 힘드셨죠? 기억은... 좀 나세요?",
                "괜찮아요, 천천히 쉬세요. 필요한 게 있으면 말씀해 주세요."
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
        """플레이어와 처음 만났을 때 - Generator 기반"""
        # 첫 만남 이벤트
        if self._event_flags.get("first_meet"):
            return None

        unit_info = morld.get_unit_info(self.instance_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        self._event_flags["first_meet"] = True
        return self._run_event_dialog("first_meet", player_id=player_id)

    def on_equip_change(self, player_id, item_id, is_equip):
        """플레이어 장비 변경 시 반응"""
        # 무기(장착:손) 체크
        item_info = morld.get_item_info(item_id)
        if not item_info:
            return None

        equip_props = item_info.get("equip_props", {})
        if not equip_props.get("장착:손"):
            return None  # 무기가 아니면 무시

        if is_equip:
            morld.add_action_log("밀라가 걱정스러운 눈으로 무기를 바라본다.")
        else:
            morld.add_action_log("밀라가 안심한 듯 미소를 짓는다.")

        return None


# ========================================
# AI Agent
# ========================================

@register_agent_class("mila")
class MilaAgent(BaseAgent):
    """
    밀라 AI - 요리 + 실내 관리 담당

    특징:
    - 다정하고 걱정 많음
    - 식사 준비와 실내 청소를 담당
    - 세라를 리더로 신뢰하고 따름
    - 플레이어가 아프면 걱정하며 지켜봄
    """

    SCHEDULE = [
        {"name": "기상", "region_id": 0, "location_id": 9, "start": 300, "end": 360, "activity": "준비"},
        {"name": "아침준비", "region_id": 0, "location_id": 2, "start": 360, "end": 420, "activity": "요리"},
        {"name": "아침식사", "region_id": 0, "location_id": 3, "start": 420, "end": 480, "activity": "식사"},
        {"name": "설거지", "region_id": 0, "location_id": 2, "start": 480, "end": 540, "activity": "설거지"},
        {"name": "청소", "region_id": 0, "location_id": 1, "start": 540, "end": 660, "activity": "청소"},  # 거실 청소
        {"name": "점심준비", "region_id": 0, "location_id": 2, "start": 660, "end": 720, "activity": "요리"},
        {"name": "점심식사", "region_id": 0, "location_id": 3, "start": 720, "end": 780, "activity": "식사"},
        {"name": "청소", "region_id": 0, "location_id": 4, "start": 780, "end": 840, "activity": "청소"},  # 욕실 청소
        {"name": "휴식", "region_id": 0, "location_id": 1, "start": 840, "end": 960, "activity": "휴식"},
        {"name": "저녁준비", "region_id": 0, "location_id": 2, "start": 1020, "end": 1110, "activity": "요리"},
        {"name": "저녁식사", "region_id": 0, "location_id": 3, "start": 1110, "end": 1170, "activity": "식사"},
        {"name": "정리", "region_id": 0, "location_id": 2, "start": 1170, "end": 1260, "activity": "정리"},
        {"name": "수면", "region_id": 0, "location_id": 9, "start": 1320, "end": 300, "activity": "수면"},
    ]

    def think(self):
        """밀라의 행동 결정 - 스케줄 기반 Job 채우기"""
        # 스케줄 기반으로 JobList 채우기
        self.fill_schedule_jobs_from(self.SCHEDULE)
        return None
