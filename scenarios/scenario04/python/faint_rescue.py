# faint_rescue.py — 플레이어 실신 후 구출/탈출/사망 사이클
#
# 1시간 단위 DES 점프로 판정 반복:
#   1. 파티 구출: 같은 location 실신 아닌 파티원 (동정심+신뢰도)
#   2. 지나가는 NPC: 평판 + 시간경과 - 층수
#   3. 자력 탈출: 기본 - 층수 (저층 전용)
#   4. 실패 시 침식 축적 → 200 도달 시 사망(재편성)
#
# 설계 문서: memory/s04-faint-rescue-design.md

import random
import morld
import ui

# === 튜닝 상수 (밸런싱 TODO) ===

MAX_CYCLES = 40                  # 안전 limit (시간 진행 누적 상한)
TICK_MILLIS = 3_600_000          # 1시간
RECOVERY_HP = 10                 # 모든 탈출 공통 회복 HP (max(1, 10))

# 자력 탈출
_SELF_BASE = 5
_SELF_FLOOR_PENALTY = 2

# 지나가는 NPC
_NPC_REP_WEIGHT = 0.15           # (rep + 100) × 0.15
_NPC_TIME_BONUS_PER_H = 2
_NPC_TIME_BONUS_MAX = 20
_NPC_FLOOR_PENALTY = 3

# 침식 가속
_EROSION_BASE = 5
_EROSION_FLOOR_BONUS = 2


# ============================================
# 메인 진입점
# ============================================

def run_faint_cycle():
    """플레이어 실신 → 구출/탈출/사망 판정 사이클 generator.

    호출측: dungeon_proceed에서 `yield from faint_rescue.run_faint_cycle()`.
    내부에서 linear_dungeon.exit_to_village 호출로 마을 복귀 처리까지 수행.
    """
    from engine import party_group as _pg

    player_id = morld.get_player_id()
    if player_id is None:
        return

    elapsed_hours = 0

    for _ in range(MAX_CYCLES):
        floor_idx = _get_current_floor_idx()

        # 1. 파티 구출 (같은 location 생존 NPC)
        rescuer = _try_party_rescue(player_id, _pg)
        if rescuer is not None:
            yield from _handle_party_rescue(rescuer)
            return

        # 2. 지나가는 NPC 구출
        if _try_passerby_rescue(elapsed_hours, floor_idx):
            yield from _handle_passerby_rescue()
            return

        # 3. 자력 탈출
        if _try_self_rescue(floor_idx):
            yield from _handle_self_rescue()
            return

        # 4. 시간 경과 + 침식 축적
        morld.advance_time_des(TICK_MILLIS)
        elapsed_hours += 1
        _add_erosion_tick(player_id, floor_idx)

        if _is_eroded_to_death(player_id):
            yield from _handle_death()
            return

    # 안전 fallback (거의 도달하지 않지만 한도 초과 시)
    yield ui.dialog("의식이 한없이 흐려진다... (한도 초과)")
    _trigger_reorganization()
    _exit_to_recovery("death")


# ============================================
# 판정 함수
# ============================================

def _try_party_rescue(player_id, _pg):
    """같은 location의 실신 아닌 파티원이 구출 판정(동정심+신뢰도) 성공 시 unit_id 반환."""
    party = _pg.get_party_of(player_id) if player_id else None
    if party is None:
        return None
    player_loc = morld.get_unit_location(player_id)
    if not player_loc:
        return None

    from engine.fsm_dungeon import _should_rescue
    for uid in party.get_members():
        if uid == player_id:
            continue
        if morld.get_unit_prop(uid, "상태:실신"):
            continue
        loc = morld.get_unit_location(uid)
        if loc is None:
            continue
        # location tuple의 region/loc만 비교 (좌표 차이는 무시)
        if loc[0] != player_loc[0] or loc[1] != player_loc[1]:
            continue
        if _should_rescue(uid):
            return uid
    return None


def _try_passerby_rescue(elapsed_hours, floor_idx):
    """평판 + 시간경과 - 층수 기반 확률 판정"""
    rep_avg = _get_public_reputation_avg()
    rep_bonus = max(0.0, (rep_avg + 100) * _NPC_REP_WEIGHT)
    time_bonus = min(_NPC_TIME_BONUS_MAX, elapsed_hours * _NPC_TIME_BONUS_PER_H)
    floor_penalty = floor_idx * _NPC_FLOOR_PENALTY
    prob = max(0.0, rep_bonus + time_bonus - floor_penalty)
    return random.random() * 100 < prob


def _try_self_rescue(floor_idx):
    """층수 반비례 자력 탈출 확률 (4층부터 0%)"""
    prob = max(0, _SELF_BASE - floor_idx * _SELF_FLOOR_PENALTY)
    return random.random() * 100 < prob


# ============================================
# 처리 함수 (yield)
# ============================================

