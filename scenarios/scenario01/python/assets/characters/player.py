# assets/characters/player.py - 플레이어 캐릭터 Asset
# 방 탈출 시나리오: 정체불명의 주인공

from assets.base import Character


class Player(Character):
    """플레이어 캐릭터"""
    unique_id = "player"
    name = "플레이어"
    type = "male"
    tags = {}
    actions = []
    mood = []
