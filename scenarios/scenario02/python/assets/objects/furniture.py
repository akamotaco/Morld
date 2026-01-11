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
from assets.base import Object


# ========================================
# 거실 오브젝트
# ========================================

class Fireplace(Object):
    unique_id = "fireplace"
    name = "벽난로"
    actions = ["call:look:살펴보기", "call:debug_props:속성 보기"]
    focus_text = {
        "default": "돌로 만들어진 오래된 벽난로. 저녁이면 불이 피워진다.",
        "저녁": "따뜻한 불꽃이 타오르고 있다.",
        "밤": "잔잔한 불씨가 남아 있다."
    }

    def look(self):
        """벽난로 살펴보기"""
        yield morld.dialog([
            "돌로 쌓아 만든 오래된 벽난로다.",
            "저녁이 되면 따뜻한 불이 피워진다."
        ])
        morld.advance_time(1)


class OldSofa(Object):
    unique_id = "old_sofa"
    name = "낡은 소파"
    actions = ["call:sit:앉기", "call:debug_props:속성 보기"]
    focus_text = {"default": "오래 사용해서 닳았지만 여전히 푹신한 소파."}

    def sit(self):
        """소파에 앉기"""
        yield morld.dialog([
            "소파에 앉았다.",
            "푹신하고 편안하다."
        ])
        morld.advance_time(5)


class LivingSofa(Object):
    """
    앉을 수 있는 거실 소파 (Vehicle 시스템 테스트용)

    좌석 Prop 시스템:
    - seated_by:left → 왼쪽 좌석 (-1이면 빈 좌석)
    - seated_by:center → 중앙 좌석 (-1이면 빈 좌석)
    - seated_by:right → 오른쪽 좌석 (-1이면 빈 좌석)
    """
    unique_id = "living_sofa"
    name = "거실 소파"
    actions = [
        "sit@left:왼쪽에 앉기",
        "sit@center:가운데 앉기",
        "sit@right:오른쪽에 앉기",
        "call:debug_props:속성 보기"
    ]
    props = {
        "seated_by:left": -1,    # 왼쪽 좌석 (빈 좌석)
        "seated_by:center": -1,  # 중앙 좌석 (빈 좌석)
        "seated_by:right": -1    # 오른쪽 좌석 (빈 좌석)
    }
    focus_text = {"default": "푹신하고 넓은 거실 소파. 편하게 앉아 쉴 수 있다."}


class Bookshelf(Object):
    unique_id = "bookshelf"
    name = "책장"
    actions = ["call:look:살펴보기", "call:debug_props:속성 보기"]
    focus_text = {"default": "벽면을 따라 놓인 큰 책장. 다양한 책이 꽂혀 있다."}

    def look(self):
        """책장 살펴보기"""
        yield morld.dialog([
            "다양한 책이 꽂혀 있다.",
            "소설, 역사서, 요리책... 장르가 다양하다."
        ])
        morld.advance_time(2)


# ========================================
# 식당 오브젝트
# ========================================

class DiningTable(Object):
    unique_id = "dining_table"
    name = "긴 식탁"
    actions = ["call:look:살펴보기", "call:debug_props:속성 보기"]
    focus_text = {"default": "여섯 명이 앉을 수 있는 긴 나무 식탁. 잘 닦여 있다."}

    def look(self):
        """식탁 살펴보기"""
        yield morld.dialog([
            "잘 닦인 긴 나무 식탁이다.",
            "여섯 개의 의자가 가지런히 놓여 있다."
        ])
        morld.advance_time(1)


