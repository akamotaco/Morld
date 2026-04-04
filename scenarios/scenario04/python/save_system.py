# save_system.py - S04 세이브 시스템
#
# 세이브 규칙:
# - 마을: 수동 세이브, 다중 슬롯
# - 던전 (긴 휴식): 자동 세이브, 단일 슬롯 (덮어쓰기)
# - 던전 (그 외): 세이브 불가
# - 플레이어 실신 → 재편성 → 자동 세이브 덮어써짐 (되돌릴 수 없음)
#
# 세이브 데이터 구조:
#   system_save (C# 영역): 지형, 유닛, 아이템, 시간 — morld API로 저장/복원
#   script_save (Python 영역): 이벤트 플래그, 오염도, 경제, 던전 상태
#
# 현재: Python 영역만 구현 (최소). C# 측 세이브는 향후 morld API 확장 필요.

import morld
import json
import os

# 세이브 디렉터리 (Godot user:// 경로)
_SAVE_DIR = "user://saves/scenario04"

# 슬롯
_MANUAL_SLOTS = 3         # 마을 수동 세이브 슬롯 수
_AUTO_SLOT = "autosave"   # 던전 자동 세이브 슬롯 이름


def reset():
    """챕터 전환 시 리셋"""
    pass


# ========================================
# 세이브 가능 여부 판정
# ========================================

def can_save_manual() -> bool:
    """수동 세이브 가능? (마을에 있을 때만)"""
    player_id = morld.get_player_id()
    if not player_id:
        return False

    loc = morld.get_unit_location(player_id)
    if not loc:
        return False

    region_id = loc[0]
    # Region 0 = 마을
    return region_id == 0


def can_save_auto() -> bool:
    """자동 세이브 가능? (던전 긴 휴식 시)"""
    # 던전 안에 있으면 가능 (호출 시점에서 긴 휴식 판정은 외부)
    player_id = morld.get_player_id()
    if not player_id:
        return False

    loc = morld.get_unit_location(player_id)
    if not loc:
        return False

    region_id = loc[0]
    # Region 0 아닌 곳 = 던전/필드
    return region_id != 0


# ========================================
# Python 상태 수집/복원
# ========================================

def _collect_script_state() -> dict:
    """Python 영역 상태 수집"""
    import survival
    import economy
    import pollution

    player_id = morld.get_player_id()

    state = {
        "version": 1,
        "player_id": player_id,
        "economy": {
            "money": economy.get_money(player_id) if player_id else 0,
        },
        "survival": {
            "health": survival.get_health(player_id) if player_id else 100,
            "satiety": survival.get_satiety(player_id) if player_id else 80,
        },
        "pollution": {
            "map": {f"{k[0]}:{k[1]}": v for k, v in pollution._pollution_map.items()},
        },
    }
    return state


def _restore_script_state(state: dict):
    """Python 영역 상태 복원"""
    import survival
    import economy

    player_id = morld.get_player_id()
    if not player_id:
        return

    if "economy" in state:
        economy.init_money(player_id, state["economy"].get("money", 50000))

    if "survival" in state:
        survival.set_health(player_id, state["survival"].get("health", 100))
        survival.set_satiety(player_id, state["survival"].get("satiety", 80))


# ========================================
# 세이브/로드 API
# ========================================

def save_manual(slot: int) -> bool:
    """
    수동 세이브 (마을)

    Args:
        slot: 슬롯 번호 (0 ~ MANUAL_SLOTS-1)

    Returns:
        True: 성공
    """
    if not can_save_manual():
        print("[save] Cannot save here (not in village)")
        return False

    if slot < 0 or slot >= _MANUAL_SLOTS:
        print(f"[save] Invalid slot: {slot}")
        return False

    state = _collect_script_state()
    _write_save(f"manual_{slot}", state)
    print(f"[save] Manual save to slot {slot}")
    return True


def save_auto() -> bool:
    """자동 세이브 (던전 긴 휴식)"""
    state = _collect_script_state()
    _write_save(_AUTO_SLOT, state)
    print("[save] Auto save (dungeon rest)")
    return True


def load_save(slot_name: str) -> bool:
    """
    세이브 로드

    Args:
        slot_name: "manual_0", "manual_1", "manual_2", "autosave"
    """
    state = _read_save(slot_name)
    if state is None:
        print(f"[save] No save data: {slot_name}")
        return False

    _restore_script_state(state)
    print(f"[save] Loaded: {slot_name}")
    return True


def get_save_slots() -> list:
    """사용 가능한 세이브 슬롯 목록"""
    slots = []
    for i in range(_MANUAL_SLOTS):
        name = f"manual_{i}"
        exists = _save_exists(name)
        slots.append({"name": name, "label": f"슬롯 {i+1}", "exists": exists})

    auto_exists = _save_exists(_AUTO_SLOT)
    slots.append({"name": _AUTO_SLOT, "label": "자동 저장", "exists": auto_exists})

    return slots


# ========================================
# 파일 I/O (향후 morld API로 대체 가능)
# ========================================

def _get_save_path(slot_name: str) -> str:
    return f"{_SAVE_DIR}/{slot_name}.json"


def _write_save(slot_name: str, state: dict):
    """세이브 파일 쓰기 (향후 Godot FileAccess로 대체)"""
    # 현재는 print만 (실제 파일 I/O는 Godot 환경에서)
    print(f"[save] Would write to {_get_save_path(slot_name)}: {len(str(state))} chars")
    # TODO: morld.save_file(path, json.dumps(state))


def _read_save(slot_name: str) -> dict:
    """세이브 파일 읽기"""
    # TODO: data = morld.load_file(path)
    print(f"[save] Would read from {_get_save_path(slot_name)}")
    return None


def _save_exists(slot_name: str) -> bool:
    """세이브 파일 존재 여부"""
    # TODO: morld.file_exists(path)
    return False
