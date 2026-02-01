# assets/objects/furniture.py - 실내 가구 오브젝트
#
# OOP call: 패턴 적용
# - actions: ["call:메서드명:표시명"] 형식
# - 각 클래스가 인스턴스 메서드로 동작 구현
#
# 사용법:
#   from assets.objects.furniture import Fireplace
#   fireplace = Fireplace()
#   loc.add_object(fireplace, instance_id)

import morld
import ui
from assets.base import Object


# ========================================
# 거실 오브젝트
# ========================================

class Fireplace(Object):
    unique_id = "fireplace"
    name = "벽난로"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {
        "default": "돌로 만들어진 오래된 벽난로. 저녁이면 불이 피워진다.",
        "저녁": "따뜻한 불꽃이 타오르고 있다.",
        "밤": "잔잔한 불씨가 남아 있다."
    }

    def look(self):
        """벽난로 살펴보기"""
        yield ui.dialog([
            "돌로 쌓아 만든 오래된 벽난로다.",
            "저녁이 되면 따뜻한 불이 피워진다."
        ])
        morld.advance_time(1 * 60_000)


class OldSofa(Object):
    unique_id = "old_sofa"
    name = "낡은 소파"
    actions = ["call:sit:앉기", "call:debug_props:(디버그) 속성 보기#"]
    props = {
        "posture": "sit",
        "posture_slots": 1,
        "seated_by:seat": -1,
    }
    focus_text = {"default": "오래 사용해서 닳았지만 여전히 푹신한 소파."}


class LivingSofa(Object):
    """
    앉을 수 있는 거실 소파 (3인용)
    """
    unique_id = "living_sofa"
    name = "거실 소파"
    actions = [
        "call:sit:앉기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    props = {
        "posture": "sit",
        "posture_slots": 3,
        "seated_by:left": -1,
        "seated_by:center": -1,
        "seated_by:right": -1,
    }
    focus_text = {"default": "푹신하고 넓은 거실 소파. 편하게 앉아 쉴 수 있다."}


class Bookshelf(Object):
    unique_id = "bookshelf"
    name = "책장"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "벽면을 따라 놓인 큰 책장. 다양한 책이 꽂혀 있다."}

    def look(self):
        """책장 살펴보기"""
        yield ui.dialog([
            "다양한 책이 꽂혀 있다.",
            "소설, 역사서, 요리책... 장르가 다양하다."
        ])
        morld.advance_time(2 * 60_000)


# ========================================
# 식당 오브젝트
# ========================================

class DiningTable(Object):
    unique_id = "dining_table"
    name = "긴 식탁"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "여섯 명이 앉을 수 있는 긴 나무 식탁. 잘 닦여 있다."}

    def look(self):
        """식탁 살펴보기"""
        yield ui.dialog([
            "잘 닦인 긴 나무 식탁이다.",
            "여섯 개의 의자가 가지런히 놓여 있다."
        ])
        morld.advance_time(1 * 60_000)


class DiningChair(Object):
    """
    앉을 수 있는 식탁 의자 (4인용)
    """
    unique_id = "dining_chair"
    name = "식탁 의자"
    actions = [
        "call:sit:앉기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    props = {
        "posture": "sit",
        "posture_slots": 4,
        "seated_by:1": -1,
        "seated_by:2": -1,
        "seated_by:3": -1,
        "seated_by:4": -1,
    }
    focus_text = {"default": "식탁 주변에 놓인 나무 의자들. 앉아서 식사할 수 있다."}


# ========================================
# 주방 오브젝트
# ========================================

class Stove(Object):
    """
    조리 가능한 아궁이

    컨테이너 패턴 + 조리 기능:
    - open: 재료 넣기/빼기 (인벤토리 조회)
    - cook: 레시피 매칭 후 조리
    - put_filter: food_ingredient 카테고리 아이템만 넣을 수 있음
    """
    unique_id = "stove"
    name = "아궁이"
    put_filter = ["food_ingredient"]  # 음식 재료만 넣을 수 있음
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:put:재료 넣기",
        "call:cook:조리하기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "요리에 사용하는 큰 아궁이. 항상 따뜻하다."}

    def look(self):
        """아궁이 살펴보기"""
        yield ui.dialog([
            "요리에 사용하는 큰 아궁이다.",
            "항상 따뜻한 열기가 느껴진다."
        ])
        morld.advance_time(1 * 60_000)

    def cook(self):
        """조리 실행 - 결과물은 플레이어 인벤토리로 바로 지급"""
        from recipes import find_matching_recipe, RECIPES
        from assets.registry import get_item_class

        player_id = morld.get_player_id()

        # 현재 재료 확인
        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            yield ui.dialog("재료가 없다.")
            return

        # unique_id 기반으로 변환
        inv_uniques = {}
        for item_id, count in inventory.items():
            info = morld.get_item_info(item_id)
            unique_id = info.get("unique_id")
            if unique_id:
                inv_uniques[unique_id] = inv_uniques.get(unique_id, 0) + count

        # 레시피 매칭
        result = find_matching_recipe(inv_uniques)
        if not result:
            yield ui.dialog("이 재료로는 만들 수 있는 것이 없다.")
            return

        recipe_id, recipe, max_count = result

        # 재료 소비 (item_id 찾아서 소비)
        for unique_id, needed in recipe["ingredients"].items():
            consumed = 0
            for item_id, count in list(inventory.items()):
                info = morld.get_item_info(item_id)
                if info.get("unique_id") == unique_id and consumed < needed:
                    to_consume = min(count, needed - consumed)
                    morld.lost_item(self.instance_id, item_id, to_consume)
                    consumed += to_consume

        # 결과물 생성 → 플레이어 인벤토리로 바로 지급
        result_unique, result_count = recipe["result"]
        result_id = morld.get_item_id_by_unique(result_unique)

        if result_id is None:
            item_class = get_item_class(result_unique)
            if item_class:
                result_item = item_class()
                result_id = morld.create_id("item")
                result_item.instantiate(result_id)

        if result_id:
            morld.give_item(player_id, result_id, result_count)

        # 시간 경과 및 메시지
        yield ui.dialog(f"{recipe['name']}을(를) 만들었다!")
        morld.advance_time(recipe["cook_time"] * 60_000)


