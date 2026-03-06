# NPC 스케줄 시스템

NPC의 일과를 정의하고 자동으로 행동하게 하는 시스템입니다.

---

## 현재 상태 요약

### 핵심 구조
| 구성 요소 | 역할 | 파일 |
|----------|------|------|
| Schedule | NPC 일과 정의 (시간대별 위치/활동) | 캐릭터 파일의 `SCHEDULE` |
| Job | 실행 중인 작업 단위 | `Job.cs` |
| JobList | Job 큐 (시간 기반 선형 리스트) | `JobList.cs` |
| ThinkSystem | 매 턴 Agent.think() 호출 | `think_system.cs` |
| Agent | NPC별 AI 로직 | `think/__init__.py` |

### 데이터 흐름
```
Schedule (정적 데이터)
    ↓ fill_schedule_jobs_from()
JobList (동적 큐)
    ↓ JobBehaviorSystem.Proc()
실제 이동/행동
```

---

## 1. Schedule 정의

### 형식
```python
SCHEDULE = [
    {
        "name": "아침식사",      # 표시용 이름
        "region_id": 0,         # 목적지 Region
        "location_id": 3,       # 목적지 Location
        "x": 90,                # (Pi-World) 목표 X 좌표 (location_id 있으면 필수)
        "start": 25_200_000,    # 시작 시간 (밀리초, 7:00 = 25,200,000)
        "end": 28_800_000,      # 종료 시간 (밀리초, 8:00 = 28,800,000)
        "activity": "식사"      # 활동 유형 (Job.Name으로 사용)
    },
    ...
]
```

### Pi-World 좌표 (x 필드)
`x` 필드는 Location 내 구체적인 목표 위치를 지정합니다.

**용도:**
- NPC가 Location 내 특정 오브젝트 위치로 이동
- 예: 식당(location_id=3)의 식탁 의자(x=90)로 이동

**필수 조건:**
- `location_id`가 명시된 경우 `x` 필드 **필수**
- `location_id` 없이 `activity`만 지정하면 현재 위치에서 대기 (이동 없음)
- 좌표값은 [terrain.md](terrain.md)의 오브젝트 위치 참고
- `y` 필드도 지원 (확장용, 현재는 사용 안 함)

### 시간 변환
| 시간 | 밀리초 | 계산 |
|------|--------|------|
| 00:00 | 0 | - |
| 06:00 | 21,600,000 | 6×3,600,000 |
| 07:00 | 25,200,000 | 7×3,600,000 |
| 12:00 | 43,200,000 | 12×3,600,000 |
| 18:00 | 64,800,000 | 18×3,600,000 |
| 22:00 | 79,200,000 | 22×3,600,000 |
| 23:59 | 86,340,000 | - |

> **참고**: `GameTime.MillisPerHour = 3,600,000`, `MillisPerMinute = 60,000`

### 자정 넘기기
수면처럼 자정을 넘는 스케줄은 `end < start`로 정의:
```python
{"name": "수면", "start": 79_200_000, "end": 21_600_000, "activity": "수면"}
# 22:00 ~ 다음날 06:00
```

### 현재 위치 대기 (STAY_SCHEDULE 패턴)
`location_id`를 지정하지 않으면 NPC는 현재 위치에서 이동 없이 대기합니다:
```python
# 임시 홀드용 (연애/NPC 주도 중 시간 정지 상태에서 사용)
STAY_SCHEDULE = [
    {"name": "대기", "start": 0, "end": 86_400_000, "activity": "대기"}
    # location_id 없음 → 이동 없이 현재 위치에서 대기
]
```

**동작:**
- `location_id` 없음 = 이동 Job 생성 안 함
- NPC는 현재 위치에 머무름
- `activity`는 표시용 (대화에서 "대기 중" 등으로 표현)

### "대기" vs "할 일 없음"

| 용어 | 의미 | 발생 조건 |
|------|------|----------|
| **대기** | 필요에 의해 제자리 대기 | handler abort/brief, 목욕 대기, 발각 처리 등 |
| **할 일 없음** | 스케줄 비어있음 + 모든 욕구 충족 | safety net 또는 tier 5 fallback |

- 스케줄 갭 (현재 시간에 해당하는 entry 없음) → safety net → "할 일 없음"
- 스케줄 entry의 dynamic 후보 전부 실패 → "할 일 없음"
- handler abort: 조건 미충족/자원 없음 등으로 핸들러가 조기 종료 → "대기" (5분)

### 순찰/산책 Wandering

`순찰`과 `산책` 활동은 도착 후 제자리 대기가 아닌, 실제로 근처 location을 돌아다닙니다.

```python
_WANDER_ACTIVITIES = frozenset({"순찰", "산책"})
```

**동작:**
- target 있으면 → target으로 이동 → 도착 후 wandering 시작
- target 없으면 → 즉시 wandering 시작
- wandering: `_do_wander()` — 랜덤 location 선택 → 이동 → 10~30분 휴식 → 반복
- 잔여 시간 5분 미만이면 wandering 중단, 대기

**그 외 활동** (벌목, 낚시, 채집 등): target=None이면 현재 위치에서 대기 (wandering 하지 않음).

### Idle Flavor 시스템 (v0.2.3)

NPC가 대기/순찰 휴식 중일 때, 하나의 긴 idle 대신 **5~15분 짧은 idle을 반복**하여 다양한 행동 묘사를 제공합니다. DES의 자연 재호출(job 만료 → think())을 활용합니다.

