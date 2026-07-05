# test_quest_board.py — quest_board 레지스트리/ref-count/조건 단위 테스트
#
# 실행: python tests/test_quest_board.py

import io
import os
import sys
import traceback


if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))
_common_dir = os.path.abspath(os.path.join(_tests_dir, "..", "..", "..", "common", "python"))

if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _common_dir not in sys.path:
    sys.path.append(_common_dir)


# ============================================
# MockMorld — quest_board + engine.quest 테스트용
# ============================================

class _MockMorld:
    def __init__(self):
        self.unit_props = {}       # uid -> {key: val}
        self.inventory = {}        # uid -> {item_id: count}
        self.gates = set()         # {(region, loc, gate_id)}
        self.items = {}            # unique_id -> item_id
        self.item_info = {}        # item_id -> {"name": ...}
        self.player_id = 1
        self.time = 0

    def get_player_id(self): return self.player_id
    def get_game_time(self): return self.time

    def get_unit_props(self, uid):
        return self.unit_props.setdefault(uid, {})

    def get_unit_prop(self, uid, key):  # 실 계약: 부재 시 0
        return self.unit_props.setdefault(uid, {}).get(key, 0)

    def set_unit_prop(self, uid, key, val):
        self.unit_props.setdefault(uid, {})[key] = val

    def set_unit_props(self, uid, props):
        self.unit_props[uid] = dict(props)

    def get_unit_inventory(self, uid):
        return dict(self.inventory.setdefault(uid, {}))

    def get_item_id_by_unique(self, unique_id):
        return self.items.get(unique_id)

    def get_item_info(self, item_id):
        return self.item_info.get(item_id)

    def give_item(self, uid, item_id_or_unique, count=1):
        # 실제 API는 item_id(int). 테스트 편의로 unique_id(str)도 허용.
        if isinstance(item_id_or_unique, str):
            unique_id = item_id_or_unique
            iid = self.items.get(unique_id)
            if iid is None:
                iid = len(self.items) + 100
                self.items[unique_id] = iid
                self.item_info[iid] = {"name": unique_id}
        else:
            iid = int(item_id_or_unique)
        inv = self.inventory.setdefault(uid, {})
        inv[iid] = inv.get(iid, 0) + int(count)

    def remove_item(self, uid, item_id, count=1):
        inv = self.inventory.setdefault(uid, {})
        cur = inv.get(item_id, 0)
        new = cur - int(count)
        if new <= 0:
            inv.pop(item_id, None)
        else:
            inv[item_id] = new
        return True

    def lost_item(self, uid, item_id, count=1):
        return self.remove_item(uid, item_id, count)

    def add_gate(self, region, loc, gate_id, x, conn_r, conn_l, arr_x):
        self.gates.add((region, loc, gate_id))

    def remove_gate(self, region, loc, gate_id):
        self.gates.discard((region, loc, gate_id))

    def add_region(self, *a, **kw): pass
    def add_location(self, *a, **kw): pass
    def remove_location(self, *a, **kw): pass
    def region_exists(self, rid): return rid == 0


mock = _MockMorld()
sys.modules["morld"] = mock

# engine.event_core의 subscribe_time_elapsed 스텁 (실제 시간 훅 불필요)
_event_core_stub = type(sys)("engine.event_core")
_event_core_stub.subscribe_time_elapsed = lambda fn, min_interval=0: None
_event_core_stub.subscribe_on_reach = lambda *a, **kw: None
_event_core_stub.reset = lambda: None
sys.modules["engine.event_core"] = _event_core_stub

import quest_board
from engine.quest import get_quest_manager, QuestStatus


# ============================================
# Tests
# ============================================

def _reset_state():
    """각 테스트 전 상태 초기화"""
    mock.unit_props.clear()
    mock.inventory.clear()
    mock.gates.clear()
    mock.items.clear()
    mock.item_info.clear()
    mock.time = 0
    # cave_moss 아이템 사전 등록
    mock.items["cave_moss"] = 10
    mock.item_info[10] = {"name": "동굴 이끼"}
    quest_board.reset()
    quest_board.initialize()


class TestLocationRegistry:

    def test_all_locations_defined(self):
        _reset_state()
        keys = set(quest_board._QUEST_LOCATIONS.keys())
        assert keys == {"cave", "deep", "guardian"}, keys

    def test_loc_id_mapping(self):
        _reset_state()
        assert quest_board.get_location_key_by_loc_id(1000) == "cave"
        assert quest_board.get_location_key_by_loc_id(1001) == "deep"
        assert quest_board.get_location_key_by_loc_id(1002) == "guardian"
        assert quest_board.get_location_key_by_loc_id(9999) is None


