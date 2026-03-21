# 던전 시스템 설계

## 개요

던전은 **별도 리전**으로 관리되며, 기존 지형 시스템을 활용합니다.
전투와 이벤트는 **다이얼로그 기반**으로 진행되고, **NPC 주도 이벤트** 패턴을 활용하여 선제 발동이 가능합니다.

### 던전 유형

| 유형 | 설명 | 문서 |
|------|------|------|
| **고정 던전** | 수동 정의 Region/Location/Gate. 영구 존재. | 이 문서 |
| **인스턴트 던전** | BSP+Spec 기반 동적 생성. 매일 생성/삭제. | [instant-dungeon.md](instant-dungeon.md) |

인스턴트 던전은 Spec + seed로 결정론적 생성, 층별 Lazy Generation, Bridge로 탐색 루프를 제공합니다.

---

## 던전 리전 구조

### 리전 배치

```
Region 0: 숲속 저택 (mansion)
Region 1: 차량 (vehicle)
Region 2: 도심 (city)
Region 3: 숲 (forest)
Region 4: 폐광산 (mine)        ← 구현 완료 (채광 + 몬스터)
Region 5: 잊혀진 유적 (test_dungeon) ← 구현 완료 (테스트 던전)
Region 6+: 던전 (dungeon)      ← 미래 확장
```

### Gate 연결 방식

던전 입구는 기존 지형의 Location에서 RegionGate로 연결됩니다.

```python
# 예시: 숲속 동굴 입구 (R0:25) ↔ 동굴 던전 (R3:0)
REGION_GATES = [
    (3, mansion.REGION_ID, 25, dungeon.REGION_ID, 0, 5),  # 5분 이동
]
```

---

## 던전 타입

### 1. 한 칸 던전 (Single-Location Dungeon)

하나의 Location만 사용하며, **props로 상태(층수 등)를 관리**합니다.

**특징:**
- 단일 Location에서 모든 진행
- `floor` prop으로 층수 관리
- 층 이동, 전투, 이벤트 모두 다이얼로그로 처리
- 탈출 시 입구로 복귀

**구조 예시:**
```
Region 3 (dungeon)
└─ Location 0 (동굴 던전)
   └─ props: {floor: 1, max_floor: 5, cleared: false}
```

**Python Asset 예시:**
```python
class CaveDungeon(Location):
    """동굴 던전 - 한 칸 던전"""
    unique_id = "cave_dungeon"
    name = "동굴 던전"
    is_indoor = True

    # 던전 설정
    max_floor = 5
    floor_events = {
        1: "슬라임 무리가 나타났다!",
        2: "독버섯 군락이 있다.",
        3: "고블린 정찰대와 마주쳤다!",
        4: "깊은 어둠이 감싸고 있다.",
        5: "보스: 동굴 골렘이 깨어났다!",
    }

    def on_enter(self, unit_id):
        """던전 진입 시 초기화"""
        morld.set_prop(f"dungeon:{self.unique_id}:floor", 1)
        yield from self._show_floor_event(1)

    def explore(self):
        """탐색 액션 - 층 이동"""
        current_floor = morld.get_prop(f"dungeon:{self.unique_id}:floor") or 1

        # 선택지: 다음 층 / 이전 층 / 탈출
        choice = yield morld.dialog(
            f"[b]동굴 던전 {current_floor}층[/b]\n\n"
            f"[url=@ret:next]다음 층으로[/url]\n"
            f"[url=@ret:prev]이전 층으로[/url]\n"
            f"[url=@ret:exit]탈출[/url]",
            autofill="off"
        )

        if choice == "next" and current_floor < self.max_floor:
            new_floor = current_floor + 1
            morld.set_prop(f"dungeon:{self.unique_id}:floor", new_floor)
            yield from self._show_floor_event(new_floor)
        elif choice == "prev" and current_floor > 1:
            new_floor = current_floor - 1
            morld.set_prop(f"dungeon:{self.unique_id}:floor", new_floor)
        elif choice == "exit":
            yield from self._exit_dungeon()

    def _show_floor_event(self, floor):
        """층별 이벤트 표시"""
        event_text = self.floor_events.get(floor, "조용하다.")
        yield morld.dialog(f"[{floor}층]\n{event_text}")
        # 전투 이벤트면 전투 다이얼로그로 연결
```

### 2. 그래프 던전 (Graph Dungeon)