```
think() → flavor 클리어
  ↓
Tier 5: _insert_flavored_idle("순찰", 40분)
  ├─ job name = "순찰" (activity 불변)
  ├─ flavor = "기지개" (모듈 딕셔너리 저장)
  └─ duration = 10분 (짧게)
  ↓
10분 후 job 만료 → think() 재호출 → flavor = "콧노래"
```

**flavor 선택 3-tier 우선순위:**
1. **오브젝트 근접**: 벽난로(heat:output) → "불멍"/"온기", 의자(can:sit) → "앉아쉬기"
2. **실내/실외**: 실내 → "창밖구경"/"정리", 실외 → "하늘구경"/"바람쐬기"
3. **공통 + 아키타입**: "기지개"/"스트레칭" 등 공통 + stoic="경계"/"명상" 등 전용

**적용 범위:**
- 순찰/산책 wandering 도착 후 휴식 (`_do_wander` → 10~30분 체류)
- 비순찰 활동의 실행 후 나머지 시간 대기
- target=None인 비순찰 활동의 제자리 대기

**적용 제외:** sleep, bath, faint, 인터럽트 핸들러의 idle

### Safety net 원인 추적

think()의 safety net은 `_action_taken=False`일 때 WARNING을 출력하며, 진단 정보를 포함합니다:

```
WARNING: {name} has no current job (tier={tier_reached}, phases: cold={cold_phase}, hot={hot_phase}, ...)
```

이는 에러 자체가 아닌 **왜 에러가 발생했는지를 파악**하기 위한 시스템입니다.
`_action_taken`은 자기 선언형 플래그로, handler가 job을 삽입하면 True를 설정합니다.

---

## 2. Job 구조

### 필드
```csharp
public class Job
{
    public string Name;       // 표시용 ("사냥", "식사", "순찰")
    public string Action;     // 실제 동작 ("move", "stay", "follow", "flee")
    public int RegionId;      // 목적지 Region
    public int LocationId;    // 목적지 Location
    public float TargetX;     // (Pi-World) 목표 X 좌표
    public float TargetY;     // (Pi-World) 목표 Y 좌표 (확장용)
    public int Duration;      // 남은 시간 (밀리초)
    public int? TargetId;     // follow/flee 대상
}
```

### Action 타입
| Action | 설명 | 필수 필드 |
|--------|------|----------|
| `move` | 목표 위치로 이동 | RegionId, LocationId, TargetX |
| `stay` | 현재 위치에서 대기 | Duration |
| `follow` | 대상 유닛 따라가기 | TargetId, Duration |
| `flee` | 대상 유닛으로부터 도망 | TargetId, Duration |

> **참고**: 스케줄 항목에서 현재 위치 대기를 원하면 `location_id`를 생략하세요. (이전의 `"action": "stay"` 패턴은 더 이상 지원되지 않습니다.)

---

## 3. get_unit_info 반환값

현재 NPC가 알 수 있는 정보:

```python
info = morld.get_unit_info(unit_id)
# {
#     "id": 5,
#     "name": "리나",
#     "region_id": 0,           # 현재 위치
#     "location_id": 20,        # 현재 위치
#     "activity": "채집",       # 현재 Job의 Name (스케줄 activity)
#     "schedule_name": "채집",  # 동일 (호환용)
#     "is_moving": True,        # 이동 중 여부
#     "is_object": False
# }
```

### 문제점
- **목적지 정보 없음**: Job의 RegionId/LocationId가 노출되지 않음
- NPC가 "채집하러 가는 중" vs "채집 중"을 구분하려면 목적지를 알아야 함

### 개선 제안
```python
# 추가되면 좋을 필드
info = {
    ...
    "dest_region_id": 0,      # 현재 Job의 목적지
    "dest_location_id": 23,   # 현재 Job의 목적지
    "job_action": "move",     # 현재 Job의 Action
}
```

그러면 NPC 대화에서:
```python
def get_status_text(self):
    info = morld.get_unit_info(self.instance_id)
    activity = info.get("activity")
    is_moving = info.get("is_moving")

    if is_moving:
        return f"{activity}하러 가는 중이에요~"
    else:
        return f"{activity} 중이에요~"
```

---

## 4. JobList 조작

### 삽입 방식
| 방식 | 메서드 | 설명 | 용도 |
|------|--------|------|------|
| Clear | `InsertWithClear()` | 기존 Job 모두 제거 후 삽입 | 플레이어 이동 명령 |
| Prepend | `Prepend()` | 맨 앞에 삽입 (기존 보존) | 긴급 행동 |
| Override | `InsertOverride()` | 기존 Job을 잘라내고 삽입 | NPC 명령 오버라이드 |
| Merge | `InsertMerge()` | 빈 공간에만 삽입 | 스케줄 채우기 |

### Python API
```python
# 스케줄 기반 채우기 (기존 Job 유지, 빈 시간만 채움)
morld.fill_schedule_jobs_from(unit_id, SCHEDULE)

# Job 삽입 (기존 Job 제거 후 삽입) — think()에서 주로 사용
morld.insert_job(unit_id, {
    "name": "이동", "action": "move",
    "region_id": 0, "location_id": 3,
    "target_x": 90, "duration": 0,
})

# NPC Job 즉시 설정 (Override)
morld.set_npc_job(unit_id, "follow", duration=1_800_000)  # 30분

# 시간 경과 포함 Job 설정
morld.set_npc_time_consume(unit_id, "stay", duration=1_800_000)  # 30분
```

