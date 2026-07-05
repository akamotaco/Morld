"""시나리오03 테스트 러너

Usage:
    python run_tests.py          # 전체 실행
    python run_tests.py world    # test_world만 실행
    python run_tests.py -v       # verbose 모드
"""
import sys
import os
import traceback

# 경로 설정
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.dirname(_tests_dir)
_common_dir = os.path.abspath(os.path.join(_tests_dir, "..", "..", "..", "common", "python"))
sys.path.insert(0, _tests_dir)
sys.path.insert(0, _python_dir)
# common은 scenario 뒤에 추가 (scenario 모듈 우선) — dungeon 등 공통화 모듈 로드용
if os.path.isdir(_common_dir) and _common_dir not in sys.path:
    sys.path.append(_common_dir)

# Mock morld 주입 (모든 import morld가 이 mock을 사용)
from mock_morld import MockMorld
_mock = MockMorld()
sys.modules["morld"] = _mock

# UI stub 주입
import types
_ui_stub = types.ModuleType("ui")
_ui_stub.dialog = lambda *a, **kw: None
_ui_stub.set_ui_lock = lambda *a: None
_ui_stub.set_view_mode = lambda *a: None
sys.modules["ui"] = _ui_stub


def run_test_module(module_name, verbose=False):
    """테스트 모듈 실행"""
    _mock.reset()

    try:
        mod = __import__(module_name)
    except Exception as e:
        print(f"  IMPORT ERROR: {e}")
        traceback.print_exc()
        return 0, 0, 1

    # Test* 클래스 수집
    test_classes = []
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and name.startswith("Test"):
            test_classes.append((name, obj))

    passed = 0
    failed = 0
    errors = 0

    for class_name, cls in sorted(test_classes):
        # test_* 메서드 수집
        methods = [m for m in dir(cls) if m.startswith("test_")]
        for method_name in sorted(methods):
            test_label = f"{class_name}.{method_name}"
            try:
                _mock.reset()
                instance = cls()
                if hasattr(instance, 'setUp'):
                    instance.setUp()
                getattr(instance, method_name)()
                passed += 1
                if verbose:
                    print(f"    PASS: {test_label}")
            except AssertionError as e:
                failed += 1
                print(f"    FAIL: {test_label}")
                if verbose:
                    traceback.print_exc()
            except Exception as e:
                errors += 1
                print(f"    ERROR: {test_label} -- {e}")
                if verbose:
                    traceback.print_exc()

    return passed, failed, errors


# 테스트 모듈 목록 (실행 순서)
TEST_MODULES = [
    "test_assets",
    "test_world",
    "test_chapters",
    "test_agents",
    "test_events",
    "test_quest",
    "test_progression",
    "test_build",
    "test_squad",
    "test_mapgen",
    "test_expedition",
    "test_combat",
    "test_cycle",
    "test_npc_dialogue",
    "test_integration",
]


def main():
    verbose = "-v" in sys.argv
    filter_name = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            filter_name = arg
            break

    modules = TEST_MODULES
    if filter_name:
        modules = [m for m in modules if filter_name in m]
        if not modules:
            print(f"No test modules matching '{filter_name}'")
            return 1

    total_passed = 0
    total_failed = 0
    total_errors = 0

    print(f"\n=== 시나리오03 테스트 ({len(modules)} modules) ===\n")

    for module_name in modules:
        print(f"  [{module_name}]")
        p, f, e = run_test_module(module_name, verbose)
        total_passed += p
        total_failed += f
        total_errors += e
        status = "OK" if (f + e) == 0 else "FAIL"
        print(f"    -> {status} (pass={p}, fail={f}, error={e})")

    print(f"\n=== 결과: {total_passed} passed, {total_failed} failed, {total_errors} errors ===\n")
    return 1 if (total_failed + total_errors) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
