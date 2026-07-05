# think/agents/faye_agent.py - 페이 AI Agent (캐릭터 표준 ③)
#
# 캐릭터 표준: ①데이터/대사 = assets/characters/faye.py + ③AI = 이 파일
# (U4b에서 assets/characters/faye.py 로부터 분리)
#
# 캐릭터 데이터(TRADE_STOCK/BUYBACK_MAX_ITEMS)는 faye.py 소유 — 순환 import
# 방지를 위해 think 시점(런타임)에 lazy import 한다.

import morld

from think import BaseAgent, register_agent_class

_M = 60_000  # millis per minute


# ========================================
# FayeAgent 스케줄 헬퍼 함수 (모듈 레벨)
# ========================================

LIMBO_REGION   = 10
LIMBO_LOCATION = 0

_SCHEDULE = [
    # 월/화/수 (0~2): 도시 입구 (Region 2, Location 0)
    {"days": {0, 1, 2}, "region_id": 2, "location_id": 0},
    # 목/금 (3~4): 숲 오두막 (Region 3, Location 5)
    {"days": {3, 4}, "region_id": 3, "location_id": 5},
    # 토/일 (5~6): 비활성 (None)
]

_WORK_START_MINUTES = 8 * 60    # 08:00
_WORK_END_MINUTES   = 20 * 60   # 20:00


def _get_day_of_week(time_info):
    """게임 내부 날짜 → 요일 (0=월, ..., 6=일)"""
    year  = time_info.get("year",  1)
    month = time_info.get("month", 1)
    day   = time_info.get("day",   1)
    total = (year - 1) * 365 + (month - 1) * 30 + (day - 1)
    return total % 7


def _get_absolute_day(time_info):
    """전체 날 수 (리셋 판정용)"""
    year  = time_info.get("year",  1)
    month = time_info.get("month", 1)
    day   = time_info.get("day",   1)
    return (year - 1) * 365 + (month - 1) * 30 + (day - 1)


def _get_time_minutes(time_info):
    """현재 시각을 분 단위로 반환 (0~1439)"""
    hour   = time_info.get("hour",   0)
    minute = time_info.get("minute", 0)
    return hour * 60 + minute


def _get_active_schedule(time_info):
    """현재 시간에 활성화된 스케줄 반환. 비활성이면 None."""
    dow     = _get_day_of_week(time_info)
    minutes = _get_time_minutes(time_info)

    if minutes < _WORK_START_MINUTES or minutes >= _WORK_END_MINUTES:
        return None  # 야간

    for entry in _SCHEDULE:
        if dow in entry["days"]:
            return entry

    return None  # 토/일


def _teleport_to_limbo(unit_id, current_loc):
    """퇴근 텔레포트 — 플레이어가 같은 위치에 있으면 행동 로그 출력"""
    player_id = morld.get_player_id()
    if player_id and current_loc:
        player_loc = morld.get_unit_location(player_id)
        if (player_loc
                and player_loc[0] == current_loc[0]
                and player_loc[1] == current_loc[1]):
            morld.add_action_log("페이가 어디론가 사라졌습니다.")
    morld.set_unit_location(unit_id, LIMBO_REGION, LIMBO_LOCATION)


def _reset_trade_items(unit_id, keep_item_ids=None):
    """
    거래 아이템 리셋 + HP 최대치 회복
    호감도·욕망·관계 props는 유지됨

    keep_item_ids: 삭제하지 않을 아이템 ID 집합 (buyback 아이템)
    """
    max_hp = morld.get_unit_prop(unit_id, "생존:최대체력") or 100
    morld.set_unit_prop(unit_id, "생존:체력", max_hp)

    keep = keep_item_ids or set()
    inventory = morld.get_unit_inventory(unit_id) or {}
    for item_id_str, count in list(inventory.items()):
        item_id = int(item_id_str)
        if item_id not in keep:
            morld.remove_item(unit_id, item_id, count)

    from assets.registry import get_or_create_item_id
    from assets.characters.faye import TRADE_STOCK
    for unique_id, count, _price in TRADE_STOCK:
        item_id = get_or_create_item_id(unique_id)
        if item_id:
            morld.give_item(unit_id, item_id, count)



@register_agent_class("faye")
class FayeAgent(BaseAgent):
    """
    페이 AI — 떠돌이 상인

    특징:
    - 요일/시간대에 따라 도시 ↔ 숲 오두막 텔레포트
    - 야간/주말엔 대기소(Region 10)로 이동 — 사라짐
    - survival/needs/temperature 미등록 (HP만 관리)
    - romance 시스템 자연 상속
    """

    owner_unique_id = "faye"

    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",
        "retreat_threshold": 0.8,
        "join_combat": False,
    }

    def __init__(self, unit_id):
        super().__init__(unit_id)
        # survival/needs/temperature 미등록 → 포만감 감소·욕구 없음
        # romance 시스템은 Character 기반으로 자동 상속
        self._last_trade_day = -1

    def _trim_buyback(self, faye_char):
        """buyback 큐 정리: BUYBACK_MAX_ITEMS 초과분 제거 (퀘스트 아이템 제외)"""
        from assets.characters.faye import BUYBACK_MAX_ITEMS
        while len(faye_char._buyback_queue) > BUYBACK_MAX_ITEMS:
            old_id = faye_char._buyback_queue.pop(0)
            if morld.has_item(self.unit_id, old_id):
                morld.remove_item(self.unit_id, old_id, 1)

    def think(self):
        time_info = morld.get_time_info()
        if not time_info:
            self._insert_idle_job("대기", _M)
            self._action_taken = True
            return

        schedule    = _get_active_schedule(time_info)
        my_loc      = self.get_location()
        current_day = _get_absolute_day(time_info)

        # ── 비활성 시간 (야간 or 주말) ──
        if schedule is None:
            if my_loc and my_loc[0] != LIMBO_REGION:
                _teleport_to_limbo(self.unit_id, my_loc)
            self._insert_idle_job("대기", _M * 60)  # 1시간 후 재판정
            self._action_taken = True
            return

        # ── 활성 시간: 날짜 변경 → 거래 아이템·HP 리셋 ──
        if current_day != self._last_trade_day:
            from assets.characters import get_instance
            faye_char = get_instance(self.unit_id)
            if faye_char:
                self._trim_buyback(faye_char)
                keep_ids = (
                    set(faye_char._buyback_quest_ids)
                    | set(faye_char._buyback_queue)
                )
            else:
                keep_ids = set()
            _reset_trade_items(self.unit_id, keep_item_ids=keep_ids)
            self._last_trade_day = current_day

        # ── 목적지 다르면 즉시 텔레포트 (출근) ──
        target_region   = schedule["region_id"]
        target_location = schedule["location_id"]
        if not my_loc or my_loc[0] != target_region or my_loc[1] != target_location:
            morld.set_unit_location(self.unit_id, target_region, target_location)

        # ── 영업 대기 ──
        self._insert_idle_job("영업", _M * 30)
        self._action_taken = True

