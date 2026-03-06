# 파티 시스템 설계 노트

> **상태: Phase 2 구현 완료 (FSM Phase 실동작 — Order 핸들러 + push/pop 통합)**
>
> 이 문서는 파티 시스템의 설계 논의(Section 1~7) + 구현 명세(Section 8)를 포함합니다.
> 기존 `party-implementation.md`(v1)을 대체하는 최신 명세입니다.
>
> **구현 현황:**
> - Phase 1 ✅: FSM pass-through 변환, party.py 모듈, party_config.py, 챕터 리셋, 53개 테스트
> - Phase 2 ✅: Order 핸들러 6종 (order_handlers.py), FSM push/pop 통합 (set_order/remove_member), 72개 테스트
> - Phase 3 ⬜: 이동/동기화 (follow, gate 동기화, 귀환)
> - Phase 4 ⬜: 플레이어 UI (모집/지시 액션)
> - Phase 5 ⬜: 연동/마무리 (전투 합류, 데이트 상호 배제, 불복)

---

## 1. 대원칙

### 1.1 시나리오 02/03 공유 시스템

파티 시스템은 시나리오 02와 03이 **같은 코어**를 사용합니다.

| 항목 | 시나리오 02 (체험형) | 시나리오 03 (전술형) |
|------|-------------------|-------------------|
| 플레이어 역할 | 캐릭터 (1인칭) | 관측자/지휘관 |
| 파티 구성 | 플레이어 + NPC 최대 3명 | NPC 4명 × 여러 분대 |
| 플레이어 화신 | 플레이어 자신 | 분대 리더로 참여 가능 (총 4명) |
| 지휘 범위 | 직접 행동 + 파티원 지시 | 매크로 방침 (분대 단위) |
| 분대 리더 | 플레이어 또는 NPC | NPC (또는 플레이어 화신) |
| 마이크로 판단 | 플레이어 직접 | 분대 리더가 자율 판단 |

### 1.2 파티 = 분대

- "파티"(시나리오 02) = "분대"(시나리오 03) = 같은 시스템 단위
- 최대 4명 (리더 포함)
- 리더 1명 존재, 리더가 분대원에게 지시
- NPC만으로 구성 가능 (시나리오 03의 기본 형태)

---

## 2. FSM Pass-Through 스택

### 2.1 현재 FSM vs 새 구조 ✅ 확정

**현재 FSM (fsm.py):**
```
update() → True: "처리 완료, 멈춤"
         → False: "pop (스택에서 제거) + 아래로"
```

**새 구조 (pass-through):**
```
update() → True:  "처리 완료, 멈춤" (스택 유지)
         → False: "스택 유지 + 아래 phase로 넘김" (pass-through)
         → 종료:   명시적 pop 호출 필요 (명령 취소/변경 시)
```

**핵심 변경**: `False`가 pop이 아니라 "스택에 남은 채 아래로 위임"

**구현 방침 (확정):**
- FSM 전체를 pass-through로 변경 (기존 CombatState/FleeState 포함)
- push/pop은 명시적으로, pass-through는 True/False로
- 기존 상태들은 완료 시 명시적 pop() 호출로 종료
- **동일 레벨 auto-pop 유지**: `_fsm_push()` 시 동일/상위 레벨 자동 pop (전투 상태 교체에 활용, 예: Flee→Desperate)

### 2.2 think() 루프 구조 ✅ 확정

```
think():
  스택을 위→아래로 순회
  각 phase의 update() 호출
  첫 True 반환에서 멈춤
```

- **비파티 NPC**: `[LifePhase]` — 기존과 동일한 동작
- **파티 NPC**: `[CommandPhase, StandbyPhase, LifePhase]`
- **전투 중**: `[CombatState, CommandPhase, StandbyPhase, LifePhase]`

### 2.3 LifeState → LifePhase 통합 ✅ 확정

- 기존 `LifeState`가 `LifePhase` 역할을 겸함
- `LifePhase.update()` = 기존 5-tier 로직 호출 → 항상 True (최하위, 반드시 처리)
- 분대 해산 시 Command/Standby pop → `[LifePhase]`로 자연 복귀
- 향후 LifePhase를 다른 phase로 교체 가능 (스택 최소 1개 보호 유지)

### 2.5 3단 스택 예시

```
스택 (위→아래): [지휘] → [대기] → [생활]
```

**시나리오: "아이템 수집" 명령**

```
[지휘: 아이템 수집]
  조사할 아이템 남음 → 조사 job 삽입 → return True (여기서 끝)
  전부 조사 완료    → return False (아래로 넘김)
        ↓
[대기]
  현재 location 유지 → idle job 삽입 → return True (여기서 끝)
  (생활 phase는 호출되지 않음)
```

**시나리오: "아이템 수집" 완료 후 장시간 대기 (시나리오 02)**

```
[지휘: 없음]
  → return False
        ↓
[대기]
  배변 욕구 80 (위험) → return False (생활로 넘김)
        ↓
[생활]
  배변 처리 실행 (현재 location 벗어날 수 있음)
  → 완료 후 다음 think()에서 다시 [지휘]부터 평가
```

### 2.6 Phase별 역할

| Phase | 역할 | True 반환 시 | False 반환 시 |
|-------|------|------------|-------------|
| **지휘** | 분대장 명령 수행 | 명령에 따른 행동 실행 | 할 일 없음 → 대기로 넘김 |
| **대기** | 현 위치 유지 (기본) | idle 유지, 생활 차단 | 욕구 위험 시 생활로 넘김 |
| **생활** | 일상 (욕구, 스케줄) | 일상 행동 실행 | - (최하위) |

### 2.7 Phase별 pop 조건

Phase는 자동으로 pop되지 않습니다. 명시적 pop이 필요한 경우:

| Phase | pop 시점 |
|-------|---------|
| 지휘 | 명령 취소, 새 명령으로 교체, 분대 해산 |
| 대기 | 분대 해산, 특수 전환 |
| 생활 | pop 없음 (최하위, 항상 존재) |

---

## 3. 욕구 처리 원칙

### 3.1 "Phase가 결정한다"

```
❌ 틀린 접근: 욕구 시스템이 FSM을 무시하고 인터럽트
✅ 맞는 접근: 각 phase 내부에서 욕구를 고려하여 True/False 결정
```

- 욕구에 대한 **별도의 예외 로직을 만들지 않음**
- 각 phase가 내부에서 "지금 욕구를 허용할지"를 판단
- True 반환 = 욕구 억제 ("참기")
- False 반환 = 아래 phase에서 처리 허용

### 3.2 "참기" 개념

Phase가 True를 반환해서 욕구를 억제하면:

1. 캐릭터는 욕구를 **참는** 상태
2. 시간 경과 → 욕구 수치 계속 상승 → 한계 초과
3. 한계 초과 시 **실수 발생**:
   - 수치심 반응
   - 오염도 상승
   - 수치 조정 (욕구 리셋)
   - 캐릭터 대사/리액션

이것은 예외 로직이 아니라 **phase의 판단 + 욕구 시스템의 자연스러운 결과**

### 3.3 시나리오별 전략

| 시나리오 | 전투 전 | 전투/임무 중 |
|---------|--------|-----------|
| **03 (전술)** | "소집" phase에서 욕구 사전 해소 (밥/화장실/수면 처리 후 출발) | 지휘 phase가 True 유지 (전투 구역에서는 억제) |
| **02 (체험)** | 별도 소집 없음 (여유로움) | 대기 phase가 상황에 따라 True/False 유연하게 판단 |

---

## 4. 지휘 흐름 ✅ 확정

### 4.1 분대 객체 (Squad Object)

분대의 명령/상태를 관리하는 중앙 객체. 분대장의 성격이 분대 객체에 반영됨.

```
분대 객체 (Squad)
  ├─ 지휘 자세 (player_directive): 공세 / 통상 / 은밀
  ├─ 분대 성격 (leader_traits): 분대장 캐릭터 성격에서 생성
  ├─ 분대원별 지시 (orders): {unit_id: Order}
  └─ 분대 구성원 (members): [unit_id, ...]
```

**핵심 설계:**
- 분대장 캐릭터의 성격 → 분대 객체의 "분대 성격"으로 투영
  - 공격적 캐릭터 → 공세적 지시 경향
  - 신중한 캐릭터 → 은밀/방어적 지시 경향
- 분대장 교체 시: 분대 성격 **전체 교체/갱신** (부분 패치 아님)
- 분대 해산 시: 객체 자체 폐기 → 명령 자동 정리

### 4.2 2계층 명령 체계

