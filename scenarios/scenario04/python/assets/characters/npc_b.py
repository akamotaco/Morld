# assets/characters/npc_b.py - 정규 NPC B: 대척점/적대자
#
# 마을 정기 방문. 전직 모험가.
# 정의감, 의심, 행동파. 던전의 위화감을 감지.
# 플레이어의 힘을 깨닫으면 경계 → 적대 가능.
# 세계의 지식 이중 경로 (점진 + B 고유 이벤트 급진).
# 마을 혼란도 핵심 트리거. 군대 소환 가능.

from assets.base import Character
from assets.registry import register_character


@register_character
class NpcB(Character):
    unique_id = "npc_b"
    name = "도현"  # 임시 이름

    base_str = 14
    base_agi = 11
    base_vit = 13
    base_mnd = 10

    character_class = "타격수"

    props = {
        "성격": "정의감",
        "성별": "남",
        "정규NPC": "B",
        "세계의지식": 0,       # 이중 경로 축적
        "B:경계단계": 0,       # 0=무관심, 1=의심, 2=확신, 3=적대
        "B:군대연결": 1,       # 군대 소환 가능 여부
    }

    def get_describe_text(self):
        return "노련해 보이는 모험가가 술집에서 주위를 살피고 있다."

    def get_focus_text(self):
        return (
            f"{self.name}. 단단한 체격에 날카로운 눈빛. "
            "과거에 무언가를 겪은 사람의 표정이다."
        )