> **참고**: `insert_job`은 `InsertJobWithClear` 사용 (기존 Job 전부 제거 후 1개 삽입).
> `_move_to()`는 매 호출마다 새 move job을 삽입합니다 (InsertJobWithClear가 기존 job 정리).
> 이전 step에서 이동 미완료 시에도 새 job으로 갱신되어 정상 동작합니다.

> **v0.2.2 DES**: move Job의 duration이 0 이하이면 C#이 자동으로 이동 시간 계산.
> 같은 Location 내 이동: `CalculateTravelTime()` 사용. 다른 Location: `PathFinder` 사용.
> 최소 1분, hop당 최소 2분 보장.

---

## 5. NPC별 스케줄 예시

### 세라 (사냥꾼) — 평일/주말 분리

v0.2.1에서 `SCHEDULES` dict로 변경. `think()`에서 `morld.get_time_info()["day"] % 7`로 평일/주말 자동 감지.

**평일:**
```
05:00 아침목욕    → 욕실
05:30 기상(준비)  → 세라방
06:00 아침순찰    → 앞마당
07:00 아침식사    → 식당
09:00 오전활동    → (동적: 낚시 > 벌목 > 순찰)   ← v0.2.1 동적 스케줄
12:00 점심식사    → 식당
14:00 오후활동    → (동적: 벌목 > 낚시 > 순찰)   ← v0.2.1 동적 스케줄
17:00 저녁순찰    → 숲 입구
18:30 저녁식사    → 식당
20:00 장비정비    → 세라방
21:00 저택 소등   → (동적 탐색)
21:30 수면        → 세라방
```

**주말 (day % 7 >= 5):**
```
05:00 아침목욕 → 06:00 기상 → 06:30 아침순찰 → 08:00 아침식사
→ 10:00 독서(거실) → 12:00 점심식사 → 14:00 순찰 → 16:00 자유시간
→ 18:30 저녁식사 → 21:00 소등 → 21:30 수면
```

### 리나 (채집 담당) — 동적 채집/독서

```
06:00 아침목욕    → 욕실
06:30 기상(준비)  → 리나방
07:00 아침식사    → 식당
08:00 빨래        → 뒷마당
09:00 오전활동    → (동적: 채집 if need_food > 독서)  ← v0.2.1
12:00 점심식사    → 식당
14:00 오후활동    → (동적: 채집 if need_food > 독서)  ← v0.2.1
17:00 빨래걷기    → 뒷마당
18:30 저녁식사    → 식당
19:30 자유시간    → 거실
21:30 저택 소등   → (동적 탐색)
22:00 수면        → 리나방
```

> 채집 시 `_handle_gather_store`: 자원 채집 → `storage:food_ingredient` 컨테이너에 동적 보관.

### 밀라 (요리 담당, 계절별 SCHEDULES) — 동적 요리/청소

밀라는 `SCHEDULES` dict를 사용하여 계절별로 다른 스케줄을 적용합니다.
`MilaAgent.think()`에서 계절 변경을 감지해 자동 전환합니다.

**봄 기준:**
```
05:00 아침목욕    → 욕실
05:30 기상(준비)  → 밀라방
06:00 아침준비    → (동적: 요리 if can_cook > 청소 if should_clean > 휴식)  ← v0.2.2
07:00 아침식사    → 식당
08:00 설거지      → 주방
09:00 청소        → (동적: 청소 if should_clean > 휴식)  ← v0.2.2
11:00 점심준비    → (동적: 요리 if can_cook > 청소 if should_clean > 휴식)  ← v0.2.2
12:00 점심식사    → 식당
13:00 정원가꾸기  → 뒷마당 (봄 한정)
17:00 저녁준비    → (동적: 요리 if can_cook > 청소 if should_clean > 휴식)  ← v0.2.2
18:30 저녁식사    → 식당
19:30 정리        → 주방
21:30 저택 소등   → (동적 탐색)
22:00 수면        → 밀라방
```

**계절별 차이점:**
| 계절 | 기상 | 오후 활동 | 소등/수면 |
|------|------|----------|----------|
| 봄 | 05:00 | 정원가꾸기 | 21:30/22:00 |
| 여름 | 04:00 | 낮잠(더위) | 22:30/23:00 |
| 가을 | 05:00 | 저장식품준비 | 21:30/22:00 |
| 겨울 | 06:00 | 실내휴식 | 20:30/21:00 |

### 엘라 (정찰병, 도시) — 동적 물자수집

```
06:00 기상       → 은신처
06:30 목욕       → 은신처 드럼통
07:00 아침식사   → 은신처
08:00 정찰(약국) → 약국
09:30 오전활동   → (동적: 물자수집 if need_supplies > 순찰)  ← v0.2.1
12:00 점심식사   → 은신처
14:00 관리       → 은신처
16:00 정찰(도시입구) → 도시입구
18:30 저녁식사   → 은신처
20:00 휴식       → 은신처
22:00 수면       → 은신처
```

> 보관소: `storage:food` prop 기반 동적 탐색. 물자수집: ScavengeableObject 탐색.

### 유키 (요리사, 도시) — 동적 요리/독서

