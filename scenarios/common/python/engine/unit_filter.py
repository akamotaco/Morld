# unit_filter.py — 유닛 가시성 필터
#
# C# LookFromLocation 등에서 유닛 목록을 필터링할 때 사용.
# 명시적 unit_ids + 동적 프리셋 조합.
#
# 설계 원칙:
#   - 엔진 프리셋: 동적 조건만 (스캔 필요) — stealthed, in_transit
#   - 시나리오 레이어: 어떤 unit을 제외할지 결정 (플레이어, 파티원 등)
#   - C# 호출: 시나리오별 래퍼 함수 경유 (엔진 직접 호출 X)

import morld


# 프리셋 레지스트리: name → callback(observer_id, location) -> list[unit_id]
_PRESETS = {}


def register_preset(name, callback):
    """프리셋 등록

    Args:
        name: 프리셋 이름
        callback: (observer_id, location) -> list[unit_id]
                  동적으로 제외 대상을 계산하는 함수
    """
    _PRESETS[name] = callback


def unregister_preset(name):
    """프리셋 등록 해제"""
    if name in _PRESETS:
        del _PRESETS[name]


def get_exclude_list(observer_id, unit_ids=None, presets=None, location=None):
    """Observer 기준 제외할 유닛 ID 리스트 반환

    Args:
        observer_id: 관찰자 유닛 ID
        unit_ids: 명시적 제외 대상 ID 리스트 (예: [player, party...])
        presets: 적용할 프리셋 이름 리스트 (예: ["stealthed", "in_transit"])
        location: (region_id, location_id) — 프리셋이 위치 기반 스캔 시 사용

    Returns:
        list[int]: 중복 제거된 제외 ID 목록
    """
    excluded = set()

    if unit_ids:
        for uid in unit_ids:
            if uid is not None:
                excluded.add(int(uid))

    if presets:
        for name in presets:
            callback = _PRESETS.get(name)
            if callback is None:
                continue
            try:
                ids = callback(observer_id, location)
                for uid in (ids or []):
                    excluded.add(int(uid))
            except Exception as e:
                print(f"[unit_filter] Preset '{name}' error: {e}")

    return list(excluded)


# ========================================
# 엔진 기본 프리셋
# ========================================

def _preset_stealthed(observer_id, location):
    """위치 내 은신 상태 유닛 (status:stealth = 1)"""
    if location is None:
        return []
    region_id, location_id = location
    try:
        chars = morld.get_characters_at_location(region_id, location_id)
    except Exception:
        return []
    return [
        uid for uid in (chars or [])
        if morld.get_unit_prop(uid, "status:stealth") == 1
    ]


def _preset_in_transit(observer_id, location):
    """이동 중 유닛 (상태:이동중 = 1)"""
    if location is None:
        return []
    region_id, location_id = location
    try:
        chars = morld.get_characters_at_location(region_id, location_id)
    except Exception:
        return []
    return [
        uid for uid in (chars or [])
        if morld.get_unit_prop(uid, "상태:이동중") == 1
    ]


def reset():
    """챕터 전환 초기화 — 엔진 기본 프리셋만 재등록"""
    _PRESETS.clear()
    register_preset("stealthed", _preset_stealthed)
    register_preset("in_transit", _preset_in_transit)


# 모듈 로드 시 기본 프리셋 등록
reset()