```
┌─ 계층 1: 지휘 (Directive) ─── 플레이어 → 분대 ──────────────────────┐
│ 7종 자세:                                                          │
│   auto / search / combat_stealth / combat_normal /                 │
│   combat_aggressive / retreat / wait                               │
│ (분대 객체의 player_directive에 저장)                                │
└──────────────────────────────────────────────────────────────────┘
          ↓ 분대장이 지휘를 해석
┌─ 계층 2: 지시 (Order) ─── 분대장 → 분대원 ─────────────────┐
│ 구체적 행동: 수색 / 경계 / 수집 / 이동 / 대기 등             │
│ 필터링 지원: "*" (전체) / "재료" / "음식" (카테고리)          │
│ (분대 객체의 orders에 저장)                                  │
└─────────────────────────────────────────────────────────┘
```

### 4.3 실행 흐름 (think 내 통합)

```
분대장 think():
  1. 분대 객체에서 플레이어 지휘(directive) 확인
  2. 지휘 + 분대 성격 + 환경 → 분대원별 지시(order) 결정
  3. 분대 객체의 orders 갱신
  4. 본인의 행동도 FSM 스택으로 결정

분대원 think():
  1. 분대 객체에서 자기 지시(order) 조회
  2. CommandPhase에서 지시에 따라 행동 or pass
  3. 나머지 FSM 스택 순회
```

- 별도의 pre-think 단계 불필요 — 명령은 분대 객체에 지속 저장
- DES에서 think() 호출 순서와 무관하게 동작 (지시는 다음 think()에서 반영)

### 4.4 불복/이탈

| 조건 | 결과 |
|------|------|
| 성향 불일치 (지시 vs 캐릭터) | 지시 무시, 자율 판단 |
| 반발 보통 이상 + 체념/공포 | 분대 이탈 이벤트 발생 |
| 지휘 무시 (분대장 vs 플레이어) | 분대장 성격에 따라 지휘 불복 가능 |

### 4.5 명령 전파 예시

```
플레이어 (지휘관)
  ├─ 분대 A: 지휘="공세" (매크로)
  │    └─ 분대장 A (공격적 성격): 지휘 수용 → 공격적 지시
  │         ├─ 대원 1: "좌측 수색"
  │         ├─ 대원 2: "우측 수색"
  │         └─ 대원 3: "돌격 대기"
  │
  └─ 분대 B: 지휘="은밀" (매크로)
       └─ 분대장 B (신중한 성격): 지휘 수용 → 은밀 지시
            ├─ 대원 1: "정찰"
            ├─ 대원 2: "경계"
            └─ 대원 3: "대기"
```

---

## 5. 파티 기능 요구사항

### 5.1 기본 기능

- [x] 최대 4명 (리더 포함)
- [x] 리더 존재, 리더가 지시
- [x] NPC만으로 구성 가능
- [x] 전투 정책 (선제 공격, 반격, 비전투)
- [x] 캐릭터 성격/상태에 따라 지시 무시 가능

### 5.2 가입/탈퇴

- [ ] NPC에게 파티 참여 요청 (호감도 + 현재 activity에 따라 수락/거부)
- [ ] NPC 자발적 참여 요청 (on_meet 이벤트로 "같이 갈까?" 제안)

### 5.3 이동

- [ ] 파티원은 평소 리더를 따라감 (follow)
- [ ] 전투/디버프로 벗어난 경우, 이동 가능 시 리더를 찾아 이동
- [ ] 차량 함께 탑승 (TODO — 차량 시스템 구현에 따라)

### 5.4 대화/잡담

- [ ] 전투 없어도 동작하는 파티원 간 잡담 시스템
- [ ] 전투 중 끊임없는 대사 (상태를 대사로 표현, 기합, 경고 등)
- [ ] 자신의 상태를 별도 UI가 아닌 대사/묘사로 전달

### 5.5 테스트

- [ ] 분대를 온전히 컨트롤할 수 있는 테스트 UI

---

## 6. 미논의 항목

> 순차적으로 검토할 항목들

### 6.1 FSM 상세 설계 ✅ 확정
- FSM 전체를 pass-through로 변경 (섹션 2.1~2.4에 반영)
- 기존 CombatState/FleeState: 동일한 pass-through 규칙, 완료 시 명시적 pop
- LifeState = LifePhase로 통합, 교체 가능

### 6.2 분대장 AI ✅ 확정
- 분대 객체(Squad)에 명령 저장 (섹션 4.1에 반영)
- 분대장 성격 → 분대 성격으로 투영, 교체 시 전체 갱신
- 2계층: 플레이어 지휘(7종) → 분대장 지시(구체적 행동)
- 불복/이탈: 성향 불일치 시 지시 무시, 극단 조건에서 분대 이탈
- think() 내 통합: 별도 pre-think 불필요, 분대 객체 지속 저장

### 6.3 파티 대화 시스템 ✅ 방향 확정 (상세는 후순위)
- **별도 대화 시스템** (기존 TALK/DESCRIBE와 별개)
- **무전/채팅형 누적 로그**: 행동 로그처럼 누적, read 처리해도 사라지지 않음
- **전투/비전투 통합**: 같은 시스템으로 잡담 + 전투 대사 출력 (D&D 로그 스타일)
- **시나리오 03 핵심**, 시나리오 02에서도 재활용 가능 (전투 공통)
- **UI**: 텔레그램/채팅형 고려 중 (시스템 구조 우선)
- **우선순위**: 파티 골격(FSM+분대+이동) 구현 후 상세화. 단, UX 핵심이므로 반드시 구현
- 예시:
  ```
  -A:'적들과 조우! 전투에 돌입합니다!'
  -'탕!탕!탕'
  -B:'리로딩! 엄호해줘'
  -C:'라져!'
  -A:'윽!, 괜찮아 아직 스친 정도야!'
  ```

### 6.4 테스트 UI ✅ 방향 확정 (상세는 후순위)
- **디버그 + 시나리오 03 프로토타입** 겸용
- 디버그는 print로도 충분, UI는 지휘관 조작 중심
- 분대 편성/지휘 자세/지시 변경/상태 모니터링
- **우선순위**: 파티 골격 구현 후 상세화

### 6.5 시나리오 03 전용 ✅ 방향 확정
- **워크플로우 (확인됨)**:
  1. Basement 플랫폼 (일상) → 분대 소집 → 전철로 이동
  2. 다른 region 전투 구역 도착 → 임무 수행
  3. 플레이어 전술 지시 + 분대장 로컬 지시
  4. 임무 완료 → 전철/운송수단으로 Basement 복귀
- **Phase 스택 매핑**:
  - 평상시: `[LifePhase]`
  - 소집~임무: `[Command, Standby, LifePhase]`
  - 전투 시: `[CombatState, Command, Standby, LifePhase]`
  - 복귀~해산: Command/Standby pop → `[LifePhase]`
- **소집**: 캐릭터 성향 기반 자율 소집 (꼼꼼한 캐릭터=준비 후 집결, 성급한 캐릭터=즉시 집결)
- **다중 분대**: 독립 운영, 전환/포커스 불필요. 분대별 지휘 자세만 설정
- **시간 체계**: 기존 DES + 자동 시간 흐름 (시나리오 02 설정 기능 활용, 03은 기본값)

### 6.6 기존 문서(party-implementation.md) 반영 ✅ 확정
- **B 방식**: 기존 문서 폐기, party-design-notes.md를 새 명세로 발전
- 신규 문서와 현재 코드를 비교 검토하며 완성도를 높인 뒤 한번에 구현
- 기존 party-implementation.md에서 살릴 부분은 검토 시 선별 반영

---

## 7. 코드 검토 — 누락/보완 필요 항목

> 기존 party-implementation.md 및 현재 코드와 비교하여 발견된 항목.
> 구현 시점에 순차적으로 반영.

### 7.1 FSM 구현 시 주의사항

| 항목 | 내용 |
|------|------|
| **think() 루프 변경** | 현재 `top.update()` 1회 → 스택 위→아래 순회로 변경 |
| **LifePhase.update()** | 기존 5-tier inline 로직을 update() 내부로 이동, 항상 True 반환 |
| **"pop + return False" 패턴** | 기존 전투 상태들의 패턴 유지 가능 (의미만 변경: "pop 후 아래로 위임") |
| **동일 레벨 auto-pop** | 유지 (Flee→Desperate 등 전투 상태 교체에 활용) |
| **CombatState 재귀 호출** | L461 `return self.update(agent)` — 스택 순회로 대체 검토 |

### 7.2 기존 명세에서 보완할 상세 메커니즘

