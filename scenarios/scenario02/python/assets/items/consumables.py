# assets/items/consumables.py - 소비 아이템 (약품, 보호구)
#
# 미약, 피임약, 콘돔 등 사용 시 소비되는 아이템
#
# 사용법:
#   from assets.items.consumables import Aphrodisiac, ContraceptivePill, Condom
#   pill = ContraceptivePill()
#   pill.instantiate(item_id)

import morld
import ui
from assets.base import Item
from assets.registry import register_item


# ========================================
# 피임약
# ========================================

@register_item
class ContraceptivePill(Item):
    unique_id = "contraceptive_pill"
    name = "피임약"
    category = "medicine"
    value = 20
    actions = ["take@ground", "take@container", "call:use:복용@inventory"]

    def get_focus_text(self):
        return "피임용 약이다. 복용하면 24시간 동안 효과가 지속된다."

    def use(self):
        """피임약 복용 — 24시간 피임 효과"""
        player_id = morld.get_player_id()

        # 이미 효과 중인지 확인
        remaining = morld.get_unit_prop(player_id, "상태:피임남은시간") or 0
        if remaining > 0:
            yield ui.dialog("이미 피임약 효과가 남아있다.")
            return

        # 효과 적용
        morld.set_unit_prop(player_id, "상태:피임", 1)
        morld.set_unit_prop(player_id, "상태:피임남은시간", 24)

        # 아이템 소비
        morld.lost_item(player_id, self.instance_id)

        yield ui.dialog([
            "피임약을 복용했다.",
            "24시간 동안 피임 효과가 지속된다.",
        ])


# ========================================
# 미약
# ========================================

@register_item
class Aphrodisiac(Item):
    unique_id = "aphrodisiac"
    name = "미약"
    category = "medicine"
    value = 30
    actions = ["take@ground", "take@container", "call:use:복용@inventory",
               "call:mix_food:음식에 넣기@inventory"]

    def get_focus_text(self):
        return "은밀한 약이다. 복용하면 성욕이 서서히 올라간다."

    def use(self):
        """미약 복용 — 6시간 성욕 증가 + 트랜스:외부 +30 (Phase 1.9.4)."""
        from romance_core import is_status_active, apply_timed_status
        player_id = morld.get_player_id()

        if is_status_active(player_id, "미약"):
            yield ui.dialog("이미 미약 효과가 남아있다.")
            return

        apply_timed_status(player_id, "미약")
        morld.modify_prop(player_id, "트랜스:외부", 30)

        morld.lost_item(player_id, self.instance_id)

        yield ui.dialog([
            "미약을 복용했다.",
            "몸이 달아오르는 느낌이 든다...",
        ])

    def mix_food(self):
        """음식에 미약 넣기 — 인벤토리에서 음식 선택"""
        from assets.items import get_instance as get_item_instance

        player_id = morld.get_player_id()
        inventory = morld.get_unit_inventory(player_id)
        if not inventory:
            yield ui.dialog("음식이 없다.")
            return

        # 음식 아이템만 필터링
        lines = ["미약을 넣을 음식을 선택하세요.\n"]
        found = False

        for item_id, count in inventory.items():
            item_id_int = int(item_id)
            if item_id_int == self.instance_id:
                continue
            inst = get_item_instance(item_id_int)
            if inst and hasattr(inst, 'food_satiety') and inst.food_satiety > 0:
                info = morld.get_item_info(item_id_int)
                if info:
                    found = True
                    lines.append(f"[url=@ret:{item_id_int}]{info.get('name', '음식')}[/url]")

        if not found:
            yield ui.dialog("미약을 넣을 수 있는 음식이 없다.")
            return

        lines.append(f"\n[url=@ret:cancel]취소[/url]")
        result = yield ui.dialog("\n".join(lines), autofill="off")

        if not result or result == "cancel":
            return

        food_id = int(result)
        food_info = morld.get_item_info(food_id)
        if not food_info:
            return

        # 음식에 미약 표시 (prop)
        morld.set_unit_prop(food_id, "상태:미약첨가", 1)

        # 미약 소비
        morld.lost_item(player_id, self.instance_id)

        food_name = food_info.get("name", "음식")
        yield ui.dialog(f"{food_name}에 미약을 몰래 넣었다.")


# ========================================
# 콘돔
# ========================================

