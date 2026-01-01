# 유저 입력 시스템 계획

## 목표
플레이어가 행동을 선택할 수 있는 간단한 입력 시스템 구현

## 현재 상태
- `PlayerSystem.Look()` - 현재 상황 정보 조회 (위치, 캐릭터, 경로)
- `DescribeSystem.GetSituationText()` - 상황을 텍스트로 변환
- `GameEngine.UpdateSituationText()` - TextUI에 표시
- 마우스 클릭으로 시간 진행 (임시 테스트용) → **주석 처리 예정**

## 기술적 제약 및 결정 사항

### BBCode 링크 활용
- RichTextLabel에 BBCode 활성화됨
- BBCode `[url]` 태그로 하이퍼링크 생성 가능
- **제약:** 링크 클릭 시 직접 함수 호출 불가
- **해결:** `meta_clicked` 시그널 연결 → 시그널 핸들러에서 게임 시스템 호출

### BBCode 링크 포맷
```bbcode
[url=move:0:1]광장으로 이동 (5분)[/url]
[url=idle]멍때리기[/url]
[url=idle:15]멍때리기 (15분)[/url]
```

**meta 포맷 규칙:**
- 구분자: `:`
- 이동: `move:regionId:localId` (TravelTime은 미포함, 내부에서 조회)
- 멍때리기 메뉴: `idle` (시간 선택 UI로 전환)
- 멍때리기 실행: `idle:minutes`

### 시그널 처리 흐름
```
1. RichTextLabel에 BBCode 링크 표시
2. 유저가 링크 클릭
3. meta_clicked(meta) 시그널 발생
4. GameEngine._OnMetaClicked(meta) 핸들러 호출
5. meta 문자열 파싱 → 행동 타입 및 파라미터 추출
6. PlayerSystem 메서드 호출 (이동/멍때리기 등)
7. 시간 진행
8. 상황 설명 업데이트
```

## 플레이어 행동 처리 방식

### 핵심 원칙
- 플레이어도 NPC와 동일하게 **Character**로 관리됨
- 행동 선택 시 **Action Queue**에 추가됨
- PlanningSystem/MovementSystem이 동일하게 처리

### 이동 처리 흐름
```
1. 유저가 이동 링크 클릭
2. GameEngine이 meta 파싱
3. PlayerSystem.RequestMove(destination) 호출
4. PlayerSystem이 PathFinder로 경로 탐색 (인접/원거리 동일 방식)
5. 플레이어 Character의 Action Queue 초기화 후 이동 ActionLog 추가
6. RequestTimeAdvance(travelTime) 호출
7. MovementSystem이 이동 처리
8. 이동 완료 후 상황 설명 업데이트
```

**참고:** 인접 이동과 원거리 PathFinding 이동 모두 동일한 흐름으로 처리됨

## 선택 가능한 행동 (1차)

### 행동 분류: 시간 소모 여부

| 행동 | 시간 소모 | UI 표시 예시 |
|------|----------|-------------|
| 이동 | O | `마을 B (15분)` |
| 멍때리기 | O | `멍때리기 (1시간)` |
| 대화 | X | `철수와 대화` (향후) |
| 매매 | X | `상점 이용` (향후) |

**핵심:** 시간 소모 행동 선택 시 → 해당 시간만큼만 진행 → SE.World 다시 pending → 유저 조작 가능

### 1. 이동 (시간 소모)
- Look의 Routes 기반으로 선택지 생성 (인접 Edge만)
- **TravelTime 표시 필수**: `광장 (5분)`, `마을 입구 (10분)`
- 차단된 경로는 비활성화 표시 (링크 없음)
- 클릭 시 해당 시간만큼만 진행

### 2. 멍때리기 (시간 소모) - 2단계 선택
**1단계:** 기본 UI에 `멍때리기` 링크 표시
**2단계:** 클릭 시 시간 선택지 표시
```
멍때리기 (15분)
멍때리기 (30분)
멍때리기 (1시간)
멍때리기 (4시간)
[뒤로]
```
- 디버깅용으로도 유용 (시간 진행 테스트)

### 향후 확장 (시간 미소모)
- 캐릭터와 대화
- 아이템 사용/매매
- 환경에 따른 동적 액션
- **맵 보기 → PathFinding으로 원거리 이동** (시간 소모)

## 구현 계획

### Phase 1: 기본 구조
- [ ] GameEngine._Input() 마우스 클릭 부분 주석 처리
- [ ] RichTextLabel의 meta_clicked 시그널 연결
- [ ] _OnMetaClicked() 핸들러 구현 (meta 파싱 포함)

### Phase 2: ActionQueue 조작 API
- [ ] PlanningSystem에 ClearActionQueue(characterId) 추가
- [ ] PlanningSystem에 SetActionQueue(characterId, actions) 추가
- [ ] PlayerSystem에 RequestMove(destination) 추가
- [ ] PlayerSystem에 RequestIdle(minutes) 추가

### Phase 3: UI 연결
- [ ] DescribeSystem.GetSituationText()에 액션 링크 추가
- [ ] 이동 경로를 클릭 가능한 링크로 변환 `[url=move:regionId:localId]`
- [ ] 멍때리기 옵션 추가 `[url=idle:15]`, `[url=idle:60]` 등

