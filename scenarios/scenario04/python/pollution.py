# pollution.py - S04 오염 시스템
#
# S02의 pollution.py를 "던전 오염"으로 재해석.
# location별 오염도 = 해당 구역의 던전 기운 농도.
# 층별 기본 오염도 + 전투/이벤트로 추가 축적.
# location 오염도가 부식(장비)/침식(캐릭터)의 기반.
#
# 현재는 최소 인터페이스만 제공. 향후 S02 코드 기반 확장.

import morld
from events import subscribe_time_elapsed

# location별 오염도: (region_id, location_id) -> 오염도
_pollution_map = {}

# 기본 오염도 (층별)
_base_pollution = {}


def reset():
    """챕터 전환 시 리셋"""
    _pollution_map.clear()
    _base_pollution.clear()


def register_location(region_id: int, location_id: int, base_pollution: int = 0):
    """location을 오염 시스템에 등록"""
    key = (region_id, location_id)
    _pollution_map[key] = base_pollution
    _base_pollution[key] = base_pollution


def get_pollution(region_id: int, location_id: int) -> int:
    """location의 현재 오염도"""
    return _pollution_map.get((region_id, location_id), 0)


def add_pollution(region_id: int, location_id: int, amount: int):
    """오염도 추가 (전투, 사망 등)"""
    key = (region_id, location_id)
    current = _pollution_map.get(key, 0)
    _pollution_map[key] = max(0, current + amount)


def _on_time_elapsed(millis: int):
    """시간 경과: 오염도 자연 변동 (향후 구현)"""
    pass


subscribe_time_elapsed(_on_time_elapsed, min_interval=3600000)
