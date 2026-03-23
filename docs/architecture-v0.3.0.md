# Morld v0.3.0 아키텍처 설계

## 목표

하나의 게임 시스템으로 여러 게임 타입을 지원한다.

| 타입 | 시나리오 | 설명 |
|------|---------|------|
| 텍스트 기반 | 02, 03 | 기존. TextUI 기반 인터랙티브 픽션 |
| 2D 플랫포머 | 04 (예정) | 메트로바니아 스타일. Godot 2D 렌더링 |

---

## 핵심 원칙

### 1. 기존 동작 보장
시나리오 02/03은 **그대로 동작**해야 한다.
Region / Gate / Location 구조, NPC think/job 시스템, DES 시간 모델 — 모두 유지.

### 2. C# 시스템 + Python 콘텐츠
- **C#**: 게임 시스템, 아키텍처, 물리, 충돌, ECS
- **Python**: 시나리오 콘텐츠, NPC AI, 이벤트, 대화

### 3. 자유도 높은 시스템 + 시나리오별 제약
불필요한 기능을 제거하는 게 아니라, 풀 기능 시스템 위에 시나리오가 제약을 건다.

```
C# Core: 2D 공간 + 충돌 + 물리 (전부 존재)
  ↓
시나리오 config:
  scenario02: { use_y_axis: false, collision: "abstract", physics: false }
  scenario03: { use_y_axis: false, collision: "abstract", physics: false }
  scenario04: { use_y_axis: true,  collision: "full",     physics: true  }
```

---

## 구조 레이어

```
┌─────────────────────────────────────────────────┐
│  Python 콘텐츠 레이어                             │
│  시나리오 02/03 (텍스트)  │  시나리오 04 (플랫포머)   │
├─────────────────────────────────────────────────┤
│  C# 게임 시스템 레이어                             │
│  Region/Location/Gate + 2D 공간 + 충돌 + ECS     │
├─────────────────────────────────────────────────┤
│  UI 레이어                                       │
│  TextUI (BBCode)          │  Godot 2D Renderer   │
└─────────────────────────────────────────────────┘
```

---

## 주요 변경점

### 1. Y축 도입

Location 내부에 2D 공간 (X + Y)을 지원한다.

| | 시나리오 02/03 | 시나리오 04 |
|---|---|---|
| 공간 | X축만 (Y=0 고정) | X + Y축 |
| 이동 | X축 텔레포트 | 실시간 2D 이동 |
| NPC 행동 | 기존 think/job 그대로 | Y축 고려한 새 행동 |

시나리오 02/03은 처음부터 시나리오 04를 고려하여 설계되었다.
Location 이동(X축) + Gate 이동은 **동일한 방식**으로 동작한다.

### 2. 충돌 처리

C# ECS 기반 충돌 시스템. 모든 시나리오에 공통 존재하나, 활용도가 다르다.

| | 시나리오 02/03 | 시나리오 04 |
|---|---|---|
| 충돌 시스템 | 존재하나 X축만 활용 | 2D 풀 활용 |
| 물리 | 없음 (텔레포트) | 중력/점프/낙하 |

### 3. 시간 모델

| 모드 | 시나리오 | 설명 |
|------|---------|------|
| 매크로턴 (DES) | 02, 03 | think → job → advance_time |
| 마이크로턴 (실시간) | 04 | 프레임 단위 갱신 |

시나리오가 시간 모드를 선택한다.

### 4. UI 분기

| UI | 시나리오 | 설명 |
|----|---------|------|
| TextUI | 02, 03 | BBCode 기반 InteractiveTextUI |
| Godot 2D | 04 | 스프라이트/타일맵 기반 렌더링 |

Focus / Header / Footer 같은 TextUI 전용 개념은 시나리오 04에서는 다른 형태로 대체된다.

---

## 불변 요소 (v0.2.x → v0.3.0)

변경하지 않는 것들:

- **Region / Gate / Location** — 공간 구조의 기본 단위
- **C# + Python 분리** — 시스템 vs 콘텐츠
- **ECS 아키텍처** — 커스텀 ECS 기반
- **시나리오 02/03 NPC 로직** — think/job/handler 전부 유지
- **Prop 시스템** — unit prop 기반 상태 관리
- **DES 시간 모델** — 시나리오 02/03에서는 기존 방식 유지

---

## 현재 시스템 분석 (v0.2.x)

### ECS 실행 파이프라인

등록 순서 = 실행 순서. 매 Step마다 순차 호출:

