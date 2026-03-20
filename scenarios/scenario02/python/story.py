# story.py — 챕터 1 스토리 로직
"""
숲속 저택 챕터 1 핵심 로직:
- 알파 판정 (신뢰 루트 / 굴복 루트)
- 단둘이 판정 (굴복 루트 전제 조건)
- 발각 판정 (굴복 루트 위험 요소)
- 약점 플래그 관리
- 피로 + 강제 수면 + 퀘스트 시간제한

이주 안전: location ID 하드코딩 없음. prop 기반 동적 탐색.
DES 호환: subscribe_time_elapsed(min_interval=1h)
"""

import morld

# 의존 모듈 (런타임에만 존재, 테스트에서는 mock)
try:
    import needs as _needs
except ImportError:
    _needs = None

# ========================================
# 상수
# ========================================

# 알파 판정 임계치
ALPHA_TRUST_THRESHOLD = 10       # 신뢰 루트: 신뢰 >= 10
ALPHA_AFFECTION_THRESHOLD = 60   # 신뢰 루트: 호감 >= 60
ALPHA_SUBMISSION_THRESHOLD = 70  # 굴복 루트: 복종 >= 70

# 저택 거주 캐릭터 (알파 판정 대상)
MANSION_MEMBERS = ["세라", "밀라", "리나"]

# 이름 → unique_id 매핑 (세력도 prop 변경 시 NPC unit_id 조회용)
_NAME_TO_UNIQUE = {"세라": "sera", "밀라": "mila", "리나": "lina"}


def _resolve_npc_id(member_name):
    """캐릭터 이름 → unit_id 조회 (registry 기반)"""
    unique_id = _NAME_TO_UNIQUE.get(member_name)
    if not unique_id:
        return None
    try:
        from assets.registry import get_instance_id
        return get_instance_id(unique_id)
    except ImportError:
        return None

# 약점 prop 키
WEAKNESS_PREFIX = "약점:"
# 예: 약점:세라:자위발각 = 1, 약점:리나:성인용품 = 1

# 발각 시 밀라가 눈감아주는 호감 임계치
MILA_FORGIVE_AFFECTION = 30


# ========================================
# 알파 판정
# ========================================

def check_alpha_status(player_id=None):
    """
    플레이어가 '알파' 조건을 달성했는지 확인.

    경로 1: 저택 3명 모두 (신뢰 OR 굴복) 충족
    경로 2: 추방 후 귀환하여 저택 점령 (전투/다수결)

    Returns:
        bool: 알파 달성 여부
    """
    if player_id is None:
        player_id = morld.get_player_id()

    # 경로 2: 점령
    if (morld.get_unit_prop(player_id, "스토리:저택점령") or 0) >= 1:
        return True

    # 경로 1: 전원 신뢰/복종
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "주인공") if player_info else "주인공"

    for member in MANSION_MEMBERS:
        if not _check_member_status(player_id, player_name, member):
            return False
    return True


def get_alpha_progress(player_id=None):
    """
    각 캐릭터별 알파 진행 상태 반환 (UI/디버그용).

    Returns:
        dict: {캐릭터명: {"trust_ok": bool, "submission_ok": bool, "details": dict}}
    """
    if player_id is None:
        player_id = morld.get_player_id()

    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "주인공") if player_info else "주인공"

    result = {}
    for member in MANSION_MEMBERS:
        props = _get_relation_props(player_id, player_name, member)
        trust_ok = props["trust"] >= ALPHA_TRUST_THRESHOLD and props["affection"] >= ALPHA_AFFECTION_THRESHOLD
        submission_ok = props["submission"] >= ALPHA_SUBMISSION_THRESHOLD
        result[member] = {
            "trust_ok": trust_ok,
            "submission_ok": submission_ok,
            "done": trust_ok or submission_ok,
            "details": props,
        }
    return result


def _check_member_status(player_id, player_name, member_name):
    """단일 캐릭터에 대한 알파 조건 충족 여부"""
    props = _get_relation_props(player_id, player_name, member_name)
    trust_ok = props["trust"] >= ALPHA_TRUST_THRESHOLD and props["affection"] >= ALPHA_AFFECTION_THRESHOLD
    submission_ok = props["submission"] >= ALPHA_SUBMISSION_THRESHOLD
    return trust_ok or submission_ok


