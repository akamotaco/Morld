# assets/items/adult_toys.py - 성인용품 아이템
#
# 장비형 (착용 시스템):
#   페니스밴드, 볼개그, 니플클램프, 안대, 목줄, 결박 로프, 수갑, 채찍
#
# 삽입형 (prop 기반 추적):
#   바이브레이터, 딜도, 로터, 항문 플러그
#   - 삽입 시 캐릭터 prop "삽입물:{부위}" 에 item_id 기록
#   - 해당 오리피스의 자연 삽입 차단
#
# 소모성 (consumables.py에서 관리):
#   미약, 배란유도제, 정력제, 윤활제, 피임약
#
# 성인용품 효과 props:
#   - "성인용품:진동": N  → 절정 +N/h (needs.py에서 처리)
#   - "성인용품:자극": N  → 절정 +N/h
#   - "임시해부학:P": 1   → 임시 P anatomy 추가 (gender.py)
#   - "결박:사지": 1      → 사지 결박 (이동/행동 불가)
#   - "결박:입": 1        → 입 결박 (말하기/구강행위 차단)
#   - "결박:눈": 1        → 시각 차단 (감각 증폭)
#   - "결박:강도": N      → 해제 난이도 (높을수록 어려움)

import morld
import ui
from assets.base import Item
from assets.registry import register_item


# ========================================
# 기본 클래스
# ========================================

class AdultToyEquipment(Item):
    """착용형 성인용품 기본 클래스"""
    category = "adult_toy"
    actions = [
        "take@container",
        "equip@inventory",
        "call:look:살펴보기@inventory",
    ]

    def look(self):
        yield ui.dialog(f"{self.name}이다.")


class AdultToyInsertable(Item):
    """
    삽입형 성인용품 기본 클래스

    삽입 시 캐릭터 prop에 기록, equip 시스템과 별도.
    - insertable_orifices: 삽입 가능한 부위 목록
    - vibration_rate: 시간당 절정 증가량 (0이면 비진동)
    """
    category = "adult_toy"
    insertable_orifices = []  # 서브클래스에서 정의
    vibration_rate = 0  # 시간당 절정 증가

    actions = [
        "take@container",
        "call:insert:삽입@inventory",
        "call:look:살펴보기@inventory",
    ]

    def look(self):
        yield ui.dialog(f"{self.name}이다.")

    def insert(self):
        """삽입 — 부위 선택 후 대상 캐릭터에 삽입"""
        player_id = morld.get_player_id()

        # 삽입 부위 선택 UI
        if len(self.insertable_orifices) == 1:
            orifice = self.insertable_orifices[0]
        else:
            lines = ["삽입할 부위를 선택하세요.\n"]
            for o in self.insertable_orifices:
                lines.append(f"[url=@ret:{o}]{o}[/url]")
            lines.append(f"\n[url=@ret:cancel]취소[/url]")
            result = yield ui.dialog("\n".join(lines), autofill="off")
            if not result or result == "cancel":
                return
            orifice = result

        # 이미 해당 부위에 삽입물이 있는지 확인
        existing = morld.get_unit_prop(player_id, f"삽입물:{orifice}")
        if existing:
            yield ui.dialog(f"이미 {orifice}에 무언가가 삽입되어 있다.")
            return

        # 삽입 적용
        morld.set_unit_prop(player_id, f"삽입물:{orifice}", self.instance_id)
        yield ui.dialog(f"{self.name}을(를) {orifice}에 삽입했다.")
        morld.advance_time_des(1 * 60_000)

    def remove_insert(self):
        """삽입물 제거"""
        player_id = morld.get_player_id()

        # 어느 부위에 삽입되어 있는지 확인
        removed = False
        for orifice in self.insertable_orifices:
            item_id = morld.get_unit_prop(player_id, f"삽입물:{orifice}")
            if item_id == self.instance_id:
                morld.clear_prop(player_id, f"삽입물:{orifice}")
                removed = True
                yield ui.dialog(f"{orifice}에서 {self.name}을(를) 제거했다.")
                break

        if not removed:
            yield ui.dialog("삽입되어 있지 않다.")


class RestraintEquipment(Item):
    """
    결박 장비 기본 클래스

    장착 시 결박:사지 prop 부여 → 이동/행동 제한
    해제 난이도는 결박:강도 값에 비례
    """
    category = "restraint"
    actions = [
        "take@container",
        "equip@inventory",
        "call:look:살펴보기@inventory",
    ]

    def look(self):
        yield ui.dialog(f"{self.name}이다.")


# ========================================
# 착용형 성인용품
# ========================================

