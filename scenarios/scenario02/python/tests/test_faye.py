# test_faye.py — 페이(Faye) 상인 NPC 단위 테스트
#
# 검증 대상:
# 1. 요일 계산 로직 (_get_day_of_week, _get_absolute_day)
# 2. 스케줄 결정 로직 (_get_active_schedule)
# 3. 거래 아이템 리셋 (_reset_trade_items)
#
# 주의: 스케줄 로직은 faye.py의 import chain 없이 알고리즘만 검증.
#       _reset_trade_items는 morld mock을 통해 검증.

import sys
import os
import types

# ============================================
# 1. 경로 설정
# ============================================

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))

if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

# ============================================
# 2. morld mock (run_tests.py가 이미 주입)
# ============================================

import morld

# ============================================
# 3. 스케줄 로직 인라인 정의
#    (faye.py 에서 복사 — import chain 없이 알고리즘만 독립 검증)
# ============================================

_SCHEDULE = [
    {"days": {0, 1, 2}, "region_id": 2, "location_id": 0},  # 월/화/수: 도시 입구
    {"days": {3, 4},    "region_id": 3, "location_id": 5},  # 목/금: 숲 오두막
    # 토(5)/일(6): 없음 → None 반환
]

_WORK_START = 8 * 60   # 08:00 (분 단위)
_WORK_END   = 20 * 60  # 20:00 (분 단위)


def _dow(ti):
    """time_info dict → 요일 (0=월, ..., 6=일)"""
    year  = ti.get("year",  1)
    month = ti.get("month", 1)
    day   = ti.get("day",   1)
    return ((year - 1) * 365 + (month - 1) * 30 + (day - 1)) % 7


def _abs_day(ti):
    """time_info dict → 절대 날 수 (리셋 판정용)"""
    year  = ti.get("year",  1)
    month = ti.get("month", 1)
    day   = ti.get("day",   1)
    return (year - 1) * 365 + (month - 1) * 30 + (day - 1)


def _active_sched(ti):
    """현재 시간에 활성 스케줄 → 없으면 None"""
    minutes = ti.get("hour", 0) * 60 + ti.get("minute", 0)
    if minutes < _WORK_START or minutes >= _WORK_END:
        return None
    dow = _dow(ti)
    for entry in _SCHEDULE:
        if dow in entry["days"]:
            return entry
    return None


# ============================================
# 4. assets.registry stub — _reset_trade_items용
# ============================================

if "assets.registry" not in sys.modules:
    _registry_stub = types.ModuleType("assets.registry")
    _registry_items = {}
    _registry_counter = [3000]

    def _get_or_create(uid):
        if uid not in _registry_items:
            _registry_counter[0] += 1
            _registry_items[uid] = _registry_counter[0]
        return _registry_items[uid]

    _registry_stub.get_or_create_item_id = _get_or_create
    sys.modules["assets.registry"] = _registry_stub
else:
    # 이미 있으면 내부 dict 참조 (리셋용)
    _registry_items = getattr(sys.modules["assets.registry"], "_items", {})


# ============================================
# 5. _reset_trade_items 인라인 정의
#    faye.py의 _reset_trade_items 로직을 morld mock으로 검증
# ============================================

TRADE_STOCK = [
    ("seed_potato",        2, 15),
    ("seed_tomato",        2, 15),
    ("seed_carrot",        2, 15),
    ("seed_herb",          2, 20),
    ("seed_cabbage",       2, 15),
    ("seed_sweet_potato",  1, 20),
    ("seed_corn",          1, 20),
    ("seed_garlic",        1, 25),
    ("seed_onion",         1, 15),
    ("seed_pumpkin",       1, 20),
    ("condom",             3, 15),
    ("contraceptive_pill", 2, 25),
    ("aphrodisiac",        1, 50),
    ("lubricant",          2, 15),
    ("stamina_potion",     1, 40),
    ("ovulation_inducer",  1, 50),
    ("vibrator",           1, 65),
    ("dildo",              1, 40),
    ("rotor",              1, 30),
    ("anal_plug",          1, 25),
    ("nipple_clamp",       1, 25),
    ("blindfold",          1, 15),
    ("simple_water_bottle", 2, 10),
]

_TRADE_PRICES = {uid: price for uid, _count, price in TRADE_STOCK}


def _reset_trade_items_local(unit_id):
    """faye.py:_reset_trade_items 로직 — morld mock으로 검증"""
    max_hp = morld.get_unit_prop(unit_id, "생존:최대체력") or 100
    morld.set_unit_prop(unit_id, "생존:체력", max_hp)

    inventory = morld.get_unit_inventory(unit_id) or {}
    for item_id, count in list(inventory.items()):
        morld.remove_item(unit_id, int(item_id), count)

    from assets.registry import get_or_create_item_id
    for unique_id, count, _price in TRADE_STOCK:
        item_id = get_or_create_item_id(unique_id)
        if item_id:
            morld.give_item(unit_id, item_id, count)


