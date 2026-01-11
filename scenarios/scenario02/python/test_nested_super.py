# test_nested_super.py - SharpPy 중첩 함수 내 super() 호출 테스트
#
# 이 테스트는 중첩 함수 내에서 클래스의 super()가 호출될 때
# SharpPy가 제대로 처리하는지 확인합니다.
#
# 문제 상황:
# - 메서드 내부에 정의된 중첩 함수(def add_to_wardrobe)에서
# - 클래스 인스턴스를 생성하고 instantiate()를 호출하면
# - 해당 클래스의 instantiate()가 super().instantiate()를 호출할 때
# - "super() argument 1 must be type" 오류 발생
#
# 실행: Godot에서 ScriptSystem을 통해 이 파일의 함수 호출

class Base:
    def __init__(self):
        self.value = 0

    def instantiate(self, val):
        self.value = val
        print(f"[Base.instantiate] value={val}")


class Child(Base):
    def __init__(self):
        super().__init__()
        self.name = "child"

    def instantiate(self, val):
        # 여기서 super() 호출
        super().instantiate(val)
        print(f"[Child.instantiate] name={self.name}, value={self.value}")


# ========================================
# 테스트 1: 직접 호출 (정상 동작 예상)
# ========================================
def test_direct_call():
    """중첩 함수 없이 직접 호출 - 정상 동작해야 함"""
    print("=== Test 1: Direct Call ===")
    child = Child()
    child.instantiate(42)
    print(f"Result: value={child.value}")
    print("=== Test 1 PASSED ===\n")


# ========================================
# 테스트 2: 중첩 함수 내 호출 (오류 발생 예상)
# ========================================
def test_nested_function_call():
    """중첩 함수 내에서 호출 - SharpPy에서 오류 발생 가능"""
    print("=== Test 2: Nested Function Call ===")

    results = []

    def create_and_init(cls, val):
        # 중첩 함수 내에서 클래스 인스턴스화 + super() 호출
        obj = cls()
        obj.instantiate(val)
        results.append(obj)

    create_and_init(Child, 100)
    create_and_init(Child, 200)

    print(f"Result: {len(results)} objects created")
    for i, obj in enumerate(results):
        print(f"  [{i}] value={obj.value}")
    print("=== Test 2 PASSED ===\n")


# ========================================
# 테스트 3: 람다 내 호출
# ========================================
def test_lambda_call():
    """람다 내에서 호출"""
    print("=== Test 3: Lambda Call ===")

    items = []
    add_item = lambda cls, val: (lambda: (items.append(cls()), items[-1].instantiate(val)))()

    add_item(Child, 300)
    add_item(Child, 400)

    print(f"Result: {len(items)} objects created")
    print("=== Test 3 PASSED ===\n")


# ========================================
# 테스트 4: 리스트 컴프리헨션 내 호출
# ========================================
def test_list_comprehension():
    """리스트 컴프리헨션 내에서 호출"""
    print("=== Test 4: List Comprehension ===")

    def make_child(val):
        c = Child()
        c.instantiate(val)
        return c

    items = [make_child(v) for v in [500, 600, 700]]

    print(f"Result: {len(items)} objects created")
    print("=== Test 4 PASSED ===\n")


# ========================================
# 모든 테스트 실행
# ========================================
def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "=" * 50)
    print("SharpPy Nested Function Super() Test")
    print("=" * 50 + "\n")

    try:
        test_direct_call()
    except Exception as e:
        print(f"!!! Test 1 FAILED: {e}\n")

    try:
        test_nested_function_call()
    except Exception as e:
        print(f"!!! Test 2 FAILED: {e}\n")

    try:
        test_lambda_call()
    except Exception as e:
        print(f"!!! Test 3 FAILED: {e}\n")

    try:
        test_list_comprehension()
    except Exception as e:
        print(f"!!! Test 4 FAILED: {e}\n")

    print("=" * 50)
    print("All tests completed")
    print("=" * 50)


# CPython에서 직접 실행 시
if __name__ == "__main__":
    run_all_tests()
