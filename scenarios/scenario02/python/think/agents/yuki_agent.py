# think/agents/yuki_agent.py - 유키 AI Agent (캐릭터 표준 ③)
#
# 캐릭터 표준: ①데이터/대사 = assets/characters/yuki.py + ③AI = 이 파일
# (U4b에서 assets/characters/yuki.py 로부터 분리 — think/agents/__init__.py 가
#  import 하는 시점에 @register_agent_class 가 레지스트리에 등록한다)

import morld

from think import BaseAgent, register_agent_class

_M = 60_000  # millis per minute


@register_agent_class("yuki")
class YukiAgent(BaseAgent):
    """
    유키 AI - 도심 은신처 생활

    특징:
    - 수줍고 얌전함
    - 은신처에서 조용히 지냄
    - 엘라를 의지함
    """

    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",
        "retreat_threshold": 0.9,
        "join_combat": False,
        "protect_player": False,
    }
    COMBAT_DESPERATE_CHANCE = 0.2   # 포위 시 20% 필사 / 80% 체념

    _responsibility = 0.5
    _collectible_items = set()

    # 도심 은신처 스케줄 (region_id=2, location_id=5=은신처, length=180)
    SCHEDULE = [
        {"name": "목욕", "region_id": 2, "location_id": 5, "x": 150, "start": 420 * _M, "end": 450 * _M, "activity": "목욕"},
        {"name": "기상", "region_id": 2, "location_id": 5, "x": 90, "start": 450 * _M, "end": 480 * _M, "activity": "준비"},
        {"name": "아침식사", "region_id": 2, "location_id": 5, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "식사"},
        {"name": "청소", "region_id": 2, "location_id": 5, "x": 60, "start": 540 * _M, "end": 660 * _M, "activity": "청소"},
        {"name": "점검", "region_id": 2, "location_id": 5, "x": 120, "start": 660 * _M, "end": 675 * _M, "activity": "점검"},
        {"name": "오전활동", "start": 675 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
            {"activity": "요리", "condition": "can_cook"},
            {"activity": "독서", "condition": None, "region_id": 2, "location_id": 5, "x": 120},
        ]},
        {"name": "점심식사", "region_id": 2, "location_id": 5, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
        {"name": "정원", "region_id": 2, "location_id": 5, "x": 160, "start": 780 * _M, "end": 900 * _M, "activity": "정원"},
        {"name": "휴식", "region_id": 2, "location_id": 5, "x": 120, "start": 900 * _M, "end": 1020 * _M, "activity": "휴식"},
        {"name": "자유시간", "region_id": 2, "location_id": 5, "x": 120, "start": 1020 * _M, "end": 1080 * _M, "activity": "휴식"},  # 은신처
        {"name": "저녁식사", "region_id": 2, "location_id": 5, "x": 90, "start": 1080 * _M, "end": 1140 * _M, "activity": "식사"},
        {"name": "독서", "region_id": 2, "location_id": 5, "x": 120, "start": 1140 * _M, "end": 1320 * _M, "activity": "휴식"},
        {"name": "수면", "region_id": 2, "location_id": 5, "x": 120, "start": 1320 * _M, "end": 420 * _M, "activity": "수면"},
    ]

    owner_unique_id = "yuki"
    _inventory_priority = {
        "tool": 80, "clothing": 70, "food": 60,
        "food_ingredient": 50, "drink_ingredient": 50,
        "material": 40, "seed": 30,
        "garden_tool": 30, "garden_supply": 30,
        "trinket": 70, "flower": 80,
    }

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self.SCHEDULE)
        import survival
        survival.register_npc(unit_id)
        import temperature
        temperature.register_character(unit_id)
        import needs
        needs.register_character(unit_id)
        import pregnancy
        pregnancy.register_character(unit_id)