여러 Location으로 구성되며, 일반 지형처럼 Gate로 연결됩니다.

**특징:**
- 여러 Location이 Gate로 연결
- 각 Location에 몬스터/이벤트 배치
- on_reach/on_meet 이벤트로 전투 트리거
- 분기, 막다른 길, 숨겨진 방 등 구현 가능

**구조 예시:**
```
Region 3 (dungeon)
├─ Location 0 (던전 입구)
├─ Location 1 (갈림길)
│   ├─ Gate → Location 2 (왼쪽 통로)
│   └─ Gate → Location 3 (오른쪽 통로)
├─ Location 2 (왼쪽 통로)
│   └─ Gate → Location 4 (보물방)
├─ Location 3 (오른쪽 통로)
│   └─ Gate → Location 5 (보스방)
├─ Location 4 (보물방)
└─ Location 5 (보스방)
```

**Python 정의 예시:**
```python
# world/dungeon.py
REGION_ID = 3

def initialize_terrain():
    from assets.locations.dungeons import (
        DungeonEntrance, DungeonFork,
        DungeonLeftPath, DungeonRightPath,
        TreasureRoom, BossRoom
    )

    morld.add_region(REGION_ID, "던전", ...)

    locations = {
        0: DungeonEntrance(),
        1: DungeonFork(),
        2: DungeonLeftPath(),
        3: DungeonRightPath(),
        4: TreasureRoom(),
        5: BossRoom(),
    }

    # 내부 Gate 연결
    gates = [
        Gate(0, 1, travel_time=3),  # 입구 → 갈림길
        Gate(1, 2, travel_time=2),  # 갈림길 → 왼쪽
        Gate(1, 3, travel_time=2),  # 갈림길 → 오른쪽
        Gate(2, 4, travel_time=2),  # 왼쪽 → 보물방
        Gate(3, 5, travel_time=3),  # 오른쪽 → 보스방
    ]
```

---

## 전투 시스템 (다이얼로그 기반)

### 전투 트리거

**방법 1: on_reach 이벤트 (위치 도착 시)**
```python
@register
class BossRoomReach(OnReachEvent):
    location = (3, 5)  # 보스방

    def handle(self, **ctx):
        if not morld.get_prop("dungeon:boss_defeated"):
            yield from start_battle("cave_golem")
```

**방법 2: NPC 주도 이벤트 패턴 (선제 발동)**
```python
# 몬스터 캐릭터의 should_initiate_encounter() 체크
class GoblinScout(Monster):
    def should_initiate_encounter(self, player_id) -> bool:
        """전투 발동 조건"""
        # 플레이어와 같은 위치일 때
        player_loc = morld.get_unit_location(player_id)
        my_loc = morld.get_unit_location(self.instance_id)
        return player_loc == my_loc and not self.is_defeated

    def initiate_encounter(self, player_id):
        """선제 전투 시작"""
        yield morld.dialog(f"[{self.name}]\n끼에엑! 침입자다!")
        yield from start_battle(self.unique_id)
```

### 전투 다이얼로그 흐름

```python
def start_battle(monster_id):
    """전투 시작"""
    monster = get_monster(monster_id)
    player_id = morld.get_player_id()

    state = {
        "monster_hp": monster.max_hp,
        "player_hp": morld.get_unit_prop(player_id, "체력"),
        "turn": 1,
    }

    def render_battle():
        return (
            f"[b]전투[/b]\n\n"
            f"{monster.name}: HP {state['monster_hp']}/{monster.max_hp}\n"
            f"플레이어: HP {state['player_hp']}\n\n"
            f"[url=@proc:attack]공격[/url]\n"
            f"[url=@proc:skill]스킬[/url]\n"
            f"[url=@proc:item]아이템[/url]\n"
            f"[url=@proc:flee]도망[/url]"
        )

    def handle_action(action):
        if action == "init":
            return render_battle()

        if action == "attack":
            # 플레이어 공격
            damage = calculate_damage(player_id, monster_id)
            state["monster_hp"] -= damage

            if state["monster_hp"] <= 0:
                return True  # 승리, 다이얼로그 종료

            # 몬스터 반격
            counter_damage = calculate_monster_damage(monster_id)
            state["player_hp"] -= counter_damage

            if state["player_hp"] <= 0:
                return True  # 패배, 다이얼로그 종료

            state["turn"] += 1
            return render_battle()

        if action == "flee":
            if random.random() < 0.5:
                state["fled"] = True
                return True
            return f"도망치지 못했다!\n\n{render_battle()}"

        return None

    result = yield morld.dialog(
        render_battle(),
        autofill="off",
        proc=handle_action,
        result=state
    )

    # 전투 결과 처리
    if state.get("fled"):
        yield morld.dialog("도망쳤다!")
    elif state["monster_hp"] <= 0:
        yield morld.dialog(f"{monster.name}을(를) 쓰러뜨렸다!")
        morld.set_prop(f"monster:{monster_id}:defeated", 1)
        # 보상 지급
    else:
        yield morld.dialog("쓰러졌다...")
        # 패널티 처리
```

