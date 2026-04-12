# assets/characters/player.py - 플레이어 캐릭터
#
# 특수 존재: 던전의 힘 사용 가능, 침식 내성 높음

from assets.base import Character
from assets.registry import register_character


@register_character
class Player(Character):
    unique_id = "player"
    name = "플레이어"

    # 기본 스탯 (특수 존재: 정신 높음)
    base_str = 12
    base_agi = 10
    base_vit = 11
    base_mnd = 15  # 침식 저항 높음

    character_class = None  # 플레이어 선택 (향후)
    is_special = True  # 던전의 힘 사용 가능

    # 플레이어는 자기 자신을 초대할 수 없으므로 액션 비움
    actions = []

    props = {
        "특수:존재": 1,
        "can:invite_to_party": 1,       # NPC에게 "파티 초대" 액션 권한
        "can:dismiss_from_party": 1,    # 파티원 NPC에게 "파티 이탈" 액션 권한
    }

    def get_describe_text(self) -> str:
        return ""  # 플레이어는 묘사 없음

    def get_focus_text(self) -> str:
        return "나 자신이다."
