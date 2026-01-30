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
        "x": 90,                # (Pi-World) 목표 X 좌표 (optional, 기본값 0)
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

**참고:**
- `x` 필드는 선택적 (optional)이며 기본값은 0
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
| `move` | 목표 위치로 이동 | RegionId, LocationId |
| `stay` | 현재 위치에서 대기 | Duration |
| `follow` | 대상 유닛 따라가기 | TargetId, Duration |
| `flee` | 대상 유닛으로부터 도망 | TargetId, Duration |

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

# NPC Job 즉시 설정 (Override)
morld.set_npc_job(unit_id, "follow", duration=1_800_000)  # 30분

# 시간 경과 포함 Job 설정
morld.set_npc_time_consume(unit_id, "stay", duration=1_800_000)  # 30분
```

---

## 5. NPC별 스케줄 예시

### 세라 (사냥꾼)
```
05:00 기상      → 자기 방
06:00 아침순찰  → 앞마당
07:00 아침식사  → 식당
09:00 사냥      → 사냥터
12:00 점심식사  → 식당
14:00 사냥      → 사냥터
17:00 저녁순찰  → 숲 입구
18:30 저녁식사  → 식당
20:00 장비정비  → 자기 방
21:30 수면      → 자기 방
```

### 리나 (채집 담당)
```
06:00 기상      → 자기 방
07:00 아침식사  → 식당
08:00 빨래      → 뒷마당
09:00 채집      → 채집터
12:00 점심식사  → 식당
14:00 채집      → 채집터
17:00 빨래걷기  → 뒷마당
18:30 저녁식사  → 식당
19:30 자유시간  → 거실
22:00 수면      → 자기 방
```

### 밀라 (요리 담당)
```
05:00 기상      → 자기 방
06:00 아침준비  → 주방
07:00 아침식사  → 식당
08:00 설거지    → 주방
09:00 청소      → 거실
11:00 점심준비  → 주방
12:00 점심식사  → 식당
13:00 욕실청소  → 욕실
14:00 휴식      → 거실
17:00 저녁준비  → 주방
...
```

---

## 6. 현재 한계점

### 문제점
| 항목 | 현재 상태 | 문제 |
|------|----------|------|
| 위치 결정 | 하드코딩된 location_id | 유연성 없음 |
| activity 효과 | 없음 (이동만) | 채집해도 아이템 획득 안됨 |
| 자원 관리 | 없음 | NPC가 배고파도 먹지 않음 |
| 도구 사용 | 없음 | 낚시대 없이도 낚시 가능 |
| 목적지 정보 | Python에 미노출 | "~하러 가는 중" 표현 불가 |

### 빠른 개선 (단기)
1. **목적지 정보 노출**
   - `get_unit_info()`에 `dest_region_id`, `dest_location_id` 추가
   - NPC가 "채집하러 가는 중" vs "채집 중" 구분 가능

---

## 7. 진보된 스케줄 시스템 (계획)

### Phase 1: Context 기반 Activity 중심 Location 탐색

**현재:**
```python
SCHEDULE = [
    {"activity": "채집", "location_id": 23, ...}  # 위치 하드코딩
]
```

**개선 후:**
```python
SCHEDULE = [
    {"activity": "채집", ...}  # 위치 없음
]

# think()에서 동적 결정
def think(self):
    activity = self.get_current_activity()

    if activity == "채집":
        # 지형 정보에서 채집 가능한 위치 탐색
        location = self.find_location_for_activity("채집")
        # 산딸기 덤불, 약초밭 등 중 선택

    elif activity == "수면":
        # 본인 소유 방 탐색
        location = self.find_owned_room()
        if not location:
            location = self.find_shelter()  # 노숙 장소