def _handle_party_rescue(rescuer_id):
    from engine import korean
    name = morld.get_unit_name(rescuer_id) or str(rescuer_id)
    particle = korean.이_가(name)
    yield ui.dialog(
        "의식이 흐려진다...\n\n"
        + name + particle + " 당신을 끌어내어 마을로 향한다.")
    _recover_minimal()
    _exit_to_recovery("rescued")


def _handle_passerby_rescue():
    yield ui.dialog(
        "의식이 흐려지는 중, 지나가던 모험가가 당신을 발견하고\n"
        "마을로 끌어내어 눕혔다.")
    _recover_minimal()
    _exit_to_recovery("rescued")


def _handle_self_rescue():
    yield ui.dialog(
        "흐려지던 의식이 다시 돌아온다.\n"
        "어떻게든 몸을 일으켜 마을로 향한다.")
    _recover_minimal()
    _exit_to_recovery("self_rescued")


def _handle_death():
    """침식 사망 → 재편성 이벤트 (다이얼로그 기반).

    연출 흐름: 침식 종결 → 암전 → 구호소/입구 기상 → 재출발 각오.
    상태 리셋(_trigger_reorganization)은 암전 시점에 수행.
    """
    # 1. 침식이 삼키는 순간
    yield ui.dialog(
        "침식이 당신을 집어삼킨다.\n\n"
        "감각이 녹아내리고, 의식이 점차 희미해진다...")

    # 2. 암전 (생략된 시간 / 미지의 구출)
    yield ui.dialog(
        "...\n\n...\n\n...")

    # 3. 상태 리셋 (재편성)
    _trigger_reorganization()

    # 4. 기상 연출 (구호소 존재 여부에 따라 분기)
    if _has_infirmary():
        yield ui.dialog(
            "눈을 뜬다.\n"
            "익숙한 구호소의 천장이 보인다.\n\n"
            "어떻게 이곳으로 돌아왔는지 기억나지 않는다.")
    else:
        yield ui.dialog(
            "눈을 뜬다.\n"
            "던전 입구의 차가운 바람이 뺨을 스친다.\n\n"
            "어떻게 여기까지 왔는지 기억나지 않는다.")

    # 5. 재출발 각오
    yield ui.dialog(
        "몸은 온전하지만, 마음 한 구석에 공허함이 남아있다.\n\n"
        "...다시 일어서야 한다.")

    _exit_to_recovery("death")


# ============================================
# 헬퍼
# ============================================

def _recover_minimal():
    """회복 공통: 실신 해제 + HP max(1, RECOVERY_HP)"""
    player_id = morld.get_player_id()
    if player_id is None:
        return
    try:
        import survival
        survival.set_health(player_id, max(1, RECOVERY_HP))
    except (ImportError, Exception):
        pass
    morld.set_unit_prop(player_id, "상태:실신", 0)


def _trigger_reorganization():
    """사망 → 재편성 처리 (임시: 실신 해제 + HP 회복 + 침식 0).

    향후 확장 TODO: 파티 재구성, 아이템 손실, 시간 경과 등.
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return
    try:
        import erosion
        erosion.set_erosion(player_id, 0)
    except (ImportError, Exception):
        pass
    try:
        import survival
        survival.set_health(player_id, max(1, RECOVERY_HP))
    except (ImportError, Exception):
        pass
    morld.set_unit_prop(player_id, "상태:실신", 0)
    print("[faint_rescue] Death → reorganization triggered")


def _exit_to_recovery(reason):
    """탈출 목적지(구호소/던전입구)로 이동 — linear_dungeon.exit_to_village 위임."""
    try:
        import linear_dungeon as ld
        ld.exit_to_village(reason=reason)
    except (ImportError, Exception) as e:
        print("[faint_rescue] exit_to_village failed: " + str(e))


def _add_erosion_tick(player_id, floor_idx):
    try:
        import erosion
        amount = _EROSION_BASE + floor_idx * _EROSION_FLOOR_BONUS
        erosion.add_erosion(player_id, amount)
    except (ImportError, Exception):
        pass


def _is_eroded_to_death(player_id):
    try:
        import erosion
        return erosion.get_erosion(player_id) >= erosion.EROSION_MAX
    except (ImportError, Exception):
        return False


def _get_current_floor_idx():
    try:
        import linear_dungeon as ld
        if ld.is_active():
            return ld.get_floor_info()[0] - 1
    except (ImportError, Exception):
        pass
    return 0


def _get_public_reputation_avg():
    """모험가길드 + 마을주민 평판 평균. (-100~+100 범위, 기본 0)"""
    try:
        import reputation
        g = reputation.get_reputation("모험가길드")
        v = reputation.get_reputation("마을주민")
        return (g + v) / 2
    except (ImportError, Exception):
        return 0


def _has_infirmary():
    """구호소 건설 여부. 사망 연출 분기에 사용."""
    try:
        import facility
        return facility.has_infirmary()
    except (ImportError, Exception):
        return False