class DiningChair(Object):
    """
    앉을 수 있는 식탁 의자 (Vehicle 시스템 테스트용)

    좌석 Prop 시스템:
    - seated_by:1~4 → 각 의자 좌석 (-1이면 빈 좌석)
    """
    unique_id = "dining_chair"
    name = "식탁 의자"
    actions = [
        "sit@1:1번 의자에 앉기",
        "sit@2:2번 의자에 앉기",
        "sit@3:3번 의자에 앉기",
        "sit@4:4번 의자에 앉기",
        "call:debug_props:속성 보기"
    ]
    props = {
        "seated_by:1": -1,  # 1번 의자 (빈 좌석)
        "seated_by:2": -1,  # 2번 의자 (빈 좌석)
        "seated_by:3": -1,  # 3번 의자 (빈 좌석)
        "seated_by:4": -1   # 4번 의자 (빈 좌석)
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
        "container",  # C# 기본 컨테이너 UI 사용
        "call:put:재료 넣기",
        "call:cook:조리하기",
        "call:debug_props:속성 보기"
    ]
    focus_text = {"default": "요리에 사용하는 큰 아궁이. 항상 따뜻하다."}

    def look(self):
        """아궁이 살펴보기"""
        yield morld.dialog([
            "요리에 사용하는 큰 아궁이다.",
            "항상 따뜻한 열기가 느껴진다."
        ])
        morld.advance_time(1)

    def cook(self):
        """조리 실행 - 결과물은 플레이어 인벤토리로 바로 지급"""
        from recipes import find_matching_recipe, RECIPES
        from assets.registry import get_item_class

        player_id = morld.get_player_id()

        # 현재 재료 확인
        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            yield morld.dialog("재료가 없다.")
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
            yield morld.dialog("이 재료로는 만들 수 있는 것이 없다.")
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
        yield morld.dialog(f"{recipe['name']}을(를) 만들었다!")
        morld.advance_time(recipe["cook_time"])


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
        "container",  # C# 기본 컨테이너 UI 사용
        "call:put:재료 넣기",
        "call:brew:끓이기",
        "call:debug_props:속성 보기"
    ]
    focus_text = {"default": "물을 끓이거나 차를 우릴 수 있는 주전자."}

    def look(self):
        """주전자 살펴보기"""
        yield morld.dialog([
            "물을 끓이거나 차를 우릴 수 있는 주전자다.",
            "아궁이 위에 올려두면 사용할 수 있다."
        ])
        morld.advance_time(1)

    def brew(self):
        """음료 제조 - 결과물은 플레이어 인벤토리로 바로 지급"""
        from recipes import find_matching_recipe, RECIPES
        from assets.registry import get_item_class

        player_id = morld.get_player_id()

        # 현재 재료 확인
        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            yield morld.dialog("재료가 없다.")
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
            yield morld.dialog("이 재료로는 만들 수 있는 것이 없다.")
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
        yield morld.dialog(f"{recipe['name']}을(를) 만들었다!")
        morld.advance_time(recipe["cook_time"])


class Cupboard(Object):
    unique_id = "cupboard"
    name = "찬장"
    actions = ["call:look:살펴보기", "call:debug_props:속성 보기"]
    focus_text = {"default": "그릇과 조리도구가 정리된 찬장."}

    def look(self):
        """찬장 살펴보기"""
        yield morld.dialog(["그릇과 조리도구가 깔끔하게 정리되어 있다."])
        morld.advance_time(1)


# ========================================
# 욕실 오브젝트
# ========================================

class Bathtub(Object):
    unique_id = "bathtub"
    name = "나무 욕조"
    actions = ["call:use:목욕하기", "call:debug_props:속성 보기"]
    focus_text = {"default": "큰 나무 욕조. 따뜻한 물을 받아 목욕할 수 있다."}

    def use(self):
        """목욕하기"""
        yield morld.dialog([
            "따뜻한 물을 받아 목욕했다.",
            "몸이 개운해졌다."
        ])
        morld.advance_time(30)


class Washbasin(Object):
    unique_id = "washbasin"
    name = "세면대"
    actions = ["call:use:세수하기", "call:debug_props:속성 보기"]
    focus_text = {"default": "도자기로 만든 세면대. 깨끗하게 관리되어 있다."}

    def use(self):
        """세수하기"""
        yield morld.dialog([
            "시원한 물로 얼굴을 씻었다.",
            "정신이 맑아졌다."
        ])
        morld.advance_time(5)


# ========================================
# 창고 오브젝트
# ========================================