```

**구현 요소:**
- `Location.activities = ["채집", "낚시"]` - 장소별 가능한 활동
- `Location.owner = "sera"` - 장소 소유자
- `find_location_for_activity(activity)` - 활동에 맞는 장소 검색

---

### Phase 2: 영향력 있는 Activity

**현재:** 이동만 하고 실제 효과 없음

**개선 후:**
```python
# Activity 완료 시 효과 발생
class LinaAgent(BaseAgent):
    def on_activity_complete(self, activity, location):
        if activity == "채집":
            # 채집 결과물 인벤토리에 추가
            items = self.roll_gathering_result(location)
            for item in items:
                morld.give_item(self.unit_id, item)

            # 보관함으로 이동하여 put
            storage = self.find_nearest_storage()
            self.set_next_job("보관", storage, duration=10)

        elif activity == "요리":
            # 재료 소비, 요리 생성
            morld.lost_item(self.unit_id, "food_fish")
            morld.give_item(self.unit_id, "food_cooked_fish")
```

**구현 요소:**
- `on_activity_complete(activity, location)` 콜백
- 활동별 결과물 테이블
- 보관함 위치 탐색 및 자동 이동

---

### Phase 3: 상호작용하는 Agent

**현재:** 스케줄대로만 움직임

**개선 후:**
```python
class SeraAgent(BaseAgent):
    def think(self):
        # 1. 생존 체크 - 스케줄보다 우선
        satiety = self.get_satiety()
        if satiety < 30:
            food_location = self.find_food_source()
            return self.set_urgent_job("식사", food_location)

        # 2. 준비 체크 - 아침에 옷 갈아입기
        if self.is_morning() and not self.is_dressed():
            wardrobe = self.find_own_wardrobe()
            return self.set_job("옷 갈아입기", wardrobe)

        # 3. 도구 체크 - 사냥 전 무기 챙기기
        if self.next_activity() == "사냥":
            if not self.has_equipped("weapon"):
                storage = self.find_weapon_storage()
                return self.set_job("무장", storage)

        # 4. 기본 스케줄 실행
        return self.fill_schedule_jobs()
```

**구현 요소:**
- NPC용 생존 시스템 (포만감, 체력)
- `has_item()`, `has_equipped()` 체크
- 우선순위: 생존 > 준비 > 스케줄
- 도구/의류 자동 장착

---

### 구현 우선순위

| 단계 | 내용 | 난이도 | 효과 |
|------|------|--------|------|
| 0 | 목적지 정보 노출 | 낮음 | 대화 개선 |
| 1a | Location.activities 추가 | 중간 | 유연한 위치 결정 |
| 1b | find_location_for_activity() | 중간 | 동적 탐색 |
| 2a | on_activity_complete 콜백 | 중간 | 활동 효과 |
| 2b | 보관함 자동 이동 | 중간 | 자원 순환 |
| 3a | NPC 생존 시스템 | 높음 | 자율 행동 |
| 3b | 도구/의류 자동 관리 | 높음 | 완전 자율 |

---

### 예상 결과

**리나의 하루 (Phase 3 완료 후):**
```
06:00 기상 - 자기 방에서 일어남
06:05 옷 갈아입기 - 옷장에서 작업복 착용
06:15 아침식사 - 식당으로 이동, 음식 섭취 (포만감 +40)
07:00 채집 준비 - 창고에서 바구니 챙김
07:10 채집 - 채집터로 이동 (지형 검색으로 결정)
      ↳ 산딸기 3개, 버섯 2개 획득
11:00 보관 - 주방 보관함에 채집물 넣기
11:30 점심 - 배고픔 체크 → 식당 이동
...
```

---

## 파일 위치

### C#
- `scripts/morld/schedule/Job.cs` - Job 구조
- `scripts/morld/schedule/JobList.cs` - JobList 큐
- `scripts/morld/schedule/DailySchedule.cs` - 스케줄 파싱
- `scripts/system/think_system.cs` - Agent.think() 호출
- `scripts/system/job_behavior_system.cs` - Job 실행

### Python
- `think/__init__.py` - BaseAgent, think_all()
- `assets/characters/*.py` - 캐릭터별 SCHEDULE 정의