class TestRefCount:

    def test_gate_created_on_first_accept(self):
        _reset_state()
        mgr = get_quest_manager()
        # 동굴 탐사 수락 → cave Gate 생성
        mgr.accept_quest("board_dungeon_explore")
        cfg = quest_board._QUEST_LOCATIONS["cave"]
        assert (0, 7, cfg["entrance_gate_id"]) in mock.gates
        assert quest_board._location_refcount["cave"] == 1

    def test_gate_shared_between_same_location_quests(self):
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_dungeon_explore")
        mgr.accept_quest("board_cave_moss")
        # 두 퀘스트 모두 cave → ref-count 2, Gate 1회 생성
        assert quest_board._location_refcount["cave"] == 2
        cfg = quest_board._QUEST_LOCATIONS["cave"]
        assert (0, 7, cfg["entrance_gate_id"]) in mock.gates

    def test_gate_removed_when_last_quest_ends(self):
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_dungeon_explore")
        mgr.accept_quest("board_cave_moss")
        cfg = quest_board._QUEST_LOCATIONS["cave"]

        # 하나 실패 처리 → Gate 유지
        mgr.fail_quest("board_dungeon_explore", reason="테스트")
        assert (0, 7, cfg["entrance_gate_id"]) in mock.gates
        assert quest_board._location_refcount["cave"] == 1

        # 나머지도 실패 → Gate 삭제
        mgr.fail_quest("board_cave_moss", reason="테스트")
        assert (0, 7, cfg["entrance_gate_id"]) not in mock.gates
        assert quest_board._location_refcount["cave"] == 0

    def test_different_locations_have_separate_gates(self):
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_dungeon_explore")
        mgr.accept_quest("board_deep_exploration")
        mgr.accept_quest("board_guardian_hunt")
        # 3개 장소 각각 고유 Gate ID
        assert len(mock.gates) >= 6  # L7측 3개 + 진입점 복귀 3개
        for key in ("cave", "deep", "guardian"):
            cfg = quest_board._QUEST_LOCATIONS[key]
            assert (0, 7, cfg["entrance_gate_id"]) in mock.gates, key


class TestItemCountCondition:

    def test_item_count_below_threshold(self):
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_cave_moss")
        progress = mgr.get_quest_progress("board_cave_moss")
        # 인벤토리 비어있음 → 미충족
        assert all(not c["is_met"] for c in progress["conditions"])

    def test_item_count_met(self):
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_cave_moss")
        # 이끼 3개 지급
        mock.give_item(mock.player_id, "cave_moss", 3)
        progress = mgr.get_quest_progress("board_cave_moss")
        assert all(c["is_met"] for c in progress["conditions"])


class TestOnDungeonClear:

    def test_cave_moss_partial_reward(self):
        """여러 번 클리어 → 이끼 누적 → 3개 달성 시 IN_PROGRESS 종료.

        repeatable=True이므로 완료 후 status는 AVAILABLE(0)로 리셋됨.
        """
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_cave_moss")

        completed = False
        for _ in range(5):  # 최악 1개×5=5≥3 보장
            quest_board.on_dungeon_clear()
            if mgr.get_quest_status("board_cave_moss") != QuestStatus.IN_PROGRESS:
                completed = True
                break
        assert completed, "5회 클리어 후에도 IN_PROGRESS 유지"

    def test_dungeon_cleared_broadcasts_to_all_active(self):
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_dungeon_explore")
        mgr.accept_quest("board_cave_moss")

        quest_board.on_dungeon_clear()

        # 동굴 탐사: 조건(dungeon_cleared) 충족 → 완료 → repeatable이므로 상태 리셋
        explore_status = mgr.get_quest_status("board_dungeon_explore")
        assert explore_status != QuestStatus.IN_PROGRESS, (
            "Expected board_dungeon_explore completed, got " + str(explore_status)
        )

        # 동굴 이끼: 1~2개 지급됨 (조건 미충족, IN_PROGRESS 유지)
        moss_id = mock.items["cave_moss"]
        moss_count = mock.inventory[mock.player_id].get(moss_id, 0)
        assert 1 <= moss_count <= 2, "moss given: " + str(moss_count)


