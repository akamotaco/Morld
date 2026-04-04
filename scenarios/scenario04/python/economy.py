# economy.py - S04 경제 시스템
#
# 화폐: 원 (KRW)
# 톤: "돈은 있는데 쓸 곳이 많다"
#
# 소지금은 prop으로 관리: "경제:소지금"
# 상점 거래, 시설 비용, 모집비 등 모든 금전 거래 처리.

import morld

# === 상수 ===

# 초기 소지금
STARTING_MONEY = 50000  # 5만원

# 시설 비용 (기본, 밸런싱 추후)
COST_TABLE = {
    # 구호소
    "치료:기본":       5000,
    "치료:중상":       15000,

    # 정화소
    "정화:소폭":       10000,   # 침식 20 감소
    "정화:대폭":       30000,   # 침식 50 감소
    "정화:기벽치료":   50000,   # 기벽 1개 제거

    # 대장간
    "수리:기본":       3000,
    "수리:부식":       8000,
    "강화:기본":       20000,

    # 여관
    "숙박:하룻밤":     2000,
    "식사:기본":       1000,
    "식사:풀코스":     3000,

    # 모집
    "모집:일반":       10000,   # 일반 NPC 파티 합류 보수
    "모집:숙련":       25000,   # 숙련 NPC
    "모집:특수":       50000,   # 특수 NPC (오염술사 등)
}


def reset():
    """챕터 전환 시 리셋"""
    pass  # 소지금은 prop 기반이므로 clear_world()로 초기화됨


def init_money(unit_id: int, amount: int = None):
    """캐릭터 소지금 초기화"""
    if amount is None:
        amount = STARTING_MONEY
    morld.set_unit_prop(unit_id, "경제:소지금", amount)


def get_money(unit_id: int) -> int:
    """소지금 조회"""
    return morld.get_unit_prop(unit_id, "경제:소지금") or 0


def add_money(unit_id: int, amount: int):
    """소지금 증가"""
    current = get_money(unit_id)
    morld.set_unit_prop(unit_id, "경제:소지금", current + amount)


def spend_money(unit_id: int, amount: int) -> bool:
    """
    소지금 지출. 잔액 부족하면 False 반환.

    Returns:
        True: 지출 성공
        False: 잔액 부족
    """
    current = get_money(unit_id)
    if current < amount:
        return False
    morld.set_unit_prop(unit_id, "경제:소지금", current - amount)
    return True


def get_cost(cost_key: str) -> int:
    """비용 테이블 조회"""
    return COST_TABLE.get(cost_key, 0)


def can_afford(unit_id: int, cost_key: str) -> bool:
    """비용 지불 가능 여부"""
    return get_money(unit_id) >= get_cost(cost_key)


def pay(unit_id: int, cost_key: str) -> bool:
    """비용 테이블 기반 지출"""
    cost = get_cost(cost_key)
    if cost <= 0:
        return True
    return spend_money(unit_id, cost)


# === 아이템 가치 ===

def get_item_value(item_id: int) -> int:
    """아이템 매각 가치 (prop 기반)"""
    value = morld.get_unit_prop(item_id, "경제:가치")
    if value is not None:
        return int(value)

    # 기본값
    return 100


def sell_item(seller_id: int, item_id: int, buyer_markup: float = 1.0) -> int:
    """
    아이템 판매.

    Args:
        seller_id: 판매자 unit_id
        item_id: 아이템 id
        buyer_markup: 구매자 마크업 (평판에 따라 변동)

    Returns:
        판매 금액
    """
    value = int(get_item_value(item_id) * buyer_markup)
    add_money(seller_id, value)
    morld.remove_item(seller_id, item_id)
    return value
