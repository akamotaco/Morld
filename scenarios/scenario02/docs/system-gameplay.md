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

## 온도 시스템 (Temperature System)

> `temperature.py` — 순수 Python, C# 변경 없음

Location별 온도 시뮬레이션 + 캐릭터 체온 수렴 시스템.

### 실외 온도 결정

```
실외 온도 = 계절 기본값 + 날씨 보정 + 시간대 오프셋
```

| 계절 | 기본값 | | 날씨 | 보정 |
|------|--------|--|------|------|
| 봄 | 15°C | | 맑음 | +2 |
| 여름 | 28°C | | 흐림 | 0 |
| 가을 | 12°C | | 비 | -3 |
| 겨울 | -5°C | | 눈 | -5 |

시간대 오프셋: 새벽 -5 ~ 낮 +5 (24시간 고정 테이블)

### 실내 온도 업데이트 (매시간)

```
1. old_temps = 스냅샷
2. 실외 location → outdoor_temp 직접 적용
3. 열원 BFS 계산 (light:on 체크, depth별 감쇠)
4. 실내 location:
   - neighbor_avg = 인접 location 가중 평균
     (indoor↔indoor: 1.0, indoor↔outdoor: 0.5)
   - target = neighbor_avg + heat_contribution
   - new = old + (target - old) × 0.3
5. Clamp [-30, 50]
```

### 열원 시스템

오브젝트에 `heat:output`, `heat:depth` prop 설정 → `temperature.register_heat_source()` 호출.
`light:on` prop을 공유하여 on/off 제어.

```python
class Fireplace(Object):
    props = {
        "light:on": 1,
        "light:value": 4,
        "heat:output": 15,   # +15°C
        "heat:depth": 1,     # 인접 1칸까지
    }

class DrumBath(Object):
    props = {
        "action:bath": 1,
        "light:on": 1,       # 물 데우는 불 (상시)
        "heat:output": 5,    # +5°C (약한 열원)
        "heat:depth": 0,     # 해당 location에만
    }
```

BFS 감쇠: depth 0 = 100%, depth 1 = 50%, depth 2 = 25%

은신처 총 열원: PortableStove(8) + DrumBath(5) = **13°C** (저택 Fireplace 15에 근접)

### 목욕 체온 효과

Bathtub(저택), DrumBath(은신처) 사용 시:
- **체온 +2°C** — `temperature.warm_character(player_id, 2.0)`
- **젖음 완전 제거** — `humidity.dry_unit(player_id, 100)`

NPC `_handle_bath()`도 동일 효과 적용 (목욕 location 도착 시).

### 캐릭터 체온

Location 온도, 젖음, 장비 보온에 따라 매시간 수렴합니다.

체열 가둠 + 환경 열교환 모델:
- **보온**: 체열을 가두어 항상 체온↑ (여름 = 옷 벗기, 겨울 = 옷 입기)
- **열전달률**: location별 수정자 (실내 0.7, 실외 1.0, 바람 1.5 등)
- **방풍**: 열전달률을 낮춰 환경 영향 감소

```
trapped_heat = 36.5 × insulation × 0.005         (체열 가둠, 항상 +)
effective_rate = max(0.3, loc_rate - windproof × 0.3)
env_change = (loc_temp - 36.5) × 0.04 × effective_rate  (환경 열교환)
target = 36.5 + trapped_heat + env_change - (wetness / 100) × 2.0
new = current + (target - current) × 0.3
clamp(34.0, 40.0)
```

| 상수 | 값 | 설명 |
|------|---|------|
| `NORMAL_BODY_TEMP` | 36.5 | 정상 체온 |
| `HEAT_TRANSFER_RATE` | 0.04 | 기본 열전달률 (체온↔환경) |
| `INSULATION_HEAT_COEFF` | 0.005 | 보온 1당 체열 가둠 계수 (체온의 0.5%) |
| `INDOOR_TRANSFER_RATE` | 0.7 | 실내 기본 열전달률 수정자 |
| `OUTDOOR_TRANSFER_RATE` | 1.0 | 실외 기본 열전달률 수정자 |
| `WINDPROOF_REDUCTION` | 0.3 | 방풍 1당 열전달률 -0.3 |
| `TRANSFER_RATE_MIN` | 0.3 | 열전달률 하한 |
| `WETNESS_TEMP_PENALTY` | 2.0 | 100% 젖음 시 target -2℃ |
| `BODY_CONVERGENCE_RATE` | 0.3 | 시간당 30% 수렴 |

