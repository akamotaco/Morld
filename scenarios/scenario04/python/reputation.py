# reputation.py - S04 평판 시스템
#
# 세력별 평판. 행동에 따른 트레이드오프.
# 플레이어도 세력으로 취급 (도달 기록/행적 기반).
#
# 세력: 마을 주민, 모험가 길드, 암시장, 던전 세력
# 평판: -100 ~ +100 (0 = 중립)

import morld

# === 세력 정의 ===

FACTIONS = {
    "마을주민":   {"default": 0, "desc": "상점 가격, NPC 모집 난이도"},
    "모험가길드": {"default": 0, "desc": "정보, 구출 보상, 파티 후보 질"},
    "암시장":     {"default": -20, "desc": "인신매매, 밀수품, 금지 아이템"},
    "던전세력":   {"default": -10, "desc": "수거반/체류자 거래 가능 여부"},
}

# 플레이어 세력 (NPC가 플레이어를 어떻게 보는가)
PLAYER_FACTION = "플레이어"

# === 상태 ===
_reputation = {}  # faction -> value


def reset():
    _reputation.clear()
    for faction, info in FACTIONS.items():
        _reputation[faction] = info["default"]
    _reputation[PLAYER_FACTION] = 0


def get_reputation(faction: str) -> int:
    return _reputation.get(faction, 0)


def modify_reputation(faction: str, delta: int, reason: str = ""):
    old = _reputation.get(faction, 0)
    new = max(-100, min(100, old + delta))
    _reputation[faction] = new

    if old != new:
        print(f"[reputation] {faction}: {old} → {new} ({'+' if delta > 0 else ''}{delta}) {reason}")


def get_all_reputations() -> dict:
    return _reputation.copy()


# === 평판 영향 ===

def get_shop_price_modifier() -> float:
    """상점 가격 보정 (마을 주민 평판 기반)"""
    rep = get_reputation("마을주민")
    # -100 → 1.5배, 0 → 1.0배, +100 → 0.8배
    return max(0.8, 1.0 - rep * 0.002)


def get_recruit_difficulty_modifier() -> float:
    """NPC 모집 난이도 보정"""
    rep_village = get_reputation("마을주민")
    rep_guild = get_reputation("모험가길드")
    avg = (rep_village + rep_guild) / 2
    # 높을수록 쉬움 (1.0 = 기본, 낮을수록 어려움)
    return max(0.5, 1.0 + avg * 0.005)


def get_black_market_access() -> bool:
    """암시장 접근 가능 여부"""
    return get_reputation("암시장") >= -10


# === 행동별 평판 변동 ===

def on_rescue_npc():
    modify_reputation("마을주민", 3, "NPC 구출")
    modify_reputation("모험가길드", 5, "NPC 구출")
    modify_reputation(PLAYER_FACTION, 2, "NPC 구출")

def on_sell_to_shop():
    modify_reputation("마을주민", 1, "상점 거래")

def on_raid_party():
    modify_reputation("모험가길드", -10, "파티 약탈")
    modify_reputation("암시장", 3, "파티 약탈")
    modify_reputation(PLAYER_FACTION, -5, "파티 약탈")

def on_human_trafficking():
    modify_reputation("마을주민", -15, "인신매매")
    modify_reputation("모험가길드", -20, "인신매매")
    modify_reputation("암시장", 10, "인신매매")
    modify_reputation(PLAYER_FACTION, -10, "인신매매")

def on_run_business():
    modify_reputation("마을주민", 2, "경영 활동")
    modify_reputation(PLAYER_FACTION, 1, "경영 활동")

def on_floor_record(floor: int):
    """최고 층 도달 기록"""
    bonus = floor // 5  # 5층마다 +1
    modify_reputation(PLAYER_FACTION, bonus, f"{floor}층 도달")
    modify_reputation("모험가길드", bonus, f"{floor}층 도달")


# 초기화
reset()
