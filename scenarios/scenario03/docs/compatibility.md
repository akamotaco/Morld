# 시나리오 호환성 (Compatibility)

## 개요

시나리오03은 시나리오02의 핵심 시스템을 **공유**한다. 대부분의 시나리오03 시스템은 신규 구현이 아니라 기존 시스템의 **확장 또는 설정 변경**으로 구현된다. 새로운 속성이나 시스템은 하위 호환성을 유지하도록 설계하여, 시나리오02의 에셋과 코드가 시나리오03에서도 문제 없이 동작하도록 한다.

---

## 시스템 매핑 총괄

### 그대로 사용하는 시스템 (변경 없음)

| 시나리오02 시스템 | 코드 위치 | 시나리오03 용도 |
|-----------------|----------|----------------|
| ECS 아키텍처 | C# `scripts/system/` | 동일 |
| TextUI 시스템 | C# `scripts/system/` | CRT/CCTV 뷰 확장 |
| Dialog 시스템 | C# + Python events/ | 원격 상담/취조에 활용 |
| DES (이산 사건 시뮬레이션) | `advance_time_des()` | 동일 (유일한 시간 진행 API) |
| Asset Registry | `assets/registry.py` | 동일 (unique_id ↔ instance_id) |
| FSM 스택 | `think/fsm.py` | 동일 (push/pop/pass-through) |
| 이동 시스템 | `think/movement_mixin.py` | 동일 (1D Location 이동) |
| 스케줄 시스템 | `think/schedule_mixin.py` | 동일 (동적 조건 평가) |
| 시설 탐색 | `think/facility_resolver.py` | 동일 (prop 기반 동적 탐색) |
| 도구/자원 활동 프레임워크 | `think/activities/tool_activity.py` 등 | 동일 패턴 |
| 환경 시스템 | `temperature/humidity/congestion/pollution/sound/lighting.py` | 동일 |
| 연료 시스템 | `fuel.py` | 플랫폼 열원 관리 |
| 운반 시스템 | `carry.py` | 동일 |
| 바닥 오브젝트 | `ground.py` | 동일 |
| 지형 시스템 | Region/Location/Gate | 동일 (동적 생성 추가) |

### 확장하여 사용하는 시스템

| 시나리오03 시스템 | 기반 코드 | 확장 내용 |
|-----------------|----------|----------|
| **마이크로턴 전투** | `think/fsm.py` CombatState | MicroTurnCombatState 서브클래스 추가, 턴 시퀀스 로직 ([combat.md](combat.md) 참조) |
| **분대 시스템** | `party.py` Squad/Order | Rank(대열 순번) 속성 추가, 공세 레벨 = Player Directive 확장 ([squad.md](squad.md) 참조) |
| **약물 시스템** | `equipment.py` equip_props | 약물 = equip_props + 시간 경과 효과 (인간성 감소) |
| **인간성 잔존율(H.I)** | `needs.py` 욕구 패턴 | 단일 prop + 임계치별 행동 변화 |
| **Vita/Sapientia** | prop 기반 | 성장 prop 2개 + 풀 한계 제약 |
| **MIA** | `survival.py` + `party.py` | 상태 prop + 구출 미션 (탐사의 변형) |
| **헌납** | `inventory.py` | `remove_item` + 상부 prop 변경 |
| **보급/배급** | `time_elapsed` 이벤트 | 시간 이벤트 → `give_item` + 인력 생성 |
| **취조** | Dialog 시스템 | 상담실 변형 — Dialog + 판정 로직 |
| **사후 보고서** | Dialog/TextUI | prop 집계 → 텍스트 출력 |
| **동적 맵 생성** | Region/Location/Gate | 2D 레이아웃 생성 → Location/Gate 변환 ([mapgen.md](mapgen.md) 참조) |

### 시나리오02 전용 (시나리오03에서 미사용)

