# 시나리오02/03 공용 확장 (Shared Extensions)

## 개요

이 문서는 시나리오03이 필요로 하지만, 시나리오02의 공유 코드베이스에 **확장**으로 구현해야 하는 기능 목록이다. 각 항목은 양쪽 시나리오 모두에 이점을 제공하며, [compatibility.md](compatibility.md)의 호환성 원칙을 준수한다.

핵심 원칙:
- **선택적 속성**: 새 prop/파라미터가 없으면 기존 동작 유지
- **기본값 적용**: 미지정 시 최적 상태로 간주
- **점진적 확장**: 기존 API 시그니처를 깨지 않음

---

## 1. 분대 대열 순번 — Party Rank System

### 대상 파일

`party.py`

### 현재 상태

Squad는 `leader_id` + 평탄한 `members` 리스트만 보유. 분대원 간 위치/역할 구분 없음.

### 확장 내용

`squad:rank` prop을 유닛에 부여하여 대열 순번을 표현한다.

| 값 | 의미 | 전투 시 역할 |
|----|------|-------------|
| `1` | 전위 | 피해를 먼저 받음, 근접 우선 |
| `2` | 중위 | 밸런스 포지션 |
| `3` | 후위 | 원거리/지원 |
| `None` | 미지정 | 기존 동작 유지 (순서 무관) |

### API

```python
def set_member_rank(unit_id: int, rank: int | None) -> None:
    """대열 순번 설정. rank=None이면 prop 제거."""
    if rank is None:
        morld.remove_unit_prop(unit_id, "squad:rank")
    else:
        morld.set_unit_prop(unit_id, "squad:rank", rank)

def get_member_rank(unit_id: int) -> int | None:
    """대열 순번 조회. 미지정이면 None."""
    return morld.get_unit_prop(unit_id, "squad:rank")
```

### 시나리오별 이점

| 시나리오 | 이점 |
|---------|------|
| S02 | 전투 포지셔닝 — 전위가 피해를 먼저 받음 |
| S03 | 마이크로턴 전투 핵심 — 대열 순번이 행동 순서와 피격 우선순위 결정 |

### 호환성

- `rank=None` → 기존 flat members 동작과 동일
- 시나리오02에서 rank를 설정하지 않으면 아무 영향 없음

---

## 2. 퀘스트 분대 조건 — Quest Squad Conditions

### 대상 파일

`quest/conditions.py`

### 현재 상태

`collect` 조건은 플레이어 인벤토리만 확인한다:

```python
# 현재 구현
count = morld.get_item_count(player_id, item_uid)
```

### 확장 내용

`source` 파라미터를 추가하여 조건 평가 범위를 확장한다.

| source 값 | 동작 |
|-----------|------|
| `"player"` (기본값) | 플레이어 인벤토리만 확인 (기존 동작) |
| `"squad"` | 분대원 전체 인벤토리 합산 |

### API

```python
def check_collect(player_id: int, item_uid: str, required: int,
                  source: str = "player") -> bool:
    """수집 조건 확인. source="squad"이면 분대원 합산."""
    if source == "squad":
        total = 0
        for uid in party.get_all_unit_ids():
            total += morld.get_item_count(uid, item_uid)
        return total >= required
    else:
        return morld.get_item_count(player_id, item_uid) >= required
```

### 시나리오별 이점

| 시나리오 | 이점 |
|---------|------|
| S02 | 파티 퀘스트 목표 — "파티원 합산 약초 10개 수집" |
| S03 | 분대 탐사 수집 퀘스트 — 분대원 누구든 주우면 카운트 |

### 호환성

- `source` 생략 시 기본값 `"player"` → 기존 동작 완전 유지
- 파티 없는 상태에서 `source="squad"` → 플레이어 단독 결과와 동일

---

## 3. 건축 원격 지정 — Build System Remote Designation

### 대상 파일

`build.py`

### 현재 상태

`build_location_frame(builder_id, ...)` 호출 시 `builder_id`가 필수이며, 해당 유닛이 소유자로 기록된다.

### 확장 내용

1. `builder_id=None` 허용 → 소유자를 `"system"` 또는 세력명으로 기본 설정
2. `designate_build()` 래퍼 — 건축 프레임 생성 + `build:designated` prop 부여

### API

```python
def designate_build(region_id: int, location_id: int, x: int,
                    blueprint_uid: str, owner: str = "system") -> int:
    """원격 건축 지정. NPC가 탐지할 수 있는 건축 현장 생성.

    Returns:
        construction_site_id: 생성된 건축 현장 유닛 ID
    """
    site_id = build_location_frame(
        builder_id=None, region_id=region_id,
        location_id=location_id, x=x, blueprint_uid=blueprint_uid
    )
    morld.set_unit_prop(site_id, "build:owner", owner)
    morld.set_unit_prop(site_id, "build:designated", 1)
    return site_id
```

### 시나리오별 이점

| 시나리오 | 이점 |
|---------|------|
| S02 | 스크립트/이벤트 기반 건설 — NPC 정착지 확장, 스토리 이벤트 건축 |
| S03 | 오퍼레이터 원격 건축 명령 — 플랫폼 시설 증설 지시 |

