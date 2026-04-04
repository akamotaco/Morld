# run_tests.py -pytest 없이 동작하는 테스트 러너
"""
사용법:
    python run_tests.py                # 전체 테스트
    python run_tests.py stimulation    # 특정 모듈만
    python run_tests.py -v             # 개별 테스트명 출력

SharpPy 호환: 외부 패키지 의존성 없음.
"""
import sys
import os
import traceback

# ============================================
# 1. 경로 설정 + mock_morld 주입
# ============================================

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))
_common_dir = os.path.abspath(os.path.join(_tests_dir, "..", "..", "..", "common", "python"))

if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)
# common은 scenario 뒤에 추가 (scenario 모듈 우선)
if os.path.isdir(_common_dir) and _common_dir not in sys.path:
    sys.path.append(_common_dir)

from mock_morld import MockMorld

_mock = MockMorld()
sys.modules["morld"] = _mock


# ============================================
# 2. 간이 테스트 러너
# ============================================

def run_test_module(module_name, verbose=False):
    """test_*.py 모듈의 Test* 클래스 → test_* 메서드를 수집/실행"""
    _mock.reset()

    try:
        mod = __import__(module_name)
    except Exception as e:
        print(f"  IMPORT ERROR: {module_name} -{e}")
        traceback.print_exc()
        return 0, 1, 0

    passed = 0
    failed = 0
    errors = 0

    # Test* 클래스 수집
    test_classes = []
    for name in sorted(dir(mod)):
        obj = getattr(mod, name)
        if isinstance(obj, type) and name.startswith("Test"):
            test_classes.append((name, obj))

    for cls_name, cls in test_classes:
        # test_* 메서드 수집
        methods = [m for m in sorted(dir(cls)) if m.startswith("test_")]
        for method_name in methods:
            _mock.reset()
            full_name = f"{cls_name}.{method_name}"
            try:
                instance = cls()
                if hasattr(instance, 'setUp'):
                    instance.setUp()
                getattr(instance, method_name)()
                passed += 1
                if verbose:
                    print(f"    PASS  {full_name}")
            except AssertionError as e:
                failed += 1
                print(f"    FAIL  {full_name}")
                if verbose:
                    traceback.print_exc()
                    print()
            except Exception as e:
                errors += 1
                print(f"    ERROR {full_name} -{e}")
                if verbose:
                    traceback.print_exc()
                    print()

    return passed, failed, errors


def main():
    verbose = "-v" in sys.argv
    filter_modules = [a for a in sys.argv[1:] if not a.startswith("-")]

    test_modules = [
        "test_stimulation",
        "test_romance_actions",
        "test_romance_mode",
        "test_romance_core",
        "test_alias_removal",
        "test_mob_character",
        "test_think_logic",
        "test_npc_objects",
        "test_aftermath",
        "test_positive_memory",
        "test_semen",
        "test_combat",
        "test_creature",
        "test_build",
        "test_fsm",
        "test_faye",
        "test_party",
        "test_inspect",
        "test_vehicle",
        "test_story",
        "test_instant_dungeon",
    ]

    if filter_modules:
        test_modules = [m for m in test_modules
                        if any(f in m for f in filter_modules)]

    total_passed = 0
    total_failed = 0
    total_errors = 0

    print("=" * 60)
    print("morld romance unit tests")
    print("=" * 60)

    for module_name in test_modules:
        print(f"\n[{module_name}]")
        try:
            p, f, e = run_test_module(module_name, verbose)
            total_passed += p
            total_failed += f
            total_errors += e
            status = "OK" if (f + e) == 0 else "FAIL"
            print(f"  {status}: {p} passed, {f} failed, {e} errors")
        except Exception as ex:
            print(f"  MODULE ERROR: {ex}")
            traceback.print_exc()
            total_errors += 1

    print("\n" + "=" * 60)
    total = total_passed + total_failed + total_errors
    print(f"TOTAL: {total_passed}/{total} passed"
          f" ({total_failed} failed, {total_errors} errors)")

    if total_failed + total_errors > 0:
        print("RESULT: FAIL")
        return 1
    else:
        print("RESULT: ALL PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
