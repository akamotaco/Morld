# assets/characters/player.py - 플레이어 캐릭터 Asset
#
# 사용법:
#   from assets.characters.player import Player, NAME_OPTIONS
#   player = Player()
#   player.instantiate(0, REGION_ID, location_id)

from assets.base import Character


# 캐릭터 생성 옵션
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
        "items": [("old_knife", 1), ("leather_pouch", 1)]
    },
    {
        "id": "scholar",
        "label": "필기구와 책 한 권",
        "desc": "학자나 서기였을까?",
        "items": [("writing_tool", 1), ("old_book", 1)]
    },
    {
        "id": "craftsman",
        "label": "작은 도구함",
        "desc": "장인이나 기술자?",
        "items": [("small_toolbox", 1)]
    },
    {
        "id": "nothing",
        "label": "아무것도 없음",
        "desc": "완전히 빈손으로 시작",
        "items": []
    },
]


class Player(Character):
    unique_id = "player"
    name = "???"
    type = "male"
    tags = {
        "힘": 5,
        "지능": 5,
        "손재주": 5,
        "체력": 5,
        "신체:보통": 1,
        "나이": 22,
        "신뢰도": 0,
    }
    actions = ["rest", "sleep", "wait"]
    mood = []