```
06:00 목욕       → 은신처 드럼통
06:30 기상       → 은신처
07:00 아침식사   → 은신처
08:00 청소       → 은신처
09:30 오전활동   → (동적: 요리 if can_cook > 독서)  ← v0.2.1
12:00 점심식사   → 은신처
13:00 정원       → 은신처 텃밭 (2이랑)  ← v0.2.2
15:00 휴식       → 은신처
18:30 저녁식사   → 은신처
20:00 독서       → 은신처
22:00 수면       → 은신처
```

> 보관소: `storage:food_ingredient` prop 기반 동적 탐색. 요리: PortableStove.npc_cook().

---

## 6. 현재 한계점

### 문제점
| 항목 | 현재 상태 | 문제 |
|------|----------|------|
| 위치 결정 | 고정 + 동적 탐색 혼용 | 대부분 동적화 완료 (v0.2.1) |
| activity 효과 | **9종 구현됨** (v0.2.1~v0.2.2) | 벌목/채집/낚시/요리/청소(도구+오염도)/물자수집/식사/소등/정원 |
| 자원 관리 | **구현됨** (v0.2.1) | 만복도 추적, 배고프면 자동 식사 |
| 도구 사용 | **벌목 도끼 + 낚시대** (v0.2.1) | 바구니 등은 미구현 |
| 목적지 정보 | Python에 미노출 | "~하러 가는 중" 표현 불가 |

### 남은 개선 (단기)
1. **목적지 정보 노출**
   - `get_unit_info()`에 `dest_region_id`, `dest_location_id` 추가
   - NPC가 "채집하러 가는 중" vs "채집 중" 구분 가능

---

## 7. 진보된 스케줄 시스템 (계획)

### Phase 1: Context 기반 Activity 중심 Location 탐색 — 구현됨 (v0.2.1)

**구현 완료:**
- `activity_resolver.py` — 활동별 동적 위치 탐색
- 스케줄에서 `location_id` 생략 시 자동으로 resolver 호출
- 구현된 resolver: `채집`, `사냥`, `순찰`, `벌목`, `낚시`, `독서`, `물자수집`

```python
# 스케줄에서 location_id 없이 activity만 지정
SCHEDULE = [
    {"name": "채집", "start": 540*_M, "end": 720*_M, "activity": "채집"},
    {"name": "벌목", "start": 840*_M, "end": 1020*_M, "activity": "벌목"},
]

# think/__init__.py의 _resolve_target()에서 자동 분기:
# - location_id 있으면 → 고정 장소
# - location_id 없으면 → activity_resolver.resolve_activity_location() 호출
```

---

### Phase 2: 영향력 있는 Activity — 구현됨 (v0.2.1)

**구현 완료 (10종 모듈화: `think/activities/`):**
- `소등`: `handle_lights_off()` → 조명 끄기 (방 순회, 열원 제외)
- `점등`: `handle_lights_on()` → 조명 켜기 (방 순회, 열원 제외)
- `벌목`: `handle_chop()` → 도끼 가져오기 → 벌목 → 도끼 반납
- `낚시`: `handle_fish()` → 낚시대 가져오기 → 낚시 → 보관소에 저장 → 반납
- `채집→저장`: `handle_gather_store()` → 채집 → 보관소에 동적 저장
- `요리`: `handle_cook()` → 보관소 재료 확인 → 화로/아궁이 요리 → 결과물 저장
- `청소`: `handle_clean()` → 빗자루(can:clean) 가져오기 → 오염 방 순회 청소 → 반납
- `물자수집`: `handle_scavenge()` → ScavengeableObject 탐색 → 식량 보관함에 저장
- `정원`: `handle_garden()` → 텃밭 이동 → 수확/물주기/씨심기 → 수확물 저장

**`think/__init__.py` 내 (인라인):**
- `식사`: `_handle_eat()` → 보관소에서 음식 꺼내 먹기 (배고픔 인터럽트, 동적 탐색)

---

### Phase 3: 상호작용하는 Agent — 부분 구현됨 (v0.2.1)

**구현된 부분:**
```python
class BaseAgent:
    def think(self):
        # 1. 배고픔 체크 - 스케줄보다 우선
        if self._check_hunger():
            return None  # _handle_eat이 job 삽입

        # 2. 동적 스케줄 - 조건 기반 활동 선택
        entry = self._resolve_dynamic_entry(entry)
        # candidates 리스트에서 조건 평가 후 활동 결정

        # 3. 활동 핸들러 디스패치
        handler = _ACTIVITY_HANDLERS.get(activity)
        if handler:
            handler(self, entry)
```

**구현 요소:**
- NPC용 생존 시스템 (포만감 추적, 시간 경과 감소)
- `_check_hunger()`: 포만감 30 이하 → 식사 인터럽트
- `_resolve_dynamic_entry()`: 조건 기반 동적 활동 선택
- `_evaluate_condition()`: need_fish, need_logs, need_food, can_cook, need_supplies, should_clean, need_fuel, need_fuel_material
- 도구 자동 관리 (도끼, 낚시대, 빗자루)

**미구현:**
- NPC 주도 대화