def _get_relation_props(player_id, player_name, member_name):
    """캐릭터의 관계 props 조회 (NPC의 prop에서 플레이어 관계 읽기)"""
    # 관계 prop은 NPC에 저장됨: 관계:{플레이어이름}:호감 등
    # 여기서는 player의 prop에 저장된 값을 읽음 (퀘스트 보상 등)
    # 양쪽 모두 확인하여 더 높은 값 사용
    trust = morld.get_unit_prop(player_id, f"관계:{member_name}:신뢰") or 0
    affection = morld.get_unit_prop(player_id, f"관계:{member_name}:호감") or 0
    submission = morld.get_unit_prop(player_id, f"관계:{member_name}:복종") or 0
    rebellion = morld.get_unit_prop(player_id, f"관계:{member_name}:반발") or 0
    return {
        "trust": trust,
        "affection": affection,
        "submission": submission,
        "rebellion": rebellion,
    }


# ========================================
# 단둘이 판정
# ========================================

def is_alone_with(player_id, target_id):
    """
    플레이어와 대상 NPC가 단둘이 있는지 확인.
    같은 location에 player + target만 있으면 True.

    오브젝트(가구 등)는 제외하고 캐릭터만 카운트.

    Args:
        player_id: 플레이어 unit_id
        target_id: 대상 NPC unit_id

    Returns:
        bool: 단둘이 여부
    """
    player_loc = morld.get_unit_location(player_id)
    target_loc = morld.get_unit_location(target_id)

    if not player_loc or not target_loc:
        return False

    # 같은 위치인지 확인
    if player_loc[0] != target_loc[0] or player_loc[1] != target_loc[1]:
        return False

    # 해당 위치의 모든 캐릭터 조회
    units = morld.get_units_at_location(player_loc[0], player_loc[1])
    if not units:
        return False

    # 캐릭터만 필터 (오브젝트/크리쳐 제외)
    characters = []
    for uid in units:
        info = morld.get_unit_info(uid)
        if info and not info.get("is_object") and not info.get("is_creature"):
            characters.append(uid)

    # 정확히 2명 (player + target)
    return len(characters) == 2 and player_id in characters and target_id in characters


def get_other_characters_at(player_id, location=None):
    """
    플레이어가 있는 위치의 다른 캐릭터 목록 반환.
    발각 위험도 표시 등에 사용.

    Returns:
        list[int]: 다른 캐릭터 unit_id 목록 (플레이어 제외)
    """
    if location is None:
        location = morld.get_unit_location(player_id)
    if not location:
        return []

    units = morld.get_units_at_location(location[0], location[1])
    if not units:
        return []

    others = []
    for uid in units:
        if uid == player_id:
            continue
        info = morld.get_unit_info(uid)
        if info and not info.get("is_object") and not info.get("is_creature"):
            others.append(uid)
    return others


# ========================================
# 발각 판정
# ========================================

def check_discovery(player_id, victim_id, witness_id):
    """
    강제 행위 중 목격자가 있을 때 결과 판정.

    게임오버 없음 — 발각 시 추방(expulsion) 또는 용서(forgive).

    Args:
        player_id: 플레이어
        victim_id: 피해자 NPC
        witness_id: 목격자 NPC

    Returns:
        str: "forgive" (밀라 눈감아줌), "expulsion" (추방)
    """
    witness_info = morld.get_unit_info(witness_id)
    if not witness_info:
        return "expulsion"

    witness_name = witness_info.get("name", "")

    # 밀라 특수: 호감이 일정 이상이면 눈감아줌
    if witness_name == "밀라":
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"
        affection = morld.get_unit_prop(witness_id, f"관계:{player_name}:호감") or 0
        if affection >= MILA_FORGIVE_AFFECTION:
            return "forgive"

    return "expulsion"


# ========================================
# 추방 시스템
# ========================================

# 추방 판정 임계치
EXPULSION_TRUST_THRESHOLD = -3  # 세라 신뢰가 이 이하이면 추방