class TestReporterConfirm:
    """reporter 기반 '확인 클리어' 방식 검증 (engine.quest_reporter)"""

    def test_cave_moss_not_auto_completed(self):
        """이끼 3개 모여도 reporter가 있으면 claim_reward 자동 호출 안 됨.
        COMPLETED 상태로 대기."""
        _reset_state()
        from engine import quest_reporter
        mgr = get_quest_manager()
        mgr.accept_quest("board_cave_moss")
        # 이끼 3개 즉시 지급
        mock.give_item(mock.player_id, "cave_moss", 3)
        # 조건 재평가 → COMPLETED로 승격
        quest_reporter.recheck("quest_board")
        status = mgr.get_quest_status("board_cave_moss")
        assert status == QuestStatus.COMPLETED, (
            "Expected COMPLETED, got " + str(status)
        )

    def test_has_reportable_detects_cave_moss(self):
        _reset_state()
        from engine import quest_reporter
        mgr = get_quest_manager()
        mgr.accept_quest("board_cave_moss")
        mock.give_item(mock.player_id, "cave_moss", 3)
        assert quest_reporter.has_reportable("quest_board")
        # 다른 reporter_key에는 안 잡힘
        assert not quest_reporter.has_reportable("other_reporter")

    def test_confirm_consumes_item_and_completes(self):
        """confirm_quest → on_confirm(consume_item) → claim_reward"""
        _reset_state()
        from engine import quest_reporter
        mgr = get_quest_manager()
        mgr.accept_quest("board_cave_moss")
        mock.give_item(mock.player_id, "cave_moss", 5)  # 여분 2개
        quest_reporter.recheck("quest_board")
        assert mgr.get_quest_status("board_cave_moss") == QuestStatus.COMPLETED

        ok = quest_reporter.confirm_quest("board_cave_moss")
        assert ok

        # 이끼 3개 소비 → 2개 남음
        moss_id = mock.items["cave_moss"]
        remaining = mock.inventory[mock.player_id].get(moss_id, 0)
        assert remaining == 2, "Expected 2 remaining, got " + str(remaining)

        # repeatable 퀘스트 → 상태 리셋
        status = mgr.get_quest_status("board_cave_moss")
        assert status != QuestStatus.IN_PROGRESS

    def test_guardian_hunt_stays_immediate(self):
        """수호수 토벌은 reporter=None → 기존대로 즉시 완료"""
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_guardian_hunt")
        quest_board.on_dungeon_clear()
        # 조건 충족 + reporter=None → 즉시 claim_reward → 반복 가능이라 리셋
        status = mgr.get_quest_status("board_guardian_hunt")
        assert status != QuestStatus.IN_PROGRESS
        assert status != QuestStatus.COMPLETED  # COMPLETED 대기 아님 (자동 처리됨)


class TestFloorsConfigForLocation:

    def test_no_active_quest(self):
        _reset_state()
        assert quest_board.get_floors_config_for_location("cave") is None

    def test_active_cave_returns_default(self):
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_dungeon_explore")
        floors = quest_board.get_floors_config_for_location("cave")
        assert floors is not None
        assert len(floors) == 1  # cave default_floors는 1층

    def test_guardian_returns_5_floors(self):
        _reset_state()
        mgr = get_quest_manager()
        mgr.accept_quest("board_guardian_hunt")
        floors = quest_board.get_floors_config_for_location("guardian")
        assert floors is not None
        assert len(floors) == 5
        # 3층 중간 보스, 5층 최종 보스
        assert floors[2]["boss"]["is_final"] is False
        assert floors[4]["boss"]["is_final"] is True


# ============================================
# 러너
# ============================================

def _run():
    test_classes = [
        TestLocationRegistry,
        TestRefCount,
        TestItemCountCondition,
        TestOnDungeonClear,
        TestReporterConfirm,
        TestFloorsConfigForLocation,
    ]
    passed = failed = errors = 0
    for cls in test_classes:
        for name in sorted(dir(cls)):
            if not name.startswith("test_"):
                continue
            instance = cls()
            method = getattr(instance, name)
            full = f"{cls.__name__}.{name}"
            try:
                method()
                print(f"  PASS  {full}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {full}: {e}")
                failed += 1
            except Exception as e:
                print(f"  ERROR {full}: {e}")
                traceback.print_exc()
                errors += 1
    total = passed + failed + errors
    print("=" * 50)
    print(f"TOTAL: {passed}/{total} passed ({failed} failed, {errors} errors)")
    return 0 if failed == 0 and errors == 0 else 1


if __name__ == "__main__":
    sys.exit(_run())
