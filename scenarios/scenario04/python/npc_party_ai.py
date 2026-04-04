# npc_party_ai.py - S04 NPC 파티 시뮬레이션
#
# 같은 층: 실시간 AI (이동/전투/함정)
# 다른 층: 추상적 처리 (결과만)
# 플레이어와 같은 층에서 갑자기 사라지지 않음.

import morld
import random
from events import subscribe_time_elapsed

# === NPC 파티 데이터 ===

_npc_parties = {}  # party_id -> {"name", "members": [...], "floor", "region_id", "loc_id", "disposition"}
_next_party_id = 1


def reset():
    global _next_party_id
    _npc_parties.clear()
    _next_party_id = 1


def create_npc_party(name: str, members: list, floor: int, disposition: str = "중립") -> int:
    """
    NPC 파티 생성.

    Args:
        name: 파티 이름
        members: [{"unit_id", "name", "stats"}, ...]
        floor: 현재 층
        disposition: "정의" / "중립" / "약탈"
    """
    global _next_party_id
    pid = _next_party_id
    _next_party_id += 1

    _npc_parties[pid] = {
        "name": name,
        "members": members,
        "floor": floor,
        "region_id": 100 + floor,
        "loc_id": 0,
        "disposition": disposition,
        "alive": True,
    }
    print(f"[npc_party] Created: {name} (floor {floor}, {len(members)} members, {disposition})")
    return pid


def get_parties_on_floor(floor: int) -> list:
    """특정 층의 NPC 파티 목록"""
    return [
        {"party_id": pid, **info}
        for pid, info in _npc_parties.items()
        if info["floor"] == floor and info["alive"]
    ]


def get_party(party_id: int) -> dict:
    return _npc_parties.get(party_id, {}).copy()


# === 같은 층: 실시간 AI ===

def simulate_same_floor(party_id: int) -> list:
    """
    같은 층 NPC 파티 1턴 행동.

    Returns:
        [이벤트 문자열, ...]
    """
    info = _npc_parties.get(party_id)
    if not info or not info["alive"]:
        return []

    events = []
    action = random.choices(
        ["이동", "탐색", "전투", "대기"],
        weights=[30, 20, 20, 30],
        k=1
    )[0]

    if action == "이동":
        # 인접 방으로 이동
        info["loc_id"] = (info["loc_id"] + random.choice([-1, 1])) % 5
        events.append(f"[{info['name']}] 이동 중...")

    elif action == "탐색":
        events.append(f"[{info['name']}] 주변을 탐색하고 있다.")

    elif action == "전투":
        # 몬스터 조우 시뮬레이션
        if random.random() < 0.4:
            casualties = random.randint(0, 1)
            if casualties > 0 and info["members"]:
                fallen = info["members"].pop()
                events.append(f"[{info['name']}] 전투! {fallen['name']}이(가) 쓰러졌다!")
                if not info["members"]:
                    info["alive"] = False
                    events.append(f"[{info['name']}] 전멸!")
            else:
                events.append(f"[{info['name']}] 몬스터와 전투 후 승리.")

    elif action == "대기":
        events.append(f"[{info['name']}] 휴식 중...")

    return events


# === 다른 층: 추상적 처리 ===

def simulate_abstract(party_id: int) -> str:
    """
    다른 층 NPC 파티 추상적 시뮬레이션.

    Returns:
        상태 문자열
    """
    info = _npc_parties.get(party_id)
    if not info or not info["alive"]:
        return "소멸"

    # 추상적 결과
    roll = random.random()
    if roll < 0.05:
        # 전멸
        info["alive"] = False
        return f"{info['name']}: {info['floor']}층에서 전멸"
    elif roll < 0.15:
        # 피해
        if info["members"]:
            info["members"].pop()
            if not info["members"]:
                info["alive"] = False
                return f"{info['name']}: 전멸"
        return f"{info['name']}: 피해 발생"
    elif roll < 0.3:
        # 층 이동
        direction = random.choice([-1, 1])
        new_floor = max(1, min(20, info["floor"] + direction))
        info["floor"] = new_floor
        info["region_id"] = 100 + new_floor
        return f"{info['name']}: {new_floor}층으로 이동"
    else:
        return f"{info['name']}: {info['floor']}층 체류 중"


# === 상호작용 ===

def get_party_disposition_reaction(party_id: int, player_action: str) -> str:
    """
    NPC 파티의 플레이어 행동에 대한 반응.

    Args:
        player_action: "약탈", "접근", "공격"
    """
    info = _npc_parties.get(party_id)
    if not info:
        return "없음"

    disposition = info["disposition"]

    reactions = {
        ("정의", "약탈"): "공격",
        ("정의", "접근"): "우호",
        ("정의", "공격"): "반격",
        ("중립", "약탈"): "도망",
        ("중립", "접근"): "경계",
        ("중립", "공격"): "반격",
        ("약탈", "약탈"): "반격",
        ("약탈", "접근"): "약탈시도",
        ("약탈", "공격"): "반격",
    }

    return reactions.get((disposition, player_action), "무시")


# === 시간 경과 ===

def _on_time_elapsed(millis: int):
    """다른 층 NPC 파티 추상적 시뮬레이션"""
    player_id = morld.get_player_id()
    player_floor = None
    if player_id:
        loc = morld.get_unit_location(player_id)
        if loc:
            region_id = loc[0]
            if region_id >= 100:
                player_floor = region_id - 100

    for pid in list(_npc_parties):
        info = _npc_parties[pid]
        if not info["alive"]:
            continue

        if player_floor is not None and info["floor"] == player_floor:
            # 같은 층 → 실시간 (외부에서 호출)
            pass
        else:
            # 다른 층 → 추상적
            simulate_abstract(pid)


subscribe_time_elapsed(_on_time_elapsed, min_interval=3600000)