class CraftingTable(Object):
    """
    제작대 - 복잡한 아이템 제작 가능

    WORKBENCH_RECIPES에 정의된 레시피 사용:
    - 사냥용 활: 나무판 2개 + 끈 1개
    """
    unique_id = "crafting_table"
    name = "제작대"
    actions = ["call:look:살펴보기", "call:craft:제작하기", "call:debug_props:속성 보기"]
    focus_text = {"default": "도구와 재료를 다룰 수 있는 튼튼한 작업대."}

    def look(self):
        """제작대 살펴보기"""
        yield morld.dialog([
            "튼튼한 나무로 만든 작업대다.",
            "복잡한 물건을 제작할 수 있다."
        ])
        morld.advance_time(1)

    def craft(self):
        """제작대에서 제작하기"""
        from crafting import open_craft_menu, WORKBENCH_RECIPES
        yield from open_craft_menu(WORKBENCH_RECIPES, "제작대")


# ========================================
# 침실 오브젝트 (주인공 방)
# ========================================

class Bed(Object):
    unique_id = "bed"
    name = "침대"
    actions = ["call:sleep:잠자기", "call:rest:누워있기", "call:debug_props:속성 보기"]
    focus_text = {"default": "작지만 편안해 보이는 침대. 깨끗한 이불이 깔려 있다."}

    def sleep(self):
        """잠자기"""
        yield morld.dialog(["침대에 누워 잠을 청했다."])
        morld.advance_time(480)  # 8시간

    def rest(self):
        """누워있기"""
        yield morld.dialog([
            "침대에 잠시 누워 쉬었다.",
            "피로가 조금 풀렸다."
        ])
        morld.advance_time(30)


class SmallDesk(Object):
    unique_id = "small_desk"
    name = "작은 책상"
    actions = ["call:look:살펴보기", "call:debug_props:속성 보기"]
    focus_text = {"default": "작은 나무 책상. 서랍이 하나 달려 있다."}

    def look(self):
        """책상 살펴보기"""
        yield morld.dialog([
            "작은 나무 책상이다.",
            "서랍이 하나 달려 있다."
        ])
        morld.advance_time(1)


class Mirror(Object):
    unique_id = "mirror"
    name = "거울"
    actions = ["call:look:거울 보기", "call:debug_self_props:나를 돌아보기", "call:debug_props:속성 보기"]
    focus_text = {"default": "벽에 걸린 작은 거울. 내 모습을 비춰볼 수 있다."}

    def look(self):
        """거울 보기"""
        yield morld.dialog([
            "거울 속에 내 얼굴이 비친다.",
            "...그래, 이게 나다."
        ])
        morld.advance_time(1)


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
        "container",  # C# 기본 컨테이너 UI 사용
        "call:debug_props:속성 보기"
    ]
    focus_text = {"default": "옷을 보관할 수 있는 나무 옷장."}

    def look(self):
        """옷장 살펴보기"""
        yield morld.dialog([
            "큰 나무 옷장이다.",
            "옷을 넣거나 꺼낼 수 있다."
        ])
        morld.advance_time(1)


# ========================================
# 2층 복도 오브젝트
# ========================================

class CorridorWindow(Object):
    unique_id = "corridor_window"
    name = "복도 창문"
    actions = ["call:look:밖을 보기", "call:debug_props:속성 보기"]
    focus_text = {"default": "2층 복도에 있는 큰 창문. 앞마당이 내려다보인다."}

    def look(self):
        """창문 밖을 보기"""
        yield morld.dialog([
            "2층 창문에서 앞마당이 내려다보인다.",
            "정원이 한눈에 들어온다."
        ])
        morld.advance_time(2)


class Vase(Object):
    unique_id = "vase"
    name = "화병"
    actions = ["call:look:살펴보기", "call:debug_props:속성 보기"]
    focus_text = {"default": "복도 끝에 놓인 장식용 화병. 마른 꽃이 꽂혀 있다."}

    def look(self):
        """화병 살펴보기"""
        yield morld.dialog([
            "장식용 화병이다.",
            "마른 꽃이 꽂혀 있다."
        ])
        morld.advance_time(1)
