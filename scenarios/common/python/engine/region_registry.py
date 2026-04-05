# region_registry.py — Region ID 동적 탐색
#
# REGION_IDS = [0, 2, 3] 하드코딩을 제거하기 위한 공용 모듈.
# morld.region_exists()로 존재하는 Region을 자동 탐색하고 캐시.
# 챕터 전환 시 reset() 호출로 캐시 무효화.

import morld

_region_ids = None
_MAX_PROBE = 20  # 탐색 범위 상한 (Region ID 0~19)


def get_region_ids():
    """현재 로드된 Region ID 목록 반환 (lazy, cached)"""
    global _region_ids
    if _region_ids is None:
        _region_ids = []
        for rid in range(_MAX_PROBE):
            try:
                if morld.region_exists(rid):
                    _region_ids.append(rid)
            except Exception:
                pass
    return _region_ids


def reset():
    """챕터 전환 시 호출 — 캐시 초기화"""
    global _region_ids
    _region_ids = None
