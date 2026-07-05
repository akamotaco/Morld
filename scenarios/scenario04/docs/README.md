# Scenario04 문서 인덱스 — 마을과 던전

> **시나리오 개요**: 시나리오02 생활 시스템 위에 JRPG 파티 '대결' 전투를 얹은 마을↔던전 로그라이트 (디아블로1 트리스트럼식 루프).
> 핵심 질문: *"같이 사는 이 사람과 던전 깊은 곳에서 등을 맡길 수 있는가?"*
> 중반 반전("소원은 단 한 명에게만") 이후 배신 시스템이 전역 활성화됨.
>
> - 코드: `../python/` (약 80개 파일, 평면적 모듈 구성 — 시스템별 단일 파일)
> - 현재 리포에서 **가장 활발히 개발 중인 시나리오** (Hybrid 대화 통합 진행)

## 문서 목록

| 문서 | 설명 |
|------|------|
| [design.md](design.md) | 마스터 설계 문서 (~2,100줄) — 세계관, 챕터 구조, 4대 NPC, 오염 3분화(부식/침식/잠식), 실신→사망 2단계, 대결 전투, 기벽, 플레이어 모드(리더/파티원) |
| [advanced-systems.md](advanced-systems.md) | 고급 시스템 — 사기/신뢰/평판/조교·복종/마을 혼란도 등 |
| [creature-system.md](creature-system.md) | 던전 생물 — 변이종/적응종, 층별 세력, 드롭 |
| [dungeon-content.md](dungeon-content.md) | 던전 콘텐츠 — 층 구성, 이벤트, 함정 |
| [item-system.md](item-system.md) | 아이템 시스템 |
| [roguelite-reset.md](roguelite-reset.md) | 재편성(로그라이트 리셋) — 플레이어 실신 시 던전 재생성 |
| [pipeline-test.md](pipeline-test.md) | 파이프라인 테스트 |
| [minor-characters.md](minor-characters.md) | 조연 캐릭터 |

## 대화 시스템 (Hybrid)

S04의 NPC 대사는 시나리오 로컬이 아니라 **공용 Hybrid 대화 엔진**을 사용합니다.
전체 레퍼런스: 루트 [docs/dialogue-hybrid.md](../../../docs/dialogue-hybrid.md) (특히 §12 "S04 통합 Phase A~D")

| 구성 요소 | 위치 |
|-----------|------|
| 엔진 | `scenarios/common/python/engine/dialogue_hybrid/` (`stateless` API 사용) |
| 아키타입 공용 풀 | `scenarios/common/python/dialogues/archetype_dialogues/<아키타입>/<컨텍스트>.yaml` — 10 아키타입 × daily/party/dungeon/combat 등 |
| 캐릭터 override | `scenarios/common/python/dialogues/characters/*.yaml` (카엘/도현/레이/유이 first_meet 시그니처 등) |
| 라우팅 허브 | `../python/npc_dialogue.py` — situation → (context, intent) 매핑, yaml 없으면 로컬 `_LINES` fallback |
| 훅 주입 지점 | `../python/encounter.py` (combat_hit/critical 등), `erosion.py` (침식 임계), `linear_dungeon.py` (층 진입), `assets/characters/npc_*.py` (first_meet) |

## 주요 캐릭터 (정식 문서 없음 — 코드 주석이 원본)

캐릭터 설정의 원본은 `../python/assets/characters/` 각 파일의 주석입니다.

| 캐릭터 | 파일 | 역할 | 아키타입 |
|--------|------|------|----------|
| 플레이어 | `player.py` | 특수 존재 — 침식 저항 ×0.5, 던전의 힘 사용 가능 | — |
| 카엘 (NpcA) | `npc_a.py` | 욕망의 동반자 — 거간꾼/상인, 탐욕 | cheerful |
| 도현 (NpcB) | `npc_b.py` | 대척점/적대자 — 전직 모험가, 정의감. 마을 혼란도·군대 소환 트리거 | proud |
| 레이 (NpcC) | `npc_c.py` | 트라우마/부활 — 체류자 출신 타격수, 케어 시 최강 전투력 | stoic |
| 유이 (NpcD) | `npc_d.py` | 거울/진실 — 플레이어와 같은 특수 존재. 사망 시 진실 루트 차단 | timid |

## 문서화 공백 (TODO)

- 주요 4대 NPC 설정의 정식 문서화 (현재 코드 주석에만 존재)
- 대결(Encounter) 전투 구현 명세 (design.md의 설계와 `encounter.py` 구현 사이 간극)
- design.md 내 "미확정/밸런싱 추후" 항목 다수 — 확정 시 반영 필요