@register_item
class Condom(Item):
    unique_id = "condom"
    name = "콘돔"
    category = "protection"
    value = 5
    actions = ["take@ground", "take@container", "call:puncture:구멍 뚫기@inventory"]

    def get_focus_text(self):
        is_punctured = morld.get_unit_prop(self.instance_id, "상태:구멍") == 1
        if is_punctured:
            return "콘돔이다. ...자세히 보면 작은 구멍이 뚫려 있다."
        return "콘돔이다. 사용하면 임신을 방지할 수 있다."

    def puncture(self):
        """콘돔에 구멍 뚫기 — 날카로운 도구 필요"""
        player_id = morld.get_player_id()

        # 이미 구멍 뚫렸는지 확인
        if morld.get_unit_prop(self.instance_id, "상태:구멍") == 1:
            yield ui.dialog("이미 구멍이 뚫려 있다.")
            return

        # 날카로운 도구 보유 확인
        has_sharp = False
        inventory = morld.get_unit_inventory(player_id)
        if inventory:
            from assets.items import get_instance as get_item_instance
            for item_id in inventory:
                inst = get_item_instance(int(item_id))
                if inst and getattr(inst, 'unique_id', '') in (
                    "old_knife", "kitchen_knife", "writing_tool"
                ):
                    has_sharp = True
                    break

        if not has_sharp:
            yield ui.dialog("날카로운 도구가 필요하다.")
            return

        morld.set_unit_prop(self.instance_id, "상태:구멍", 1)
        yield ui.dialog("콘돔에 눈에 띄지 않는 작은 구멍을 뚫었다.")


# ========================================
# 붕대
# ========================================

@register_item
class Bandage(Item):
    """붕대 — 출혈 치료 + HP 소량 회복"""
    unique_id = "bandage"
    name = "붕대"
    category = "medicine"
    value = 10
    actions = ["take@ground", "take@container", "call:use:사용@inventory"]

    def get_focus_text(self):
        return "간단한 상처를 감싸는 붕대다. 출혈을 멈추고 약간의 체력을 회복할 수 있다."

    def use(self):
        """붕대 사용 — 출혈 치료 + HP 10 회복"""
        import combat
        import survival

        player_id = morld.get_player_id()

        # 출혈 치료
        has_bleeding = morld.get_unit_prop(player_id, "상태:출혈")
        if has_bleeding:
            combat.cure_bleeding(player_id)
            morld.add_action_log("출혈을 멈추었다.")

        # HP 회복
        survival.add_health(player_id, 10)
        morld.add_action_log("붕대를 감았다. 체력이 약간 회복되었다.")

        # 아이템 소비
        morld.lost_item(player_id, self.instance_id)
        morld.advance_time_des(5_000)


@register_item
class Antidote(Item):
    """해독제 — 독 치료 + HP 소량 회복"""
    unique_id = "antidote"
    name = "해독제"
    category = "medicine"
    value = 15
    actions = ["take@ground", "take@container", "call:use:사용@inventory"]

    def get_focus_text(self):
        return "약초에서 추출한 해독제다. 독을 해소하고 약간의 체력을 회복할 수 있다."

    def use(self):
        """해독제 사용 — 독 치료 + HP 5 회복"""
        import combat
        import survival

        player_id = morld.get_player_id()

        has_poison = morld.get_unit_prop(player_id, "상태:독")
        if has_poison:
            combat.cure_poison(player_id)
            morld.add_action_log("독을 해소했다.")

        survival.add_health(player_id, 5)
        morld.add_action_log("해독제를 복용했다. 체력이 약간 회복되었다.")

        morld.lost_item(player_id, self.instance_id)
        morld.advance_time_des(5_000)


# ========================================
# 와인 (알코올)
# ========================================

_WINE_DRUNK_GAIN = 15    # 1잔 = 취기 +15 (약 3시간 지속, -5/h 감쇠)


