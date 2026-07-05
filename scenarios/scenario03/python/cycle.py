# cycle.py — 반복 운영 루프 (시나리오03 MVP)
#
# 데모 14단계(튜토리얼) 종료 후 진입하는 로그라이트 코어 루프:
#   보급(supply) → 준비(ready: 편성/출발) → 탐사(expedition) → 보고(debrief) → 다음 주기
#
# 게임 루프 설계(design.md 6.1)의 MVP 절단면 — 헌납/취조/상담은 범위 외.
# 결번(사망) 처리와 차기 시리얼 재보급(재활용 테마)이 이 모듈의 책임.

import morld


# 역할 표시명(prop "역할") ↔ ROLE_PROPS 키
ROLE_KEYS = {
    "돌격": "assault",
    "화력 지원": "support",
    "저격": "sniper",
    "의무병": "medic",
}
ROLE_LABELS = {v: k for k, v in ROLE_KEYS.items()}

# 주기당 정기 배급 자재
SUPPLY_PACKAGE = {"plank": 5, "concrete_block": 3, "metal_pipe": 2, "wire": 2}

# 주기 → 난이도 (외적 팽창 대신 완만한 상승)
def difficulty_for_cycle(cycle_number):
    if cycle_number <= 2:
        return "easy"
    if cycle_number <= 4:
        return "normal"
    return "hard"


# ========================================
# 모듈 상태
# ========================================

_ops = {
    "active": False,
    "cycle": 0,             # 현재 운행 주기 (1-based)
    "phase": "idle",        # idle → ready → expedition → debrief → ready ...
    "stockpile": {},        # {unique_id: count} — 플랫폼 자재 재고 (서로게이트)
    "reports": [],          # 주기별 보고서 dict 누적
    "pending_supply": [],   # [{"role_key", "prev_name"}] — 결번 → 차기 보급 대기
    "next_serial": 5,       # Echo-01~04는 튜토리얼 보급분
    "role_deaths": {},      # {role_key: count} — 트라우마 계승 계산용
}


def reset():
    _ops.update({
        "active": False, "cycle": 0, "phase": "idle",
        "stockpile": {}, "reports": [], "pending_supply": [],
        "next_serial": 5, "role_deaths": {},
    })


# ========================================
# 라이프사이클
# ========================================

def start_operations():
    """데모(튜토리얼) 종료 후 운영 모드 진입 — 운행 주기 1, 출발 대기"""
    _ops["active"] = True
    _ops["cycle"] = 1
    _ops["phase"] = "ready"
    print("[cycle] Operations started (cycle 1, phase=ready)")


def is_active():
    return _ops["active"]


def get_phase():
    return _ops["phase"]


def get_cycle_number():
    return _ops["cycle"]


def get_stockpile():
    return dict(_ops["stockpile"])


def current_difficulty():
    return difficulty_for_cycle(_ops["cycle"])


def mark_expedition_started():
    if _ops["active"]:
        _ops["phase"] = "expedition"


# ========================================
# 결번 처리 (전투 사망)
# ========================================

def process_casualties(squad_id, dead_unit_ids):
    """전투 사망자 결번 처리.

    - 분대에서 제거 (분대장이면 잔존 대원 승계)
    - Agent 레지스트리 해제 + 유닛 제거
    - 차기 시리얼 보급 대기열 등록

    Returns:
        [{"name", "role_key"}] — 결번 기록 (보고서/대화용)
    """
    import squad as squad_module
    from think import unregister_agent

    records = []
    for uid in dead_unit_ids:
        info = morld.get_unit_info(uid) or {}
        name = info.get("name", f"Unit-{uid}")
        role_label = morld.get_unit_prop(uid, "역할")
        role_key = ROLE_KEYS.get(role_label, "assault")
        records.append({"name": name, "role_key": role_key})

        sq = squad_module.get_squad_by_unit(uid)
        if sq:
            if sq.leader_id == uid:
                survivors = list(sq.members)
                if survivors:
                    # 죽은 분대장을 멤버로 밀어낸 뒤 제거 (승계)
                    squad_module.change_leader(sq.squad_id, survivors[0])
                    squad_module.remove_member(sq.squad_id, uid)
                else:
                    squad_module.disband_squad(sq.squad_id)
            else:
                squad_module.remove_member(sq.squad_id, uid)

        unregister_agent(uid)
        morld.remove_unit(uid)

        _ops["role_deaths"][role_key] = _ops["role_deaths"].get(role_key, 0) + 1
        _ops["pending_supply"].append({"role_key": role_key, "prev_name": name})
        print(f"[cycle] 결번 처리: {name} ({role_key})")

    return records