| loc_temp | 보온 | loc_rate | 방풍 | target |
|----------|------|---------|------|--------|
| 20℃(실외) | 0 | 1.0 | 0 | 35.8 |
| 20℃(실내) | 2 | 0.7 | 0 | 36.4 |
| -5℃(바람) | 0 | 1.5 | 0 | 34.0 |
| -5℃(바람) | 7 | 1.5 | 1 | 35.8 |
| 33℃(실외) | 0 | 1.0 | 0 | 36.4 |

### Python API

```python
import temperature

# Location 온도 조회
temp = temperature.get_temperature(region_id, location_id)

# 캐릭터 체온
temperature.register_character(unit_id)             # 체온 추적 등록
temperature.get_body_temperature(unit_id)            # → float (기본 36.5)
temperature.set_body_temperature(unit_id, value)     # 체온 설정

# 열원 등록
temperature.register_heat_source(unit_id, region_id, location_id)

# Location 열전달률 (바람, 특수 환경 등)
temperature.set_location_transfer_rate(region_id, location_id, 1.5)  # 바람
temperature.get_location_transfer_rate(region_id, location_id)       # → float (기본 1.0)

# 체온 즉시 조작 (목욕 등)
temperature.warm_character(unit_id, 2.0)           # 체온 +2°C (BODY_TEMP_MAX 제한)

# NPC 인터럽트용 상태 확인
temperature.is_cold(unit_id, threshold=35.5)       # → bool (체온 ≤ threshold)
temperature.is_hot(unit_id, threshold=37.5)        # → bool (체온 ≥ threshold)
temperature.get_insulation_total(unit_id)           # → float (장착 보온 합계)
```

플레이어는 자동 추적 (register 불필요). NPC는 에이전트 `__init__`에서 `register_character()` 호출.

### 챕터 전환 대응

`reset()` 함수로 상태 초기화. `chapters/__init__.py`의 `load_chapter()`에서 자동 호출.

**주의**: 초기화 완료 후 미등록 location 조회 시 `KeyError` 발생 (데이터 누락 버그 조기 감지)

### UI 표시

**Header** — `ui.get_time_weather_text()`에서 날씨 뒤에 location 온도 표시:
```
1년 4월 1일 (수) 20:00 / 흐림 12℃
```

**Footer** — `ui._get_environment_status_text()`에서 캐릭터 체온 표시:
```
체온 36.5℃ | 젖음 20% | 오염 15
```
- 체온: 항상 표시 (`< 35.5` cyan, `> 37.5` red)
- 젖음: `> 0`일 때만 (cyan)
- 오염: `> 0`일 때만 (orange)

---

## 오염도 시스템 (Pollution System)

> `pollution.py` — 순수 Python, C# 변경 없음

Location/오브젝트/캐릭터의 오염도를 시간 경과에 따라 시뮬레이션합니다.
NPC(밀라)가 빗자루로 청소하거나, 플레이어가 직접 청소할 수 있습니다.

### 오염도 등록 및 증가

```python
import pollution

# 챕터 초기화 시 location 등록
pollution.register_location(region_id, location_id, max_pollution=20, rate=1)
```

`subscribe_time_elapsed`로 1시간마다 업데이트:
- **Location**: `current += rate` (max까지)
- **오브젝트**: Location 오염도에 비례하여 증가 (prop `오염:수치`)
- **캐릭터**: `rate × CHAR_POLLUTION_FACTOR(0.3)`, 장비는 확률적 오염

### 청소

```python
# NPC/플레이어 청소
pollution.clean_location(region_id, location_id, amount)

# 오브젝트/유닛 청소
pollution.clean_unit(unit_id, amount)

# 현재 오염도 조회
current = pollution.get_location_pollution(region_id, location_id)
```

### NPC 청소 활동

`handle_clean()` — 4-phase 도구 기반 (chop.py 패턴):

```
idle → getting_tool → going_to_room ↔ (다음 방) → returning_tool
```

