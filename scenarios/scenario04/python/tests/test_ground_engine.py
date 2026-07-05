# test_ground_engine.py — engine.ground 시스템 단위 테스트
#
# 검증 범위:
#   - 계층 플래그: set_auto_ground_default / set_region_auto_ground / can_auto_generate
#   - ensure_ground_at이 off된 region에서 None 반환
#   - fallback 체인: 시나리오 grounds.py 없을 때 _EngineDynamicGround 사용

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
# Mock
# ============================================

class _MockMorld:
    """ground 테스트용 최소 API."""
    def __init__(self):
        self.units = {}        # unit_id → info
        self.positions = {}    # unit_id → (x, y)
        self.props = {}        # unit_id → {key: val}
        self.inventory = {}    # unit_id → {item_id: count}
        self.location_grounds = {}  # (r, l) → ground_unit_id
        self._next_id = 1000

    def create_id(self, kind):
        self._next_id += 1
        return self._next_id

    def add_unit(self, *a, **kw):
        uid = a[0]
        self.units[uid] = {"name": a[1], "region": a[2], "loc": a[3]}
        return True

    def remove_unit(self, uid):
        self.units.pop(uid, None)
        return True

    def set_unit_position(self, uid, x, y):
        self.positions[uid] = (x, y)

    def get_unit_position(self, uid):
        return self.positions.get(uid)

    def set_unit_prop(self, uid, key, val):
        self.props.setdefault(uid, {})[key] = val

    def get_unit_prop(self, uid, key):  # 실 계약: 부재 시 0
        return self.props.setdefault(uid, {}).get(key, 0)

    def get_unit_inventory(self, uid):
        return dict(self.inventory.setdefault(uid, {}))

    def get_unit_location(self, uid):
        info = self.units.get(uid)
        if info:
            return (info["region"], info["loc"])
        return None

    def get_time_info(self):
        # pollution/humidity 모듈 초기화용 stub
        return {"year": 1, "month": 4, "day": 1, "hour": 8, "minute": 0}

    def get_game_time(self):
        return 0

    def get_weather(self, *a, **kw):
        return "맑음"

    def give_item(self, uid, item_id, count=1):
        inv = self.inventory.setdefault(uid, {})
        inv[item_id] = inv.get(item_id, 0) + count

    def get_location_ground_id(self, r, l):
        return self.location_grounds.get((r, l))

    def set_location_ground_id(self, r, l, uid):
        if uid is None:
            self.location_grounds.pop((r, l), None)
        else:
            self.location_grounds[(r, l)] = uid


mock = _MockMorld()
sys.modules["morld"] = mock

# assets.registry stub (get_unique_id / get_location_class가 없으면 fallback 경로만 실행됨)
_registry_stub = type(sys)("assets.registry")
_registry_stub.get_unique_id = lambda lid: None
_registry_stub.get_location_class = lambda uid: None
sys.modules.setdefault("assets.registry", _registry_stub)

# assets.objects stub with register_instance
_objects_stub = type(sys)("assets.objects")
_objects_stub._instances = {}
_objects_stub.register_instance = lambda uid, inst: _objects_stub._instances.__setitem__(uid, inst)
sys.modules.setdefault("assets.objects", _objects_stub)

# assets.objects.grounds는 일부러 제공하지 않음 → engine fallback 테스트

from engine import ground


# ============================================
# Tests
# ============================================

def _reset():
    ground.reset()
    ground.AUTO_GROUND_GLOBAL_DEFAULT = True
    mock.units.clear()
    mock.positions.clear()
    mock.props.clear()
    mock.inventory.clear()
    mock.location_grounds.clear()
    _objects_stub._instances.clear()