# ========================================
# 주기 완료 (귀환 → 보고서)
# ========================================

def complete_cycle(expedition_summary):
    """귀환 후 주기 마감. 전리품 입고 + 보고서 생성.

    Args:
        expedition_summary: expedition.complete_expedition() 반환 dict

    Returns:
        report dict
    """
    if not _ops["active"]:
        return None

    loot = expedition_summary.get("collected_loot", {})
    for uid, cnt in loot.items():
        _ops["stockpile"][uid] = _ops["stockpile"].get(uid, 0) + cnt

    # 생존 대원 스냅샷
    import squad as squad_module
    members = []
    for sq in squad_module.get_all_squads():
        for unit_id in sq.all_unit_ids():
            info = morld.get_unit_info(unit_id) or {}
            hp = morld.get_unit_prop(unit_id, "생존:체력") or 0
            hp_max = morld.get_unit_prop(unit_id, "생존:체력max") or 60
            members.append({
                "name": info.get("name", f"Unit-{unit_id}"),
                "role": morld.get_unit_prop(unit_id, "역할") or "?",
                "hp": hp, "hp_max": hp_max,
                "vita": morld.get_unit_prop(unit_id, "vita") or 5,
                "humanity": morld.get_unit_prop(unit_id, "인간성") or 0,
                "rank": squad_module.get_member_rank(sq.squad_id, unit_id),
                "is_leader": unit_id == sq.leader_id,
            })

    report = {
        "cycle": _ops["cycle"],
        "difficulty": expedition_summary.get("difficulty", "easy"),
        "rooms_explored": expedition_summary.get("rooms_explored", 0),
        "rooms_total": expedition_summary.get("rooms_total", 0),
        "combat_count": expedition_summary.get("combat_count", 0),
        "victory_count": expedition_summary.get("victory_count", 0),
        "collected_loot": dict(loot),
        "casualties": list(expedition_summary.get("casualties", [])),
        "members": members,
        "stockpile": dict(_ops["stockpile"]),
    }
    _ops["reports"].append(report)
    _ops["phase"] = "debrief"
    print(f"[cycle] Cycle {_ops['cycle']} debrief ready")
    return report


def get_last_report():
    return _ops["reports"][-1] if _ops["reports"] else None


# ========================================
# 보급 (다음 주기 개시)
# ========================================

def run_supply_phase():
    """보급 열차 도착: 정기 자재 + 결번 대체 개체 송출. 다음 주기로 진행.

    Returns:
        {"cycle", "materials", "replacements": [{"name", "role_key", "humanity"}]}
    """
    if not _ops["active"]:
        return None

    for uid, cnt in SUPPLY_PACKAGE.items():
        _ops["stockpile"][uid] = _ops["stockpile"].get(uid, 0) + cnt

    replacements = []
    for pending in _ops["pending_supply"]:
        rec = _spawn_replacement(pending["role_key"])
        if rec:
            replacements.append(rec)
    _ops["pending_supply"] = []

    _ops["cycle"] += 1
    _ops["phase"] = "ready"
    print(f"[cycle] Supply complete → cycle {_ops['cycle']}")
    return {
        "cycle": _ops["cycle"],
        "materials": dict(SUPPLY_PACKAGE),
        "replacements": replacements,
    }