@register_item
class Wine(Item):
    """와인 — 마시면 `상태:취기` 상승. 트랜스 진입 쉬워지고 정신 방어 약화.

    Phase 1.9.4: `상태:취기` 독립 축 도입. `compute_trance_level`에서
    `트랜스:외부`와 함께 external 기여. `_decay_drunk_tick` (1h -5/h).
    """
    unique_id = "wine"
    name = "와인"
    category = "drink"
    value = 15
    actions = ["take@ground", "take@container", "call:drink:마시기@inventory",
               "call:mix_food:음식에 넣기@inventory"]

    def get_focus_text(self):
        return "와인 한 병이다. 마시면 취기가 올라 경계심이 무뎌진다."

    def drink(self):
        """플레이어 본인이 와인 마시기 — 취기 +15."""
        player_id = morld.get_player_id()
        current = morld.get_unit_prop(player_id, "상태:취기") or 0
        morld.set_unit_prop(player_id, "상태:취기",
                            min(100, current + _WINE_DRUNK_GAIN))
        morld.lost_item(player_id, self.instance_id)
        yield ui.dialog([
            "와인을 마셨다.",
            "몸이 따뜻해지며 머리가 살짝 몽롱해진다...",
        ])

    def mix_food(self):
        """음식에 와인 몰래 넣기 — NPC가 먹으면 취기 가산."""
        from assets.items import get_instance as get_item_instance

        player_id = morld.get_player_id()
        inventory = morld.get_unit_inventory(player_id)
        if not inventory:
            yield ui.dialog("음식이 없다.")
            return

        lines = ["와인을 넣을 음식을 선택하세요.\n"]
        found = False
        for item_id, _count in inventory.items():
            item_id_int = int(item_id)
            if item_id_int == self.instance_id:
                continue
            inst = get_item_instance(item_id_int)
            if inst and hasattr(inst, 'food_satiety') and inst.food_satiety > 0:
                info = morld.get_item_info(item_id_int)
                if info:
                    found = True
                    lines.append(f"[url=@ret:{item_id_int}]{info.get('name', '음식')}[/url]")

        if not found:
            yield ui.dialog("와인을 넣을 수 있는 음식이 없다.")
            return

        lines.append(f"\n[url=@ret:cancel]취소[/url]")
        result = yield ui.dialog("\n".join(lines), autofill="off")
        if not result or result == "cancel":
            return

        food_id = int(result)
        food_info = morld.get_item_info(food_id)
        if not food_info:
            return

        morld.set_unit_prop(food_id, "상태:취기첨가", 1)
        morld.lost_item(player_id, self.instance_id)
        food_name = food_info.get("name", "음식")
        yield ui.dialog(f"{food_name}에 와인을 몰래 넣었다.")


# ========================================
# 독주 (강한 알코올)
# ========================================

_STRONG_LIQUOR_DRUNK_GAIN = 30


@register_item
class StrongLiquor(Item):
    """독주 — 한 번에 취기가 급격히 오름 (Wine의 2배 효과)."""
    unique_id = "strong_liquor"
    name = "독주"
    category = "drink"
    value = 30
    actions = ["take@ground", "take@container", "call:drink:마시기@inventory",
               "call:mix_food:음식에 넣기@inventory"]

    def get_focus_text(self):
        return "도수가 높은 독주다. 한 잔에 급하게 취하게 된다."

    def drink(self):
        player_id = morld.get_player_id()
        current = morld.get_unit_prop(player_id, "상태:취기") or 0
        morld.set_unit_prop(player_id, "상태:취기",
                            min(100, current + _STRONG_LIQUOR_DRUNK_GAIN))
        morld.lost_item(player_id, self.instance_id)
        yield ui.dialog([
            "독주를 단숨에 들이켰다.",
            "불덩이가 목을 타고 내려가며 머리가 핑 돈다...",
        ])

    def mix_food(self):
        from assets.items import get_instance as get_item_instance
        player_id = morld.get_player_id()
        inventory = morld.get_unit_inventory(player_id)
        if not inventory:
            yield ui.dialog("음식이 없다.")
            return
        lines = ["독주를 넣을 음식을 선택하세요.\n"]
        found = False
        for item_id, _c in inventory.items():
            item_id_int = int(item_id)
            if item_id_int == self.instance_id:
                continue
            inst = get_item_instance(item_id_int)
            if inst and hasattr(inst, 'food_satiety') and inst.food_satiety > 0:
                info = morld.get_item_info(item_id_int)
                if info:
                    found = True
                    lines.append(f"[url=@ret:{item_id_int}]{info.get('name', '음식')}[/url]")
        if not found:
            yield ui.dialog("독주를 넣을 수 있는 음식이 없다.")
            return
        lines.append(f"\n[url=@ret:cancel]취소[/url]")
        result = yield ui.dialog("\n".join(lines), autofill="off")
        if not result or result == "cancel":
            return
        food_id = int(result)
        food_info = morld.get_item_info(food_id)
        if not food_info:
            return
        morld.set_unit_prop(food_id, "상태:독주첨가", 1)
        morld.lost_item(player_id, self.instance_id)
        yield ui.dialog(f"{food_info.get('name', '음식')}에 독주를 몰래 섞었다.")


# ========================================
# 마약 (강한 정신 교란)
# ========================================

_NARCOTIC_TRANCE_GAIN = 50


