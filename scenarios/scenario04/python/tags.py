# tags.py — S04 태그 기반 선호/비선호 시스템
#
# 캐릭터의 성별/연령/종족 등 특성(self_tags)과 취향(preferences/aversions)을
# 네임스페이스 태그(`{cat}:{value}`)로 표현한다.
#
# 매칭은 태그 집합 연산으로 결정: 혐오 교집합이 비어있지 않으면 "aversion",
# 선호 교집합이 비어있지 않으면 "attraction", 그 외 "neutral".
#
# 이 모듈은 성인 모드와 무관하게 유효한 핵심 모듈이다. 성인 전용 판정(매춘/합의
# 성행위/성적 습격 등)은 이 모듈의 결과를 입력으로 받는 adult/ 하위 모듈에서
# 처리한다.
#
# 설계: docs/advanced-systems.md §3

import morld


# prop 이름
PROP_SELF = "태그:self"
PROP_PREF = "태그:선호"
PROP_AVER = "태그:비선호"


# ========================================
# 직렬화
# ========================================

def _decode(raw) -> set:
    """prop 값 → 태그 set. 공백 구분 문자열, None/빈값은 공집합."""
    if not raw:
        return set()
    return set(raw.split())


def _encode(tags) -> str:
    """태그 iterable → 공백 구분 문자열. 정렬로 결정성 보장."""
    return " ".join(sorted(tags))


# ========================================
# 조회 / 설정
# ========================================

def get_self_tags(unit_id: int) -> set:
    """본인 특성 태그. 예: {'sex:male', 'age:adult', 'species:human'}"""
    return _decode(morld.get_unit_prop(unit_id, PROP_SELF))


def get_preferences(unit_id: int) -> set:
    """선호 태그. 대상이 이 중 하나를 가지면 매력."""
    return _decode(morld.get_unit_prop(unit_id, PROP_PREF))


def get_aversions(unit_id: int) -> set:
    """비선호 태그. 대상이 이 중 하나라도 가지면 즉시 혐오(차단)."""
    return _decode(morld.get_unit_prop(unit_id, PROP_AVER))


def set_self_tags(unit_id: int, tags) -> None:
    morld.set_unit_prop(unit_id, PROP_SELF, _encode(tags))


def set_preferences(unit_id: int, tags) -> None:
    morld.set_unit_prop(unit_id, PROP_PREF, _encode(tags))


def set_aversions(unit_id: int, tags) -> None:
    morld.set_unit_prop(unit_id, PROP_AVER, _encode(tags))


def add_self_tags(unit_id: int, *tags) -> None:
    current = get_self_tags(unit_id)
    current.update(tags)
    set_self_tags(unit_id, current)


def add_preferences(unit_id: int, *tags) -> None:
    current = get_preferences(unit_id)
    current.update(tags)
    set_preferences(unit_id, current)


def add_aversions(unit_id: int, *tags) -> None:
    current = get_aversions(unit_id)
    current.update(tags)
    set_aversions(unit_id, current)


# ========================================
# 매칭
# ========================================

ATTRACTION_AVERSION = "aversion"
ATTRACTION_NEUTRAL = "neutral"
ATTRACTION_ATTRACTION = "attraction"


def get_attraction(observer_id: int, target_id: int) -> str:
    """관찰자가 대상에게 느끼는 관심 종류.

    Returns:
        'aversion'   : 비선호 태그가 하나라도 걸림 → 접근 거부
        'attraction' : 선호 태그 교집합 존재 → 매력 발생
        'neutral'    : 비선호도 선호도 아님

    성인 모드와 무관하게 호출 가능 — 파티 호감도/연애 감정 단계 등
    비성인 맥락에서도 쓰인다.
    """
    target_tags = get_self_tags(target_id)
    if not target_tags:
        # 대상이 태그를 갖지 않으면 판정 불가 → 중립
        return ATTRACTION_NEUTRAL

    aversions = get_aversions(observer_id)
    if target_tags & aversions:
        return ATTRACTION_AVERSION

    preferences = get_preferences(observer_id)
    if target_tags & preferences:
        return ATTRACTION_ATTRACTION

    return ATTRACTION_NEUTRAL


def is_mutual_attraction(a_id: int, b_id: int) -> bool:
    """양방향 매력 성립 여부. 합의 기반 이벤트(§7 1:1)의 전제 조건."""
    return (
        get_attraction(a_id, b_id) == ATTRACTION_ATTRACTION
        and get_attraction(b_id, a_id) == ATTRACTION_ATTRACTION
    )


# ========================================
# 레거시 호환
# ========================================

def init_from_legacy_gender(unit_id: int) -> None:
    """기존 '성별' prop("남"/"여")을 읽어 self_tags에 sex:* 태그를 병합.

    기존 캐릭터 데이터를 태그 시스템으로 점진적 마이그레이션할 때 사용.
    self_tags가 이미 sex:* 를 포함하고 있으면 덮어쓰지 않는다.
    """
    current = get_self_tags(unit_id)
    if any(t.startswith("sex:") for t in current):
        return
    gender = morld.get_unit_prop(unit_id, "성별")
    if gender == "남":
        add_self_tags(unit_id, "sex:male")
    elif gender == "여":
        add_self_tags(unit_id, "sex:female")
