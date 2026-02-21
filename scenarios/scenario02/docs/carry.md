# 운반 시스템 (Carry System)

유닛(캐릭터/오브젝트)을 들어올려 운반하는 시스템.

## 개요

**통합 Limbo + Pointer Item 방식**:
1. `pick_up`: target을 Limbo region으로 텔레포트 + 포인터 아이템을 carrier 인벤토리에 추가
2. `put_down`: target을 carrier 현재 위치로 텔레포트 + 포인터 아이템 제거

모든 유닛(캐릭터/오브젝트)을 동일한 방식으로 처리. 유닛이 Limbo에 있는 동안 원래 상태(props, 인벤토리)가 보존됨.

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `python/carry.py` | 핵심 운반 모듈 (API, 레지스트리, 포인터 아이템) |
| `python/chapters/__init__.py` | Limbo region 생성 (챕터 로드 시) |
| `python/think/__init__.py` | NPC Tier -1: 운반 중 상태 처리 |
| `python/assets/base.py` | 플레이어 액션 + Focus/Describe 텍스트 |

---

## Limbo Region

```
Region ID: 99 (LIMBO_REGION)
Location ID: 0 (LIMBO_LOCATION)
```

- Gate 없음 (NPC/플레이어 도보 접근 불가)
- 환경 시스템 미등록 (체온/습도/혼잡도 처리 안함)
- 챕터 `load_chapter()` 마다 재생성 (`clear_world()` 후)

## 포인터 아이템 (Pointer Item)

C 언어의 포인터처럼, Limbo에 있는 유닛을 가리키는 가상 아이템.

```
unique_id: "carry:{unit_unique_id}:{unit_id}"
name: "[세라]" 또는 "[의자]"
passive_props: {"운반:참조": unit_id}
actions: ["call:put_down:내려놓기"]
```

- `morld.add_item()`으로 동적 생성 (싱글톤 레지스트리 우회)
- `_CarryToken` 클래스: `call:put_down` 액션 처리용 Python 인스턴스
- `_carry_registry`: `item_id → carried_unit_id` 매핑

## Props

| 대상 | Prop | 값 | 설명 |
|------|------|----|------|
| 운반자 | `운반:대상` | carried_unit_id | 누구를 들고 있는가 |
| 운반자 | `운반:방식` | hash값 | 운반 유형 |
| 피운반자 | `운반:운반자` | carrier_unit_id | 누가 들고 있는가 |

### 운반 방식

| 상수 | 값 | 조건 |
|------|----|------|
| `METHOD_RESCUE` | `carry_rescue` | 기절/탈진 |
| `METHOD_FORCED` | `carry_forced` | 하체결박 |
| `METHOD_OBJECT` | `carry_object` | 오브젝트 |

---

## API

### 조회

```python
import carry

carry.is_being_carried(unit_id) → bool       # 운반 당하는 중인가
carry.get_carrier(unit_id) → int | None       # 운반자 unit_id
carry.is_carrying(carrier_id) → bool          # 무언가 운반 중인가
carry.get_carried_unit(carrier_id) → int | None  # 운반 대상 unit_id
carry.get_carry_method(carrier_id) → int      # 운반 방식 (hash)
```

### 검증

```python
carry.can_pick_up(carrier_id, target_id) → (bool, str)
```

검증 조건:
1. carrier가 이미 운반 중이 아닌지 (**용량 제한: 1명/1개**)
2. target이 이미 운반 중이 아닌지
3. 자기 자신이 아닌지
4. target 상태:
   - **캐릭터**: 기절 OR 탈진 OR 하체결박 상태만 가능
   - **오브젝트**: 좌석 점유(seated_by) 없음

### 실행

```python
carry.pick_up(carrier_id, target_id, method=None) → bool
```
1. `can_pick_up()` 검증
2. target을 Limbo로 텔레포트
3. 포인터 아이템 동적 생성 + carrier 인벤토리에 추가
4. 양쪽 props 설정
5. method가 None이면 자동 판정 (결박→forced, 기절→rescue, 오브젝트→object)

```python
carry.put_down(carrier_id) → bool
```
1. target을 carrier 현재 위치로 텔레포트
2. 포인터 아이템 제거
3. 양쪽 props 해제

### 챕터 전환

```python
carry.reset()  # _carry_registry 초기화
```

`chapters/__init__.py`의 `load_chapter()`에서 자동 호출.

---

## NPC Think 처리

### Tier -1: 운반 중

`think()` 최상단 (Tier 0 결박보다 앞)에서 `carry.is_being_carried()` 체크.

```
운반 중 → _handle_being_carried()
  ├─ 기절/탈진 해제 + 비결박 → 자동 put_down (의식 회복)
  ├─ 기절/탈진 해제 + 결박   → 운반 계속 (저항 대사 예정)
  └─ 기절/탈진 중            → "운반 중" idle job (1시간)
```

일반 think 로직은 완전 스킵.

---

## 플레이어 액션

### 들어올리기

Character/Object 클래스에 `pick_up_unit()` 메서드.

- **Character**: `_add_carry_action()`이 Focus 메뉴에 동적 추가 (기절/탈진 OR 하체결박 시)
- **Object**: `portable = True`인 서브클래스만 (현재 해당 없음)

### 내려놓기

인벤토리의 포인터 아이템에서 `call:put_down:내려놓기` 액션.
`_CarryToken.put_down()` → `carry.put_down(player_id)` 호출.

---

## Focus/Describe 텍스트

| 종류 | 조건 | 텍스트 |
|------|------|--------|
| Focus | `carrying=True` | `{carried_name}을(를) 업고 있다.` |
| Describe | `carrying=True` | `{name}(이)가 {carried_name}을(를) 업고 있다.` |

`_build_context()`에서 `carry.get_carried_unit()` 기반으로 context 구성.

---

## 환경 시스템 호환

Limbo는 환경 시스템에 등록되지 않으므로 자연히 처리 skip:

| 시스템 | 영향 |
|--------|------|
| temperature | 등록 location만 순회 → skip |
| humidity | 등록 location만 순회 → skip |
| congestion | `on_reach/on_leave`에서 `key not in _population` 가드 → skip |
| pollution | `register_location()` 명시적 등록 → skip |

단기 운반이므로 체온/습도 동결 허용.

---

## 향후 확장 (TODO)

| 기능 | 설명 | 의존성 |
|------|------|--------|
| 복수 운반 | 용량 제한 해제 + UI 변경 | carry.py |
| NPC AI 운반 | think activity handler (구조/어부바) | carry.py + think |
| 건설 시스템 | 오브젝트 배치/회수 | carry.py + 건설 아이템 |
| 시체 시스템 | 사망→시체 전환 | carry.py + 전투 시스템 |
| 수면 중 운반 | 수면 유형 prop 추가 | carry.py + survival |
| 운반 방식별 텍스트 | 구조→업고, 강제→끌고, 오브젝트→들고 | base.py |
| 피운반자 묘사 | 의식 있는 결박 캐릭터 시점 | base.py |
| NPC 목격 반응 | 운반 중 다른 NPC 반응 | 이벤트 시스템 |
| 포인터 아이템 cleanup | RemoveItem Python API 노출 | C# 수정 |
| 결박 저항 대사 | 의식+결박 상태 운반 시 반응 | think + 대사 |
