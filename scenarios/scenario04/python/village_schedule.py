# village_schedule.py - S04 마을 NPC 스케줄
#
# 마을 거주 NPC (상점 주인, 대장간 등)의 스케줄.
# 영업 시간/위치 관리. 랜덤 NPC/파티원은 스케줄 없음.
#
# S02의 schedule_mixin 패턴 참고, 경량화.

import morld
from events import subscribe_time_elapsed

# === 마을 시설 NPC 스케줄 ===

# (시작시간, 종료시간, location_id)
VILLAGE_SCHEDULES = {
    "잡화점주인": {
        "name": "잡화점 주인",
        "home": 3,       # 잡화점 (loc 3)
        "schedule": [
            (8, 20, 3),   # 08:00~20:00 잡화점 영업
            (20, 8, 1),   # 20:00~08:00 여관 (퇴근)
        ],
    },
    "대장간주인": {
        "name": "대장간 주인",
        "home": 2,       # 대장간 (loc 2)
        "schedule": [
            (6, 21, 2),   # 06:00~21:00 대장간 영업
            (21, 6, 1),   # 21:00~06:00 여관
        ],
    },
    "구호소의사": {
        "name": "구호소 의사",
        "home": 5,       # 구호소 (loc 5)
        "schedule": [
            (0, 24, 5),   # 24시간 상주
        ],
    },
    "정화사": {
        "name": "정화사",
        "home": 6,       # 정화소 (loc 6)
        "schedule": [
            (9, 18, 6),   # 09:00~18:00 정화소 영업
            (18, 22, 4),  # 18:00~22:00 술집 (퇴근 후)
            (22, 9, 1),   # 22:00~09:00 여관
        ],
    },
    "술집주인": {
        "name": "술집 주인",
        "home": 4,       # 술집 (loc 4)
        "schedule": [
            (16, 2, 4),   # 16:00~02:00 술집 영업
            (2, 16, 1),   # 02:00~16:00 여관 (낮잠)
        ],
    },
}

# === 상태 ===
_npc_units = {}  # schedule_key -> unit_id
_accumulated_millis = 0


def reset():
    global _accumulated_millis
    _npc_units.clear()
    _accumulated_millis = 0


def initialize():
    """마을 NPC 생성 및 스케줄 등록"""
    for key, data in VILLAGE_SCHEDULES.items():
        unit_id = morld.create_id("character")
        morld.add_character(unit_id, data["name"], 0, data["home"], x=50)
        morld.set_unit_prop(unit_id, "마을NPC", key)
        morld.set_unit_prop(unit_id, "영업중", 0)
        _npc_units[key] = unit_id
        print(f"[schedule] Village NPC created: {data['name']} (id={unit_id})")


def _on_time_elapsed(millis: int):
    """시간 경과: NPC 위치 업데이트"""
    global _accumulated_millis
    _accumulated_millis += millis

    # 30분마다 체크
    if _accumulated_millis < 1800000:
        return
    _accumulated_millis = 0

    time_info = morld.get_time_info()
    if not time_info:
        return

    hour = time_info.get("hour", 0)

    for key, data in VILLAGE_SCHEDULES.items():
        unit_id = _npc_units.get(key)
        if not unit_id:
            continue

        target_loc = _get_scheduled_location(data["schedule"], hour)
        if target_loc is not None:
            current_loc = morld.get_unit_location(unit_id)
            if current_loc and current_loc[1] != target_loc:
                morld.set_unit_location(unit_id, 0, target_loc, x=50)

            # 영업 상태 갱신
            is_at_work = (target_loc == data["home"])
            morld.set_unit_prop(unit_id, "영업중", 1 if is_at_work else 0)


def _get_scheduled_location(schedule: list, current_hour: int) -> int:
    """현재 시간에 해당하는 location 반환"""
    for start, end, loc_id in schedule:
        if start < end:
            if start <= current_hour < end:
                return loc_id
        else:  # 자정을 넘기는 경우
            if current_hour >= start or current_hour < end:
                return loc_id
    return None


def is_shop_open(schedule_key: str) -> bool:
    """해당 시설이 영업 중인지"""
    unit_id = _npc_units.get(schedule_key)
    if not unit_id:
        return False
    return bool(morld.get_unit_prop(unit_id, "영업중"))


def get_village_npc_id(schedule_key: str) -> int:
    return _npc_units.get(schedule_key)


subscribe_time_elapsed(_on_time_elapsed, min_interval=1800000)
