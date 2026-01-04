# entities/characters/lina.py - 리나 캐릭터 정의

from entities.characters.base import BaseCharacter


class Lina(BaseCharacter):
    """리나 - 밝은 금발 단발머리의 활기찬 소녀"""

    # === 기본 정보 ===
    ID = 1
    NAME = "리나"
    TYPE = "female"
    START_LOCATION = (0, 7)  # 리나의 방

    # === 태그 (스탯) ===
    TAGS = {
        # 외모
        "외모:금발": 1,
        "외모:단발": 1,
        "외모:녹색눈": 1,
        # 성격
        "성격:명랑함": 1,
        "성격:활발함": 1,
        # 관계 (플레이어와)
        "애정": 0,
        "성욕": 0,
        "질투": 0,
        # 상태
        "피로": 0,
        "기분": 7,
    }

    # === 외관 묘사 ===
    APPEARANCE = {
        "default": "밝은 금발 단발머리의 활기찬 소녀. 녹색 눈이 반짝인다.",
        "기쁨": "환하게 웃고 있다. 에너지가 넘쳐 보인다.",
        "슬픔": "평소와 달리 기운이 없어 보인다.",
        "식사": "맛있게 음식을 먹고 있다.",
        "수면": "새근새근 잠들어 있다. 평화로운 얼굴이다.",
        "채집": "바구니를 들고 열심히 열매를 따고 있다."
    }

    # === 행동 목록 ===
    ACTIONS = ["script:npc_talk:대화"]

    # === Presence Text (상황 묘사) ===
    PRESENCE_TEXT = {
        # activity 기반
        "activity:채집": "{name}가 채집 준비를 하고 있다.",
        "activity:식사": "{name}가 맛있게 밥을 먹고 있다.",
        "activity:수면": "{name}가 새근새근 잠들어 있다.",
        "activity:휴식": "{name}가 기지개를 켜며 쉬고 있다.",

        # 장소 기반
        "0:23": "{name}가 열매를 따고 있다.",  # 채집터
        "0:1": "{name}가 소파에 앉아 발을 흔들고 있다.",  # 거실

        # 기본값
        "default": "{name}가 밝은 표정으로 주변을 둘러본다."
    }

    # === 대화 데이터 ===
    DIALOGUES = {
        "default": {"pages": ["안녕! 나는 리나야.", "오늘 날씨가 좋네~"]},
        "식사": {"pages": ["(음식을 먹고 있다)", "...냠냠, 맛있어!"]},
        "수면": {"pages": ["(자고 있다)", "...zzZ"]},
        "채집": {"pages": ["어? 왔어?", "나 지금 열매 따는 중이야!"]}
    }

    # === 장소 상수 ===
    MY_ROOM = (0, 7)
    DINING = (0, 3)
    GATHERING = (0, 23)  # 채집터
    LIVING = (0, 1)

    # === 시간대별 스케줄 ===
    # 기존 scheduleStack을 Python SCHEDULE로 변환
    # (시작시, 종료시, 활동, 위치)
    SCHEDULE = [
        (6, 7, "준비", MY_ROOM),      # 6시~7시: 기상
        (7, 8, "식사", DINING),       # 7시~8시: 아침식사
        (9, 12, "채집", GATHERING),   # 9시~12시: 채집
        (12, 13, "식사", DINING),     # 12시~13시: 점심식사
        (14, 17, "채집", GATHERING),  # 14시~17시: 채집
        (18, 19, "휴식", LIVING),     # 18시~19시: 귀가
        (19, 20, "식사", DINING),     # 19시~20시: 저녁식사
        (20, 22, "휴식", LIVING),     # 20시~22시: 자유시간
        (22, 6, "수면", MY_ROOM),     # 22시~다음날 6시: 수면
    ]

    # === 이벤트 핸들러 ===
    def on_meet_player(self) -> dict:
        """플레이어와 처음 만났을 때"""
        if not self._first_met:
            self._first_met = True
            return {
                "type": "monologue",
                "pages": [
                    "어? 너 누구야?",
                    "...아, 쓰러져 있던 사람?",
                    "나는 리나! 반가워~"
                ],
                "time_consumed": 5,
                "button_type": "ok"
            }
        return None
