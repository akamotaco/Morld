# assets/characters/npc_c.py - 정규 NPC C: 트라우마/부활
#
# 던전 내 조우 (5~10F). 체류자 출신.
# 파티 전멸 후 삶의 의미 상실. 과묵, 체념적.
# 케어하면 과거의 강력한 전투력 부활 (AP 스킬 최강).
# 방치하면 자살 암시.

from assets.base import Character
from assets.registry import register_character
from engine.character_props import COMMON_ACTION_PROPS


@register_character
class NpcC(Character):
    unique_id = "npc_c"
    name = "레이"  # 임시 이름

    base_str = 16   # 잠재 전투력 최강
    base_agi = 14
    base_vit = 15
    base_mnd = 7    # 정신 낮음 (트라우마)

    character_class = "타격수"  # 부활 시 최강 근접

    props = {
        **COMMON_ACTION_PROPS,
        "성격": "체념",
        "성별": "여",
        "정규NPC": "C",
        "C:상태": "무기력",     # 무기력 → 회복 → 부활
        "C:신뢰축적": 0,        # 플레이어 케어 누적
        "C:부활임계": 50,       # 이 값 도달 시 전투력 부활
        # 성격="체념"은 PERSONALITY_TO_ARCHETYPE 미매핑 → 기본 stoic.
        # 레이는 트라우마로 감정 봉인된 톤 — stoic 일치, 명시로 의도 고정.
        "아키타입": "stoic",
    }

    REACTION_PROFILE = {
        "name": "레이",
        "archetype": "stoic",
    }

    def get_describe_text(self):
        state = self.props.get("C:상태", "무기력")
        if state == "무기력":
            return "텅 빈 눈으로 벽을 바라보는 사람이 있다."
        elif state == "회복":
            return "조금은 생기가 돌아온 표정의 여자가 앉아 있다."
        else:
            return "날카로운 눈빛의 전사가 무기를 점검하고 있다."

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