```
ThinkSystem (Python AI: think_all())
  → EventPredictionSystem (시간 조정)
  → EventSystem (만남/도착 감지)
  → JobBehaviorSystem (이동 실행 + 시간 소비)
  → PlayerSystem (플레이어 입력)
  → WeatherSystem (매시간 전이)
  → TextUISystem (렌더링)
```

### 위치 모델 (현재)

```
Unit
  ├─ CurrentLocation: LocationRef (regionId, localId) — 이산 그래프 위치
  ├─ PositionX: float — Location 내 연속 1D 위치
  └─ CurrentMovement: MovementProgress? — 이동 보간 상태
       ├─ StartX, TargetX, Speed
       ├─ TotalDistance, TraveledDistance
       └─ TargetGateId — Gate 도달 시 Location 전환
```

### Python ↔ C# 연계

```
Python → C#: morld.* API (PyBuiltinFunction → C# 시스템 직접 접근)
C# → Python: CallModuleFunction(module, func) — SharpPy ImportModule + GetAttribute + Call
ThinkSystem: Execute("import think; think.think_all()")
```

### 새 시스템 추가 패턴

1. `ECS.System` 상속, `Proc(int step, Span<Component[]> allComponents)` 오버라이드
2. `GameEngine.RegisterAllSystems()`에 등록 (순서 = 실행 순서)
3. `_hub.GetSystem("name")`으로 다른 시스템 접근 (Component 필터 미사용)

---

## 구현 계획: 2D 위치 시스템

### Phase 1: Vector2 기반 통일 (Z축 없음, 영구)

모든 위치를 `Vec2(X, Y)`로 표현한다. Z축은 추가하지 않는다.

```csharp
// 공통 using alias — 나중에 Mysix.Vector2 등으로 교체 용이
using Vec2 = Godot.Vector2;
```

각 파일 상단에 `using Vec2 = Godot.Vector2;`를 선언하여,
향후 자체 수학 라이브러리로 교체 시 이 한 줄만 변경하면 된다.

#### Unit 변경

```csharp
// 현재 (1D)
public float PositionX { get; set; }

// 변경 (2D)
public Vec2 Position { get; set; }  // (X, Y)
// 시나리오 02/03: Position.Y == 0 항상
// 시나리오 04: Position.Y 자유
```

**하위 호환**: `PositionX` 프로퍼티를 `Position.X` 래퍼로 유지하면
기존 C# 코드 변경 최소화.

```csharp
public float PositionX
{
    get => Position.X;
    set => Position = new Vec2(value, Position.Y);
}
```

#### MovementProgress 변경

```csharp
// 현재 (1D)
public float StartX, TargetX;
public float CurrentX => ...;

// 변경 (2D)
public Vec2 Start, Target;
public Vec2 Current => ...;  // 보간
public float TotalDistance => Start.DistanceTo(Target);

// 하위 호환
public float StartX => Start.X;
public float TargetX => Target.X;
public float CurrentX => Current.X;
```

#### Gate 변경

```csharp
// 현재
public float X { get; }           // 이 Location 내 X 위치
public float ArrivalX { get; }    // 연결된 Location의 도착 X

// 변경
public Vec2 Position { get; }        // (X, Y)
public Vec2 ArrivalPosition { get; } // 연결된 Location의 도착 (X, Y)

// 하위 호환
public float X => Position.X;
public float ArrivalX => ArrivalPosition.X;
```

#### Location 변경

```csharp
// 현재
public int Length { get; }        // X축 길이
public string Geometry { get; }   // "line" | "ring"

// 추가
public int Height { get; }       // Y축 높이 (시나리오 02/03: 0)
```

### Phase 2: 충돌 시스템 (CollisionSystem)

새 ECS.System. `Proc()`에서 매 Step마다 충돌 판정.

```csharp
public class CollisionSystem : ECS.System
{
    protected override void Proc(int step, Span<Component[]> allComponents)
    {
        // 시나리오 config에 따라:
        // - abstract: X축 거리 기반 (기존 EventSystem의 만남 판정 확장)
        // - full: AABB 2D 충돌
    }
}
```

**실행 위치**: EventSystem 앞 (충돌 결과를 이벤트가 활용)

```
ThinkSystem → EventPredictionSystem → CollisionSystem → EventSystem → ...
```

### Ring Geometry Edge 처리

Ring(원통형) Location에서는 X축이 wrap-around한다 (0 = 360).
오딘 스피어와 같은 구조: 직진하면 한 바퀴 돌아 제자리.

```
Ring 세계:   [----A----B--------]
              0                360

플레이어(350)의 뷰포트가 edge를 넘을 때:
렌더링:  ...B--------A--[@]--A'--------B'...
                             ↑ 가상 복제(ghost)
```