---

## 던전 이벤트

### 이벤트 타입

| 이벤트 | 트리거 | 설명 |
|--------|--------|------|
| 전투 | on_reach, NPC 주도 | 몬스터와 전투 |
| 함정 | on_reach | 데미지, 상태이상 |
| 보물 | 오브젝트 클릭 | 아이템 획득 |
| 퍼즐 | 다이얼로그 선택지 | 문 열기, 장치 작동 |
| NPC | on_meet | 상인, 조력자 |

### 이벤트 구현 예시

**함정:**
```python
class TrapRoom(Location):
    def on_enter(self, unit_id):
        if not morld.get_prop(f"trap:{self.unique_id}:triggered"):
            yield morld.dialog("바닥이 무너졌다!")
            morld.add_unit_prop(unit_id, "체력", -10)
            morld.set_prop(f"trap:{self.unique_id}:triggered", 1)
```

**보물:**
```python
class TreasureChest(Object):
    unique_id = "treasure_chest_01"
    name = "보물 상자"
    actions = ["call:open:열기"]

    def open(self):
        if morld.get_prop(f"chest:{self.unique_id}:opened"):
            yield morld.dialog("이미 열린 상자다.")
            return

        yield morld.dialog("상자를 열었다!")
        morld.give_item(morld.get_player_id(), "gold_coin", 50)
        morld.set_prop(f"chest:{self.unique_id}:opened", 1)
```

**조건부 문:**
```python
# Gate 조건으로 문 잠금
Gate(3, 5, conditions={"열쇠:보스방": 1})  # 열쇠 필요
Gate(2, 4, conditions={"퍼즐:레버#": 1})   # 레버 당겨야 열림 (# = 조건 미충족 시 숨김)
```

---

## 몬스터 시스템

### Monster 클래스

```python
class Monster(Character):
    """몬스터 기본 클래스"""
    unique_id: str = ""
    name: str = "몬스터"

    # 전투 스탯
    max_hp: int = 10
    attack: int = 3
    defense: int = 1

    # 드롭 아이템
    drops: list = []  # [(item_id, count, chance), ...]

    # 경험치/보상
    exp_reward: int = 10
    gold_reward: int = 5

    def should_initiate_encounter(self, player_id) -> bool:
        """선제 공격 조건"""
        return False

    def get_attack_message(self) -> str:
        return f"{self.name}의 공격!"

    def get_defeat_message(self) -> str:
        return f"{self.name}을(를) 쓰러뜨렸다!"
```

### 몬스터 예시

```python
class Slime(Monster):
    unique_id = "slime"
    name = "슬라임"
    max_hp = 15
    attack = 2
    defense = 0
    drops = [("slime_jelly", 1, 0.5)]
    exp_reward = 5
    gold_reward = 3

class CaveGolem(Monster):
    unique_id = "cave_golem"
    name = "동굴 골렘"
    max_hp = 100
    attack = 15
    defense = 10
    drops = [("golem_core", 1, 1.0), ("stone_fragment", 5, 1.0)]
    exp_reward = 100
    gold_reward = 50

    def should_initiate_encounter(self, player_id) -> bool:
        # 보스는 항상 선제 발동
        return True

    def get_attack_message(self) -> str:
        return "동굴 골렘이 거대한 주먹을 휘둘렀다!"
```

---

## 파일 구조

