# Action Priority System 설계

## 목표
캐릭터의 행동을 여러 계층의 시스템이 **override 방식**으로 결정하는 구조 설계

## 현재 문제점

### 동작하지 않는 이유
```
현재 흐름:
1. 유저가 이동 링크 클릭
2. PlayerSystem.RequestCommand() 호출
3. ExecuteMove()에서 ActionQueue 설정 + RequestTimeAdvance()
4. _Process()에서 Step 실행 시작
5. MovementSystem.Proc() - ActionQueue 소비 (여기까지 OK)
6. PlanningSystem.Proc() - ActionQueue 전체 초기화 후 재생성 ← 문제!
7. 다음 Step에서 MovementSystem은 PlanningSystem이 만든 Queue를 소비
```

**핵심 문제:** PlayerSystem이 ActionQueue를 설정하는 시점이 Step 실행 **이전**이라서,
PlanningSystem.Proc()에서 덮어씌워짐

## 제안하는 아키텍처

### 우선순위 계층 (낮음 → 높음)
```
1. SchedulingSystem (기존 PlanningSystem)
   - 스케줄 기반 기본 ActionQueue 생성
   - 모든 캐릭터에 대해 동작

2. ReactionSystem (향후 구현)
   - FSM 상태 기반 override
   - 상태: 호위, 순찰, 경계, 따라가기 등
   - 스케줄보다 우선

3. PlayerSystem (최고 우선순위)
   - 플레이어 입력 기반 override
   - 다른 모든 시스템보다 우선
```

### 실행 순서
```
MovementSystem → PlanningSystem → ReactionSystem → PlayerSystem
     ↓                ↓                 ↓              ↓
  Queue 소비      기본 Queue 생성    상태 기반 override   플레이어 override
```

### Override 메커니즘

**핵심 원칙:**
- 모든 시스템은 매 Step마다 ActionQueue를 덮어쓸 수 있음
- 나중에 실행되는 시스템이 우선순위가 높음
- 특별한 "스킵 플래그" 없이, 단순히 덮어쓰기

**구현 방식:**
```csharp
// PlanningSystem.Proc()
foreach (var character in characters)
{
    BuildActionQueue(character);  // 모든 캐릭터에 대해 생성
}

// ReactionSystem.Proc() (향후)
foreach (var character in charactersWithReactionState)
{
    if (character.ReactionState != None)
    {
        OverrideActionQueue(character);  // 반응 상태가 있으면 override
    }
}

// PlayerSystem.Proc()
if (_pendingCommand != null)
{
    ExecutePendingCommand();  // 대기 중인 명령이 있으면 override
    _pendingCommand = null;
}
```

## 수정이 필요한 부분

### PlayerSystem 변경사항

**현재:**
```csharp
public void RequestCommand(string cmd)
{
    // 즉시 ExecuteMove/ExecuteIdle 호출
    ExecuteMove(destination);  // ActionQueue 즉시 설정
}
```

**변경 후:**
```csharp
private string? _pendingCommand = null;

public void RequestCommand(string cmd)
{
    _pendingCommand = cmd;  // 저장만 하고 실행 안 함
}

protected override void Proc(int step, ...)
{
    // PlanningSystem 이후에 실행됨
    if (_pendingCommand != null)
    {
        ExecuteCommand(_pendingCommand);
        _pendingCommand = null;
    }

    // 기존 시간 진행 로직...
}
```

### 장점
1. PlanningSystem 코드 수정 불필요
2. 동일한 패턴으로 ReactionSystem 추가 가능
3. 실행 순서만으로 우선순위 결정 (명시적, 단순)

## 저장/불러오기 고려사항

### 저장이 필요한 데이터
| 데이터 | 저장 여부 | 이유 |
|--------|----------|------|
| Character.CurrentLocation | O | 위치 복원 필수 |
| Character.Schedule | O | 스케줄 데이터 |
| Character.ReactionState | O | FSM 상태 (향후) |
| PlayerSystem._pendingCommand | △ | 진행 중인 명령 (선택적) |
| ActionQueue | X | 매 Step마다 재생성됨 |
| PathFinding 결과 | X | 동일 입력 → 동일 결과 |

### 재현 가능성
```
로드 시:
1. Character 위치/스케줄/상태 복원
2. 첫 Step에서:
   - PlanningSystem이 스케줄 기반 ActionQueue 생성
   - ReactionSystem이 상태 기반 override
   - PlayerSystem이 저장된 명령 실행 (있는 경우)
3. MovementSystem이 ActionQueue 소비
→ 저장 직전과 동일한 동작 재현
```

## 구현 순서

### Phase 1: PlayerSystem 수정 (현재 버그 수정)
- [ ] `_pendingCommand` 필드 추가
- [ ] `RequestCommand()`에서 저장만 하도록 변경
- [ ] `Proc()`에서 대기 명령 실행

### Phase 2: 테스트 및 검증
- [ ] 이동 링크 클릭 → 이동 동작 확인
- [ ] 휴식 링크 클릭 → 휴식 동작 확인
- [ ] NPC 스케줄 기반 이동 정상 동작 확인

### Phase 3: ReactionSystem 기반 구조 (향후)
- [ ] ReactionState enum 정의
- [ ] Character에 ReactionState 필드 추가
- [ ] ReactionSystem 구현

## 미결정 사항

1. **진행 중 명령 취소**
   - 이동 중 다른 행동 선택 시 즉시 취소?
   - 현재 Edge 완료 후 취소?

2. **ReactionState 우선순위**
   - 여러 상태가 동시에 활성화될 수 있는가?
   - 상태 간 우선순위는?

3. **저장 시점의 _pendingCommand**
   - 저장할 것인가? (이동 중 저장 시)
   - 저장하지 않고 다시 입력받을 것인가?

## 참고

### 현재 시스템 등록 순서 (GameEngine.cs:37-41)
```csharp
this._world.AddSystem(new MovementSystem(), "movementSystem");
this._world.AddSystem(new PlanningSystem(), "planningSystem");
_playerSystem = this._world.AddSystem(new PlayerSystem(), "playerSystem");
_describeSystem = this._world.AddSystem(new DescribeSystem(), "describeSystem");
```

→ 실행 순서: Movement → Planning → Player → Describe
→ PlayerSystem이 Planning 이후 실행되므로 override 가능