@register_item
class Narcotic(Item):
    """마약 — 트랜스:외부 +50, 깊은 트랜스 직진. 저항 자동 약화 (Phase 1.9.1 페널티)."""
    unique_id = "narcotic"
    name = "마약"
    category = "medicine"
    value = 80
    actions = ["take@ground", "take@container", "call:use:복용@inventory",
               "call:mix_food:음식에 넣기@inventory"]

    def get_focus_text(self):
        return "은밀히 유통되는 강력한 약물이다. 복용하면 정신이 극도로 흐려진다."

    def use(self):
        player_id = morld.get_player_id()
        morld.modify_prop(player_id, "트랜스:외부", _NARCOTIC_TRANCE_GAIN)
        morld.lost_item(player_id, self.instance_id)
        yield ui.dialog([
            "마약을 복용했다.",
            "시야가 흐려지며 의식이 멀어져 간다...",
        ])

    def mix_food(self):
        from assets.items import get_instance as get_item_instance
        player_id = morld.get_player_id()
        inventory = morld.get_unit_inventory(player_id)
        if not inventory:
            yield ui.dialog("음식이 없다.")
            return
        lines = ["마약을 넣을 음식을 선택하세요.\n"]
        found = False
        for item_id, _c in inventory.items():
            item_id_int = int(item_id)
            if item_id_int == self.instance_id:
                continue
            inst = get_item_instance(item_id_int)
            if inst and hasattr(inst, 'food_satiety') and inst.food_satiety > 0:
                info = morld.get_item_info(item_id_int)
                if info:
                    found = True
                    lines.append(f"[url=@ret:{item_id_int}]{info.get('name', '음식')}[/url]")
        if not found:
            yield ui.dialog("마약을 넣을 수 있는 음식이 없다.")
            return
        lines.append(f"\n[url=@ret:cancel]취소[/url]")
        result = yield ui.dialog("\n".join(lines), autofill="off")
        if not result or result == "cancel":
            return
        food_id = int(result)
        food_info = morld.get_item_info(food_id)
        if not food_info:
            return
        morld.set_unit_prop(food_id, "상태:마약첨가", 1)
        morld.lost_item(player_id, self.instance_id)
        yield ui.dialog(f"{food_info.get('name', '음식')}에 마약을 몰래 섞었다.")


# ========================================
# 최면제 (정신 조작)
# ========================================

_HYPNOTIC_TRANCE_GAIN = 40


@register_item
class Hypnotic(Item):
    """최면제 — 트랜스:외부 +40, 저항 약화. 마약보다 약하지만 더 은밀."""
    unique_id = "hypnotic"
    name = "최면제"
    category = "medicine"
    value = 60
    actions = ["take@ground", "take@container", "call:use:복용@inventory",
               "call:mix_food:음식에 넣기@inventory"]

    def get_focus_text(self):
        return "정신을 조작하는 약이다. 복용하면 암시에 취약해진다."

    def use(self):
        player_id = morld.get_player_id()
        morld.modify_prop(player_id, "트랜스:외부", _HYPNOTIC_TRANCE_GAIN)
        morld.lost_item(player_id, self.instance_id)
        yield ui.dialog([
            "최면제를 복용했다.",
            "머리가 무거워지며 생각이 흐릿해진다...",
        ])

    def mix_food(self):
        from assets.items import get_instance as get_item_instance
        player_id = morld.get_player_id()
        inventory = morld.get_unit_inventory(player_id)
        if not inventory:
            yield ui.dialog("음식이 없다.")
            return
        lines = ["최면제를 넣을 음식을 선택하세요.\n"]
        found = False
        for item_id, _c in inventory.items():
            item_id_int = int(item_id)
            if item_id_int == self.instance_id:
                continue
            inst = get_item_instance(item_id_int)
            if inst and hasattr(inst, 'food_satiety') and inst.food_satiety > 0:
                info = morld.get_item_info(item_id_int)
                if info:
                    found = True
                    lines.append(f"[url=@ret:{item_id_int}]{info.get('name', '음식')}[/url]")
        if not found:
            yield ui.dialog("최면제를 넣을 수 있는 음식이 없다.")
            return
        lines.append(f"\n[url=@ret:cancel]취소[/url]")
        result = yield ui.dialog("\n".join(lines), autofill="off")
        if not result or result == "cancel":
            return
        food_id = int(result)
        food_info = morld.get_item_info(food_id)
        if not food_info:
            return
        morld.set_unit_prop(food_id, "상태:최면제첨가", 1)
        morld.lost_item(player_id, self.instance_id)
        yield ui.dialog(f"{food_info.get('name', '음식')}에 최면제를 몰래 섞었다.")
