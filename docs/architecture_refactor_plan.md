# 아키텍처 리팩토링 계획: Queue 기반 시간 점프 시스템

## 배경 및 문제점

### 현재 구현의 문제점
1. **고정 시간 증가 (5분/15분)**: 세밀한 스케줄 (1분, 3분) 처리 시 오동작 가능
2. **불필요한 루프**: 밤에 모든 캐릭터 수면 중이어도 5분씩 반복 실행
3. **그래프 기반 추상화와 불일치**: 실시간 시뮬레이션이 아닌데 매 분 처리 불필요

### 목표
- 이벤트 드리븐 방식으로 전환
- 의미 있는 시점까지 시간 점프
- 향후 플레이어 조작 및 캐릭터 조우 이벤트 지원 가능한 구조

---

## 새로운 아키텍처

### System 실행 순서 변경

**현재:**
```
WorldSystem → CharacterSystem → PlanningSystem → MovementSystem
```

**변경 후:**
```
MovementSystem → PlanningSystem → PlayerSystem
```

**Data Systems (Proc 없음, 데이터 저장소):**
- WorldSystem: Terrain + GameTime 보관, JSON import/export
- CharacterSystem: Character 데이터 보관, JSON import/export

### 새로운 Step 사이클

```
Step N 시작
│
├─ MovementSystem
│   ├─ PlanningSystem에서 NextStepDuration 읽기
│   ├─ 각 캐릭터에 대해:
│   │   ├─ PlanningSystem.GetActionQueue(characterId) 가져오기
│   │   ├─ PlanningSystem.GetCurrentActionIndex(characterId)부터 순회
│   │   ├─ 시간 범위 내 Action 실행
│   │   ├─ PlanningSystem.SetCurrentActionIndex() 업데이트
│   │   └─ 이동 완료/중단 시 Character.CurrentLocation, CurrentEdge 업데이트
│   └─ WorldSystem.GameTime을 NextStepDuration만큼 증가
│
├─ PlanningSystem
│   ├─ _actionQueues.Clear(), _currentActionIndices.Clear() (매번 새로 생성)
│   ├─ 각 캐릭터에 대해:
│   │   ├─ CurrentEdge 확인 → 남은 이동을 첫 Action으로 추가 후 CurrentEdge = null
│   │   ├─ 스케줄 기반으로 1시간 분량 행동 Queue 생성
│   │   └─ _currentActionIndices[characterId] = 0
│   ├─ NextStepDuration 저장 (기본 1시간)
│   └─ (향후) 이벤트 조건 확인 → 충돌 시점까지로 NextStepDuration 조정
│
└─ PlayerSystem
    ├─ 플레이어 캐릭터 확인
    ├─ 플레이어 입력 대기 (시스템 정지)
    └─ 플레이어 선택에 따라 NextStepDuration 덮어쓰기

Step N+1 시작 → MovementSystem이 Queue 소비...
```

**첫 Step 동작:**
- MovementSystem: NextStepDuration = 0, Queue 비어있음 → 스킵, GameTime 변화 없음
- PlanningSystem: 1시간 분량 Queue 생성, NextStepDuration = 60 저장
- 두 번째 Step부터 정상 동작

---

## 데이터 구조 변경

### 1. 행동 로그 구조 (새로 추가)

```csharp
/// <summary>
/// 캐릭터의 단일 행동 기록 (Edge 단위로 분리)
/// </summary>
public class ActionLog
{
    /// <summary>
    /// 행동 시작 시간 (상대 분 - 현재 Step 시작 기준 0분부터)
    /// </summary>
    public int StartTime { get; set; }

    /// <summary>
    /// 행동 종료 시간 (상대 분)
    /// </summary>
    public int EndTime { get; set; }

    /// <summary>
    /// 이동 중 여부 (true면 이동 처리, Activity 값은 무시하고 보관만)
    /// </summary>
    public bool IsMoving { get; set; }

    /// <summary>
    /// 위치 (IsMoving=false면 현재 위치, IsMoving=true면 출발지)
    /// LocationRef는 readonly struct이므로 자동 값 복사
    /// </summary>
    public LocationRef Location { get; set; }

    /// <summary>
    /// 도착 위치 (IsMoving=true일 때만 유효, 단일 Edge의 도착지)
    /// LocationRef는 readonly struct이므로 자동 값 복사
    /// </summary>
    public LocationRef? Destination { get; set; }

    /// <summary>
    /// 활동명 (스케줄에서 그대로 복사, null이면 Idle)
    /// IsMoving=true일 때도 값 유지 (이동 목적 표시용)
    /// </summary>
    public string? Activity { get; set; }
}
```

