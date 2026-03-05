# 파티 시스템 구현 명세 (v1 — 대체됨)

> **상태: 대체됨 — 아래 문서를 참고하세요.**
>
> 이 문서는 초기 설계 명세(v1)입니다. 이후 설계 논의를 거쳐 아래 문서로 대체되었습니다:
>
> - **[party-design-notes.md](party-design-notes.md) Section 8** — 최신 구현 명세 (v2)
>   - FSM pass-through 스택, 분대(Squad) 시스템, Disposition 2D, 개별 Gate transit 등
>
> 이 문서의 내용 중 일부(date.py follow 패턴, C# follow 동작 등)는 여전히 참고 가치가 있습니다.

---

> ~~이 문서만으로 구현이 가능한 수준의 상세 명세서입니다.~~
> combat-implementation.md Section 26의 Phase 2 파티 시스템을 독립 설계합니다.
> 기존 date.py의 follow 패턴을 확장하여 다인 파티를 구현합니다.

---

## 목차

- **Part A: 기반** — 1. 기존 시스템 연동 / 2. party.py 코어 (2.7 헬퍼) / 3. Props
- **Part B: 플레이어 리더** — 4. 파티 생성 / 5. 명령 체계 (5.5 비전투 명령, 5.6 지시 무시) / 6. 해산 (6.2 귀환)
- **Part C: NPC 리더** — 7. NPC 주도 파티 (7.2 분대 명령, 7.3 리더 성향 오버라이드) / 8. NPC 리더 AI / 9. 플레이어 참여
- **Part D: 이동** — 10. follow 통합 / 11. 대기/집결 / 12. Gate 이동
- **Part E: 전투** — 13. 전투 합류 / 14. 전투 정책 / 15. 전투 중 역할
- **Part F: think 통합** — 16. Tier 삽입 / 17. 파티 핸들러 / 18. 인터럽트 공존
- **Part G: UI/UX** — 19. 파티 UI (19.1 3레이어 묘사 통합) / 20. 대사/리액션
- **Part H: 통합** — 21. 파일 목록 / 22. 구현 순서 / 23. 테스트 계획

---

# Part A: 기반

## 1. 기존 시스템 연동

### 1.1 date.py 패턴 (재사용)

date.py에 이미 구현된 1인 follow 패턴을 파티 시스템의 기반으로 사용:

```python
# date.py:26-28 — follow 스케줄 (검증 완료)
FOLLOW_SCHEDULE = [
    {"name": "따라가기", "action": "follow", "start": 0, "end": MILLIS_PER_DAY, "activity": "데이트"}
]
```

**핵심 패턴 3단계:**
1. `push_schedule(FOLLOW_SCHEDULE)` → NPC 스케줄 오버라이드
2. `morld.set_npc_job(partner_id, "follow", duration, target_id)` → C# follow 실행
3. `pop_schedule()` → 원래 스케줄 복원

이 패턴을 그대로 확장하되, activity를 `"파티"`, name을 `"파티 이동"`으로 변경.

### 1.2 C# follow 동작 (기존)

```
job_behavior_system.cs:137-147
- action == "follow" → target의 Location + X 좌표로 이동
- TargetId 미지정 시 → 플레이어 자동 대상
- ProcessMoveAction2D()로 이동 처리 (속도, 혼잡도 반영)
```

**제약:**
- follow는 대상의 **현재 위치**로 이동 (예측 없음)
- 대상이 Location 이동하면 follower도 곧 따라감 (같은 Gate 경유)
- 대상보다 느릴 경우 점점 벌어질 수 있음

### 1.3 데이트와 파티의 관계

| 항목 | 데이트 | 파티 |
|------|--------|------|
| 인원 | 1:1 | 최대 4인 (리더 포함) |
| 리더 | 항상 플레이어 | 플레이어 또는 NPC |
| 종료 조건 | 플레이어 선택 | 해산/탈퇴/사망 |
| 스케줄 | push_schedule | push_schedule (동일) |
| 전투 | 없음 (비전투) | 전투 정책 연동 |

**호환 규칙:** 데이트 중에는 파티 생성 불가. 파티 중에는 데이트 불가.

### 1.4 combat.py 연동

combat-implementation.md에서 정의한 전투 시스템과의 연동점:

| combat.py 항목 | 파티 연동 |
|---------------|----------|
| `check_npc_combat_join()` | 파티 멤버 우선 합류 (호감도 체크 생략) |
| `BATTLE_BEHAVIOR.join_combat` | 파티 내에서는 항상 True |
| `combat.start_combat()` | 파티 멤버에게 전투 시작 알림 |
| `combat.end_combat()` | 파티 멤버 follow 복원 |
| NPC 아군 공격 반응 | `leaves_party: True` → 파티 탈퇴 |

---

## 2. party.py 코어

### 2.1 모듈 구조

```python
# party.py - 파티 시스템 모듈
"""
파티 시스템 — 다인 그룹 이동/전투

핵심 기능:
- 최대 4인 파티 (리더 포함)
- 플레이어 리더: 모집/명령/해산
- NPC 리더: 이벤트/퀘스트 기반 그룹 행동
- 전투 정책 연동
"""

import morld
import think

# ============================================
# 상수
# ============================================

MAX_PARTY_SIZE = 4
MILLIS_PER_DAY = 86_400_000

# 파티원 모집 최소 호감도 / 복종도
RECRUIT_MIN_AFFECTION = 40
RECRUIT_MIN_SUBMISSION = 50   # 복종 경로: 호감 부족해도 가입 가능

# 전투 정책
POLICY_AGGRESSIVE = "aggressive"   # 적 발견 시 자동 공격
POLICY_DEFENSIVE = "defensive"     # 피격 시에만 반격
POLICY_PACIFIST = "pacifist"       # 전투 회피, 도주 우선

# 파티 follow 스케줄
PARTY_FOLLOW_SCHEDULE = [
    {
        "name": "파티 이동",
        "action": "follow",
        "start": 0,
        "end": MILLIS_PER_DAY,
        "activity": "파티",
    }
]
```

### 2.2 파티 상태 (싱글톤)

```python
# ============================================
# 파티 상태 관리
# ============================================

# 현재 활성 파티 (단일 파티만 허용)
_party = None  # None이면 파티 없음

class Party:
    """파티 인스턴스"""

    def __init__(self, leader_id, leader_type="player"):
        self.leader_id = leader_id          # 리더 unit_id
        self.leader_type = leader_type      # "player" | "npc"
        self.members = []                   # 멤버 unit_id 리스트 (리더 제외)
        self.policy = POLICY_DEFENSIVE      # 기본 전투 정책
        self.waiting = {}                   # {unit_id: location_dict} 대기 중인 멤버

    @property
    def size(self):
        return 1 + len(self.members)  # 리더 포함

    @property
    def all_unit_ids(self):
        """리더 + 멤버 전체"""
        return [self.leader_id] + list(self.members)

    def is_member(self, unit_id):
        return unit_id == self.leader_id or unit_id in self.members
```

### 2.3 공개 API

```python
# ============================================
# 공개 API
# ============================================

def get_party():
    """현재 파티 반환 (없으면 None)"""
    return _party

def is_in_party(unit_id):
    """unit_id가 파티에 소속되어 있는지"""
    return _party is not None and _party.is_member(unit_id)

def is_party_leader(unit_id):
    """unit_id가 현재 파티 리더인지"""
    return _party is not None and _party.leader_id == unit_id

def get_party_leader_id():
    """파티 리더 unit_id (없으면 None)"""
    return _party.leader_id if _party else None

def get_party_members():
    """리더 제외 멤버 리스트 (없으면 [])"""
    return list(_party.members) if _party else []

def get_party_policy():
    """현재 전투 정책"""
    return _party.policy if _party else None

def is_waiting(unit_id):
    """해당 멤버가 대기 상태인지"""
    return _party is not None and unit_id in _party.waiting
```

### 2.4 파티 생성/해산 (내부)

```python
def _create_party(leader_id, leader_type="player"):
    """파티 생성 (내부용)"""
    global _party

    # 데이트 중이면 생성 불가
    import date
    if date.is_on_date(leader_id):
        return None

    if _party is not None:
        return None  # 이미 파티 존재

    _party = Party(leader_id, leader_type)

    # 리더 prop 설정
    morld.set_unit_prop(leader_id, "파티:역할", "리더")
    morld.set_unit_prop(leader_id, "파티:정책", POLICY_DEFENSIVE)

    print(f"[party] Created: leader={leader_id}, type={leader_type}")
    return _party


def _disband_party():
    """파티 해산 (내부용)"""
    global _party
    if _party is None:
        return

    # 모든 멤버 복원
    for member_id in list(_party.members):
        _remove_member(member_id, reason="disband")

    # 리더 prop 정리
    morld.clear_prop(_party.leader_id, "파티:역할")
    morld.clear_prop(_party.leader_id, "파티:정책")

    print(f"[party] Disbanded: leader={_party.leader_id}")
    _party = None
```

### 2.5 멤버 추가/제거 (내부)

```python
def _add_member(unit_id):
    """멤버 추가 (내부용)"""
    if _party is None:
        return False
    if _party.size >= MAX_PARTY_SIZE:
        return False
    if _party.is_member(unit_id):
        return False

    _party.members.append(unit_id)

    # NPC 스케줄 오버라이드 (follow)
    agent = think.get_agent(unit_id)
    if agent:
        agent.push_schedule(PARTY_FOLLOW_SCHEDULE)

    # follow job 설정
    morld.set_npc_job(unit_id, "follow", MILLIS_PER_DAY, _party.leader_id)

    # prop 설정
    morld.set_unit_prop(unit_id, "파티:역할", "멤버")
    morld.set_unit_prop(unit_id, "파티:리더", _party.leader_id)

    print(f"[party] Added member: {unit_id}")
    return True


def _remove_member(unit_id, reason="dismiss"):
    """멤버 제거 (내부용)

    Args:
        unit_id: 제거할 멤버
        reason: "dismiss" (해제) / "leave" (자발적 탈퇴) / "disband" (해산)
                / "faint" (기절) / "death" (사망) / "hostile" (적대화)
    """
    if _party is None or unit_id not in _party.members:
        return

    _party.members.remove(unit_id)
    _party.waiting.pop(unit_id, None)

    # NPC 스케줄 복원
    agent = think.get_agent(unit_id)
    if agent:
        agent.pop_schedule()

    # prop 정리
    morld.clear_prop(unit_id, "파티:역할")
    morld.clear_prop(unit_id, "파티:리더")

    print(f"[party] Removed member: {unit_id}, reason={reason}")
```

### 2.6 리셋

```python
def reset():
    """챕터 전환 시 초기화"""
    global _party
    if _party:
        _disband_party()
    _party = None
```

`chapters/__init__.py`의 `load_chapter()`에서 `party.reset()` 호출 추가.

### 2.7 내부 헬퍼

```python
def _get_name(unit_id):
    """유닛 이름 조회"""
    info = morld.get_unit_info(unit_id)
    return info.get("name", "?") if info else "?"


def _get_player_name():
    return _get_name(morld.get_player_id())


def _get_battle_behavior(unit_id):
    """BATTLE_BEHAVIOR dict 조회 (think agent 경유)"""
    agent = think.get_agent(unit_id)
    return getattr(agent, 'BATTLE_BEHAVIOR', {}) if agent else {}


def _get_party_behavior(unit_id):
    """PARTY_BEHAVIOR dict 조회 (think agent 경유)"""
    agent = think.get_agent(unit_id)
    return getattr(agent, 'PARTY_BEHAVIOR', {}) if agent else {}


def _get_party_leader_behavior(leader_id):
    """PARTY_LEADER_BEHAVIOR dict 조회"""
    agent = think.get_agent(leader_id)
    return getattr(agent, 'PARTY_LEADER_BEHAVIOR', {}) if agent else {}


def _get_affection_to_leader(unit_id):
    """멤버 → 리더 호감도"""
    if not _party:
        return 0
    leader_name = _get_name(_party.leader_id)
    return morld.get_unit_prop(unit_id, f"관계:{leader_name}:호감") or 0


def _get_submission_to_leader(unit_id):
    """멤버 → 리더 복종도"""
    if not _party:
        return 0
    leader_name = _get_name(_party.leader_id)
    return morld.get_unit_prop(unit_id, f"관계:{leader_name}:복종") or 0
```

---

## 3. Props

### 3.1 유닛 Props

| prop | 값 | 대상 | 설명 |
|------|-----|------|------|
| `파티:역할` | `"리더"` / `"멤버"` | 리더/멤버 | 파티 내 역할 |
| `파티:리더` | unit_id (int) | 멤버만 | 따라가는 대상 |
| `파티:정책` | `"aggressive"` / `"defensive"` / `"pacifist"` | 리더 | 전투 정책 |
| `파티:대기` | 1 | 멤버 | 대기 명령 받은 멤버 |

### 3.2 NPC 클래스 속성

```python
class Character(Object):
    # 기존
    BATTLE_BEHAVIOR = { ... }

    # 파티 추가
    PARTY_BEHAVIOR = {
        "recruitable": True,            # 파티 모집 가능 여부
        "recruit_affection": 40,        # 모집 최소 호감도 (캐릭터별 오버라이드)
        "recruit_submission": 50,       # 모집 최소 복종도 (호감 OR 복종)
        "follow_distance": 30,          # 따라가기 시 선호 거리 (x 좌표 오프셋)
        "auto_heal": False,             # 자동 치유 (미래 확장)
        "combat_join_in_party": True,   # 파티 상태에서 전투 자동 합류
        "leaves_if_hostile": True,      # 적대 시 자동 탈퇴
    }
```

### 3.3 캐릭터별 PARTY_BEHAVIOR

```python
# 세라 — 적극적 전투 파트너
class Sera(Character):
    PARTY_BEHAVIOR = {
        "recruitable": True,
        "recruit_affection": 30,        # 무뚝뚝하지만 일찍 동행
        "recruit_submission": 40,       # 복종 경로도 비교적 쉬움
        "follow_distance": 20,          # 가까이 따라감
        "combat_join_in_party": True,
        "leaves_if_hostile": True,
    }

# 밀라 — 신중한 지원
class Mila(Character):
    PARTY_BEHAVIOR = {
        "recruitable": True,
        "recruit_affection": 50,        # 신뢰가 쌓여야
        "recruit_submission": 60,       # 복종 경로는 더 높은 복종 필요
        "follow_distance": 40,          # 약간 거리 유지
        "combat_join_in_party": True,
        "leaves_if_hostile": True,
    }

# 리나 — 비전투 동행
class Lina(Character):
    PARTY_BEHAVIOR = {
        "recruitable": True,
        "recruit_affection": 35,
        "recruit_submission": 45,
        "follow_distance": 25,
        "combat_join_in_party": False,   # 전투 합류 안함 (evasive)
        "leaves_if_hostile": True,
    }

# 유키 — 조건부 동행
class Yuki(Character):
    PARTY_BEHAVIOR = {
        "recruitable": True,
        "recruit_affection": 60,        # 높은 호감 필요
        "recruit_submission": 70,       # 복종 경로도 높음
        "follow_distance": 35,
        "combat_join_in_party": True,
        "leaves_if_hostile": True,
    }

# 엘라 — 독립적, 잘 안 따라감
class Ella(Character):
    PARTY_BEHAVIOR = {
        "recruitable": True,
        "recruit_affection": 70,        # 매우 높은 호감 필요
        "recruit_submission": 80,       # 복종 경로도 매우 높음
        "follow_distance": 50,          # 느슨하게 따라감
        "combat_join_in_party": True,
        "leaves_if_hostile": True,
    }
```

---

# Part B: 플레이어 리더

## 4. 파티 생성 (플레이어 리더)

### 4.1 동행 요청 액션

NPC focus 메뉴에서 "동행 요청" / "동행 해제" 액션을 표시:

```python
# assets/base.py — Character 클래스 수정
# build_focus_actions() 또는 actions 리스트에 추가

# 플레이어 can: prop
"can:recruit_party": 1,    # 동행 요청 가능 (기본 ON)

# NPC 액션 (focus 메뉴)
"call:recruit_party:동행 요청"      # 파티 미소속 NPC에게
"call:dismiss_party:동행 해제"      # 파티 멤버에게
```

**표시 조건 (액션 필터링):**

```python
# 동행 요청 표시 조건:
#   1. can:recruit_party == 1
#   2. 대상 NPC가 파티 미소속
#   3. NPC.PARTY_BEHAVIOR["recruitable"] == True
#   4. 현재 파티 인원 < MAX_PARTY_SIZE (또는 파티 없음)
#   5. 데이트 중이 아님

# 동행 해제 표시 조건:
#   1. 대상 NPC가 현재 파티 멤버
```

### 4.2 동행 요청 처리

```python
# assets/base.py — Character 인스턴스 메서드
def recruit_party(self):
    """플레이어가 NPC에게 동행 요청"""
    import morld
    import party

    player_id = morld.get_player_id()
    npc_id = self.instance_id

    # 1. 유효성 검증
    behavior = getattr(self, 'PARTY_BEHAVIOR', None)
    if not behavior or not behavior.get("recruitable", False):
        morld.add_action_log(f"{self.name}은(는) 동행할 수 없다.")
        return

    # 2. 호감도 OR 복종도 체크 (이중 경로)
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "주인공") if player_info else "주인공"
    affection = morld.get_unit_prop(npc_id, f"관계:{player_name}:호감") or 0
    submission = morld.get_unit_prop(npc_id, f"관계:{player_name}:복종") or 0
    min_affection = behavior.get("recruit_affection", RECRUIT_MIN_AFFECTION)
    min_submission = behavior.get("recruit_submission", RECRUIT_MIN_SUBMISSION)

    # 호감 경로 OR 복종 경로 — 하나라도 충족하면 수락
    if affection < min_affection and submission < min_submission:
        morld.add_action_log(f"{self.name}이(가) 고개를 저었다.")
        # NPC 리액션 (거절)
        return

    # 3. 상태 체크 — 기절/수면/결박/전투 중이면 불가
    import survival
    if survival.is_npc_fainted(npc_id):
        morld.add_action_log(f"{self.name}은(는) 의식이 없다.")
        return

    # 4. 파티 생성 (없으면) + 멤버 추가
    if not party.get_party():
        party._create_party(player_id, "player")

    if party._add_member(npc_id):
        morld.add_action_log(f"{self.name}이(가) 동행에 합류했다.")
        # NPC 리액션 (수락)
    else:
        morld.add_action_log("더 이상 동행할 수 없다.")  # 인원 초과
```

### 4.3 가입 조건 (호감 OR 복종)

| NPC | recruit_affection | recruit_submission | 비고 |
|-----|-------------------|-------------------|------|
| 세라 | 30 | 40 | 전사 기질, 일찍 동행 |
| 리나 | 35 | 45 | 호기심이 많아 비교적 쉽게 |
| 밀라 | 50 | 60 | 신중, 신뢰 필요 |
| 유키 | 60 | 70 | 경계심, 높은 신뢰 필요 |
| 엘라 | 70 | 80 | 독립적, 매우 높은 신뢰 |

**이중 경로 설계 의도:**
- **호감 경로**: 신뢰/우정 → 자발적 동행 (거절 시 반발 없음)
- **복종 경로**: 강제/복종 → 마지못한 동행 (내심 불만, 지시 무시 확률 상승)
- 복종 경로로 가입한 NPC는 반발이 높아 명령 거부 확률이 높음 (Section 5.6 참조)

---

## 5. 명령 체계 (플레이어 리더)

### 5.1 파티 명령 개요

파티 리더(플레이어)가 멤버에게 내릴 수 있는 명령:

| 명령 | 대상 | 효과 | 구현 |
|------|------|------|------|
| **따라와** | 개별/전체 | 리더 follow (기본) | `set_npc_job("follow")` |
| **대기** | 개별/전체 | 현재 위치 유지 | `set_npc_job("stay")` + `파티:대기` prop |
| **집결** | 전체 | 대기 멤버 전원 follow 복귀 | 대기 해제 + follow 재설정 |
| **공격해** | 개별 | 지정 대상 공격 | combat 연동 (전투 중) |
| **물러나** | 개별/전체 | 전투 이탈 + 후방 | combat 연동 (전투 중) |

### 5.2 명령 UI

파티 상태일 때 플레이어에게 추가되는 액션:

```python
# player.py — 파티 관련 액션
"call:party_follow_all:전원 따라와"
"call:party_wait_all:전원 대기"
"call:party_gather:전원 집결"
"call:party_disband:파티 해산"

# NPC focus 시 (파티 멤버에게)
"call:party_follow:{name} 따라와"
"call:party_wait:{name} 대기"
"call:party_attack:{name} 공격해"      # 전투 중에만
"call:party_retreat:{name} 물러나"     # 전투 중에만
```

### 5.3 전투 정책 변경

전투 정책은 settings.py 토글 또는 파티 메뉴에서 변경:

```python
# settings.py에 추가 (토글 패턴)
# 또는 별도 party_menu에서

def set_party_policy(policy):
    """전투 정책 변경"""
    if _party is None:
        return
    _party.policy = policy
    morld.set_unit_prop(_party.leader_id, "파티:정책", policy)
    morld.add_action_log(f"전투 정책: {_POLICY_LABELS[policy]}")

_POLICY_LABELS = {
    "aggressive": "공격적 — 적 발견 시 자동 공격",
    "defensive": "방어적 — 피격 시에만 반격",
    "pacifist": "비전투 — 전투 회피, 도주 우선",
}
```

### 5.4 개별 멤버 명령 구현

```python
def command_follow(unit_id):
    """멤버에게 따라오기 명령"""
    if _party is None or unit_id not in _party.members:
        return

    # 대기 해제
    _party.waiting.pop(unit_id, None)
    morld.clear_prop(unit_id, "파티:대기")

    # follow job 재설정
    morld.set_npc_job(unit_id, "follow", MILLIS_PER_DAY, _party.leader_id)


def command_wait(unit_id):
    """멤버에게 대기 명령"""
    if _party is None or unit_id not in _party.members:
        return

    # 현재 위치 저장
    loc = morld.get_unit_location(unit_id)
    if loc:
        _party.waiting[unit_id] = {"region_id": loc[0], "location_id": loc[1]}

    # stay job으로 전환
    morld.set_unit_prop(unit_id, "파티:대기", 1)
    morld.set_npc_job(unit_id, "stay", MILLIS_PER_DAY, None)


def command_gather():
    """전원 집결 — 대기 중인 멤버 전원 follow 복귀"""
    if _party is None:
        return

    for member_id in list(_party.waiting.keys()):
        command_follow(member_id)

    morld.add_action_log("전원에게 집결 명령을 내렸다.")
```

### 5.5 비전투 명령

파티 멤버에게 전투 외의 작업을 지시할 수 있다.
기존 activity handler(`think/activities/`)와 매핑:

| 명령 | activity 매핑 | 기존 핸들러 | 비고 |
|------|-------------|-----------|------|
| "자원 수집해" | 벌목/채집/낚시 디스패치 | `chop.py`, `gather.py`, `fish.py` | NPC 스킬에 따라 자동 선택 |
| "청소해" | 청소 | `clean.py` | 현재 Location 대상 |
| "제작해" | 제작 | `craft.py` | CraftingTable 필요 |
| "건축해" | 건축 | (build 시스템 연동) | 건축 가능 NPC만 |
| "요리해" | 요리 | `cook.py` | Stove 연료 필요 |
| "대기" | idle | `_insert_idle_job()` | 현위치 정지 |

```python
# party.py — 비전투 명령

TASK_COMMANDS = {
    "자원 수집해": ["벌목", "채집", "낚시"],   # 후보 activity 리스트
    "청소해": ["청소"],
    "제작해": ["제작"],
    "건축해": ["건축"],
    "요리해": ["요리"],
}

def command_task(unit_id, task_name):
    """멤버에게 비전투 작업 지시

    Args:
        unit_id: 대상 멤버
        task_name: TASK_COMMANDS 키

    NPC가 해당 능력이 없으면 거부 리액션.
    """
    if _party is None or unit_id not in _party.members:
        return False

    candidates = TASK_COMMANDS.get(task_name)
    if not candidates:
        return False

    agent = think.get_agent(unit_id)
    if not agent:
        return False

    # NPC가 수행 가능한 activity 확인
    from think.activities import ACTIVITY_HANDLERS
    for activity in candidates:
        if activity in ACTIVITY_HANDLERS:
            # 대기 상태로 전환 + 작업 스케줄 삽입
            task_schedule = [
                {
                    "name": f"파티 작업: {task_name}",
                    "action": "stay",
                    "start": 0,
                    "end": MILLIS_PER_DAY,
                    "activity": activity,
                }
            ]
            # 기존 파티 follow 스케줄을 task 스케줄로 교체
            agent.pop_schedule()
            agent.push_schedule(task_schedule)
            _party.waiting[unit_id] = {"task": task_name}
            morld.set_unit_prop(unit_id, "파티:대기", 1)
            morld.add_action_log(f"{_get_name(unit_id)}이(가) {task_name} 작업을 시작했다.")
            return True

    # 수행 불가
    morld.add_action_log(f"{_get_name(unit_id)}: 그건 못 해.")
    return False
```

**작업 복귀:**
- 작업 완료 후 또는 "따라와" 명령 시 → pop_schedule + push(PARTY_FOLLOW_SCHEDULE)
- `command_follow()` 수정: waiting에 "task"가 있으면 스케줄 교체 처리

```python
# player.py — 비전투 명령 액션 (NPC focus 시)
"call:party_task_gather:{name} 자원 수집해"
"call:party_task_clean:{name} 청소해"
"call:party_task_craft:{name} 제작해"
"call:party_task_build:{name} 건축해"
"call:party_task_cook:{name} 요리해"
```

### 5.6 지시 무시 (명령 거부)

NPC의 상태나 성향에 따라 플레이어의 명령을 무시하거나 변환할 수 있다.

**거부 판정 수식:**

```python
def _check_command_refusal(unit_id, command):
    """명령 거부 판정

    Returns:
        None: 명령 수행
        str: 거부 사유 (UI 메시지용)
    """
    # 1. 절대 거부 조건 (상태 기반)
    import survival
    if survival.is_npc_fainted(unit_id):
        return "의식이 없다"
    if survival.get_health_percent(unit_id) < 20:
        return "체력이 너무 낮다"  # HP < 20% → 후퇴 자동 전환

    # 2. 성향 거부 (BATTLE_BEHAVIOR 기반)
    behavior = _get_battle_behavior(unit_id)
    if command == "공격해" and behavior.get("style") == "pacifist":
        return "전투를 거부했다"

    # 3. 반발 거부 (관계 기반)
    player_name = _get_player_name()
    rebellion = morld.get_unit_prop(unit_id, f"관계:{player_name}:반발") or 0
    submission = morld.get_unit_prop(unit_id, f"관계:{player_name}:복종") or 0

    # 거부 확률 = 반발 × 0.008 - 복종 × 0.005 (0~1 클램프)
    refusal_chance = max(0.0, min(1.0, rebellion * 0.008 - submission * 0.005))

    import random
    if random.random() < refusal_chance:
        return "지시를 무시했다"

    return None  # 수행
```

**거부 조건 요약:**

| 조건 | 거부 | 비고 |
|------|------|------|
| 기절/수면 (Tier 1) | 모든 명령 | think 5-tier가 자동 처리 |
| HP < 20% | 공격 계열 → 후퇴 전환 | 생존 우선 |
| 성향 = pacifist | "공격해" 거부 | BATTLE_BEHAVIOR 참조 |
| 반발 ≥ 50 | 확률적 거부 (40%~) | 복종이 높으면 상쇄 |
| 반발 ≥ 80 | 높은 거부 (64%~) | 적대화 임계 근접 |
| 복종 ≥ 60 | 거부 확률 감소 (-30%) | 복종이 반발을 억제 |
| 배고픔/추위 임계 | Tier 3 인터럽트 | 도착 후 자동 해결 |

**거부 시 UI 표시:**

```python
# command 실행 전 체크
reason = _check_command_refusal(unit_id, command)
if reason:
    name = _get_name(unit_id)
    morld.add_action_log(f"{name}이(가) {reason}.")
    # 복종 경로 가입 NPC: 반발 +1 (불만 누적)
    return False
```

**복종 경로 가입 NPC의 특성:**
- 호감 < recruit_affection이지만 복종 ≥ recruit_submission로 가입한 NPC는
  반발이 높을 확률이 높으므로 명령 거부율이 자연스럽게 상승
- 장기적으로 반발 basin(0/35/75)에 수렴하며, 반발 75 basin에 갇힌 NPC는
  거부율 ≈ 60%로 사실상 비협조적

---

## 6. 해산

### 6.1 해산 조건

| 조건 | 동작 |
|------|------|
| 플레이어가 "파티 해산" 선택 | `_disband_party()` |
| 마지막 멤버 탈퇴 | 자동 해산 |
| 리더 기절 | 전원 자유행동 (파티 유지, 기절 해제 시 복원) |
| 리더 사망 | 자동 해산 |
| 챕터 전환 | `party.reset()` |

### 6.2 해산 후 귀환 (cross-region)

파티 해산 후 NPC가 home_region이 아닌 곳에 있을 때의 귀환 처리.

**문제:** `pop_schedule()` → 기본 스케줄 복원 → 현위치에서 일상 재개.
NPC가 home_region 밖에 버려질 수 있음.

**해결: think() Tier 5에서 귀환 체크**

```python
# think/__init__.py — BaseAgent 메서드

def _check_return_home(self):
    """Tier 5 초반: 현재 region ≠ home_region이면 귀환 이동

    파티/데이트 해체 후 타 region에 남겨진 경우 자동 귀환.
    Returns:
        True: 귀환 이동 삽입됨 (action_taken)
        False: 이미 home_region에 있음
    """
    import party
    # 파티 소속이면 귀환 불필요
    if party.is_in_party(self.unit_id):
        return False

    my_loc = self.get_location()
    if not my_loc:
        return False

    home_region = self._get_home_region()
    if my_loc[0] == home_region:
        return False  # 이미 집

    # home_region 입구로 이동
    self._move_to({"region_id": home_region, "location_id": 0}, "귀환")
    return True
```

**적용 위치 (think 본체):**

```python
# Tier 5 시작 전에 귀환 체크 삽입
# elif 체인 내에서:

    # Tier 5: 일과
    _tier_reached = 5
    if self._check_return_home():
        pass  # 귀환 이동 삽입됨
    else:
        self._check_tier5_routine()
```

**장점:**
- date 해체에도 동일하게 적용 (date 전용 코드 불필요)
- 기존 시스템 수정 최소화 (think Tier 5에 한 줄 삽입)
- NPC가 자연스럽게 걸어서 귀환 (텔레포트 아님)
- 파티 소속이면 건너뜀 (충돌 없음)

### 6.3 멤버 자발적 탈퇴

NPC가 자발적으로 파티를 탈퇴하는 조건:

```python
def _check_member_leave(unit_id):
    """멤버 자발적 탈퇴 체크 — think()에서 호출"""

    # 1. 호감도/복종도 하락 → 탈퇴 (가입 시 이중 경로에 대응)
    behavior = _get_party_behavior(unit_id)
    if not behavior:
        return True  # PARTY_BEHAVIOR 없으면 탈퇴

    min_affection = behavior.get("recruit_affection", RECRUIT_MIN_AFFECTION)
    min_submission = behavior.get("recruit_submission", RECRUIT_MIN_SUBMISSION)
    affection = _get_affection_to_leader(unit_id)
    submission = _get_submission_to_leader(unit_id)

    # 호감 경로 OR 복종 경로 — 둘 다 탈퇴 임계 이하면 탈퇴
    affection_leave = affection < min_affection * 0.5   # 모집 조건의 50% 이하
    submission_leave = submission < min_submission * 0.5
    if affection_leave and submission_leave:
        return True

    # 2. 적대 상태 (combat.py의 관계:{name}:적대 prop 사용)
    if behavior.get("leaves_if_hostile", True):
        import combat
        leader_name = _get_name(_party.leader_id) if _party else ""
        hostility = combat.get_hostility(unit_id, leader_name)
        if hostility >= combat.HOSTILITY_ATTACK_ON_SIGHT:  # 80
            return True

    return False
```

### 6.4 리더 기절 시 처리

```python
def on_leader_faint():
    """리더 기절 시 — 파티 유지, 멤버 자유행동"""
    if _party is None:
        return

    for member_id in _party.members:
        if member_id not in _party.waiting:
            # follow 중단, 자유행동 (스케줄은 push된 상태 유지)
            # think에서 파티 follow 대신 일반 스케줄 실행
            morld.set_unit_prop(member_id, "파티:대기", 1)

    # 리더 기절 해제 시 on_leader_recover()에서 follow 재설정
```

---

# Part C: NPC 리더

## 7. NPC 주도 파티

### 7.1 개요

NPC가 리더인 파티는 **이벤트/퀘스트에 의해 생성**됩니다.
플레이어가 아닌 NPC가 경로를 결정하고, 다른 멤버(플레이어 포함)가 따라갑니다.

**사용 사례:**
- NPC가 위험 지역을 안내 (숲 가이드)
- NPC 호위 퀘스트 (경비대 순찰)
- NPC 그룹 이동 (피난, 이주)

### 7.2 NPC 분대 명령 체계

NPC 리더 파티(분대)의 명령은 **플레이어 리더 파티보다 제한적**이다.
플레이어는 분대에 **방침**만 설정하고, 세부 판단은 NPC 리더가 수행한다.

**분대 방침 (5+1):**

| 방침 | 키 | 설명 | 플레이어 설정 | NPC 리더 해석 |
|------|-----|------|-------------|-------------|
| **자율** (기본) | `auto` | NPC 리더 판단에 위임 | O | 리더 성향대로 행동 |
| **수색** | `search` | 주변 탐색/정찰 | O | 리더가 탐색 범위 결정 |
| **전투(은밀)** | `combat_stealth` | 기습만, 선제공격 회피 | O | aggressive 리더: 무시 가능 |
| **전투(통상)** | `combat_normal` | 일반 교전 | O | — |
| **전투(적극)** | `combat_aggressive` | 선제 공격 포함 | O | pacifist 리더: 거부 가능 |
| **후퇴** | `retreat` | 전투 이탈 | O | — |
| **대기** | `wait` | 현위치 정지 | O | — |

```python
# party.py — NPC 분대 방침

SQUAD_DIRECTIVES = {
    "auto": "자율 — NPC 리더 판단에 위임",
    "search": "수색 — 주변 탐색/정찰",
    "combat_stealth": "전투(은밀) — 기습만, 선제공격 회피",
    "combat_normal": "전투(통상) — 일반 교전",
    "combat_aggressive": "전투(적극) — 선제 공격 포함",
    "retreat": "후퇴 — 전투 이탈",
    "wait": "대기 — 현위치 정지",
}

def set_squad_directive(directive):
    """NPC 분대에 방침 설정 (플레이어 액션)"""
    if _party is None or _party.leader_type != "npc":
        return
    if directive not in SQUAD_DIRECTIVES:
        return

    # 방침을 리더에게 전달 (리더 AI가 해석)
    morld.set_unit_prop(_party.leader_id, "파티:방침", directive)
    morld.add_action_log(f"방침: {SQUAD_DIRECTIVES[directive]}")
```

**플레이어 액션 (NPC 리더 파티 소속 시):**

```python
# player.py — NPC 분대 방침 설정 액션
"call:squad_auto:자율"
"call:squad_search:수색"
"call:squad_combat_stealth:전투(은밀)"
"call:squad_combat_normal:전투(통상)"
"call:squad_combat_aggressive:전투(적극)"
"call:squad_retreat:후퇴"
"call:squad_wait:대기"

# 표시 조건: can:squad_directive == 1 (NPC 리더 파티 합류 시 활성)
```

### 7.3 NPC 리더 성향에 의한 반응 조정

NPC 리더는 플레이어가 설정한 방침을 **자신의 성향에 따라 해석**한다.
기본적으로 방침을 그대로 따르지만, 성향과 충돌 시 변환/거부할 수 있다.

```python
# NPC 클래스에 추가
PARTY_LEADER_BEHAVIOR = {
    "auto_style": "aggressive",     # 자율 모드 시 기본 판단 성향
    "override_rules": {
        # directive → (변환 결과, 변환 확률)
        # None이면 그대로 실행
    },
    "override_chance": 0.0,         # 기본: 오버라이드 안함
}

# 세라 — 공격적, 후퇴를 거부하는 성향
class Sera(Character):
    PARTY_LEADER_BEHAVIOR = {
        "auto_style": "aggressive",
        "override_rules": {
            "retreat": ("combat_normal", 0.4),   # 40% 후퇴→통상전투 변환
            "combat_stealth": ("combat_normal", 0.3),  # 30% 은밀→통상 변환
        },
        "override_chance": 0.3,
    }

# 밀라 — 신중, 적극 전투를 거부하는 성향
class Mila(Character):
    PARTY_LEADER_BEHAVIOR = {
        "auto_style": "defensive",
        "override_rules": {
            "combat_aggressive": ("combat_normal", 0.5),  # 50% 적극→통상
        },
        "override_chance": 0.2,
    }

# 유키 — 은밀 선호
class Yuki(Character):
    PARTY_LEADER_BEHAVIOR = {
        "auto_style": "combat_stealth",
        "override_rules": {
            "combat_aggressive": ("combat_stealth", 0.6),  # 60% 적극→은밀
            "combat_normal": ("combat_stealth", 0.3),      # 30% 통상→은밀
        },
        "override_chance": 0.4,
    }
```

**리더 AI 방침 해석 흐름:**

```python
def _interpret_directive(leader_id, directive):
    """NPC 리더가 방침을 해석

    Returns:
        실제 실행할 directive (변환될 수 있음)
    """
    behavior = _get_party_leader_behavior(leader_id)
    if not behavior:
        return directive

    # 자율 → 리더 성향
    if directive == "auto":
        return behavior.get("auto_style", "combat_normal")

    # 오버라이드 체크
    override_rules = behavior.get("override_rules", {})
    if directive in override_rules:
        new_directive, chance = override_rules[directive]
        import random
        if random.random() < chance:
            name = _get_name(leader_id)
            morld.add_action_log(f"{name}이(가) 방침을 자기 판단으로 변경했다.")
            return new_directive

    return directive  # 그대로 실행
```

**방침 변환 시 UI:**

```python
# 리더가 방침을 변환했을 때 로그
morld.add_action_log("[color=yellow]세라가 후퇴 대신 통상 전투를 선택했다.[/color]")
```

### 7.4 NPC 리더 파티 생성

```python
def create_npc_party(leader_id, member_ids=None, include_player=True):
    """NPC 리더 파티 생성 (이벤트/퀘스트용)

    Args:
        leader_id: NPC 리더 unit_id
        member_ids: 초기 멤버 리스트 (리더 제외)
        include_player: 플레이어를 멤버로 포함할지
    """
    global _party

    party = _create_party(leader_id, "npc")
    if party is None:
        return None

    # 멤버 추가
    if member_ids:
        for mid in member_ids:
            _add_member(mid)

    # 플레이어 포함 시
    if include_player:
        player_id = morld.get_player_id()
        _add_player_to_npc_party(player_id)

    return party


def _add_player_to_npc_party(player_id):
    """플레이어를 NPC 리더 파티에 추가"""
    if _party is None:
        return

    _party.members.append(player_id)
    morld.set_unit_prop(player_id, "파티:역할", "멤버")
    morld.set_unit_prop(player_id, "파티:리더", _party.leader_id)

    # 플레이어 액션 변경: 이탈 가능
    morld.set_unit_prop(player_id, "can:leave_party", 1)
    morld.set_unit_prop(player_id, "can:recruit_party", 0)
```

### 7.5 플레이어 이탈

NPC 리더 파티에서 플레이어는 "이탈" 액션으로 탈퇴:

```python
# player.py 액션 (NPC 리더 파티 시)
"call:leave_party:파티 이탈"
"can:leave_party": 0,    # 기본 비활성, NPC 파티 합류 시 1

def leave_party(self):
    """플레이어가 NPC 리더 파티에서 이탈"""
    import party
    player_id = self.instance_id

    party._remove_player_from_npc_party(player_id)
    morld.add_action_log("파티에서 이탈했다.")
```

---

## 8. NPC 리더 AI

### 8.1 NPC 리더의 think() 동작

NPC 리더는 **자신의 스케줄**대로 행동합니다 (follow가 아님).
파티 멤버들이 리더를 follow합니다.

```python
# think/__init__.py — NPC 리더 think() 분기

# Tier 2에서 파티 상태 체크:
def _check_party_leader(self):
    """파티 리더인 경우 특수 동작"""
    import party
    if not party.is_party_leader(self.unit_id):
        return False

    p = party.get_party()
    if p.leader_type != "npc":
        return False

    # NPC 리더는 자신의 스케줄 실행 (특별한 변경 없음)
    # 단, 멤버 상태 체크:

    # 1. 기절 멤버 발견 → 잠시 대기
    for mid in p.members:
        import survival
        if survival.is_npc_fainted(mid):
            # 간호 (선택적) 또는 대기
            pass

    # 2. 전투 상황 → 파티 전투 진입
    # (combat 연동에서 처리)

    return False  # 리더는 자신의 스케줄 진행 (True 반환 안함)
```

### 8.2 NPC 리더 경로 제어

NPC 리더의 이동 경로는 **스케줄** 또는 **이벤트 스크립트**로 제어:

```python
# 이벤트에서 NPC 리더 경로 설정 예시
def escort_quest_start():
    """호위 퀘스트: 세라가 광산까지 안내"""
    import party

    sera_id = morld.get_instance_id("sera")

    # 호위 경로 스케줄
    escort_schedule = [
        {"name": "출발", "activity": "이동", "start": 0, "end": 14_400_000,
         "target": {"region_id": 3, "location_id": 5}},
        {"name": "광산 도착", "activity": "대기", "start": 14_400_000, "end": 28_800_000},
    ]

    # 파티 생성 + 스케줄 설정
    p = party.create_npc_party(sera_id, include_player=True)
    agent = think.get_agent(sera_id)
    if agent:
        agent.push_schedule(escort_schedule)
```

---

## 9. 플레이어 참여 (NPC 리더 파티)

### 9.1 플레이어의 이동

NPC 리더 파티에서 플레이어의 이동:

**자동 follow (기본):**
- 시간 경과 시(`advance_time_des`) 플레이어가 NPC 리더를 자동 추적
- C# `follow` 동작과 동일

**수동 이동 (자유):**
- 플레이어는 여전히 직접 이동 가능
- 리더의 Location을 벗어나면 "파티에서 떨어지고 있다" 경고
- 일정 거리 이상 벗어나면 자동 이탈 또는 대기 전환

### 9.2 이탈 거리 체크

```python
# 1시간마다 (subscribe_time_elapsed) 체크
def _check_party_separation():
    """파티 분리 체크 — 멤버가 리더와 다른 Location에 있으면 경고"""
    if _party is None:
        return

    leader_loc = morld.get_unit_location(_party.leader_id)
    if not leader_loc:
        return

    for member_id in list(_party.members):
        if member_id in _party.waiting:
            continue  # 대기 멤버는 체크 안함

        member_loc = morld.get_unit_location(member_id)
        if not member_loc:
            continue

        # 같은 Region이 아니면 경고
        if member_loc[0] != leader_loc[0]:
            _on_member_separated(member_id, "different_region")
        # 같은 Region, 다른 Location이면 경고
        elif member_loc[1] != leader_loc[1]:
            _on_member_separated(member_id, "different_location")


def _on_member_separated(member_id, reason):
    """멤버 분리 시 처리"""
    player_id = morld.get_player_id()
    if member_id == player_id:
        morld.add_action_log("[color=yellow]파티 리더와 떨어지고 있다.[/color]")
    # NPC 멤버는 자동으로 follow 재시도 (think에서 처리)
```

---

# Part D: 이동

## 10. follow 통합

### 10.1 follow job 갱신 타이밍

파티 멤버의 follow job은 **think() 호출 시** 갱신:

```python
# think/__init__.py — 파티 멤버 follow 처리
def _check_party_follow(self):
    """파티 follow 체크 — think()에서 Tier 2 직후 호출

    Returns:
        True: follow job 삽입됨 (다른 tier 스킵)
        False: 파티 관련 처리 없음
    """
    import party

    if not party.is_in_party(self.unit_id):
        return False
    if party.is_party_leader(self.unit_id):
        return False  # 리더는 자신의 스케줄 실행
    if party.is_waiting(self.unit_id):
        return False  # 대기 멤버는 자유행동

    # 리더 위치 조회
    p = party.get_party()
    leader_loc = morld.get_unit_location(p.leader_id)
    my_loc = self.get_location()

    if not leader_loc or not my_loc:
        return False

    # 같은 Location에 있으면 idle (리더 근처 대기)
    if my_loc[0] == leader_loc[0] and my_loc[1] == leader_loc[1]:
        # 리더와 같은 장소 → 짧은 idle
        self._insert_idle_job("파티 대기", self._get_action_duration("brief"))
        return True

    # 다른 Location이면 follow job
    morld.set_npc_job(self.unit_id, "follow", MILLIS_PER_DAY, p.leader_id)
    self._action_taken = True
    return True
```

### 10.2 X 좌표 오프셋 (대형)

같은 Location 내에서 멤버가 리더와 겹치지 않도록 오프셋:

```python
def _get_follow_offset(member_index):
    """멤버 인덱스에 따른 X 오프셋

    대형:
      [멤버1]  [리더]  [멤버2]
                      [멤버3]
    """
    offsets = [-30, 30, -15]  # 3인 최대
    if member_index < len(offsets):
        return offsets[member_index]
    return 0
```

> **주의:** C# follow는 대상의 정확한 X 좌표로 이동하므로, 오프셋 적용은
> follow 완료 후 미세 조정이 필요합니다. Phase 1에서는 오프셋 없이 구현하고,
> 멤버들이 리더와 같은 위치에 겹치는 것을 허용합니다.
> Phase 2에서 C# follow에 오프셋 파라미터를 추가하는 방향 검토.

---

## 11. 대기/집결

### 11.1 대기 명령 동작

대기 명령을 받은 멤버:

1. `파티:대기` prop = 1 설정
2. `_party.waiting[unit_id] = location_dict` 저장
3. stay job 삽입 (MILLIS_PER_DAY)
4. think()에서 `_check_party_follow()`가 `is_waiting()` True → 건너뜀
5. **Tier 3-5 스킵**: 대기 중에는 자유행동 (일반 스케줄 또는 idle)

```python
# 대기 멤버의 think() 동작
# 파티 follow가 False → 일반 Tier 진행
# 단, push된 PARTY_FOLLOW_SCHEDULE이 있으므로
# schedule의 activity = "파티" → _handle_default_activity에서 idle

# 실제 구현: 대기 멤버는 push_schedule 유지 + stay job으로
# think()가 불릴 때마다 idle job 삽입
```

### 11.2 집결 명령 동작

집결(gather) 명령:
1. 모든 대기 멤버의 `파티:대기` prop 해제
2. `_party.waiting` 딕셔너리 클리어
3. 각 멤버에게 follow job 재설정
4. 멤버들이 리더의 현재 위치로 이동 시작

---

## 12. Gate 이동 (Location 간)

### 12.1 리더 이동 시 멤버 동작

리더가 Gate를 통해 다른 Location으로 이동하면:

1. C# `follow` action이 멤버를 리더의 새 Location으로 안내
2. Gate 통과 = 즉시 이동 (StayDuration만큼 지체 가능)
3. 멤버가 도착하면 on_reach 이벤트 발생

**문제점:**
- 리더가 빠르게 여러 Location을 통과하면 멤버가 뒤처짐
- C# follow는 매 step마다 대상의 **현재** 위치를 추적하므로, 리더가 A→B→C로 이동하면 멤버도 A→C로 직행 (B 건너뜀)

**해결 (Phase 1):**
- 허용: 멤버가 중간 Location을 건너뛰는 것을 허용
- 다른 Region으로 이동 시에만 주의 (RegionGate 통과 시 동기화)

### 12.2 Region 이동 시 동기화

리더가 RegionGate를 통과하면 파티 멤버도 함께 이동해야 합니다:

```python
def on_leader_region_change(leader_id, new_region_id, new_location_id):
    """리더가 Region 이동 시 — 멤버 동기화

    on_reach 이벤트에서 호출.
    대기 중이 아닌 멤버를 리더와 같은 Region으로 텔레포트.
    """
    if _party is None or _party.leader_id != leader_id:
        return

    for member_id in _party.members:
        if member_id in _party.waiting:
            continue  # 대기 멤버는 텔레포트 안함

        member_loc = morld.get_unit_location(member_id)
        if not member_loc:
            continue

        # 다른 Region에 있으면 텔레포트
        if member_loc[0] != new_region_id:
            morld.set_unit_location(member_id, new_region_id, new_location_id)
            # follow job 재설정
            morld.set_npc_job(member_id, "follow", MILLIS_PER_DAY, leader_id)
```

> **주의:** 텔레포트는 게임플레이상 어색할 수 있습니다.
> Phase 1에서는 텔레포트 + "뒤따라왔다" 로그로 처리.
> Phase 2에서 Region 이동 연출 개선 검토.

---

# Part E: 전투

## 13. 전투 합류

### 13.1 파티 멤버 자동 합류

combat-implementation.md의 `check_npc_combat_join()`을 확장:

```python
# combat.py — 파티 멤버 우선 합류
def check_npc_combat_join(location_id):
    """전투 합류 체크 — 파티 멤버 우선"""
    import party

    joiners = []
    p = party.get_party()

    # 1. 파티 멤버 (호감도 체크 생략)
    if p:
        for member_id in p.members:
            if member_id == morld.get_player_id():
                continue  # 플레이어는 별도 처리
            behavior = _get_battle_behavior(member_id)
            if not behavior:
                continue
            party_behavior = _get_party_behavior(member_id)
            if party_behavior and not party_behavior.get("combat_join_in_party", True):
                continue  # combat_join_in_party = False (리나 등)

            # 전투 가능 상태만 체크 (호감도 무시)
            if can_fight(member_id):
                joiners.append(member_id)

    # 2. 비파티 NPC (기존 로직 — 호감도 체크)
    npcs = get_friendly_npcs_at_location(location_id)
    for npc_id in npcs:
        if party.is_in_party(npc_id):
            continue  # 이미 처리됨
        # 기존 check_npc_combat_join 로직...

    return joiners
```

### 13.2 전투 시작 알림

```python
def _notify_party_combat(attacker_id, target_id):
    """파티에 전투 시작 알림

    리더가 전투 시작 → 멤버에게 알림
    멤버가 공격받음 → 리더 + 다른 멤버에게 알림
    """
    import party

    p = party.get_party()
    if not p:
        return

    if not p.is_member(attacker_id) and not p.is_member(target_id):
        return  # 파티와 무관한 전투

    # 전투 참여 플래그 설정
    for member_id in p.all_unit_ids:
        morld.set_unit_prop(member_id, "파티:전투중", 1)
```

---

## 14. 전투 정책

### 14.1 정책별 동작

| 정책 | 적 발견 | 피격 | 리더 피격 | 후퇴 조건 |
|------|---------|------|----------|----------|
| aggressive | 자동 공격 | 반격 | 보호 우선 | HP < threshold |
| defensive | 무시 | 반격 | 보호 우선 | HP < threshold |
| pacifist | 도주 | 도주 | 도주 | 항상 (전투 회피) |

### 14.2 정책 적용 (think 통합)

```python
def _get_combat_action_for_policy(agent, enemy_id):
    """전투 정책에 따른 행동 결정

    Returns:
        "attack": 공격
        "defend": 방어 자세
        "flee": 도주
        None: 무시
    """
    import party
    p = party.get_party()
    if not p:
        return None

    policy = p.policy
    behavior = getattr(agent, 'BATTLE_BEHAVIOR', {})

    if policy == POLICY_AGGRESSIVE:
        return "attack"

    elif policy == POLICY_DEFENSIVE:
        # 피격 시에만 반격
        is_being_attacked = morld.get_unit_prop(agent.unit_id, "전투:피격자") == enemy_id
        leader_attacked = morld.get_unit_prop(p.leader_id, "전투:피격자") is not None
        if is_being_attacked or leader_attacked:
            return "attack"
        return "defend"

    elif policy == POLICY_PACIFIST:
        return "flee"

    return None
```

### 14.3 리더 보호

`BATTLE_BEHAVIOR.protect_player`가 True인 멤버의 리더 보호:

```python
def _check_protect_leader(agent):
    """리더가 공격받으면 끼어들기"""
    import party, combat

    p = party.get_party()
    if not p:
        return False

    behavior = getattr(agent, 'BATTLE_BEHAVIOR', {})
    if not behavior.get("protect_player", False):
        return False

    # 리더가 전투 중인지
    leader_combat = combat.get_combat_state(p.leader_id)
    if not leader_combat:
        return False

    # 리더의 적을 대신 공격
    enemy_id = leader_combat.get("target_id")
    if enemy_id:
        combat.switch_target(agent.unit_id, enemy_id)
        return True

    return False
```

---

## 15. 전투 중 역할

### 15.1 전투 종료 시 복원

전투 종료 후 파티 멤버 상태 복원:

```python
def on_combat_end():
    """전투 종료 시 파티 복원"""
    if _party is None:
        return

    for member_id in _party.members:
        # 전투 플래그 해제
        morld.clear_prop(member_id, "파티:전투중")

        # 기절 멤버 처리
        import survival
        if survival.is_npc_fainted(member_id):
            _remove_member(member_id, reason="faint")
            continue

        # 대기 멤버는 대기 유지
        if member_id in _party.waiting:
            continue

        # follow 복원
        morld.set_npc_job(member_id, "follow", MILLIS_PER_DAY, _party.leader_id)

    # 리더 전투 플래그 해제
    morld.clear_prop(_party.leader_id, "파티:전투중")
```

### 15.2 멤버 사망/기절

```python
def on_member_faint(unit_id):
    """파티 멤버 기절 시"""
    if _party is None:
        return
    if unit_id not in _party.members:
        return

    # 기절 멤버는 파티에서 제거
    _remove_member(unit_id, reason="faint")
    morld.add_action_log(f"{_get_name(unit_id)}이(가) 쓰러져 파티에서 이탈했다.")

    # 마지막 멤버였으면 해산
    if not _party.members:
        _disband_party()


def on_member_death(unit_id):
    """파티 멤버 사망 시"""
    if _party is None:
        return
    _remove_member(unit_id, reason="death")
```

---

# Part F: think 통합

## 16. Tier 삽입

### 16.1 파티 follow의 위치

파티 follow 체크는 **Tier 2 (Reactive)와 Tier 3 (Survival) 사이**에 삽입:

```
[Tier -1] Carry (운반 중)
[Tier 0]  Restraint (결박)
[Tier 1]  Involuntary (기절, 수면)
[Tier 2]  Reactive (전투 위협, 소리, 구출)
[Tier 2.5] ★ Party Follow (파티 멤버 → 리더 따라가기)  ← 새로 삽입
[Tier 3]  Survival (배고픔, 추위, 더위)
[Tier 4]  Comfort (목욕, 배변, 수면 등)
[Tier 5]  Routine (스케줄)
```

**이유:**
- 기절/수면(Tier 1)은 파티보다 우선 (기절하면 follow 불가)
- 전투 위협(Tier 2)은 파티보다 우선 (전투 중이면 전투 AI 실행)
- 파티 follow는 생존(Tier 3)보다 우선 (배고프더라도 일단 따라가기)
- **예외:** 대기 멤버는 Tier 2.5 건너뜀 → Tier 3-5 진행

### 16.2 think() 수정

```python
# think/__init__.py — think() 수정

def think(self):
    self._action_taken = False
    _tier_reached = 0

    # Tier -1: 운반 중
    import carry
    if carry.is_being_carried(self.unit_id):
        self._handle_being_carried()
        return None

    # Tier 0: 결박
    import restraint
    if restraint.is_restrained(self.unit_id):
        if restraint.is_lower_restrained(self.unit_id):
            self._handle_restrained()
            return None
        else:
            self._handle_upper_restrained()
            return None

    schedule = self.get_current_schedule()
    if schedule:
        # Tier 1: 비자발적 (기절, 수면)
        if self._check_tier1_involuntary():
            _tier_reached = 1
        else:
            self._ensure_standing()

            # Tier 2: 반응형 (전투 위협, 구출, 소리)
            if self._check_restrained_nearby():
                _tier_reached = 2
            elif self._check_tier2_reactive():
                _tier_reached = 2

            # ★ Tier 2.5: 파티 follow
            elif self._check_party_follow():
                _tier_reached = 2  # 디버그용: 2로 표기

            # Tier 3: 생존
            elif self._check_tier3_survival():
                _tier_reached = 3
            # Tier 4: 쾌적
            elif self._check_tier4_comfort():
                _tier_reached = 4
            else:
                # Tier 5: 일과
                _tier_reached = 5
                self._check_tier5_routine()

    # safety net
    if not self._action_taken:
        # ... 기존 safety net 코드 ...
        pass

    return None
```

---

## 17. 파티 핸들러

### 17.1 _check_party_follow() 전체 구현

```python
# think/__init__.py — BaseAgent 메서드

def _check_party_follow(self):
    """Tier 2.5: 파티 follow 체크

    Returns:
        True: 파티 follow 처리됨 (action_taken)
        False: 파티 무관 또는 대기 상태
    """
    import party

    # 파티 미소속
    if not party.is_in_party(self.unit_id):
        return False

    # 리더는 자신의 스케줄 실행
    if party.is_party_leader(self.unit_id):
        return False

    # 대기 멤버는 자유행동
    if party.is_waiting(self.unit_id):
        return False

    # 자발적 탈퇴 체크
    if party._check_member_leave(self.unit_id):
        party._remove_member(self.unit_id, reason="leave")
        morld.add_action_log(f"{self.get_info().get('name', '?')}이(가) 파티에서 이탈했다.")
        return False  # 탈퇴 후 일반 스케줄 진행

    # 리더 기절 상태면 자유행동
    p = party.get_party()
    import survival
    if survival.is_npc_fainted(p.leader_id):
        return False

    # 리더 위치 조회
    leader_loc = morld.get_unit_location(p.leader_id)
    my_loc = self.get_location()

    if not leader_loc or not my_loc:
        return False

    # 같은 Location이면 짧은 대기
    if my_loc[0] == leader_loc[0] and my_loc[1] == leader_loc[1]:
        self._insert_idle_job("파티 대기", self._get_action_duration("brief"))
        return True

    # 다른 Location이면 follow
    self._move_to({
        "region_id": leader_loc[0],
        "location_id": leader_loc[1],
    }, "파티 이동")
    return True
```

### 17.2 _memory 확장

파티 관련 _memory 키 (필요 시):

```python
# think/__init__.py — _memory 초기화에 추가
"party_combat_target": None,    # 파티 전투 시 배정된 적 ID
```

> **최소 설계:** 파티 상태는 대부분 `party.py` 모듈에서 관리하므로,
> _memory에는 전투 중 타겟 배정만 저장합니다.
> 파티 소속 여부는 `party.is_in_party()`로 조회.

---

## 18. 인터럽트 공존

### 18.1 파티 follow와 기존 인터럽트

| Tier | 인터럽트 | 파티 follow보다 우선? | 비고 |
|------|---------|---------------------|------|
| -1 | 운반 (Carry) | O | 운반 중이면 follow 불가 |
| 0 | 결박 (Restraint) | O | 결박 중이면 follow 불가 |
| 1 | 기절/수면 | O | 기절/수면 중이면 follow 불가 |
| 2 | 전투 위협 | O | 전투 중이면 전투 AI 실행 |
| 2 | 구출 | O | 구출 우선 |
| **2.5** | **파티 follow** | — | **여기에 삽입** |
| 3 | 배고픔 | X | 따라가면서 식사 불가 (도착 후) |
| 3 | 추위/더위 | X | 따라가면서 착의 불가 (도착 후) |
| 4 | 배변/목욕 등 | X | 리더 도착 후 짧은 시간에 해결 |

### 18.2 대기 멤버의 인터럽트

대기 상태 멤버는 Tier 2.5를 건너뛰므로 Tier 3-5가 정상 실행:

- 대기 중 배고프면 → 식사 (Tier 3)
- 대기 중 추우면 → 방한 (Tier 3)
- 대기 중 졸리면 → 수면 (Tier 4)

**주의:** 대기 멤버도 push된 PARTY_FOLLOW_SCHEDULE이 활성이므로,
Tier 5에서 `activity == "파티"` → `_handle_default_activity`가 호출됩니다.
이때 activity가 `_WANDER_ACTIVITIES`에 없고 ACTIVITY_HANDLERS에도 없으므로
idle job 삽입 (대기 동작).

---

# Part G: UI/UX

## 19. 파티 UI

### 19.1 3레이어 묘사 통합

파티/전투 행동은 기존 UI 3레이어에 자연스럽게 통합된다.
**추가 시스템 구현 불필요 — 룰 데이터만 추가.**

| 레이어 | 기존 용도 | 파티/전투 용도 | API |
|--------|----------|-------------|-----|
| **Describe Text** | 장소 묘사 ("세라가 경계하고 있다") | 파티 활동 묘사 | `DESCRIBE_RULES` + activity 매칭 |
| **Focus Text** | 클릭 시 상세 | 파티 상태 상세 | `FOCUS_RULES` |
| **Action Log** | 이벤트 메시지 | 전투 결과, 명령 거부 | `morld.add_action_log(msg)` |
| **Animlog** | 연출 시퀀스 | 보스전 컷씬 (미래) | `ui.Animlog()` block 모드 |

**Describe Text 추가 예시 (캐릭터별 DESCRIBE_RULES):**

```python
# sera.py — DESCRIBE_RULES에 파티 활동 추가
activities=[
    # 기존
    ("순찰", "{name}가 주변을 경계하고 있다."),
    ("벌목", "{name}가 묵묵히 나무를 베고 있다."),
    # 파티 추가
    ("파티", "{name}가 함께 걷고 있다."),
    ("파티 대기", "{name}가 팔짱을 끼고 기다리고 있다."),
    ("파티 작업: 자원 수집해", "{name}가 자원을 모으고 있다."),
    ("전투:공격", "{name}가 활을 재빠르게 겨눈다."),
    ("전투:방어", "{name}가 방어 자세를 취하고 있다."),
]
```

**Focus Text 추가 예시:**

```python
# sera.py — FOCUS_RULES에 파티 컨텍스트 추가
activities=[
    ("파티", "날카로운 눈으로 주변을 경계하며 걷고 있다."),
    ("파티 대기", "팔짱을 끼고 불만스러운 표정이다."),
]
```

**Action Log 사용 시점:**

```python
# 전투 행동
morld.add_action_log("세라가 드래곤에게 15의 피해를 입혔다!")
morld.add_action_log("[color=red]리나는 회피했다![/color]")

# 명령 거부
morld.add_action_log("[color=yellow]세라가 후퇴 지시를 무시했다.[/color]")

# 파티 이벤트
morld.add_action_log("밀라가 파티에서 이탈했다.")
morld.add_action_log("[color=cyan]전원 집결 명령을 내렸다.[/color]")
```

**context 확장 (base.py `_build_context()`):**

```python
# 파티 관련 컨텍스트 추가
import party
context["in_party"] = party.is_in_party(unit_id)
context["party_role"] = morld.get_unit_prop(unit_id, "파티:역할")  # 리더/멤버
context["party_waiting"] = party.is_waiting(unit_id)
context["in_combat"] = morld.get_unit_prop(unit_id, "파티:전투중") == 1
```

### 19.2 파티 상태 표시

파티 상태는 UI에 간단히 표시:

```python
# ui.py — 파티 상태 표시 (info 패널)
def _render_party_status():
    """파티 상태 문자열 생성"""
    import party

    p = party.get_party()
    if not p:
        return ""

    leader_name = _get_name(p.leader_id)
    lines = [f"[color=cyan]파티[/color] ({p.size}/{MAX_PARTY_SIZE})"]

    # 리더
    lines.append(f"  ★ {leader_name} (리더)")

    # 멤버
    for mid in p.members:
        name = _get_name(mid)
        status = ""
        if party.is_waiting(mid):
            status = " [color=yellow](대기)[/color]"
        elif morld.get_unit_prop(mid, "파티:전투중"):
            status = " [color=red](전투중)[/color]"
        lines.append(f"  • {name}{status}")

    # 전투 정책
    policy_label = party._POLICY_LABELS.get(p.policy, p.policy)
    lines.append(f"  정책: {policy_label}")

    return "\n".join(lines)
```

### 19.3 파티 액션 표시 조건

```python
# assets/base.py — 동적 액션 필터링

# 파티 관련 액션 표시 규칙:
# "동행 요청" → 파티 미소속 NPC focus 시 + recruitable + 인원 여유
# "동행 해제" → 파티 멤버 NPC focus 시
# "{name} 따라와" → 대기 중인 파티 멤버 focus 시
# "{name} 대기" → follow 중인 파티 멤버 focus 시
# "전원 따라와" / "전원 대기" / "전원 집결" → 파티 존재 시 플레이어 액션
# "파티 해산" → 플레이어 리더 파티 존재 시
# "파티 이탈" → NPC 리더 파티에서 플레이어 멤버 시
```

---

## 20. 대사/리액션

### 20.1 동행 수락/거절

```python
# 동행 수락 리액션 (캐릭터 아키타입별)
RECRUIT_ACCEPT = {
    "stoic": "...알았다.",
    "gentle": "네, 함께 가요.",
    "cheerful": "좋아! 같이 가자~",
    "timid": "저... 저도 괜찮을까요?",
    "cold": "...마음대로 해.",
    "fierce": "흥, 약하면 두고 가겠어.",
    "proud": "그래, 따라오는 건 허락하지.",
    "innocent": "와, 모험이다!",
    "devoted": "언제든 함께할게요.",
    "seductive": "후후, 둘이서... 아, 파티?",
}

RECRUIT_REJECT = {
    "stoic": "...지금은 안 된다.",
    "gentle": "미안해요, 지금은 좀...",
    "cheerful": "음~ 나중에!",
    "timid": "아직... 준비가 안 됐어요...",
    "cold": "싫어.",
    "fierce": "너랑? 됐어.",
    "proud": "아직 자격이 부족해.",
    "innocent": "으음... 무서워...",
    "devoted": "조금만 더 알고 싶어요.",
    "seductive": "아직은 이른 것 같아~",
}
```

### 20.2 파티 내 반응

NPC on_meet_player 이벤트에서 파티 상태 체크:

```python
# assets/base.py — on_meet_player 확장
def on_meet_player(self, player_id):
    # ... 기존 체크 (로맨스 발각, 기절 등) ...

    # 파티 멤버인 경우 — 일상 인사 대신 동행 대사
    import party
    if party.is_in_party(self.instance_id):
        # 파티 중 on_meet는 빈번하므로 쿨다운 적용
        last_party_greet = self._memory.get("party_greet_cooldown")
        now = morld.get_current_time()
        if last_party_greet and now - last_party_greet < 3_600_000:  # 1시간
            return None  # 인사 스킵
        self._memory["party_greet_cooldown"] = now
        # 간단한 동행 대사
        yield ui.dialog([f"[{self.name}]", _get_party_greeting(self)])
```

---

# Part H: 통합

## 21. 파일 목록

### 21.1 신규 파일

| 파일 | 설명 |
|------|------|
| `scenarios/scenario02/python/party.py` | 파티 시스템 코어 (Party 클래스, API, 명령) |

### 21.2 수정 파일

| 파일 | 수정 내용 | 위치 |
|------|----------|------|
| `think/__init__.py` | `_check_party_follow()` 추가, think() Tier 2.5 삽입 | ~line 1565 |
| `think/__init__.py` | `_check_return_home()` 추가, Tier 5 귀환 체크 | ~line 1460 |
| `think/__init__.py` | `_memory`에 `party_combat_target` 추가 | ~line 122 |
| `assets/base.py` | `recruit_party()`, `dismiss_party()` 메서드 | Character 클래스 |
| `assets/base.py` | `PARTY_BEHAVIOR` 클래스 속성 기본값 (`recruit_submission` 포함) | Character 클래스 |
| `assets/base.py` | `_build_context()`에 파티 컨텍스트 추가 | ~line 1220 |
| `assets/base.py` | on_meet_player 파티 분기 | ~line 3280 |
| `assets/characters/player.py` | 파티 관련 can: props, 액션, 분대 방침 액션 | props, actions |
| `assets/characters/sera.py` | `PARTY_BEHAVIOR` + `PARTY_LEADER_BEHAVIOR` 오버라이드 | 클래스 상단 |
| `assets/characters/mila.py` | `PARTY_BEHAVIOR` + `PARTY_LEADER_BEHAVIOR` 오버라이드 | 클래스 상단 |
| `assets/characters/lina.py` | `PARTY_BEHAVIOR` 오버라이드 | 클래스 상단 |
| `assets/characters/yuki.py` | `PARTY_BEHAVIOR` + `PARTY_LEADER_BEHAVIOR` 오버라이드 | 클래스 상단 |
| `assets/characters/ella.py` | `PARTY_BEHAVIOR` 오버라이드 | 클래스 상단 |
| `chapters/__init__.py` | `party.reset()` 호출 추가 | load_chapter() |
| `events/__init__.py` | on_reach에서 Region 이동 시 파티 동기화 | on_reach 핸들러 |
| `combat.py` | 파티 멤버 전투 합류 우선 | check_npc_combat_join() |
| `settings.py` (선택) | 전투 정책 토글 | 파티 섹션 |
| `ui.py` | 파티 상태 표시 | info 패널 |

---

## 22. 구현 순서

### Phase 1: 기본 파티 (플레이어 리더)

```
Step 1: party.py 코어
  - Party 클래스
  - _create_party(), _disband_party()
  - _add_member(), _remove_member()
  - 공개 API (is_in_party, get_party 등)
  - 내부 헬퍼 (_get_name, _get_player_name, _get_*_behavior, _get_*_to_leader)
  - reset()

Step 2: 동행 요청/해제
  - player.py can:recruit_party prop
  - base.py recruit_party(), dismiss_party()
  - 캐릭터별 PARTY_BEHAVIOR (recruit_affection + recruit_submission)
  - 호감도 OR 복종도 이중 경로 체크

Step 3: think 통합
  - _check_party_follow() 구현
  - think() Tier 2.5 삽입
  - _check_return_home() 구현 (Tier 5 귀환 체크)
  - safety net에 party 관련 phase 추가

Step 4: 명령 체계
  - command_follow(), command_wait(), command_gather()
  - 플레이어 액션 추가 (전원 따라와/대기/집결/해산)
  - NPC focus 액션 (개별 따라와/대기)
  - 비전투 명령 (command_task: 자원 수집/청소/제작/건축/요리)
  - 지시 무시 판정 (_check_command_refusal: 반발/복종/상태/성향)

Step 5: 전투 연동
  - combat.py check_npc_combat_join 파티 확장
  - 전투 정책 (aggressive/defensive/pacifist)
  - on_combat_end 파티 복원
  - 멤버 기절/사망 처리

Step 6: UI
  - 파티 상태 표시
  - 3레이어 묘사 통합 (Describe/Focus/ActionLog)
  - 대사/리액션 (수락/거절)
  - _build_context()에 파티 컨텍스트 추가

Step 7: 챕터 전환
  - chapters/__init__.py에 party.reset() 추가
```

### Phase 2: NPC 리더 + 고급 기능

```
Step 8: NPC 리더 파티
  - create_npc_party()
  - 플레이어 참여/이탈
  - NPC 리더 경로 제어

Step 9: NPC 분대 명령 + 리더 오버라이드
  - SQUAD_DIRECTIVES (자율/수색/전투×3/후퇴/대기)
  - PARTY_LEADER_BEHAVIOR (캐릭터별 성향)
  - _interpret_directive() (리더 AI 방침 해석)
  - 분대 방침 플레이어 액션

Step 10: Region 이동 동기화
  - on_reach 이벤트 연동
  - Region 이동 시 텔레포트

Step 11: X 오프셋 대형
  - C# follow 오프셋 파라미터 추가 (필요 시)
  - 멤버 인덱스별 대형

Step 12: 고급 전투
  - 리더 보호 (protect_player)
  - 타겟 배분
  - 전투 중 명령 (공격해/물러나)
```

### Phase 3: Scenario 03 확장 (미래)

```
- NPC 전용 분대 (플레이어 미참여)
- 거시 명령 (전체 방향)
- 미시 명령 (개별 유닛 지정)
- 전술 AI (협공, 포위, 엄호)
- 분대 간 연합 작전
```

---

## 23. 테스트 계획

### 23.0 MockMorld 보완

combat/party 테스트를 위해 `tests/mock_morld.py`에 추가 필요:

```python
# mock_morld.py — 추가 메서드

def get_actual_props(self, unit_id):
    """base props + 장착 아이템 equip_props 합산 (combat.get_combat_stat 의존)"""
    unit = self._units.get(unit_id)
    if not unit:
        return {}
    result = dict(unit["props"])
    for item_id, count in unit.get("inventory", {}).items():
        item = self._items.get(item_id)
        if item and item.get("equip_props"):
            for k, v in item["equip_props"].items():
                result[k] = result.get(k, 0) + v
    return result

def set_unit(self, unit_id, key, value):
    """유닛 속성 변경 (name 등)"""
    unit = self._units.get(unit_id)
    if unit:
        unit["info"][key] = value

def get_current_time(self):
    return self._time
```

### 23.1 단위 테스트

```python
# tests/test_party.py

def test_create_party():
    """파티 생성 + 멤버 추가"""
    party.reset()
    p = party._create_party(player_id, "player")
    assert p is not None
    assert p.leader_id == player_id
    assert p.size == 1

    # 멤버 추가
    assert party._add_member(sera_id)
    assert p.size == 2
    assert party.is_in_party(sera_id)

    # 최대 인원 (4인)
    party._add_member(mila_id)
    party._add_member(lina_id)
    assert p.size == 4
    assert not party._add_member(yuki_id)  # 초과


def test_disband_party():
    """파티 해산"""
    party.reset()
    party._create_party(player_id, "player")
    party._add_member(sera_id)
    party._disband_party()
    assert party.get_party() is None
    assert not party.is_in_party(sera_id)


def test_party_commands():
    """대기/집결 명령"""
    party.reset()
    party._create_party(player_id, "player")
    party._add_member(sera_id)

    # 대기
    party.command_wait(sera_id)
    assert party.is_waiting(sera_id)

    # 집결
    party.command_gather()
    assert not party.is_waiting(sera_id)


def test_party_date_conflict():
    """데이트 중 파티 생성 불가"""
    date._start_date(player_id, sera_id)
    p = party._create_party(player_id, "player")
    assert p is None
    date._end_date(player_id)


def test_member_leave():
    """호감도 하락 시 탈퇴"""
    party.reset()
    party._create_party(player_id, "player")
    party._add_member(sera_id)

    # 호감도를 모집 조건의 50% 이하로 설정
    morld.set_unit_prop(sera_id, "관계:주인공:호감", 10)  # 30 * 0.5 = 15 이하

    assert party._check_member_leave(sera_id)
```

### 23.2 통합 테스트

```python
def test_party_follow_think():
    """파티 멤버 think() — follow 동작"""
    party.reset()
    party._create_party(player_id, "player")
    party._add_member(sera_id)

    # 리더와 다른 Location에 배치
    morld.set_unit_location(player_id, 0, 1)
    morld.set_unit_location(sera_id, 0, 5)

    # think() 실행
    agent = think.get_agent(sera_id)
    agent.think()

    # sera가 move job 삽입했는지 확인
    assert agent._action_taken


def test_party_combat_join():
    """파티 멤버 전투 합류"""
    party.reset()
    party._create_party(player_id, "player")
    party._add_member(sera_id)

    # 같은 Location에 적 배치
    joiners = combat.check_npc_combat_join(location_id)
    assert sera_id in joiners
```

### 23.3 시나리오 테스트

```
1. 기본 동행 시나리오
   - 세라에게 동행 요청 → 수락 → 이동 시 따라옴 → 해산
   - 호감도 부족한 NPC에게 요청 → 거절

2. 전투 시나리오
   - 파티 상태에서 몬스터 조우
   - 정책별 멤버 행동 확인 (aggressive/defensive/pacifist)
   - 멤버 기절 → 파티 탈퇴

3. 대기/집결 시나리오
   - 멤버 대기 → 자유행동 (식사 등) → 집결 → follow 복귀

4. 데이트 충돌
   - 데이트 중 동행 요청 불가 확인
   - 파티 중 데이트 요청 불가 확인

5. NPC 리더 (Phase 2)
   - NPC 주도 파티 생성 → 경로 이동 → 플레이어 이탈
```

---

## 부록: 기존 시스템 참조

### A. C# follow 동작

| 파일 | 라인 | 내용 |
|------|------|------|
| `job_behavior_system.cs` | 137-147 | follow action 처리 |
| `script_system_npc_api.cs` | 29-68 | set_npc_job 정의 (29) + follow 처리 (56-68) |
| `Unit.cs` | 48-81 | 위치/이동 상태 |
| `Unit.cs` | 423-443 | GetMovementSpeed() |

### B. date.py 패턴

| 파일 | 라인 | 내용 |
|------|------|------|
| `date.py` | 26-28 | FOLLOW_SCHEDULE |
| `date.py` | 48-65 | _start_date (push_schedule + follow job) |
| `date.py` | 68-86 | _end_date (pop_schedule) |

### C. think 시스템

| 파일 | 라인 | 내용 |
|------|------|------|
| `think/__init__.py` | 89-122 | _memory 초기화 |
| `think/__init__.py` | 1519-1596 | think() 본체 (5-tier) |
| `think/__init__.py` | 1770-1789 | _move_to() |
| `think/handlers/social.py` | 114-188 | 핸들러 패턴 예시 |

### D. survival 시스템

| 파일 | 라인 | 내용 |
|------|------|------|
| `survival.py` | 142 | `is_npc_fainted(unit_id)` — NPC 기절 여부 |
| `survival.py` | 241 | `_enter_faint(npc_id)` — NPC 기절 처리 |
| `survival.py` | 278 | `_enter_player_faint()` — 플레이어 기절 |

### E. 전투 시스템

| 파일 | 참조 |
|------|------|
| `combat-implementation.md` | 전체 전투 구현 명세 |
| Section 2.6 | `check_npc_combat_join()`, `can_fight()` API |
| Section 15 | think Tier 2 전투 통합 |
| Section 16 | NPC 전투 스탯 |
| Section 17 | on_meet 전투 분기 |
