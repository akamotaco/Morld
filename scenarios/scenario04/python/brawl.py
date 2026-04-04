# brawl.py - S04 난투 (Brawl) 시스템
#
# 대결(Encounter)과 다른 즉흥적 전투.
# 다수 세력 뒤섞임 가능. 씬 전환 없이 간소화/자동 진행.
# 예시: 약탈 중 끼어들기, 3파전, 수거반 습격.
#
# Phase 1: 간소화된 자동 전투 (encounter 변형)

import random
import encounter


def run_brawl(groups: list, max_rounds: int = 10) -> dict:
    """
    난투 실행.

    Args:
        groups: [
            {"name": "그룹명", "combatants": [make_combatant(), ...]},
            {"name": "그룹명", "combatants": [...]},
            ...
        ]
        max_rounds: 최대 라운드

    Returns:
        {"result": str, "log": [str], "survivors": {group_name: [combatant]},
         "fainted": [unit_id]}
    """
    log = []
    fainted = []
    all_combatants = []

    for group in groups:
        for c in group["combatants"]:
            c["_group"] = group["name"]
            all_combatants.append(c)

    log.append(f"=== 난투 발생! {len(groups)}개 세력 ===")
    for g in groups:
        alive = sum(1 for c in g["combatants"] if c["alive"])
        log.append(f"  {g['name']}: {alive}명")

    for round_num in range(1, max_rounds + 1):
        log.append(f"\n--- 라운드 {round_num} ---")

        alive = [c for c in all_combatants if c["alive"]]
        if not alive:
            break

        # 이니셔티브 순서
        turn_order = sorted(alive, key=lambda c: c["agi"] + random.uniform(0, 5), reverse=True)

        for combatant in turn_order:
            if not combatant["alive"]:
                continue

            # 타겟: 다른 그룹 중 살아있는 적
            enemies = [c for c in alive
                       if c["alive"] and c["_group"] != combatant["_group"]]
            if not enemies:
                continue

            target = random.choice(enemies)

            # 간소화 공격
            damage = max(1, combatant["attack"] - target["defense"] // 2 + random.randint(-2, 2))
            target["hp"] = max(0, target["hp"] - damage)

            log.append(f"  {combatant['name']}({combatant['_group']}) → "
                       f"{target['name']}({target['_group']}) {damage}dmg")

            if target["hp"] <= 0:
                target["alive"] = False
                fainted.append(target["unit_id"])
                log.append(f"    {target['name']} 쓰러졌다!")

        # 생존 그룹 체크
        surviving_groups = set()
        for c in all_combatants:
            if c["alive"]:
                surviving_groups.add(c["_group"])

        if len(surviving_groups) <= 1:
            break

    # 결과
    survivors = {}
    for group in groups:
        alive_in_group = [c for c in group["combatants"] if c["alive"]]
        if alive_in_group:
            survivors[group["name"]] = alive_in_group

    if len(survivors) == 1:
        winner = list(survivors.keys())[0]
        log.append(f"\n=== {winner} 승리! ===")
        result = winner
    elif len(survivors) == 0:
        log.append("\n=== 전원 전멸 ===")
        result = "annihilation"
    else:
        log.append(f"\n=== 난투 종료 (생존: {', '.join(survivors.keys())}) ===")
        result = "stalemate"

    return {
        "result": result,
        "log": log,
        "survivors": survivors,
        "fainted": fainted,
    }
