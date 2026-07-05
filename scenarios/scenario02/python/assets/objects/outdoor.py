# assets/objects/outdoor.py - 실외 오브젝트
#
# OOP call: 패턴 적용
# - actions: ["call:메서드명:표시명"] 형식
# - 각 클래스가 인스턴스 메서드로 동작 구현
#
# 사용법:
#   from assets.objects.outdoor import GardenBench
#   bench = GardenBench()
#   loc.add_object(bench, instance_id)

import morld
import ui
from assets.base import Object


# ========================================
# 앞마당 오브젝트
# ========================================

class GardenBench(Object):
    unique_id = "garden_bench"
    name = "정원 벤치"
    actions = ["call:sit:앉기", "call:debug_props:(디버그) 속성 보기#"]
    props = {
        "posture": "sit",
        "posture_slots": 2,
        "seated_by:left": -1,
        "seated_by:right": -1,
        "cover:level": 1,  # COVER_PARTIAL
    }
    focus_text = {"default": "정원에 놓인 나무 벤치. 앉아서 쉴 수 있다."}


class Well(Object):
    unique_id = "well"
    name = "우물"
    actions = ["call:look:들여다보기", "call:draw:물 길어올리기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "돌로 쌓아 만든 우물. 맑은 물이 고여 있다."}

    def look(self):
        """우물 들여다보기"""
        yield ui.dialog([
            "우물 안을 들여다봤다.",
            "맑은 물이 깊은 곳에서 반짝인다."
        ])
        morld.advance_time_des(1 * 60_000)

    def draw(self):
        """물 길어올리기"""
        yield ui.dialog([
            "두레박으로 물을 길어올렸다.",
            "시원하고 맑은 물이다."
        ])
        morld.advance_time_des(5 * 60_000)


# ========================================
# 뒷마당 오브젝트
# ========================================

class DryingRack(Object):
    unique_id = "drying_rack"
    name = "빨래 건조대"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "뒷마당에 놓인 빨래 건조대. 가끔 빨래가 널려 있다."}

    def look(self):
        """빨래 건조대 살펴보기"""
        yield ui.dialog([
            "빨래 건조대다.",
            "빨래가 마르면 걷어야 할 것 같다."
        ])
        morld.advance_time_des(1 * 60_000)


# ========================================
# 도시/거리 오브젝트
# ========================================

class StreetBench(Object):
    unique_id = "street_bench"
    name = "벤치"
    actions = ["call:sit:앉기", "call:debug_props:(디버그) 속성 보기#"]
    props = {
        "posture": "sit",
        "posture_slots": 3,
        "seated_by:left": -1,
        "seated_by:center": -1,
        "seated_by:right": -1,
        "cover:level": 1,  # COVER_PARTIAL
    }
    focus_text = {"default": "거리에 놓인 낡은 벤치. 앉아서 쉴 수 있다."}


# ========================================
# 강가 오브젝트
# ========================================

