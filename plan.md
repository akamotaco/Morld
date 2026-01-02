# 로그 및 대화 시스템 설계

## 구현 완료 요약

### Phase 1 완료 ✓
- **ScriptSystem**: sharpPy 기반 Python 인터프리터 통합
- **모놀로그 시스템**: 페이지 기반 텍스트, YesNo 버튼, 콜백 처리
- **morld 모듈 API**:
  - `get_player_id()` - 플레이어 유닛 ID 반환
  - `give_item(unit_id, item_id, count)` - 아이템 지급
  - `get_unit_info(unit_id)` - 유닛 정보 조회 (id, name, activity, is_moving 등)
- **BBCode script: 연동**: `[url=script:함수:args]` → Python 함수 호출
- **context_unit_id 자동 전달**: Focus.UnitId → Python 함수 첫 번째 인자
- **NPC 대화 오버라이드 시스템**: activity 기반 + 캐릭터별 오버라이드

### 핵심 아키텍처 결정사항
- **C#**: 이벤트 감지 (언제), **Python**: 콘텐츠 결정 (무엇을)
- **sharpPy**: 순수 C# Python 3.12 인터프리터 (외부 의존성 없음)
- **morld 모듈**: Python → C# 역호출 (게임 데이터 조회/수정)
- **Flag 관리**: Python 전담 (C# FlagSystem 없음)

---

## 미구현 시스템

### EventSystem (미구현)

이벤트 기반 아키텍처로 기반 시스템과 플러그인 시스템을 분리합니다.

**이벤트 타입:**
| 타입 | 생성 시점 | 생성 주체 |
|------|----------|----------|
| `arrive` | 유닛이 위치에 도착 | MovementSystem |
| `depart` | 유닛이 위치에서 출발 | MovementSystem |
| `meet` | 두 유닛이 같은 위치 | MovementSystem |
| `action` | 유닛이 행동 수행 | ActionSystem |

**구현 필요 시점:** 자동 이벤트 트리거가 필요해질 때

---

## 남은 구현 Phase

### Phase 2: 로그 시스템
1. LogSystem 또는 기존 시스템 확장
2. 이동 로그 자동 기록
3. Text UI에 로그 영역 표시

### Phase 3: UI 포맷팅 개선
1. 헤더 영역 (날짜/시간/날씨)
2. 로그 + 묘사 영역
3. 행동 영역 분리

### Phase 4: 다이얼로그 (별도 설계 필요)
1. 선택지 시스템
2. 조건부 분기
3. 게임 데이터 영향

---

## 미해결 질문

### 포맷팅 관련
1. 헤더(날짜/시간)를 별도 RichTextLabel로 분리할지, 단일 텍스트로 유지할지?
2. 스크롤 시 헤더가 함께 스크롤되어도 괜찮은지?
3. 로그 최대 보관 개수?

### 모놀로그 관련
1. 모놀로그 스킵 기능 필요 여부?
2. 모놀로그 텍스트에 변수 치환 필요 여부? (예: `{playerName}`)

### 이벤트 시스템 관련
1. 이벤트 트리거 조건 정의 방식?
2. 이벤트 → 모놀로그 연결 방식?
3. 이벤트의 1회성 vs 반복성 처리?

---

## 관련 파일

```
scripts/
├─ system/
│  ├─ script_system.cs          # ✓ ScriptSystem (morld 모듈, context_unit_id)
│  └─ text_ui_system.cs         # ✓ ShowMonologue, YesNo 처리
├─ morld/
│  └─ ui/
│     └─ Focus.cs               # ✓ FocusType.Monologue, MonologueButtonType
├─ python/
│  ├─ monologues.py             # ✓ NPC 대화, 직업선택, 오브젝트 상호작용
│  └─ job_blessings.json        # ✓ 직업별 축복 메시지 데이터
├─ MetaActionHandler.cs         # ✓ script:, monologue_yes/no 처리
│
└─ (추후 구현)
   ├─ python/dialogues.py       # 다이얼로그
   ├─ python/event_handler.py   # 이벤트 처리
   └─ python/flags.py           # 플래그 관리

util/
└─ sharpPy/
   ├─ core/PyContextManager.cs  # ✓ Godot res:// 경로 지원
   └─ platform/helper_godot.cs  # ✓ IsGodotPath, ReadAllText
```