| 항목 | 중요도 | 출처 | 내용 |
|------|--------|------|------|
| **작업 명령 (Task Commands)** | HIGH | impl 5.5 | 파티 중 벌목/청소/제작 가능 (follow만이 아님). 임시 스케줄 교체 |
| **귀환 메커니즘** | HIGH | impl 6.2 | 파티 해산 시 NPC → home_region 입구 자동 귀환 (소프트락 방지) |
| **PARTY_BEHAVIOR dict** | HIGH | impl 3.2 | 캐릭터별 설정: recruitable, follow_distance, combat_join_in_party, leaves_if_hostile 등 |
| **명령 거부 공식** | MEDIUM | impl 5.6 | `refusal_chance = rebellion * 0.008 - submission * 0.005` |
| **NPC 리더 override 규칙** | MEDIUM | impl 7.3 | PARTY_LEADER_BEHAVIOR: auto_style + override_rules + override_chance |
| **Region 텔레포트 동기화** | MEDIUM | impl 12.2 | 리더 RegionGate 통과 시 파티원 자동 동기화 |
| **가입 이중경로** | MEDIUM | impl 4.3 | 호감도 경로 (자발) vs 복종도 경로 (강제, 반발 위험) |
| **비전투 파티원** | MEDIUM | impl 13.1 | combat_join_in_party=False 옵션 (리나 등) |
| **date.py 상호배제** | LOW | impl 1.3 | 파티 중 데이트 불가 |
| **on_meet 쿨다운** | LOW | impl 20.2 | 파티원 인사 1시간 쿨다운 |
| **same-location idle** | LOW | impl 10.1 | 리더와 같은 위치 도착 시 brief idle 삽입 (시각적 안정) |
| **챕터 전환 reset** | LOW | impl 21.2 | chapters/__init__.py에 party.reset() 추가 |

---

## 8. 구현 명세

> 설계 확정 사항을 코드 수준으로 구체화한 명세.
> Section A~G 순서로 작성.

### 8.1 데이터 구조 (Section A) ✅ 확정

#### A1. Disposition — 지시 성향 (2D, 캐릭터 고유)

archetype(묘사 톤)과 **별개**인 전술 성향. 분대장의 판단 기준이 됨.

```
축 1: 공세 (Aggression)
  -1.0 방어/회복 ────── 0 ────── +1.0 돌격
  아군 회복, 엄호       균형      쉬지 않고 공격

축 2: 집중 (Focus)
  -1.0 수집형 ─────── 0 ─────── +1.0 목표형
  적 클리어, 아이템 수집  균형     목표 직행, 적 무시
```

파일 위치: `think/party_config.py`

```python
_COMMAND_DISPOSITION = {
    #              (공세,   집중)
    "sera":       (+0.7,  +0.3),   # 돌격형, 약간 목표 지향
    "mila":       (-0.6,  -0.3),   # 방어/회복, 약간 꼼꼼
    "lina":       (-0.7,  -0.8),   # 강한 지원형, 강한 수집형
    "yuki":       (+0.2,  +0.5),   # 약간 공세(정밀 타격), 목표형
    "ella":       (+0.4,  +0.7),   # 공세, 강한 목표 직행
    "faye":       (-0.3,  -0.6),   # 약간 방어, 수집형(상인 기질)
}
```

#### A2. Squad 클래스

```python
class Squad:
    def __init__(self, squad_id):
        self.squad_id = squad_id
        self.leader_id = None               # 리더 미지정 가능 (빈 분대)
        self.members = []                   # [unit_id, ...] (리더 제외)
        self.player_directive = "auto"      # 7종: auto/search/combat_stealth/
                                            #   combat_normal/combat_aggressive/
                                            #   retreat/wait
        self.orders = {}                    # {unit_id: Order}
        self.leader_traits = {}             # assign_leader() 시 생성
        self.leader_destination = None      # {"region_id", "location_id"} — 리더 이동 목적지 (E3)
```

- **분대 생성과 리더 지정은 별도** — 분대는 리더 없이도 존재
- `leader_traits`: 리더 지정 시 disposition 기반 생성, 교체 시 전체 교체
- 해산 시 객체 폐기

#### A3. Order 클래스

```python
class Order:
    def __init__(self, order_type, target=None,
                 priority=0.0, stealth=0.0):
        self.order_type = order_type    # "주타입" 또는 "주타입:부타입"
        self.target = target            # {region_id, location_id} 또는 None
        self.priority = priority        # -1.0 아이템 수집 ↔ +1.0 적 퇴치
        self.stealth = stealth          # 0.0 노출 ↔ 1.0 은밀
```

**콜론 계층형 order_type:**

| order_type | 설명 | target | priority/stealth |
|-----------|------|--------|-----------------|
| `"follow"` | 리더 따라가기 (기본) | — | 상속 |
| `"수색"` | 기본 수색 | 선택 | 반영 |
| `"수색:적"` | 적 수색 특화 | 선택 | 반영 |
| `"수색:경로"` | 미탐험 경로 탐색 | 선택 | 반영 |
| `"경계"` | 현위치 방어 | — | 반영 |
| `"경계:매복"` | 은밀 대기 + 기습 | — | 반영 |
| `"수집:*"` | 모든 아이템 | 선택 | 반영 |
| `"수집:재료"` | 재료 카테고리만 | 선택 | 반영 |
| `"수집:음식"` | 음식 카테고리만 | 선택 | 반영 |
| `"이동"` | 목표 지점 이동 | 필수 | stealth만 |
| `"대기"` | 현위치 정지 | — | — |
| `"대기:휴식"` | 정지 + 욕구 해소 허용 | — | — |

파싱: `main_type = order_type.split(":")[0]`, `sub_type = split[1] if ":" else "*"`

**stealth 동적 전환**: 은밀 이동 중 발각 → stealth 무효화 (전투 전환) → location 클리어 → stealth 복원

#### A4. 모듈 레지스트리 (party.py)

```python
_squads = {}            # {squad_id: Squad}
_unit_squad = {}        # {unit_id: squad_id} 역참조
_next_id = 0

def reset():
    """챕터 전환 시 호출 (chapters/__init__.py)"""
    global _next_id
    _squads.clear()
    _unit_squad.clear()
    _next_id = 0
```

- S02: 사실상 1개 (플레이어 파티)
- S03: 여러 개 (NPC 분대 × N)
- 싱글턴 제약은 게임플레이 레이어에서 관리 (데이터 구조는 다중 지원)

#### A5. Props 스키마

```
# 플레이어 can: props (focus 액션 제어용)
can:recruit = 0/1       # 모집 가능 (파티 미편성 or 정원 미달 시 1)
can:command = 0/1       # 지시 가능 (파티 편성 시 1)
can:disband = 0/1       # 해산 가능 (파티 편성 시 1)
```

상태는 모듈 dict(`_unit_squad`)로 관리, props는 UI 제어(can:)에만 사용.

#### A6. PARTY_BEHAVIOR — 멤버 설정

파일 위치: `think/party_config.py` (아키타입/disposition 기반 중앙 관리)

```python
_DEFAULT_PARTY_BEHAVIOR = {
    "recruitable": True,
    "recruit_affection": 40,
    "recruit_submission": 50,
    "follow_distance": 30,
    "combat_join_in_party": True,
    "leaves_if_hostile": True,
}

# disposition 기반 보정
_DISPOSITION_PARTY = {
    #                    affection  submission  distance  combat_join
    # aggressive(+,+):   낮음       낮음        가까움     True
    # defensive(-,*):     보통       보통        보통       True
    # supportive(-,-):    낮음       보통        가까움     False  (비전투)
    # ...
}

# 캐릭터 직접 오버라이드 (예외만)
_CHARACTER_PARTY_OVERRIDE = {}
```

#### A7. 전체 계층 정리

```
[불변] Disposition (2D)          → 분대장 전술 판단 기준
         공세 × 집중
         파일: think/party_config.py

[가변] Order 파라미터            → 임무마다 조정
         priority (아이템↔적)
         stealth (노출↔은밀)
         파일: Order 클래스

[관계] 순종성                    → 명령 불복 판정
         반발/복종 prop (기존 관계 시스템)
         분대장↔플레이어, 분대원↔분대장 각각 적용
```

### 8.2 모듈 API (Section B) ✅ 확정

파일 위치: `party.py` (시나리오 python/ 루트)

#### B1. 생명주기

```python
def create_squad() -> int:
    """빈 분대 생성, squad_id 반환
    - 리더/멤버 없는 상태로 생성
    - S02: 플레이어가 1개 생성
    - S03: 시나리오 초기화에서 복수 생성
    """

def disband_squad(squad_id):
    """분대 해산
    - 전 멤버 정리 (remove_member 순차 호출)
    - 리더 해제 (remove_leader)
    - Squad 객체 폐기
    - on_squad_disbanded 훅 호출
    """

def reset():
    """챕터 전환 (chapters/__init__.py에서 호출)
    - 전체 분대 무조건 폐기 (disband 없이 직접 클리어)
    """
```

