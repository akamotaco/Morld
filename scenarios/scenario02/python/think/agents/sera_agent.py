# think/agents/sera_agent.py - 세라 AI Agent (캐릭터 표준 ③)
#
# 캐릭터 표준: ①데이터/대사 = assets/characters/sera.py + ③AI = 이 파일
# (U4b에서 assets/characters/sera.py 로부터 분리 — think/agents/__init__.py 가
#  import 하는 시점에 @register_agent_class 가 레지스트리에 등록한다)

import morld

from think import BaseAgent, register_agent_class

_M = 60_000  # millis per minute


@register_agent_class("sera")
class SeraAgent(BaseAgent):
    """
    세라 AI - 저택 리더 + 사냥 + 경비 담당

    특징:
    - 과묵하고 듬직함
    - 저택 생존자들의 리더 (밀라, 리나가 신뢰함)
    - 사냥과 저택 순찰을 담당
    - 플레이어에게 무관심하지만 위험시 보호
    """

    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "strongest",
        "preferred_range": 60,
        "retreat_threshold": 0.15,
        "join_combat": True,
        "join_threshold": 20,
        "protect_player": True,
        "can_sprint": True,
    }
    COMBAT_DESPERATE_CHANCE = 0.9   # 포위 시 90% 필사 / 10% 체념

    _responsibility = 0.9
    _collectible_items = {"food_fish", "log", "wood_chip"}

    SCHEDULES = {
        "평일": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 300 * _M, "end": 330 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 8, "x": 120, "start": 330 * _M, "end": 360 * _M, "activity": "준비"},
            {"name": "아침순찰", "region_id": 0, "location_id": 12, "x": 300, "start": 360 * _M, "end": 420 * _M, "activity": "순찰"},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "훈련", "region_id": 0, "location_id": 13, "x": 300, "start": 480 * _M, "end": 540 * _M, "activity": "훈련"},  # 뒷마당
            {"name": "물자점검", "region_id": 0, "location_id": 16, "x": 90, "start": 540 * _M, "end": 570 * _M, "activity": "점검"},
            {"name": "오전활동", "start": 570 * _M, "end": 720 * _M, "activity": "취미낚시"},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "휴식", "region_id": 0, "location_id": 1, "x": 210, "start": 780 * _M, "end": 840 * _M, "activity": "휴식"},  # 거실
            {"name": "오후활동", "start": 840 * _M, "end": 1020 * _M, "activity": "취미벌목"},
            {"name": "저녁순찰", "region_id": 0, "location_id": 20, "x": 900, "start": 1020 * _M, "end": 1080 * _M, "activity": "순찰"},
            {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 1080 * _M, "end": 1110 * _M, "activity": "휴식"},  # 거실
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "휴식", "region_id": 0, "location_id": 8, "x": 90, "start": 1170 * _M, "end": 1200 * _M, "activity": "휴식"},  # 세라방
            {"name": "장비정비", "region_id": 0, "location_id": 8, "x": 90, "start": 1200 * _M, "end": 1260 * _M, "activity": "정비"},
            {"name": "저택 소등", "start": 1260 * _M, "end": 1290 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 8, "x": 90, "start": 1290 * _M, "end": 300 * _M, "activity": "수면"},
        ],
        "주말": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 300 * _M, "end": 330 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 8, "x": 120, "start": 330 * _M, "end": 360 * _M, "activity": "준비"},
            {"name": "아침순찰", "region_id": 0, "location_id": 12, "x": 300, "start": 360 * _M, "end": 420 * _M, "activity": "순찰"},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "훈련", "region_id": 0, "location_id": 13, "x": 300, "start": 480 * _M, "end": 540 * _M, "activity": "훈련"},  # 뒷마당
            {"name": "독서", "start": 540 * _M, "end": 720 * _M, "activity": "독서"},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "휴식", "region_id": 0, "location_id": 1, "x": 210, "start": 780 * _M, "end": 840 * _M, "activity": "휴식"},  # 거실
            {"name": "순찰", "region_id": 0, "location_id": 12, "x": 300, "start": 840 * _M, "end": 960 * _M, "activity": "순찰"},
            {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 960 * _M, "end": 1080 * _M, "activity": "휴식"},
            {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 1080 * _M, "end": 1110 * _M, "activity": "휴식"},  # 거실
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "취침준비", "region_id": 0, "location_id": 8, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "휴식"},  # 세라방
            {"name": "저택 소등", "start": 1260 * _M, "end": 1290 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 8, "x": 90, "start": 1290 * _M, "end": 300 * _M, "activity": "수면"},
        ],
    }

    owner_unique_id = "sera"
    _inventory_priority = {
        "tool": 90, "clothing": 70, "food": 60,
        "food_ingredient": 50, "drink_ingredient": 50,
        "material": 60, "seed": 30,
        "garden_tool": 30, "garden_supply": 30,
        "trinket": 10, "flower": 10,
    }

    # 일일 퀘스트 풀 (quest unique_id 목록)
    DAILY_QUEST_IDS = [
        "daily_gather_herb", "daily_gather_berry", "daily_firewood",
        "daily_fishing", "daily_clean", "daily_water_garden", "daily_deliver_food",
    ]
    DAILY_QUEST_COUNT = 3  # 매일 제공할 퀘스트 수

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self._memory["current_day_type"] = None
        self._memory["daily_quest_day"] = -1  # 마지막 일일퀘스트 선택일
        import survival
        survival.register_npc(unit_id)
        import temperature
        temperature.register_character(unit_id)
        import needs
        needs.register_character(unit_id)
        import pregnancy
        pregnancy.register_character(unit_id)

    def _select_daily_quests(self, day):
        """매일 아침 일일 퀘스트 3개 랜덤 선택 → _memory 저장"""
        import random
        selected = random.sample(self.DAILY_QUEST_IDS, self.DAILY_QUEST_COUNT)
        self._memory["daily_quest_list"] = selected
        self._memory["daily_quest_day"] = day

    def is_daily_quest_disabled(self):
        """일일퀘스트 영구 비활성화 여부 (호감>=0 or 복종>=50)"""
        player_id = morld.get_player_id()
        if not player_id:  # 부재 시 0 (None 아님) — CLAUDE.md prop 계약
            return False
        affection = morld.get_unit_prop(player_id, "관계:세라:호감") or 0
        submission = morld.get_unit_prop(player_id, "관계:세라:복종") or 0
        return affection >= 0 or submission >= 50

    def get_today_daily_quests(self):
        """오늘 활성화된 일일 퀘스트 ID 목록 반환 (disabled면 빈 리스트)"""
        if self.is_daily_quest_disabled():
            return []
        return list(self._memory.get("daily_quest_list", []))

    def think(self):
        """주말/평일 감지 + 일일 퀘스트 선택"""
        time_info = morld.get_time_info()
        day = time_info.get("day", 0)

        # 주말/평일 스케줄 전환
        day_type = "주말" if day % 7 >= 5 else "평일"
        if self._memory["current_day_type"] != day_type:
            self._memory["current_day_type"] = day_type
            self.set_base_schedule(self.SCHEDULES[day_type])

        # 일일 퀘스트 선택 (날짜 변경 시 1회)
        if self._memory["daily_quest_day"] != day:
            self._select_daily_quests(day)

        return super().think()

