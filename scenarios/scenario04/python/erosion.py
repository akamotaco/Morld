# erosion.py - S04 침식 시스템
#
# 캐릭터의 정신적 오염. location 오염도(pollution)에 비례하��� 축적.
# 침식 게이지: 0~200
#   0~50: 정상
#   50~100: 경미한 기벽 발현 가능
#   100: 판정 (75% 고질 / 25% 깨우침) → 게이지 50으로 감소
#   100~200: 고질/깨우침 보유 상태에서 추가 축적 (2차 판정 없음)
#   200: 소멸 (극소 확률로 경계 생환)
#
# 침식 저항 = 정신 스탯 + 내오성 장비
# 특수 존재 (플레이어/D)는 내성 높음

import morld
import random
from events import subscribe_time_elapsed

# === 상수 ===
EROSION_MAX = 200
EROSION_CHECK_THRESHOLD = 100   # 판정 발동 침식
EROSION_POST_CHECK = 50         # 판정 후 게이지 (밸런스 조정 가능)

AFFLICTION_CHANCE = 0.75        # 고질 확률
AWAKENING_CHANCE = 0.25         # 깨우침 확률
PERMANENT_AWAKENING_CHANCE = 0.10  # 깨우침 중 영구 확률

SURVIVAL_CHANCE_BASE = 0.05     # 200 도달 시 경계 생환 기본 확률
SURVIVAL_IMMUNITY_HOURS = 24    # 경계 생환 후 침식 면역 시간

# 침식 축적 속도 (location 오염도 1당 시간당)
EROSION_PER_POLLUTION_PER_HOUR = 0.5

# 특수 존재 내성 배율
SPECIAL_RESISTANCE_MULT = 0.5   # 50%만 축적

# === 상태 ===
_registered = set()  # 등록된 캐릭터
_accumulated_millis = 0
_immunity = {}  # unit_id -> remaining_hours (경계 생환 면역)


def reset():
    global _accumulated_millis
    _registered.clear()
    _accumulated_millis = 0
    _immunity.clear()


def register(unit_id: int):
    """침식 시스템에 캐릭터 등록"""
    _registered.add(unit_id)
    if morld.get_unit_prop(unit_id, "침식") is None:
        morld.set_unit_prop(unit_id, "침식", 0)


def get_erosion(unit_id: int) -> int:
    val = morld.get_unit_prop(unit_id, "침식")
    return int(val) if val is not None else 0


def set_erosion(unit_id: int, value: int):
    morld.set_unit_prop(unit_id, "침식", max(0, min(EROSION_MAX, value)))


def add_erosion(unit_id: int, amount: float):
    """
    침식 추가. 저항/면역 적용.

    Args:
        amount: 기본 침식량 (저항 적용 전)
    """
    if unit_id in _immunity and _immunity[unit_id] > 0:
        return  # 면역 중

    # 저항 계산: 정신 스탯 기반
    mnd = morld.get_unit_prop(unit_id, "스탯:정신") or 10
    resistance = mnd * 0.02  # 정신 10 = 20% 감소
    amount *= max(0.1, 1.0 - resistance)

    # 침식 저항 배수 (1.0=보통, 0.5=50%만 축적 등) — 원자 능력 prop
    resist_mult = morld.get_unit_prop(unit_id, "침식:저항배수")
    if resist_mult is not None:
        amount *= float(resist_mult)

    # 사기 보정
    import morale
    m = morale.get_morale(unit_id)
    if m < 40:
        amount *= 1.3  # 낮은 사기 → 침식 가속
    elif m >= 70:
        amount *= 0.8  # 높은 사기 → 침식 감속

    current = get_erosion(unit_id)
    new_val = current + amount
    set_erosion(unit_id, int(new_val))

    # 임계 체크
    _check_thresholds(unit_id, current, int(new_val))


def reduce_erosion(unit_id: int, amount: int):
    """침식 감소 (휴식/정화소)"""
    current = get_erosion(unit_id)
    set_erosion(unit_id, max(0, current - amount))


# === 임계 판정 ===

def _check_thresholds(unit_id: int, old: int, new: int):
    """침식 임계치 도달 시 처리"""
    import quirk
    import morale

    # 50 넘을 때 기벽 체크
    if old < 50 <= new or (new >= 50 and random.random() < 0.05):
        result = quirk.check_erosion_quirk(unit_id, new)
        if result:
            morale.on_affliction(unit_id)
        if old < 50 <= new:
            # 첫 50 임계 통과 시 1회성 발화
            _voice_corrosion(unit_id, "corrosion_rise")

    # 100 도달: 판정 (1회만 — 이미 판정받았으면 스킵)
    if old < EROSION_CHECK_THRESHOLD <= new:
        _voice_corrosion(unit_id, "corrosion_critical")
        _voice_ally_concern(unit_id)
        _resolve_check(unit_id)

    # 200 도달: 소멸
    if new >= EROSION_MAX:
        _handle_erosion_death(unit_id)


def _voice_corrosion(unit_id: int, intent: str):
    """침식 임계 통과 시 NPC 대사 출력 (Phase D-1).

    hybrid dungeon.yaml 의 corrosion_rise / corrosion_critical 인텐트 사용.
    플레이어/이름 없는 유닛/빈 라인은 silent. 예외 발생 시도 silent
    (침식 임계 처리 흐름이 발화 실패로 끊기면 안 됨).
    """
    try:
        import npc_dialogue
        name = morld.get_unit_name(unit_id)
        if not name:
            return
        line = npc_dialogue.get_line(unit_id, intent, name=name)
        if line and line.strip(". ") not in ("", "..", "...", "...."):
            morld.add_action_log(f"[{name}] \"{line}\"")
    except Exception as e:
        print(f"[dialogue] WARN _voice_corrosion failed: {e}")


