# 지형 속성 시스템 설계

> **v0.2.2에서 온도 시스템 구현 완료.**
>
> **구현된 항목:**
> - Location별 온도 시뮬레이션 → `temperature.py`
> - 계절/날씨/시간대별 실외 온도 (고정 테이블)
> - 실내 온도 평활화 (인접 가중 평균 + 수렴률 0.3)
> - 열원 BFS 확산 (벽난로 등, light:on 공유)
> - 헤더 UI에 온도 표시 (`22℃`)
>
> **미구현 항목:** 습도, 풍속, 달의 위상, 조도(기존 lighting.py와 별도), 체감 온도
>
> 온도 시스템 상세는 [system-gameplay.md#온도-시스템](system-gameplay.md#온도-시스템-temperature-system) 참조.

## 개요

지형 속성은 각 Location이 가지는 **환경 시뮬레이션 데이터**입니다.
날씨, 시간, 계절, 설치된 장치 등에 따라 동적으로 변화하며,
연결된 실내 공간끼리는 일부 속성을 공유합니다.

---

## Region 레벨 환경 데이터

Region은 해당 지역의 **천체/날씨 정보**를 관리합니다.
Location은 Region의 데이터를 참조하여 지형 속성을 계산합니다.

### Region 환경 속성

| 속성 | 키 | 설명 | 예시 |
|------|-----|------|------|
| 날씨 | `CurrentWeather` | 현재 날씨 | "맑음", "흐림", "비", "눈" |
| 계절 | `CurrentSeason` | 현재 계절 | "봄", "여름", "가을", "겨울" |
| 달의 위상 | `MoonPhase` | 0~27 (28일 주기) | 0=신월, 14=보름달 |

### C# Region 확장

```csharp
public class Region
{
    // 기존 속성
    public string CurrentWeather { get; set; } = "맑음";

    // 추가 속성
    public string CurrentSeason { get; set; } = "봄";
    public int MoonPhase { get; set; } = 0;  // 0~27

    /// <summary>
    /// 날씨에 따른 구름량 (0~100%)
    /// </summary>
    public int GetCloudCover()
    {
        return CurrentWeather switch
        {
            "맑음" => 0,
            "흐림" => 70,
            "비" => 90,
            "눈" => 80,
            _ => 0
        };
    }

    /// <summary>
    /// 달빛 강도 (위상 기반, 0~100%)
    /// </summary>
    public int GetMoonlightIntensity()
    {
        // 보름달(14)에서 최대, 신월(0, 28)에서 최소
        var distanceFromFull = Math.Abs(14 - MoonPhase);
        return 100 - (distanceFromFull * 100 / 14);
    }
}
```

### Python Region 확장

```python
# world.py에서 Region 등록 시

morld.add_region(
    region_id=0,
    name="숲속 저택",
    weather="맑음",
    season="봄",
    moon_phase=14  # 보름달
)

# 조회
weather = morld.get_region_weather(region_id)
season = morld.get_region_season(region_id)
moon_phase = morld.get_region_moon_phase(region_id)

# 설정
morld.set_region_weather(region_id, "비")
morld.set_region_moon_phase(region_id, 7)  # 상현달
```

### 시간 경과에 따른 자동 업데이트

```python
def on_day_passed():
    """하루가 지날 때마다 호출"""
    for region_id in morld.get_all_region_ids():
        # 달의 위상 진행
        phase = morld.get_region_moon_phase(region_id)
        morld.set_region_moon_phase(region_id, (phase + 1) % 28)

        # 날씨 변화 (확률 기반)
        maybe_change_weather(region_id)
```

---

## Location 속성 종류

### 1. 실외 전용 속성

| 속성 | 키 | 단위 | 범위 | 영향 요소 |
|------|-----|------|------|----------|
| 일조량 | `sunlight` | % | 0~100 | 시간대, Region.날씨 |
| 월조량 | `moonlight` | % | 0~100 | 시간대(밤), Region.달의위상 |
| 습도 | `humidity` | % | 0~100 | Region.날씨, 지형 특성 |

### 속성 계산 (Region 참조)

```python
def calculate_sunlight(region_id, location_id):
    """일조량 계산 - Region 날씨 + 시간대"""
    hour = morld.get_game_time() // 60

    # 기본 일조량 (시간대)
    if 6 <= hour < 18:  # 낮
        base = 100 - abs(12 - hour) * 8  # 정오에 최대
    else:
        base = 0  # 밤

    # Region 날씨 영향
    cloud_cover = morld.get_region_cloud_cover(region_id)
    return max(0, base - cloud_cover)

def calculate_moonlight(region_id, location_id):
    """월조량 계산 - Region 달의 위상 + 시간대"""
    hour = morld.get_game_time() // 60

    if 6 <= hour < 18:  # 낮이면 월광 없음
        return 0

    # Region 달빛 강도
    moon_intensity = morld.get_region_moonlight_intensity(region_id)

    # 구름 영향
    cloud_cover = morld.get_region_cloud_cover(region_id)
    return max(0, moon_intensity - cloud_cover // 2)

def calculate_humidity(region_id, location_id):
    """습도 계산 - Region 날씨 기반"""
    weather = morld.get_region_weather(region_id)

    base_humidity = {
        "맑음": 40,
        "흐림": 60,
        "비": 90,
        "눈": 70,
    }.get(weather, 50)

    return base_humidity
```

### 2. 실내 전용 속성

| 속성 | 키 | 단위 | 범위 | 영향 요소 |
|------|-----|------|------|----------|
| 전기 | `electricity` | bool | 0/1 | 발전기, 전선 연결 |
| 조명 | `lighting` | % | 0~100 | 전기 + 전등, 촛불 등 |

### 3. 공통 속성

| 속성 | 키 | 단위 | 범위 | 영향 요소 |
|------|-----|------|------|----------|
| 온도 | `temperature` | ℃ | -30~50 | 계절, 날씨, 난로, 인접 공간 |

---

## 달의 위상 (Moon Phase)

```
신월(0) → 상현달(7) → 보름달(14) → 하현달(21) → 신월(28)
```

| 위상 | 일수 | moonlight |
|------|------|-----------|
| 신월 | 0~3 | 0% |
| 초승달 | 4~6 | 15% |
| 상현달 | 7~10 | 40% |
| 철월 | 11~13 | 70% |
| 보름달 | 14~17 | 100% |
| 철월 | 18~20 | 70% |
| 하현달 | 21~24 | 40% |
| 그믐달 | 25~27 | 15% |

---

## 실내 공간 연결 (Indoor Cluster)

### 개념

실내 Location들이 Gate로 연결되어 있으면 **같은 건물/구역**으로 취급합니다.
실외 Location을 만나면 연결이 끊어집니다.

```
실내 A ←→ 실내 B ←→ 실외 ←→ 실내 C

[클러스터 1: A, B] [클러스터 2: C]
```

### 공유 속성

| 속성 | 공유 방식 |
|------|----------|
| 전기 | 클러스터 내 하나라도 발전기가 있으면 전체 공급 |
| 온도 | 인접 Location과 평균 수렴 (열 전도) |

### 온도 전파 알고리즘

```python
def propagate_temperature(location):
    """인접 Location과 온도 평균화"""
    my_temp = location.temperature
    neighbors = get_connected_indoor_locations(location)

    if not neighbors:
        return

    # 열원이 있으면 열원 온도 유지
    if has_heat_source(location):
        return

    # 인접 온도 평균으로 수렴 (느리게)
    avg_temp = sum(n.temperature for n in neighbors) / len(neighbors)
    location.temperature += (avg_temp - my_temp) * 0.1  # 10%씩 수렴
```

### 온도 영향 요소

| 요소 | 효과 | 비고 |
|------|------|------|
| 난로 (켜짐) | +15℃ | 해당 Location만 |
| 에어컨 | 목표 온도로 조절 | 전기 필요 |
| 실외 연결 | 외부 온도 영향 | 문/창문 열림 시 |
| Region.계절 | 기본 온도 결정 | 봄 15℃, 여름 28℃, 가을 12℃, 겨울 -5℃ |

### 기본 온도 계산 (Region 계절 기반)

```python
def get_base_temperature(region_id):
    """Region 계절에 따른 기본 온도"""
    season = morld.get_region_season(region_id)
    weather = morld.get_region_weather(region_id)

    season_temp = {
        "봄": 15,
        "여름": 28,
        "가을": 12,
        "겨울": -5,
    }.get(season, 15)

    # 날씨 보정
    weather_modifier = {
        "맑음": 2,    # 햇빛으로 약간 따뜻
        "흐림": 0,
        "비": -3,     # 비 오면 쌀쌀
        "눈": -5,     # 눈 오면 더 추움
    }.get(weather, 0)

    return season_temp + weather_modifier
```

---

## 데이터 구조

### Python Location 확장

```python
class Location(Asset):
    # 기존 속성
    is_indoor: bool = True

    # 지형 속성 (동적)
    properties: dict = None  # 런타임에 설정

    # 속성 기본값 (클래스별 오버라이드 가능)
    DEFAULT_PROPERTIES = {
        "temperature": None,  # None = 외부/계절 기준
    }

    # 열원/전원 장치
    heat_sources: list = []  # ["fireplace", "stove"]
    power_sources: list = []  # ["generator", "solar_panel"]
```

### C# Location 확장

```csharp
public class Location
{
    // 기존 속성...

    /// <summary>
    /// 지형 속성 (동적 환경 데이터)
    /// </summary>
    public Dictionary<string, float> Properties { get; set; } = new();
}
```

### 속성 키 네이밍

```
terrain:{location_global_id}:{property_key}
```

예시:
- `terrain:0:5:temperature` → Region 0, Location 5의 온도
- `terrain:0:5:electricity` → Region 0, Location 5의 전기 공급 상태

---

## 시스템 구현

### TerrainPropertySystem (Logic System)

```csharp
public class TerrainPropertySystem
{
    /// <summary>
    /// 매 시간(게임 내 1시간) 호출
    /// </summary>
    public void UpdateProperties(int elapsedMinutes)
    {
        // 1. 실외 속성 업데이트 (일조량, 월조량, 습도)
        UpdateOutdoorProperties();

        // 2. 실내 클러스터 계산
        var clusters = CalculateIndoorClusters();

        // 3. 클러스터별 전기 공급
        UpdateElectricity(clusters);

        // 4. 온도 전파
        PropagateTemperature();

        // 5. 조명 계산
        UpdateLighting();
    }
}
```

### Python API

```python
import morld

# 속성 조회
temp = morld.get_terrain_property(region_id, location_id, "temperature")
electricity = morld.get_terrain_property(region_id, location_id, "electricity")

# 속성 설정 (장치 효과 등)
morld.set_terrain_property(region_id, location_id, "temperature", 25)

# 열원/전원 등록
morld.add_heat_source(region_id, location_id, "fireplace", heat_output=15)
morld.remove_heat_source(region_id, location_id, "fireplace")

# 실내 클러스터 조회
cluster = morld.get_indoor_cluster(region_id, location_id)
# [LocationRef(0, 5), LocationRef(0, 6), LocationRef(0, 7)]
```

---

## 활용 예시

### 1. 전등 켜기

```python
class LightSwitch(Object):
    def toggle(self):
        loc = morld.get_unit_location(morld.get_player_id())
        electricity = morld.get_terrain_property(loc[0], loc[1], "electricity")

        if not electricity:
            yield morld.dialog("전기가 안 들어온다...")
            return

        current = morld.get_terrain_property(loc[0], loc[1], "lighting")
        if current > 0:
            morld.set_terrain_property(loc[0], loc[1], "lighting", 0)
            yield morld.dialog("전등을 껐다.")
        else:
            morld.set_terrain_property(loc[0], loc[1], "lighting", 100)
            yield morld.dialog("전등을 켰다.")
```

### 2. 난로 피우기

```python
class Fireplace(Object):
    def light(self):
        if not morld.has_item(morld.get_player_id(), "firewood"):
            yield morld.dialog("땔감이 필요하다.")
            return

        morld.lost_item(morld.get_player_id(), "firewood", 1)
        loc = morld.get_unit_location(morld.get_player_id())
        morld.add_heat_source(loc[0], loc[1], "fireplace", heat_output=15)
        yield morld.dialog("난로에 불을 피웠다. 따뜻해진다...")
```

### 3. 날씨/시간에 따른 묘사

```python
class ForestClearing(Location):
    def get_describe_text(self):
        sunlight = morld.get_terrain_property(self.region_id, self.location_id, "sunlight")

        if sunlight >= 80:
            return "햇살이 나뭇잎 사이로 쏟아진다."
        elif sunlight >= 40:
            return "흐린 하늘 아래 숲이 고요하다."
        else:
            moonlight = morld.get_terrain_property(self.region_id, self.location_id, "moonlight")
            if moonlight >= 70:
                return "달빛이 숲을 은빛으로 물들인다."
            else:
                return "어둠 속에 나무들의 실루엣만 보인다."
```

### 4. 작물 성장

```python
def check_crop_growth(crop_object):
    """작물 성장 체크 (일조량 기반)"""
    loc = morld.get_object_location(crop_object.instance_id)
    sunlight = morld.get_terrain_property(loc[0], loc[1], "sunlight")
    humidity = morld.get_terrain_property(loc[0], loc[1], "humidity")

    # 일조량 + 습도 조건 충족 시 성장
    if sunlight >= 50 and 30 <= humidity <= 70:
        crop_object.growth += 1
```

---

## 파일 구조

```
scenarios/scenario02/python/
├─ terrain_property/
│   ├─ __init__.py          # API 래퍼
│   ├─ calculator.py        # 속성 계산 로직
│   ├─ cluster.py           # 실내 클러스터 관리
│   └─ devices.py           # 열원/전원 장치 관리
scripts/
├─ system/
│   └─ terrain_property_system.cs  # Logic System
├─ morld/
│   └─ terrain/
│       └─ Location.cs      # Properties 필드 추가
```

---

## 구현 순서

1. **Location.Properties 필드 추가** (C#, Python)
   - 기본 속성 딕셔너리

2. **실외 속성 계산**
   - 일조량: 시간대 + 날씨
   - 월조량: 밤 시간 + 달의 위상
   - 습도: 날씨 (비/눈)

3. **실내 클러스터 계산**
   - BFS/DFS로 연결된 실내 Location 탐색

4. **전기 시스템**
   - 발전기/태양광 → 클러스터 전체 공급

5. **온도 시스템**
   - 계절 기본 온도
   - 열원 효과
   - 인접 전파

6. **조명 시스템**
   - 전기 + 전등/촛불

7. **Python API**
   - get/set_terrain_property
   - 장치 등록/해제

---

## 참고: 실외-실내 온도 영향

실외와 연결된 실내는 외부 온도의 영향을 받습니다.

```
실외 (0℃) ←→ 실내 A (난로 +15℃) ←→ 실내 B

계산:
- 실내 A: 0 + 15 = 15℃ (난로 효과)
- 실내 B: (15 + 0) / 2 = 7.5℃ (실내 A와 실외 평균)
```

문/창문 열림 상태에 따라 외부 영향도를 조절할 수 있습니다:
- 닫힘: 외부 영향 20%
- 열림: 외부 영향 80%

---

## UI 표시

### Location UI에 환경 정보 표시

현재 위치의 지형 속성을 Location UI (헤더/상황 텍스트)에 표시합니다.

**실외 표시 예시:**
```
[숲 입구] 맑음, 17℃
햇살이 따사롭다. (일조량 85%)
```

**실내 표시 예시:**
```
[거실] 실내, 22℃
난로가 타닥거리며 타오르고 있다.
```

**밤 실외 표시 예시:**
```
[숲 입구] 맑음, 8℃
보름달이 숲을 환하게 비춘다. (월조량 100%)
```

### Python ui.py 확장

```python
def get_location_environment_text(region_id, location_id):
    """Location 환경 정보 텍스트 생성"""
    location = morld.get_location(region_id, location_id)

    if location.is_indoor:
        return get_indoor_environment_text(region_id, location_id)
    else:
        return get_outdoor_environment_text(region_id, location_id)

def get_outdoor_environment_text(region_id, location_id):
    """실외 환경 텍스트"""
    weather = morld.get_region_weather(region_id)
    temp = morld.get_terrain_property(region_id, location_id, "temperature")
    sunlight = morld.get_terrain_property(region_id, location_id, "sunlight")
    moonlight = morld.get_terrain_property(region_id, location_id, "moonlight")

    # 헤더: 날씨, 온도
    header = f"{weather}, {temp:.0f}℃"

    # 상세: 일조량 또는 월조량
    if sunlight > 0:
        detail = f"일조량 {sunlight:.0f}%"
    elif moonlight > 0:
        phase_name = get_moon_phase_name(morld.get_region_moon_phase(region_id))
        detail = f"{phase_name}, 월조량 {moonlight:.0f}%"
    else:
        detail = "어둠"

    return header, detail

def get_indoor_environment_text(region_id, location_id):
    """실내 환경 텍스트"""
    temp = morld.get_terrain_property(region_id, location_id, "temperature")
    electricity = morld.get_terrain_property(region_id, location_id, "electricity")
    lighting = morld.get_terrain_property(region_id, location_id, "lighting")

    # 헤더: 실내, 온도
    header = f"실내, {temp:.0f}℃"

    # 상세: 전기/조명 상태
    details = []
    if electricity:
        details.append("전기 공급 중")
    if lighting > 0:
        details.append(f"조명 {lighting:.0f}%")

    detail = ", ".join(details) if details else "어둡다"

    return header, detail
```

### 헤더 통합

기존 `ui.py`의 `get_header()`에서 환경 정보를 포함:

```python
def get_header():
    """헤더 텍스트 생성"""
    if not _show_header:
        return ""

    player_id = morld.get_player_id()
    region_id, location_id = morld.get_unit_location(player_id)
    location_name = morld.get_location_name(region_id, location_id)

    # 환경 정보
    env_header, env_detail = get_location_environment_text(region_id, location_id)

    # 시간 정보
    time_str = get_time_string()

    return f"[b][{location_name}][/b] {env_header}\n{time_str}\n{env_detail}"
```

### 표시 항목 요약

| 위치 | 표시 항목 |
|------|----------|
| 실외 (낮) | 날씨, 온도, 일조량 |
| 실외 (밤) | 날씨, 온도, 달의 위상, 월조량 |
| 실내 | 온도, 전기 상태, 조명 |

---

## 지형 효과 (Terrain Effects)

### 개요

특정 Location에 **지형 효과**를 부여하여 해당 위치에 있는 캐릭터에게 버프/디버프를 적용합니다.
시간 경과에 따라 효과가 누적되며, 생존 시스템과 연동됩니다.

### 효과 종류

| 효과 | 키 | 영향 | 예시 |
|------|-----|------|------|
| 방사능 | `radiation` | 체력 감소 | 폐허, 오염 지역 |
| 독성 | `toxic` | 체력 감소, 상태이상 | 독늪, 가스 지역 |
| 축복 | `blessed` | 체력 회복, 포만감 유지 | 신전, 성지 |
| 저주 | `cursed` | 체력 감소, 불운 | 저주받은 유적 |
| 치유 | `healing` | 체력 회복 | 온천, 치유의 샘 |
| 마나 충전 | `mana_regen` | 마나 회복 | 마법의 숲, 결계 |
| 기 고갈 | `mana_drain` | 마나 감소 | 봉인된 장소 |
| 포만감 억제 | `satiety_preserve` | 포만감 감소 없음 | 신성한 장소 |
| 굶주림 | `starvation` | 포만감 빠르게 감소 | 황무지 |

### 효과 강도

| 강도 | 값 | 설명 |
|------|-----|------|
| 약함 | 1 | 1시간당 1 변화 |
| 보통 | 2 | 1시간당 2 변화 |
| 강함 | 3 | 1시간당 3 변화 |
| 치명적 | 5 | 1시간당 5 변화 |

### Location 효과 정의

```python
class RadioactiveRuins(Location):
    unique_id = "radioactive_ruins"
    name = "방사능 폐허"
    is_indoor = False

    # 지형 효과
    terrain_effects = {
        "radiation": 2,  # 1시간당 체력 -2
    }

class HealingSpring(Location):
    unique_id = "healing_spring"
    name = "치유의 샘"
    is_indoor = False

    terrain_effects = {
        "healing": 3,           # 1시간당 체력 +3
        "satiety_preserve": 1,  # 포만감 감소 없음
    }

class CursedCrypt(Location):
    unique_id = "cursed_crypt"
    name = "저주받은 지하묘지"
    is_indoor = True

    terrain_effects = {
        "cursed": 2,      # 1시간당 체력 -2
        "mana_drain": 1,  # 1시간당 마나 -1
    }
```

### 효과 처리 시스템

```python
# terrain_property/effects.py

EFFECT_HANDLERS = {
    "radiation": lambda unit_id, intensity, hours:
        survival.add_health(unit_id, -intensity * hours),

    "toxic": lambda unit_id, intensity, hours:
        (survival.add_health(unit_id, -intensity * hours),
         maybe_apply_poison(unit_id, intensity)),

    "blessed": lambda unit_id, intensity, hours:
        (survival.add_health(unit_id, intensity * hours),
         survival.preserve_satiety(unit_id, hours)),

    "cursed": lambda unit_id, intensity, hours:
        survival.add_health(unit_id, -intensity * hours),

    "healing": lambda unit_id, intensity, hours:
        survival.add_health(unit_id, intensity * hours),

    "mana_regen": lambda unit_id, intensity, hours:
        morld.add_unit_prop(unit_id, "마나", intensity * hours),

    "mana_drain": lambda unit_id, intensity, hours:
        morld.add_unit_prop(unit_id, "마나", -intensity * hours),

    "satiety_preserve": lambda unit_id, intensity, hours:
        survival.preserve_satiety(unit_id, hours),

    "starvation": lambda unit_id, intensity, hours:
        survival.add_satiety(unit_id, -intensity * hours),
}

def apply_terrain_effects(unit_id, region_id, location_id, elapsed_hours):
    """Location의 지형 효과를 유닛에게 적용"""
    effects = morld.get_terrain_effects(region_id, location_id)

    for effect_key, intensity in effects.items():
        handler = EFFECT_HANDLERS.get(effect_key)
        if handler:
            handler(unit_id, intensity, elapsed_hours)
```

### 효과 저항

캐릭터/장비의 props로 효과를 감소시킬 수 있습니다.

```python
# 효과 저항 체크
def get_effective_intensity(unit_id, effect_key, base_intensity):
    """저항력을 적용한 실제 효과 강도"""
    resistance_key = f"저항:{effect_key}"
    resistance = morld.get_unit_actual_prop(unit_id, resistance_key) or 0

    # 저항력만큼 강도 감소 (최소 0)
    return max(0, base_intensity - resistance)

# 장비 예시
class HazmatSuit(Item):
    unique_id = "hazmat_suit"
    name = "방호복"
    equip_props = {
        "착용:몸통": 1,
        "저항:radiation": 3,  # 방사능 저항 +3
        "저항:toxic": 2,      # 독성 저항 +2
    }

class BlessedAmulet(Item):
    unique_id = "blessed_amulet"
    name = "축복받은 부적"
    equip_props = {
        "장착:목": 1,
        "저항:cursed": 5,     # 저주 완전 저항
    }
```

### UI 표시 (효과 경고)

위험한 지형 효과가 있으면 UI에 경고를 표시합니다.

```python
def get_terrain_effect_warning(region_id, location_id):
    """지형 효과 경고 텍스트"""
    effects = morld.get_terrain_effects(region_id, location_id)

    warnings = []
    for effect, intensity in effects.items():
        if effect in ["radiation", "toxic", "cursed", "mana_drain", "starvation"]:
            name = EFFECT_NAMES.get(effect, effect)
            warnings.append(f"[color=red]⚠ {name} (강도 {intensity})[/color]")
        elif effect in ["blessed", "healing", "mana_regen", "satiety_preserve"]:
            name = EFFECT_NAMES.get(effect, effect)
            warnings.append(f"[color=green]✦ {name}[/color]")

    return "\n".join(warnings)

EFFECT_NAMES = {
    "radiation": "방사능 오염",
    "toxic": "독성 지역",
    "blessed": "축복받은 땅",
    "cursed": "저주받은 땅",
    "healing": "치유의 기운",
    "mana_regen": "마나 충전",
    "mana_drain": "마나 고갈",
    "satiety_preserve": "풍요의 땅",
    "starvation": "황폐한 땅",
}
```

**표시 예시:**
```
[폐허 지하실] 실내, 15℃
[color=red]⚠ 방사능 오염 (강도 2)[/color]
방호복이 없으면 위험하다.
```

```
[치유의 샘] 맑음, 20℃
[color=green]✦ 치유의 기운[/color]
[color=green]✦ 풍요의 땅[/color]
몸과 마음이 편안해진다.
```

### 일시적 효과 vs 영구적 효과

| 타입 | 설명 | 예시 |
|------|------|------|
| 영구적 | Location에 항상 존재 | 온천, 방사능 지역 |
| 일시적 | 조건에 따라 활성화 | 의식 진행 중인 제단, 마법 발동 중인 결계 |

```python
class RitualAltar(Location):
    unique_id = "ritual_altar"
    name = "의식 제단"

    # 기본 효과 없음
    terrain_effects = {}

    def get_active_effects(self):
        """조건부 효과"""
        if morld.get_prop("altar:ritual_active"):
            return {"blessed": 3, "healing": 2}
        return {}
```
