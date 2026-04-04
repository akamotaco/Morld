# business.py - S04 경영 시스템
#
# 플레이어가 건축한 시설(여관/상점)을 운영.
# 시간 경과로 자동 수입 발생.
# 알바생 고용으로 수입 효율 증가.
# 평판에 따라 수익 변동.

import morld
from events import subscribe_time_elapsed
import economy
import reputation

# === 상수 ===

# 시설별 시간당 기본 수입
BASE_INCOME = {
    "여관": 500,    # 시간당 500원
    "상점": 300,    # 시간당 300원
    "농장": 100,    # 시간당 100원 (식량 생산)
}

# 알바생 비용/효과
EMPLOYEE_COST_PER_DAY = 3000   # 일당 3000원
EMPLOYEE_INCOME_MULT = 1.5     # 수입 1.5배

# === 상태 ===

_businesses = {}  # loc_id -> {"type", "employees", "accumulated_income"}
_accumulated_millis = 0


def reset():
    global _accumulated_millis
    _businesses.clear()
    _accumulated_millis = 0


def register_business(loc_id: int, business_type: str):
    """시설을 경영 대상으로 등록"""
    _businesses[loc_id] = {
        "type": business_type,
        "employees": 0,
        "accumulated_income": 0,
    }
    print(f"[business] Registered: {business_type} at loc {loc_id}")


def hire_employee(loc_id: int) -> bool:
    """알바생 고용"""
    if loc_id not in _businesses:
        return False

    player_id = morld.get_player_id()
    if not economy.spend_money(player_id, EMPLOYEE_COST_PER_DAY):
        print("[business] Not enough money for employee")
        return False

    _businesses[loc_id]["employees"] += 1
    print(f"[business] Employee hired at loc {loc_id} "
          f"(total: {_businesses[loc_id]['employees']})")
    return True


def fire_employee(loc_id: int) -> bool:
    """알바생 해고"""
    if loc_id not in _businesses:
        return False
    if _businesses[loc_id]["employees"] <= 0:
        return False

    _businesses[loc_id]["employees"] -= 1
    return True


def get_business_info(loc_id: int) -> dict:
    return _businesses.get(loc_id, {}).copy()


def get_all_businesses() -> dict:
    return _businesses.copy()


# === 시간 경과: 수입 발생 ===

def _on_time_elapsed(millis: int):
    global _accumulated_millis
    _accumulated_millis += millis

    hours = _accumulated_millis // 3600000
    if hours < 1:
        return
    _accumulated_millis %= 3600000

    player_id = morld.get_player_id()
    if not player_id:
        return

    total_income = 0

    for loc_id, biz in _businesses.items():
        biz_type = biz["type"]
        base = BASE_INCOME.get(biz_type, 0) * hours

        # 알바생 보정
        if biz["employees"] > 0:
            base = int(base * EMPLOYEE_INCOME_MULT)

        # 평판 보정
        price_mod = reputation.get_shop_price_modifier()
        income = int(base / price_mod)  # 물가 높으면 수입도 높음

        biz["accumulated_income"] += income
        total_income += income

    if total_income > 0:
        economy.add_money(player_id, total_income)


# === 알바생 일당 지불 (매일) ===

def pay_daily_wages():
    """하�� 1회 호출: 알바생 임금 지불"""
    player_id = morld.get_player_id()
    if not player_id:
        return

    total_wages = 0
    for loc_id, biz in _businesses.items():
        wages = biz["employees"] * EMPLOYEE_COST_PER_DAY
        total_wages += wages

    if total_wages > 0:
        if economy.spend_money(player_id, total_wages):
            print(f"[business] Paid daily wages: {total_wages}원")
        else:
            # 임금 부족 → 전원 해고? 부분 해고?
            print(f"[business] Cannot pay wages: {total_wages}원! Employees leaving...")
            for loc_id, biz in _businesses.items():
                biz["employees"] = 0


subscribe_time_elapsed(_on_time_elapsed, min_interval=3600000)