### 호환성

- 기존 `build_location_frame(builder_id, ...)` 호출은 변경 없음
- `build:designated` prop이 없는 건축 현장 → NPC가 무시 (기존 플레이어 건축과 충돌 없음)

---

## 4. NPC 건설 활동 — NPC Construction Activity

### 대상 파일

`think/activities/construct.py` (신규)

### 현재 상태

NPC 건설 활동 핸들러 없음. 건축은 플레이어 전용.

### 확장 내용

`handle_construct()` 활동 핸들러를 추가한다. 기존 `build.build_location_progress()` API를 호출하는 NPC 자동화 래퍼.

### Phase 흐름

```
idle → going_to_storage → carrying → going_to_site → building → idle
```

| Phase | 동작 | 사용 API |
|-------|------|---------|
| `idle` | `build:designated` prop 가진 ConstructionSite 탐색 | `morld.find_units_with_prop("build:designated")` |
| `going_to_storage` | 필요 재료 보관소로 이동 | `resolve_storage_container(agent, category)` |
| `carrying` | 재료 수취 | `morld.give_item()` |
| `going_to_site` | 건축 현장으로 이동 | `_move_to()` |
| `building` | 건축 진행 | `build.build_location_progress()` |
| `idle` (완료) | 다음 현장 또는 스케줄 복귀 | — |

### 스케줄 등록 예시

```python
# NPC 스케줄에 건설 활동 추가
schedule = [
    {"time": "09:00", "activity": "건설", "duration": 180},  # 3시간
]
```

### 시나리오별 이점

| 시나리오 | 이점 |
|---------|------|
| S02 | NPC 자율 건설 — 세라 울타리 수리, 밀라 부엌 개선 |
| S03 | 에이전트 건설 수행 — 오퍼레이터 지정 시설 증설 |

### 호환성

- 신규 파일이므로 기존 코드에 영향 없음
- `ACTIVITY_HANDLERS`에 `"건설": handle_construct` 등록 필요
- `build:designated` prop이 없으면 핸들러가 idle 유지 → 안전

---

## 5. NPC 스폰 유틸리티 — spawn_npc

### 대상 파일

`assets/` 또는 `utils/` (위치 미정)

### 현재 상태

NPC 생성에 3단계가 필요하다:

```python
# 현재: 3단계
unit_id = registry.create_id(unique_id)          # 1. ID 생성
asset_class.instantiate(unit_id)                  # 2. 에셋 초기화
agent_registry.register_agent(unit_id, AgentCls)  # 3. AI 등록
```

### 확장 내용

원라이너 유틸리티로 통합한다.

### API

```python
def spawn_npc(unique_id: str, region_id: int, location_id: int,
              x: int = 0, equipment: list[str] | None = None) -> int:
    """NPC를 생성하고 지정 위치에 배치한다.

    Args:
        unique_id: 에셋 고유 ID (예: "merchant_01")
        region_id: 배치할 Region ID
        location_id: 배치할 Location ID
        x: Location 내 x 좌표 (기본 0)
        equipment: 초기 장비 unique_id 리스트 (선택)

    Returns:
        unit_id: 생성된 유닛 ID
    """
    asset = registry.get_asset(unique_id)
    unit_id = registry.create_id(unique_id)
    asset.instantiate(unit_id)

    morld.set_unit_location(unit_id, region_id, location_id, x)

    if equipment:
        for eq_uid in equipment:
            item_id = registry.get_or_create_item_id(eq_uid)
            morld.give_item(unit_id, item_id)

    agent_cls = asset.agent_class or BaseAgent
    agent_registry.register_agent(unit_id, agent_cls)

    return unit_id
```

### 시나리오별 이점

| 시나리오 | 이점 |
|---------|------|
| S02 | 이벤트 기반 NPC 스폰 — 방문자, 상인, 습격자 |
| S03 | 에이전트 증원 — 보급 시 신규 분대원 배치 |

### 호환성

- 유틸리티 함수이므로 기존 코드에 영향 없음
- 기존 3단계 방식도 그대로 사용 가능

---

## 구현 우선순위

| 우선순위 | 항목 | 대상 파일 | S02 이점 | S03 필수 | 난이도 |
|---------|------|----------|---------|---------|--------|
| 1 | Party Rank System | `party.py` | 전투 포지셔닝 | **필수** (마이크로턴 핵심) | 낮음 |
| 2 | spawn_npc Utility | `assets/` 또는 `utils/` | 이벤트 NPC 스폰 | **필수** (증원) | 낮음 |
| 3 | Quest Squad Conditions | `quest/conditions.py` | 파티 퀘스트 | 높음 | 낮음 |
| 4 | Build Remote Designation | `build.py` | 스크립트 건설 | 중간 | 중간 |
| 5 | NPC Construction Activity | `think/activities/construct.py` | NPC 자율 건설 | 중간 | 높음 |

---

## 구현 상태

- [ ] Party Rank System (`party.py`)
- [ ] Quest Squad Conditions (`quest/conditions.py`)
- [ ] Build System Remote Designation (`build.py`)
- [ ] NPC Construction Activity (`think/activities/construct.py`)
- [ ] spawn_npc Utility