def _spawn_replacement(role_key):
    """결번 역할의 차기 시리얼 개체 생성 + 분대 자동 편입.

    재활용 테마: 해당 역할의 누적 결번 수만큼 인간성이 깎인 채 도착
    (전임자의 파편화된 트라우마 계승 — design.md 4.3).
    """
    from assets.characters.squad_member import SquadMember
    from think.agents.squad_agent import SquadMemberAgent
    from think import register_agent
    import squad as squad_module

    serial = _ops["next_serial"]
    _ops["next_serial"] += 1
    unique_id = f"echo_{serial:02d}"
    name = f"Echo-{serial:02d}"

    deaths = _ops["role_deaths"].get(role_key, 0)
    humanity = max(30, 100 - 10 * deaths)

    npc = SquadMember()
    npc.configure(unique_id, name, role_key, humanity=humanity)
    npc_id = morld.create_id("unit")
    npc.instantiate(npc_id, 0, 0)  # 승강장(R0, L0) 도착

    agent = SquadMemberAgent(npc_id)
    register_agent(npc_id, agent)

    # 기존 분대에 자동 편입 (없으면 플레이어가 수동 편성)
    squads = squad_module.get_all_squads()
    if squads:
        sq = squads[0]
        if sq.leader_id is None:
            squad_module.assign_leader(sq.squad_id, npc_id)
        elif not sq.is_full():
            squad_module.add_member(sq.squad_id, npc_id)

    print(f"[cycle] 보급 개체 도착: {name} ({role_key}, 인간성 {humanity})")
    return {"unit_id": npc_id, "name": name, "role_key": role_key,
            "humanity": humanity}


# ========================================
# 보고서 텍스트 (행정 문서 톤)
# ========================================

RANK_LABELS = {1: "전위", 2: "중위", 3: "후위"}

_CLOSING_LINES = [
    "손실은 관리되어야 하며, 관리된 손실은 손실이 아닙니다.",
    "적시 교체는 최선의 유지보수입니다.",
    "한 개체의 지연이 전체 운행에 영향을 미칩니다.",
]


def build_report_text(report=None):
    """사후 운용 보고서 텍스트 (ui.dialog용)"""
    r = report or get_last_report()
    if not r:
        return "제출된 운용 보고서가 없습니다."

    lines = [f"[b]운행 주기 {r['cycle']} — 사후 운용 보고서[/b]\n"]
    lines.append(f"  탐사: {r['rooms_explored']}/{r['rooms_total']} 구역"
                 f" (난이도: {r['difficulty']})")
    lines.append(f"  전투: {r['combat_count']}회 교전, {r['victory_count']}회 제압")

    lines.append("\n  [대원별 최종 상태]")
    if r["members"]:
        for m in r["members"]:
            rank = RANK_LABELS.get(m["rank"], "?")
            leader = " ◆" if m["is_leader"] else ""
            lines.append(
                f"    [{rank}] {m['name']} ({m['role']}){leader}"
                f" — 체력 {m['hp']}/{m['hp_max']},"
                f" Vita {m['vita']}, H.I {m['humanity']}%")
    else:
        lines.append("    (활동 개체 없음)")

    if r["casualties"]:
        lines.append("\n  [결번]")
        for c in r["casualties"]:
            lines.append(f"    {c.get('name', '?')} — 차기 개체 보급 예정")

    if r["collected_loot"]:
        loot_text = ", ".join(f"{u} x{c}" for u, c in r["collected_loot"].items())
        lines.append(f"\n  수집: {loot_text}")

    stock_text = ", ".join(f"{u} x{c}" for u, c in r["stockpile"].items())
    if stock_text:
        lines.append(f"  재고: {stock_text}")

    closing = _CLOSING_LINES[(r["cycle"] - 1) % len(_CLOSING_LINES)]
    lines.append(f"\n[i]\"{closing}\"[/i]")
    return "\n".join(lines)