# ============================================
# TestDayOfWeek: 요일 계산 검증
# ============================================

class TestDayOfWeek:
    def _ti(self, year=1, month=1, day=1, hour=12, minute=0):
        return {"year": year, "month": month, "day": day,
                "hour": hour, "minute": minute}

    def test_game_start_is_monday(self):
        """게임 시작일(1년 4월 2일)은 월요일(0)
        계산: (1-1)*365 + (4-1)*30 + (2-1) = 91; 91 % 7 = 0"""
        assert _dow({"year": 1, "month": 4, "day": 2}) == 0

    def test_weekday_sequence(self):
        """1년 4월 2~8일 = 월~일 (0~6)"""
        for i in range(7):
            ti = {"year": 1, "month": 4, "day": 2 + i}
            got = _dow(ti)
            assert got == i, f"day={2 + i}: expected {i}, got {got}"

    def test_next_week_monday(self):
        """7일 후(day=9) → 다시 월요일(0)"""
        assert _dow({"year": 1, "month": 4, "day": 9}) == 0

    def test_default_values(self):
        """빈 dict → 기본값(1년 1월 1일) → 0 (월요일)"""
        assert _dow({}) == 0

    def test_month_boundary(self):
        """달 경계: 1월 31일 → 2월 1일이 1일 차이"""
        d1 = _abs_day({"year": 1, "month": 1, "day": 30})
        d2 = _abs_day({"year": 1, "month": 2, "day": 1})
        # 30일짜리 달 가정: (1-1)*30 + (30-1) = 29, (2-1)*30 + (1-1) = 30
        assert d2 - d1 == 1

    def test_absolute_day_origin(self):
        """1년 1월 1일 → 절대 날 0"""
        assert _abs_day({"year": 1, "month": 1, "day": 1}) == 0

    def test_absolute_day_game_start(self):
        """게임 시작일(1년 4월 2일) → 절대 날 91"""
        assert _abs_day({"year": 1, "month": 4, "day": 2}) == 91

    def test_absolute_day_year2(self):
        """2년 1월 1일 → 절대 날 365"""
        assert _abs_day({"year": 2, "month": 1, "day": 1}) == 365

    def test_absolute_day_increments(self):
        """연속 날짜의 절대 날 차이 = 1"""
        d1 = _abs_day({"year": 1, "month": 3, "day": 15})
        d2 = _abs_day({"year": 1, "month": 3, "day": 16})
        assert d2 - d1 == 1


# ============================================
# TestSchedule: 스케줄 결정 검증
# ============================================

class TestSchedule:
    def _ti(self, day=2, hour=12, minute=0):
        """1년 4월 N일 HH:MM (day=2 → 월요일)"""
        return {"year": 1, "month": 4, "day": day,
                "hour": hour, "minute": minute}

    # ── 활성 케이스 ──

    def test_monday_active_city(self):
        """월요일(day=2) 12:00 → 도시(R2, L0)"""
        s = _active_sched(self._ti(day=2))
        assert s is not None
        assert s["region_id"] == 2
        assert s["location_id"] == 0

    def test_tuesday_active_city(self):
        """화요일(day=3) 10:00 → 도시"""
        s = _active_sched(self._ti(day=3, hour=10))
        assert s is not None and s["region_id"] == 2

    def test_wednesday_active_city(self):
        """수요일(day=4) → 도시"""
        s = _active_sched(self._ti(day=4))
        assert s is not None and s["region_id"] == 2

    def test_thursday_active_forest(self):
        """목요일(day=5) 14:00 → 숲 오두막(R3, L5)"""
        s = _active_sched(self._ti(day=5, hour=14))
        assert s is not None
        assert s["region_id"] == 3
        assert s["location_id"] == 5

    def test_friday_active_forest(self):
        """금요일(day=6) 09:00 → 숲 오두막"""
        s = _active_sched(self._ti(day=6, hour=9))
        assert s is not None and s["region_id"] == 3

    # ── 비활성 케이스 ──

    def test_saturday_inactive(self):
        """토요일(day=7) → None (주말)"""
        assert _active_sched(self._ti(day=7)) is None

    def test_sunday_inactive(self):
        """일요일(day=8) → None"""
        assert _active_sched(self._ti(day=8)) is None

    def test_before_work_start(self):
        """07:59 → None (출근 전)"""
        assert _active_sched(self._ti(day=2, hour=7, minute=59)) is None

    def test_work_start_inclusive(self):
        """08:00 정각 → 활성"""
        assert _active_sched(self._ti(day=2, hour=8, minute=0)) is not None

    def test_work_end_exclusive(self):
        """20:00 → None (퇴근)"""
        assert _active_sched(self._ti(day=2, hour=20, minute=0)) is None

    def test_last_minute_active(self):
        """19:59 → 활성"""
        assert _active_sched(self._ti(day=2, hour=19, minute=59)) is not None

    def test_midnight_inactive(self):
        """00:00 → None (야간)"""
        assert _active_sched(self._ti(day=2, hour=0)) is None

    def test_day_off_overrides_work_hours(self):
        """주말은 업무 시간 내에도 None"""
        assert _active_sched(self._ti(day=7, hour=10)) is None
        assert _active_sched(self._ti(day=8, hour=15)) is None