class TestAutoGroundFlags:

    def test_default_is_true(self):
        _reset()
        assert ground.can_auto_generate(0, 0) is True
        assert ground.can_auto_generate(200, 1000) is True

    def test_global_default_override(self):
        _reset()
        ground.set_auto_ground_default(False)
        assert ground.can_auto_generate(0, 0) is False
        ground.set_auto_ground_default(True)
        assert ground.can_auto_generate(0, 0) is True

    def test_region_override_off(self):
        _reset()
        ground.set_region_auto_ground(200, False)
        assert ground.can_auto_generate(200, 0) is False
        assert ground.can_auto_generate(0, 0) is True  # 다른 region은 전역 default

    def test_region_override_on_despite_global_off(self):
        _reset()
        ground.set_auto_ground_default(False)
        ground.set_region_auto_ground(0, True)
        assert ground.can_auto_generate(0, 0) is True
        assert ground.can_auto_generate(999, 0) is False  # 전역 off 상속

    def test_region_override_clear(self):
        _reset()
        ground.set_region_auto_ground(200, False)
        assert ground.can_auto_generate(200, 0) is False
        ground.set_region_auto_ground(200, None)  # 제거 → 전역으로 복귀
        assert ground.can_auto_generate(200, 0) is True

    def test_reset_clears_region_flags(self):
        _reset()
        ground.set_region_auto_ground(200, False)
        ground.reset()
        assert ground.can_auto_generate(200, 0) is True


class TestEnsureGroundDisabled:

    def test_returns_none_when_disabled(self):
        _reset()
        ground.set_region_auto_ground(200, False)
        result = ground.ensure_ground_at(200, 0, 50)
        assert result is None

    def test_returns_id_when_enabled(self):
        _reset()
        result = ground.ensure_ground_at(0, 0, 50)
        assert isinstance(result, int)
        assert result > 0


class TestFallbackClass:
    """시나리오에 grounds.py 없을 때 엔진 fallback 사용"""

    def test_fallback_class_used(self):
        _reset()
        gid = ground.ensure_ground_at(0, 0, 50)
        # fallback이 사용되었는지 — _instances에 _EngineDynamicGround가 등록됨
        instance = _objects_stub._instances.get(gid)
        assert instance is not None
        assert instance.__class__.__name__ == "_EngineDynamicGround"

    def test_fallback_ground_is_registered(self):
        _reset()
        gid = ground.ensure_ground_at(0, 0, 50)
        # morld.add_unit이 호출되어 units dict에 등록됨
        assert gid in mock.units
        assert mock.units[gid]["name"] == "바닥"

    def test_merge_within_threshold(self):
        _reset()
        gid1 = ground.ensure_ground_at(0, 0, 50)
        gid2 = ground.ensure_ground_at(0, 0, 51)  # 1.0 거리 → 병합
        assert gid1 == gid2

    def test_no_merge_beyond_threshold(self):
        _reset()
        gid1 = ground.ensure_ground_at(0, 0, 50)
        gid2 = ground.ensure_ground_at(0, 0, 60)  # 10.0 거리 → 새 바닥
        assert gid1 != gid2


class TestDropItemIntegration:
    """drop_item_at이 flag 체크 + fallback 체인을 통과해 작동"""

    def test_drop_creates_ground_and_adds_item(self):
        _reset()
        player_id = 1
        mock.units[player_id] = {"name": "player", "region": 0, "loc": 0}
        mock.positions[player_id] = (50, 0)

        gid = ground.drop_item_at(player_id, item_id=42, count=2)
        assert gid is not None
        # 바닥 인벤토리에 item=42, count=2
        assert mock.inventory[gid].get(42) == 2

    def test_drop_blocked_when_region_off(self):
        _reset()
        player_id = 1
        mock.units[player_id] = {"name": "player", "region": 0, "loc": 0}
        mock.positions[player_id] = (50, 0)
        ground.set_region_auto_ground(0, False)

        gid = ground.drop_item_at(player_id, item_id=42)
        assert gid is None


# ============================================
# 러너
# ============================================

def _run():
    test_classes = [TestAutoGroundFlags, TestEnsureGroundDisabled,
                    TestFallbackClass, TestDropItemIntegration]
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
