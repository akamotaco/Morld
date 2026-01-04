# entities/characters/sera.py - 세라 캐릭터 정의

from entities.characters.base import BaseCharacter


class Sera(BaseCharacter):
    """세라 - 과묵한 사냥꾼"""

    # === 기본 정보 ===
    ID = 2
    NAME = "세라"
    TYPE = "female"
    START_LOCATION = (0, 8)  # 세라의 방

    # === 태그 (스탯) ===
    TAGS = {
        # 외모
        "외모:흑발": 1,
        "외모:장발": 1,
        "외모:갈색눈": 1,
        # 성격
        "성격:과묵함": 1,
        "성격:듬직함": 1,
        # 관계 (플레이어와)
        "애정": 0,
        "성욕": 0,
        "질투": 0,
        # 상태
        "피로": 0,
        "기분": 5,
    }

    # === 외관 묘사 ===
    APPEARANCE = {
        "default": "긴 흑발을 묶은 과묵한 여성. 날카로운 갈색 눈이 인상적이다.",
        "기쁨": "표정 변화는 적지만, 눈가가 부드러워졌다.",
        "슬픔": "평소보다 더 말이 없다. 어딘가 먼 곳을 보고 있다.",
        "식사": "조용히 음식을 먹고 있다.",
        "수면": "경계심 없이 잠들어 있다.",
        "사냥": "활을 들고 날카로운 눈으로 주변을 살핀다."
    }

    # === 행동 목록 ===
    ACTIONS = ["script:npc_talk:대화"]

    # === Presence Text (상황 묘사) ===
    PRESENCE_TEXT = {
        # activity 기반
        "activity:사냥": "{name}가 활을 점검하고 있다.",
        "activity:식사": "{name}가 조용히 식사 중이다.",
        "activity:수면": "{name}가 조용히 잠들어 있다.",
        "activity:휴식": "{name}가 벽에 기대어 쉬고 있다.",

        # 장소 기반
        "0:24": "{name}가 사냥감을 추적하고 있다.",  # 사냥터
        "0:1": "{name}가 창가에 서서 밖을 바라본다.",  # 거실

        # 기본값
        "default": "{name}가 과묵하게 서 있다."
    }

    # === 대화 데이터 ===
    DIALOGUES = {
        "default": {"pages": ["......", "...세라다.", "사냥을 맡고 있다."]},
        "휴식": {"pages": ["......", "...좀 쉬는 중이다."]},
        "식사": {"pages": ["(조용히 먹고 있다)", "......", "...밀라의 요리는 괜찮다."]},
        "수면": {"pages": ["(자고 있다)", "......"]},
        "사냥": {"pages": ["......조용히 해라.", "...사냥감이 도망간다."]},
        "준비": {"pages": ["(활을 점검하고 있다)", "......"]},
        "정비": {"pages": ["(화살을 다듬고 있다)", "...장비 관리는 중요하다."]}
    }

    # === 장소 상수 ===
    MY_ROOM = (0, 8)
    DINING = (0, 3)
    LIVING = (0, 1)
    HUNTING = (0, 24)

    # === 시간대별 스케줄 ===
    SCHEDULE = [
        (5, 6, "준비", MY_ROOM),         # 5시~6시: 기상 (일찍)
        (7, 7, "식사", DINING),           # 7시~7:30: 아침식사 (짧게)
        (8, 12, "사냥", HUNTING),         # 8시~12시: 사냥
        (12, 13, "식사", DINING),         # 12시~13시: 점심식사
        (14, 18, "사냥", HUNTING),        # 14시~18시: 사냥
        (18, 19, "식사", DINING),         # 18:30~19:30: 저녁식사
        (20, 21, "정비", MY_ROOM),        # 20시~21:30: 장비정비
        (21, 5, "수면", MY_ROOM),         # 21:30~다음날 5시: 수면
    ]

    # === 이벤트 핸들러 ===
    def on_meet_player(self) -> dict:
        """플레이어와 처음 만났을 때"""
        if self._first_met:
            return None

        # 수면 중에는 이벤트 없음
        if self.get_activity() == "수면":
            return None

        self._first_met = True
        return {
            "type": "monologue",
            "pages": [
                "......",
                "...일어났군.",
                "...세라다. 사냥을 맡고 있다.",
                "...무리하지 마라."
            ],
            "time_consumed": 2,
            "button_type": "ok",
            "freeze_others": True
        }