@register_item
class PenisBand(AdultToyEquipment):
    """
    페니스 밴드 — 장착 시 임시 P anatomy 추가

    V/C anatomy가 있는 캐릭터만 착용 가능.
    사정 기능은 없음 (삽입 행위만 가능).
    """
    unique_id = "penis_band"
    name = "페니스 밴드"
    equip_props = {"착용:하체장비": 1, "임시해부학:P": 1}
    value = 40

    def look(self):
        yield ui.dialog([
            "스트랩이 달린 페니스 밴드다.",
            "장착하면 삽입 행위가 가능해진다.",
        ])


@register_item
class BallGag(AdultToyEquipment):
    """
    볼개그 — 입 결박

    말하기, 구강행위, 음식 섭취, 소리치기 차단.
    """
    unique_id = "ball_gag"
    name = "볼개그"
    equip_props = {"착용:구강장비": 1, "결박:입": 1}
    value = 25

    def look(self):
        yield ui.dialog([
            "입에 물리는 결박 장비다.",
            "장착하면 말하거나 먹을 수 없게 된다.",
        ])


@register_item
class NippleClamp(AdultToyEquipment):
    """
    니플클램프 — 유두 자극

    +3 절정/h. 가슴 관련 행위 감도 증가.
    """
    unique_id = "nipple_clamp"
    name = "니플클램프"
    equip_props = {"착용:유두장비": 1, "성인용품:자극": 3}
    value = 20

    def look(self):
        yield ui.dialog([
            "유두에 끼우는 클램프다.",
            "장착하면 지속적인 자극이 가해진다.",
        ])


@register_item
class Blindfold(AdultToyEquipment):
    """
    안대 — 시각 차단

    기존 안경 슬롯 공유. 시각 차단으로 감각 증폭.
    """
    unique_id = "blindfold"
    name = "안대"
    equip_props = {"착용:안경": 1, "결박:눈": 1}
    value = 10

    def look(self):
        yield ui.dialog([
            "눈을 가리는 안대다.",
            "시각을 차단하면 다른 감각이 예민해진다.",
        ])


@register_item
class CollarLeash(AdultToyEquipment):
    """
    목줄 — 복종 효과 + describe 표현
    """
    unique_id = "collar_leash"
    name = "목줄"
    equip_props = {"착용:목장비": 1, "성인용품:목줄": 1}
    value = 30

    def look(self):
        yield ui.dialog("가죽으로 만든 목줄이다.")


# ========================================
# 결박 장비
# ========================================

@register_item
class RestraintRope(RestraintEquipment):
    """
    결박 로프 — 사지 결박 (해제 난이도 낮음)

    일반 밧줄(tools.py Rope)과 별도 아이템.
    """
    unique_id = "restraint_rope"
    name = "결박 로프"
    equip_props = {"착용:결박": 1, "결박:사지": 1, "결박:강도": 30}
    value = 15

    def look(self):
        yield ui.dialog([
            "사지를 묶기 위한 튼튼한 로프다.",
            "적당히 저항하면 풀 수 있을 것 같다.",
        ])


@register_item
class Handcuffs(RestraintEquipment):
    """
    수갑 — 사지 결박 (해제 난이도 높음)
    """
    unique_id = "handcuffs"
    name = "수갑"
    equip_props = {"착용:결박": 1, "결박:사지": 1, "결박:강도": 60}
    value = 35

    def look(self):
        yield ui.dialog([
            "금속으로 만든 수갑이다.",
            "일단 채워지면 풀기 매우 어렵다.",
        ])


# ========================================
# 삽입형 성인용품
# ========================================

@register_item
class Vibrator(AdultToyInsertable):
    """
    바이브레이터 — 진동 삽입형

    삽입 부위: 음부 또는 항문 (선택)
    진동: +10 절정/h
    해당 오리피스의 자연 삽입 차단
    """
    unique_id = "vibrator"
    name = "바이브레이터"
    insertable_orifices = ["음부", "항문"]
    vibration_rate = 10
    value = 50

    def look(self):
        yield ui.dialog([
            "진동 기능이 있는 성인용품이다.",
            "삽입하면 지속적으로 자극이 가해진다.",
        ])


@register_item
class Dildo(AdultToyInsertable):
    """
    딜도 — 정적 삽입형

    삽입 부위: 음부 또는 항문 (선택)
    정적: +3 절정/h
    해당 오리피스의 자연 삽입 차단
    """
    unique_id = "dildo"
    name = "딜도"
    insertable_orifices = ["음부", "항문"]
    vibration_rate = 3
    value = 30

    def look(self):
        yield ui.dialog("삽입형 성인용품이다.")


