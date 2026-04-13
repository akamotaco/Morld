# encounter_handler.py - 대결 결과를 게임 시스템에 반영하는 글루 코드
#
# encounter.py는 순수 전투 모듈 (입력→출력).
# 이 파일이 전투 전 정보 패키징 + 전투 후 결과 반영을 담당.

import morld
import encounter
import party
import morale
import trust
import survival
import erosion
import reputation
import quirk


def start_encounter(enemy_data: list) -> dict:
    """
    대결 시작: 파티 vs 파티 전투.

    enemy_data는 creature_pool.generate_encounter()가 만든 파티 구성.
    첫 번째 요소가 리더 (is_leader=True).

    Args:
        enemy_data: [{"name", "stats", "is_leader", ...}, ...] 몬스터 파티

    Returns:
        encounter 결과 dict
    """
    # 1. 아군 파티 패키징
    allies = _package_allies()

    # 2. 적 파티 패키징 (몬스터 파티 구성)
    enemies = _package_enemies(enemy_data)

    # 3. 전투 실행
    result = encounter.run_encounter(allies, enemies)

    # 4. 결과 반영 (원본 enemy_data 전달 — 침식 계산용)
    _apply_result(result, enemy_data)

    return result


def _package_allies() -> list:
    """파티원을 전투 참가자 데이터로 변환"""
    allies = []
    for mid in party.get_members():
        info = morld.get_unit_info(mid)
        if not info:
            continue

        name = info.get("name", "???")
        hp = survival.get_health(mid)
        max_hp = morld.get_unit_prop(mid, "생존:최대체력") or 100

        stats = {
            "hp": hp,
            "max_hp": max_hp,
            "str": morld.get_unit_prop(mid, "스탯:근력") or 10,
            "agi": morld.get_unit_prop(mid, "스탯:민첩") or 10,
            "vit": morld.get_unit_prop(mid, "스탯:체력") or 10,
            "mnd": morld.get_unit_prop(mid, "스탯:정신") or 10,
            "ap_max": 3,
            "attack": (morld.get_unit_prop(mid, "스탯:근력") or 10),
            "defense": (morld.get_unit_prop(mid, "스탯:체력") or 10) // 2,
        }

        is_player = (mid == party.get_leader())
        combatant = encounter.make_combatant(mid, name, stats, is_player=is_player)
        allies.append(combatant)

    return allies


def _package_enemies(enemy_data: list) -> list:
    """적 데이터를 전투 참가자로 변환 (몬스터 파티)

    enemy_data[0]가 리더 (is_leader=True이면 해당 요소).
    리더 먼저 생성하여 unit_id=-1 할당. 나머지는 -2, -3...
    몬스터 파티는 전투 동안만 존재 → 엔진 Party 등록 생략.
    """
    enemies = []

    # 리더 인덱스 (없으면 첫 요소)
    leader_idx = next((i for i, d in enumerate(enemy_data) if d.get("is_leader")), 0)

    default_stats = {"hp": 30, "max_hp": 30, "str": 8, "agi": 8,
                     "vit": 8, "mnd": 5, "ap_max": 2,
                     "attack": 8, "defense": 4}

    # 리더 먼저
    next_id = -1
    order = [leader_idx] + [i for i in range(len(enemy_data)) if i != leader_idx]
    for i in order:
        data = enemy_data[i]
        stats = data.get("stats", default_stats)
        skills = data.get("skills", [])
        combatant = encounter.make_combatant(
            unit_id=next_id,
            name=data.get("name", f"적 {abs(next_id)}"),
            stats=stats,
            skills=skills,
        )
        # 리더 표시 (첫 combatant = 리더)
        if isinstance(combatant, dict):
            combatant["is_leader"] = (i == leader_idx)
        enemies.append(combatant)
        next_id -= 1
    return enemies


def _apply_result(result: dict, enemy_data: list = None):
    """전투 결과를 게임 시스템에 반영"""

    # 1. 사기 변동
    if result["result"] == "victory":
        morale.on_battle_victory()
    elif result["result"] == "defeat":
        morale.on_battle_defeat()

    # 2. 아군 HP 동기화
    for ally in result["allies"]:
        uid = ally["unit_id"]
        survival.set_health(uid, max(0, ally["hp"]))

    # 3. 실신 처리
    for fainted_id in result["fainted"]:
        if fainted_id > 0:  # 아군 (양수 ID)
            party.handle_faint(fainted_id)

            # 사기: 동료 실신 목격
            morale.on_ally_fainted(fainted_id)

            # 신뢰: 파티원들에게 영향 (방치?)
            # → 이건 플레이어 선택에 따라 나중에

    # 4. 전투 결과 기반 침식 적용
    #    - 피격 시 erosion_on_hit (적 데이터에서)
    #    - 처치 시 erosion_on_death (음수면 정화 효과)
    _apply_erosion_from_combat(result, enemy_data)

    # 5. 전투 로그 출력 (mini_monologue용)
    #    실신 → 재편성 트리거는 제거됨. 재편성은 사망 이벤트(party.handle_death)에서만.
    for line in result["log"]:
        print(line)


def _apply_erosion_from_combat(result, enemy_data):
    """전투 결과 기반 침식 적용

    - 피격당한 아군: 적의 erosion_on_hit만큼 침식 증가
    - 처치한 적: erosion_on_death만큼 파티 전원 침식 변동 (음수=정화)
    """
    if not enemy_data:
        return

    # 처치된 적의 erosion_on_death 합산
    # 적 unit_id는 _package_enemies에서 리더 먼저(-1), 나머지(-2, -3...) 순으로 할당됨
    total_death_erosion = 0
    fainted_enemies = set(uid for uid in result.get("fainted", []) if uid < 0)
    leader_idx = next((i for i, d in enumerate(enemy_data) if d.get("is_leader")), 0)
    order = [leader_idx] + [i for i in range(len(enemy_data)) if i != leader_idx]
    for slot, i in enumerate(order):
        enemy_uid = -(slot + 1)
        if enemy_uid in fainted_enemies:
            total_death_erosion += enemy_data[i].get("erosion_on_death", 0)

    # 피격 침식: 전투 중 받은 총 대미지 기반 (간이 계산)
    # 적의 erosion_on_hit × 피격 횟수를 정확히 추적하려면 encounter 내부 수정 필요
    # 현재: 적 중 erosion_on_hit > 0인 적이 있으면 파티 전원에 기본 침식
    hit_erosion = 0
    for data in enemy_data:
        eoh = data.get("erosion_on_hit", 0)
        if eoh > 0:
            hit_erosion += eoh

    # 파티 전원에 적용
    members = party.get_members()
    for mid in members:
        total = hit_erosion + total_death_erosion
        if total != 0:
            try:
                if total > 0:
                    erosion.add_erosion(mid, total)
                else:
                    erosion.reduce_erosion(mid, abs(total))
            except Exception:
                pass