#### 렌더링 (시나리오 04)
- 카메라 뷰포트가 edge(0 or 360)를 넘으면, 반대쪽 오브젝트를 **ghost로 복제** 표시
- ghost는 렌더링 전용 — 실제 Entity가 아님
- 뷰포트 폭 이내의 오브젝트만 ghost 생성 (성능)

#### 충돌
- Ring Location 내 거리 계산은 **wrap-around 최단 거리** 사용
  - 기존 `Location.CalculateDistance()`가 이미 처리
- edge 근처(예: X=355) 유닛의 충돌 판정 시, X=5 유닛과의 거리 = 10 (360-355+5)
- AABB 충돌도 wrap-around 고려: 박스가 edge를 걸치면 **양쪽에서 판정**

```
충돌 판정 (Ring):
  A.X=355, A.width=20 → 실제 범위: [345, 360) + [0, 15)
  B.X=5 → A와 B 충돌!
```

#### 물리
- 투사체/이동이 X > 360이면 `X %= 360` (기존 `NormalizeX()`)
- 중력(Y축)은 Ring과 무관 — Y는 항상 Line 방식

#### 시나리오별 차이

| | 시나리오 02/03 (텍스트) | 시나리오 04 (플랫포머) |
|---|---|---|
| Ring 거리 | `CalculateDistance()` (기존) | 동일 |
| Ring 렌더링 | 불필요 (텍스트) | ghost 복제 필요 |
| Ring 충돌 | X축 거리만 (abstract) | AABB wrap-around |
| Ring 물리 | 없음 | `NormalizeX()` wrap |

### Phase 3: 물리 시스템 (PhysicsSystem)

시나리오 04 전용. 캐주얼 플랫포머 물리 (마리오/오딘 스피어 스타일).

#### 속도 모델

| 항목 | 방식 |
|------|------|
| X 이동 | 즉시 최대 속도 (or 약간의 가감속) |
| Y 중력 | 고정 가속도 + 최대 낙하 속도 캡 |
| 점프 | 초기 Y속도, 버튼 홀드로 높이 조절 (가변 점프) |
| 착지 | 발 위치가 Platform Line 위 → Y속도 0 |

#### 물리 상수 (튜닝 가능)

```csharp
// 간단한 중력 가속도 — 리얼하지 않지만 자연스러운 포물선
const float Gravity      = 800f;   // 픽셀/초² (가속)
const float MaxFallSpeed = 400f;   // 픽셀/초 (캡 — 터널링 방지 + 공기저항 모사)
const float JumpVelocity = -350f;  // 픽셀/초 (위로, 음수)

// 매 프레임:
VelocityY += Gravity * dt;                       // 가속
VelocityY = MathF.Min(VelocityY, MaxFallSpeed);  // 캡
Position.Y += VelocityY * dt;
```

가속도가 있으면 점프 커브가 포물선이 되어 자연스럽다:
```
가속도 있음 (채택):     고정 속도 (부자연):
     ╱╲                    ┌──┐
    ╱  ╲                   │  │
   ╱    ╲                  │  │
  ╱      ╲                 │  │
```

#### 터널링 방지 (Swept 검사)

고속 낙하/투사체가 1프레임에 플랫폼을 뚫는 문제:

```
프레임 N:    ●  prevPos (Y=100)
             │
━━━━━━━━━━━━━╋━  바닥 (Y=120) → 교차점에서 착지!
             │
프레임 N+1:  ○  currPos (Y=150) ← 여기까지 안 감
```

**전략: 캐릭터(A) + 투사체(B) 분리**

| 대상 | 방법 | 이유 |
|------|------|------|
| 캐릭터 | MaxFallSpeed 캡 | 속도 제한으로 터널링 원천 차단 |
| 투사체 | Swept AABB | 빠른 속도, 캡 불가 → 경로 교차 검사 |

```csharp
// Swept 검사: 이전→현재 이동 경로가 Platform Line과 교차하는지
bool SweptCheck(Vec2 prevPos, Vec2 currPos, Platform platform)
{
    return LineSegmentIntersect(
        prevPos, currPos,             // 이동 경로 (선분)
        platform.Start, platform.End  // 플랫폼 (선분)
    );
    // 교차점이 있으면 → 해당 위치에서 충돌 처리
}
```

#### 충돌 2종 분리

```
CollisionSystem
  ├─ AABB 판정: 유닛↔유닛, 유닛↔벽 (X축 차단)
  └─ Line 판정: 캐릭터 발 위치↔Platform (Y축 착지)

PhysicsSystem
  ├─ 중력 적용 (Y 속도)
  ├─ 점프 (초기 Y속도 + 가변 높이)
  └─ CollisionSystem 결과로 착지/벽 정지 처리
```