**내부 처리 우선순위:**
1. `IsMoving == true` → 이동 처리 (Activity 값은 무시하되 보관)
2. `IsMoving == false` → Activity 확인 (null이면 Idle, 값 있으면 해당 활동)

**이동 경로 분리 예시:**
```
스케줄: "순찰" (광장 → 시장, 총 30분)

생성되는 ActionQueue:
1. { IsMoving: true, Location: 광장, Destination: 골목, Activity: "순찰" }  // 0~15분
2. { IsMoving: true, Location: 골목, Destination: 시장, Activity: "순찰" }  // 15~30분
3. { IsMoving: false, Location: 시장, Activity: "순찰" }                    // 30분~

→ 골목에서 다른 캐릭터와 조우 여부 탐색 가능
→ Activity는 스케줄에서 그대로 유지 (이동 중에도 "순찰" 표시)
```

### 2. Character 클래스 확장

```csharp
public class Character
{
    // 기존 필드...

    /// <summary>
    /// 이동 중 Edge 위에 있는 경우의 정보 (저장 대상)
    /// </summary>
    public EdgeProgress? CurrentEdge { get; set; }
}
```

**ActionQueue는 Character가 아닌 PlanningSystem에서 관리:**
- 게임 로드 시 Character만 로드하면 PlanningSystem이 동일한 Queue 재생성
- ActionQueue는 저장/로드 대상 아님 (런타임 데이터)

### 2-1. CurrentEdge JSON 저장 (CharacterJsonFormat.cs)

```csharp
internal class CharacterJsonData
{
    // 기존 필드...

    [JsonPropertyName("currentEdge")]
    public EdgeProgressJsonData? CurrentEdge { get; set; }
}

internal class EdgeProgressJsonData
{
    [JsonPropertyName("fromRegionId")]
    public int FromRegionId { get; set; }

    [JsonPropertyName("fromLocalId")]
    public int FromLocalId { get; set; }

    [JsonPropertyName("toRegionId")]
    public int ToRegionId { get; set; }

    [JsonPropertyName("toLocalId")]
    public int ToLocalId { get; set; }

    [JsonPropertyName("totalTime")]
    public int TotalTime { get; set; }

    [JsonPropertyName("elapsedTime")]
    public int ElapsedTime { get; set; }
}
```

**JSON 예시:**
```json
{
  "id": "npc_001",
  "name": "철수",
  "regionId": 0,
  "locationId": 0,
  "currentEdge": {
    "fromRegionId": 0,
    "fromLocalId": 0,
    "toRegionId": 0,
    "toLocalId": 1,
    "totalTime": 10,
    "elapsedTime": 5
  },
  "schedule": [ ... ]
}
```

**하위 호환성:**
- `currentEdge`가 없는 기존 JSON 파일도 정상 로드 (null로 처리)
- 이동 중이 아닌 캐릭터는 `currentEdge` 필드 생략

### 2-2. EdgeProgress 클래스 (ActionLog.cs에 포함)