# ============================================
# TestTradeStock: TRADE_STOCK 무결성
# ============================================

class TestTradeStock:
    def test_stock_count(self):
        """총 23종 품목"""
        assert len(TRADE_STOCK) == 23

    def test_no_duplicate_items(self):
        """unique_id 중복 없음"""
        uids = [uid for uid, _, _ in TRADE_STOCK]
        assert len(uids) == len(set(uids)), "중복된 아이템 ID 발견"

    def test_positive_prices(self):
        """모든 가격 > 0"""
        for uid, count, price in TRADE_STOCK:
            assert price > 0, f"{uid}: 가격={price} (0 이하)"

    def test_positive_counts(self):
        """모든 수량 > 0"""
        for uid, count, price in TRADE_STOCK:
            assert count > 0, f"{uid}: 수량={count} (0 이하)"

    def test_price_lookup(self):
        """_TRADE_PRICES 딕셔너리 조회 — TRADE_STOCK과 일치"""
        for uid, _count, price in TRADE_STOCK:
            assert _TRADE_PRICES.get(uid) == price, \
                f"{uid}: TRADE_PRICES={_TRADE_PRICES.get(uid)}, expected={price}"

    def test_seeds_present(self):
        """씨앗류 10종 포함"""
        uids = {uid for uid, _, _ in TRADE_STOCK}
        seed_ids = {
            "seed_potato", "seed_tomato", "seed_carrot", "seed_herb",
            "seed_cabbage", "seed_sweet_potato", "seed_corn",
            "seed_garlic", "seed_onion", "seed_pumpkin",
        }
        missing = seed_ids - uids
        assert not missing, f"씨앗 누락: {missing}"

    def test_adult_items_present(self):
        """성인용품 핵심 품목 포함"""
        uids = {uid for uid, _, _ in TRADE_STOCK}
        required = {"condom", "contraceptive_pill", "aphrodisiac", "vibrator"}
        missing = required - uids
        assert not missing, f"성인용품 누락: {missing}"


# ============================================
# TestResetTradeItems: 거래 아이템 리셋 검증
# ============================================

class TestResetTradeItems:
    def setUp(self):
        self.faye_id = 500
        morld.register_unit(
            self.faye_id,
            name="페이",
            props={"생존:최대체력": 80, "생존:체력": 30},
        )
        # 기존 아이템 (리셋 후 사라져야 함)
        morld.add_to_inventory(self.faye_id, 9999, 5)

    def test_hp_restored_to_max(self):
        """리셋 후 HP = 최대체력(80)"""
        _reset_trade_items_local(self.faye_id)
        hp = morld.get_unit_prop(self.faye_id, "생존:체력")
        assert hp == 80, f"HP should be 80, got {hp}"

    def test_old_items_cleared(self):
        """기존 아이템(9999) 제거됨"""
        _reset_trade_items_local(self.faye_id)
        inv = morld.get_unit_inventory(self.faye_id)
        assert 9999 not in inv, "기존 아이템이 제거되어야 함"

    def test_trade_items_given(self):
        """TRADE_STOCK 아이템 지급됨 (인벤토리 비어있지 않음)"""
        _reset_trade_items_local(self.faye_id)
        inv = morld.get_unit_inventory(self.faye_id)
        assert len(inv) > 0, "거래 아이템이 지급되어야 함"

    def test_trade_item_count_matches_stock(self):
        """지급된 아이템 종류 = TRADE_STOCK 품목 수"""
        _reset_trade_items_local(self.faye_id)
        inv = morld.get_unit_inventory(self.faye_id)
        assert len(inv) == len(TRADE_STOCK), \
            f"expected {len(TRADE_STOCK)} items, got {len(inv)}"

    def test_default_max_hp_fallback(self):
        """최대체력 prop 없으면 100으로 회복"""
        morld.register_unit(501, name="페이2", props={"생존:체력": 10})
        _reset_trade_items_local(501)
        hp = morld.get_unit_prop(501, "생존:체력")
        assert hp == 100, f"기본 최대체력 100 사용해야 함, got {hp}"

    def test_reset_twice_no_duplication(self):
        """두 번 리셋해도 아이템 수 동일 (누적 없음)"""
        _reset_trade_items_local(self.faye_id)
        count_1 = len(morld.get_unit_inventory(self.faye_id))
        _reset_trade_items_local(self.faye_id)
        count_2 = len(morld.get_unit_inventory(self.faye_id))
        assert count_1 == count_2, \
            f"두 번째 리셋 후 아이템 수 달라짐: {count_1} → {count_2}"