- `_find_tool_by_capability("can:clean")` — 빗자루 탐색
- `find_polluted_room(agent)` — 거처 내 오염된 방 탐색
- 청소 시 `pollution.clean_location(r, l, 청소력)` 호출 (빗자루 청소력=5)
- 동적 스케줄 조건 `should_clean`: 거처 내 오염도 > 0인 location 존재 여부

### 플레이어 청소

빗자루를 인벤토리에 넣고 "청소하기" 액션 사용:
- 현재 위치의 오염도를 `청소력`만큼 감소
- 소요 시간: 30분

### 오염도 등록 범위 (챕터 1)

| Region | Locations | max | rate |
|--------|-----------|-----|------|
| 0 (저택) | 0~16, 20~24 (22개) | 20 | 1 |
| 2 (도시) | 0~6 (7개) | 20 | 1 |
| 3 (숲) | 0~5 (6개) | 20 | 1 |

---

## 습도 시스템 (Humidity System)

> `humidity.py` — 순수 Python, C# 변경 없음

Location별 습도를 날씨 기반으로 관리하고, 비/눈에 의한 캐릭터·오브젝트·아이템 젖음을 처리합니다.
온도와 달리 **region → 실외 location 단방향**이며, 인접 location 영향은 없습니다.

### 날씨 강도 시스템

기본 날씨 타입(비/눈/맑음)에 **강도(intensity)**를 Python에서 관리합니다.
C# 태그(`날씨:비`)는 변경 없이 호환됩니다.

| 날씨 | 강도 | 습도 | 시간당 젖음 |
|------|------|------|------------|
| 비 | (기본) | 80% | +15 |
| 비 | 가랑비 | 60% | +5 |
| 비 | 소나기 | 90% | +25 |
| 비 | 폭우 | 100% | +40 |
| 눈 | (기본) | 60% | +5 |
| 눈 | 폭설 | 75% | +10 |
| 맑음 | (기본) | 30% | - |
| 맑음 | 폭염 | 15% | - |
| 흐림 | - | 50% | - |

- 날씨 변경 시 가중치 랜덤으로 강도 결정
- 폭염은 여름에만 발동
- UI: `"비(소나기)"`, `"맑음(폭염)"` 형태로 표시

### 실내/실외 습도

```
실외: WEATHER_BASE_HUMIDITY[날씨] + INTENSITY_HUMIDITY_MOD[강도]
실내: 고정 35% (비 영향 없음)
```

### 젖음 전파 (단방향: location → unit/item)

비/눈이 내리는 실외 location에서만 적용:

| 대상 | 젖음 | 비고 |
|------|------|------|
| 오브젝트 | O | location 내 모든 오브젝트 |
| item_visible 컨테이너 내 아이템 | O | 외부 노출 상태 |
| 캐릭터 | O | 매시간 + on_reach 즉시 |
| 캐릭터 장비 | O | 착용 중인 아이템 |
| 캐릭터 인벤토리 아이템 | X | 보호됨 |
| 연쇄 전파 (젖은 오브젝트 → 아이템) | X | 없음 |

### 방수 (Waterproof)

장착 아이템의 `equip_props`에서 `"방수"` 값을 합산하여 젖음 획득량을 감소시킵니다.

```
reduction = min(0.9, 방수합계 × 0.4)
actual_gain = gain × (1 - reduction)
```

| 아이템 | 방수 | 감소율 |
|--------|------|--------|
| 우산 | 1 | 40% |
| 우비 | 2 | 80% |
| 우비+우산 | 3 | 90% (상한) |

매시간 젖음과 on_reach 즉시 효과 모두에 적용됩니다.

### 방풍 (Windproof)

장착 아이템의 `equip_props`에서 `"방풍"` 값을 합산하여 환경 열전달률을 감소시킵니다.

```
effective_rate = max(0.3, loc_rate - 방풍합계 × 0.3)
```

| 아이템 | 방풍 |
|--------|------|
| 후드 망토 | 1 |
| 항공 자켓 | 1 |
| 우비 | 1 |

location 열전달률이 높을수록 (바람 등) 체온이 환경 온도에 더 빨리 영향받습니다.
방풍은 이 효과를 줄여줍니다. `set_location_transfer_rate(r, l, rate)`로 설정 가능.

### 건조 (매시간)

```
dry_rate = 5 (base)
if 온도 > 20℃: dry_rate += (온도 - 20) × 0.2
if 실내: dry_rate += 5
```

