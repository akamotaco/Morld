# think/agents/lina_agent.py - 리나 AI Agent (캐릭터 표준 ③)
#
# 캐릭터 표준: ①데이터/대사 = assets/characters/lina.py + ③AI = 이 파일
# (U4b에서 assets/characters/lina.py 로부터 분리 — think/agents/__init__.py 가
#  import 하는 시점에 @register_agent_class 가 레지스트리에 등록한다)

import morld

from think import BaseAgent, register_agent_class

_M = 60_000  # millis per minute


@register_agent_class("lina")
class LinaAgent(BaseAgent):
    """
    리나 AI - 채집 + 빨래 담당

    특징:
    - 활발하고 명랑함
    - 채집과 빨래를 담당
    - 세라를 리더로 신뢰하고 따름
    - 플레이어 호감도 높으면 근처에 머무름
    """

    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",
        "target_priority": "weakest",
        "retreat_threshold": 0.3,
        "join_combat": True,
        "join_threshold": 40,
        "protect_player": True,
    }

    _responsibility = 0.3
    _collectible_items = {"food_fish"}

    SCHEDULE = [
        # x: Location 내 목표 좌표 (Pi-World, 1unit/sec 기준)
        # terrain.md 참고: 리나방 침대(x=120), 식당 식탁(x=90), 뒷마당 length=600, 채집터 length=900, 거실 소파(x=210)
        {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 360 * _M, "end": 390 * _M, "activity": "목욕"},
        {"name": "기상", "region_id": 0, "location_id": 7, "x": 120, "start": 390 * _M, "end": 420 * _M, "activity": "준비"},
        {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
        {"name": "빨래", "region_id": 0, "location_id": 13, "x": 300, "start": 480 * _M, "end": 540 * _M, "activity": "빨래"},  # 뒷마당
        {"name": "물자확인", "region_id": 0, "location_id": 16, "x": 90, "start": 540 * _M, "end": 555 * _M, "activity": "점검"},
        {"name": "오전활동", "start": 555 * _M, "end": 720 * _M, "activity": "취미채집"},
        {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
        {"name": "휴식", "region_id": 0, "location_id": 1, "x": 210, "start": 780 * _M, "end": 840 * _M, "activity": "휴식"},  # 거실
        {"name": "오후활동", "start": 840 * _M, "end": 1020 * _M, "activity": "취미채집"},
        {"name": "빨래걷기", "region_id": 0, "location_id": 13, "x": 300, "start": 1020 * _M, "end": 1080 * _M, "activity": "빨래"},  # 뒷마당
        {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 1080 * _M, "end": 1110 * _M, "activity": "휴식"},  # 거실
        {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
        {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 1170 * _M, "end": 1290 * _M, "activity": "휴식"},
        {"name": "저택 소등", "start": 1290 * _M, "end": 1320 * _M, "activity": "소등"},
        {"name": "수면", "region_id": 0, "location_id": 7, "x": 120, "start": 1320 * _M, "end": 360 * _M, "activity": "수면"},
    ]

    owner_unique_id = "lina"
    _inventory_priority = {
        "tool": 80, "clothing": 70, "food": 60,
        "food_ingredient": 80, "drink_ingredient": 80,
        "material": 40, "seed": 30,
        "garden_tool": 30, "garden_supply": 30,
        "trinket": 60, "flower": 10,
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

