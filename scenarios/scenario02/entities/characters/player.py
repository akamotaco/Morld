# entities/characters/player.py - 플레이어 캐릭터 정의

from entities.characters.base import BaseCharacter


class Player(BaseCharacter):
    """플레이어 캐릭터"""

    # === 기본 정보 ===
    ID = 0
    NAME = "???"
    TYPE = "male"
    START_LOCATION = (0, 21)  # 숲 깊은 곳에서 시작

    # === 태그 (스탯) ===
    TAGS = {
        # 기본 스탯
        "힘": 5,
        "지능": 5,
        "손재주": 5,
        "체력": 5,
        # 신체 (기본값, 캐릭터 생성 시 변경)
        "신체:보통": 1,
        # 나이
        "나이": 22,
        # 그룹 내 지위
        "신뢰도": 0,
    }

    # === 외관 묘사 ===
    APPEARANCE = {
        "default": "평범한 남자. 기억을 잃은 듯하다."
    }

    # === 행동 목록 ===
    ACTIONS = ["rest", "sleep", "wait"]

    # === 스케줄 (비어있음 - PlayerSystem이 override) ===
    SCHEDULE = []

    # 플레이어는 think()가 호출되어도 PlayerSystem이 override하므로
    # 기본 구현은 None 반환
    def think(self, game_time: int) -> dict:
        """플레이어는 Python에서 자동 행동하지 않음"""
        # 향후 자동 수면 등 구현 가능
        return None

    def decide(self, game_time: int) -> dict:
        """플레이어는 사용자 입력으로 행동 결정"""
        return None


# === 캐릭터 생성 옵션 ===

NAME_OPTIONS = ["카이", "레온", "아론", "유진"]

AGE_OPTIONS = [
    {"value": 17, "label": "17세 - 아직 어린 소년"},
    {"value": 22, "label": "22세 - 청년"},
    {"value": 30, "label": "30세 - 성숙한 장년"},
]

BODY_OPTIONS = [
    {"value": "왜소", "label": "왜소함 - 작고 가벼운 몸"},
    {"value": "보통", "label": "보통 - 평범한 체격"},
    {"value": "장신", "label": "장신 - 키가 크고 늘씬함"},
    {"value": "거구", "label": "거구 - 크고 건장한 몸"},
]

EQUIPMENT_OPTIONS = [
    {
        "id": "hunter",
        "label": "낡은 칼과 가죽 주머니",
        "desc": "전직 사냥꾼의 기억?",
        "items": [(10, 1), (11, 1)]  # (item_id, count)
    },
    {
        "id": "scholar",
        "label": "필기구와 책 한 권",
        "desc": "학자나 서기였을까?",
        "items": [(20, 1), (21, 1)]
    },
    {
        "id": "craftsman",
        "label": "작은 도구함",
        "desc": "장인이나 기술자?",
        "items": [(30, 1)]
    },
    {
        "id": "nothing",
        "label": "아무것도 없음",
        "desc": "완전히 빈손으로 시작",
        "items": []
    },
]
