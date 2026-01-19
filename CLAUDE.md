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
| [system-core.md](scenarios/scenario02/docs/system-core.md) | ECS 아키텍처, 시스템 구조, 프로젝트 레이아웃 | ~150 |
| [system-api.md](scenarios/scenario02/docs/system-api.md) | morld Python API, Dialog, Asset 클래스 | ~200 |
| [system-ui.md](scenarios/scenario02/docs/system-ui.md) | TextUI, 토글, 액션 필터링 | ~150 |
| [system-gameplay.md](scenarios/scenario02/docs/system-gameplay.md) | 장비, 생존, 연애 등 게임플레이 시스템 | ~180 |

---

## 작업별 참고 문서

### 지형/맵 작업

| 작업 | 참고 문서 |
|------|----------|
| Region/Location/Edge 구조 | [terrain.md](scenarios/scenario02/docs/terrain.md) |
| 맵 구성 (저택, 마을, 숲 등) | [map.md](scenarios/scenario02/docs/map.md) |
| 환경 속성 (온도, 조명, 날씨) | [terrain_property.md](scenarios/scenario02/docs/terrain_property.md) |
| 던전 시스템 | [dungeon.md](scenarios/scenario02/docs/dungeon.md) |
| 바닥 오브젝트 | [ground.md](scenarios/scenario02/docs/ground.md) |

### 캐릭터/NPC 작업

| 작업 | 참고 문서 |
|------|----------|
| NPC AI/스케줄/Agent | [agent.md](scenarios/scenario02/docs/agent.md) |
| 연애/스킨십 시스템 | [romance.md](scenarios/scenario02/docs/romance.md) |
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
| 이벤트 시스템 (on_meet, on_reach) | [event.md](scenarios/scenario02/docs/event.md) |
| 시간 정지 (Frozen) 상태 | [frozen.md](scenarios/scenario02/docs/frozen.md) |

---

## 문서 구조

```
scenarios/scenario02/docs/
├── system-core.md      # ECS 아키텍처, 프로젝트 구조
├── system-api.md       # morld Python API, Dialog
├── system-ui.md        # TextUI, 액션 필터링
├── system-gameplay.md  # 장비, 생존, 연애 시스템
├── design.md           # 시나리오 설계 (세계관, 캐릭터)
├── terrain.md          # 지형 시스템
├── terrain_property.md # 환경 속성
├── map.md              # 맵 구성
├── dungeon.md          # 던전 시스템
├── ground.md           # 바닥 오브젝트
├── agent.md            # NPC AI/Agent
├── romance.md          # 연애 시스템
├── quest.md            # 퀘스트 시스템
├── clothes.md          # 의류/장비
├── food.md             # 음식/요리
├── craft.md            # 크래프팅
├── event.md            # 이벤트 시스템
└── frozen.md           # 시간 정지 상태
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
