# assets/characters/npc_a.py - 정규 NPC A: 욕망의 동반자
#
# 마을 정기 방문. 정보상/상인 계열.
# 탐욕적이지만 유쾌. 플레이어의 비밀에 개의치 않음.
# "넌 리셋해도 살아남잖아? 최고의 파트너야"

from assets.base import Character
from assets.registry import register_character
from engine.character_props import COMMON_ACTION_PROPS


@register_character
class NpcA(Character):
    unique_id = "npc_a"
    name = "카엘"  # 임시 이름

    base_str = 9
    base_agi = 12
    base_vit = 9
    base_mnd = 13

    character_class = "거간꾼"

    props = {
        **COMMON_ACTION_PROPS,
        "성격": "탐욕",
        "성별": "남",
        "정규NPC": "A",
        "소문:관심": 1,  # 던전 소문/정보에 관심
        # 성격="탐욕"의 PERSONALITY_TO_ARCHETYPE 디폴트는 cold지만,
        # 카엘은 유쾌/거간꾼 톤이라 cheerful로 명시 오버라이드.
        "아키타입": "cheerful",
    }

    REACTION_PROFILE = {
        "name": "카엘",
        "archetype": "cheerful",
    }

    def get_describe_text(self):
        return "눈이 번쩍이는 상인이 여관 한쪽에서 장사 준비를 하고 있다."

    def get_focus_text(self):
        """첫 만남이면 시그니처 인사 (character.yaml first_meet), 이후 일반 흐름."""
        import morld
        import npc_dialogue

        player_id = morld.get_player_id()
        progress_key = f"관계:{self.name}:진척도"
        if player_id and morld.get_unit_prop(player_id, progress_key) <= 0:
            morld.set_unit_prop(player_id, progress_key, 1)
            line = npc_dialogue.get_line(self.instance_id, "first_meet", name=self.name)
            return f"[{self.name}] \"{line}\""
        return super().get_focus_text()