# 추방 상태 prop
PROP_EXPELLED = "스토리:추방됨"
# 저택 점령 prop (추방 후 귀환 시 전투/다수결로 점령)
PROP_MANSION_CONQUERED = "스토리:저택점령"


def check_expulsion_trigger(player_id):
    """
    추방 조건 확인 (매시간 체크 — _on_time_elapsed에서 호출).

    조건: 세라의 신뢰가 -3 이하.
    이미 추방된 상태이거나, 알파 달성 후에는 무시.

    Returns:
        bool: 추방이 발동되어야 하면 True
    """
    # 이미 추방됨 or 알파 달성 → 무시
    if is_expelled(player_id):
        return False
    if check_alpha_status(player_id):
        return False

    trust = morld.get_unit_prop(player_id, "관계:세라:신뢰") or 0
    return trust <= EXPULSION_TRUST_THRESHOLD


def apply_expulsion(player_id):
    """
    추방 처리 — prop 변경만. 이벤트/텔레포트는 호출자가 처리.

    효과:
    - 추방 플래그 설정
    - 저택 멤버 전원 호감 하락 + 반발 상승
    - 저택 멤버 세력도 → 적대 (-1)
    """
    morld.set_unit_prop(player_id, PROP_EXPELLED, 1)

    # NPC별 관계 악화 + 세력 적대화
    for member in MANSION_MEMBERS:
        # 호감 하락
        current_aff = morld.get_unit_prop(player_id, f"관계:{member}:호감") or 0
        morld.set_unit_prop(player_id, f"관계:{member}:호감", max(0, current_aff - 15))
        # 반발 상승
        current_reb = morld.get_unit_prop(player_id, f"관계:{member}:반발") or 0
        morld.set_unit_prop(player_id, f"관계:{member}:반발", min(100, current_reb + 20))
        # 세력 적대화: NPC의 관계:방문자:세력도 → -1
        npc_id = _resolve_npc_id(member)
        if npc_id:
            morld.set_unit_prop(npc_id, "관계:방문자:세력도", -1)


def is_expelled(player_id):
    """추방 상태인지 확인"""
    return (morld.get_unit_prop(player_id, PROP_EXPELLED) or 0) >= 1


def apply_mansion_conquest(player_id):
    """
    저택 점령 — 추방 후 귀환하여 점령 성공 시.
    기존 시스템(전투 승리 / 다수결)에 의해 호출됨.

    효과:
    - 점령 플래그 설정
    - 추방 플래그 해제
    - 저택 멤버 세력도 → 중립 (0) 복원
    """
    morld.set_unit_prop(player_id, PROP_MANSION_CONQUERED, 1)
    morld.set_unit_prop(player_id, PROP_EXPELLED, 0)

    # 세력 적대 해제
    for member in MANSION_MEMBERS:
        npc_id = _resolve_npc_id(member)
        if npc_id:
            morld.set_unit_prop(npc_id, "관계:방문자:세력도", 0)


# ========================================
# 약점 플래그
# ========================================

def set_weakness(player_id, target_name, weakness_key):
    """약점 플래그 설정 (플레이어 prop에 저장)"""
    prop = f"{WEAKNESS_PREFIX}{target_name}:{weakness_key}"
    morld.set_unit_prop(player_id, prop, 1)


def has_weakness(player_id, target_name, weakness_key):
    """약점 플래그 확인"""
    prop = f"{WEAKNESS_PREFIX}{target_name}:{weakness_key}"
    return (morld.get_unit_prop(player_id, prop) or 0) >= 1


def get_all_weaknesses(player_id, target_name):
    """특정 캐릭터에 대한 모든 약점 목록 반환"""
    props = morld.get_unit_props(player_id) or {}
    prefix = f"{WEAKNESS_PREFIX}{target_name}:"
    return [k[len(prefix):] for k, v in props.items() if k.startswith(prefix) and v >= 1]


# ========================================
# 다수결 굴복
# ========================================

