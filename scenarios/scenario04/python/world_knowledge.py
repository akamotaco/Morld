# world_knowledge.py - S04 세계의 지식 + 마을 혼란도
#
# 파티원이 던전의 진실에 가까워질수록 이탈 압박.
# "아는 자"가 마을에 돌아가면 혼란도 상승.
#
# 세계의 지식 (개인): NPC가 진실에 가까워지는 수치
#   무지(0~20) → 의심(21~50) → 확신(51~80) → 한계(81+)
#
# 마을 혼란도 (전역): 마을 전체의 동요 수준
#   낮음(0~20) → 소문(21~40) → 동요(41~60) → 위기(61~80) → 붕괴(81+)

import morld

# === 세계의 지식 ===

KNOWLEDGE_SUSPICION = 21   # 의심
KNOWLEDGE_CONVICTION = 51  # 확신
KNOWLEDGE_LIMIT = 81       # 한계 → 이탈 압박

# 지식 축적 요인 (기본값)
KNOWLEDGE_GAINS = {
    "환경단서":      3,   # 벽화, 일지 발견
    "재편성경험":    10,  # 재편성을 겪음
    "꺾기이벤트":    15,  # 꺾기 사실 인지
    "깊은층도달":    2,   # 층당
    "체류자대화":    5,   # 체류자에게 정보 구매
    "관리자조우":    20,  # 관리자 직접 조우
}

# B 고유 이벤트 (급진적)
B_KNOWLEDGE_GAINS = {
    "재편성목격":    20,
    "플레이어힘목격": 30,
    "D조우목격":     20,
}


def get_knowledge(unit_id: int) -> int:
    val = morld.get_unit_prop(unit_id, "세계의지식")
    return int(val) if val is not None else 0


def add_knowledge(unit_id: int, reason: str, amount: int = None):
    """세계의 지식 축적"""
    if amount is None:
        amount = KNOWLEDGE_GAINS.get(reason, 0)

    current = get_knowledge(unit_id)
    new_val = min(100, current + amount)
    morld.set_unit_prop(unit_id, "세계의지식", new_val)

    if new_val != current:
        old_state = _knowledge_state(current)
        new_state = _knowledge_state(new_val)
        if old_state != new_state:
            name = morld.get_unit_info(unit_id).get("name", "???") if morld.get_unit_info(unit_id) else "???"
            print(f"[knowledge] {name}: {old_state} → {new_state} ({new_val})")


def add_knowledge_b_event(unit_id: int, event: str):
    """B 고유 이벤트에 의한 급진적 지식 축적"""
    amount = B_KNOWLEDGE_GAINS.get(event, 0)
    if amount:
        add_knowledge(unit_id, event, amount)


def get_knowledge_state(unit_id: int) -> str:
    return _knowledge_state(get_knowledge(unit_id))


def _knowledge_state(value: int) -> str:
    if value >= KNOWLEDGE_LIMIT:
        return "한계"
    elif value >= KNOWLEDGE_CONVICTION:
        return "확신"
    elif value >= KNOWLEDGE_SUSPICION:
        return "의심"
    else:
        return "무지"


def is_at_limit(unit_id: int) -> bool:
    return get_knowledge(unit_id) >= KNOWLEDGE_LIMIT


# === 파티 전원에게 지식 축적 ===

def add_party_knowledge(reason: str, amount: int = None):
    """파티원 전원에게 세계의 지식 축적"""
    import party
    for mid in party.get_members():
        add_knowledge(mid, reason, amount)


# === 마을 혼란도 ===

_village_chaos = 0

CHAOS_RUMOR = 21      # 소문
CHAOS_UNREST = 41     # 동요
CHAOS_CRISIS = 61     # 위기
CHAOS_COLLAPSE = 81   # 붕괴


def reset():
    global _village_chaos
    _village_chaos = 0


def get_chaos() -> int:
    return _village_chaos


def add_chaos(amount: int, reason: str = ""):
    """혼란도 증가"""
    global _village_chaos
    old = _village_chaos
    _village_chaos = min(100, max(0, _village_chaos + amount))

    old_state = _chaos_state(old)
    new_state = _chaos_state(_village_chaos)
    if old_state != new_state:
        print(f"[chaos] Village chaos: {old_state} → {new_state} "
              f"({_village_chaos}) reason={reason}")


def get_chaos_state() -> str:
    return _chaos_state(_village_chaos)


def _chaos_state(value: int) -> str:
    if value >= CHAOS_COLLAPSE:
        return "붕괴"
    elif value >= CHAOS_CRISIS:
        return "위기"
    elif value >= CHAOS_UNREST:
        return "동요"
    elif value >= CHAOS_RUMOR:
        return "소문"
    else:
        return "낮음"


# === "아는 자" 이탈 → 혼란도 ===

# 이탈한 아는 자 수 추적
_known_departed = 0

CHAOS_PER_DEPARTED = {
    1: 5,    # 1명: 무시됨에 가까움
    2: 10,   # 2명: 소문 시작
    3: 15,   # 3명: 본격 확산
    4: 20,   # 4명: 급등
    5: 25,   # 5명+
}


def on_knower_departed(unit_id: int):
    """'아는 자'가 마을에 돌아감 → 혼란도 상승"""
    global _known_departed
    _known_departed += 1

    knowledge = get_knowledge(unit_id)
    name = morld.get_unit_info(unit_id).get("name", "???") if morld.get_unit_info(unit_id) else "???"

    # 지식 수준에 따라 혼란도 가중
    base_chaos = CHAOS_PER_DEPARTED.get(
        min(_known_departed, 5),
        25
    )

    if knowledge >= KNOWLEDGE_CONVICTION:
        base_chaos = int(base_chaos * 1.5)  # 확신자는 더 큰 영향

    add_chaos(base_chaos, reason=f"{name} departed (knowledge={knowledge})")
    print(f"[chaos] Knower departed: {name} (total departed: {_known_departed})")


# B 전용: 군대 소환
def on_b_calls_army():
    """B가 군대를 소환 → 혼란도 급등"""
    add_chaos(40, reason="B called the army")
    print("[chaos] B called the army! Crisis imminent!")