#### B2. 리더 관리

```python
def assign_leader(squad_id, leader_id):
    """리더 지정 (분대 생성과 별도)
    - leader_traits 생성 (party_config.build_leader_traits)
    - _unit_squad 등록
    - on_leader_changed 훅 호출
    """

def remove_leader(squad_id):
    """리더 해제
    - leader_id = None, leader_traits 클리어
    - _unit_squad에서 제거
    - 기존 orders 유지 (멤버들은 마지막 지시 계속 수행)
    - on_leader_changed 훅 호출
    """

def change_leader(squad_id, new_leader_id):
    """리더 교체 (remove + assign 일괄)
    - 이전 리더 → 멤버로 전환
    - 새 리더 → 멤버에서 제거 후 리더로
    - leader_traits 전체 교체
    """
```

#### B3. 멤버 관리

```python
def add_member(squad_id, unit_id):
    """멤버 등록
    - members 리스트에 추가
    - _unit_squad 역참조 등록
    - FSM push 하지 않음 (지시가 없으면 LifePhase만)
    - 이미 orders에 해당 unit 지시가 있으면 → CommandPhase 명시적 push
    - on_member_added 훅 호출
    """

def remove_member(squad_id, unit_id):
    """멤버 제거
    - members에서 제거
    - _unit_squad에서 제거
    - orders에서 해당 unit 제거
    - pop_schedule (follow 해제)
    - Command/StandbyPhase가 스택에 있으면 pop
    - on_member_removed 훅 호출
    """
```

**FSM push 정책:**
- 멤버 등록 시 기본 = **push 없음** (생활 phase만)
- 지시 부여 시 = **CommandPhase 명시적 push** (set_order에서)
- 지시 취소/해산 시 = **명시적 pop**

#### B4. 조회

```python
def get_squad(squad_id) -> Squad | None:
def get_squad_by_unit(unit_id) -> Squad | None:
def is_in_squad(unit_id) -> bool:
def is_squad_leader(unit_id) -> bool:
def get_squad_members(squad_id) -> list[int]:    # 리더 제외
def get_all_unit_ids(squad_id) -> list[int]:     # 리더 포함
def get_all_squads() -> list[Squad]:             # S03: 전체 분대 목록
```

#### B5. 지휘/지시

```python
def set_directive(squad_id, directive: str):
    """플레이어 지휘 설정 (7종)
    - Squad.player_directive 갱신
    - 분대장 다음 think()에서 orders 재생성
    """

def get_directive(squad_id) -> str:

def set_order(squad_id, unit_id, order: Order):
    """분대장 → 분대원 지시 설정 (분대장 think() 내부에서 호출)
    - Squad.orders[unit_id] = order
    - 해당 멤버에 CommandPhase 없으면 push
    - push_schedule(FOLLOW_SCHEDULE) (follow 지시 시)
    """

def clear_order(squad_id, unit_id):
    """지시 해제
    - orders에서 제거
    - CommandPhase pop
    - pop_schedule (follow 해제)
    """

def get_order(squad_id, unit_id) -> Order | None:
    """분대원이 자기 지시 조회 (분대원 think() 내부에서 호출)"""
```

#### B6. 이벤트 훅

```python
def on_member_added(squad_id, unit_id):
    """멤버 등록 후 호출 — 향후 대화 시스템 연동용"""
    pass

def on_member_removed(squad_id, unit_id):
    """멤버 제거 후 호출 — 향후 귀환/대화 연동용"""
    pass

def on_leader_changed(squad_id, old_leader_id, new_leader_id):
    """리더 변경 후 호출 — 향후 분대 성격 갱신 연동용"""
    pass

def on_squad_disbanded(squad_id):
    """해산 후 호출 — 향후 이벤트/대화 연동용"""
    pass

def on_directive_changed(squad_id, old_directive, new_directive):
    """지휘 변경 후 호출 — 향후 로그/대화 연동용"""
    pass
```

#### B7. 설계 원칙 정리

| 원칙 | 내용 |
|------|------|
| **분대 ≠ 리더** | 분대는 리더 없이 존재 가능 |
| **등록 ≠ 지시** | 멤버 등록은 FSM 변경 없음, 지시 부여 시 명시적 push |
| **지시 ≠ 활동** | Order는 의도, 실제 행동은 CommandPhase.update()에서 결정 |
| **훅 선제 배치** | 지금 사용하지 않더라도 확장 지점 마련 |

### 8.3 플레이어 인터페이스 (Section C) ✅ 확정

#### C1. 역할 기반 계층 접근

S02와 S03은 **구조적으로 동일**. 플레이어가 어느 계층에서 개입하느냐만 다름.

```
NPC 리더 분대:
  플레이어 → [지휘(Directive)] → NPC 리더 AI → [지시(Order)] → 분대원

플레이어 리더 분대:
  플레이어 → [지시(Order)] → 분대원 (지휘 계층 불필요)
```

| 상황 | 지휘(Directive) | 지시(Order) |
|------|---------------|------------|
| NPC 리더 분대 | 플레이어가 설정 | NPC 리더가 생성 |
| 플레이어 리더 분대 | 사용 안 함 | 플레이어가 직접 설정 |
| 리더 없는 분대 | 사용 안 함 | 없음 (LifePhase만) |

#### C2. can: props (역할에 따라 토글)

```python
# player.py props 추가
"can:create_squad": 1,       # 분대 생성 (항상 가능)
"can:disband_squad": 0,      # 해산 (분대 존재 시 1)
"can:assign_leader": 0,      # 리더 지정 (리더 없는 분대 존재 시 1)
"can:set_directive": 0,      # 지휘 변경 (NPC 리더 분대 존재 시 1)
"can:set_order": 0,          # 지시 (플레이어 리더 분대 존재 시 1)
"can:recruit": 0,            # 모집 (분대에 빈자리 시 1)
```

#### C3. UI 배치

