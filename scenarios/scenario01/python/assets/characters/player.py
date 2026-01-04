# assets/characters/player.py - 플레이어 캐릭터 Asset
# 방 탈출 시나리오: 정체불명의 주인공

from assets import registry

# ========================================
# Asset 정의
# ========================================

PLAYER = {
    "unique_id": "player",
    "name": "플레이어",
    "type": "male",
    "tags": {},
    "actions": [],
    "focus_text": {},
    "mood": []
}


def register():
    """플레이어 Asset 등록"""
    registry.register_character(PLAYER)
