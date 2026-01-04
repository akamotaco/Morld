# assets/characters/player.py - 플레이어 캐릭터 Asset
#
# 사용법:
#   from assets.characters.player import Player
#   player = Player()
#   player.instantiate(0, REGION_ID, location_id)

from assets.base import Character


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
    appearance = {}
    mood = []
    schedule_stack = [
        {
            "name": "대기",
            "schedule": [],
            "endConditionType": None,
            "endConditionParam": None
        }
    ]