class Kettle(Object):
    """
    음료 제조용 주전자

    컨테이너 패턴 + 음료 제조 기능:
    - open: 재료 넣기/빼기 (인벤토리 조회)
    - brew: 레시피 매칭 후 음료 제조
    - put_filter: drink_ingredient 카테고리 아이템만 넣을 수 있음
    """
    unique_id = "kettle"
    name = "주전자"
    put_filter = ["drink_ingredient"]  # 음료 재료만 넣을 수 있음
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:put:재료 넣기",
        "call:brew:끓이기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "물을 끓이거나 차를 우릴 수 있는 주전자."}

    def look(self):
        """주전자 살펴보기"""
        yield ui.dialog([
            "물을 끓이거나 차를 우릴 수 있는 주전자다.",
            "아궁이 위에 올려두면 사용할 수 있다."
        ])
        morld.advance_time(1 * 60_000)

    def brew(self):
        """음료 제조 - 결과물은 플레이어 인벤토리로 바로 지급"""
        from recipes import find_matching_recipe, RECIPES
        from assets.registry import get_item_class

        player_id = morld.get_player_id()

        # 현재 재료 확인
        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            yield ui.dialog("재료가 없다.")
            return

        # unique_id 기반으로 변환
        inv_uniques = {}
        for item_id, count in inventory.items():
            info = morld.get_item_info(item_id)
            unique_id = info.get("unique_id")
            if unique_id:
                inv_uniques[unique_id] = inv_uniques.get(unique_id, 0) + count

        # 레시피 매칭
        result = find_matching_recipe(inv_uniques)
        if not result:
            yield ui.dialog("이 재료로는 만들 수 있는 것이 없다.")
            return

        recipe_id, recipe, max_count = result

        # 재료 소비 (item_id 찾아서 소비)
        for unique_id, needed in recipe["ingredients"].items():
            consumed = 0
            for item_id, count in list(inventory.items()):
                info = morld.get_item_info(item_id)
                if info.get("unique_id") == unique_id and consumed < needed:
                    to_consume = min(count, needed - consumed)
                    morld.lost_item(self.instance_id, item_id, to_consume)
                    consumed += to_consume

        # 결과물 생성 → 플레이어 인벤토리로 바로 지급
        result_unique, result_count = recipe["result"]
        result_id = morld.get_item_id_by_unique(result_unique)

        if result_id is None:
            item_class = get_item_class(result_unique)
            if item_class:
                result_item = item_class()
                result_id = morld.create_id("item")
                result_item.instantiate(result_id)

        if result_id:
            morld.give_item(player_id, result_id, result_count)

        # 시간 경과 및 메시지
        yield ui.dialog(f"{recipe['name']}을(를) 만들었다!")
        morld.advance_time(recipe["cook_time"] * 60_000)


class Cupboard(Object):
    unique_id = "cupboard"
    name = "찬장"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "그릇과 조리도구가 정리된 찬장."}

    def look(self):
        """찬장 살펴보기"""
        yield ui.dialog(["그릇과 조리도구가 깔끔하게 정리되어 있다."])
        morld.advance_time(1 * 60_000)


# ========================================
# 욕실 오브젝트
# ========================================