**v0.2.2 추가 구현:**
- 추위/더위 인터럽트 → 의류 자동 착탈 (`_check_cold`/`_check_hot`)
- 시설 탐색 리졸버 → 목욕/화장실 선착순 + 옷장 소유권 탐색 (`facility_resolver.py`)
- **욕구 수치화** → `needs.py` (배변/피로/청결/사회/성욕) 매시간 추적
- **배변 인터럽트** → `_check_excretion()` + `_handle_excretion()` (Tier 4)
- **피로 인터럽트** → `_check_fatigue()` + `_handle_sleep()` 재사용 (Tier 4)
- **청결 인터럽트** → `is_npc_need_bath()` + `_handle_bath()` 재사용 (Tier 4)
- **5-tier 우선순위** → think() 재구성 (Involuntary/Reactive/Survival/Comfort/Routine)

---

### 동적 스케줄 시스템 (v0.2.1)

스케줄 entry에 `"dynamic": True`와 `"candidates"` 리스트 추가:

```python
{"name": "오전활동", "start": 9*H, "end": 12*H,
 "dynamic": True, "candidates": [
     {"activity": "낚시", "condition": "need_fish", "priority": 2},
     {"activity": "벌목", "condition": "need_logs", "priority": 1},
     {"activity": "순찰", "condition": None, "priority": 0},  # fallback
 ]}
```

조건 평가 (`_evaluate_condition`):
| 조건 | 의미 | 체크 방법 |
|------|------|----------|
| `need_fish` | 물고기 부족 | `storage:food_ingredient` 컨테이너에 food_fish < 기준치 |
| `need_logs` | 통나무 부족 | `storage:material` 컨테이너에 log < 기준치 |
| `need_food` | 식량 부족 | `storage:food_ingredient` 컨테이너에 food_ingredient 카테고리 아이템 < 기준치 |
| `can_cook` | 요리 가능 | `storage:food_ingredient` 컨테이너에 food_ingredient 카테고리 재료 ≥ 2 |
| `need_supplies` | 물자 부족 | `storage:food` 컨테이너에 food 카테고리 아이템 < 기준치 |
| `should_clean` | 청소 필요 | 거처 내 오염도 > 0인 location 존재 |
| `need_social` | 사교 필요 | `needs.get_max_longing(unit_id) >= 50` (최대 그리움 기반) |
| `need_fuel` | 연료 부족 | 거처 내 열원에 연료 부족 |
| `need_fuel_material` | 연료 재료 부족 | `storage:material` 컨테이너에 branch < 기준치 또는 log < 기준치 |

