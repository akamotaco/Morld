# think/agents/ella_agent.py - 엘라 AI Agent (캐릭터 표준 ③)
#
# 캐릭터 표준: ①데이터/대사 = assets/characters/ella.py + ③AI = 이 파일
# (U4b에서 assets/characters/ella.py 로부터 분리 — think/agents/__init__.py 가
#  import 하는 시점에 @register_agent_class 가 레지스트리에 등록한다)

import morld

from think import BaseAgent, register_agent_class

_M = 60_000  # millis per minute


@register_agent_class("ella")
class EllaAgent(BaseAgent):
    """
    엘라 AI - 도심 생존자 리더

    특징:
    - 냉정하고 리더십 있음
    - 유키를 보호하고 돌봄
    - 외부인에 대한 불신
    """

    BATTLE_BEHAVIOR = {
        "combat_style": "defensive",
        "target_priority": "nearest",
        "preferred_range": 60,
        "retreat_threshold": 0.2,
        "join_combat": True,
        "join_threshold": 30,
        "protect_player": False,
        "can_sprint": True,
    }
    COMBAT_DESPERATE_CHANCE = 0.7   # 포위 시 70% 필사 / 30% 체념

    _responsibility = 0.8
    _collectible_items = {"branch", "log"}

    # 도심 은신처 스케줄 (region_id=2)
    SCHEDULE = [
        # x: Location 내 목표 좌표 (Pi-World, 1unit/sec 기준)
        # 은신처(180), 약국(180), 편의점(180), 도시입구(600)
        {"name": "기상", "region_id": 2, "location_id": 5, "x": 90, "start": 360 * _M, "end": 390 * _M, "activity": "준비"},
        {"name": "목욕", "region_id": 2, "location_id": 5, "x": 150, "start": 390 * _M, "end": 420 * _M, "activity": "목욕"},
        {"name": "아침식사", "region_id": 2, "location_id": 5, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
        {"name": "준비", "region_id": 2, "location_id": 5, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "준비"},  # 은신처
        {"name": "정찰", "region_id": 2, "location_id": 3, "x": 90, "start": 540 * _M, "end": 660 * _M, "activity": "순찰"},  # 약국
        {"name": "물자점검", "region_id": 2, "location_id": 5, "x": 120, "start": 660 * _M, "end": 690 * _M, "activity": "점검"},
        {"name": "순찰", "region_id": 2, "location_id": 0, "x": 300, "start": 690 * _M, "end": 720 * _M, "activity": "순찰"},
        {"name": "점심식사", "region_id": 2, "location_id": 5, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
        {"name": "관리", "region_id": 2, "location_id": 5, "x": 90, "start": 780 * _M, "end": 960 * _M, "activity": "관리"},
        {"name": "정찰", "region_id": 2, "location_id": 0, "x": 300, "start": 960 * _M, "end": 1020 * _M, "activity": "순찰"},  # 도시입구
        {"name": "자유시간", "region_id": 2, "location_id": 5, "x": 90, "start": 1020 * _M, "end": 1080 * _M, "activity": "휴식"},  # 은신처
        {"name": "저녁식사", "region_id": 2, "location_id": 5, "x": 90, "start": 1080 * _M, "end": 1140 * _M, "activity": "식사"},
        {"name": "휴식", "region_id": 2, "location_id": 5, "x": 90, "start": 1140 * _M, "end": 1320 * _M, "activity": "휴식"},
        {"name": "수면", "region_id": 2, "location_id": 5, "x": 90, "start": 1320 * _M, "end": 360 * _M, "activity": "수면"},
    ]

    owner_unique_id = "ella"
    _inventory_priority = {
        "tool": 90, "clothing": 70, "food": 60,
        "food_ingredient": 50, "drink_ingredient": 50,
        "material": 40, "seed": 30,
        "garden_tool": 30, "garden_supply": 30,
        "trinket": 10, "flower": 10,
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