def _voice_ally_concern(victim_id: int):
    """victim의 침식 critical 시 같은 파티 동료가 우려 발화 (Phase D-3, 2026-04-26).

    hybrid dungeon.yaml 의 ally_corrosion_concern 인텐트 사용.
    {victim} 플레이스홀더로 victim 이름 주입.
    동료 후보: victim과 같은 파티 멤버 중 victim/플레이어/이름 없는 유닛 제외, 1명 무작위.
    파티 미가입/후보 없음/예외 시 silent.
    """
    try:
        import npc_dialogue
        from engine import party_group
        victim_name = morld.get_unit_name(victim_id)
        if not victim_name:
            return
        party = party_group.get_party_of(victim_id)
        if party is None:
            return
        player_id = morld.get_player_id()
        candidates = [
            m for m in party.members
            if m != victim_id
            and m != player_id
            and morld.get_unit_name(m)
        ]
        if not candidates:
            return
        voicer_id = random.choice(candidates)
        voicer_name = morld.get_unit_name(voicer_id)
        line = npc_dialogue.get_line(voicer_id, "ally_corrosion_concern",
                                       name=voicer_name, victim=victim_name)
        if line and line.strip(". ") not in ("", "..", "...", "...."):
            morld.add_action_log(f"[{voicer_name}] \"{line}\"")
    except Exception as e:
        print(f"[dialogue] WARN _voice_ally_concern failed: {e}")


def _resolve_check(unit_id: int):
    """침식 100 판정: 고질 or 깨우침"""
    import quirk
    import morale

    roll = random.random()

    if roll < AWAKENING_CHANCE:
        # 깨우침
        _apply_awakening(unit_id)
        morale.on_awakening(unit_id)
    else:
        # 고질
        _apply_affliction(unit_id)
        morale.on_affliction(unit_id)

    # 게이지 감소
    set_erosion(unit_id, EROSION_POST_CHECK)
    print(f"[erosion] Resolve check for {unit_id}: erosion reset to {EROSION_POST_CHECK}")


def _apply_affliction(unit_id: int):
    """고질 적용"""
    import quirk

    severe_quirks = [name for name, data in quirk.QUIRKS.items()
                     if data["grade"] in ("severe", "sexual_severe")]
    existing = {q["name"] for q in quirk.get_quirks(unit_id)}
    candidates = [q for q in severe_quirks if q not in existing]

    if candidates:
        chosen = random.choice(candidates)
        quirk.add_quirk(unit_id, chosen)
        print(f"[erosion] Affliction: {unit_id} gained '{chosen}'")


def _apply_awakening(unit_id: int):
    """깨우침 적용"""
    import quirk

    positive_quirks = [name for name, data in quirk.QUIRKS.items()
                       if data["grade"] == "positive"]
    existing = {q["name"] for q in quirk.get_quirks(unit_id)}
    candidates = [q for q in positive_quirks if q not in existing]

    if candidates:
        chosen = random.choice(candidates)
        quirk.add_quirk(unit_id, chosen)

        # 영구 깨우침?
        if random.random() < PERMANENT_AWAKENING_CHANCE:
            morld.set_unit_prop(unit_id, "깨우침:영구", 1)
            print(f"[erosion] PERMANENT Awakening: {unit_id} gained '{chosen}'!")
        else:
            morld.set_unit_prop(unit_id, "깨우침:임시", 1)
            print(f"[erosion] Awakening: {unit_id} gained '{chosen}' (temporary)")


def _handle_erosion_death(unit_id: int):
    """침식 200: 소멸 판정"""
    # 경계 생환 확률
    mnd = morld.get_unit_prop(unit_id, "스탯:정신") or 10
    survival_chance = SURVIVAL_CHANCE_BASE + (mnd * 0.005)

    # 깨우침 보유 시 확률 증가
    if morld.get_unit_prop(unit_id, "깨우침:영구"):
        survival_chance += 0.10

    if random.random() < survival_chance:
        # 경계 생환!
        set_erosion(unit_id, 50)  # 대폭 감소
        _immunity[unit_id] = SURVIVAL_IMMUNITY_HOURS
        print(f"[erosion] SURVIVAL! {unit_id} returned from the brink!")
    else:
        # 소멸
        morld.set_unit_prop(unit_id, "상태:소멸", 1)

        # 파티에서 제거
        import party
        if party.is_member(unit_id):
            party.remove_member(unit_id, reason="소멸")

        print(f"[erosion] DEATH by erosion: {unit_id} dissolved.")


# === 시간 경과: location 오염도 기반 침식 축적 ===

def _on_time_elapsed(millis: int):
    global _accumulated_millis
    _accumulated_millis += millis

    hours = _accumulated_millis // 3600000
    if hours < 1:
        return
    _accumulated_millis %= 3600000

    import pollution

    for unit_id in list(_registered):
        # 면역 시간 감소
        if unit_id in _immunity:
            _immunity[unit_id] -= hours
            if _immunity[unit_id] <= 0:
                del _immunity[unit_id]

        # 현재 위치의 오염도
        loc = morld.get_unit_location(unit_id)
        if not loc:
            continue
        region_id, loc_id = loc
        poll = pollution.get_pollution(region_id, loc_id)

        if poll > 0:
            erosion_amount = poll * EROSION_PER_POLLUTION_PER_HOUR * hours
            add_erosion(unit_id, erosion_amount)


subscribe_time_elapsed(_on_time_elapsed, min_interval=3600000)
