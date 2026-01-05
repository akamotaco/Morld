# Plan: 탈것(Vehicle) 시스템

## 목표
캐릭터의 자세(Posture) 시스템과 다양한 탈것(Vehicle) 기능 추가

## 난이도 분석
1. **의자** (쉬움) - 정적 오브젝트, 앉으면 이동 불가
2. **자동차** (중간) - Location + 오브젝트들, 동적 Edge
3. **자전거** (어려움) - 앉은 상태에서 특수 이동, Location describe 유지

---

## 1. 자세(Posture) 시스템

### 개념
- 캐릭터 상태: `standing` (서기), `sitting` (앉기)
- 기본 상태: `standing`
- 이동 시 자동으로 `standing`으로 변경

### 구현 (Prop 기반)
**Prop 시스템을 활용한 양방향 참조**

캐릭터 측:
- `seated_on:{object_id}` → 좌석 이름 (예: `seated_on:230` → `"front"`)
- 값이 없으면 서있는 상태

오브젝트 측:
- `seated_by:{seat_name}` → 앉은 캐릭터 ID (예: `seated_by:front` → `0`)
- 값이 -1이면 빈 좌석

```
자전거 (ID: 230) - 초기 상태
├── seated_by:front  → -1  (빈 좌석, 운전석)
└── seated_by:rear   → -1  (빈 좌석)

[플레이어(0)가 앞좌석에 앉음]
├── seated_by:front  → 0   (플레이어)
└── seated_by:rear   → -1  (빈 좌석)

플레이어 (ID: 0)
└── seated_on:230    → "front"  (자전거 앞좌석에 앉음)
```

### 앉기 액션 처리
```csharp
// 1. 캐릭터가 이미 앉아있는지 확인
if (character.Props.HasType("seated_on")) return fail;

// 2. 좌석이 비어있는지 확인
int seatOccupant = object.Props.Get($"seated_by:{seatName}", -1);
if (seatOccupant != -1) return fail;

// 3. 양방향 설정
character.Props.Set($"seated_on:{objectId}", seatName);
object.Props.Set($"seated_by:{seatName}", characterId);
```

### 일어나기 액션 처리
```csharp
// 1. seated_on에서 오브젝트 ID와 좌석 이름 추출
var (objectId, seatName) = character.Props.GetSeatedInfo();

// 2. 양방향 해제
character.Props.Remove($"seated_on:{objectId}");
object.Props.Set($"seated_by:{seatName}", -1);
```

### 앉은 상태의 액션 표시
**앉으면 캐릭터에 액션이 추가됨** (오브젝트가 아닌 캐릭터)

describe text에서 자세와 함께 표시:
```
[앉음: 의자] - 일어나기
[앉음: 운전석] - 일어나기, 운전
[앉음: 자전거] - 일어나기, 운전
```

- 기본: "일어나기" 액션 항상 추가
- 운전석(`driver_seat: 1`): "운전" 액션 추가

---

## 2. 자동차형

### 핵심 개념
**자동차 = 하나의 Location**

```
자동차 Location (예: "내 자동차")
├── 운전석 (Object) - passive_props: {driver_seat: 1}, 앉으면 운전 가능
├── 조수석 (Object) - 앉기만 가능
├── 뒷좌석 (Object) - 앉기만 가능
└── 트렁크 (Object) - 인벤토리 보유, 아이템 보관
```

### 플레이어 흐름 (혼자 운전)
```
1. 이동 → 자동차 Location 진입 (탑승)
2. 운전석(Object)에 앉기 → SittingOn: 운전석 ID
3. 앉은 상태에서 이동 가능한 외부 지역 표시 (실내 제외)
4. 지역 선택 → 자동차와 함께 이동 (Edge 변경, 빠른 이동)
5. 일어나기 → SittingOn: null
6. 이동 → 외부 Location으로 하차
```

