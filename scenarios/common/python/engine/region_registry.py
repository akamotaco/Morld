# region_registry.py — Region ID 레지스트리
#
# 정적 Region: morld.region_exists()로 자동 탐색 (ID 0~_MAX_PROBE)
# 동적 Region: register_dynamic(rid) / unregister_dynamic(rid) 명시 등록
# 챕터 전환 시 reset() 호출로 전체 초기화.

import morld

_region_ids = None
_MAX_PROBE = 20  # 정적 탐색 범위 상한 (Region ID 0~19)
_dynamic_ids = set()  # 동적 등록된 Region ID (인스턴트/리니어 던전 등)


def get_region_ids():
    """현재 로드된 Region ID 목록 반환 (정적 + 동적, lazy cached)"""
    global _region_ids
    if _region_ids is None:
        _region_ids = []
        for rid in range(_MAX_PROBE):
            try:
                if morld.region_exists(rid):
                    _region_ids.append(rid)
            except Exception:
                pass
    # 동적 Region 합산 (매번 — 동적 등록은 캐시 이후에도 발생)
    combined = list(_region_ids)
    for rid in _dynamic_ids:
        if rid not in combined:
            combined.append(rid)
    return combined


def register_dynamic(region_id):
    """동적 Region 등록 (던전 생성 시 호출)"""
    _dynamic_ids.add(region_id)


def unregister_dynamic(region_id):
    """동적 Region 해제 (던전 삭제 시 호출)"""
    _dynamic_ids.discard(region_id)


def reset():
    """챕터 전환 시 호출 — 캐시 + 동적 전부 초기화"""
    global _region_ids
    _region_ids = None
    _dynamic_ids.clear()