| 시스템 | 이유 |
|--------|------|
| romance*.py (연애) | 시나리오03 세계관과 무관 |
| pregnancy.py (임신) | 연애 연동 |
| stealth.py (은신) | 1D 마이크로턴 전투 기반, 별도 은신 시스템 불필요 |
| combat.py (직접 전투) | 시나리오02 플레이어 직접 전투, 시나리오03은 간접 지휘 |
| garden.py (텃밭) | 시나리오03 세계관과 무관 |
| vehicle.py (차량) | 시나리오03은 열차(지저철)를 별도 설계 |
| build.py (건축) | 시나리오03은 플랫폼 확장으로 대체 |

---

## 호환성 원칙

### 기본 원칙

1. **선택적 속성**: 새로운 prop은 없어도 동작하도록 설계
2. **기본값 적용**: 속성이 없으면 최적/최상의 상태로 간주
3. **점진적 확장**: 기존 시스템을 수정하지 않고 확장

### 호환성 패턴

**패턴 1: 선택적 prop**

```python
def get_optional_prop(unit_id, prop_name, default_value):
    value = morld.get_unit_prop(unit_id, prop_name)
    return value if value is not None else default_value
```

적용 예시:
- `durability`: 없으면 1.0 (최상)
- `humanity`: 없으면 1.0 (완전한 인간성)
- `rank`: 없으면 None (대열 순번 미지정)

**패턴 2: 확장 클래스**

```python
# 시나리오02 - 기본 클래스
class Item:
    unique_id = ""
    name = ""
    passive_props = {}
    equip_props = {}

# 시나리오03 - 확장 클래스
class DurableItem(Item):
    initial_durability = 1.0

    def instantiate(self, item_id):
        super().instantiate(item_id)
        morld.set_unit_prop(item_id, "durability", self.initial_durability)
```

**패턴 3: FSM 서브클래스**

```python
# 시나리오02 - CombatState (기존)
class CombatState:
    def update(self, agent): ...

# 시나리오03 - 마이크로턴 전투 (확장)
class MicroTurnCombatState(CombatState):
    def update(self, agent):
        # 턴 시퀀스 로직 + 대열 순번 처리
        ...
```

---

## 시나리오03 전용 속성 목록

| 속성 | 기본값 | 설명 | 기반 시스템 |
|------|--------|------|-----------|
| `durability` | 1.0 | 아이템 내구도 | equipment.py |
| `humanity` | 1.0 | 인간성 잔존율 (H.I) | needs.py 패턴 |
| `vita` | 0 | 생명 트랙 레벨 | prop |
| `sapientia` | 0 | 지혜 트랙 레벨 | prop |
| `morale` | 1.0 | 분대원 사기 | needs.py 패턴 |
| `stress` | 0.0 | 분대원 스트레스 | needs.py 패턴 |
| `trust` | 0.5 | 오퍼레이터 신뢰도 | prop |
| `rank` | None | 대열 순번 (1/2/3) | party.py 확장 |
| `serial_number` | None | 시리얼 번호 (예: "Echo-07") | prop |
| `model_id` | None | 모델명 (예: "Echo") | prop |
| `drug:강화` | 0 | 강화 약물 투여량 | equip_props |
| `drug:진정` | 0 | 진정 약물 투여량 | equip_props |
| `drug:임계` | 0 | 임계 약물 투여량 | equip_props |
| `mia_status` | None | MIA 상태 (None/mia/rescued) | survival.py |
| `hazard:{type}` | None | 환경 위협 (Location prop) | pollution.py 패턴 |

---

## 주의사항

### 호환성 깨지는 경우

```python
# BAD: prop이 없으면 에러
humanity = morld.get_unit_prop(unit_id, "humanity")
humanity -= 0.1  # None이면 에러!

# GOOD: 기본값 처리
humanity = morld.get_unit_prop(unit_id, "humanity")
if humanity is not None:
    morld.set_unit_prop(unit_id, "humanity", max(0.0, humanity - 0.1))
```

### 테스트 권장사항

- 시나리오02 에셋으로 시나리오03 시스템 테스트
- 새 시스템 추가 시 prop 없는 경우 테스트
- 기본값 동작 확인
- 기존 시나리오02 테스트 suite 통과 확인