### 운전석 판별
- 오브젝트 Prop: `driver_seat: 1`
- 앉은 오브젝트가 이 Prop을 가지면 → 운전 가능 상태

### 자동차 이동 메커니즘
**핵심: 자동차 이동 = RegionEdge 변경 (Location 변경 아님)**

```
[이동 전]
Region 0: 주차장(29) ←RegionEdge→ Region 1: 자동차(0)

[운전 이동 후 - RegionEdge의 LocationA만 변경]
Region 0: 도시 입구(25) ←RegionEdge→ Region 1: 자동차(0)
```

- 자동차는 별도 Region (Region 1)에 속함
- 자동차 Location 자체는 변하지 않음
- **RegionEdge의 LocationA (외부 Region 쪽)**가 변경됨
- 탑승자들은 자동차 Location에 계속 머무름
- 이동 시간: RegionEdge travelTime 적용 (도보보다 빠름)

### 이동 제한
- 실내(indoor) Location으로는 자동차 이동 불가
- Edge 또는 Location에 `indoor: true` 속성으로 판별

### 탑승자 처리
- 자동차 Location에 있는 모든 캐릭터가 함께 이동
- 운전자만 이동 명령 가능

### 트렁크/좌석
- 기존 오브젝트 시스템 그대로 활용
- 트렁크: 인벤토리 보유, `take@container`, `put@inventory`
- 좌석: `seats: 1` Prop으로 좌석 수 제한 가능

---

## 3. 의자형 (정적 탈것)

### 개념
- 오브젝트 타입
- 오브젝트 클릭 → "앉기" 액션 → SittingOn 설정
- 앉은 상태에서 이동 불가
- Location의 describe 정보는 그대로 유지

### 핵심 규칙
1. **앉은 상태에서 이동 차단**
   - SittingOn이 설정된 상태에서 move 불가
   - "일어나기" 후에만 이동 가능

2. **Location 변경 시 자동 일어남**
   - 이벤트 등으로 Location이 강제 변경되면 → SittingOn = null
   - 버그 방지 (다른 장소의 의자에 앉아있는 상태 방지)

### 좌석 제한 (추후)
- 오브젝트 Prop: `seats: 2` (최대 좌석 수)
- 해당 오브젝트에 앉은 캐릭터 수를 카운트
- 만석이면 앉기 액션 비활성화

---

## 4. 탈것 분류: 밀폐형 vs 개방형

### 밀폐형 (Location 타입)
- **자동차**: 자체 Location, 외부 정보 차단
- 항상 "실내" 취급
- 연결된 외부 Location의 날씨/묘사 영향 없음

### 개방형 (Object 타입)
- **의자, 자전거**: 배치된 Location의 정보 유지
- 날씨, 묘사, 시간대 등 외부 환경 그대로 적용
- 같은 Location의 다른 캐릭터와 상호작용 가능

---

## 5. 자전거형 (이동 가능 탈것) - 검토 중

### 기본 구조
- 오브젝트 타입 (개방형)
- Location의 describe 정보 그대로 유지
- 같은 장소 캐릭터와 대화 가능

### 핵심 문제들

**1. 탑승자 동시 이동**
- 자전거 운전자 이동 시 → 뒷자석 탑승자도 함께 이동
- 오브젝트는 Edge가 없음 → 새로운 "동반 이동" 로직 필요?

**2. 이동 속도**
- 자전거는 도보보다 빠름
- Edge travelTime에 비율 적용? (예: 0.5배)
- "따라가기"로는 속도 차이 표현 불가

**3. 이동 제한**
- 실내 진입 불가 (자동차와 동일)
- "도로" 개념 필요한가? → 추후 검토

### 구현 방안
**자동차와 동일하게 "운전" 액션 사용**

1. 자전거 = 오브젝트 (운전석/뒷자석 구분 가능)
2. 운전석에 앉으면 → "운전" 액션 활성화
3. 운전 액션 실행 시:
   - 자전거 오브젝트 Location 변경
   - 탑승자들(SittingOn == 자전거) 강제 Location 변경