def check_majority_against(player_id, target_name):
    """
    다수결로 대상을 굴복시킬 수 있는지 확인.
    저택 3명 중 대상을 제외한 2명이 플레이어 편이면 가능.

    "플레이어 편" 조건: 호감 >= 50 OR 복종 >= 50

    Args:
        target_name: 굴복 대상 캐릭터 이름

    Returns:
        bool: 다수결 가능 여부
    """
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "주인공") if player_info else "주인공"

    allies = 0
    for member in MANSION_MEMBERS:
        if member == target_name:
            continue

        affection = morld.get_unit_prop(player_id, f"관계:{member}:호감") or 0
        submission = morld.get_unit_prop(player_id, f"관계:{member}:복종") or 0

        if affection >= 50 or submission >= 50:
            allies += 1

    # 대상 외 2명 모두 플레이어 편
    return allies >= 2


# ========================================
# 플레이어 피로 + 강제 수면
# ========================================

PLAYER_FORCED_SLEEP_THRESHOLD = 95   # 이 이상이면 강제 수면
PLAYER_SLEEP_WARNING_THRESHOLD = 80  # 경고 표시 임계치

# 행동별 피로 증가량 (기본 시간당 +4는 needs.py에서 처리)
ACTION_FATIGUE = {
    "달리기": 4,     # 시간당 추가 +4 (needs.py에서 이미 2배 처리)
    "전투": 10,      # 전투 1회당
    "채집": 3,       # 채집 1회당
    "벌목": 5,       # 벌목 1회당
    "청소": 2,       # 청소 1회당
    "낚시": 1,       # 낚시 1회당 (앉아서 하므로 낮음)
}


def check_player_fatigue(player_id=None):
    """
    플레이어 피로 상태 확인.

    Returns:
        str: "normal" / "warning" / "forced_sleep"
    """
    if player_id is None:
        player_id = morld.get_player_id()

    fatigue = morld.get_unit_prop(player_id, "욕구:피로") or 0

    if fatigue >= PLAYER_FORCED_SLEEP_THRESHOLD:
        return "forced_sleep"
    elif fatigue >= PLAYER_SLEEP_WARNING_THRESHOLD:
        return "warning"
    return "normal"


def add_action_fatigue(player_id, action_key):
    """행동에 따른 피로 증가"""
    amount = ACTION_FATIGUE.get(action_key, 0)
    if amount > 0:
        current = morld.get_unit_prop(player_id, "욕구:피로") or 0
        new_val = min(100, current + amount)
        morld.set_unit_prop(player_id, "욕구:피로", new_val)
    return amount


# ========================================
# 수면 중 강제 기상
# ========================================

# 침대 주인의 호감이 이 미만이면 쫓아냄
BED_KICK_AFFECTION_THRESHOLD = 30


def should_kick_from_bed(player_id, bed_owner_name):
    """
    플레이어가 남의 침대에서 자고 있을 때 쫓아낼지 판정.

    조건: 침대 주인의 호감 < 30
    (자기 침대이거나 주인 없는 침대면 False)

    Args:
        player_id: 플레이어 ID
        bed_owner_name: 침대 주인 이름 (None이면 무주)

    Returns:
        bool: 쫓아내야 하면 True
    """
    if not bed_owner_name:
        return False

    # 플레이어 자신의 침대면 OK
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "") if player_info else ""
    if bed_owner_name == player_name:
        return False

    affection = morld.get_unit_prop(player_id, f"관계:{bed_owner_name}:호감") or 0
    return affection < BED_KICK_AFFECTION_THRESHOLD


# ========================================
# 퀘스트 시간제한 + 자동 실패
# ========================================

DAILY_QUEST_DEADLINE_HOURS = 18  # 18시까지 (오후 6시)


def check_quest_timeout(player_id, quest_id, current_hour):
    """
    퀘스트 시간제한 초과 여부 확인.

    일일 퀘스트: 당일 18시까지 미완료 시 실패.

    Args:
        player_id: 플레이어 ID
        quest_id: 퀘스트 ID
        current_hour: 현재 시간 (0~23)

    Returns:
        bool: 시간 초과 여부
    """
    # daily_ 로 시작하는 퀘스트만 시간제한 적용
    if not quest_id.startswith("daily_"):
        return False

    # IN_PROGRESS 상태인 경우만 (미수락이면 타임아웃 아님)
    status = morld.get_unit_prop(player_id, f"퀘스트:{quest_id}:상태") or 0
    if status != 2:  # QuestStatus.IN_PROGRESS = 2
        return False

    return current_hour >= DAILY_QUEST_DEADLINE_HOURS