class FishingSpot(Object):
    """
    낚시터 - can:fish 필요 (낚시대 장착)

    props 기반 자원 관리:
    - "자원:물고기": 현재 어획 가능 물고기 수
    - OnTimeElapsed 이벤트로 자동 보충 (resource_agent)

    플레이어가 낚시대를 장착하면 can:fish가 부여되고,
    이 오브젝트의 "낚시" 액션이 표시됨.
    """
    unique_id = "fishing_spot"
    name = "낚시터"
    actions = ["call:look:살펴보기", "call:fish:낚시", "call:debug_props:(디버그) 속성 보기#"]

    # 자원 설정 (prop 기반, Tree 패턴)
    max_fish = 5
    initial_fish = 4
    fish_chance = 0.7    # 70%

    def instantiate(self, instance_id: int, region_id: int = None, location_id: int = None):
        """낚시터 인스턴스화 - 초기 자원 설정 및 resource_agent 등록"""
        super().instantiate(instance_id, region_id, location_id)
        self.set_fish_count(self.initial_fish)
        from think.resource_agent import register_fishing_spot
        register_fishing_spot(instance_id, self.unique_id)

    def get_fish_count(self) -> int:
        """현재 물고기 수 (props에서 조회)"""
        if not self._instantiated:
            return 0
        props = morld.get_unit_props(self.instance_id)
        return props.get("자원:물고기", 0)

    def set_fish_count(self, count: int):
        """물고기 수 설정"""
        morld.set_unit_prop(self.instance_id, "자원:물고기",
                            max(0, min(count, self.max_fish)))

    def can_fish(self) -> bool:
        """낚시 가능 여부 (물고기 남아있는지)"""
        return self.get_fish_count() > 0

    def has_resource(self) -> bool:
        """통일 리소스 체크 인터페이스"""
        return self.can_fish()

    def get_focus_text(self):
        """현재 상태에 따른 묘사"""
        count = self.get_fish_count()
        if count >= 4:
            return "물이 깊고 잔잔한 곳. 물고기가 많이 보인다."
        elif count > 0:
            return f"낚시터. 물고기가 좀 보인다. ({count}마리 정도)"
        else:
            return "낚시터. 물고기가 보이지 않는다. 시간이 지나면 돌아올 것이다."

    def look(self):
        """낚시터 살펴보기"""
        count = self.get_fish_count()
        if count >= 4:
            lines = ["물이 깊고 잔잔한 곳이다.", "물고기가 많이 보인다."]
        elif count > 0:
            lines = ["낚시터다.", f"물고기가 {count}마리 정도 보인다."]
        else:
            lines = ["낚시터다.", "물고기가 보이지 않는다. 시간이 지나면 돌아올 것이다."]
        lines.append("낚시대를 장착하면 낚시를 할 수 있다.")
        yield ui.dialog(lines)
        morld.advance_time_des(1 * 60_000)

    def fish(self, equipment=None):
        """
        낚시하기 - can:fish가 있어야 실행 가능

        자원 체크 + 확률 기반 생선 획득

        Args:
            equipment: 낚시에 사용된 장비 정보
                       {"item_id": int, "unique_id": str, "name": str} 또는 None
        """
        import random
        from assets.registry import get_item_class

        # 자원 체크
        if not self.can_fish():
            yield ui.dialog([
                "한참을 기다렸지만...",
                "물고기가 보이지 않는다. 다른 곳을 찾아보자."
            ])
            return

        # 장비에 따라 다른 낚시 메시지
        if equipment:
            equip_id = equipment.get("unique_id", "")
            if equip_id == "fishing_rod":
                yield ui.dialog("낚싯줄을 드리운다...")
            else:
                yield ui.dialog(f"{equipment.get('name', '도구')}(으)로 낚시를 시작한다...")
        else:
            yield ui.dialog("맨손으로 물고기를 잡아본다...")
        morld.advance_time_des(15 * 60_000)  # 15분 소요

        # 확률 기반 성공
        if random.random() < self.fish_chance:
            player_id = morld.get_player_id()

            # 기존 생선 아이템 ID 조회 (스택을 위해)
            fish_id = morld.get_item_id_by_unique("food_fish")

            # 기존 아이템이 없으면 새로 생성
            if fish_id is None:
                fish_class = get_item_class("food_fish")
                if fish_class:
                    fish = fish_class()
                    fish_id = morld.create_id("item")
                    fish.instantiate(fish_id)
                else:
                    yield ui.dialog("물고기를 잡았지만, 놓쳐버렸다.")
                    return

            import inventory as inv_module
            inv_module.safe_give_item(player_id, fish_id, 1)
            self.set_fish_count(self.get_fish_count() - 1)
            yield ui.dialog([
                "물고기를 잡았다!",
                "신선한 생선이다."
            ])
        else:
            yield ui.dialog([
                "한참을 기다렸지만...",
                "아무것도 잡히지 않았다."
            ])

    def npc_fish(self, npc_id):
        """NPC 낚시 — 자원 체크 + 확률 + 차감"""
        if not self.can_fish():
            return False
        import random
        from assets.registry import get_or_create_item_id
        if random.random() < self.fish_chance:
            item_id = get_or_create_item_id("food_fish")
            if item_id:
                import inventory as inv_module
                inv_module.safe_give_item(npc_id, item_id, 1)
                self.set_fish_count(self.get_fish_count() - 1)
                return True
        return False


# ========================================
# 자판기
# ========================================