**Tab 뷰 전환 (신규 — [system-ui.md](system-ui.md#tab-뷰-전환-시스템-계획) 참조):**
- Situation Tab 1: 분대 현황 (전체 분대 목록, 멤버 상태)
- Unit Tab 1: 분대원 상세 (해당 NPC의 지시/상태/disposition)
- Focus 유지, Tab 키로 콘텐츠만 전환

**분대 관리 (footer / situation UI + dialog):**
- 분대 편성/해산
- 지휘 변경 (NPC 리더 분대)
- 분대 선택 UI (**신규 구현 필요** — 기존에 목록 선택 패턴 없음)

**NPC 포커스:**
```python
# 각 NPC actions에 추가
"call:recruit:분대 모집#",          # can:recruit 체크
"call:assign_leader:분대장 지정#",   # can:assign_leader 체크
```

**멤버 포커스 (플레이어 리더 분대):**
```python
# 분대 멤버인 NPC 포커스 시 추가 액션
"call:set_order:지시#",             # can:set_order 체크
```

#### C4. UI 흐름

```
분대 편성:
  footer/situation → "분대 편성" → create_squad()
  → can: props 갱신

리더 지정:
  NPC 포커스 → "분대장 지정" → 분대 선택 dialog → assign_leader()

모집:
  NPC 포커스 → "분대 모집" → 분대 선택 dialog → add_member()
  전제: recruit_affection OR recruit_submission 충족

지휘 변경 (NPC 리더):
  footer/situation → "지휘 변경" → 분대 선택 → directive 7종 선택
  → set_directive()

지시 (플레이어 리더):
  멤버 NPC 포커스 → "지시" → order_type 선택 → set_order()

해산:
  footer/situation → "분대 해산" → 분대 선택 → disband_squad()
```

#### C5. 분대 수 제한

데이터 레이어에서 분대 수 제한 **없음**. S02/S03 모두 복수 분대 가능.
- S02: 주로 1개 사용 (플레이어 리더)
- S03: 복수 분대 (NPC 리더)
- S03 + 플레이어 화신: 1개는 플레이어 리더(직접 지시) + 나머지 NPC 리더(지휘)

### 8.4 FSM Phase 로직 (Section D) ✅ 확정

#### D1. think() 루프 변경

```python
# 현재 (단일 top)
if self._fsm_stack:
    top = self._fsm_stack[-1]
    if top.update(self):
        return

# 변경 후 (스택 위→아래 순회)
for state in reversed(list(self._fsm_stack)):
    if state.update(self):
        return   # 첫 True에서 멈춤
```

- 비파티 NPC: `[LifePhase]` → LifePhase.update() → True (기존과 동일)
- 파티 NPC: `[CommandPhase, StandbyPhase, LifePhase]` → 위부터 순회

#### D2. 레벨 배치

```
Life(0) < Standby(3) < Command(5) < Combat(10) < CombatSub(20) < Transit(30)
```

```python
LV_LIFE        =  0   # 기존
LV_STANDBY     =  3   # 신규
LV_COMMAND     =  5   # 신규
LV_COMBAT      = 10   # 기존
LV_COMBAT_SUB  = 20   # 기존
LV_TRANSIT     = 30   # 기존
```

#### D3. CommandPhase

```python
class CommandPhase(FSMState):
    state_type = "command"
    level = LV_COMMAND  # 5

    _ORDER_HANDLERS = {
        "follow":  "_handle_order_follow",
        "수색":    "_handle_order_search",
        "경계":    "_handle_order_guard",
        "수집":    "_handle_order_collect",
        "이동":    "_handle_order_move",
        "대기":    "_handle_order_wait",
    }

    def update(self, agent) -> bool:
        order = party.get_order_for_unit(agent.unit_id)
        if order is None:
            return False   # 지시 없음 → 아래(Standby/Life)로 위임

        main_type = order.order_type.split(":")[0]
        handler_name = self._ORDER_HANDLERS.get(main_type)
        if handler_name is None:
            return False

        handler = getattr(agent, handler_name, None)
        if handler is None:
            return False

        return handler(order)

    def exit(self, agent):
        # order 관련 _memory 정리
        for key in list(agent._memory):
            if key.startswith("order_"):
                agent._memory[key] = None
```

#### D4. Order 핸들러 구조

파일 위치: `think/order_handlers.py` (신규, activity handler와 동일 패턴)

기존 `_memory` + phase 패턴 재활용:

```python
def _handle_order_collect(self, order):
    """수집 지시 — multi-phase (기존 activity handler 패턴)"""
    sub = order.order_type.split(":")[1] if ":" in order.order_type else "*"
    phase = self._memory.get("order_phase")

    if phase is None:
        items = self._scan_collectibles(sub)
        if not items:
            return False  # 수집 대상 없음 → 아래로 위임
        self._memory["order_phase"] = "going"
        self._memory["order_target"] = items[0]
        self._move_to(items[0]["location"], "수집")
        return True

    elif phase == "going":
        # 도착 → 수집 실행
        self._memory["order_phase"] = "taking"
        # ... take item ...
        return True

    elif phase == "taking":
        # 완료 → 다음 아이템 or 재탐색
        self._memory["order_phase"] = None
        return True

    return False

def _handle_order_follow(self, order):
    """리더 따라가기"""
    squad = party.get_squad_by_unit(self.unit_id)
    if not squad or not squad.leader_id:
        return False
    leader_loc = morld.get_unit_location(squad.leader_id)
    my_loc = self.get_location()
    if my_loc == leader_loc:
        self._insert_idle_job("대기", 5 * 60_000)
        self._action_taken = True
        return True
    self._move_to({"region_id": leader_loc[0],
                    "location_id": leader_loc[1]}, "이동")
    return True

def _handle_order_guard(self, order):
    """경계 — 현위치 idle + 적 감지"""
    # priority > 0 → 적극적 적 탐색
    # priority < 0 → 방어만 (피격 시만 반격)
    self._insert_idle_job("경계", 5 * 60_000)
    self._action_taken = True
    return True

def _handle_order_wait(self, order):
    """대기 — 정지"""
    sub = order.order_type.split(":")[1] if ":" in order.order_type else ""
    if sub == "휴식":
        return False  # 생활 phase로 위임 (욕구 해소 허용)
    self._insert_idle_job("대기", 5 * 60_000)
    self._action_taken = True
    return True
```

#### D5. StandbyPhase

분대 소속이지만 지시가 없는 상태. 기본적으로 현위치 유지.

```python
class StandbyPhase(FSMState):
    state_type = "standby"
    level = LV_STANDBY  # 3

    def update(self, agent) -> bool:
        if not party.is_in_squad(agent.unit_id):
            return False   # 분대 아님 → 생활로

        # 욕구 위험 체크 (기존 tier 3-4 임계치 재사용)
        if self._needs_critical(agent):
            return False   # 생활 phase에서 처리

        # 현위치 idle
        agent._insert_idle_job("대기", 5 * 60_000)
        agent._action_taken = True
        return True

    def _needs_critical(self, agent):
        """기존 tier 3-4 임계치: 배변 70, 피로 80, 청결 70 등"""
        import needs
        npc_id = agent.unit_id
        if needs.get_need(npc_id, "배변") >= 70:
            return True
        if needs.get_need(npc_id, "피로") >= 80:
            return True
        # ... 추가 욕구 체크
        return False
```

#### D6. 성격 기반 지시 변형 (미구현, 향후 확장)

> 캐릭터의 성향/욕심에 따라 지시를 "자기 식으로 해석"하는 메커니즘.
> 거부(불복)와 다름 — 지시를 수행하되 디테일이 달라짐.
>
> 예시:
> - 음식 탐욕 캐릭터: `수집:재료` 지시 → 음식도 함께 수집
> - 전투광 캐릭터: `수색` 지시 → 적 발견 시 교전 우선
> - 수집벽 캐릭터: `이동` 지시 → 경로 상 아이템 줍기
>
> 구현 시점: 기본 CommandPhase 안정화 후. 핸들러 내부에서 disposition/성격 참조.

#### D7. 기존 상태와의 상호작용

```
전투 발생 시:
  [CombatState, CommandPhase, StandbyPhase, LifePhase]
  CombatState.update() → True (전투 처리)
  CommandPhase 이하 호출되지 않음

전투 종료 시:
  CombatState pop → [CommandPhase, StandbyPhase, LifePhase]
  CommandPhase.update() → 기존 지시 계속 수행

GateTransit 중:
  [GateTransitState, CombatState?, CommandPhase, StandbyPhase, LifePhase]
  Transit이 최상위 → 이동 완료까지 다른 phase 차단
```

---

### 8.5 Section E: 이동/동기화

#### E1. Follow 메커니즘

리더를 따라가는 기본 이동. date.py의 FOLLOW_SCHEDULE 패턴 재사용.

```python
# party 모듈 내부

PARTY_FOLLOW_SCHEDULE = [
    {"name": "따라가기", "action": "follow", "start": 0,
     "end": MILLIS_PER_DAY, "activity": "분대행동"}
]

def _start_follow(unit_id, leader_id):
    """멤버에게 follow 스케줄 push + follow job 설정"""
    agent = _get_agent(unit_id)
    if agent:
        agent.push_schedule(PARTY_FOLLOW_SCHEDULE)
    morld.set_npc_job(unit_id, "follow", MILLIS_PER_DAY, leader_id)

def _stop_follow(unit_id):
    """follow 스케줄 pop + 원래 스케줄 복귀"""
    agent = _get_agent(unit_id)
    if agent:
        agent.pop_schedule()
```

**Order → follow 관계:**
- `이동` order → follow 활성화 (리더를 따라감)
- `수집`, `경계` 등 → follow 비활성화 (독립 행동)
- `대기` → follow 비활성화 (현위치 정지)

#### E2. Order 변경 시 전환

Order 변경 = **기존 스케줄 pop → 새 로직 진입** (순차, 동시 아님).

```
현재: 이동(follow) 중
  ↓
플레이어: set_order(unit_id, "수집:재료")
  ↓
1. _stop_follow(unit_id)         # follow 스케줄 pop
2. squad.orders[unit_id] = new_order  # 새 Order 설정
3. 다음 think() → CommandPhase.update() → _handle_order_collect()
```

**핵심 원칙:** 모든 Order 전환은 이전 상태를 정리(pop)한 후 새 로직에 진입.
follow 중이든, 수집 중이든, 경계 중이든 동일한 전환 흐름.

```python
def set_order(unit_id, order):
    """기존 order 정리 → 새 order 설정"""
    squad = get_squad_by_member(unit_id)
    if not squad:
        return

    old_order = squad.orders.get(unit_id)
    if old_order:
        _cleanup_order(unit_id, old_order)  # 이전 follow/스케줄 정리

    squad.orders[unit_id] = order
    # 다음 think()에서 CommandPhase가 새 order 처리
```

#### E3. Region Gate 동기화

Gate 통과는 **분대 단위**. 같은 분대의 모든 멤버가 함께 이동.

```
리더 cross-location 이동 시:
  1. squad.leader_destination = target 기록
  2. 리더: 정상 GateTransitState push (개별 이동)
  3. 멤버: 다음 think()에서 leader_destination 감지
     → 자신도 _move_to(leader_destination) → 개별 GateTransitState
  4. 각자 도착 (시차 자연 발생)
  5. 도착 후 기존 order/follow 재개
```

**Squad에 목적지 필드 추가 (A2 보완):**
```python
class Squad:
    def __init__(self, squad_id):
        ...
        self.leader_destination = None   # {"region_id": ..., "location_id": ...}
```

**리더 이동 시 목적지 기록:**
```python
# _move_to() 또는 GateTransitState.enter()에서 호출

def _on_leader_move(leader_id, target):
    """리더의 cross-location 이동 시 분대에 목적지 기록"""
    squad = get_squad_by_unit(leader_id)
    if not squad or squad.leader_id != leader_id:
        return
    squad.leader_destination = {
        "region_id": target["region_id"],
        "location_id": target["location_id"],
    }

def _on_leader_arrived(leader_id):
    """리더 도착 시 목적지 클리어"""
    squad = get_squad_by_unit(leader_id)
    if not squad or squad.leader_id != leader_id:
        return
    squad.leader_destination = None
```

**멤버 측 감지 (CommandPhase/StandbyPhase):**
```python
def _check_leader_destination(self, agent):
    """리더 목적지 확인 → 다른 region이면 따라감"""
    squad = party.get_squad_by_member(agent.unit_id)
    if not squad or not squad.leader_destination:
        return False

    dest = squad.leader_destination
    # 특수 region 제외 (merchant_limbo 등)
    if dest["region_id"] in _EXCLUDED_REGIONS:
        return False

    loc = agent.get_location()
    if loc and loc[0] == dest["region_id"]:
        return False  # 이미 같은 region

    # 따라가기
    agent._move_to(dest)
    return True

_EXCLUDED_REGIONS = {10}  # merchant_limbo
```

**120분 Gate 시나리오:**
```
t=0    플레이어(리더) Gate 진입
       → squad.leader_destination = {region: 3, location: 0}
       → 플레이어: approaching → transiting (상태:이동중=1, 숨김)

t=1~   멤버들의 다음 think()
       → _check_leader_destination() → 목적지 감지
       → 각 멤버 _move_to(destination) → 개별 GateTransitState push
       → 각자 gate로 걸어감 → 각자 transit

t=?    멤버들 각자 도착 (경로/거리에 따라 시차)
       → 리더보다 먼저 도착 가능 → StandbyPhase idle (대기)

t=120  플레이어 도착 → leader_destination 클리어
       → 생활 재개, 멤버들 follow/order 재개
```

**멤버 상태별 동작:**

| 멤버 상태 | 리더 Gate 진입 시 | 동작 |
|-----------|-------------------|------|
| follow 중 | 다음 think()에서 감지 | gate로 이동 → transit |
| 수집 중 | 다음 think()에서 감지 | 수집 중단 → gate 이동 |
| 경계 중 | 다음 think()에서 감지 | 경계 중단 → gate 이동 |
| 전투 중 | CombatState 차단 | 전투 종료 후 감지 → gate 이동 |
| 대기:휴식 | 다음 think()에서 감지 | gate로 이동 |

#### E4. 귀환 메커니즘

분대 해산 또는 멤버 제거 시 원래 스케줄로 복귀.

```python
def _return_to_life(unit_id):
    """분대 이탈 → 일상 복귀"""
    # 1. CommandPhase pop (있으면)
    # 2. StandbyPhase pop (있으면)
    # 3. follow 스케줄 pop (있으면)
    agent = _get_agent(unit_id)
    if not agent:
        return

    # FSM 스택에서 파티 관련 phase 제거
    agent._fsm_pop_by_type("command")
    agent._fsm_pop_by_type("standby")

    # follow 스케줄 정리
    _stop_follow(unit_id)

    # 원래 스케줄의 think()가 자연스럽게 재개
```

**귀환 이동:**
- 현재 위치가 home_region이 아니면 → 다음 think()에서 기존 스케줄이 귀환 처리
- 기존 movement_mixin의 `_handle_default_activity`가 목표 location으로 이동 시킴
- 별도 귀환 로직 불필요 — 기존 시스템이 자연 처리

#### E5. 이동 관련 제약

| 상황 | 동작 |
|------|------|
| 리더 gate 통과 | 목적지 기록 → 멤버 각자 개별 transit |
| 멤버 독자 gate 접근 | leader_destination 없으면 차단 (region 이탈 불가) |
| 리더 없는 분대 | leader_destination 없음 → 현재 region 유지 |
| 분대 해산 중 gate | 해산 처리 우선, transit 중이면 도착 후 해산 |
| follow 중 전투 | CombatState push → follow 일시 중단 → 전투 후 follow 재개 |
| 멤버 transit 중 리더 사망 | transit 완료 후 승계 판정 (E6) |

#### E6. 리더 승계 (Leader Succession)

리더가 사망/기절/도주 시 분대 등록 순서에 따라 승계.

```python
def _on_leader_incapacitated(squad_id, reason):
    """리더 전투불능 시 승계 처리

    reason: "death" / "faint" / "flee"
    트리거: CombatState 종료, survival faint/death 감지
    """
    squad = _squads.get(squad_id)
    if not squad:
        return

    # 등록 순서대로 승계 후보 탐색
    for member_id in squad.members:
        if not _is_capable(member_id):
            continue

        # 이탈 판정 (성격 기반)
        if _wants_to_leave(member_id, reason):
            remove_member(squad_id, member_id)  # 분대 이탈
            continue

        # 승계 성공
        change_leader(squad_id, member_id)
        return

    # 승계 실패 → 리더 없는 분대
    remove_leader(squad_id)


def _is_capable(unit_id):
    """전투/행동 가능 여부"""
    import survival
    if survival.get_health(unit_id) <= 0:
        return False  # 사망
    if survival.is_fainted(unit_id):
        return False  # 기절
    return True
```

**성격 기반 이탈 판정:**
```python
def _wants_to_leave(unit_id, reason):
    """리더 상실 시 이탈 의사

    판단 기준:
    - BATTLE_BEHAVIOR.retreat_threshold: 높으면 겁쟁이 → 이탈 경향
    - disposition 공세: 낮으면 비전투 성향 → 이탈 경향
    - reason: death > faint > flee 순으로 이탈 확률 증가
    """
    from assets.characters import get_instance
    char = get_instance(unit_id)
    if not char:
        return False

    behavior = getattr(char, 'BATTLE_BEHAVIOR', {})
    retreat = behavior.get("retreat_threshold", 0.5)

    unique_id = _get_unique_id(unit_id)
    aggression, _ = get_disposition(unique_id)

    leave_chance = 0.0
    if retreat > 0.7:
        leave_chance += 0.3        # 겁쟁이
    if aggression < -0.3:
        leave_chance += 0.2        # 비공세
    if reason == "death":
        leave_chance += 0.2        # 사망은 충격 큼
    elif reason == "faint":
        leave_chance += 0.1

    return random.random() < leave_chance
```

**캐릭터별 예상:**

| 캐릭터 | retreat | aggression | 이탈 경향 | 비고 |
|---------|---------|------------|----------|------|
| 세라 | 0.15 | +0.7 | 극히 낮음 | 승계 1순위 |
| 엘라 | 0.20 | +0.4 | 낮음 | 승계 적합 |
| 리나 | 0.30 | -0.7 | 약간 있음 | 비공세이나 따름 |
| 유키 | 0.90 | +0.2 | 높음 | 겁쟁이 |
| 밀라 | 0.80 | -0.6 | 높음 | 비전투 + 겁쟁이 |
| 페이 | 0.80 | -0.3 | 있음 | 상인 기질, 위험 회피 |

**기절 회복 시:**
- 이전 리더가 기절에서 회복 → **새 리더 유지** (자동 복귀 없음)
- 원래 리더 복귀는 플레이어가 수동으로 `change_leader()` 호출

**트리거 등록:**
```python
# party.py 초기화 시

def _check_leader_status():
    """1시간마다: 리더 상태 체크"""
    for squad_id, squad in _squads.items():
        if squad.leader_id is None:
            continue
        if not _is_capable(squad.leader_id):
            _on_leader_incapacitated(squad_id, "faint")

# 또는 즉시 감지: survival.on_faint / combat.on_death 이벤트 훅
```

---

### 8.6 Section F: 캐릭터 통합

#### F1. 모집 조건 (Recruit Conditions)

NPC를 분대에 모집하려면 관계 조건 충족 필요.
기존 `관계:{player}:호감/복종` props 재사용.

```python
# think/party_config.py

_DEFAULT_RECRUIT_CONDITION = {
    "affection": 40,      # 호감 >= 40 (기본)
    "submission": 50,      # 또는 복종 >= 50 (대안 경로)
    "rebellion_max": 50,   # 반발 < 50 필수 (초과 시 모집 불가)
}

# 캐릭터별 오버라이드 (예외만)
_RECRUIT_OVERRIDE = {
    "sera":  {"affection": 50},            # 신뢰 요구 높음
    "yuki":  {"affection": 30},            # 쉽게 따라옴
    "ella":  {"affection": 60, "submission": 40},  # 높은 호감 OR 복종
    "faye":  {"affection": 35},            # 상인 기질, 이해관계면 동행
}
```

**모집 판정 흐름:**
```
recruit(npc_id) 호출
  ↓
1. 조건 조회: _RECRUIT_OVERRIDE.get(unique_id, _DEFAULT_RECRUIT_CONDITION)
2. props 읽기: 관계:{player}:호감, 관계:{player}:복종, 관계:{player}:반발
3. 판정:
   - 반발 >= rebellion_max → 거절 (무조건)
   - 호감 >= affection OR 복종 >= submission → 수락
   - 아니면 → 거절
4. 수락 시: party.add_member(squad_id, npc_id) 호출
```

**NPC 리더가 모집하는 경우 (S03):**
- `관계:{leader_name}:호감` 대신 `관계:{leader_name}:신뢰` 사용
- NPC-NPC 관계 prop은 이미 존재 (예: `관계:세라:신뢰`)
- 별도 판정 함수: `can_recruit_by_npc(leader_id, target_id)`

#### F2. 불복 공식 (Disobedience Formula)

Order를 받아도 반발이 높으면 지시를 거부하거나 변형할 수 있음.

```python
# think/party_config.py

def check_disobedience(unit_id, leader_id, order):
    """불복 판정 — True면 지시 거부

    판정 요소:
    - 반발: 높을수록 거부 확률 증가
    - 복종: 높을수록 거부 확률 감소
    - order 위험도: 위험한 지시일수록 거부 확률 증가
    """
    props = morld.get_unit_props(unit_id) or {}
    leader_name = _get_name(leader_id)

    rebellion = props.get(f"관계:{leader_name}:반발", 0)
    submission = props.get(f"관계:{leader_name}:복종", 0)

    # 기본 거부 확률: (반발 - 복종) / 200
    # 범위: -0.5 ~ +0.5
    base_chance = (rebellion - submission) / 200.0

    # order 위험도 보정
    risk = _ORDER_RISK.get(order.order_type.split(":")[0], 0.0)
    chance = base_chance + risk

    # 최종: 0% ~ 80% 클램프
    chance = max(0.0, min(0.8, chance))

    return random.random() < chance
```

**Order 위험도 테이블:**
```python
_ORDER_RISK = {
    "이동": 0.0,       # 안전 → 거부 보정 없음
    "대기": 0.0,
    "수집": 0.05,      # 약간 위험
    "수색": 0.1,       # 미지 탐색
    "경계": 0.1,
    "전투": 0.2,       # 위험
    "후퇴": -0.1,      # 안전해지므로 거부 감소
}
```

**불복 시 동작:**
```
CommandPhase.update()
  ↓
order = squad.orders[unit_id]
  ↓
check_disobedience() → True (거부)
  ↓
1. 불복 리액션 (대사 출력, 향후)
2. return False → 생활 phase로 위임 (잠시 쉬는 것처럼 보임)
3. 다음 think()에서 다시 판정 (매번 새 확률 → 결국 수행할 수도)
```

**불복 불가 조건 (무조건 복종):**
- `복종 >= 80`: 절대 복종 (거부 확률 항상 0%)
- `order_type == "후퇴"`: 도망은 거부하지 않음

#### F3. party_config.py 전체 구조

```python
# scenarios/scenario02/python/think/party_config.py
"""
파티 시스템 캐릭터 설정 — 중앙 관리
아키타입(묘사 톤)과 별도인 전술/분대 설정을 관리.
캐릭터 파일 부담 최소화.
"""

# ========================================
# A1. Disposition — 지시 성향 (2D)
# ========================================
_COMMAND_DISPOSITION = {
    #              (공세,   집중)
    "sera":       (+0.7,  +0.3),
    "mila":       (-0.6,  -0.3),
    "lina":       (-0.7,  -0.8),
    "yuki":       (+0.2,  +0.5),
    "ella":       (+0.4,  +0.7),
    "faye":       (-0.3,  -0.6),
}

# ========================================
# F1. 모집 조건
# ========================================
_DEFAULT_RECRUIT_CONDITION = {
    "affection": 40,
    "submission": 50,
    "rebellion_max": 50,
}

_RECRUIT_OVERRIDE = {
    "sera":  {"affection": 50},
    "yuki":  {"affection": 30},
    "ella":  {"affection": 60, "submission": 40},
    "faye":  {"affection": 35},
}

# ========================================
# F2. 불복 위험도
# ========================================
_ORDER_RISK = {
    "이동": 0.0, "대기": 0.0,
    "수집": 0.05, "수색": 0.1, "경계": 0.1,
    "전투": 0.2, "후퇴": -0.1,
}

# ========================================
# A6. 기본 분대 행동
# ========================================
_DEFAULT_PARTY_BEHAVIOR = {
    "recruitable": True,
    "follow_distance": 30,
    "combat_join_in_party": True,
    "leaves_if_hostile": True,
}

# ========================================
# 공개 API
# ========================================

def get_disposition(unique_id):
    """Disposition 2D 조회 (기본값: 0.0, 0.0)"""
    return _COMMAND_DISPOSITION.get(unique_id, (0.0, 0.0))

def get_recruit_condition(unique_id):
    """모집 조건 조회 (기본 + 오버라이드 병합)"""
    base = dict(_DEFAULT_RECRUIT_CONDITION)
    override = _RECRUIT_OVERRIDE.get(unique_id, {})
    base.update(override)
    return base

def can_recruit(unit_id, player_id):
    """모집 가능 여부 판정"""
    ...

def check_disobedience(unit_id, leader_id, order):
    """불복 판정"""
    ...

def build_leader_traits(unique_id):
    """리더 특성 생성 (assign_leader 시 호출)"""
    aggression, focus = get_disposition(unique_id)
    return {
        "aggression": aggression,
        "focus": focus,
        "unique_id": unique_id,
    }
```

#### F4. BATTLE_BEHAVIOR와의 관계

기존 `BATTLE_BEHAVIOR`는 **비파티 상태의 전투 AI**. 파티 참여 시 동작이 달라짐.

```
비파티 상태:
  BATTLE_BEHAVIOR.combat_style → 개별 전투 AI
  (sera: aggressive, yuki: evasive, ...)

파티 상태:
  Order.order_type → CommandPhase가 전투 참여 여부 결정
  BATTLE_BEHAVIOR는 전투 진입 후의 세부 AI로만 사용

우선순위:
  CommandPhase(파티 지시) > BATTLE_BEHAVIOR(개인 전투 성향)
```

**변경 사항:**
- `BATTLE_BEHAVIOR.join_combat`: 파티 상태에서는 무시 (Order가 결정)
- `BATTLE_BEHAVIOR.retreat_threshold`: 파티 상태에서도 유지 (생존 본능)
- `BATTLE_BEHAVIOR.combat_style`: 전투 진입 후 세부 행동으로 유지

#### F5. 캐릭터 파일 변경 사항

캐릭터 파일에는 **최소한의 추가만**:

```python
# 각 캐릭터 Character 클래스의 actions에 추가

# sera.py 등 모든 NPC
"call:recruit:분대 모집#",           # can:recruit 체크 (base.py에서 처리)
"call:assign_leader:분대장 지정#",    # can:assign_leader 체크
"call:set_order:지시#",              # can:set_order 체크 (분대원일 때만)
```

- 모집/불복 조건 → party_config.py (중앙 관리)
- 모집 대사/거절 대사 → 캐릭터 TALK_RULES에 추가 (향후)
- Focus 액션 → base.py에서 공통 처리 가능

---

### 8.7 Section G: 기존 시스템 연동

#### G1. 전투 시스템 연동

**FSM 레벨 관계:**
```
LV_LIFE = 0       ← LifePhase
LV_STANDBY = 3    ← StandbyPhase (분대 대기)
LV_COMMAND = 5    ← CommandPhase (분대 지시)
LV_COMBAT = 10    ← CombatState (전투)
LV_COMBAT_SUB = 20  ← FleeState/ResignationState/DesperateState
LV_TRANSIT = 30   ← GateTransitState
```

전투가 파티 지시보다 상위 → 전투 중에는 CommandPhase 차단됨.
전투 종료(pop) → CommandPhase 재개.

**전투 합류 (combat.check_npc_combat_join) 변경:**
```python
# 현재: BATTLE_BEHAVIOR.join_combat 체크
# 변경: 파티 상태 우선

def check_npc_combat_join(region_id, location_id):
    for unit_id, agent in think.get_all_agents().items():
        # 파티 멤버인 경우
        squad = party.get_squad_by_member(unit_id)
        if squad:
            order = squad.orders.get(unit_id)
            if order:
                main_type = order.order_type.split(":")[0]
                if main_type == "전투":
                    joinable.append(unit_id)     # 전투 지시 → 합류
                elif main_type == "경계":
                    joinable.append(unit_id)     # 경계 지시 → 합류
                # 수집/대기/이동 → 합류 안 함
                continue

        # 비파티: 기존 BATTLE_BEHAVIOR 로직 유지
        behavior = getattr(char, 'BATTLE_BEHAVIOR', {})
        if behavior.get("join_combat"):
            joinable.append(unit_id)
```

**전투 종료 후 처리:**
- CombatState pop → CommandPhase.update() 재개
- 기존 order 유지 (전투 전 수집 중이었으면 수집 재개)
- 파티원 전원 생존 여부 체크 (사망/기절 시 order 정리)

#### G2. 데이트 시스템 상호 배제

데이트와 파티 follow는 **같은 스케줄 스택**을 사용 (push/pop).
동시 활성화 시 LIFO로 마지막 push가 우선.

**원칙: 상호 배제 (동시 불가)**

```
데이트 중 모집 시도 → 거절 (데이트 우선)
파티원에게 데이트 시도 → 거절 (파티 우선) 또는 일시 이탈
```

**구현:**
```python
# date.py — 모집 차단
def _start_date(player_id, partner_id):
    # 파티 멤버 체크
    if party.is_in_squad(partner_id):
        # 선택지: 데이트 거절 OR 파티 일시 이탈
        # 우선은 거절 (단순)
        return False
    ...

# party.py — 데이트 중 차단
def add_member(squad_id, unit_id):
    import date
    if date.is_on_date(unit_id):
        return False   # 데이트 중 모집 불가
    ...
```

**향후 확장**: 파티 일시 이탈 → 데이트 → 데이트 종료 → 파티 복귀.
현재 스펙에서는 **단순 상호 배제**로 시작.

#### G3. 스케줄 스택 정리

스케줄 스택 사용 현황:

```
[0]: base_schedule      ← 기본 (보호됨, pop 불가)
[1]: follow_schedule    ← 데이트 or 파티 (하나만)
```

**파티 follow 스케줄:**
```python
PARTY_FOLLOW_SCHEDULE = [
    {"name": "따라가기", "action": "follow",
     "start": 0, "end": MILLIS_PER_DAY, "activity": "분대행동"}
]
```

date.py의 FOLLOW_SCHEDULE과 구조 동일, `activity`만 다름 ("데이트" vs "분대행동").
→ `activity` 필드로 현재 follow 이유 구분 가능.

**스케줄 vs FSM 역할 분리:**
| 시스템 | 스케줄 스택 | FSM 스택 |
|--------|-----------|---------|
| 데이트 | push (follow) | 미사용 |
| 파티 follow | push (follow) | StandbyPhase / CommandPhase |
| 파티 독립행동 | push 안 함 | CommandPhase (독자 이동) |
| 전투 | 미사용 | CombatState |

→ 파티는 **FSM + 스케줄 동시 사용**. follow 시에만 스케줄 push.

#### G4. 챕터 전환 연동

`chapters/__init__.py`의 `load_chapter()`에 추가:

```python
# 기존 reset() 호출 목록 (22개) 이후 추가
import party
party.reset()                # 23번째
```

`party.reset()`:
- `_squads.clear()` — 전체 분대 폐기
- `_unit_squad.clear()` — 역참조 클리어
- FSM 스택 정리 불필요 — `think.reset()`이 전체 agent 폐기

#### G5. 이벤트 훅 연동

파티 시스템이 등록할 이벤트:

```python
# party.py 초기화 시

from events import subscribe_time_elapsed

# 1. 시간 경과 — 충성도/결속 변화 (향후)
subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)

def _on_time_elapsed(elapsed_ms):
    """1시간마다: 분대 상태 업데이트"""
    # 향후: 충성도 감소, 결속 변화 등
    pass
```

**기존 이벤트 수정:**
- `on_reach`: 분대원 위치 도착 시 → 분대 동기화 체크 (E3 gate 동기화)
- `on_meet`: NPC 만남 시 → 모집 가능 여부 props 업데이트
- `check_npc_combat_join`: 파티 상태 체크 추가 (G1)

#### G6. think() 루프 변경

**현재 (fsm.py 호출부, think/__init__.py L746-750):**
```python
# 단일 top 호출
top = self._fsm_stack[-1]
if top.update(self):
    return  # 처리 완료
# top이 False → pop 됨 → 아래 phase
```

**변경 (pass-through 스택 순회):**
```python
# 스택 상위→하위 순회
for state in reversed(self._fsm_stack):
    if state.update(self):
        return  # 이 state가 처리 완료
    # False → 아래 state로 위임 (pop 아님, 스택 유지)

# 모든 state가 False → 5-tier 생활 로직
self._life_logic()
```

**주의:**
- 기존 `False = pop` 동작을 사용하는 코드 전부 수정 필요
- CombatState, FleeState 등 기존 FSM state의 `return False` 의미 변경
- 마이그레이션: 기존 state에서 `return False`하던 곳 → 명시적 `_fsm_pop()` + `return False`

**마이그레이션 대상:**
```
CombatState.update():
  기존: return False (= pop + 위임)
  변경: self._fsm_pop(); return False

FleeState.update():
  기존: return False
  변경: self._fsm_pop(); return False

ResignationState.update():
  기존: return False
  변경: self._fsm_pop(); return False

DesperateState.update():
  기존: return False
  변경: self._fsm_pop(); return False

GateTransitState.update():
  기존: return False
  변경: self._fsm_pop(); return False

LifeState.update():
  기존: return False (= 5-tier 로직으로)
  변경: return False (동일 — 최하위이므로 pop 의미 없음)
```

#### G7. 시나리오03 호환성 체크리스트

| 항목 | 호환 방법 |
|------|----------|
| party.py | 순수 Python, C# 변경 없음 |
| party_config.py | `_COMMAND_DISPOSITION.get(uid, (0,0))` → 미등록 NPC도 동작 |
| StandbyPhase | 분대 미소속 → `return False` → 무영향 |
| CommandPhase | order 없으면 생성 안 됨 → 무영향 |
| 모집 조건 | `_RECRUIT_OVERRIDE` 미등록 → 기본 조건 사용 |
| 불복 판정 | 관계 prop 없으면 반발=0, 복종=0 → 거부 없음 |
| BATTLE_BEHAVIOR | 파티 미소속 → 기존 로직 그대로 |
| 챕터 전환 | `party.reset()` → 빈 dict clear → 무영향 |
| 스케줄 스택 | push/pop 구조 동일 → 호환 |
| FSM pass-through | 기존 state에 `_fsm_pop()` 추가 → 동작 동일 |

---

### 8.8 구현 순서 제안

```
Phase 1 — 골격 (FSM 변경 + 데이터) ✅ 완료
  1. ✅ fsm.py pass-through 변환 + LV_STANDBY/LV_COMMAND 추가
  2. ✅ party.py 모듈 (Squad/Order + 레지스트리 + B1-B5 API)
  3. ✅ party_config.py (disposition + 모집조건 + 불복 + 리더특성)
  4. ✅ chapters/__init__.py reset 등록
  5. ✅ think() 루프 pass-through 변환 + _fsm_pop_by_type 추가
  6. ✅ StandbyPhase/CommandPhase 골격 (fsm.py)
  7. ✅ test_party.py (53개 테스트, 785/785 전체 회귀 통과)

Phase 2 — FSM Phase 실동작
  8. order_handlers.py (follow/수색/경계/수집/이동/대기 핸들러)
  9. think() 루프에 phase 실 연동
  10. 테스트: 분대 생성 → 지시 → 동작 확인

Phase 3 — 이동/동기화
  10. follow 메커니즘 (E1)
  11. gate 동기화 (E3)
  12. order 전환 (E2)
  13. 귀환 (E4)
  14. 테스트: 이동/gate/귀환 흐름

Phase 4 — 플레이어 UI
  15. can: props 추가 (C2)
  16. 분대 선택 UI (C3)
  17. 모집/지시 액션 (C4 + F5)
  18. 테스트: 전체 UI 흐름

Phase 5 — 연동/마무리
  19. 전투 합류 연동 (G1)
  20. 데이트 상호 배제 (G2)
  21. 불복 판정 (F2)
  22. 통합 테스트
```
