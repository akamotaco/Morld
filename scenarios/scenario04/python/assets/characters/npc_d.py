# assets/characters/npc_d.py - 정규 NPC D: 거울/진실
#
# 던전 내 조우 (10F+ 권장). 특수 존재 (플레이어와 동일).
# 외유내강, 내성적, 비밀 많음.
# 던전의 힘 = 플레이어보다 압도적으로 강하지만 안 씀 (두려움).
# D 실신 = 재편성 트리거. D 사망 = 영구 삭제 (진실 루트 차단).
# 스토리 이벤트: 꺾기 완료 후 트리거.

from assets.base import Character
from assets.registry import register_character
from engine.character_props import COMMON_ACTION_PROPS


@register_character
class NpcD(Character):
    unique_id = "npc_d"
    name = "유이"  # 임시 이름

    base_str = 10
    base_agi = 11
    base_vit = 10
    base_mnd = 20   # 정신 극강 (침식 내성 최고)

    character_class = None  # 미정 (다양하게 가능)
    # 능력은 props의 "침식:저항배수", "던전:힘사용"으로 표현 (is_special 단일 플래그 제거)

    props = {
        **COMMON_ACTION_PROPS,
        "성격": "내성적",
        "성별": "여",
        "정규NPC": "D",
        # 능력 (원자 props — 기존 "특수:존재" 단일 플래그 대체)
        "침식:저항배수": 0.5,   # 침식 50%만 축적
        "던전:힘사용": 1,       # 던전의 힘 사용 가능 (향후 시스템용)
        "리더십": 3,            # 파티 풀 통솔 가능
        "D:힘공개": 0,          # 0=숨김, 1=일부공개, 2=완전공개
        "D:진실단계": 0,        # 스토리 진행도
        # 성격="내성적"은 PERSONALITY_TO_ARCHETYPE 미매핑 → 기본 stoic이지만,
        # 유이는 외유내강/두려움 톤이라 timid로 명시. D:진실단계 진행 시 gentle 전환은 후속.
        "아키타입": "timid",
    }

    REACTION_PROFILE = {
        "name": "유이",
        "archetype": "timid",
    }

    def get_describe_text(self):
        power_revealed = self.props.get("D:힘공개", 0)
        if power_revealed == 0:
            return "조용히 웅크리고 있는 소녀가 있다. 혼자인 것 같다."
        elif power_revealed == 1:
            return "어딘가 범상치 않은 기운을 풍기는 소녀가 있다."
        else:
            return "강대한 힘이 느껴지지만, 그 눈에는 두려움이 담겨 있다."

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