class Bathtub(Object):
    unique_id = "bathtub"
    name = "나무 욕조"
    actions = ["call:use:목욕하기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "큰 나무 욕조. 따뜻한 물을 받아 목욕할 수 있다."}

    def use(self):
        """목욕하기"""
        yield ui.dialog([
            "따뜻한 물을 받아 목욕했다.",
            "몸이 개운해졌다."
        ])
        morld.advance_time(30 * 60_000)


class Washbasin(Object):
    unique_id = "washbasin"
    name = "세면대"
    actions = ["call:use:세수하기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "도자기로 만든 세면대. 깨끗하게 관리되어 있다."}

    def use(self):
        """세수하기"""
        yield ui.dialog([
            "시원한 물로 얼굴을 씻었다.",
            "정신이 맑아졌다."
        ])
        morld.advance_time(5 * 60_000)


# ========================================
# 창고 오브젝트
# ========================================

class CraftingTable(Object):
    """
    제작대 - 복잡한 아이템 제작 가능

    crafting_recipes.py의 workbench=True 레시피 사용
    """
    unique_id = "crafting_table"
    name = "제작대"
    actions = ["call:look:살펴보기", "call:craft:제작하기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "도구와 재료를 다룰 수 있는 튼튼한 작업대."}

    def look(self):
        """제작대 살펴보기"""
        yield ui.dialog([
            "튼튼한 나무로 만든 작업대다.",
            "복잡한 물건을 제작할 수 있다."
        ])
        morld.advance_time(1 * 60_000)

    def craft(self):
        """제작대에서 제작하기"""
        from crafting_recipes import get_workbench_recipes
        from crafting import open_craft_menu
        yield from open_craft_menu(get_workbench_recipes(), "제작대")


# ========================================
# 소형 가구
# ========================================

class WoodenStool(Object):
    unique_id = "wooden_stool"
    name = "나무 의자"
    actions = ["call:sit:앉기", "call:debug_props:(디버그) 속성 보기#"]
    props = {
        "posture": "sit",
        "posture_slots": 1,
        "seated_by:seat": -1,
    }
    focus_text = {"default": "튼튼한 나무 의자. 앉아서 쉴 수 있다."}


# ========================================
# 침실 오브젝트 (주인공 방)
# ========================================

class Bed(Object):
    unique_id = "bed"
    name = "침대"
    actions = ["call:lie_down:눕기", "call:sleep:잠자기", "call:debug_props:(디버그) 속성 보기#"]
    props = {
        "posture": "lie",
        "posture_slots": 2,
        "seated_by:left": -1,
        "seated_by:right": -1,
    }
    focus_text = {"default": "작지만 편안해 보이는 침대. 깨끗한 이불이 깔려 있다."}

    def _find_owner_unit(self, region_id, location_id, owner_unique):
        """방 주인 캐릭터가 같은 Location에 있으면 unit_id 반환"""
        unit_ids = morld.get_units_at_location(region_id, location_id)
        for uid in unit_ids:
            info = morld.get_unit_info(uid)
            if info and info.get("unique_id") == owner_unique:
                return uid
        return None

    def _get_affection(self, owner_id, player_id):
        """캐릭터의 플레이어에 대한 호감도 조회"""
        owner_props = morld.get_unit_props(owner_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공")
        return owner_props.get(f"관계:{player_name}:호감", 0)

    def _is_sleeping_on_this_bed(self, owner_id):
        """주인이 이 침대에 누워있는지 확인 (seated_by 슬롯에 owner_id가 있으면 수면 중)"""
        seated_by = morld.get_unit_props_by_type(self.instance_id, "seated_by")
        for slot_name, occupant_id in seated_by.items():
            if occupant_id == owner_id:
                return True
        return False

    def lie_down(self):
        """눕기 - 방 주인이 있으면 캐릭터별 반응"""
        player_id = morld.get_player_id()

        # 빈 슬롯 확인
        slot = self._find_empty_slot()
        if slot is None:
            yield ui.dialog(["자리가 없다."])
            return

        # 방 주인 확인
        player_info = morld.get_unit_info(player_id)
        region_id = player_info["region_id"]
        location_id = player_info["location_id"]
        loc_info = morld.get_location_info(region_id, location_id)
        owner_unique = loc_info.get("owner") if loc_info else None

        # 주인공 방이거나 공용 방이면 → 침대 자체의 소유자 확인
        if not owner_unique or owner_unique == "player":
            # 침대 인스턴스에 owner_unique가 설정된 경우 (공유 공간용)
            bed_owner = getattr(self, 'bed_owner', None)
            if bed_owner:
                owner_unique = bed_owner
            else:
                success = morld.sit_on(player_id, self.instance_id, slot)
                if success:
                    yield ui.dialog([f"{self.name}에 누웠다."])
                return

        # 방 주인이 같은 방에 있는지 확인
        owner_id = self._find_owner_unit(region_id, location_id, owner_unique)

        if owner_id is None:
            # 주인 부재 - 그냥 눕기
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([f"{self.name}에 몰래 누웠다."])
            return

        # 주인이 이 침대에서 자고 있는지 확인
        owner_sleeping = self._is_sleeping_on_this_bed(owner_id)
        affection = self._get_affection(owner_id, player_id)

        if owner_unique == "sera":
            if owner_sleeping:
                yield from self._sera_bed_sleeping(player_id, slot, affection, owner_id)
            else:
                yield from self._sera_bed_event(player_id, slot, affection, region_id, owner_id)
        elif owner_unique == "mila":
            if owner_sleeping:
                yield from self._mila_bed_sleeping(player_id, slot, affection, owner_id)
            else:
                yield from self._mila_bed_event(player_id, slot, affection, region_id, owner_id)
        elif owner_unique == "lina":
            if owner_sleeping:
                yield from self._lina_bed_sleeping(player_id, slot, affection, owner_id)
            else:
                yield from self._lina_bed_event(player_id, slot, affection, region_id, owner_id)
        elif owner_unique == "yuki":
            if owner_sleeping:
                yield from self._yuki_bed_sleeping(player_id, slot, affection, owner_id)
            else:
                yield from self._yuki_bed_event(player_id, slot, affection, region_id, owner_id)
        elif owner_unique == "ella":
            if owner_sleeping:
                yield from self._ella_bed_sleeping(player_id, slot, affection, owner_id)
            else:
                yield from self._ella_bed_event(player_id, slot, affection, region_id, owner_id)
        else:
            # 기타 캐릭터 - 기본 반응
            owner_info = morld.get_unit_info(owner_id)
            owner_name = owner_info.get("name", "누군가") if owner_info else "누군가"
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                if owner_sleeping:
                    yield ui.dialog([
                        f"{owner_name}(이)가 자고 있다.",
                        "조심스럽게 옆에 누웠다."
                    ])
                else:
                    yield ui.dialog([f"{self.name}에 누웠다."])

    def _sera_bed_event(self, player_id, slot, affection, region_id, owner_id):
        """
        세라 방 침대 반응
        - 호감도 무관하게 내쫓지 않음 (눕는 것 자체는 허용)
        - 호감도 낮을 때 만지면 쫓아냄
        """
        success = False
        if affection >= 50:
            yield ui.dialog([
                "[세라]",
                "...뭐해."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "세라의 침대에 누웠다.",
                    "세라가 별 말 없이 자리를 내줬다."
                ])
        elif affection >= 20:
            yield ui.dialog([
                "[세라]",
                "......",
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "세라의 침대에 누웠다.",
                    "(세라가 아무 말 없이 비켜줬다.)"
                ])
        else:
            yield ui.dialog([
                "[세라]",
                "...마음대로 해.",
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "세라의 침대에 누웠다.",
                    "(세라가 무관심하게 고개를 돌렸다.)"
                ])

        if success:
            yield from self._sera_awake_touch(player_id, affection, region_id, owner_id)

    def _mila_bed_event(self, player_id, slot, affection, region_id, owner_id):
        """
        밀라 방 침대 반응
        - 호감도 50 이상: 허용 + 행동 선택
        - 호감도 50 미만: 강제 퇴출 (반복 가능)
        """
        if affection >= 50:
            yield ui.dialog([
                "[밀라]",
                "어머, 피곤해? 잠깐 누워도 돼~"
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "밀라의 침대에 누웠다.",
                    "은은한 꽃향기가 난다."
                ])
                yield from self._mila_awake_touch(player_id, affection, region_id, owner_id)
        else:
            # 강제 퇴출 이벤트
            yield ui.dialog([
                "[밀라]",
                "...뭐 하는 거야?"
            ])
            yield ui.dialog([
                "[밀라]",
                "남의 침대에 함부로 눕는 건 좀 아니지 않아?",
                "나가줘."
            ])
            # 거실로 강제 이동 (밀라 방은 1층 → 거실 location 1)
            morld.set_unit_location(player_id, region_id, 1, 120)
            yield ui.dialog(["밀라에게 쫓겨나 거실로 나왔다..."])

    def _mila_awake_touch(self, player_id, affection, region_id, owner_id):
        """밀라가 깨어있을 때 행동 선택지 (호감 50+ 전용)"""
        choice = yield ui.dialog(
            self._build_awake_choices(affection),
            autofill="off"
        )

        if choice == "nothing" or not choice:
            return

        # 스킨십 모드 진입
        if choice == "romance":
            from romance import start_romance
            yield from start_romance(player_id, owner_id)
            return

        if affection >= 80:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 밀라의 가슴에 살짝 닿았다."])
                yield ui.dialog([
                    "[밀라]",
                    "앗...! 뭐, 뭐야~",
                    "...갑자기 그러면 놀라잖아."
                ])
                yield ui.dialog([
                    "밀라가 얼굴을 붉히면서도...",
                    "손을 치우지는 않았다."
                ])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 밀라의 엉덩이에 살짝 닿았다."])
                yield ui.dialog([
                    "[밀라]",
                    "까악! 어디 만지는 거야!",
                    "...진짜 나쁜 사람이네."
                ])
                yield ui.dialog([
                    "밀라가 이불로 얼굴을 가렸다.",
                    "...하지만 화난 것 같지는 않다."
                ])
            elif choice == "kiss":
                yield ui.dialog(["밀라의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[밀라]",
                    "...어...?",
                    "......"
                ])
                yield ui.dialog(["밀라의 입술에 가볍게 키스했다."])
                yield ui.dialog([
                    "밀라가 눈을 감았다.",
                    "얼굴이 새빨갛다.",
                    "\"...바보.\""
                ])
            elif choice == "hug":
                yield ui.dialog(["밀라를 부드럽게 안아줬다."])
                yield ui.dialog([
                    "[밀라]",
                    "...에헤헤.",
                    "갑자기 왜 이래~"
                ])
                yield ui.dialog([
                    "밀라가 행복하게 안겨왔다.",
                    "따뜻하고 포근한 체온이 느껴진다."
                ])
        else:
            # 호감 50~79 - 당황하지만 허용
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 밀라의 가슴에 닿으려는 순간—"])
                yield ui.dialog([
                    "[밀라]",
                    "...!! 뭐, 뭐 하는 거야!?"
                ])
                yield ui.dialog([
                    "밀라가 얼굴을 붉히며 손을 쳐냈다.",
                    "\"그런 건 아직... 이르다고!\""
                ])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 밀라의 엉덩이에 닿으려는 순간—"])
                yield ui.dialog([
                    "[밀라]",
                    "어딜 만져!?",
                    "이 사람 진짜...!"
                ])
                yield ui.dialog([
                    "밀라가 화를 내면서도 쫓아내지는 않았다.",
                    "...다행이다."
                ])
            elif choice == "kiss":
                yield ui.dialog(["밀라의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[밀라]",
                    "으, 응...? 갑자기 왜...?"
                ])
                yield ui.dialog([
                    "밀라가 당황해서 눈을 질끈 감았다.",
                    "...이마에 가볍게 키스했다."
                ])
                yield ui.dialog([
                    "[밀라]",
                    "...바, 바보!! 놀라잖아!!"
                ])
            elif choice == "hug":
                yield ui.dialog(["밀라를 살짝 안아줬다."])
                yield ui.dialog([
                    "[밀라]",
                    "엇, 갑자기...!",
                    "...뭐야, 좀 부끄럽잖아."
                ])
                yield ui.dialog([
                    "밀라가 어색하게 웃으며 안겼다.",
                    "심장 소리가 빠르게 뛰는 게 느껴진다."
                ])

    def _lina_bed_event(self, player_id, slot, affection, region_id, owner_id):
        """
        리나 방 침대 반응
        - 호감도에 따라 반응만 달라짐 (내쫓지는 않음)
        """
        success = False
        if affection >= 50:
            yield ui.dialog([
                "[리나]",
                "에헤헤, 오빠도 누울래?"
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "리나의 침대에 누웠다.",
                    "리나가 환하게 웃었다."
                ])
        elif affection >= 20:
            yield ui.dialog([
                "[리나]",
                "어... 오빠? 내 침대에...?"
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "리나의 침대에 누웠다.",
                    "(리나가 어색하게 웃으며 비켜줬다.)"
                ])
        else:
            yield ui.dialog([
                "[리나]",
                "아, 네... 괜찮아요.",
                "(리나가 조금 긴장한 표정으로 비켜섰다.)"
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["리나의 침대에 누웠다."])

        if success:
            yield from self._lina_awake_touch(player_id, affection, region_id, owner_id)

    def _lina_awake_touch(self, player_id, affection, region_id, owner_id):
        """리나가 깨어있을 때 행동 선택지"""
        choice = yield ui.dialog(
            self._build_awake_choices(affection),
            autofill="off"
        )

        if choice == "nothing" or not choice:
            return

        # 스킨십 모드 진입 (호감 50+)
        if choice == "romance":
            from romance import start_romance
            yield from start_romance(player_id, owner_id)
            return

        if affection >= 50:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 리나의 가슴에 살짝 닿았다."])
                yield ui.dialog([
                    "[리나]",
                    "히잇...! 오, 오빠...!?",
                    "거, 거기는...!"
                ])
                yield ui.dialog([
                    "리나가 새빨개진 얼굴로 이불을 끌어당겼다.",
                    "...하지만 오빠의 손을 밀어내지는 않았다."
                ])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 리나의 엉덩이에 살짝 닿았다."])
                yield ui.dialog([
                    "[리나]",
                    "으앗...! 오빠 변태...!",
                    "...그래도 싫지는... 않아."
                ])
                yield ui.dialog([
                    "리나가 얼굴을 이불에 파묻었다.",
                    "귀까지 빨갛다."
                ])
            elif choice == "kiss":
                yield ui.dialog(["리나의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[리나]",
                    "오, 오빠...? 왜 그렇게 가까이..."
                ])
                yield ui.dialog(["리나의 이마에 가볍게 키스했다."])
                yield ui.dialog([
                    "[리나]",
                    "...!!",
                    "...에헤헤... 오빠..."
                ])
                yield ui.dialog([
                    "리나가 행복하게 눈을 감았다."
                ])
            elif choice == "hug":
                yield ui.dialog(["리나를 부드럽게 안아줬다."])
                yield ui.dialog([
                    "[리나]",
                    "...!",
                    "에헤헤... 오빠 따뜻해."
                ])
                yield ui.dialog([
                    "리나가 작은 몸을 꼭 안겨왔다.",
                    "심장 소리가 들린다."
                ])
        elif affection >= 20:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 리나의 가슴에 닿으려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "으잇!? 오, 오빠...!?",
                    "그, 그건 좀...!"
                ])
                yield ui.dialog([
                    "리나가 당황해서 이불로 몸을 감쌌다.",
                    "...아직은 이르다."
                ])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 리나의 엉덩이에 닿으려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "엇, 오빠!?",
                    "그, 그런 건 안 돼요...!"
                ])
                yield ui.dialog(["리나가 후다닥 이불 속으로 들어갔다."])
            elif choice == "kiss":
                yield ui.dialog(["리나의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[리나]",
                    "으...! 가, 가까워...!",
                    "아직 마음의 준비가..."
                ])
                yield ui.dialog(["리나가 새빨갛게 달아올라 고개를 숙였다."])
            elif choice == "hug":
                yield ui.dialog(["리나를 살짝 안으려 했다."])
                yield ui.dialog([
                    "[리나]",
                    "어...! 오빠...?",
                    "...어색하지만... 싫지는 않아요."
                ])
                yield ui.dialog(["리나가 뻣뻣하게 안겨 있다."])
        else:
            # 호감도 낮을 때 - 놀라서 거부 (쫓아내지는 않음)
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 리나의 가슴에 닿으려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "...!!! 저, 저기...!",
                    "그, 그런 건... 안 돼요..."
                ])
                yield ui.dialog(["리나가 겁먹은 표정으로 몸을 움츠렸다."])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 리나의 엉덩이에 닿으려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "히잇...!",
                    "제, 제발 그러지 마세요..."
                ])
                yield ui.dialog(["리나가 떨리는 목소리로 부탁했다."])
            elif choice == "kiss":
                yield ui.dialog(["리나의 얼굴에 가까이 다가가려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "으...! 너무 가까워요...!"
                ])
                yield ui.dialog(["리나가 얼굴을 가리며 뒤로 물러났다."])
            elif choice == "hug":
                yield ui.dialog(["리나를 안으려 했지만—"])
                yield ui.dialog([
                    "[리나]",
                    "어...! 저, 저는... 괜찮아요..."
                ])
                yield ui.dialog([
                    "리나가 긴장한 표정으로 살짝 몸을 피했다.",
                    "...아직은 친해지는 게 먼저인 것 같다."
                ])

    def _yuki_bed_event(self, player_id, slot, affection, region_id, owner_id):
        """
        유키 침대 반응
        - 호감도 무관하게 내쫓지 않음 (너무 소심해서 거부 못함)
        - 호감도에 따라 반응만 달라짐
        """
        success = False
        if affection >= 50:
            yield ui.dialog([
                "[유키]",
                "...어...? 같이... 누울 거예요...?"
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "유키의 침대에 누웠다.",
                    "유키가 조용히 자리를 내줬다."
                ])
        elif affection >= 20:
            yield ui.dialog([
                "[유키]",
                "...저기... 그건...",
                "...네... 괜찮아요..."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "유키의 침대에 누웠다.",
                    "(유키가 움츠리며 구석으로 비켜줬다.)"
                ])
        else:
            yield ui.dialog([
                "[유키]",
                "...!",
                "...저... 그... 네..."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "유키의 침대에 누웠다.",
                    "(유키가 겁먹은 표정으로 몸을 웅크렸다.)"
                ])

        if success:
            yield from self._yuki_awake_touch(player_id, affection, region_id, owner_id)

    def _yuki_awake_touch(self, player_id, affection, region_id, owner_id):
        """유키가 깨어있을 때 행동 선택지"""
        choice = yield ui.dialog(
            self._build_awake_choices(affection),
            autofill="off"
        )

        if choice == "nothing" or not choice:
            return

        if choice == "romance":
            from romance import start_romance
            yield from start_romance(player_id, owner_id)
            return

        if affection >= 50:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 유키의 가슴에 살짝 닿았다."])
                yield ui.dialog([
                    "[유키]",
                    "...!!",
                    "...저, 저기... 그건..."
                ])
                yield ui.dialog([
                    "유키가 새빨개진 얼굴로 눈을 감았다.",
                    "...하지만 밀어내지는 않았다."
                ])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 유키의 엉덩이에 살짝 닿았다."])
                yield ui.dialog([
                    "[유키]",
                    "히잇...!",
                    "...저... 그, 거기는..."
                ])
                yield ui.dialog([
                    "유키가 몸을 떨며 이불을 꽉 잡았다.",
                    "...거부하지는 못하는 것 같다."
                ])
            elif choice == "kiss":
                yield ui.dialog(["유키의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[유키]",
                    "...어...? 가, 가까..."
                ])
                yield ui.dialog(["유키의 이마에 가볍게 키스했다."])
                yield ui.dialog([
                    "유키가 얼굴을 붉히며 눈을 감았다.",
                    "\"...고마워요...\""
                ])
            elif choice == "hug":
                yield ui.dialog(["유키를 부드럽게 안아줬다."])
                yield ui.dialog([
                    "[유키]",
                    "...!",
                    "...따뜻해요..."
                ])
                yield ui.dialog([
                    "유키가 처음엔 몸을 굳혔지만...",
                    "이내 조심스럽게 안겨왔다."
                ])
        elif affection >= 20:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 유키의 가슴에 닿으려는 순간—"])
                yield ui.dialog([
                    "[유키]",
                    "...!!! 저, 저기...!",
                    "그건... 좀..."
                ])
                yield ui.dialog(["유키가 겁먹은 눈으로 이불을 끌어당겼다."])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 유키의 엉덩이에 닿으려는 순간—"])
                yield ui.dialog([
                    "[유키]",
                    "히...!",
                    "...안 돼요..."
                ])
                yield ui.dialog(["유키가 떨리는 목소리로 거부했다."])
            elif choice == "kiss":
                yield ui.dialog(["유키의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[유키]",
                    "...너무 가까워요...",
                    "...아직..."
                ])
                yield ui.dialog(["유키가 얼굴을 숙이며 뒤로 물러났다."])
            elif choice == "hug":
                yield ui.dialog(["유키를 안으려 했다."])
                yield ui.dialog([
                    "[유키]",
                    "...어...!",
                    "...저... 좀 놀랐어요..."
                ])
                yield ui.dialog(["유키가 뻣뻣하게 굳어 있다."])
        else:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 유키의 가슴에 닿으려는 순간—"])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 유키의 엉덩이에 닿으려는 순간—"])
            elif choice == "kiss":
                yield ui.dialog(["유키의 얼굴에 가까이 다가가려는 순간—"])
            elif choice == "hug":
                yield ui.dialog(["유키를 안으려는 순간—"])
            yield ui.dialog([
                "[유키]",
                "...! ...하지 마세요...!",
                "(유키가 몸을 웅크리며 떨기 시작했다.)"
            ])
            yield ui.dialog([
                "...너무 겁을 먹은 것 같다.",
                "그만두는 게 좋겠다."
            ])

    def _ella_bed_event(self, player_id, slot, affection, region_id, owner_id):
        """
        엘라 침대 반응
        - 호감도 50 이상: 허용 (날카롭지만)
        - 호감도 50 미만: 강제 퇴출
        """
        if affection >= 50:
            yield ui.dialog([
                "[엘라]",
                "...뭐 하는 거지?",
                "...좋아. 잠깐만이야."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "엘라의 침대에 누웠다.",
                    "은은한 가죽 냄새가 난다."
                ])
                yield from self._ella_awake_touch(player_id, affection, region_id, owner_id)
        else:
            yield ui.dialog([
                "[엘라]",
                "...뭐 하는 거야."
            ])
            yield ui.dialog([
                "[엘라]",
                "내 침대에 함부로 눕지 마.",
                "나가."
            ])
            # 약국으로 강제 이동 (은신처 → 약국 location 3, x=180)
            morld.set_unit_location(player_id, region_id, 3, 180)
            yield ui.dialog(["엘라에게 쫓겨나 약국으로 나왔다..."])

    def _ella_awake_touch(self, player_id, affection, region_id, owner_id):
        """엘라가 깨어있을 때 행동 선택지 (호감 50+ 전용)"""
        choice = yield ui.dialog(
            self._build_awake_choices(affection),
            autofill="off"
        )

        if choice == "nothing" or not choice:
            return

        if choice == "romance":
            from romance import start_romance
            yield from start_romance(player_id, owner_id)
            return

        if affection >= 80:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 엘라의 가슴에 살짝 닿았다."])
                yield ui.dialog([
                    "[엘라]",
                    "...!",
                    "...대담하군."
                ])
                yield ui.dialog([
                    "엘라가 눈을 가늘게 떴지만...",
                    "손을 치우지는 않았다."
                ])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 엘라의 엉덩이에 살짝 닿았다."])
                yield ui.dialog([
                    "[엘라]",
                    "......",
                    "...한 번만 더 하면 팔을 분지르겠어."
                ])
                yield ui.dialog([
                    "엘라가 날카롭게 경고했다.",
                    "...하지만 진심은 아닌 것 같다."
                ])
            elif choice == "kiss":
                yield ui.dialog(["엘라의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[엘라]",
                    "...뭐야."
                ])
                yield ui.dialog(["엘라의 입술에 가볍게 키스했다."])
                yield ui.dialog([
                    "엘라가 잠시 굳었다가...",
                    "조용히 눈을 감았다.",
                    "\"...바보.\""
                ])
            elif choice == "hug":
                yield ui.dialog(["엘라를 조용히 안아줬다."])
                yield ui.dialog([
                    "[엘라]",
                    "......",
                    "...뭐야. 갑자기."
                ])
                yield ui.dialog([
                    "엘라가 잠시 뻣뻣하게 있더니...",
                    "살짝 몸을 기댔다.",
                    "\"...잠깐만.\""
                ])
        else:
            # 호감 50~79
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 엘라의 가슴에 닿으려는 순간—"])
                yield ui.dialog([
                    "[엘라]",
                    "...건드리면 죽어."
                ])
                yield ui.dialog(["엘라의 눈빛이 진심이다. 손을 거뒀다."])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 엘라의 엉덩이에 닿으려는 순간—"])
                yield ui.dialog([
                    "[엘라]",
                    "...손. 치워."
                ])
                yield ui.dialog(["엘라가 차갑게 경고했다."])
            elif choice == "kiss":
                yield ui.dialog(["엘라의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[엘라]",
                    "...가까이 오지 마.",
                    "아직 그럴 사이 아니야."
                ])
                yield ui.dialog(["엘라가 고개를 돌렸다."])
            elif choice == "hug":
                yield ui.dialog(["엘라를 안으려 했지만—"])
                yield ui.dialog([
                    "[엘라]",
                    "...만지지 마.",
                    "아직은 안 돼."
                ])
                yield ui.dialog(["엘라가 거리를 뒀다."])

    # ========================================
    # 깨어있을 때 행동 선택지
    # ========================================

    def _build_awake_choices(self, affection):
        """깨어있을 때 행동 선택지 구성"""
        lines = "...\n\n"
        lines += "[url=@ret:breast]가슴 만지기[/url]\n"
        lines += "[url=@ret:butt]엉덩이 만지기[/url]\n"
        lines += "[url=@ret:kiss]키스하기[/url]\n"
        lines += "[url=@ret:hug]안아주기[/url]\n"
        if affection >= 50:
            lines += "[url=@ret:romance]스킨십[/url]\n"
        lines += "[url=@ret:nothing]가만히 있기[/url]"
        return lines

    def _sera_awake_touch(self, player_id, affection, region_id, owner_id):
        """세라가 깨어있을 때 행동 선택지"""
        choice = yield ui.dialog(
            self._build_awake_choices(affection),
            autofill="off"
        )

        if choice == "nothing" or not choice:
            return

        # 스킨십 모드 진입 (호감 50+)
        if choice == "romance":
            from romance import start_romance
            yield from start_romance(player_id, owner_id)
            return

        if affection >= 50:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 세라의 가슴에 살짝 닿았다."])
                yield ui.dialog([
                    "[세라]",
                    "...!",
                    "...뭐 하는 거야."
                ])
                yield ui.dialog([
                    "세라가 고개를 돌렸다.",
                    "귀끝이 살짝 붉어져 있다."
                ])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 세라의 엉덩이에 살짝 닿았다."])
                yield ui.dialog([
                    "[세라]",
                    "......!",
                    "...한 번만 더 하면 죽어."
                ])
                yield ui.dialog([
                    "세라가 이불을 끌어당기며 등을 돌렸다.",
                    "...하지만 내쫓지는 않았다."
                ])
            elif choice == "kiss":
                yield ui.dialog(["세라의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[세라]",
                    "...뭐야."
                ])
                yield ui.dialog(["세라의 입술에 가볍게 키스했다."])
                yield ui.dialog([
                    "세라가 눈을 피했다.",
                    "...하지만 피하지는 않았다.",
                    "귀끝까지 붉어져 있다."
                ])
            elif choice == "hug":
                yield ui.dialog(["세라를 조용히 안아줬다."])
                yield ui.dialog([
                    "[세라]",
                    "......",
                    "...뭐냐."
                ])
                yield ui.dialog([
                    "세라가 뻣뻣하게 있다가...",
                    "살짝 몸을 기댔다."
                ])
        elif affection >= 20:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 세라의 가슴에 닿으려는 순간—"])
                yield ui.dialog(["[세라]", "...건드리지 마."])
                yield ui.dialog(["세라의 차가운 눈빛에 손을 거뒀다."])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 세라의 엉덩이에 닿으려는 순간—"])
                yield ui.dialog(["[세라]", "...손 치워."])
                yield ui.dialog(["세라가 날카롭게 경고했다."])
            elif choice == "kiss":
                yield ui.dialog(["세라의 얼굴에 가까이 다가갔다."])
                yield ui.dialog(["[세라]", "...가까이 오지 마."])
                yield ui.dialog(["세라가 차갑게 고개를 돌렸다."])
            elif choice == "hug":
                yield ui.dialog(["세라를 안으려 했지만—"])
                yield ui.dialog(["[세라]", "......만지지 마."])
                yield ui.dialog(["세라가 몸을 비켜 거리를 뒀다."])
        else:
            # 호감도 낮으면 강제 퇴출
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 세라의 가슴에 닿으려는 순간—"])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 세라의 엉덩이에 닿으려는 순간—"])
            elif choice == "kiss":
                yield ui.dialog(["세라의 얼굴에 가까이 다가가려는 순간—"])
            elif choice == "hug":
                yield ui.dialog(["세라를 안으려는 순간—"])
            yield ui.dialog([
                "[세라]",
                "...나가."
            ])
            yield ui.dialog([
                "세라가 조용히, 하지만 단호하게 말했다.",
                "눈빛이 얼음장같다."
            ])
            # 2층 복도로 강제 이동 (세라 방은 2층 → 2층 복도 location 14)
            morld.set_unit_location(player_id, region_id, 14, 60)
            yield ui.dialog(["세라에게 쫓겨나 복도로 나왔다..."])

    # ========================================
    # 수면 중 침대 이벤트 (깨어남 없음, 반응만)
    # ========================================

    def _sera_bed_sleeping(self, player_id, slot, affection, owner_id):
        """세라가 자고 있을 때 - 호감도별 묘사"""
        success = False
        if affection >= 50:
            yield ui.dialog([
                "세라가 조용히 잠들어 있다.",
                "편안한 숨소리가 들린다."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["조심스럽게 옆에 누웠다."])
        elif affection >= 20:
            yield ui.dialog([
                "세라가 잠들어 있다.",
                "잠결에 살짝 몸을 뒤척였다."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["깨우지 않게 조심하며 옆에 누웠다."])
        else:
            yield ui.dialog([
                "세라가 잠들어 있다.",
                "...남의 침대에 눕는 건 좀 그렇지만."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["슬며시 옆자리에 누웠다."])

        if success:
            yield from self._sleeping_touch_choices("sera", affection)

    def _mila_bed_sleeping(self, player_id, slot, affection, owner_id):
        """밀라가 자고 있을 때 - 호감도 무관하게 허용 (자고 있으니 모름)"""
        success = False
        if affection >= 50:
            yield ui.dialog([
                "밀라가 새근새근 잠들어 있다.",
                "평소의 활기찬 모습과는 다른, 고요한 얼굴."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["살며시 옆에 누웠다."])
        else:
            yield ui.dialog([
                "밀라가 잠들어 있다.",
                "깨우면 큰일날 것 같다..."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "숨을 죽이며 옆에 누웠다.",
                    "(들키면 죽는다.)"
                ])

        if success:
            yield from self._sleeping_touch_choices("mila", affection)

    def _lina_bed_sleeping(self, player_id, slot, affection, owner_id):
        """리나가 자고 있을 때 - 호감도별 묘사"""
        success = False
        if affection >= 50:
            yield ui.dialog([
                "리나가 곤히 잠들어 있다.",
                "작은 체구가 이불 속에 동그랗게 말려 있다."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["조심스럽게 옆에 누웠다."])
        elif affection >= 20:
            yield ui.dialog([
                "리나가 잠들어 있다.",
                "잠꼬대를 하는 것 같다... \"음... 오빠...\""
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["깨우지 않게 살짝 옆에 누웠다."])
        else:
            yield ui.dialog([
                "리나가 잠들어 있다.",
                "...깨우면 놀라겠지."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["조용히 옆에 누웠다."])

        if success:
            yield from self._sleeping_touch_choices("lina", affection)

    # ========================================
    # 수면 중 만지기 (테스트용)
    # ========================================

    def _sleeping_touch_choices(self, owner_unique, affection):
        """수면 중 행동 선택지"""
        choice = yield ui.dialog(
            "...\n\n"
            "[url=@ret:breast]가슴 만지기[/url]\n"
            "[url=@ret:butt]엉덩이 만지기[/url]\n"
            "[url=@ret:kiss]키스하기[/url]\n"
            "[url=@ret:nothing]가만히 있기[/url]",
            autofill="off"
        )

        if choice == "nothing" or not choice:
            return

        if owner_unique == "sera":
            yield from self._sera_sleep_touch(choice, affection)
        elif owner_unique == "mila":
            yield from self._mila_sleep_touch(choice, affection)
        elif owner_unique == "lina":
            yield from self._lina_sleep_touch(choice, affection)
        elif owner_unique == "yuki":
            yield from self._yuki_sleep_touch(choice, affection)
        elif owner_unique == "ella":
            yield from self._ella_sleep_touch(choice, affection)

    def _sera_sleep_touch(self, part, affection):
        """세라 수면 중 - 행동 반응"""
        if part == "breast":
            yield ui.dialog([
                "손을 뻗어 세라의 가슴에 살짝 닿았다.",
                "...부드럽다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "세라가 잠결에 가볍게 몸을 뒤척였다.",
                    "\"...음...\"",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "세라가 살짝 미간을 찌푸렸다.",
                    "...위험하다. 그만두는 게 좋겠다."
                ])
        elif part == "butt":
            yield ui.dialog([
                "손을 뻗어 세라의 엉덩이에 살짝 닿았다.",
                "...탄력이 있다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "세라가 살짝 몸을 움츠렸다.",
                    "\"...ん...\"",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "세라가 잠결에 손을 쳐냈다.",
                    "...심장이 쿵 내려앉았다."
                ])
        elif part == "kiss":
            yield ui.dialog(["세라의 얼굴에 가까이 다가갔다."])
            if affection >= 50:
                yield ui.dialog([
                    "잠든 세라의 입술에 살짝 키스했다.",
                    "세라의 입술이 부드럽게 떨렸다."
                ])
                yield ui.dialog([
                    "\"...음...\"",
                    "세라가 잠결에 살짝 미소 짓는 것 같다.",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "잠든 세라의 이마에 가볍게 키스했다.",
                    "세라의 눈꺼풀이 파르르 떨렸다."
                ])
                yield ui.dialog(["...깨기 전에 그만두는 게 좋겠다."])

    def _mila_sleep_touch(self, part, affection):
        """밀라 수면 중 - 행동 반응"""
        if part == "breast":
            yield ui.dialog([
                "손을 뻗어 밀라의 가슴에 살짝 닿았다.",
                "...풍만하고 부드럽다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "밀라가 잠결에 \"음...\" 하고 신음했다.",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "밀라의 눈꺼풀이 파르르 떨렸다.",
                    "(이건 진짜 죽는다.)",
                    "...서둘러 손을 뗐다."
                ])
        elif part == "butt":
            yield ui.dialog([
                "손을 뻗어 밀라의 엉덩이에 살짝 닿았다.",
                "...탱글탱글하다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "밀라가 잠결에 살짝 몸을 뒤척였다.",
                    "...깨지 않았다. 다행이다."
                ])
            else:
                yield ui.dialog([
                    "밀라가 \"으...\" 하며 인상을 찌푸렸다.",
                    "(심장이 멎을 뻔했다.)",
                    "...서둘러 손을 뗐다."
                ])
        elif part == "kiss":
            yield ui.dialog(["밀라의 얼굴에 가까이 다가갔다."])
            if affection >= 50:
                yield ui.dialog([
                    "잠든 밀라의 볼에 살짝 키스했다.",
                    "밀라가 잠결에 \"음...\" 하고 웃었다."
                ])
                yield ui.dialog([
                    "잠결에도 행복한 표정이다.",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "잠든 밀라의 이마에 가볍게 키스했다.",
                    "밀라의 미간이 살짝 움직였다."
                ])
                yield ui.dialog([
                    "(깨면 진짜 끝이다.)",
                    "...서둘러 물러났다."
                ])

    def _lina_sleep_touch(self, part, affection):
        """리나 수면 중 - 행동 반응"""
        if part == "breast":
            yield ui.dialog([
                "손을 뻗어 리나의 가슴에 살짝 닿았다.",
                "...작고 부드럽다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "리나가 잠결에 \"으응...\" 하고 작게 신음했다.",
                    "얼굴이 살짝 붉어졌다.",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "리나가 잠결에 움찔했다.",
                    "\"...오빠...?\"",
                    "...아직 잠꼬대인 것 같다."
                ])
        elif part == "butt":
            yield ui.dialog([
                "손을 뻗어 리나의 엉덩이에 살짝 닿았다.",
                "...작고 동글동글하다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "리나가 잠결에 몸을 동그랗게 말았다.",
                    "\"음...\"",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "리나가 잠결에 살짝 몸을 떨었다.",
                    "...이 이상은 위험할 것 같다."
                ])
        elif part == "kiss":
            yield ui.dialog(["리나의 얼굴에 가까이 다가갔다."])
            if affection >= 50:
                yield ui.dialog([
                    "잠든 리나의 이마에 살짝 키스했다.",
                    "리나가 잠결에 \"에헤헤...\" 하고 웃었다."
                ])
                yield ui.dialog([
                    "행복한 꿈을 꾸는 것 같다.",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "잠든 리나의 이마에 가볍게 키스했다.",
                    "리나가 잠결에 \"음... 오빠...\" 하고 중얼거렸다."
                ])
                yield ui.dialog(["...잠꼬대인 것 같다."])

    def _yuki_bed_sleeping(self, player_id, slot, affection, owner_id):
        """유키가 자고 있을 때 - 호감도별 묘사"""
        success = False
        if affection >= 50:
            yield ui.dialog([
                "유키가 조용히 잠들어 있다.",
                "작은 체구가 이불 속에 꼭 감싸여 있다."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["조심스럽게 옆에 누웠다."])
        elif affection >= 20:
            yield ui.dialog([
                "유키가 잠들어 있다.",
                "잠결에도 불안한 표정이다."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["깨우지 않게 살짝 옆에 누웠다."])
        else:
            yield ui.dialog([
                "유키가 잠들어 있다.",
                "...엘라가 알면 죽을 수도 있다."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["숨을 죽이며 옆에 누웠다."])

        if success:
            yield from self._sleeping_touch_choices("yuki", affection)

    def _ella_bed_sleeping(self, player_id, slot, affection, owner_id):
        """엘라가 자고 있을 때 - 호감도별 묘사"""
        success = False
        if affection >= 50:
            yield ui.dialog([
                "엘라가 잠들어 있다.",
                "깨어있을 때와 다른, 편안한 얼굴."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog(["조심스럽게 옆에 누웠다."])
        else:
            yield ui.dialog([
                "엘라가 잠들어 있다.",
                "...잠이 얕아 보인다. 위험하다."
            ])
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([
                    "숨을 죽이며 옆에 누웠다.",
                    "(깨면 진짜 끝이다.)"
                ])

        if success:
            yield from self._sleeping_touch_choices("ella", affection)

    def _yuki_sleep_touch(self, part, affection):
        """유키 수면 중 - 행동 반응"""
        if part == "breast":
            yield ui.dialog([
                "손을 뻗어 유키의 가슴에 살짝 닿았다.",
                "...작고 부드럽다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "유키가 잠결에 \"음...\" 하고 작게 신음했다.",
                    "얼굴이 살짝 붉어졌다.",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "유키가 잠결에 몸을 움츠렸다.",
                    "불안한 표정이 스쳤다.",
                    "...그만두는 게 좋겠다."
                ])
        elif part == "butt":
            yield ui.dialog([
                "손을 뻗어 유키의 엉덩이에 살짝 닿았다.",
                "...작고 부드럽다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "유키가 잠결에 살짝 몸을 뒤척였다.",
                    "\"...음...\"",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "유키가 잠결에 몸을 떨었다.",
                    "...이 이상은 너무하다."
                ])
        elif part == "kiss":
            yield ui.dialog(["유키의 얼굴에 가까이 다가갔다."])
            if affection >= 50:
                yield ui.dialog([
                    "잠든 유키의 이마에 살짝 키스했다.",
                    "유키가 잠결에 살짝 미소 짓는 것 같다."
                ])
                yield ui.dialog([
                    "\"...음... 따뜻해...\"",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "잠든 유키의 이마에 가볍게 키스했다.",
                    "유키의 눈꺼풀이 떨렸다."
                ])
                yield ui.dialog(["...깨기 전에 그만두자."])

    def _ella_sleep_touch(self, part, affection):
        """엘라 수면 중 - 행동 반응"""
        if part == "breast":
            yield ui.dialog([
                "손을 뻗어 엘라의 가슴에 살짝 닿았다.",
                "...단단하면서도 부드럽다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "엘라가 잠결에 살짝 미간을 찌푸렸다.",
                    "\"...음...\"",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "엘라의 눈꺼풀이 움직였다.",
                    "(이건 자살행위다.)",
                    "...서둘러 손을 뗐다."
                ])
        elif part == "butt":
            yield ui.dialog([
                "손을 뻗어 엘라의 엉덩이에 살짝 닿았다.",
                "...탄력이 있다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "엘라가 잠결에 몸을 뒤척였다.",
                    "...깨지 않았다. 다행이다."
                ])
            else:
                yield ui.dialog([
                    "엘라가 잠결에 손목을 잡았다.",
                    "(심장이 멎을 뻔했다.)",
                    "...잠꼬대인 것 같다. 서둘러 빼냈다."
                ])
        elif part == "kiss":
            yield ui.dialog(["엘라의 얼굴에 가까이 다가갔다."])
            if affection >= 50:
                yield ui.dialog([
                    "잠든 엘라의 이마에 살짝 키스했다.",
                    "엘라의 표정이 살짝 부드러워졌다."
                ])
                yield ui.dialog([
                    "깨어있을 때는 보기 힘든 표정이다.",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "잠든 엘라의 이마에 가볍게 키스했다.",
                    "엘라의 미간이 움찔했다."
                ])
                yield ui.dialog([
                    "(깨면 팔이 분질러진다.)",
                    "...서둘러 물러났다."
                ])

    def sleep(self):
        """잠자기"""
        yield ui.dialog(["침대에 누워 잠을 청했다."])
        morld.advance_time(480 * 60_000)  # 8시간


class SmallDesk(Object):
    unique_id = "small_desk"
    name = "작은 책상"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "작은 나무 책상. 서랍이 하나 달려 있다."}

    def look(self):
        """책상 살펴보기"""
        yield ui.dialog([
            "작은 나무 책상이다.",
            "서랍이 하나 달려 있다."
        ])
        morld.advance_time(1 * 60_000)


class Mirror(Object):
    unique_id = "mirror"
    name = "거울"
    actions = ["call:look:거울 보기", "call:debug_self_props:(디버그) 나를 돌아보기#", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "벽에 걸린 작은 거울. 내 모습을 비춰볼 수 있다."}

    def look(self):
        """거울 보기"""
        yield ui.dialog([
            "거울 속에 내 얼굴이 비친다.",
            "...그래, 이게 나다."
        ])
        morld.advance_time(1 * 60_000)


# ========================================
# 옷장 오브젝트
# ========================================

class Wardrobe(Object):
    """
    옷장 - 의류 보관 및 관리

    컨테이너 패턴:
    - container: 옷 넣기/빼기 (인벤토리 조회)
    - put_filter: clothing 카테고리 아이템만 넣을 수 있음
    """
    unique_id = "wardrobe"
    name = "옷장"
    put_filter = ["clothing"]  # 의류만 넣을 수 있음
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:put:옷 넣기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "옷을 보관할 수 있는 나무 옷장."}

    def look(self):
        """옷장 살펴보기"""
        yield ui.dialog([
            "큰 나무 옷장이다.",
            "옷을 넣거나 꺼낼 수 있다."
        ])
        morld.advance_time(1 * 60_000)


# ========================================
# 상점/편의점 오브젝트
# ========================================

class Shelf(Object):
    """
    선반 - 물건 보관 및 진열

    컨테이너 패턴:
    - container: 물건 넣기/빼기 (인벤토리 조회)
    - item_visible: True (아이템 개수 표시)
    """
    unique_id = "shelf"
    name = "선반"
    item_visible = True  # 아이템 개수 표시
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "물건을 놓을 수 있는 선반."}

    def look(self):
        """선반 살펴보기"""
        yield ui.dialog([
            "물건을 진열할 수 있는 선반이다.",
            "남은 물건이 있는지 확인해 볼 수 있다."
        ])
        morld.advance_time(1 * 60_000)


class Refrigerator(Object):
    """
    냉장고 - 음료 및 음식 보관

    컨테이너 패턴:
    - container: 물건 넣기/빼기 (인벤토리 조회)
    - item_visible: True (아이템 개수 표시)
    """
    unique_id = "refrigerator"
    name = "냉장고"
    item_visible = True  # 아이템 개수 표시
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "낡은 냉장고. 전기가 안 들어와 그냥 보관함으로 쓰인다."}

    def look(self):
        """냉장고 살펴보기"""
        yield ui.dialog([
            "낡은 냉장고다.",
            "전기가 들어오지 않아 차갑지 않지만, 음료가 남아있을지도 모른다."
        ])
        morld.advance_time(1 * 60_000)


# ========================================
# 2층 복도 오브젝트
# ========================================

class CorridorWindow(Object):
    unique_id = "corridor_window"
    name = "복도 창문"
    actions = ["call:look:밖을 보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "2층 복도에 있는 큰 창문. 앞마당이 내려다보인다."}

    def look(self):
        """창문 밖을 보기"""
        yield ui.dialog([
            "2층 창문에서 앞마당이 내려다보인다.",
            "정원이 한눈에 들어온다."
        ])
        morld.advance_time(2 * 60_000)


class Vase(Object):
    unique_id = "vase"
    name = "화병"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "복도 끝에 놓인 장식용 화병. 마른 꽃이 꽂혀 있다."}

    def look(self):
        """화병 살펴보기"""
        yield ui.dialog([
            "장식용 화병이다.",
            "마른 꽃이 꽂혀 있다."
        ])
        morld.advance_time(1 * 60_000)


# ========================================
# 장식 오브젝트
# ========================================

class OldDoll(Object):
    """
    낡은 인형 - 귀여운 곰 인형
    owner는 instantiate 시 지정 (예: 세라 방에서 sera 소유로 배치)
    """
    unique_id = "old_doll"
    name = "낡은 인형"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "작고 낡은 곰 인형. 누군가 소중히 다뤄온 흔적이 보인다."}

    def look(self):
        """인형 살펴보기"""
        yield ui.dialog([
            "작은 곰 인형이다.",
            "오래되어 색이 바랬지만, 깨끗하게 관리되어 있다.",
            "...누가 이런 걸 두고 있는 걸까?"
        ])
        morld.advance_time(1 * 60_000)