4. 이동 속도: travelTime 비율 감소 (예: 0.5배)

---

## 6. 구현 우선순위

### Phase 1: 자세 시스템 (Prop 기반) ✅
- [x] 앉기 액션 구현: `seated_on:{object_id}` + `seated_by:{seat_name}` 양방향 설정
- [x] 일어나기 액션 구현: 양방향 Prop 해제
- [x] `Props.GetByType("seated_on")` 활용 중복 앉기 방지
- [x] Python morld API: `sit_on(unit_id, object_id, seat_name)`, `stand_up(unit_id)`, `is_seated(unit_id)`

### Phase 2: 의자 ✅
- [x] 의자 오브젝트 정의 (seats Prop) - Python 데이터로 정의됨
- [x] 앉은 상태에서 이동 차단 (JobBehaviorSystem)
- [x] Location 변경 시 자동 일어남 (ClearSeatedState)

### Phase 3: 자동차 ✅
- [x] 자동차 Location 구조 정의 (Region 1)
- [x] 운전석 오브젝트 (`driver_seat` Prop)
- [x] 운전 상태에서 이동 가능 지역 표시 (GetDrivableDestinations)
- [x] 자동차 이동 시 RegionEdge 변경 로직 (ExecuteDrive)
- [x] Python morld API: `can_drive`, `get_drivable_destinations`, `drive_to`
- [ ] 탑승자 동시 이동 (Future: 자동차 내 모든 유닛 동시 처리)

### Phase 4: 자전거
- [ ] 추후 구체화

---

## 7. 이벤트 예측 시스템 (EventPredictionSystem)

### 문제 상황
현재 시스템은 **이동 후 이벤트 감지** 구조로, 시간 조정이 필요한 경우를 처리할 수 없음.

**예시: NPC 텔레파시**
```
플레이어: 4시간 수면 요청
NPC A: 2시간 후 텔레파시 대화 예정

현재 동작:
1. JobBehaviorSystem이 4시간 진행
2. EventSystem이 만남 감지 → 이미 4시간 지남
3. 텔레파시는 4시간 후에 발생 (의도: 2시간 후)

원하는 동작:
1. 2시간 후 텔레파시 이벤트 예측
2. 시간을 2시간으로 조정
3. 2시간만 진행 후 텔레파시 처리
```

### 현재 시스템 순서
```
ThinkSystem → JobBehaviorSystem → EventSystem
     ↓              ↓                  ↓
  JobList 채움   이동 실행 +        이벤트 감지
               GameTime 업데이트   (이동 완료 후)
```

**문제점:**
- JobBehaviorSystem에서 이동과 시간 업데이트가 **동시에** 발생
- EventSystem은 이동 **완료 후** 이벤트 감지
- 시간 조정 타이밍 없음

### 제안 시스템 순서
```
ThinkSystem → EventPredictionSystem → JobBehaviorSystem → EventSystem
     ↓              ↓                        ↓                ↓
  JobList 채움   1. 경로 충돌 예측        조정된 시간만큼    즉시 이벤트
               2. NPC 액션 예측         이동 실행         처리
               3. 최소 시간 계산
               4. NextStepDuration 조정
```

### EventPredictionSystem 역할

**1. 이동 경로 충돌 예측**
- 각 유닛의 이동 예정 경로 분석
- 같은 Edge 또는 같은 Location 도착 시점 계산
- 충돌 시 이벤트 등록 (OnMeet 예정)

**2. NPC 액션 예측 (JobList 기반)**
- NPC JobList에서 특정 시간 내 액션 확인
- 시간 중단 필요 액션 감지 (텔레파시, 습격 등)
- 이벤트 등록 (OnAction 예정)

**3. 최소 시간 계산**
- 등록된 이벤트 중 가장 빠른 시간 확인
- `PlayerSystem.NextStepDuration`을 해당 시간으로 조정