```csharp
/// <summary>
/// Edge 위에서의 진행 상태 (이동 중단 시 현재 위치 정보 보존용)
/// </summary>
public class EdgeProgress
{
    /// <summary>
    /// 출발 Location (LocationRef는 readonly struct이므로 자동 값 복사)
    /// </summary>
    public LocationRef From { get; set; }

    /// <summary>
    /// 도착 Location (LocationRef는 readonly struct이므로 자동 값 복사)
    /// </summary>
    public LocationRef To { get; set; }

    /// <summary>
    /// 총 이동 시간 (분)
    /// </summary>
    public int TotalTime { get; set; }

    /// <summary>
    /// 경과 시간 (분)
    /// </summary>
    public int ElapsedTime { get; set; }

    /// <summary>
    /// 남은 시간 (분) - 다음 Planning에서 사용
    /// </summary>
    public int RemainingTime => TotalTime - ElapsedTime;

    /// <summary>
    /// 진행률 (0.0 ~ 1.0)
    /// </summary>
    public float Progress => TotalTime > 0 ? (float)ElapsedTime / TotalTime : 1.0f;
}
```

**EdgeProgress 사용 예시:**
```
Step N (10분 Edge 이동 중 5분에서 Step 종료):
  MovementSystem:
    - EdgeProgress = { From: 광장, To: 골목, TotalTime: 10, ElapsedTime: 5 }
    - CurrentLocation은 여전히 "광장" (도착 전이므로)

Step N+1:
  PlanningSystem:
    - CurrentEdge.RemainingTime = 5분 확인
    - 첫 Action: Moving 광장→골목 (0분~5분)
    - CurrentEdge = null (Action으로 변환 완료)

  MovementSystem:
    - 첫 Action 실행 → 5분 후 골목 도착
    - CurrentLocation = 골목
```

### 3. PlanningSystem 확장

```csharp
public class PlanningSystem : ECS.System
{
    /// <summary>
    /// 다음 Step에서 진행할 시간 (분)
    /// MovementSystem이 이 값을 읽어서 시간 진행
    /// </summary>
    public int NextStepDuration { get; private set; } = 60; // 기본 1시간

    /// <summary>
    /// 캐릭터별 행동 Queue (런타임만, 저장 안 함)
    /// </summary>
    private Dictionary<string, List<ActionLog>> _actionQueues = new();

    /// <summary>
    /// 캐릭터별 현재 Action 인덱스 (런타임만, 저장 안 함)
    /// </summary>
    private Dictionary<string, int> _currentActionIndices = new();

    // Queue 접근 메서드
    public List<ActionLog>? GetActionQueue(string characterId) =>
        _actionQueues.TryGetValue(characterId, out var queue) ? queue : null;

    public int GetCurrentActionIndex(string characterId) =>
        _currentActionIndices.TryGetValue(characterId, out var idx) ? idx : 0;

    public void SetCurrentActionIndex(string characterId, int index) =>
        _currentActionIndices[characterId] = index;
}
```

### 4. PlayerSystem (새로 추가)

```csharp
public class PlayerSystem : ECS.System
{
    /// <summary>
    /// 현재 플레이어가 조작 중인 캐릭터 ID
    /// </summary>
    public string? ActivePlayerId { get; set; }

    /// <summary>
    /// 플레이어 입력 대기 중 여부
    /// </summary>
    public bool WaitingForInput { get; private set; }

    /// <summary>
    /// 플레이어가 선택한 행동 시간 (분)
    /// </summary>
    public int PlayerSelectedDuration { get; set; }
}
```

---

## 구현 단계

### 1단계: 기본 구조 구축

1. **ActionLog 클래스 생성**
   - 파일: `scripts/morld/character/ActionLog.cs`

2. **Character 클래스 수정**
   - CurrentEdge 필드 추가 (ActionQueue, CurrentActionIndex는 PlanningSystem으로 이동)
   - 기존 Movement, MovementInfo 관련 코드 삭제
   - CharacterState enum 및 State 필드 삭제 (CurrentEdge로 상태 판단)
   - IsMoving, IsIdle 프로퍼티는 CurrentEdge 기반으로 변경:
     ```csharp
     public bool IsMoving => CurrentEdge != null;
     public bool IsIdle => CurrentEdge == null;
     ```

3. **CharacterJsonFormat.cs 수정**
   - EdgeProgressJsonData 클래스 추가
   - CharacterJsonData에 CurrentEdge 필드 추가

4. **CharacterSystem.cs 수정**
   - Import: CurrentEdge 로드 로직 추가
   - Export: CurrentEdge 저장 로직 추가

