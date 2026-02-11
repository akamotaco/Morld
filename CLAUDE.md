# Morld 문서 가이드

> **현재 작업 대상: scenario02**
>
> 이 프로젝트는 여러 시나리오를 지원하지만, 현재 개발 중인 시나리오는 `scenario02`입니다.
> 모든 문서는 scenario02 기준으로 작성되어 있습니다.
>
> - 시나리오 경로: `scenarios/scenario02/`
> - Python 코드: `scenarios/scenario02/python/`
> - 문서: `scenarios/scenario02/docs/`

---

## 필수 문서 (시스템 이해)

| 문서 | 설명 | 줄 수 |
|------|------|-------|
| [system-core.md](scenarios/scenario02/docs/system-core.md) | ECS 아키텍처, 시스템 구조, 챕터 전환 라이프사이클 | ~200 |
| [system-api.md](scenarios/scenario02/docs/system-api.md) | morld Python API, Asset 클래스 | ~150 |
| [dialog.md](scenarios/scenario02/docs/dialog.md) | 대화/리액션/묘사 시스템 (Lines, Rules 등) | ~250 |
| [system-ui.md](scenarios/scenario02/docs/system-ui.md) | TextUI, 토글, 액션 필터링 | ~150 |
| [system-gameplay.md](scenarios/scenario02/docs/system-gameplay.md) | 장비, 생존, 욕구, 연애, 온도, 습도, 혼잡도, 텃밭 등 게임플레이 시스템 | ~850 |

---

## 작업별 참고 문서

### 지형/맵 작업

| 작업 | 참고 문서 |
|------|----------|
| Region/Location/Gate 구조 | [terrain.md](scenarios/scenario02/docs/terrain.md) |
| 맵 구성 (저택, 마을, 숲 등) | [map.md](scenarios/scenario02/docs/map.md) |
| 환경 속성 (온도, 습도, 날씨) | [terrain_property.md](scenarios/scenario02/docs/terrain_property.md) |
| 조명 시스템 (밝기, 광원) | [lighting.md](scenarios/scenario02/docs/lighting.md) |
| 던전 시스템 | [dungeon.md](scenarios/scenario02/docs/dungeon.md) |
| 바닥 오브젝트 | [ground.md](scenarios/scenario02/docs/ground.md) |

### 캐릭터/NPC 작업

