# encounter.py - S04 대결 (Encounter) 시스템
#
# 독립 모듈: 입력(전투 정보) → 처리(이니셔티브 턴제) → 출력(결과)
# Phase 1: 자동 전투 (AI 전원 조작)
# Phase 2: 플레이어 커맨드 + Godot 씬 연출
#
# 게임 엔진과 분리. 순수 Python. Godot 비의존.

import random

# === 전투 참가자 데이터 ===

def make_combatant(unit_id: int, name: str, stats: dict, skills: list = None,
                    is_player: bool = False, ai_mode: str = "auto") -> dict:
    """
    전투 참가자 데이터 생성.

    Args:
        unit_id: 유닛 ID
        name: 이름
        stats: {"hp", "max_hp", "str", "agi", "vit", "mnd", "ap_max", "attack", "defense"}
        skills: [{"name", "ap_cost", "power", "type"}, ...]
        is_player: 플레이어 여부
        ai_mode: "auto" / "physical_only" / "full_power"
    """
    return {
        "unit_id": unit_id,
        "name": name,
        "hp": stats.get("hp", stats.get("max_hp", 50)),
        "max_hp": stats.get("max_hp", 50),
        "str": stats.get("str", 10),
        "agi": stats.get("agi", 10),
        "vit": stats.get("vit", 10),
        "mnd": stats.get("mnd", 10),
        "ap_max": stats.get("ap_max", 3),
        "attack": stats.get("attack", 10),
        "defense": stats.get("defense", 5),
        "skills": skills or [],
        "is_player": is_player,
        "ai_mode": ai_mode,
        "hate": 0,
        "alive": True,
    }


# === 전투 실행 ===

def run_encounter(allies: list, enemies: list, max_turns: int = 30) -> dict:
    """
    대결 실행 (자동 전투).

    Args:
        allies: [make_combatant(), ...] 아군 목록
        enemies: [make_combatant(), ...] 적 목록
        max_turns: 최대 턴 수

    Returns:
        {
            "result": "victory" / "defeat" / "flee" / "draw",
            "turns": int,
            "log": [str, ...],
            "allies": [updated combatant, ...],
            "enemies": [updated combatant, ...],
            "fainted": [unit_id, ...],
            "fled": [unit_id, ...],
        }
    """
    log = []
    all_combatants = allies + enemies
    fainted = []
    fled = []

    log.append(f"=== 대결 시작: {len(allies)}명 vs {len(enemies)}명 ===")

    for turn in range(1, max_turns + 1):
        log.append(f"\n--- 턴 {turn} ---")

        # 이니셔티브 순서 결정
        alive = [c for c in all_combatants if c["alive"]]
        turn_order = sorted(alive, key=lambda c: _calc_initiative(c), reverse=True)

        for combatant in turn_order:
            if not combatant["alive"]:
                continue

            # 행동 결정 (AI)
            ap_remaining = combatant["ap_max"]

            while ap_remaining > 0:
                action = _decide_action(combatant, allies, enemies, ap_remaining)
                if action is None:
                    break

                result = _execute_action(combatant, action, allies, enemies)
                log.append(result["message"])
                ap_remaining -= action.get("ap_cost", 1)

                # 사망 체크
                for c in all_combatants:
                    if c["hp"] <= 0 and c["alive"]:
                        c["alive"] = False
                        fainted.append(c["unit_id"])
                        log.append(f"  {c['name']} 쓰러졌다!")

            # 승패 판정
            allies_alive = any(c["alive"] for c in allies)
            enemies_alive = any(c["alive"] for c in enemies)

            if not enemies_alive:
                log.append("\n=== 승리! ===")
                return _build_result("victory", turn, log, allies, enemies, fainted, fled)

            if not allies_alive:
                log.append("\n=== 패배... ===")
                return _build_result("defeat", turn, log, allies, enemies, fainted, fled)

    log.append("\n=== 무승부 (턴 제한) ===")
    return _build_result("draw", max_turns, log, allies, enemies, fainted, fled)


# === 내부 함수 ===

def _calc_initiative(combatant: dict) -> float:
    """이니셔티브 계산: 민첩 + 랜덤"""
    return combatant["agi"] + random.uniform(0, 5)


def _decide_action(combatant, allies, enemies, ap_remaining) -> dict:
    """AI 행동 결정 (Phase 1: 심플)"""
    # 적군/아군 판별
    is_ally = combatant in allies
    targets = enemies if is_ally else allies
    alive_targets = [t for t in targets if t["alive"]]

    if not alive_targets:
        return None

    # 스킬 사용 가능하면 스킬 우선 (AP 충분한 것 중 랜덤)
    usable_skills = [s for s in combatant["skills"]
                     if s.get("ap_cost", 1) <= ap_remaining]

    if usable_skills and random.random() < 0.3:
        skill = random.choice(usable_skills)
        target = _select_target(alive_targets, combatant)
        return {"type": "skill", "skill": skill, "target": target,
                "ap_cost": skill.get("ap_cost", 1)}

    # 기본 공격
    target = _select_target(alive_targets, combatant)
    return {"type": "attack", "target": target, "ap_cost": 1}


def _select_target(targets, attacker) -> dict:
    """타겟 선택: Hate 높은 적 우선"""
    if not targets:
        return None
    # Hate 기반 가중치
    weights = [max(1, t.get("hate", 0) + 5) for t in targets]
    return random.choices(targets, weights=weights, k=1)[0]


def _execute_action(combatant, action, allies, enemies) -> dict:
    """행동 실행"""
    if action["type"] == "attack":
        return _do_attack(combatant, action["target"])
    elif action["type"] == "skill":
        return _do_skill(combatant, action["skill"], action["target"])
    return {"message": f"  {combatant['name']}은(는) 아무것도 하지 않았다."}


def _do_attack(attacker, target) -> dict:
    """기본 공격"""
    base_dmg = attacker["attack"] - target["defense"] // 2
    damage = max(1, base_dmg + random.randint(-2, 2))
    target["hp"] = max(0, target["hp"] - damage)
    target["hate"] += 1

    return {"message": f"  {attacker['name']} → {target['name']}에게 {damage} 데미지!"}


def _do_skill(attacker, skill, target) -> dict:
    """스킬 사��"""
    power = skill.get("power", 10)
    base_dmg = power + attacker["attack"] // 2 - target["defense"] // 3
    damage = max(1, base_dmg + random.randint(-3, 3))
    target["hp"] = max(0, target["hp"] - damage)
    target["hate"] += 2

    return {"message": f"  {attacker['name']}의 [{skill['name']}]! {target['name']}에게 {damage} 데미지!"}


def _build_result(result, turns, log, allies, enemies, fainted, fled) -> dict:
    return {
        "result": result,
        "turns": turns,
        "log": log,
        "allies": allies,
        "enemies": enemies,
        "fainted": fainted,
        "fled": fled,
    }