class VendingMachine(Object):
    """
    음료 자판기 — 코인으로 음료 구매

    재고 관리: props 기반 (FishingSpot 패턴)
      "상점:재고:{unique_id}" — 각 아이템별 현재 재고
      "상점:리젠"            — 1=리젠 ON, 0=OFF

    리젠: resource_agent에 등록, 시간 경과마다 재고 보충
    """
    unique_id = "working_vending_machine"
    name = "음료 자판기"

    # 카탈로그: {unique_id: (표시명, 가격_코인, 최대재고)}
    CATALOG = {
        "drink_water":         ("생수",          3, 5),
        "drink_canned_cola":   ("캔 콜라",       5, 4),
        "drink_canned_coffee": ("캔 커피",       5, 4),
        "drink_green_tea":     ("녹차",          4, 3),
        "drink_sports":        ("스포츠 음료",   6, 3),
        "drink_energy":        ("에너지 드링크", 8, 3),
    }

    actions = [
        "call:look:살펴보기",
        "call:buy:구매",
        "call:debug_props:(디버그) 속성 보기#",
    ]

    def instantiate(self, instance_id: int, region_id: int = None, location_id: int = None):
        super().instantiate(instance_id, region_id, location_id)

        # 초기 재고 설정 (이미 설정된 경우 유지)
        # 실 API 계약: 부재 시 0 — is None 판정이면 초기화가 영원히 실행되지 않아
        # 재고/리젠이 항상 0. 1회 초기화 여부는 마커 prop으로 판정.
        if not morld.get_unit_prop(instance_id, "상점:초기화"):
            for uid, (_, _, max_stock) in self.CATALOG.items():
                morld.set_unit_prop(instance_id, f"상점:재고:{uid}", max_stock)
            # 리젠 기본값 ON
            morld.set_unit_prop(instance_id, "상점:리젠", 1)
            morld.set_unit_prop(instance_id, "상점:초기화", 1)

        # resource_agent에 등록
        from think.resource_agent import register_vending_machine
        register_vending_machine(instance_id, self.unique_id)

    # ── 재고 조회/설정 ──

    def get_stock(self, uid: str) -> int:
        if not self._instantiated:
            return 0
        return morld.get_unit_prop(self.instance_id, f"상점:재고:{uid}") or 0

    def set_stock(self, uid: str, count: int):
        max_stock = self.CATALOG[uid][2]
        morld.set_unit_prop(self.instance_id, f"상점:재고:{uid}",
                            max(0, min(count, max_stock)))

    def get_focus_text(self):
        available = []
        for uid, (name, price, _) in self.CATALOG.items():
            if self.get_stock(uid) > 0:
                available.append(f"{name}({price}코인)")
        if available:
            return f"음료 자판기. {', '.join(available)} 구매 가능."
        return "음료 자판기. 재고가 없다."

    # ── 액션 ──

    def look(self):
        """자판기 재고 목록 표시"""
        lines = ["[음료 자판기 재고]"]
        for uid, (name, price, _) in self.CATALOG.items():
            stock = self.get_stock(uid)
            if stock > 0:
                lines.append(f"· {name} — {price}코인  (재고: {stock})")
            else:
                lines.append(f"· {name} — 품절")
        yield ui.dialog(lines)
        morld.advance_time_des(1 * 60_000)

    def buy(self):
        """음료 구매 — 코인 차감 후 아이템 지급"""
        player_id = morld.get_player_id()
        coins = self._get_coin_count(player_id)

        lines = [f"보유 코인: {coins}개\n구매할 음료를 선택하세요.\n"]
        for uid, (name, price, _) in self.CATALOG.items():
            stock = self.get_stock(uid)
            if stock <= 0:
                lines.append(f"{name} — 품절")
            elif coins >= price:
                lines.append(f"[url=@ret:{uid}]{name} — {price}코인 (재고: {stock})[/url]")
            else:
                lines.append(f"{name} — {price}코인 (코인 부족)")
        lines.append(f"\n[url=@ret:cancel]취소[/url]")

        result = yield ui.dialog("\n".join(lines), autofill="off")
        if not result or result == "cancel":
            return

        uid = result
        if uid not in self.CATALOG:
            return

        name, price, _ = self.CATALOG[uid]
        stock = self.get_stock(uid)

        if stock <= 0:
            yield ui.dialog(f"{name}의 재고가 없다.")
            return
        if coins < price:
            yield ui.dialog(f"코인이 부족하다. ({coins}/{price})")
            return

        # 코인 차감
        if not self._remove_coins(player_id, price):
            yield ui.dialog("코인 차감에 실패했다.")
            return

        # 재고 차감 + 아이템 지급
        self.set_stock(uid, stock - 1)
        from assets.registry import get_or_create_item_id
        item_id = get_or_create_item_id(uid)
        if item_id:
            import inventory as inv_module
            inv_module.safe_give_item(player_id, item_id, 1)
            yield ui.dialog(f"{name}을(를) 구매했다. (코인: {coins - price}개 남음)")
        else:
            # 아이템 ID 없으면 코인 환불
            self._give_coins(player_id, price)
            yield ui.dialog("오류: 아이템을 찾을 수 없다.")

        morld.advance_time_des(30_000)

    # ── 코인 헬퍼 ──

    def _get_coin_count(self, unit_id: int) -> int:
        inventory = morld.get_unit_inventory(unit_id)
        if not inventory:
            return 0
        total = 0
        for item_id, count in inventory.items():
            info = morld.get_item_info(item_id)
            if info and info.get("unique_id") == "coin":
                total += count
        return total

    def _remove_coins(self, unit_id: int, amount: int) -> bool:
        inventory = morld.get_unit_inventory(unit_id)
        if not inventory:
            return False
        remaining = amount
        for item_id, count in list(inventory.items()):
            info = morld.get_item_info(item_id)
            if info and info.get("unique_id") == "coin":
                take = min(count, remaining)
                morld.remove_item(unit_id, int(item_id), take)
                remaining -= take
                if remaining <= 0:
                    break
        return remaining == 0

    def _give_coins(self, unit_id: int, amount: int):
        from assets.registry import get_or_create_item_id
        coin_id = get_or_create_item_id("coin")
        if coin_id:
            import inventory as inv_module
            inv_module.safe_give_item(unit_id, coin_id, amount)
