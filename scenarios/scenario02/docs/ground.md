# 바닥(Ground) 시스템 개선 계획

## 개요

Location의 "바닥" 오브젝트를 통한 아이템 관리 시스템 개선.
구조적 일관성(Location은 inventory 없음, Ground Object가 담당)을 유지하면서 UX를 개선한다.

## 현재 구조

```
Location (숲 입구)
  ├─ Object: 바닥 (inventory: [도토리 x3, 나뭇가지 x2])
  ├─ Object: 사과나무
  └─ Character: 세라
```

- Location은 inventory를 갖지 않음
- "바닥" Object가 떨어진 아이템을 저장
- 바닥 클릭 → Container Focus로 아이템 조작

---

## 구현 계획

### 1. Location에 ground_id 필드 추가

**목적:** Location이 자신의 바닥 오브젝트를 참조할 수 있도록 함

**Python (assets/base.py):**
```python
class Location:
    ground: Object = None      # 바닥 오브젝트 인스턴스 (Python 레벨)
    ground_id: int = None      # instantiate 후 설정되는 ID
```

**C# (Location.cs):**
```csharp
public int? GroundUnitId { get; set; }  // 바닥 오브젝트의 Unit ID
```

**morld API:**
```python
morld.get_location_ground_id(region_id, location_id)  # 바닥 오브젝트 ID 반환 (없으면 None)
```

---

### 2. 바닥에 버리기 액션

**설계 방침:** 특별 취급 (항상 표시, 실행 시 조건 체크)

**이유:**
- "버리기"는 기본 기능으로 사용자가 항상 존재한다고 기대
- Grey out보다 다이얼로그가 왜 안 되는지 설명 가능
- 저주 아이템은 `action_props: {"drop_floor": 0}` 또는 별도 prop으로 처리

**Item Focus에서의 동작:**
```
버리기 버튼 클릭 시:
  1. 아이템이 버릴 수 있는지 체크 (저주 등)
     → 불가: "이 아이템은 버릴 수 없다" 다이얼로그
  2. 현재 Location에 ground_id가 있는지 체크
     → 없음: "여기에는 버릴 수 없다" 다이얼로그
  3. 정상: 아이템을 바닥 오브젝트의 인벤토리로 이동
```

**URL 패턴:** `drop_floor` (C# HandleDropFloorAction에서 처리)

**구현 위치:**
- `MetaActionHandler.Item.cs` - HandleDropFloorAction 추가
- `describe_system.cs` - GetItemMenuText()에 버리기 버튼 추가

---

### 3. Situation 화면에 바닥 아이템 요약 표시

**목적:** 바닥 클릭 없이도 떨어진 아이템 확인 가능

**표시 형식:**
```
숲 입구

세라가 주변을 경계하고 있다.
사과나무가 있다.

[url=toggle:ground]▶바닥[/url]
[hidden=ground]
  도토리 x3
  나뭇가지 x2
[/hidden=ground]

이동 가능:
  저택 앞마당 (10분)
```

**조건:**
- 바닥 오브젝트가 존재하고 (`ground_id != null`)
- 바닥에 아이템이 1개 이상 있을 때만 표시

**토글 동작:**
- 기존 `toggle:ID` 시스템 그대로 사용
- 클릭하면 펼침/접힘만 되고 다른 액션 없음
- 상세 조작은 여전히 바닥 오브젝트 클릭 → Container Focus

**구현 위치:**
- `describe_system.cs` - GetSituationText()에서 바닥 아이템 요약 섹션 추가
- 또는 Python `ui.py`의 `get_action_text()`에서 처리

---

## 구현 순서

1. **C# Location.GroundUnitId 필드 추가**
   - `scripts/morld/terrain/Location.cs`
   - JSON 직렬화/역직렬화 지원

2. **Python Location.ground_id 연동**
   - `assets/base.py` - Location.instantiate()에서 ground_id 설정
   - `morld` API - get_location_ground_id() 추가

3. **바닥에 버리기 액션 구현**
   - `MetaActionHandler.Item.cs` - HandleDropFloorAction
   - `describe_system.cs` - 버리기 버튼 추가

4. **Situation에 바닥 아이템 표시**
   - `describe_system.cs` 또는 `ui.py`에서 바닥 아이템 요약 렌더링

---

## 결정 사항

- **버리기 액션:** A. 특별 취급 (항상 표시, 실행 시 조건 체크)
- **버리기 불가 아이템:** `action_props: {"drop_floor": 0}` 또는 별도 prop으로 처리 (추후 결정)
- **바닥 아이템 표시:** 기존 toggle 시스템 사용 (`toggle:ground` + `[hidden=ground]`)
