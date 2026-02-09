# Morld 시스템 코어

## 프로젝트 개요

Morld는 ECS(Entity Component System) 아키텍처를 기반으로 한 게임 월드 시뮬레이션 시스템입니다.

**핵심 기술:**
- Godot 4 엔진 + C# .NET
- ECS 아키텍처
- JobList 기반 행동 시스템 (시간 기반 선형 리스트)
- sharpPy (Python 인터프리터) 기반 스크립트 시스템
- Python Asset 클래스 기반 데이터 정의

---

## ECS 아키텍처

### Data Management Systems (데이터 관리 시스템)

게임 상태를 저장하고 관리. JSON Import/Export 지원, 세이브/로드 대상.

| 시스템 | 역할 |
|--------|------|
| `WorldSystem` | 지형(Terrain) 데이터 및 GameTime 보관 |
| `UnitSystem` | 유닛 데이터 (캐릭터/오브젝트, 위치, JobList) |
| `ItemSystem` | 아이템 정의 데이터 |
| `InventorySystem` | 인벤토리 데이터 (유닛별 아이템 소유, 장착) |

### Logic/Behavior Systems (로직 시스템)

매 Step마다 게임 로직 실행. Stateless.

| 시스템 | 역할 |
|--------|------|
| `ThinkSystem` | Python Agent의 think() 호출, JobList 채우기 |
| `JobBehaviorSystem` | JobList 기반 이동/행동 처리, GameTime 업데이트 |
| `PlayerSystem` | 플레이어 입력 기반 시간 진행 제어 |
| `DescribeSystem` | 묘사 텍스트 생성 |
| `TextUISystem` | RichTextLabel 관리, 스택 기반 화면 전환 |
| `ScriptSystem` | Python 스크립트 실행, Dialog/이벤트 처리 |
| `EventSystem` | 게임 이벤트 감지 및 Python 전달 |

### 시스템 실행 순서

```
ThinkSystem → EventPredictionSystem → EventSystem → JobBehaviorSystem → PlayerSystem → DescribeSystem
```

---

## GameEngine 이벤트 루프

```csharp
// GameEngine._Process() - 매 프레임 실행
if (_playerSystem.HasPendingTime)
{
    // 1. World Step 실행
    this._world.Step(delta_int);

    // 2. 만남 감지
    _eventSystem.DetectMeetings();
    var eventHandled = _eventSystem.FlushEvents();

    // 3. 이벤트 발생 시 시간 진행 중단
    if (eventHandled)
        _playerSystem.ClearPendingTime();

    // 4. 시간 진행 완료 후 추가 처리
    if (!_playerSystem.HasPendingTime)
    {
        _eventSystem.DetectLocationChanges();
        _eventSystem.FlushEvents();
        UpdateSituationText();
    }
}
```

---

## JobList 기반 행동 시스템

**JobList**는 시간 기반 선형 리스트로, 각 유닛이 수행할 Job들을 관리합니다.

### Job 구조

```csharp
Job
├─ Name (string - "순찰", "이동", "대기")
├─ Action (string - "move", "stay", "follow", "flee")
├─ Duration (int - 소요 시간, 분)
├─ RegionId, LocationId (move 목표)
├─ TargetId (follow/flee 대상)
└─ Activity (string - 현재 활동)
```

### Job Action 타입

| Action | 설명 | 필수 필드 |
|--------|------|----------|
| `move` | 목표 위치로 이동 | RegionId, LocationId |
| `stay` | 현재 위치에서 대기 | Duration |
| `follow` | 대상 유닛 따라가기 | TargetId, Duration |
| `flee` | 대상으로부터 도망 | TargetId, Duration |

---

## Unit 데이터 구조

```csharp
Unit
├─ Id (int)
├─ UniqueId (string - "sera", "mila")
├─ Name
├─ IsObject (bool)
├─ CurrentLocation (LocationRef)
├─ PositionX, PositionY (float - Pi-World 2D 좌표)
├─ CurrentMovement (MovementProgress? - Pi-World 이동 상태)
├─ JobList
├─ Actions (List<string>)
├─ Mood (HashSet<string>)
├─ IsMoving (CurrentMovement != null)
├─ IsTraveling (currentLoc != jobLoc)
└─ IsIdle (CurrentMovement == null)
```

---

## 프로젝트 구조

```
scripts/
├─ GameEngine.cs (진입점)
├─ MetaActionHandler/ (BBCode URL 클릭 핸들러)
├─ system/ (ECS Systems)
│  ├─ world_system.cs
│  ├─ unit_system.cs
│  ├─ item_system.cs
│  ├─ inventory_system.cs
│  ├─ think_system.cs
│  ├─ job_behavior_system.cs
│  ├─ player_system.cs
│  ├─ describe_system.cs
│  ├─ text_ui_system.cs
│  ├─ script_system.cs
│  └─ event_system.cs
└─ morld/ (Core Data Structures)
   ├─ unit/
   ├─ schedule/
   ├─ terrain/
   ├─ item/
   └─ ui/

scenarios/scenario02/python/
├─ __init__.py (시나리오 초기화)
├─ world.py (지형 데이터)
├─ items.py (아이템 데이터)
├─ assets/ (Python Asset 클래스)
├─ events/ (이벤트 핸들러)
├─ chapters/ (챕터 관리)
├─ think/ (NPC AI Agent)
├─ temperature.py (온도 시스템)
├─ humidity.py (습도 시스템)
├─ congestion.py (혼잡도 시스템)
├─ pollution.py (오염도 시스템)
└─ sound.py (소리 전파 시스템)
```

---

## 챕터 전환 라이프사이클

`chapters/__init__.py`의 `load_chapter()` 실행 순서:

```
1. 기존 데이터 저장 (preserve_player=True 시)
2. morld.clear_world() — 기존 유닛/지형 삭제
2.1. 환경 시스템 reset() — temperature, humidity, congestion, sound
3. 챕터 모듈 동적 import
4. chapter_module.initialize() — 새 지형/유닛/오브젝트 생성
5. 저장된 플레이어 데이터 복원
5.1. chapter_module.post_restore() — 챕터별 후처리
6. morld.reinitialize_locations() — EventSystem 위치 초기화
7. Instance ID 중복 검사
8. 현재 챕터 기록
```

**환경 시스템 reset**: lazy init 모듈(`temperature`, `humidity`, `congestion`, `sound`)은 `get_region_info()`로 location 데이터를 구축합니다. 챕터 전환 시 location이 바뀌므로, `reset()`으로 `_initialized = False`를 설정하여 다음 접근 시 새 데이터로 재초기화됩니다.

---

## 빌드 및 실행

```bash
dotnet build
```

Godot 에디터에서 프로젝트 실행
