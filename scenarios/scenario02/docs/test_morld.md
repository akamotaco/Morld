# 유닛 테스트 (Unit Test)

## 개요

morld C# API를 인메모리 Python mock으로 대체하여, 순수 Python 환경에서 연애 시스템의 로직을 검증하는 유닛 테스트.

- **외부 패키지 의존성 0** — pytest 불필요, SharpPy에서도 실행 가능
- **mock 기반** — `sys.modules['morld']`에 MockMorld 주입

---

## 파일 구조

```
scenarios/scenario02/python/tests/
├── run_tests.py              # 테스트 러너 (진입점)
├── mock_morld.py             # morld API 인메모리 구현체
├── test_stimulation.py       # stimulation.py 상태머신 테스트
├── test_romance_actions.py   # romance_actions.py 데이터 무결성 검증
├── test_romance_mode.py      # romance_mode.py 순수 함수 + mock 테스트
└── test_romance_core.py      # romance_core.py 핵심 로직 테스트
```

---

## 실행 방법

```bash
# 전체 테스트
python tests/run_tests.py

# 특정 모듈만
python tests/run_tests.py core

# 개별 테스트명 출력
python tests/run_tests.py -v

# 조합
python tests/run_tests.py stimulation -v
```

---

## 테스트 결과

```
237/237 passed (0 failed, 0 errors) — ALL PASSED
```

---

## 테스트 작성 방법

### 1. 테스트 파일 생성

`tests/test_<모듈명>.py` 파일을 생성한다.

```python
# test_example.py
import sys

# mock_morld 접근 (run_tests.py가 주입)
morld = sys.modules["morld"]

# 테스트할 모듈 import
import my_module


class TestMyFunction:
    def test_basic(self):
        """기본 동작 검증"""
        assert my_module.my_function(1, 2) == 3

    def test_edge_case(self):
        """경계값 검증"""
        assert my_module.my_function(0, 0) == 0
```

### 2. 규칙

- 클래스명: `Test`로 시작 (예: `TestMyFunction`)
- 메서드명: `test_`로 시작 (예: `test_basic`)
- 검증: `assert` 문 사용 (pytest/unittest 불필요)
- morld API 사용 시: `morld.register_unit()` 등으로 테스트 데이터 설정
- 상태 초기화: run_tests.py가 매 테스트마다 `mock.reset()` 자동 호출

### 3. 러너에 등록

[run_tests.py](../python/tests/run_tests.py)의 `test_modules` 리스트에 추가:

```python
test_modules = [
    "test_stimulation",
    "test_romance_actions",
    "test_romance_mode",
    "test_romance_core",
    "test_example",        # 추가
]
```

### 4. morld mock API

MockMorld가 제공하는 API:

| 카테고리 | API |
|---------|-----|
| 테스트 셋업 | `register_unit(id, name, props, location, gender)` |
| 테스트 셋업 | `register_item(id, name, equip_props)` |
| 테스트 셋업 | `add_to_inventory(unit_id, item_id)` |
| Property | `get_unit_prop`, `get_unit_props`, `set_unit_prop`, `modify_prop`, `clear_prop` |
| Unit 정보 | `get_unit_info`, `get_unit_location`, `get_units_at_location`, `get_player_id` |
| 인벤토리 | `get_unit_inventory`, `lost_item` |
| 아이템 | `get_item_info` |
| 시간 | `get_time`, `advance_time_des`, `is_time_frozen` |
| NPC/UI | `set_npc_job`, `add_action_log`, `queue_event`, `add_unit_mood`, `pop_to_situation` |

### 5. mock 확장

테스트에 필요한 morld API가 MockMorld에 없으면 `mock_morld.py`에 추가한다.

```python
# mock_morld.py에 추가
def new_api(self, arg):
    # 인메모리 구현
    pass
```