def apply_quest_failure(player_id, quest_id):
    """
    퀘스트 실패 처리: 신뢰 -1, 퀘스트 상태 리셋.

    Args:
        player_id: 플레이어 ID
        quest_id: 퀘스트 ID

    Returns:
        dict: 실패 효과 요약
    """
    effects = {"quest_id": quest_id}

    # 신뢰 하락 (세라 기준) — 음수 허용 (추방 트리거에 사용)
    trust = morld.get_unit_prop(player_id, "관계:세라:신뢰") or 0
    new_trust = trust - 1
    morld.set_unit_prop(player_id, "관계:세라:신뢰", new_trust)
    effects["trust_loss"] = -1

    # 퀘스트 상태 → LOCKED (0) — 다음 날 리셋 대기
    morld.set_unit_prop(player_id, f"퀘스트:{quest_id}:상태", 0)
    effects["status"] = "reset"

    return effects


# ========================================
# 유키·엘라 합류 판정
# ========================================

# 합류 방법
RECRUIT_PERSUADE = "persuade"       # 설득 (호감 기반)
RECRUIT_KIDNAP = "kidnap"           # 납치 (강제)
RECRUIT_BLACKMAIL = "blackmail"     # 협박 (유키 인질로 엘라 협박)

# 설득 임계치
YUKI_PERSUADE_AFFECTION = 50   # 유키 설득에 필요한 호감
ELLA_PERSUADE_AFFECTION = 60   # 엘라 설득에 필요한 호감 (더 높음)

# 합류 후 반발
KIDNAP_REBELLION_PENALTY = 30      # 납치 시 반발 증가
BLACKMAIL_REBELLION_PENALTY = 40   # 협박 시 반발 증가


def can_recruit(player_id, target_name, method):
    """
    합류 가능 조건 확인.

    Args:
        player_id: 플레이어 ID
        target_name: "유키" or "엘라"
        method: RECRUIT_PERSUADE / RECRUIT_KIDNAP / RECRUIT_BLACKMAIL

    Returns:
        bool: 합류 가능 여부
    """
    if method == RECRUIT_PERSUADE:
        threshold = YUKI_PERSUADE_AFFECTION if target_name == "유키" else ELLA_PERSUADE_AFFECTION
        affection = morld.get_unit_prop(player_id, f"관계:{target_name}:호감") or 0
        return affection >= threshold

    elif method == RECRUIT_KIDNAP:
        # 납치는 언제든 가능 (조건 없음, 결과만 나쁨)
        return True

    elif method == RECRUIT_BLACKMAIL:
        # 엘라 협박: 유키가 이미 저택에 합류해 있어야 함
        if target_name == "엘라":
            yuki_joined = (morld.get_unit_prop(player_id, "합류:유키") or 0) >= 1
            return yuki_joined
        return False

    return False


def apply_recruit_effects(player_id, target_name, method):
    """
    합류 시 효과 적용 (prop 변경).

    Args:
        player_id: 플레이어 ID
        target_name: "유키" or "엘라"
        method: 합류 방법

    Returns:
        dict: 적용된 효과 요약
    """
    effects = {"method": method, "target": target_name}

    # 합류 플래그 설정
    morld.set_unit_prop(player_id, f"합류:{target_name}", 1)

    if method == RECRUIT_PERSUADE:
        # 설득: 호감 보너스
        effects["affection_bonus"] = 5
        morld.modify_prop(player_id, f"관계:{target_name}:호감", 5)

    elif method == RECRUIT_KIDNAP:
        # 납치: 반발 대폭 증가
        effects["rebellion_penalty"] = KIDNAP_REBELLION_PENALTY
        morld.modify_prop(player_id, f"관계:{target_name}:반발", KIDNAP_REBELLION_PENALTY)

    elif method == RECRUIT_BLACKMAIL:
        # 협박: 반발 더 크게 증가
        effects["rebellion_penalty"] = BLACKMAIL_REBELLION_PENALTY
        morld.modify_prop(player_id, f"관계:{target_name}:반발", BLACKMAIL_REBELLION_PENALTY)

    return effects


