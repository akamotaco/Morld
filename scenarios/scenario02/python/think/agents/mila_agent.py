# think/agents/mila_agent.py - 밀라 AI Agent (캐릭터 표준 ③)
#
# 캐릭터 표준: ①데이터/대사 = assets/characters/mila.py + ③AI = 이 파일
# (U4b에서 assets/characters/mila.py 로부터 분리 — think/agents/__init__.py 가
#  import 하는 시점에 @register_agent_class 가 레지스트리에 등록한다)

import morld

from think import BaseAgent, register_agent_class

_M = 60_000  # millis per minute


@register_agent_class("mila")
class MilaAgent(BaseAgent):
    """
    밀라 AI - 요리 + 실내 관리 담당

    특징:
    - 다정하고 걱정 많음
    - 식사 준비와 실내 청소를 담당
    - 세라를 리더로 신뢰하고 따름
    - 플레이어가 아프면 걱정하며 지켜봄
    - 계절별로 스케줄이 달라짐
    """

    # 전투 AI — 은퇴한 전설의 전사
    # 평소: 전투 회피. 하지만 저택이 공격받으면(적대 세력 감지) 본기 발동.
    # 본기 시 aggressive + 후퇴 안 함 → 외부 침입의 최종 장벽.
    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",    # 본기: 공격적
        "retreat_threshold": 0.05,       # 거의 후퇴 안 함
        "join_combat": True,             # 동료 위기 시 참전
        "join_threshold": 30,
        "protect_player": False,         # 추방 후에는 적대
    }
    COMBAT_DESPERATE_CHANCE = 1.0   # 포위 시 100% 필사 (숨겨진 고수)

    _responsibility = 0.8
    _collectible_items = {"branch"}

    # 계절별 스케줄
    # x: Location 내 목표 좌표 (Pi-World, 1unit/sec 기준)
    # 밀라방(180), 주방(180), 식당(180), 거실(360), 뒷마당(600)
    SCHEDULES = {
        "봄": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 300 * _M, "end": 330 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 330 * _M, "end": 345 * _M, "activity": "준비"},
            {"name": "아침 소등", "start": 345 * _M, "end": 360 * _M, "activity": "소등"},
            {"name": "물자점검", "region_id": 0, "location_id": 16, "x": 90, "start": 360 * _M, "end": 380 * _M, "activity": "점검"},
            {"name": "아침준비", "start": 380 * _M, "end": 420 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "설거지"},
            {"name": "청소", "start": 540 * _M, "end": 660 * _M, "dynamic": True, "candidates": [
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심준비", "start": 660 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
                {"activity": "연료장전", "condition": "need_fuel"},
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "정원가꾸기", "region_id": 0, "location_id": 13, "x": 300, "start": 780 * _M, "end": 900 * _M, "activity": "정원"},  # 봄: 정원 가꾸기
            {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 900 * _M, "end": 1020 * _M, "activity": "휴식"},  # 거실 소파
            {"name": "저녁준비", "start": 1020 * _M, "end": 1080 * _M, "dynamic": True, "candidates": [
                {"activity": "연료장전", "condition": "need_fuel"},
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "저택 점등", "start": 1080 * _M, "end": 1110 * _M, "activity": "점등"},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "취침준비", "region_id": 0, "location_id": 9, "x": 120, "start": 1260 * _M, "end": 1290 * _M, "activity": "휴식"},  # 밀라방
            {"name": "저택 소등", "start": 1290 * _M, "end": 1320 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1320 * _M, "end": 300 * _M, "activity": "수면"},
        ],
        "여름": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 240 * _M, "end": 270 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 270 * _M, "end": 285 * _M, "activity": "준비"},  # 여름: 일찍 기상
            {"name": "아침 소등", "start": 285 * _M, "end": 300 * _M, "activity": "소등"},
            {"name": "물자점검", "region_id": 0, "location_id": 16, "x": 90, "start": 300 * _M, "end": 320 * _M, "activity": "점검"},
            {"name": "아침준비", "start": 320 * _M, "end": 360 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 360 * _M, "end": 420 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "설거지"},
            {"name": "청소", "start": 480 * _M, "end": 600 * _M, "dynamic": True, "candidates": [
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 600 * _M, "end": 660 * _M, "activity": "휴식"},  # 거실
            {"name": "점심준비", "start": 660 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
                {"activity": "연료장전", "condition": "need_fuel"},
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "낮잠", "region_id": 0, "location_id": 9, "x": 120, "start": 780 * _M, "end": 900 * _M, "activity": "휴식"},  # 여름: 더위 피해 낮잠
            {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 900 * _M, "end": 1020 * _M, "activity": "휴식"},  # 거실 소파
            {"name": "저녁준비", "start": 1020 * _M, "end": 1080 * _M, "dynamic": True, "candidates": [
                {"activity": "연료장전", "condition": "need_fuel"},
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "저택 점등", "start": 1080 * _M, "end": 1110 * _M, "activity": "점등"},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "취침준비", "region_id": 0, "location_id": 9, "x": 120, "start": 1260 * _M, "end": 1350 * _M, "activity": "휴식"},  # 밀라방
            {"name": "저택 소등", "start": 1350 * _M, "end": 1380 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1380 * _M, "end": 240 * _M, "activity": "수면"},  # 여름: 늦게 잠
        ],
        "가을": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 300 * _M, "end": 330 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 330 * _M, "end": 345 * _M, "activity": "준비"},
            {"name": "아침 소등", "start": 345 * _M, "end": 360 * _M, "activity": "소등"},
            {"name": "물자점검", "region_id": 0, "location_id": 16, "x": 90, "start": 360 * _M, "end": 380 * _M, "activity": "점검"},
            {"name": "아침준비", "start": 380 * _M, "end": 420 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "설거지"},
            {"name": "청소", "start": 540 * _M, "end": 660 * _M, "dynamic": True, "candidates": [
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심준비", "start": 660 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
                {"activity": "연료장전", "condition": "need_fuel"},
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "저장식품준비", "start": 780 * _M, "end": 960 * _M, "dynamic": True, "candidates": [
                {"activity": "연료장전", "condition": "need_fuel"},
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 960 * _M, "end": 1020 * _M, "activity": "휴식"},  # 거실
            {"name": "저녁준비", "start": 1020 * _M, "end": 1080 * _M, "dynamic": True, "candidates": [
                {"activity": "연료장전", "condition": "need_fuel"},
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "저택 점등", "start": 1080 * _M, "end": 1110 * _M, "activity": "점등"},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "취침준비", "region_id": 0, "location_id": 9, "x": 120, "start": 1260 * _M, "end": 1290 * _M, "activity": "휴식"},  # 밀라방
            {"name": "저택 소등", "start": 1290 * _M, "end": 1320 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1320 * _M, "end": 300 * _M, "activity": "수면"},
        ],
        "겨울": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 360 * _M, "end": 390 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 390 * _M, "end": 405 * _M, "activity": "준비"},  # 겨울: 늦게 기상
            {"name": "아침 소등", "start": 405 * _M, "end": 420 * _M, "activity": "소등"},
            {"name": "물자점검", "region_id": 0, "location_id": 16, "x": 90, "start": 420 * _M, "end": 440 * _M, "activity": "점검"},
            {"name": "아침준비", "start": 440 * _M, "end": 480 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 540 * _M, "end": 600 * _M, "activity": "설거지"},
            {"name": "청소", "start": 600 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심준비", "start": 720 * _M, "end": 780 * _M, "dynamic": True, "candidates": [
                {"activity": "연료장전", "condition": "need_fuel"},
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 780 * _M, "end": 840 * _M, "activity": "식사"},
            {"name": "휴식", "region_id": 0, "location_id": 1, "x": 210, "start": 840 * _M, "end": 960 * _M, "activity": "휴식"},  # 겨울: 실내 휴식 (소파)
            {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 960 * _M, "end": 1000 * _M, "activity": "휴식"},  # 거실
            {"name": "저택 점등", "start": 1000 * _M, "end": 1020 * _M, "activity": "점등"},  # 겨울: 일찍 점등
            {"name": "저녁준비", "start": 1020 * _M, "end": 1110 * _M, "dynamic": True, "candidates": [
                {"activity": "연료장전", "condition": "need_fuel"},
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1230 * _M, "activity": "정리"},
            {"name": "저택 소등", "start": 1230 * _M, "end": 1260 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1260 * _M, "end": 360 * _M, "activity": "수면"},  # 겨울: 일찍 잠
        ],
    }

    owner_unique_id = "mila"
    _inventory_priority = {
        "tool": 80, "clothing": 70, "food": 90,
        "food_ingredient": 60, "drink_ingredient": 60,
        "material": 40, "seed": 70,
        "garden_tool": 50, "garden_supply": 50,
        "trinket": 10, "flower": 10,
    }

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self._memory["current_season"] = None
        # 초기 스케줄은 think()에서 계절 확인 후 설정
        import survival
        survival.register_npc(unit_id)
        import temperature
        temperature.register_character(unit_id)
        import needs
        needs.register_character(unit_id)
        import pregnancy
        pregnancy.register_character(unit_id)

    def _get_current_season(self):
        """현재 계절 반환 (게임 날짜 기반)"""
        time_info = morld.get_time_info()
        month = time_info.get("month", 3)  # 기본값: 3월 (봄)

        # 월 -> 계절 매핑 (3-5: 봄, 6-8: 여름, 9-11: 가을, 12-2: 겨울)
        if month in (3, 4, 5):
            return "봄"
        elif month in (6, 7, 8):
            return "여름"
        elif month in (9, 10, 11):
            return "가을"
        else:  # 12, 1, 2
            return "겨울"

    def think(self):
        """밀라의 행동 결정 - 계절에 따라 스케줄 변경"""
        # 계절이 바뀌면 기본 스케줄 교체
        season = self._get_current_season()
        if season != self._memory["current_season"]:
            self._memory["current_season"] = season
            new_schedule = self.SCHEDULES.get(season, self.SCHEDULES["봄"])
            self.set_base_schedule(new_schedule)
            print(f"[MilaAgent] 계절 변경: {season}")

        # 나머지는 BaseAgent.think()에 위임
        return super().think()

