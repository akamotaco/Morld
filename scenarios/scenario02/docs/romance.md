# 연애 시스템 (Romance System)

## 개요

플레이어와 호감도가 높은 NPC 간의 친밀한 상호작용 시스템.

**하위 문서**:
| 문서 | 설명 |
|------|------|
| [romance-relationship.md](romance-relationship.md) | 관계 라벨, 욕망, 이중 경로, 복종, 사적인 대화, 성별 |
| [romance-actions.md](romance-actions.md) | 스킨십, 데이트, NPC 주도, 감각/자극, 탈의/노출, 은신/발각, 소음, 삽입 |
| [romance-pregnancy.md](romance-pregnancy.md) | 임신과 출산 (월경/수정/임신/출산/아이 NPC) |
| [romance-join.md](romance-join.md) | 합류/복수 파트너 시스템 |
| [adult-toys.md](adult-toys.md) | 성인용품, 결박 시스템, 절정 상시 관리 |

---

## 구현 상태

### 완료된 기능

| 기능 | 파일 | 상태 |
|------|------|------|
| 스킨십 UI | romance.py | ✅ 완료 |
| 토글/즉시형 행위 | romance.py | ✅ 완료 |
| 경험치 시스템 | romance.py | ✅ 완료 |
| 절정 시스템 | romance.py | ✅ 완료 |
| 중단 이벤트 (이벤트 큐 연동) | romance.py | ✅ 완료 |
| 캐릭터별 반응 | 전체 NPC | ✅ 완료 |
| 데이트 요청/종료 | date.py | ✅ 완료 |
| 데이트 중 애정 표현 | date.py | ✅ 완료 |
| 데이트 외 애정 표현 | date.py | ✅ 완료 |
| 애정 표현 '#' 처리 | date.py, player.py | ✅ 완료 |
| NPC 주도 기본 구조 | npc_initiative.py | ✅ 완료 |
| 빠져나가기 시스템 | npc_initiative.py | ✅ 완료 |
| NPC 주도 트리거 | base.py, 전체 NPC | ✅ 완료 |
| 행위 마스킹 (exp_part) | npc_initiative.py | ✅ 완료 |
| 캐릭터별 액션 필터 | 전체 NPC | ✅ 완료 |
| 사적인 대화 (진척도 1-3) | 전체 NPC | ✅ 완료 |
| 은신 시스템 (플레이어/NPC 주도) | romance.py, npc_initiative.py | ✅ 완료 |
| 제3자 방해 이벤트 (NPC 주도) | npc_initiative.py | ✅ 완료 |
| 캐릭터별 은신 반응 | base.py, 전체 NPC | ✅ 완료 |
| 소음 시스템 (흥분도 3단계) | romance.py, npc_initiative.py, sound.py | ✅ 완료 |
| 캐릭터별 소음 프로필 | 전체 NPC (ROMANCE_SOUND_PROFILE) | ✅ 완료 |
| 발각 반응 시스템 | base.py (on_romance_discovered) | ✅ 완료 |
| 캐릭터별 발각 반응 | 전체 NPC (ROMANCE_DISCOVERY_REACTIONS) | ✅ 완료 |
| 발각 반발 증가 | base.py, 전체 NPC (effects에 반발 추가) | ✅ 완료 |
| 나체 발각 추가 페널티 | base.py (EXPOSURE_DISCOVERY_PENALTY), npc_initiative.py | ✅ 완료 |
| 나체 발각 전용 대사 | 전체 NPC (exposed_text) | ✅ 완료 |
| 중단 액션 로그 | romance.py ("XX의 방해로 중단되었다.") | ✅ 완료 |
| 감각 시스템 (M/B/A/V/C) | romance.py (SENSATION_MAP, get_sensation_level) | ✅ 완료 |
| 감각 보정 (성욕 효과) | romance.py (calculate_effects) | ✅ 완료 |
| 욕망 prop 인프라 | romance.py (apply_effects), needs.py (동적 cap) | ✅ 완료 |
| NPC 주도 욕망 임계값 | base.py (desire_threshold) | ✅ 완료 |
| V/C/P 부위 액션 (8종) | romance.py, npc_initiative.py | ✅ 완료 |
| 행위 해부학 필터링 | romance.py (is_anatomy_compatible), npc_initiative.py | ✅ 완료 |
| 이중 경로 잠금 해제 | romance.py, npc_initiative.py (욕망 할인) | ✅ 완료 |
| 욕망 효과 활성화 | romance.py, npc_initiative.py (butt_caress/breast_touch 욕망+1) | ✅ 완료 |
| FILTERS context 욕망 | base.py (get_allowed_initiative_actions) | ✅ 완료 |
| 복종 디버그 조정 | base.py (debug_submission_up/down), 전체 NPC | ✅ 완료 |
| 복종 이중 경로 | romance.py (is_action_available + submission) | ✅ 완료 |
| 복종 자연 증가 (행위/절정) | romance.py, npc_initiative.py (apply_effects) | ✅ 완료 |
| 관계 항상성 (호감/반발/복종 basin 수렴) | needs.py (_apply_homeostasis) | ✅ 완료 |
| 감각 비선형 진행 (제곱 곡선) | romance.py (get_sensation_level) | ✅ 완료 |
| 연쇄 절정 경험치 배율 (×2.5) | stimulation.py (get_climax_sensation_gain) | ✅ 완료 |
| 성적 지향성 (NPC별 배율) | gender.py (orientation system) | ✅ 완료 |
| 체격/음경 크기 호환성 | gender.py (check_penetration_compatibility) | ✅ 완료 |
| M 감각 삼키기 게이트 | romance.py, npc_initiative.py | ✅ 완료 |
| 준비부족 강도 행위 페널티 | romance.py, npc_initiative.py | ✅ 완료 |
| 사정감 참기 (hold_back) | romance.py, npc_initiative.py | ✅ 완료 |
| pull_out 버그 수정 | romance.py (is_pull_out_available) | ✅ 완료 |
| 관계 라벨 시스템 | romance.py | ✅ 완료 |
| 반발 시스템 | romance.py, base.py | ✅ 완료 |
| 성별 시스템 | gender.py | ✅ 완료 |
| 자극 시스템 (부위별) | stimulation.py, romance.py, npc_initiative.py | ✅ 완료 |
| 남성 불응기 (refractory) | stimulation.py (male_mode), romance.py, npc_initiative.py | ✅ 완료 |
| 자극 UI (여운/연쇄/절정) | romance.py, npc_initiative.py | ✅ 완료 |
| 애정 prop 제거 (호감 통합) | romance.py, npc_initiative.py, date.py, 5캐릭터 | ✅ 완료 |
| 공수 전환 (주도권 전환) | romance.py, npc_initiative.py | ✅ 완료 |
| 탈의/노출 시스템 | romance.py, npc_initiative.py | ✅ 완료 |
| 노출 기반 행위 해금 (하드 락) | romance.py, npc_initiative.py | ✅ 완료 |
| 노출 기반 효과 보너스 (×1.5) | romance.py, npc_initiative.py | ✅ 완료 |
| 세션 종료 → 착의 인터럽트 연계 | romance.py, npc_initiative.py | ✅ 완료 |
| 동작 모드 인프라 (4모드) | romance_mode.py | ✅ 완료 |
| 강제 모드 (Player→NPC) | romance.py, romance_mode.py, base.py | ✅ 완료 |
| 무의식 모드 (기절 NPC) | romance.py, romance_mode.py | ✅ 완료 |
| 시간정지 모드 (지연 효과) | romance.py, romance_mode.py | ✅ 완료 |
| NPC→Player 저항 모드 | npc_initiative.py | ✅ 완료 |
| 강제 진입 은신 기습 보너스 | romance_mode.py | ✅ 완료 |
| NPC 저항/탈출 (강제 중) | romance_mode.py (check_resistance) | ✅ 완료 |
| 탈출 확률 개편 (성욕/게이지 감소) | romance_mode.py (calculate_escape_chance) | ✅ 완료 |
| 항상실패(futile) 판정 | romance_mode.py (escape_power vs suppression) | ✅ 완료 |
| 탈출 시도 메시지 (실패 시) | romance_mode.py (get_escape_attempt_message) | ✅ 완료 |
| 탈출 확률 UI 표시 | romance_ui.py (저항 바 + 탈출%) | ✅ 완료 |
| 신체 반응 묘사 (10 아키타입) | romance_body_reaction.py | ✅ 완료 |
| 모드별 캐릭터 반응 | 전체 NPC (forced_/aftermath) | ✅ 완료 |
| 임신 이벤트 (수정/발표) | pregnancy.py, base.py, 전체 NPC | ✅ 완료 |
| 모드 사후 이벤트 (on_meet) | base.py, 전체 NPC | ✅ 완료 |
| HP 통합 (스태미나→생존체력) | romance.py, npc_initiative.py, romance_core.py | ✅ 완료 |
| 조건부 쿨다운 (NPC 주도) | npc_initiative.py, base.py | ✅ 완료 |
| NPC 만족 종료 | npc_initiative.py | ✅ 완료 |
| 행위 묘사 시스템 | romance_actions.py, romance.py, npc_initiative.py | ✅ 완료 |
| 자극 상태 자동 묘사 | romance_core.py, romance_ui.py | ✅ 완료 |
| 탈진 HP 1 보존 | romance.py, npc_initiative.py | ✅ 완료 |
| 체력 바 10칸 정규화 | romance_ui.py, npc_initiative.py | ✅ 완료 |
| 대사 generator (3D 좌표 기반) | romance_line_generator.py | ✅ 완료 |
| 묘사 generator (3D 좌표 기반) | romance_reaction_generator.py | ✅ 완료 |
| 톤 템플릿 (10 아키타입) | tone_templates/ | ✅ 완료 |
| 캐릭터 오버레이 (5 NPC) | characters/*.py (CHARACTER_REACTIONS/LINES) | ✅ 완료 |
| FOCUS/DESCRIBE 아키타입 빌더 | base.py (build_focus_rules, build_describe_rules) | ✅ 완료 |
| ROMANCE_REACTIONS 아키타입 빌더 | base.py (build_romance_reactions) | ✅ 완료 |
| 1회성(once) 반응 시스템 | base.py, stimulation.py, characters/*.py | ✅ 완료 |
| NPC 주도 플레이어 행동 제한 | npc_initiative.py, romance_actions.py | ✅ 완료 |
| 능동/수동 행위 분류 (passive_in_npc_initiative) | romance_actions.py | ✅ 완료 |
| 차단 확률 (근력/체격 보정) | npc_initiative.py (_check_npc_block) | ✅ 완료 |
| "애원하기" NPC 주도 전용 행위 | romance_actions.py, npc_initiative.py | ✅ 완료 |
| NPC 차단/애원 반응 (10 아키타입) | tone_templates/, characters/*.py | ✅ 완료 |
| NPC 여운 상태 체감 (UI + 반응) | romance.py, npc_initiative.py | ✅ 완료 |
| 여운 강도별 반응 (sensitive/trembling/fading) | tone_templates/, characters/*.py | ✅ 완료 |
| 여운 종료 반응 (afterglow_end) | stimulation.py, romance.py, npc_initiative.py | ✅ 완료 |
| NPC 주도 여운 행동 (자동 일시정지) | npc_initiative.py (_npc_auto_advance) | ✅ 완료 |

### 지원 캐릭터

| 캐릭터 | 스킨십 반응 | NPC 주도 | 사적인 대화 | 은신 반응 | 소음 | 발각 반응 | 특징 |
|--------|-----------|----------|-----------|----------|------|---------|------|
| 세라 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 무뚝뚝/거친 - 연애 쑥맥 |
| 밀라 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 다정/포근 - 연애 저돌적 |
| 리나 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 활발 - 연애엔 수줍음 |
| 유키 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 매우 수줍음 |
| 엘라 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 냉정함 |

### 미구현/선택적 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| ~~캐릭터별 목격 반응~~ | ~~목격자 × 파트너 분기~~ | ✅ 완료 (ROMANCE_DISCOVERY_REACTIONS) |
| 합류 이벤트 | 호감 높은 NPC 합류 | 취소 |
| ~~성적흥분 상한 클램프~~ | ~~동적 cap 초과 시 즉시 클램프~~ | ✅ 완료 (needs.py) |
| 복수 파트너 UI | 3인 이상 연애 | 취소 |
| ~~자위 행동~~ | ~~NPC self-comfort think 핸들러~~ | ✅ 완료 (think/__init__.py) |
| ~~NPC→플레이어 탐색~~ | ~~고욕망+고관계+고성욕 시 플레이어 찾기~~ | ✅ 완료 (think/__init__.py) |
| ~~감각 기반 주도 제한~~ | ~~INITIATIVE_SENSATION_REQS 필터~~ | ✅ 완료 (base.py) |
| ~~자위 발각~~ | ~~on_meet 시 자위 중 발각 처리~~ | ✅ 완료 (base.py) |
| ~~은밀 장소 판정~~ | ~~length 기반 은밀 장소 선정~~ | ✅ 완료 (length 기반) |
| ~~화장실 프라이버시~~ | ~~ROOM_PRIVACY_CONFIG "화장실" 추가~~ | ✅ 완료 (5캐릭터) |
| ~~NPC-NPC 대화~~ | ~~사회욕 기반 대화 시스템 + describe text~~ | ✅ 완료 (think/__init__.py _handle_socialize) |
| 성인용품 시스템 (17종) | 착용형/삽입형/소모성 아이템 | ✅ 완료 (adult_toys.py) |
| 결박 시스템 (로프/수갑) | 행동 제한, 자력 해제, NPC 구출 | ✅ 완료 (restraint.py) |
| 절정 상시 관리 (`상태:절정`) | 비로맨스 절정 게이지, 세션 동기화 | ✅ 완료 (needs.py) |
| 로맨스 신규 액션 (6종) | 결박/해제, 성인용품 장착/해제, 강제 투여, 채찍 | ✅ 완료 (romance_actions.py) |
| 행위 차단 로직 (결박/삽입물) | 입 결박→구강 차단, 삽입물→삽입 차단 | ✅ 완료 (romance_core.py) |
| 임시 해부학 (페니스밴드) | `has_anatomy` vs `has_natural_anatomy` | ✅ 완료 (gender.py) |
| NPC 자위 성인용품 사용 | 삽입형 자동 사용 + 효과 증가 | ✅ 완료 (self_comfort.py) |
| 음식 첨가물 효과 (NPC 식사) | 미약/배란유도제/정력제 첨가 감지 | ✅ 완료 (eat.py) |
| 결박/성인용품 톤 반응 (10 아키타입) | restrained_idle/passive_climax/toy_equipped | ✅ 완료 (tone_templates/) |
| NPC-NPC 행위 발각 | 행위 중 플레이어 개입 이벤트 | 미구현 |
| NPC-NPC 자위 발각 상호작용 | 연인 NPC 발각 시 상호 애정 행위 전환 | 미구현 (현재: NPC 방해 → 짧은 쿨다운) |
| ~~V 부위 액션~~ | ~~Vaginal 카테고리 액션 추가~~ | ✅ 완료 (V/C 4종 추가) |
| ~~복종 시스템~~ | ~~관계:{name}:복종 prop + 이중 경로 + 자연 증가/감소~~ | ✅ 완료 (romance.py, npc_initiative.py, needs.py) |

---

## 관련 morld API

| API | 설명 | 사용처 |
|-----|------|--------|
| `get_units_at_location(r, l)` | Location의 유닛 ID 목록 | 제3자 체크 |
| `advance_time_des(millis)` | DES 시뮬레이션 (think + 이동 + 이벤트) | 행위 시간 경과 |
| `modify_prop(id, prop, delta)` | prop 상대값 변경 | 호감도/애정 증감 |
| `add_unit_mood(id, mood)` | mood 추가 | 부끄러움 등 |
| `set_npc_job(id, action, dur, target)` | NPC Job 설정 | flee, follow |
| `set_unit_prop(id, prop, value)` | prop 절대값 설정 | can: props |

---

## 파일 구조

```
scenarios/scenario02/python/
├── romance.py                    # 스킨십 시스템 (플레이어 주도)
├── romance_actions.py            # 행위 정의 + 공유 상수
├── romance_core.py               # 공유 핵심 로직 (25+ 함수)
├── romance_mode.py               # 동작 모드 (합의/강제/무의식/시간정지)
├── romance_body_reaction.py      # 강제 모드 신체 반응 (10 아키타입 × 각성 단계)
├── romance_ui.py                 # 연애 UI 렌더링
├── romance_line_generator.py     # 대사 generator (:start 1인칭, 3D 좌표 기반)
├── romance_reaction_generator.py # 묘사 generator (:during 3인칭, 3D 좌표 기반)
├── tone_templates/               # 아키타입별 좌표→텍스트 풀 패키지
│   ├── coords.py                 # 3D 좌표 계산 (calc_coordinates, select_by_coord)
│   ├── __init__.py               # 4개 dict 집계 (CATEGORY/ARCHETYPE/LINE/ACTION_LINE)
│   ├── stoic.py                  # stoic 아키타입 (세라)
│   ├── gentle.py                 # gentle 아키타입 (밀라)
│   ├── cheerful.py               # cheerful 아키타입 (리나)
│   ├── timid.py                  # timid 아키타입 (유키)
│   ├── cold.py                   # cold 아키타입 (엘라)
│   ├── seductive.py              # seductive 아키타입 (모브)
│   ├── fierce.py                 # fierce 아키타입 (모브)
│   ├── proud.py                  # proud 아키타입 (모브)
│   ├── innocent.py               # innocent 아키타입 (모브)
│   └── devoted.py                # devoted 아키타입 (모브)
├── date.py                       # 데이트 시스템 + 애정 표현
├── npc_initiative.py             # NPC 주도 스킨십 시스템 (행위 마스킹, 캐릭터 필터)
├── gender.py                     # 성별/성적지향/체격/음경크기/삽입호환성
├── stimulation.py                # 자극 시스템 (절정/여운/연쇄)
├── restraint.py                  # 결박 시스템 (상태 판별/자력 해제/타인 해제)
├── pregnancy.py                  # 임신/출산 시스템 (월경/수정/임신/출산/이벤트)
├── assets/
│   ├── items/
│   │   └── adult_toys.py         # 성인용품 17종 아이템 정의 + 유틸리티
│   ├── base.py                   # Character 클래스 + 빌더 함수
│   │                             # - build_focus_rules(): FOCUS_RULES 아키타입 빌더
│   │                             # - build_describe_rules(): DESCRIBE_RULES 아키타입 빌더
│   │                             # - build_romance_reactions(): ROMANCE_REACTIONS 빌더
│   │                             # - should_initiate_skinship()
│   │                             # - get_initiative_reaction()
│   │                             # - get_allowed_initiative_actions()
│   │                             # - get_stealth_success_reaction()
│   │                             # - apply_stealth_success_effects()
│   └── characters/
│       ├── player.py             # 플레이어 (can: props)
│       ├── sera.py               # 세라 - stoic, 연애 쑥맥
│       ├── mila.py               # 밀라 - gentle, 연애 저돌적
│       ├── lina.py               # 리나 - cheerful, 연애엔 수줍음
│       ├── yuki.py               # 유키 - timid
│       ├── ella.py               # 엘라 - cold
│       └── child.py              # 아이 NPC (출산 시 동적 생성)
└── think/
    ├── __init__.py               # BaseAgent (think 5-tier, NPC 성욕/사회 행동)
    ├── child_agent.py            # 아이 NPC Agent (최소 욕구 행동)
    └── activities/
        └── childbirth.py         # 출산/모성 활동 핸들러
```