**4. 이벤트 유형**
| 유형 | 설명 | 시간 중단 |
|------|------|----------|
| OnMeet | 캐릭터 만남 예정 | 조건부 |
| OnReach | 위치 도착 예정 | No |
| OnAction | NPC 액션 예정 | Yes |
| OnCollision | 경로 충돌 예정 | Yes |

### 구현 방안

**Option A: 새 시스템 추가**
```csharp
// 새 시스템: EventPredictionSystem
public class EventPredictionSystem : LogicSystem {
    public void Proc(int step) {
        var pendingDuration = _playerSystem.NextStepDuration;
        var events = PredictEvents(pendingDuration);
        var earliestInterrupt = FindEarliestInterrupt(events);

        if (earliestInterrupt != null) {
            _playerSystem.AdjustDuration(earliestInterrupt.Time);
        }
    }
}
```

**Option B: JobBehaviorSystem 분리**
```
MovementPlanSystem (경로 계산만)
    ↓
EventPredictionSystem (충돌/이벤트 예측)
    ↓
MovementExecuteSystem (실제 이동)
```

### 관련 데이터 구조

```csharp
// 예측된 이벤트
public class PredictedEvent {
    public GameEventType Type;
    public int TriggerTime;     // GameTime 기준
    public int[] InvolvedUnits;
    public bool InterruptsTime; // 시간 중단 여부
}

// Unit에 이동 예정 정보 추가
public class Unit {
    // 기존 필드...
    public PlannedMovement? NextMovement; // 예정된 이동 (경로, 도착 시간)
}
```

### 설계 결정
- **시간 중단 이벤트 정의**: Python에서 지정 (dialog의 button_type처럼), C#에서 로직 구현
- **구현 우선순위**: Vehicle 시스템 완료 후 진행 (스케줄/JobList/Activity와 연계됨)

### 열린 질문 (Section 9 참조)
- 예측 범위, NPC 행동 예측 정확도 등

---

## 8. 차량 전용 Region

### 설계 결정
차량(자동차)은 별도의 Region으로 관리한다.

**이유:**
- RegionEdge를 활용하면 차량 이동 시 연결 위치만 변경하면 됨
- Region 간 연결은 별도의 Edge 데이터(RegionEdge)로 관리되므로 유연함

### 구조
```
Region 2 (황폐화된 도시)           Region 1 (차량)
┌─────────────────┐              ┌─────────────────┐
│  주차장(4)      │◄─ RegionEdge ─│  낡은 자동차(0) │
└─────────────────┘              └─────────────────┘

[운전 후 - RegionEdge의 LocationA만 변경]
Region 2 (황폐화된 도시)           Region 1 (차량)
┌─────────────────┐              ┌─────────────────┐
│  도시 입구(0)   │◄─ RegionEdge ─│  낡은 자동차(0) │
└─────────────────┘              └─────────────────┘
```

### 차량 Region 초기화
- Region ID: 1 (차량 전용)
- 각 차량은 해당 Region 내의 Location
- RegionEdge로 외부 Location과 연결

---

## 9. 열린 질문들

### 해결됨
1. ~~자동차 Location의 초기 Edge 설정 방법?~~ → 차량 전용 Region + RegionEdge로 해결
2. ~~탑승 인원 제한?~~ → Prop 기반 좌석 시스템으로 해결 (seated_by:-1로 좌석 정의)
3. ~~시간 중단 이벤트 정의 위치?~~ → Python에서 지정 (dialog의 button_type처럼), C#에서 로직 구현

### Vehicle 시스템 관련
4. 자동차 소유권/열쇠 시스템?
5. 연료/내구도 시스템 필요?

### Future Work (NPC 운전)
6. NPC도 자동차 운전 가능하게 할 것인가? (스케줄/JobList/Activity 연계)
7. MovementPlanSystem/MovementExecuteSystem 분리 시 다른 시스템에 미치는 영향?