| 상황 | 건조 속도 | 만젖(100)→건조 |
|------|----------|--------------|
| 실내 30℃ | 12/시간 | ~8시간 |
| 실외 10℃ | 5/시간 | ~20시간 |
| 실외 40℃(폭염) | 9/시간 | ~11시간 |

### Python API

```python
import humidity

humidity.get_humidity(region_id, location_id)  # → float (0-100)
humidity.get_unit_wetness(unit_id)             # → float (0-100, 0=건조)
humidity.dry_unit(unit_id, amount)             # 건조 (모닥불 등)
humidity.is_raining()                          # → bool
humidity.get_weather_display()                 # → "비(소나기)" (UI용)
humidity.get_intensity()                       # → "소나기" or None
```

### 챕터 전환 대응

`reset()` 함수로 상태 초기화. `chapters/__init__.py`의 `load_chapter()`에서 자동 호출.

**주의**: 초기화 완료 후 미등록 location 조회 시 `KeyError` 발생 (데이터 누락 버그 조기 감지)

### UI 표시

`ui.get_time_weather_text()`에서 날씨 강도 + 습도 + 혼잡도 표시:
```
1년 4월 1일 (수) 20:00 / 비(소나기) 12℃ 습도90% 혼잡x2.0
```
혼잡도는 congestion > 0.5일 때만, > 1.0이면 노란색으로 표시.

---

## 혼잡도 시스템 (Congestion System)

> `congestion.py` — 순수 Python + C# `이동:혼잡` prop

Location별 혼잡도를 on_reach/on_leave 이벤트로 추적하고, 혼잡 시 이동속도를 감소시킵니다.

### 혼잡도 계산

```
congestion = population / capacity
capacity = max(MIN_CAPACITY, length / SPACE_PER_UNIT)
```

| 상수 | 값 | 설명 |
|------|---|------|
| `SPACE_PER_UNIT` | 5 | 캐릭터 1명당 점유 공간 |
| `MIN_CAPACITY` | 2 | 최소 수용 인원 |

### 이동속도 감속

congestion > 1일 때 `이동:혼잡` prop을 유닛에 설정:

| 혼잡도 | 이동:혼잡 | 실제 속도 |
|--------|----------|----------|
| 1.0 이하 | (없음) | 100% |
| 2.0 | 50 | 50% |
| 3.0 | 33 | 33% |
| 5.0+ | 20 | 20% (최소) |

C# `Unit.GetMovementSpeed()`에서 `이동:혼잡` prop을 읽어 최종 속도에 적용:
```
result = 이동:속도 × 자세보정 × 이동:혼잡 / 100
```

### 이벤트 연동

```
on_leave(unit, old_r, old_l) → population-- → _apply_congestion
on_reach(unit, new_r, new_l) → population++ → _apply_congestion
```

- `_apply_congestion`: 해당 location의 모든 유닛에 `이동:혼잡` prop 설정/해제
- lazy init: `get_region_info()` → location별 capacity 구축

### 초기화 및 동기화

- **lazy init**: 첫 접근 시 `get_region_info()`로 capacity 구축 + `_sync_population()` 호출
- **초기 인구 스캔**: `get_units_at_location()`으로 모든 location 인구 카운트 (게임 시작 시 on_reach 미발생 보정)
- **자정 동기화**: `subscribe_time_elapsed(1시간)` → 매일 00:00에 전체 인구 재스캔 (drift 보정)
- **챕터 전환**: `reset()` 함수로 상태 초기화 → 다음 접근 시 재초기화 (아래 "챕터 전환 대응" 참조)

### Python API

```python
import congestion

congestion.get_congestion(region_id, location_id)  # → float (1.0=정상, 2.0=2배 혼잡)
congestion.get_population(region_id, location_id)   # → int (현재 인구)
congestion.get_capacity(region_id, location_id)     # → int (수용력)
```

**주의**: 초기화 완료 후 미등록 location 조회 시 `KeyError` 발생 (데이터 누락 버그 조기 감지)

### UI 표시

`ui.get_time_weather_text()`에서 혼잡 시에만 표시:
```
1년 4월 1일 (수) 20:00 / 흐림 12℃ 습도50% 혼잡x2.0
```

---

## 챕터 전환과 환경 시스템 리셋