@register_item
class Rotor(AdultToyInsertable):
    """
    로터 — 클리토리스 진동

    삽입 부위: 클리토리스
    진동: +5 절정/h
    소형이라 삽입 비차단 (음부/항문 삽입과 병용 가능)
    """
    unique_id = "rotor"
    name = "로터"
    insertable_orifices = ["클리토리스"]
    vibration_rate = 5
    value = 25

    def look(self):
        yield ui.dialog([
            "소형 진동 기기다.",
            "클리토리스에 부착하여 사용한다.",
        ])


@register_item
class AnalPlug(AdultToyInsertable):
    """
    항문 플러그 — 항문 전용

    삽입 부위: 항문
    +3 절정/h
    항문 삽입 차단
    """
    unique_id = "anal_plug"
    name = "항문 플러그"
    insertable_orifices = ["항문"]
    vibration_rate = 3
    value = 20

    def look(self):
        yield ui.dialog("항문에 삽입하는 플러그다.")


# ========================================
# 사용 도구
# ========================================

@register_item
class Whip(Item):
    """
    채찍 — 로맨스 액션 전용 도구

    손에 장착하여 사용. 로맨스 중 채찍질 액션 가능.
    반발 증가 + 복종 증가 + 성욕 증가.
    """
    unique_id = "whip"
    name = "채찍"
    category = "adult_toy"
    equip_props = {"장착:손": 1, "성인용품:채찍": 1}
    value = 25
    actions = [
        "take@container",
        "equip@inventory",
        "call:look:살펴보기@inventory",
    ]

    def look(self):
        yield ui.dialog([
            "가죽으로 만든 채찍이다.",
            "손에 장착하면 로맨스 중 사용할 수 있다.",
        ])


# ========================================
# 소모성 성인용품
# ========================================

@register_item
class OvulationInducer(Item):
    """
    배란유도제 — 24시간 가임 확률 100%

    직접 복용 또는 음식에 섞기 가능.
    """
    unique_id = "ovulation_inducer"
    name = "배란유도제"
    category = "medicine"
    value = 40
    actions = [
        "take@ground", "take@container",
        "call:use:복용@inventory",
        "call:mix_food:음식에 넣기@inventory",
    ]

    def get_focus_text(self):
        return "복용하면 24시간 동안 배란이 유도된다."

    def use(self):
        """배란유도제 복용"""
        player_id = morld.get_player_id()

        remaining = morld.get_unit_prop(player_id, "상태:배란유도남은시간") or 0
        if remaining > 0:
            yield ui.dialog("이미 배란유도제 효과가 남아있다.")
            return

        morld.set_unit_prop(player_id, "상태:배란유도", 1)
        morld.set_unit_prop(player_id, "상태:배란유도남은시간", 24)
        morld.lost_item(player_id, self.instance_id)

        yield ui.dialog([
            "배란유도제를 복용했다.",
            "24시간 동안 가임 확률이 극대화된다.",
        ])

    def mix_food(self):
        """음식에 배란유도제 넣기"""
        yield from _mix_drug_into_food(self, "상태:배란유도제첨가", "배란유도제")


@register_item
class StaminaPotion(Item):
    """
    정력제 — 6시간 동안 절정 감소 + 성욕 증가

    절정 -5/h, 성욕 +3/h 효과.
    """
    unique_id = "stamina_potion"
    name = "정력제"
    category = "medicine"
    value = 35
    actions = [
        "take@ground", "take@container",
        "call:use:복용@inventory",
        "call:mix_food:음식에 넣기@inventory",
    ]

    def get_focus_text(self):
        return "복용하면 6시간 동안 절정을 늦추고 성욕을 높인다."

    def use(self):
        """정력제 복용"""
        player_id = morld.get_player_id()

        remaining = morld.get_unit_prop(player_id, "상태:정력제남은시간") or 0
        if remaining > 0:
            yield ui.dialog("이미 정력제 효과가 남아있다.")
            return

        morld.set_unit_prop(player_id, "상태:정력제", 1)
        morld.set_unit_prop(player_id, "상태:정력제남은시간", 6)
        morld.lost_item(player_id, self.instance_id)

        yield ui.dialog([
            "정력제를 복용했다.",
            "몸에 힘이 솟는 느낌이 든다.",
        ])

    def mix_food(self):
        """음식에 정력제 넣기"""
        yield from _mix_drug_into_food(self, "상태:정력제첨가", "정력제")


