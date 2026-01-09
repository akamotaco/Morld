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
from assets.base import Object


# ========================================
# 앞마당 오브젝트
# ========================================

class GardenBench(Object):
    unique_id = "garden_bench"
    name = "정원 벤치"
    actions = ["call:sit:앉기", "script:debug_props:속성 보기"]
    focus_text = {"default": "정원에 놓인 나무 벤치. 앉아서 쉴 수 있다."}

    def sit(self):
        """벤치에 앉기"""
        yield morld.dialog([
            "정원 벤치에 앉았다.",
            "바람이 시원하다."
        ])
        morld.advance_time(10)


class Well(Object):
    unique_id = "well"
    name = "우물"
    actions = ["call:look:들여다보기", "call:draw:물 길어올리기", "script:debug_props:속성 보기"]
    focus_text = {"default": "돌로 쌓아 만든 우물. 맑은 물이 고여 있다."}

    def look(self):
        """우물 들여다보기"""
        yield morld.dialog([
            "우물 안을 들여다봤다.",
            "맑은 물이 깊은 곳에서 반짝인다."
        ])
        morld.advance_time(1)

    def draw(self):
        """물 길어올리기"""
        yield morld.dialog([
            "두레박으로 물을 길어올렸다.",
            "시원하고 맑은 물이다."
        ])
        morld.advance_time(5)


# ========================================
# 뒷마당 오브젝트
# ========================================

class GardenPlot(Object):
    unique_id = "garden_plot"
    name = "텃밭"
    actions = ["call:look:살펴보기", "script:debug_props:속성 보기"]
    focus_text = {
        "default": "작은 텃밭. 간단한 채소를 기를 수 있을 것 같다.",
        "봄": "새싹이 돋아나고 있다.",
        "여름": "채소들이 무성하게 자라고 있다.",
        "가을": "수확할 채소가 익어가고 있다.",
        "겨울": "텅 빈 텃밭. 봄을 기다리고 있다."
    }

    def look(self):
        """텃밭 살펴보기"""
        yield morld.dialog([
            "작은 텃밭이다.",
            "간단한 채소를 기를 수 있을 것 같다."
        ])
        morld.advance_time(2)


class DryingRack(Object):
    unique_id = "drying_rack"
    name = "빨래 건조대"
    actions = ["call:look:살펴보기", "script:debug_props:속성 보기"]
    focus_text = {"default": "뒷마당에 놓인 빨래 건조대. 가끔 빨래가 널려 있다."}

    def look(self):
        """빨래 건조대 살펴보기"""
        yield morld.dialog([
            "빨래 건조대다.",
            "빨래가 마르면 걷어야 할 것 같다."
        ])
        morld.advance_time(1)