온도/습도/혼잡도/소리 시스템은 `get_region_info()`로 lazy init됩니다.
챕터 전환 시 location 데이터가 바뀌므로 재초기화가 필요합니다.

### 문제

```
load_chapter("chapter_0") → 4개 location으로 humidity 초기화
load_chapter("chapter_1") → 35+ location 추가
→ humidity._initialized = True → 새 location 미등록 → get_humidity() 실패
```

### 해결: reset() 패턴

`chapters/__init__.py`의 `load_chapter()`에서 자동 호출:

```python
# load_chapter() step 2.1
import temperature, humidity, congestion, sound, garden
temperature.reset()
humidity.reset()
congestion.reset()
sound.reset()
garden.reset()
```

각 모듈의 `reset()`: `_initialized = False` + 데이터 dict 초기화 → 다음 접근 시 재초기화.

### 대상 모듈

| 모듈 | reset() 대상 | 비고 |
|------|-------------|------|
| `temperature.py` | temps, adjacency, heat_sources, indoor | 열원은 챕터 초기화에서 재등록 |
| `humidity.py` | humidity, indoor, intensity, last_weather | |
| `congestion.py` | capacity, population, last_sync_day | 재초기화 시 인구 재스캔 |
| `sound.py` | adjacency, location_info | hearing/heard_events는 유지 |
| `garden.py` | _registered_gardens | GardenBed.instantiate()에서 재등록 |
| `pollution.py` | register_location() 명시적 호출 | lazy init 아님, reset 불필요 |

---

## 소리 전파 시스템 (Sound System)

> `sound.py` — 순수 Python, C# 변경 없음

캐릭터 중심 소리 전파: `emit_sound()` → BFS 전파 → 청력별 필터 → heard 리스트.

### 소리 타입 및 카테고리

| 카테고리 | 소리 타입 | 기본 강도 |
|---------|----------|----------|
| 전투 | combat(80), scream(100), gunshot(120) | 높음 |
| 이동 | footstep(20), footstep_run(40) | 낮음 |
| 작업 | chop(50), cooking(10), splash(25) | 중간 |
| 자연 | animal(60) | 중간 |
| 사고 | crash(70) | 중간 |
| 생활 | door(30), talk(15) | 낮음 |
| 친밀 | moan(20) | 낮음 |

카테고리는 `SOUND_CATEGORIES` dict에 정의. NPC 리액션 디스패치용 (예: "전투" 소리 → 도망).

### 감쇠 모델

```
attenuated = intensity / (1 + distance / ATTENUATION_HALF)
```
- `ATTENUATION_HALF = 500` (이 거리에서 강도 절반)
- 실내↔실외 경계: `INDOOR_BOUNDARY_FACTOR = 0.7` (30% 추가 감쇠)

### 청력

| 청력 | threshold |
|------|-----------|
| keen | 5 |
| normal | 15 |
| dull | 30 |

### Python API

```python
import sound

sound.emit_sound(source_id, "combat")                    # 소리 발생 + BFS 전파
sound.emit_sound(source_id, "moan", intensity=50)        # 강도 지정
sound.register_hearing(unit_id, "normal")                 # 청력 등록
sound.get_heard(unit_id)                                  # → [SoundEvent, ...]
sound.get_heard_by_category(unit_id, "전투")              # → 카테고리 필터링
sound.get_heard_texts(unit_id)                            # → ["어딘가에서 전투 소리가...", ...]
sound.flush()                                             # step 종료 시 초기화
```

`SoundEvent` 속성: `sound_type`, `category`, `intensity`, `source_id`, `source_location`, `distance`, `hops`

---

## 텃밭 시스템 (Garden System)

> `garden.py` + `assets/objects/garden.py` — 순수 Python, C# 변경 없음

텃밭(GardenBed)에 씨앗을 심고, 수분/비료를 관리하여 작물을 수확하는 시스템.

### 텃밭 구조

| Prop | 범위 | 설명 |
|------|------|------|
| `이랑수` | 정수 (기본 4) | 이랑 개수 |
| `수분` | 0-100 | 텃밭 수분 (공유, 시간당 -3 감소) |
| `비료` | 0-100 | 텃밭 비료 (공유, 시간당 -2 감소) |
| `씨앗:N` | 0-5 | N번째 이랑 씨앗 코드 (0=비어있음) |
| `성장:N` | 0-100 | N번째 이랑 성장도 (100=수확 가능) |

