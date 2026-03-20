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
[사막 - 한낮] [눈부심]     # 1.5+
```

### 6.2 밝기별 제한 및 UI 마스킹

| 밝기 | 레벨 | 효과 | 링크 마스킹 |
|------|------|------|------------|
| 1.5+ | 눈부심 | 시야 제한 | ■ + 밝은 색상 |
| 0.6~1.5 | 밝음 | 정상 | 없음 |
| 0.2~0.6 | 어두움 | 발각 어려움 | 없음 (인프라 예약) |
| 0.0~0.2 | 암흑 | 오브젝트/NPC 인식 불가 | ■ + 어두운 색상 |

### 6.3 링크 마스킹 시스템

암흑/눈부심 환경에서 Situation Focus의 클릭 가능한 링크(토글, 선택지, 액션 등)가 ■■■로 마스킹됨.
마우스 hover 시 원문이 드러남 — "어둠 속에서 더듬어 찾는" 느낌.

- **적용 범위**: Situation Focus만 (Dialog, Inventory 등은 항상 밝게)
- **렌더러 레벨**: GodotRenderer에서 `[url=...]` 태그 내부 텍스트를 ■로 치환
- **hover 연동**: `[url=...]` 태그 자체는 유지 → Godot MetaHoverStarted 이벤트 정상 발생
- **색상**: 암흑=LinkMaskedColor(어둡게), 눈부심=LinkGlareColor(밝게)

```python
# Python override — 마스킹 강제 해제 (프롤로그 등)
ui.set_darkness_masking(False)   # 밝기와 무관하게 마스킹 해제
ui.set_darkness_masking(True)    # 다시 활성화 (기본값)
# ※ 현재 C#에서 미연결 — 필요 시 GetDarknessLevelFromPython()에서 호출 추가
```

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

## 8. NPC 조명 관리 — 구현됨 (v0.2.2)

### 3-phase 시간 패턴

| 시간대 | 동작 | 비고 |
|--------|------|------|
| 06:00~18:00 (주간) | 소등 | 밤새 켜둔 조명 끄기 |
| 18:00~21:00 (저녁) | 점등 | 실내 조명 켜기 |
| 21:00~06:00 (야간) | 소등 | 취침 전 소등 |

열원(`heat:output` prop)은 소등/점등 대상에서 제외 (Fireplace, DrumBath, PortableStove).

### 적극적 관리 (밀라)

`handle_lights_off()` / `handle_lights_on()` — 스케줄 활동으로 거처 내 방을 순회하며 조명 끄기/켜기.
아침 소등(기상 후) + 저녁 점등(18:00 전후) + 밤 소등(취침 전) 3회 순회.

### 소극적 관리 (전체 NPC)

`_check_environment()` — 도착 시 1회 호출. 현재 시간대에 따라 자동으로 조명 토글:
- 점등 시간인데 꺼져있으면 → 첫 번째 조명 1개 켜기
- 소등 시간인데 켜져있으면 → 모든 조명 끄기

---

## 9. 구현 순서

1. **Location indoor 속성** - 실내/실외 구분
2. **Region 시간대 밝기** - 시간 시스템 연동
3. **창문 오브젝트** - Region 밝기 전달
4. **고정 조명** - on/off 기능
5. **휴대 광원** - 장비 시스템 연동
6. **UI 표시** - Header 밝기 표시
7. **은신 연동** - 발각 확률 계산

---

## 10. 관련 문서

- [stealth.md](stealth.md) - 은신 시스템 (발각 공식)
- [terrain_property.md](terrain_property.md) - 환경 속성
- [system-gameplay.md](system-gameplay.md) - 장비 시스템

