# Morld 게임플레이 시스템

## 장비 시스템 (Equipment System)

### 슬롯 정의

`equip_props`에 `"장착:{슬롯}": 1` 형식으로 슬롯 직접 정의

```python
class FishingRod(Item):
    unique_id = "fishing_rod"
    name = "낚시대"
    equip_props = {"can:fish": 1, "장착:손": 1}
    actions = ["take@container", "equip@inventory"]
```

| 슬롯 | 키 형식 | 설명 |
|------|---------|------|
| 손 | `장착:손` | 무기, 도구 |
| 머리 | `장착:머리` | 헬멧, 모자 |
| 몸통 | `장착:몸통` | 갑옷, 의류 |

### 장비 정보 전달 (equipment 파라미터)

`call:` 액션 실행 시, `can:` prop을 제공한 장비 정보가 Python 메서드에 전달됨

```python
def chop(self, equipment=None):
    if equipment:
        equip_props = equipment.get("equip_props", {})
        if equip_props.get("날붙이"):
            yield morld.dialog("뚝딱뚝딱 벌목한다...")
```

---

## 바닥(Ground) 시스템

Location은 inventory를 갖지 않음. "바닥" Object가 아이템 저장.

```python
class Ground(Object):
    item_visible = True  # 아이템 개수 표시
    actions = ["putinobject"]

class GroundGrass(Ground):
    unique_id = "ground_grass"
    name = "잔디"
```

### morld API

```python
morld.set_location_ground_id(region_id, location_id, ground_unit_id)
morld.get_location_ground_id(region_id, location_id)
```

---

## 소유자(Owner) 시스템

`Owner`는 **원래 소유자**를 나타냄. 획득해도 변경되지 않음.

```python
class KitchenKnife(Item):
    unique_id = "kitchen_knife"
    name = "부엌칼"
    owner = "mila"  # 밀라 소유

class LinaRoom(Location):
    unique_id = "lina_room"
    name = "방"
    owner = "lina"  # 리나 소유
```

UI에서 `(XXX 소유)` 형태로 표시

---

## 관계(Prop) 형식

**형식:** `관계:{대상}:{유형}`

```python
props = {
    "관계:세라:신뢰": 1,      # 세라를 신뢰
    "관계:플레이어:호감": 3,  # 플레이어에게 호감 3
}
```

---

## 생존 시스템 (Survival System)

### 수치 설계

| 상수 | 값 | 설명 |
|------|-----|------|
| SATIETY_DECAY_RATE | 1 | 1시간당 포만감 감소 |
| HEALTH_REGEN_RATE | 1 | 포만감 50+일 때 1시간당 체력 회복 |
| HEALTH_DECAY_RATE | 2 | 포만감 0일 때 1시간당 체력 감소 |

### Python API

```python
import survival

stats = survival.get_survival_stats(unit_id)
# {"health": 100, "max_health": 100, "satiety": 80, "max_satiety": 100}

survival.add_satiety(unit_id, 25)
survival.add_health(unit_id, -10)

bar = survival.get_status_bar(unit_id)
# "체력: [color=lime]████████░░[/color] 80  포만감: ..."
```

### 활성화 조건

- `생존:활성화` prop이 1 이상이면 활성화
- 챕터 0에서는 비활성화, 챕터 1에서 활성화

---

## 자원 생성 시스템 (Resource Spawning)

`on_time_elapsed` 이벤트 구독, 오브젝트별 시간 누적 후 자원 생성

```python
# think/resource_agent.py
RESOURCE_CONFIG = {
    "apple_tree": (720, 3),      # 12시간마다, 최대 3개
    "berry_bush": (480, 5),      # 8시간마다, 최대 5개
}
```

---

## 덫 시스템 (Trap System)

토끼 굴 등에 덫을 설치하여 동물 포획

```python
# think/trap_agent.py
RABBIT_BURROW_CONFIG = {
    "rabbit_burrow": (360, 0.4),  # 6시간마다 체크, 40% 확률
}
```

동작 흐름:
1. `RabbitBurrow.instantiate()` → `trap_agent.register_rabbit_burrow()`
2. `on_time_elapsed` 이벤트 발생 시 시간 누적
3. `check_interval` 도달 시 확률 판정
4. 성공 시 `rabbit_trap` 제거, `trapped_rabbit` 생성

---

## 시간 정지 시스템 (Time Freeze)

> 상세 내용은 [frozen.md](frozen.md) 참조

```python
morld.set_time_frozen(True)   # 시간 정지
morld.set_time_frozen(False)  # 시간 흐름 복원
```

### Freeze 상태에서

| 비활성화 | 활성화 |
|----------|--------|
| 시간 흐름, NPC 이동/AI | 플레이어 이동 (즉시 텔레포트) |
| on_meet, on_time_elapsed | on_reach 이벤트 |
| 생존 시스템 | 아이템 조작 |

---

## 연애 시스템 (Romance System)

> 상세 내용은 [romance.md](romance.md) 참조

| 시스템 | 파일 | 설명 |
|--------|------|------|
| 스킨십 | `romance.py` | 플레이어 주도 친밀 행위 |
| 데이트 | `date.py` | 데이트 요청/종료 |
| NPC 주도 | `npc_initiative.py` | NPC가 먼저 스킨십 시작 |

### 캐릭터별 NPC 주도 설정

| 캐릭터 | 성욕 임계값 | 호감도 임계값 | 쿨다운 |
|--------|------------|--------------|--------|
| 세라 | 70 | 60 | 8시간 |
| 밀라 | 50 | 40 | 6시간 |
| 리나 | 65 | 55 | 8시간 |
| 유키 | 80 | 70 | 12시간 |
| 엘라 | 75 | 65 | 10시간 |
