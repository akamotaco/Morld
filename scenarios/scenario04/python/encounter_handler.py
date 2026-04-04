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
import pollution
import quirk


def start_encounter(enemy_data: list) -> dict:
    """
    대결 시작: 파티 정보 패키징 → 전투 실행 → 결과 반영.

    Args:
        enemy_data: [{"name", "stats", "skills"}, ...] 적 데이터

    Returns:
        encounter 결과 dict
    """
    # 1. 아군 정보 패키징
    allies = _package_allies()

    # 2. 적 정보 패키징
    enemies = _package_enemies(enemy_data)

    # 3. 전투 실행
    result = encounter.run_encounter(allies, enemies)

    # 4. 결과 반영
    _apply_result(result)

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
    """적 데이터를 전투 참가자로 변환"""
    enemies = []
    for i, data in enumerate(enemy_data):
        stats = data.get("stats", {"hp": 30, "max_hp": 30, "str": 8, "agi": 8,
                                     "vit": 8, "mnd": 5, "ap_max": 2,
                                     "attack": 8, "defense": 4})
        skills = data.get("skills", [])
        combatant = encounter.make_combatant(
            unit_id=-(i + 1),  # 음수 ID = 적
            name=data.get("name", f"적 {i+1}"),
            stats=stats,
            skills=skills,
        )
        enemies.append(combatant)
    return enemies


def _apply_result(result: dict):
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

    # 4. 전투 중 location 오염도 증가
    player_id = morld.get_player_id()
    if player_id:
        loc = morld.get_unit_location(player_id)
        if loc:
            region_id, loc_id = loc
            # 전투 = 오염도 +2
            pollution.add_pollution(region_id, loc_id, 2)

    # 5. 플레이어 실신 → 재편성
    if party.get_leader() in result["fainted"]:
        import dungeon
        dungeon.reorganize()

    # 6. 전투 로그 출력 (mini_monologue용)
    for line in result["log"]:
        print(line)