5. **PlanningSystem 수정**
   - NextStepDuration 필드 추가
   - _actionQueues, _currentActionIndices Dictionary 추가
   - 캐릭터별 ActionQueue 생성 로직 구현
   - Queue 접근 메서드 (GetActionQueue, GetCurrentActionIndex, SetCurrentActionIndex)
   - 시간 계산 로직 (현재는 고정 1시간)

6. **WorldSystem 수정**
   - Proc() 함수 삭제 (순수 데이터 저장소로 변경)
   - GameTime 업데이트는 MovementSystem에서 수행

7. **MovementSystem 수정**
   - PlanningSystem에서 NextStepDuration, ActionQueue, CurrentActionIndex 읽기
   - 시간 범위 내 Action 순회 및 실행
   - SetCurrentActionIndex()로 진행 상태 업데이트
   - 이동 완료/중단 처리 (CurrentLocation, CurrentEdge)
   - WorldSystem.GameTime 업데이트

8. **GameEngine.cs 수정**
   - System 등록 순서 변경

### 2단계: PlayerSystem 도입

1. **PlayerSystem 클래스 생성**
   - 파일: `scripts/system/player_system.cs`

2. **플레이어 입력 대기 로직**
   - WaitingForInput 상태 관리
   - Godot UI 연동 (또는 콘솔 입력)

3. **PlanningSystem과 연동**
   - PlayerSystem의 선택이 있으면 해당 시간 사용
   - 없으면 자동 계획된 시간 사용

### 3단계: 이벤트 시스템 기반 마련 (향후)

1. **이벤트 탐색 로직 (PlanningSystem 내부 또는 별도 EventSystem)**
   - ActionQueue 생성 후 이벤트 조건 확인
   - 관련 캐릭터들의 ActionQueue를 직접 비교 분석
   - 충돌 시점 계산 → NextStepDuration 조정

2. **이벤트 탐색 예시**
   ```
   이벤트 조건: "캐릭터 A와 B가 만남"

   PlanningSystem:
   1. 모든 캐릭터의 1시간 ActionQueue 생성
   2. A의 ActionQueue와 B의 ActionQueue 비교
   3. 같은 시간대에 같은 Edge/Location 발견 (예: 23분에 골목)
   4. 플레이어도 해당 위치에 있는지 확인
   5. 충돌 발견 → NextStepDuration = 23분으로 조정
   6. MovementSystem: 23분만 실행 후 이벤트 발생
   ```

---

## 잠재적 문제점 및 해결 방안

### 문제 1: 시간 동기화
**문제**: MovementSystem이 먼저 실행되는데, 첫 Step에서는 이전 Planning 결과가 없음

**해결**:
- 첫 Step에서 MovementSystem은 빈 Queue를 확인하고 스킵
- 또는 _Ready()에서 초기 Planning 1회 실행

### 문제 2: 플레이어 입력 대기 시 게임 루프
**문제**: PlayerSystem에서 입력 대기 시 _Process()가 계속 호출됨

**해결**:
- PlayerSystem.WaitingForInput이 true면 SE.World.Step() 스킵
- 또는 별도 게임 상태 머신 도입 (Running / WaitingInput)

### 문제 3: Queue와 기존 Movement 로직 충돌
**문제**: 기존 Character.Movement와 새로운 ActionQueue가 중복

**해결**:
- 1단계에서 Movement, MovementInfo, CharacterState 완전 삭제
- ActionQueue + CurrentEdge로 대체
- IsMoving/IsIdle은 CurrentEdge 기반 프로퍼티로 변경

### 문제 4: 긴 시간 점프 시 중간 이벤트 누락
**문제**: 1시간 점프 시 중간에 발생해야 할 이벤트(캐릭터 조우 등) 누락

**해결**:
- PlanningSystem에서 ActionQueue 생성 후 이벤트 조건 탐색
- 관련 캐릭터들의 ActionQueue를 직접 비교하여 충돌 시점 계산
- 충돌 발견 시 NextStepDuration을 해당 시점까지로 조정
- 이벤트 발생 시점에 시간 흐름 정지 → 이벤트 처리 → 재개