### 씨앗 레지스트리 (SEED_REGISTRY)

| 코드 | 씨앗 | 수확물 | 성장/시간 | ~소요시간 | 수확량 | 씨앗 확률 |
|------|------|--------|-----------|-----------|--------|-----------|
| 1 | 감자 씨앗 | 감자 | 3 | ~34h | 2-4개 | 30% |
| 2 | 토마토 씨앗 | 토마토 | 2 | ~50h | 3-5개 | 25% |
| 3 | 당근 씨앗 | 당근 | 4 | ~25h | 2-3개 | 20% |
| 4 | 약초 씨앗 | 약초(기존) | 3 | ~34h | 1-3개 | 35% |
| 5 | 양배추 씨앗 | 양배추 | 2 | ~50h | 1-2개 | 40% |

### 성장 수식 (매시간)

```
if 수분 >= 10:
    fertilizer_bonus = 1.0 + 비료 / 100.0   # 1.0 ~ 2.0
    성장 += base_rate × fertilizer_bonus
    수분 -= 3   # 수분 감소
    비료 -= 2   # 비료 감소

if 비 오는 중:
    rain_amount = {"가랑비": 5, "소나기": 15, "폭우": 25}
    수분 = min(100, 수분 + rain_amount)
```

- 비료 100일 때: 성장속도 2배 (소요시간 절반)
- 수분 < 10: 성장 정지

### 물 아이템

| 아이템 | unique_id | 용량 | 효과 |
|--------|-----------|------|------|
| 물뿌리개 | watering_can | 3회 | 수분 +20 |
| 물통 | water_bucket | 5회 | 수분 +20 |
| 간이 물병 | simple_water_bottle | 2회 | 수분 +20 |

- Prop `물:양`: 0=비어있음, 1~N=남은 횟수
- 싱크대/세면대/수도꼭지에서 "물 받기" → 용량만큼 충전
- 텃밭 "물 주기" → 횟수 -1, 수분 +20
- "물 마시기" → 횟수 -1, 포만감 +5

### 플레이어 액션

| 액션 | 설명 | 소요 시간 |
|------|------|-----------|
| 살펴보기 | 수분/비료/이랑 상태 표시 | - |
| 씨 심기 | 씨앗 선택 → 이랑 선택 → 씨앗 소비 | 10분 |
| 물 주기 | 물 아이템 선택 → 수분 +20, 물 -1 | 10분 |
| 비료 주기 | 비료 아이템 소비 → 비료 +30 | 10분 |
| 수확하기 | 성장 100인 이랑 일괄 수확 | 20분 |
| 식물 제거 | 이랑 선택 → 식물 제거 (반환 없음) | 5분 |

### NPC 정원 활동

`handle_garden()` — 4-phase 핸들러:

```
idle → going_to_garden → working ↔ storing_harvest → going_to_garden
```

- **working 우선순위**: 수확 → 물주기 → 씨 심기
- **수확 후**: 음식 저장소(kitchen_fridge)로 이동하여 보관
- **씨 심기**: NPC 인벤토리에 씨앗이 있을 때만 (수확 시 seed_chance로 획득)
- 밀라 봄 스케줄: `{"activity": "정원", ...}` (13:00~15:00, 앞마당)
- 유키 스케줄: `{"activity": "정원", ...}` (13:00~15:00, 은신처 텃밭)

### Python API

```python
import garden

garden.SEED_REGISTRY              # 씨앗 코드 → 정보
garden.SEED_CODE_MAP              # seed_unique_id → 코드 역매핑
garden.get_seed_name(code)        # 코드 → 이름
garden.get_growth_stage_text(g)   # 성장도 → "새싹"/"자라는 중"/...
garden.get_moisture_text(m)       # 수분 → "메마름"/"건조"/...
garden.do_harvest(inst, fi, pid)  # 수확 실행 → {crop_name, crop_count, seed_name, seed_count}
garden.register_garden(inst_id)   # 텃밭 등록
garden.reset()                    # 챕터 전환용
```

### 챕터 전환 대응

`reset()` 함수로 상태 초기화. `chapters/__init__.py`의 `load_chapter()`에서 자동 호출.

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