#### Platform 데이터 구조

```csharp
public class Platform
{
    public Vec2 Start { get; }   // 선분 시작
    public Vec2 End { get; }     // 선분 끝
    public bool OneWay { get; }  // true = semi-solid (반투과)
}
```

#### Platform 타입

```
━━━━━━━━━━━  Solid (OneWay=false)
             위아래 모두 차단. 올라갈 수 없고, 내려갈 수 없음.

──────────── Semi-solid (OneWay=true)
             아래에서 점프 → 관통 → 착지 가능.
             ↓+점프 → 관통 낙하 가능.
```

#### 판정 규칙

| Platform 타입 | 상승 중 (점프) | 하강 중 | ↓+점프 |
|---|---|---|---|
| Solid | 차단 (머리 부딪힘) | 착지 | 불가 |
| Semi-solid | 관통 (올라감) | 착지 | 관통 (내려감) |

```csharp
bool ShouldCollide(Unit unit, Platform platform)
{
    if (platform.OneWay)
    {
        if (unit.VelocityY > 0)  return false;  // 상승 → 관통
        if (unit.IsDropping)     return false;  // ↓+점프 → 관통
        return unit.FootY >= platform.Y - epsilon;  // 발이 위에 있을 때만
    }
    return true;  // Solid: 항상 충돌
}
```

#### ↓+점프 (Drop-through) 구현

1. 플레이어 ↓ + 점프 입력
2. `Unit.IsDropping = true`
3. 현재 밟고 있는 Semi-solid 플랫폼 무시
4. 발이 플랫폼 아래로 완전히 빠지면 `IsDropping = false` 해제

#### 경사/계단

경사 Line segment로 자연스러운 2층 구현:

```
        ╱─── 2층 플랫폼
       ╱ ← 경사 Line (계단)
──────╱
 1층 바닥
```

캐릭터 발 위치 X가 경사 Line 위에 있으면,
Y를 해당 X의 Line 높이로 고정 (지면 추종).

#### 실행 순서

```
ThinkSystem → ... → CollisionSystem (AABB + Line) → PhysicsSystem (중력/점프) → ...
```

PhysicsSystem은 CollisionSystem 결과를 읽어 착지/벽 정지를 처리한다.

```csharp
public class PhysicsSystem : ECS.System
{
    protected override void Proc(int step, Span<Component[]> allComponents)
    {
        if (!_scenarioConfig.PhysicsEnabled) return;
        // 1. 중력 적용 (VelocityY += gravity * dt)
        // 2. 위치 갱신 (Position += Velocity * dt)
        // 3. CollisionSystem 결과 반영 (착지 → VelocityY=0, 벽 → VelocityX=0)
    }
}
```

### Python API 확장

```python
# 기존 (유지)
morld.get_unit_location(unit_id)           # → (region_id, location_id)

# 확장
morld.get_unit_position(unit_id)           # → (x, y)
morld.set_unit_position(unit_id, x, y)
morld.get_location_size(region_id, loc_id) # → (width, height)
```

시나리오 02/03에서 `get_unit_position()`은 `(x, 0)` 반환.

---

## 구현 순서

| 순서 | 작업 | 검증 |
|------|------|------|
| 1 | Unit.Position → Vec2 + PositionX 래퍼 | 시나리오 02 기존 동작 확인 |
| 2 | MovementProgress 2D 확장 + 1D 래퍼 | 이동/Gate 전환 동작 확인 |
| 3 | Gate.Position → Vec2 + X 래퍼 | Gate 이동 동작 확인 |
| 4 | Location.Height 추가 | 기존 Location은 Height=0 |
| 5 | CollisionSystem 추가 (abstract 모드) | 시나리오 02 이벤트 동작 확인 |
| 6 | Python API 확장 | morld.get_unit_position 테스트 |
| 7 | PhysicsSystem 추가 (비활성 기본) | 시나리오 02 영향 없음 확인 |
| 8 | 시나리오 04 프로토타입 | 중력/점프/충돌 통합 테스트 |

**핵심**: 매 단계마다 시나리오 02를 실행하여 기존 동작을 검증한다.

---

## 설계 배경

시나리오 02/03은 처음부터 Location 이동(X축) + Gate 이동을
플랫포머와 호환 가능한 구조로 설계하였다.
v0.3.0은 이 기반 위에 Y축, 충돌, 실시간 물리를 **추가**하는 것이지,
기존 구조를 **교체**하는 것이 아니다.

Z축은 추가하지 않는다. 이 프로젝트는 2D(XY) 기반이며, 이는 영구 결정이다.