> **기준치 결정**: 컨테이너에 `need:{item_uid}` prop이 설정되어 있으면 해당 값을 기준치로 사용.
> 없으면 코드의 fallback 값 사용 (예: need_fish → 3, need_logs → 5).
> 상세: [make_activity.md](make_activity.md#보관-시스템-storage-system)

---

### 구현 우선순위

| 단계 | 내용 | 난이도 | 효과 | 상태 |
|------|------|--------|------|------|
| 0 | 목적지 정보 노출 | 낮음 | 대화 개선 | 미구현 |
| 1a | activity_resolver 동적 탐색 | 중간 | 유연한 위치 결정 | **구현됨** (7종) |
| 1b | Location.activities 범용 매핑 | 중간 | 확장성 | 미구현 |
| 2a | 활동 효과 | 중간 | 활동 효과 | **구현됨** (8종) |
| 2b | 보관함 자동 이동 | 중간 | 자원 순환 | **구현됨** |
| 3a | NPC 만복도 시스템 | 높음 | 자율 행동 | **구현됨** |
| 3b | 동적 스케줄 | 높음 | 조건 기반 선택 | **구현됨** |
| 3c | 도구/의류 자동 관리 | 높음 | 완전 자율 | **도구 구현됨** (도끼/낚시대/빗자루) |

---

## 8. v0.2.1 Phase 시스템

### 개요

v0.2.1에서 도입된 **Phase-based Activity** 시스템. 다단계 활동(벌목: 도끼 가져오기 → 벌목 → 도끼 반납)을 지원합니다.

### 상태 변수

```python
self._activity_phase = "idle"    # 활동 내 단계
self._activity_state = {}        # 활동별 임시 데이터
self._action_taken = False       # 행동 결정 여부 (경고용)
```

activity가 변경되면 자동 리셋됩니다.

### 지속 기억 (`_memory` dict) — v0.2.2

활동 간/턴 간 유지되어야 하는 데이터를 `_memory` dict에 통합합니다.
`_activity_state`는 활동 변경 시 리셋되지만, `_memory`는 유지됩니다.

```python
self._memory = {
    "tool": {},              # 도구 반납 위치 {item_id: {"container_id", "location"}}
    "hunger_phase": None,    # 식사 인터럽트 단계 (None/idle/going_to_storage/taking_food/eating)
    "cold_phase": None,      # 방한 인터럽트 단계 (None/idle/going/taking/equipping)
    "cold_last_attempt": None,  # 추위 대응 쿨다운 타임스탬프
    "hot_phase": None,       # 더위 인터럽트 단계 (None/idle/unequipping/storing)
    "excretion_phase": None, # 배변 인터럽트 단계 (None/idle/going/using)
    "current_season": None,  # 밀라 계절 추적
    "current_day_type": None # 세라 요일 타입 추적
}
```

| 키 | 용도 | 사용 NPC |
|----|------|----------|
| `tool` | 도구를 가져온 컨테이너 위치 기억 (반납 시 사용) | 벌목/낚시/청소 |
| `hunger_phase` | 식사 인터럽트 multi-step 상태 | 전체 |
| `cold_phase` | 방한 인터럽트 단계 | 전체 (resolve_wardrobe 가능 NPC) |
| `cold_last_attempt` | 추위 대응 쿨다운 (1시간) | 전체 |
| `hot_phase` | 더위 인터럽트 단계 | 전체 |
| `excretion_phase` | 배변 인터럽트 단계 | 전체 (resolve_toilet 가능 NPC) |
| `excretion_target` | 배변 대상 화장실 캐시 | 전체 |
| `current_season` | 계절 변화 감지 → 스케줄 갱신 | 밀라 |
| `current_day_type` | 요일 타입 변화 감지 → 스케줄 갱신 | 세라 |

### 활동 핸들러 디스패치

핸들러는 `think/activities/` 패키지에 모듈화되어 있으며, `ACTIVITY_HANDLERS` dict로 자동 등록됩니다.

```python
# think/activities/__init__.py
from .lights import handle_lights_off, handle_lights_on
from .chop import handle_chop
from .fish import handle_fish
from .gather import handle_gather_store
from .cook import handle_cook
from .clean import handle_clean
from .scavenge import handle_scavenge
from .garden_activity import handle_garden
from .fuel import handle_fuel

ACTIVITY_HANDLERS = {
    "소등": handle_lights_off,
    "점등": handle_lights_on,
    "벌목": handle_chop,
    "낚시": handle_fish,
    "채집": handle_gather_store,
    "요리": handle_cook,
    "청소": handle_clean,
    "물자수집": handle_scavenge,
    "정원": handle_garden,
    "연료수집": handle_fuel,
    "난방 연료 수집": handle_branch_collect,
}

# think/__init__.py에서 import하여 사용:
from think.activities import ACTIVITY_HANDLERS as _ACTIVITY_HANDLERS

# think() 내부:
handler = _ACTIVITY_HANDLERS.get(activity)
if handler:
    handler(self, entry)        # 전용 핸들러
else:
    self._handle_default_activity(entry)  # 기본 (이동→환경체크→실행)
```

### 핸들러 모듈 구조

```
think/activities/
├── __init__.py          # ACTIVITY_HANDLERS dict (핸들러 등록)
├── helpers.py           # 공용 헬퍼 (resolve_storage_container, store_npc_items, resolve_branch_tree 등)
├── lights.py            # 소등/점등 (3-phase 조명 관리)
├── chop.py              # 벌목
├── fish.py              # 낚시
├── gather.py            # 채집→저장
├── cook.py              # 요리
├── clean.py             # 청소
├── scavenge.py          # 물자수집
├── garden_activity.py   # 정원 (텃밭 관리)
├── fuel.py              # 연료수집 (나뭇가지 줍기 → 열원 장전)
└── branch_collect.py    # 난방 연료 수집 (나뭇가지 줍기 → 보관소 비축)
```

새 활동 핸들러 추가 시: 모듈 파일 생성 → `__init__.py`에 import + dict 등록 → 스케줄에 activity 이름 지정

### 벌목 Phase 흐름

```
idle → getting_tool → going_to_tree → storing_logs → returning_tool → idle
```

| Phase | 설명 |
|-------|------|
| `idle` | 충분성 체크 (`_check_storage_need("material", "log", 5)`), 도끼 소지 확인 → 있으면 `going_to_tree`, 없으면 `getting_tool` |
| `getting_tool` | 창고(도구함)로 이동 → 도착 시 도끼 pick up → `going_to_tree` |
| `going_to_tree` | 나무 위치로 이동 → 도착 시 npc_chop → `storing_logs` |
| `storing_logs` | `resolve_storage_container(agent, "material")` → 보관소로 이동 → `store_npc_items(categories=["material"])` → `returning_tool` |
| `returning_tool` | 창고로 이동 → 도착 시 도끼 반납 → `idle` |

### 소등 Phase 흐름

```
idle → going → idle → going → ... → idle (완료)
```

| Phase | 설명 |
|-------|------|
| `idle` | 조명 켜진 실내 방 탐색 → 있으면 `going`, 없으면 완료 |
| `going` | 해당 방으로 이동 → 도착 시 조명 끄기 → `idle` (다음 방) |

### 청소 Phase 흐름 (v0.2.2)

```
idle → getting_tool → going_to_room ↔ (다음 방) → returning_tool → idle
```

| Phase | 설명 |
|-------|------|
| `idle` | `_find_tool_by_capability("can:clean")` → 빗자루 탐색, `find_polluted_room()` → 오염 방 탐색 |
| `getting_tool` | 도구함으로 이동 → 빗자루 pick up → `going_to_room` |
| `going_to_room` | 오염 방으로 이동 → 도착 시 `pollution.clean_location()` + 10분 대기 → 다음 방 or `returning_tool` |
| `returning_tool` | 도구함으로 이동 → 빗자루 반납 → `idle` |

### 연료수집 Phase 흐름 (v0.2.2)

```
idle → going_to_tree → going_to_heat_source → idle
```

| Phase | 설명 |
|-------|------|
| `idle` | `find_heat_source_needing_fuel()` → 연료 부족 열원 탐색, `resolve_branch_tree()` (helpers) → 나뭇가지 있는 나무 탐색. 둘 다 없으면 대기 |
| `going_to_tree` | 나무로 이동 → 도착 시 `npc_gather_branch()` ×3 → `going_to_heat_source` |
| `going_to_heat_source` | 열원으로 이동 → 도착 시 `_load_all_fuel()` (인벤토리의 branch/log 전부 장전) → `idle` |

**스케줄 조건**:
- `need_fuel` — `_check_heat_source_needs_fuel()`로 거처 내 연료 부족 열원 확인.
- `need_fuel_material` — `material` 컨테이너에서 branch/log 부족 확인 (prop 기반 기준치).

엘라 스케줄에서 물자수집/관리 시간대에 dynamic 후보로 등록.

### 난방 연료 수집 Phase 흐름 (v0.2.2)

```
idle → going_to_tree → going_to_storage → idle
```

| Phase | 설명 |
|-------|------|
| `idle` | 충분성 체크 (`_check_storage_need("material", "branch/log")`), `resolve_branch_tree()` (helpers) → 나뭇가지 있는 나무 탐색 |
| `going_to_tree` | 나무로 이동 → 도착 시 `npc_gather_branch()` ×3 → `going_to_storage` |
| `going_to_storage` | `resolve_storage_container(agent, "material")` → 보관소로 이동 → `store_npc_items(categories=["material"])` → `idle` |

**연료수집과의 차이**: 연료수집은 열원에 직접 장전, 난방 연료 수집은 material 컨테이너에 비축.
엘라 스케줄에서 `need_fuel_material` 조건으로 dynamic 후보 등록.

> 활동 핸들러 작성 가이드: [make_activity.md](make_activity.md)

### 리소스 검증

활동 핸들러는 자원 오브젝트의 `has_resource()` 메서드로 자원 존재 여부를 확인합니다.

| 오브젝트 | `has_resource()` | 자원 관리 |
|----------|-----------------|-----------|
| `TreeObject` | 인벤토리에 log 있음 | 벌목 시 log 소비 |
| `FishingSpot` | props `fish_count > 0` | 낚시 시 감소, 시간 경과로 재생 |
| `WildBerryBush` | 인벤토리에 아이템 있음 | 채집 시 소비, 시간 경과로 재생 |
| `WildHerbPatch` | 인벤토리에 아이템 있음 | 채집 시 소비, 시간 경과로 재생 |

자원이 없는 오브젝트는 `activity_resolver`가 자동 스킵합니다.

### 도구 관리 API

```python
agent._has_tool("axe")       # 도끼 소지 확인
agent._pickup_tool("axe")    # 도구함에서 가져오기
agent._return_tool("axe")    # 도구함에 반납
```

도구 반납: `_memory["tool"]`에 기억된 원래 위치 → fallback으로 `resolve_storage_container(agent, "tool")` 동적 탐색

### 시간대별 조명

`_check_environment()`: NPC가 장소에 도착할 때 시간대를 확인하여 조명 자동 관리.

| 시간대 | 조건 | 행동 |
|--------|------|------|
| 밤 (18:00~06:00) | 조명 꺼져있음 | 켜기 |
| 낮 (06:00~18:00) | 조명 켜져있음 | 끄기 |

---

## 9. v0.2.2 DES (Discrete Event Simulation)

### 개요

시간 건너뛰기 시 NPC가 **자율적으로 행동**하도록 하는 시스템.
`advance_time_des()`는 step별로 NPC think()를 호출하여 자율 행동을 시뮬레이션.

> **이중 파이프라인**: DES 루프는 ECS Step과 별도 경로로 시간을 진행함.
> C#(시스템: 이동/Job/시간) + Python(컨텐츠: think/이벤트)가 분리되어 있어 실질적으로 단일 호출.
> C# 시스템 로직 변경 시 `AdvanceTimeDES()`도 동기화 필요.

### 시간 진행 API 비교

| API | think() | 이동 | 이벤트 | 용도 |
|-----|---------|------|--------|------|
| `advance_time_des(ms)` | **O** | **O** | **O** | **모든 시간 진행** |

### DES 루프 흐름

```
advance_time_des(총시간) {
    while 남은시간 > 0:
        step = min(남은시간, 가장 짧은 NPC Job duration)
        이동 시뮬레이션 (step만큼)
        move job 완료된 NPC → 텔레포트
        AdvanceJobs (duration 차감)
        GameTime 증가 (step만큼)
        survival 시간 경과 처리
        OnTimeElapsed 이벤트 발행 → FlushEvents
        think_all() → NPC 재결정
}
```

### move Job duration 자동 계산 (v0.2.2)

Python에서 move Job을 `duration=0`으로 삽입하면, C#이 자동으로 이동 시간을 계산:

| 조건 | 계산 방법 |
|------|----------|
| 같은 Location 내 | `CalculateTravelTime(fromX, toX, speedModifier)` — X좌표 기반 |
| 다른 Location 간 | `CalculatePathTravelTime()` — 경로 전체 X좌표 기반 |
| 경로 없음 | 에러 출력 + 0 반환 |

최소값 없음 — 이동 거리가 0이면 0ms를 반환한다.

```python
# Python에서는 duration=0으로 삽입 — C#이 자동 계산
morld.insert_job(unit_id, {
    "name": "이동", "action": "move",
    "region_id": 0, "location_id": 3,
    "target_x": 90, "duration": 0,  # ← C#이 자동 계산
})
```

### DES think() 규칙

1. **모든 think() 경로는 반드시 job을 삽입해야 함** (duration > 0)
2. Job 없으면 DES 루프가 무한 반복 (min duration = 0 → step = 0)
3. stay job: `"action": "stay"` (NOT `"idle"`)
4. move job: `"action": "move"`, duration=0 (C# 자동 계산)
5. `_insert_idle_job(name, ms)` 헬퍼로 대기 job 삽입
6. **고정 시간 행동**: `agent._do_instant_action("이름", "key")` — ACTION_DURATION 테이블 조회 + job 삽입 + action_taken 설정을 한 번에 처리. 테이블: `think/activities/helpers.py`
7. **캐릭터 오버라이드**: `_action_duration_overrides` dict로 NPC별 행동 시간 변경 가능
8. **Gate Transit** (v0.2.3): cross-location 이동 시 FSM 스택에 `GateTransitState`(lv=30) push → think() 차단 (기존 move job 보존). 도착 시 자동 pop → Life 로직 재개. 상세: [movement-system.md#2.6](movement-system.md#26-gate-transit-system-npc-숨김-이동--v023)

### C# 구현 위치

- `script_system.cs`: `EstimateMoveTravelTime()` — X좌표 기반 이동 시간 추정
- `script_system_data_api.cs`: `AdvanceTimeDES()` — DES 루프, move duration 자동 계산

---

## 10. 디버그 작업지시

디버그 모드에서 NPC에게 특정 활동을 직접 지시하여 테스트할 수 있습니다.

### 사용법

1. 설정에서 디버그 모드 ON (`can:debug_*`)
2. NPC 포커스 → "(디버그) 작업지시 [현재활동]" 클릭
3. 활동 목록에서 선택 → NPC가 즉시 해당 활동 시작
4. 해제 시 원래 스케줄 복원

### 구현

`assets/base.py`의 `debug_work_order()` 메서드:

```python
# 임시 스케줄 push (24시간 = 항상 매칭)
work_order = [{"name": f"DEBUG: {choice}", "activity": choice,
               "start": 0, "end": 86_400_000}]
agent.push_schedule(work_order)
```

- `push_schedule()` → `morld.clear_jobs()` → 다음 tick에서 `think()` 재호출
- `pop_schedule()` → 원래 스케줄 복원
- 활동 목록은 `ACTIVITY_HANDLERS.keys()`에서 동적으로 가져옴
- 포커스 메뉴에 현재 NPC 활동이 동적 표시 (`_apply_dynamic_action_labels`)

---

## 파일 위치

### C#
- `scripts/morld/schedule/Job.cs` - Job 구조
- `scripts/morld/schedule/JobList.cs` - JobList 큐
- `scripts/morld/schedule/DailySchedule.cs` - 스케줄 파싱
- `scripts/system/think_system.cs` - Agent.think() 호출
- `scripts/system/job_behavior_system.cs` - Job 실행
- `scripts/system/script_system.cs` - EstimateMoveTravelTime — X좌표 기반 이동 시간 추정 (v0.2.2)
- `scripts/system/script_system_data_api.cs` - AdvanceTimeDES, move duration 자동 계산 (v0.2.2)

### Python
- `think/__init__.py` - BaseAgent, FSM 스택 관리, Phase 시스템, 동적 스케줄, 도구 관리, wandering, flavor 클리어
- `think/idle_flavors.py` - Idle flavor 시스템 (상태 관리 + 3-tier 선택 + flavor 풀 데이터)
- `think/fsm.py` - Pass-Through 스택 FSM (LifeState, StandbyPhase, CommandPhase, GateTransitState, CombatState, FleeState, ResignationState, DesperateState, 레벨 기반 auto-pop)
- `think/party_config.py` - 파티 캐릭터 설정 (Disposition 2D, 모집 조건, 불복 판정, 리더 특성)
- `think/order_handlers.py` - 분대 지시 핸들러 Mixin (follow/이동/대기/경계/수색/수집, CommandPhase가 dispatch)
- `party.py` - 파티(분대) 시스템 (Squad/Order 데이터, 생명주기/멤버/리더/지시 API, follow 스케줄, gate 동기화, 귀환)
- `think/handlers/` - 인터럽트 핸들러 (식사/배변/체온/착의/자위/사회/선물)
- `think/movement_mixin.py` - 이동 + 활동 디스패치 + Tier 5 루틴, _insert_flavored_idle()
- `think/activities/` - 활동 핸들러 패키지 (10종: 소등/점등/벌목/낚시/채집/요리/청소/물자수집/정원/연료수집)
- `think/activities/helpers.py` - 핸들러 공용 헬퍼 (resolve_storage_container, store_npc_items, find_npc_food 등)
- `think/activity_resolver.py` - 활동별 동적 위치 탐색 (채집/사냥/순찰/벌목/낚시/독서/물자수집)
- `think/facility_resolver.py` - 시설 탐색 리졸버 (목욕/화장실 선착순 + 옷장 소유권 탐색) (v0.2.2)
- `think/resource_agent.py` - 자원 재생 시스템 (인벤토리 기반 + props 기반)
- `think/trap_agent.py` - 덫 시스템 (토끼 굴 체크)
- `survival.py` - NPC 만복도 추적 (register_npc, is_npc_hungry, npc_eat, 기절 시스템)
- `needs.py` - 욕구 수치화 (배변/피로/청결/사회/성욕), NPC 인터럽트 체크 (v0.2.2)
- `assets/characters/*.py` - 캐릭터별 SCHEDULE/SCHEDULES 정의
- `assets/base.py` - Object 컨테이너 헬퍼, 디버그 작업지시 (debug_work_order)
- `assets/objects/scavenge.py` - 비충전 수집 오브젝트 (도시 자원)