| 작업 | 참고 문서 |
|------|----------|
| NPC 대화/리액션/묘사 | [dialog.md](scenarios/scenario02/docs/dialog.md) |
| 애니메이션 연출 (컷씬, 전투) | [system-ui.md#animlog](scenarios/scenario02/docs/system-ui.md#animlog-애니메이션-시퀀스) |
| 자세/착석 시스템 (앉기, 눕기) | [movement-system.md#4](scenarios/scenario02/docs/movement-system.md#4-자세posture-시스템) |
| 은신 시스템 (잠입, 발각) | [stealth.md](scenarios/scenario02/docs/stealth.md) |
| NPC 스케줄/AI/Agent | [schedule.md](scenarios/scenario02/docs/schedule.md) |
| NPC 생활/욕구/자율행동 | [life.md](scenarios/scenario02/docs/life.md) |
| 연애/스킨십 시스템 | [romance.md](scenarios/scenario02/docs/romance.md) |
| 전투 시스템 | [battle.md](scenarios/scenario02/docs/battle.md) |
| 퀘스트 시스템 | [quest.md](scenarios/scenario02/docs/quest.md) |
| 시나리오 설계 (세계관, 캐릭터) | [design.md](scenarios/scenario02/docs/design.md) |

### 아이템 작업

| 작업 | 참고 문서 |
|------|----------|
| 의류/장비 시스템 | [clothes.md](scenarios/scenario02/docs/clothes.md) |
| 음식/요리 시스템 | [food.md](scenarios/scenario02/docs/food.md) |
| 크래프팅 레시피 | [craft.md](scenarios/scenario02/docs/craft.md) |

### 이벤트/시스템 작업

| 작업 | 참고 문서 |
|------|----------|
| 이벤트 시스템 (on_meet, on_reach, on_leave) | [event.md](scenarios/scenario02/docs/event.md) |
| 시간 정지 (Frozen) 상태 | [frozen.md](scenarios/scenario02/docs/frozen.md) |
| 시간 흐름 (자동 시간 흐름) | [time-flow.md](scenarios/scenario02/docs/time-flow.md) |

---

## 문서 구조

```
scenarios/scenario02/docs/
├── system-core.md      # ECS 아키텍처, 프로젝트 구조
├── system-api.md       # morld Python API
├── system-ui.md        # TextUI, 액션 필터링
├── system-gameplay.md  # 장비, 생존, 연애 시스템
├── movement-system.md  # 이동 시스템, 자세/착석
├── stealth.md          # 은신 시스템
├── dialog.md           # 대화/리액션/묘사 시스템
├── design.md           # 시나리오 설계 (세계관, 캐릭터)
├── terrain.md          # 지형 시스템
├── terrain_property.md # 환경 속성
├── lighting.md         # 조명 시스템
├── map.md              # 맵 구성
├── dungeon.md          # 던전 시스템
├── ground.md           # 바닥 오브젝트
├── schedule.md         # NPC 스케줄/AI/Agent
├── life.md             # NPC 생활/욕구/자율행동
├── battle.md           # 전투 시스템
├── romance.md          # 연애 시스템
├── quest.md            # 퀘스트 시스템
├── clothes.md          # 의류/장비
├── food.md             # 음식/요리
├── craft.md            # 크래프팅
├── event.md            # 이벤트 시스템
├── frozen.md           # 시간 정지 상태
└── time-flow.md        # 시간 흐름 시스템
```

---

## 코드 경로 요약

| 구분 | 경로 |
|------|------|
| C# 시스템 | `scripts/system/` |
| C# 데이터 구조 | `scripts/morld/` |
| C# 액션 핸들러 | `scripts/MetaActionHandler/` |
| Python 시나리오 | `scenarios/scenario02/python/` |
| Python Asset 클래스 | `scenarios/scenario02/python/assets/` |
| Python 이벤트 핸들러 | `scenarios/scenario02/python/events/` |
| Python NPC AI | `scenarios/scenario02/python/think/` |
| Python 환경 시스템 | `scenarios/scenario02/python/` (temperature, humidity, congestion, pollution, sound, garden, needs) |

---

## 시나리오03 호환성 고려

> **시스템 수정 시 시나리오03 호환성을 고려하세요.**
>
> 시나리오03 (Mind The Gap)은 시나리오02의 핵심 시스템을 공유합니다.
> C# 시스템이나 공용 Python 코드를 수정할 때 아래 원칙을 따라주세요.

### 호환성 원칙

1. **선택적 속성**: 새로운 prop은 없어도 동작하도록 설계
2. **기본값 적용**: 속성이 없으면 최적/최상의 상태로 간주
3. **점진적 확장**: 기존 시스템을 수정하지 않고 확장

### 예시: 내구도 시스템

```python
# GOOD: prop이 없으면 기본값 사용
def get_durability(item_id: int) -> float:
    durability = morld.get_unit_prop(item_id, "durability")
    if durability is None:
        return 1.0  # 시나리오02 아이템도 정상 동작
    return durability

# BAD: prop이 없으면 에러
durability = morld.get_unit_prop(item_id, "durability")
durability -= 0.1  # None이면 에러!
```

### 참고 문서

- 시나리오03 설계: [scenarios/scenario03/docs/design.md](scenarios/scenario03/docs/design.md)
- 호환성 상세: [scenarios/scenario03/docs/compatibility.md](scenarios/scenario03/docs/compatibility.md)