## 결정된 사항
1. ~~멍때리기 시간 옵션~~ → 2단계 선택 (15분, 30분, 1시간, 4시간)
2. ~~meta 포맷~~ → `move:regionId:localId`, `idle`, `idle:minutes` (TravelTime 미포함)

## 미결정 사항
1. 이동 중 취소 가능? (1차에서는 미지원 예정)
2. 링크 스타일링 (기본 BBCode 스타일 사용)

## BBCode 상태 관리

### 개요
RichTextLabel의 BBCode는 `[url]` 태그로 링크를 생성할 수 있지만,
마우스 오버나 2단계 메뉴 등의 동적 UI 상태는 직접 Text를 조작해야 함.

### 구현 방식
RichTextLabel.Text를 직접 검색/치환하여 UI 상태 변경

### 예시

**1. 마우스 오버 효과:**
```
Before: [url=move:0:1]광장으로 이동 (5분)[/url]
After:  [url=move:0:1][color=red]광장으로 이동 (5분)[/color][/url]
```
- 마우스 진입 시: 패턴 검색 → color 태그 삽입
- 마우스 이탈 시: 패턴 검색 → color 태그 제거

**2. 멍때리기 2단계 메뉴:**
```
1단계 표시:
[url=idle]멍때리기[/url]

클릭 후 2단계로 전환:
[url=idle:15]멍때리기 (15분)[/url]
[url=idle:30]멍때리기 (30분)[/url]
[url=idle:60]멍때리기 (1시간)[/url]
[url=idle:240]멍때리기 (4시간)[/url]
[url=back]뒤로[/url]
```
- `idle` 클릭 시: 해당 라인을 검색하여 시간 선택지로 교체
- `back` 클릭 시: 시간 선택지를 검색하여 원래 `idle` 링크로 복원

### 구현 시 주의사항
- 패턴 검색 시 정규표현식 또는 문자열 검색 사용
- 전체 Text 교체 시 기존 다른 BBCode 유지 필요
- 상태 전환 시 현재 UI 모드 추적 필요 (enum: Normal, IdleSelect 등)

## 현재 Action 시스템 분석

### ActionLog 구조
```csharp
public class ActionLog
{
    public int StartTime { get; set; }      // 상대 시간 (Step 기준 0분~)
    public int EndTime { get; set; }
    public bool IsMoving { get; set; }      // true면 이동
    public LocationRef Location { get; set; }
    public LocationRef? Destination { get; set; }  // 이동 시 도착지
    public string? Activity { get; set; }   // 활동명 (null = Idle)
}
```

### PlanningSystem 동작
1. **매 Step마다** ActionQueue 초기화 후 재생성
2. **스케줄 기반** 자동 계획 - `character.Schedule.GetEntryAt(minuteOfDay)`
3. 경로 탐색 → ActionLog 리스트 생성
4. MovementSystem이 ActionQueue 소비

### 플레이어 행동 처리 방향

**동작 방식:**
1. PlanningSystem이 스케줄 기반으로 ActionQueue 생성 (플레이어 포함)
2. SE.World가 pending 상태 (Step 미실행)
3. 플레이어가 행동 선택 시:
   - 기존 ActionQueue **전체 삭제**
   - 새로운 Action으로 교체
4. Step 실행 → MovementSystem이 ActionQueue 처리

**핵심 포인트:**
- 플레이어 조작은 **Step 실행 전** (World pending 상태)에 이루어짐
- 기존 스케줄 기반 Action은 플레이어 입력 시 덮어씌워짐
- MovementSystem은 동일하게 ActionQueue를 소비
- **시간 소모 행동 완료 후** → SE.World가 다시 pending 상태로 → 유저 조작 대기

**시간 진행 흐름:**
```
1. SE.World pending 상태 (HasPendingTime = false)
2. 상황 설명 + 선택지 표시
3. 유저가 "마을 B (15분)" 클릭
4. RequestTimeAdvance(15) 호출 → HasPendingTime = true
5. _Process()에서 Step 실행 시작
6. 15분 경과 후 HasPendingTime = false
7. 1로 돌아감 (상황 설명 업데이트)
```

### 구현 방향
```
PlayerSystem 확장:
  - RequestMove(destination)
    → PathFinder로 경로 탐색
    → PlanningSystem.ClearActionQueue(playerId)
    → 경로의 각 Edge에 대해 ActionLog 생성 및 추가
    → 총 이동 시간 계산
    → RequestTimeAdvance(totalTravelTime)

  - RequestIdle(minutes)
    → PlanningSystem.ClearActionQueue(playerId)
    → PlanningSystem.AddAction(playerId, idleAction)
    → RequestTimeAdvance(minutes)

PlanningSystem 확장:
  - ClearActionQueue(characterId) - 기존 Queue 삭제
  - AddAction(characterId, action) - 새 Action 추가
  - SetActionQueue(characterId, actions) - 여러 Action 한번에 설정 (경로 이동용)
```

## 참고
- Godot RichTextLabel meta_clicked: `signal meta_clicked(meta: Variant)`
- `LookResult.Routes` 에 이동 가능한 경로 정보 있음
- `RequestTimeAdvance(minutes, actionName)` 으로 시간 진행 요청
- `PlayerSystem.PlayerId`로 플레이어 캐릭터 교체 가능