```
scenarios/scenario02/python/
├─ world/
│   ├─ dungeon.py          # 던전 리전 정의
│   └─ __init__.py         # REGION_GATES에 던전 연결 추가
├─ assets/
│   ├─ locations/
│   │   └─ dungeons.py     # 던전 Location 클래스
│   ├─ characters/
│   │   └─ monsters.py     # 몬스터 클래스
│   └─ objects/
│       └─ dungeon_objects.py  # 보물상자, 함정 등
├─ events/
│   ├─ dungeon/
│   │   ├─ reach.py        # 던전 on_reach 이벤트
│   │   └─ battle.py       # 전투 이벤트
│   └─ __init__.py
└─ dungeon/
    ├─ __init__.py         # 전투 시스템 API
    ├─ battle.py           # start_battle(), 전투 로직
    └─ monsters.py         # 몬스터 데이터
```

---

## 구현 순서

1. **던전 리전 기본 구조** (`world/dungeon.py`)
   - Region 등록
   - 테스트용 한 칸 던전 Location 추가

2. **한 칸 던전 구현** (`assets/locations/dungeons.py`)
   - CaveDungeon 클래스
   - floor prop 관리
   - 층 이동 다이얼로그

3. **전투 시스템** (`dungeon/battle.py`)
   - start_battle() 함수
   - 전투 다이얼로그 렌더링
   - 데미지 계산

4. **몬스터 클래스** (`assets/characters/monsters.py`)
   - Monster 베이스 클래스
   - 테스트 몬스터 (슬라임)

5. **이벤트 연동** (`events/dungeon/`)
   - on_reach 전투 트리거
   - NPC 주도 선제 공격

6. **그래프 던전 확장**
   - 복잡한 던전 레이아웃
   - 퍼즐, 분기, 숨겨진 방

---

## 잊혀진 유적 (Region 5) — 구현 완료

### 개요

깊은 숲(R3:L3)에서 연결되는 그래프 던전. 인간형/기생형 몬스터 테스트용.

### 파일

| 파일 | 역할 |
|------|------|
| `world/test_dungeon.py` | R5 지형 정의 + Gate + 스폰 소스 |
| `assets/locations/test_dungeon.py` | 5개 Location 클래스 |

### 레이아웃

```
숲속(R3:L3) ─── 15분 도보 ──→ 유적 입구(R5:L0)
                                  │
                              1층 회랑(R5:L1) ─── 거미
                                  │
                              2층 거미굴(R5:L2) ─── 아라크네 + 유방기생충
                                  │
                              3층 기생실(R5:L3) ─── 음부기생충 × 2
                                  │
                              유적 심층(R5:L4) ─── 서큐버스 (보스)
```

### Location 명세

| ID | 이름 | 실내 | 지면 | 길이 | 특이사항 |
|----|------|------|------|------|---------|
| 0 | 유적 입구 | X | Dirt | 400 | 기생체 제거제 2개 바닥 배치 |
| 1 | 1층 회랑 | O | Concrete | 500 | |
| 2 | 2층 거미굴 | O | Dirt | 400 | |
| 3 | 3층 기생실 | O | Dirt | 300 | |
| 4 | 유적 심층 | O | Concrete | 200 | |

### 스폰 소스

| ID | 몬스터 | 최대 수 | 간격 | 위치 |
|----|--------|---------|------|------|
| ruin_spiders_1f | Spider | 2 | 4h | R5:L1 |
| ruin_arachne | Arachne | 1 | 6h | R5:L2 |
| ruin_parasites_2f | BreastParasiteCreature | 1 | 8h | R5:L2 |
| ruin_parasites_3f | GenitalParasiteCreature | 2 | 6h | R5:L3 |
| ruin_boss | Succubus | 1 | 12h | R5:L4 |

### Gate 연결

| 시작 | 끝 | 거리 |
|------|-----|------|
| R5:L0 (입구) | R5:L1 (회랑) | 400 |
| R5:L1 (회랑) | R5:L2 (거미굴) | 500 |
| R5:L2 (거미굴) | R5:L3 (기생실) | 400 |
| R5:L3 (기생실) | R5:L4 (심층) | 300 |

모든 Gate는 양방향.

---

## 참고: 자동차 시스템과의 비교

| 항목 | 자동차 | 던전 |
|------|--------|------|
| 리전 타입 | 내부 공간 (1 Location) | 탐험 공간 (1+ Location) |
| 진입 방식 | sit 액션 | Gate 이동 |
| 상태 관리 | seated_on prop | floor, cleared prop |
| 이동 | RegionGate 변경 | Gate 이동 또는 prop 변경 |
| 이벤트 | 운전 다이얼로그 | 전투/탐험 다이얼로그 |
