# 조명 시스템 (Lighting System)

> Location 밝기 계산 및 조명 오브젝트 관리

---

## 1. 개요

### 1.1 밝기 계층

```
Region (시간대별 기본 밝기)
  └─ Location
       ├─ 실외: Region 밝기 상속
       └─ 실내: max(창문, 조명, 휴대 광원)
```

### 1.2 밝기 범위

| 값 | 상태 | 은신 효과 |
|----|------|----------|
| 1.0 | 대낮 | 발각 쉬움 |
| 0.8 | 밝음 | - |
| 0.5 | 보통 | - |
| 0.2 | 어두움 | 발각 어려움 |
| 0.0 | 암흑 | 거의 안 보임 |

---

## 2. Region 밝기 (시간대별)

### 2.1 야외 기본 밝기

| 시간대 | 시간 | 밝기 |
|--------|------|------|
| 새벽 | 05:00~07:00 | 0.3 |
| 아침 | 07:00~09:00 | 0.7 |
| 낮 | 09:00~17:00 | 1.0 |
| 저녁 | 17:00~19:00 | 0.7 |
| 황혼 | 19:00~21:00 | 0.3 |
| 밤 | 21:00~05:00 | 0.1 |

### 2.2 날씨 보정

| 날씨 | 밝기 계수 |
|------|----------|
| 맑음 | 1.0 |
| 흐림 | 0.7 |
| 비 | 0.5 |
| 폭풍 | 0.3 |

```python
region_brightness = base_brightness * weather_modifier
```

---

## 3. Location 밝기 계산

### 3.1 실외 Location

```python
def get_outdoor_brightness(region):
    return region.get_brightness()  # 시간대 × 날씨
```

### 3.2 실내 Location

```python
def get_indoor_brightness(region, location, player):
    light_sources = []

    # 1. 창문 (Region 밝기 전달)
    for obj in location.objects:
        if obj.has_prop("light:window"):
            light_sources.append(region.get_brightness())

    # 2. 고정 조명 (on/off)
    for obj in location.objects:
        if obj.get_prop("light:on") == 1:
            light_sources.append(LIGHT_VALUES[obj.light_type])

    # 3. 휴대 광원 (플레이어 장비)
    portable_light = get_player_portable_light(player)
    if portable_light > 0:
        light_sources.append(portable_light)

    return max(light_sources) if light_sources else 0.0
```

### 3.3 Location 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `indoor` | bool | 실내 여부 (기본: False) |
| `base_light` | float | 기본 밝기 (조명 없을 때, 기본: 0.0) |

---

## 4. 조명 오브젝트

### 4.1 고정 조명

| 타입 | 밝기 | on/off | Props |
|------|------|--------|-------|
| 창문 | Region 연동 | - | `light:window=1` |
| 형광등 | 0.8 | O | `light:on=0/1`, `light:value=0.8` |
| 전등 | 0.5 | O | `light:on=0/1`, `light:value=0.5` |
| 촛불 | 0.3 | O | `light:on=0/1`, `light:value=0.3` |
| 벽난로 | 0.4 | O | `light:on=0/1`, `light:value=0.4` |

### 4.2 휴대 광원 (장비 가능)

| 아이템 | 밝기 | 장비 슬롯 | 비고 |
|--------|------|----------|------|
| 랜턴 | 0.4 | 손/허리 | on/off 가능 |
| 횃불 | 0.5 | 손 | 시간 지나면 소진 |
| 발광석 | 0.2 | 목걸이/손 | 영구 |

> **은신 해제**: 휴대 광원을 켜면 은신 상태가 자동 해제됩니다. 어둠 속에서 숨으려면 광원을 꺼야 합니다.

### 4.3 휴대 광원 Props

```python
# 아이템 props
light:portable = 1     # 휴대 가능 광원
light:value = 0.4      # 밝기
light:on = 1           # 켜짐 상태

# 플레이어 장비 확인
def get_player_portable_light(player):
    for equipped_item in player.equipped_items:
        if equipped_item.get_prop("light:portable") == 1:
            if equipped_item.get_prop("light:on") == 1:
                return equipped_item.get_prop("light:value")
    return 0.0
```

---

## 5. 조명 조작

### 5.1 고정 조명 on/off

```python
# 오브젝트 액션
actions = ["call:toggle_light:불 켜기/끄기"]

def toggle_light(self, player_id):
    current = morld.get_unit_prop(self.unit_id, "light:on") or 0
    new_value = 0 if current == 1 else 1
    morld.set_unit_prop(self.unit_id, "light:on", new_value)

    state = "켰다" if new_value == 1 else "껐다"
    yield ui.dialog(f"{self.name}을(를) {state}.")
```

### 5.2 휴대 광원 on/off

```python
# 인벤토리/장비 메뉴에서
def toggle_lantern(item_id):
    current = morld.get_unit_prop(item_id, "light:on") or 0
    new_value = 0 if current == 1 else 1
    morld.set_unit_prop(item_id, "light:on", new_value)
```

---

## 6. UI 표시

### 6.1 Header 밝기 표시

```
[저택 - 거실] [밝음]       # 0.6~1.0
[저택 - 거실] [어두움]     # 0.2~0.5
[저택 - 거실] [암흑]       # 0.0~0.1
```

### 6.2 암흑 시 제한

| 밝기 | 효과 |
|------|------|
| 0.0 | 이동 가능, 오브젝트/NPC 인식 불가 |
| 0.1 | 근접 오브젝트만 인식 |
| 0.2+ | 정상 인식 |

---

## 7. 은신 시스템 연동

### 7.1 발각 확률 계산

```python
# stealth.md 참조
detection_rate = 밝기 × 자세계수 × 엄폐계수 × NPC감지력
```

### 7.2 밝기별 발각 예시

| 상황 | 밝기 | 자세 (crouch 0.5) | 발각률 |
|------|------|-------------------|--------|
| 대낮 야외 | 1.0 | 0.5 | 50% |
| 형광등 실내 | 0.8 | 0.5 | 40% |
| 랜턴만 | 0.4 | 0.5 | 20% |
| 암흑 | 0.0 | 0.5 | 0% |

---

## 8. 구현 순서

1. **Location indoor 속성** - 실내/실외 구분
2. **Region 시간대 밝기** - 시간 시스템 연동
3. **창문 오브젝트** - Region 밝기 전달
4. **고정 조명** - on/off 기능
5. **휴대 광원** - 장비 시스템 연동
6. **UI 표시** - Header 밝기 표시
7. **은신 연동** - 발각 확률 계산

---

## 9. 관련 문서

- [stealth.md](stealth.md) - 은신 시스템 (발각 공식)
- [terrain_property.md](terrain_property.md) - 환경 속성
- [system-gameplay.md](system-gameplay.md) - 장비 시스템