### 문제 5: 스케줄 경계 처리
**문제**: 1시간 점프 중 스케줄이 바뀌는 경우 (예: 11:30에 새 스케줄 시작)

**해결**:
- Planning 시 다음 스케줄 시작 시간 확인
- NextStepDuration = min(기본시간, 다음스케줄까지남은시간)
- 스케줄 경계에서 자동으로 짧은 Step 실행

### 문제 6: System 순서와 첫 Step 문제
**문제**: 문제 1과 동일 - MovementSystem → PlanningSystem 순서에서, 첫 Step 실행 시 PlanningSystem이 아직 실행되지 않아 Queue가 비어있음

**해결**: 문제 1에서 설명한 방안 B 채택 (첫 Step에서 MovementSystem은 빈 Queue 확인하고 스킵)

---

## 파일 변경 목록

### 새로 생성
- `scripts/morld/character/ActionLog.cs` - ActionLog, EdgeProgress 클래스 포함
- `scripts/system/player_system.cs`

### 수정
- `scripts/morld/character/Character.cs` - Movement/MovementInfo/CharacterState 삭제, CurrentEdge 추가
- `scripts/morld/character/CharacterJsonFormat.cs` - EdgeProgressJsonData 추가
- `scripts/system/character_system.cs` - CurrentEdge Import/Export 로직 추가
- `scripts/system/planning_system.cs` - NextStepDuration, ActionQueue, CurrentActionIndex 관리
- `scripts/system/world_system.cs` - Proc() 삭제 (순수 데이터 저장소)
- `scripts/system/movement_system.cs` - Queue 소비 방식으로 변경, GameTime 업데이트
- `scripts/GameEngine.cs` - System 등록 순서 변경
- `CLAUDE.md` - 아키텍처 문서 업데이트

---

## 검증 방법

### 1단계 완료 조건
- [ ] 1시간 단위로 시간이 점프됨
- [ ] PlanningSystem에서 캐릭터별 ActionQueue가 생성됨 (Edge 단위로 분리)
- [ ] MovementSystem이 PlanningSystem의 Queue를 읽어서 실행
- [ ] 기존 스케줄 기반 이동이 정상 동작

### 2단계 완료 조건
- [ ] PlayerSystem이 플레이어 캐릭터 감지
- [ ] 플레이어 입력 대기 시 게임 정지
- [ ] 플레이어 선택에 따라 시간 점프 (휴식 4시간, 이동 3분 등)

---

## 결정 사항

### 1. 이벤트 탐색 방식
- **ActionQueue 직접 분석**: CompletedActions 없이 ActionQueue만으로 이벤트 탐색
- PlanningSystem에서 Queue 생성 후 관련 캐릭터들의 ActionQueue 비교
- 충돌 시점 발견 시 NextStepDuration 조정
- 향후 LogSystem 도입 시 별도 관리 예정

### 2. 시간 처리 방식
```
예시 흐름:
1. PlanningSystem: 1시간 기준으로 모든 캐릭터 행동 Queue 생성
2. PlayerSystem: 플레이어가 15분 행동 선택
3. 실제 진행 시간: 1시간 → 15분으로 변경
4. ActionQueue는 수정하지 않음 (15분까지만 실행하면 됨)
5. MovementSystem: 15분 분량만 Queue에서 소비
6. NPC들의 남은 45분 Queue: 사용되지 않고 유지
7. 다음 Step: PlanningSystem이 새로운 1시간 Queue 생성 (기존 Queue 전체 대체)
```

**Queue 재활용 안 함**: 남은 Queue를 이어서 사용하지 않고, 매 PlanningSystem에서 현재 상태 기준으로 새로 계획

### 3. PlayerSystem UI
- Godot UI로 구현 예정
- **현재 단계에서는 미구현** (아키텍처 우선)
- UI 없이 자동 진행 모드로 동작

### 4. 다중 플레이어
- PlayerSystem은 Character ID 기반으로 처리
- 구조적으로는 다중 플레이어 지원 가능
- **현재 구현에서는 단일 플레이어만 고려**
