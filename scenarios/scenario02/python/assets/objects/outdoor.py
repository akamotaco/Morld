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

class GardenPlot(Object):
    unique_id = "garden_plot"
    name = "텃밭"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {
        "default": "작은 텃밭. 간단한 채소를 기를 수 있을 것 같다.",
        "봄": "새싹이 돋아나고 있다.",
        "여름": "채소들이 무성하게 자라고 있다.",
        "가을": "수확할 채소가 익어가고 있다.",
        "겨울": "텅 빈 텃밭. 봄을 기다리고 있다."
    }

    def look(self):
        """텃밭 살펴보기"""
        yield ui.dialog([
            "작은 텃밭이다.",
            "간단한 채소를 기를 수 있을 것 같다."
        ])
        morld.advance_time_des(2 * 60_000)


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
    }
    focus_text = {"default": "거리에 놓인 낡은 벤치. 앉아서 쉴 수 있다."}


# ========================================
# 강가 오브젝트
# ========================================

class FishingSpot(Object):
    """
    낚시터 - can:fish 필요 (낚시대 장착)

    플레이어가 낚시대를 장착하면 can:fish가 부여되고,
    이 오브젝트의 "낚시" 액션이 표시됨.
    """
    unique_id = "fishing_spot"
    name = "낚시터"
    actions = ["call:look:살펴보기", "call:fish:낚시", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "물이 깊고 잔잔한 곳. 물고기가 많을 것 같다."}

    def look(self):
        """낚시터 살펴보기"""
        yield ui.dialog([
            "물이 깊고 잔잔한 곳이다.",
            "물고기가 많이 잡힐 것 같다.",
            "낚시대를 장착하면 낚시를 할 수 있다."
        ])
        morld.advance_time_des(1 * 60_000)

    def fish(self, equipment=None):
        """
        낚시하기 - can:fish가 있어야 실행 가능

        랜덤으로 생선 획득 또는 실패

        Args:
            equipment: 낚시에 사용된 장비 정보
                       {"item_id": int, "unique_id": str, "name": str} 또는 None
        """
        import random
        from assets.registry import get_item_class

        # 장비에 따라 다른 낚시 메시지
        if equipment:
            equip_id = equipment.get("unique_id", "")
            if equip_id == "fishing_rod":
                yield ui.dialog("낚싯줄을 드리운다...")
            else:
                yield ui.dialog(f"{equipment.get('name', '도구')}(으)로 낚시를 시작한다...")
        else:
            # can:fish가 기본 능력인 경우 (장비 없이 가능할 때)
            yield ui.dialog("맨손으로 물고기를 잡아본다...")
        morld.advance_time_des(15 * 60_000)  # 15분 소요

        # 70% 확률로 성공
        if random.random() < 0.7:
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

            morld.give_item(player_id, fish_id, 1)
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
        """NPC 낚시 (non-generator, 70% 성공)"""
        import random
        from assets.registry import get_or_create_item_id
        if random.random() < 0.7:
            item_id = get_or_create_item_id("food_fish")
            if item_id:
                morld.give_item(npc_id, item_id, 1)
                return True
        return False