@register_item
class Lubricant(Item):
    """
    윤활제 — 즉시 삽입 준비도 충족

    사용 시 대상의 삽입 준비도를 즉시 100%로 설정.
    로맨스 중에 사용하는 것이 일반적.
    """
    unique_id = "lubricant"
    name = "윤활제"
    category = "medicine"
    value = 15
    actions = [
        "take@ground", "take@container",
        "call:use:사용@inventory",
    ]

    def get_focus_text(self):
        return "삽입 시 통증을 줄여주는 윤활제다."

    def use(self):
        """윤활제 사용 — 로맨스 세션 밖에서는 단순 소비"""
        player_id = morld.get_player_id()
        morld.lost_item(player_id, self.instance_id)
        yield ui.dialog("윤활제를 사용했다.")


# ========================================
# 공용 헬퍼
# ========================================

def _mix_drug_into_food(item_instance, prop_key, drug_name):
    """
    음식에 약물 넣기 공통 로직

    Aphrodisiac.mix_food() 패턴 재사용.
    """
    from assets.items import get_instance as get_item_instance

    player_id = morld.get_player_id()
    inventory = morld.get_unit_inventory(player_id)
    if not inventory:
        yield ui.dialog("음식이 없다.")
        return

    lines = [f"{drug_name}을(를) 넣을 음식을 선택하세요.\n"]
    found = False

    for item_id, count in inventory.items():
        item_id_int = int(item_id)
        if item_id_int == item_instance.instance_id:
            continue
        inst = get_item_instance(item_id_int)
        if inst and hasattr(inst, 'food_satiety') and inst.food_satiety > 0:
            info = morld.get_item_info(item_id_int)
            if info:
                found = True
                lines.append(f"[url=@ret:{item_id_int}]{info.get('name', '음식')}[/url]")

    if not found:
        yield ui.dialog(f"{drug_name}을(를) 넣을 수 있는 음식이 없다.")
        return

    lines.append(f"\n[url=@ret:cancel]취소[/url]")
    result = yield ui.dialog("\n".join(lines), autofill="off")

    if not result or result == "cancel":
        return

    food_id = int(result)
    food_info = morld.get_item_info(food_id)
    if not food_info:
        return

    morld.set_unit_prop(food_id, prop_key, 1)
    morld.lost_item(player_id, item_instance.instance_id)

    food_name = food_info.get("name", "음식")
    yield ui.dialog(f"{food_name}에 {drug_name}을(를) 몰래 넣었다.")


# ========================================
# 유틸리티 API
# ========================================

# 삽입물 부위 목록 (needs.py 등에서 참조)
INSERTABLE_ORIFICES = ("음부", "항문", "클리토리스")


def get_inserted_toy_info(unit_id, orifice):
    """
    특정 부위에 삽입된 성인용품 정보 반환

    Returns:
        dict {"item_id": int, "vibration_rate": int} 또는 None
    """
    from assets.items import get_instance as get_item_instance

    item_id = morld.get_unit_prop(unit_id, f"삽입물:{orifice}")
    if not item_id:
        return None

    inst = get_item_instance(int(item_id))
    if inst and isinstance(inst, AdultToyInsertable):
        return {
            "item_id": int(item_id),
            "vibration_rate": inst.vibration_rate,
        }

    return {"item_id": int(item_id), "vibration_rate": 0}


def get_total_climax_rate(unit_id):
    """
    캐릭터의 총 절정 증가율 계산 (시간당)

    삽입물 + 착용형 자극 합산.
    Returns:
        int: 시간당 절정 증가량 (양수=증가, 음수=감소)
    """
    import equipment

    rate = 0

    # 삽입물 체크
    for orifice in INSERTABLE_ORIFICES:
        info = get_inserted_toy_info(unit_id, orifice)
        if info:
            rate += info["vibration_rate"]

    # 착용형 체크 (니플클램프 등의 "성인용품:자극" prop)
    equipped = equipment.get_equipped_items(unit_id)
    for item_id in equipped:
        item_info = morld.get_item_info(item_id)
        if item_info:
            ep = item_info.get("equip_props", {})
            stim = ep.get("성인용품:자극", 0)
            if stim > 0:
                rate += stim

    return rate


def has_any_insertable(unit_id):
    """캐릭터에 삽입물이 하나라도 있는지 확인"""
    for orifice in INSERTABLE_ORIFICES:
        if morld.get_unit_prop(unit_id, f"삽입물:{orifice}"):
            return True
    return False


def clear_all_insertables(unit_id):
    """캐릭터의 모든 삽입물 제거 (결박 해제 등에서 사용)"""
    for orifice in INSERTABLE_ORIFICES:
        if morld.get_unit_prop(unit_id, f"삽입물:{orifice}"):
            morld.clear_prop(unit_id, f"삽입물:{orifice}")
