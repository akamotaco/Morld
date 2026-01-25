# 시나리오 호환성 (Compatibility)

## 개요

시나리오03은 시나리오02의 핵심 시스템을 공유하면서 새로운 기능을 추가합니다. 새로운 속성이나 시스템은 **하위 호환성**을 유지하도록 설계하여, 시나리오02의 에셋과 코드가 시나리오03에서도 문제 없이 동작하도록 합니다.

---

## 호환성 원칙

### 기본 원칙

1. **선택적 속성**: 새로운 prop은 없어도 동작하도록 설계
2. **기본값 적용**: 속성이 없으면 최적/최상의 상태로 간주
3. **점진적 확장**: 기존 시스템을 수정하지 않고 확장

### 장점

- 시나리오02 에셋을 시나리오03에서 재사용 가능
- 공용 시스템 유지보수 용이
- 시나리오별 기능 선택적 적용

---

## 호환성 예시

### 내구도 시스템 (Durability)

시나리오03에서는 장비/아이템에 **내구도** 개념을 도입합니다.

#### 설계 원칙

```
내구도 prop이 있는 경우: 해당 값 사용
내구도 prop이 없는 경우: 항상 최상의 상태 (100%)로 간주
```

#### 구현 예시

```python
# 공용 함수 - 시나리오02/03 모두에서 사용
def get_durability(item_id: int) -> float:
    """
    아이템 내구도 조회 (0.0 ~ 1.0)

    내구도 prop이 없으면 1.0 (최상) 반환
    → 시나리오02 아이템도 문제 없이 동작
    """
    durability = morld.get_unit_prop(item_id, "durability")
    if durability is None:
        return 1.0  # 기본값: 최상의 상태
    return max(0.0, min(1.0, durability))


def is_broken(item_id: int) -> bool:
    """아이템이 파손되었는지 확인"""
    return get_durability(item_id) <= 0.0


def reduce_durability(item_id: int, amount: float):
    """
    내구도 감소

    내구도 prop이 없는 아이템은 영향 없음
    → 시나리오02 아이템은 내구도 감소 안 함
    """
    current = morld.get_unit_prop(item_id, "durability")
    if current is None:
        return  # 내구도 시스템 미적용 아이템

    new_value = max(0.0, current - amount)
    morld.set_unit_prop(item_id, "durability", new_value)
```

#### 시나리오별 동작

| 시나리오 | 아이템 정의 | 동작 |
|----------|-----------|------|
| 시나리오02 | `durability` prop 없음 | 항상 최상 상태, 파손 안 됨 |
| 시나리오03 | `durability: 1.0` 정의 | 사용에 따라 내구도 감소 |

#### 아이템 정의 예시

```python
# 시나리오02 - 내구도 없음 (기존 방식)
@register_item
class OldKnife(Blade):
    unique_id = "old_knife"
    name = "낡은 칼"
    passive_props = {"can:skin": 1}
    equip_props = {"공격": 2, "사냥": 1}
    # durability 없음 → 시나리오03에서도 파손 안 됨


# 시나리오03 - 내구도 있음
@register_item
class CombatKnife(Blade):
    unique_id = "combat_knife"
    name = "전투용 칼"
    passive_props = {"can:skin": 1, "durability": 1.0}  # 내구도 추가
    equip_props = {"공격": 5, "사냥": 3}
    # durability 있음 → 사용 시 내구도 감소
```

---

## 추가 호환성 패턴

### 패턴 1: 선택적 prop

```python
# 새로운 기능을 prop으로 관리
# prop이 없으면 기본값 사용

def get_optional_prop(unit_id, prop_name, default_value):
    value = morld.get_unit_prop(unit_id, prop_name)
    return value if value is not None else default_value
```

적용 예시:
- `durability`: 없으면 1.0 (최상)
- `morale`: 없으면 1.0 (최고 사기)
- `fatigue`: 없으면 0.0 (피로 없음)

### 패턴 2: 기능 플래그

```python
# 시나리오별 기능 활성화 플래그
ENABLE_DURABILITY = True  # 시나리오03에서만 True
ENABLE_SQUAD_SYSTEM = True

def use_item(item_id):
    # 기본 사용 로직 (공용)
    do_use(item_id)

    # 내구도 시스템 (시나리오03 전용)
    if ENABLE_DURABILITY:
        reduce_durability(item_id, 0.1)
```

### 패턴 3: 확장 클래스

```python
# 시나리오02 - 기본 클래스
class Item:
    unique_id = ""
    name = ""
    passive_props = {}
    equip_props = {}


# 시나리오03 - 확장 클래스 (내구도 지원)
class DurableItem(Item):
    initial_durability = 1.0

    def instantiate(self, item_id):
        super().instantiate(item_id)
        # 내구도 초기화
        morld.set_unit_prop(item_id, "durability", self.initial_durability)
```

---

## 시나리오03 전용 속성 목록

> TODO: 시스템 구현 시 추가

| 속성 | 기본값 | 설명 |
|------|--------|------|
| `durability` | 1.0 | 아이템 내구도 |
| `morale` | 1.0 | 요원 사기 |
| `fatigue` | 0.0 | 요원 피로도 |
| `stress` | 0.0 | 요원 스트레스 |
| `trust` | 0.5 | 오퍼레이터 신뢰도 |

---

## 주의사항

### 호환성 깨지는 경우

다음은 피해야 할 패턴:

```python
# BAD: prop이 없으면 에러
durability = morld.get_unit_prop(item_id, "durability")
durability -= 0.1  # None이면 에러!

# GOOD: 기본값 처리
durability = morld.get_unit_prop(item_id, "durability")
if durability is not None:
    morld.set_unit_prop(item_id, "durability", durability - 0.1)
```

### 테스트 권장사항

- 시나리오02 에셋으로 시나리오03 테스트
- 새 시스템 추가 시 prop 없는 경우 테스트
- 기본값 동작 확인

---

## 미정 사항

- [ ] 시나리오03 전용 prop 전체 목록
- [ ] 공용 유틸리티 함수 정의
- [ ] 시나리오 감지 메커니즘 (필요시)