### EventPredictionSystem 관련
8. 예측 범위는 얼마로 할 것인가? (요청된 시간 전체? 최대 N분?)
9. NPC 행동 예측의 정확도는? (확정적 vs 확률적)

---

## 10. 테스트 데이터 추가 (시나리오2)

### Region 구조 (파일별 분리)

| Region ID | 이름 | 파일 | 설명 |
|-----------|------|------|------|
| 0 | 숲속 저택 | `world/mansion.py` | 저택, 마당, 숲 |
| 1 | 차량 | `world/vehicle.py` | 차량 전용 Region |
| 2 | 황폐화된 도시 | `world/city.py` | 도시 지역 |

### Region 0: 숲속 저택 (mansion.py)

**Location:**
| ID | unique_id | 한글명 | is_indoor |
|----|-----------|--------|-----------|
| 0~14 | (저택 내부) | 현관, 거실, 주방, 식당, 욕실, 창고, 각 방 | true |
| 12~13 | (마당) | 앞마당, 뒷마당 | false |
| 20~24 | (야외/숲) | 숲 입구, 깊은 숲, 강가, 채집터, 사냥터 | false |

### Region 1: 차량 (vehicle.py)

| ID | unique_id | 한글명 | 내부 오브젝트 |
|----|-----------|--------|--------------|
| 0 | old_car | 낡은 자동차 | 운전석(231), 조수석(232), 트렁크(233) |

### Region 2: 황폐화된 도시 (city.py)

| ID | unique_id | 한글명 | is_indoor |
|----|-----------|--------|-----------|
| 0 | city_entrance | 도시 입구 | false |
| 1 | gas_station | 주유소 | false |
| 2 | convenience_store | 편의점 | true |
| 3 | pharmacy | 약국 | true |
| 4 | parking_lot | 주차장 | false |

### RegionEdge 연결 (__init__.py)

| Edge ID | Region A | Location A | Region B | Location B | Travel Time |
|---------|----------|------------|----------|------------|-------------|
| 0 | 0 (저택) | 20 (숲 입구) | 2 (도시) | 0 (도시 입구) | 30분 |
| 1 | 2 (도시) | 4 (주차장) | 1 (차량) | 0 (자동차) | 1분 |

### 오브젝트 배치

#### 실내 가구 (앉을 수 있는 오브젝트)
| 오브젝트 | 배치 위치 | props |
|---------|----------|-------|
| 의자 (DiningChair) | 식당 (R0:3) | seated_by:1~4=-1 (4개 좌석) |
| 소파 (LivingSofa) | 거실 (R0:1) | seated_by:left/center/right=-1 (3개 좌석) |

#### 자전거 (Object 타입)
| 오브젝트 | 배치 위치 | props |
|---------|----------|-------|
| 자전거 (Bicycle) | 뒷마당 (R0:13) | seated_by:front=-1, seated_by:rear=-1 |

### Unit ID 할당
```
플레이어: 0
NPC: 1~99
아이템: 100~199
오브젝트: 200~299
바닥: 1000 + location_id
```

새 오브젝트 ID:
- 의자 (DiningChair): 220
- 소파 (LivingSofa): 221
- 자전거 (Bicycle): 230
- 운전석 (CarDriverSeat): 231
- 조수석 (CarPassengerSeat): 232
- 트렁크 (CarTrunk): 233

### 파일 작업 (완료)
1. `world/mansion.py` - Region 0 (숲속 저택)
2. `world/vehicle.py` - Region 1 (차량 전용)
3. `world/city.py` - Region 2 (황폐화된 도시)
4. `world/__init__.py` - 통합 초기화 + RegionEdge
5. `assets/objects/furniture.py` - Chair, Sofa (seated_by props)
6. `assets/objects/vehicles.py` - Bicycle, CarSeat, Trunk (seated_by props)
7. `assets/locations/city.py` - 도시 Location 클래스들
8. `assets/locations/vehicles.py` - OldCar Location