def check_all_joined(player_id):
    """5명 전원 합류 확인 (저택 3명 + 유키 + 엘라)"""
    for name in ["유키", "엘라"]:
        if (morld.get_unit_prop(player_id, f"합류:{name}") or 0) < 1:
            return False
    return True


# ========================================
# 페이 합류 판정
# ========================================

FAYE_TRADE_TRUST_AFFECTION = 60   # 거래 신뢰 합류 조건: 호감 >= 60
FAYE_RESCUE_FLAG = "이벤트:페이구출"  # 위기 구출 이벤트 완료 플래그

RECRUIT_FAYE_TRADE = "trade_trust"    # 거래 신뢰
RECRUIT_FAYE_RESCUE = "rescue"        # 위기 구출
RECRUIT_FAYE_OFFER = "offer"          # 알파 후 전속 상인 제안
RECRUIT_FAYE_BLACKMAIL = "blackmail"  # 성인용품 판매 비밀 협박
RECRUIT_FAYE_DEBT = "debt"            # 빚 관계


def can_recruit_faye(player_id, method):
    """
    페이 합류 조건 확인.

    Args:
        method: 합류 방법

    Returns:
        bool: 합류 가능 여부
    """
    if method == RECRUIT_FAYE_TRADE:
        affection = morld.get_unit_prop(player_id, "관계:페이:호감") or 0
        return affection >= FAYE_TRADE_TRUST_AFFECTION

    elif method == RECRUIT_FAYE_RESCUE:
        return (morld.get_unit_prop(player_id, FAYE_RESCUE_FLAG) or 0) >= 1

    elif method == RECRUIT_FAYE_OFFER:
        return check_alpha_status(player_id)

    elif method == RECRUIT_FAYE_BLACKMAIL:
        return has_weakness(player_id, "페이", "성인용품판매")

    elif method == RECRUIT_FAYE_DEBT:
        debt = morld.get_unit_prop(player_id, "관계:페이:빚") or 0
        return debt > 0

    return False


# ========================================
# 매시간 자동 처리 (subscribe_time_elapsed)
# ========================================

# 세라 일일 퀘스트 ID 목록 (SeraAgent.DAILY_QUEST_IDS와 동기화)
_DAILY_QUEST_IDS = [
    "daily_gather_herb", "daily_gather_berry", "daily_firewood",
    "daily_fishing", "daily_clean", "daily_water_garden", "daily_deliver_food",
]


def _on_time_elapsed(elapsed_millis):
    """
    매시간 호출 — 퀘스트 시간제한 + 알파 체크.

    subscribe_time_elapsed로 등록되어 시간 흐름에 자연스럽게 녹아듦.
    플레이어가 수면 중이든 활동 중이든 동일하게 동작.
    """
    player_id = morld.get_player_id()
    if not player_id:
        return

    time_info = morld.get_time_info()
    if not time_info:
        return

    current_hour = time_info.get("hour", 0)

    # ── 일일 퀘스트 시간제한 자동 실패 ──
    for quest_id in _DAILY_QUEST_IDS:
        if check_quest_timeout(player_id, quest_id, current_hour):
            effects = apply_quest_failure(player_id, quest_id)
            morld.add_action_log(f"[일일 심부름] '{quest_id}' 시간 초과 — 실패 처리됨 (신뢰 {effects['trust_loss']})")

    # ── 추방 체크 (신뢰 바닥 → 추방) ──
    if check_expulsion_trigger(player_id):
        apply_expulsion(player_id)
        morld.add_action_log("[스토리] 저택에서 추방당했다.")


# ── 시간 구독 등록 (모듈 로드 시) ──
try:
    from events import subscribe_time_elapsed
    subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)  # 1시간
except ImportError:
    pass  # 테스트 환경에서는 events 모듈 없음
