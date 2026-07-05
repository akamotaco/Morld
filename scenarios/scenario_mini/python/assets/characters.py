# assets/characters.py — scenario_mini 캐릭터 (캐릭터 표준 ①: 데이터 파일)
#
# engine.asset_base.CharacterBase 직접 상속 + engine.archetype_describe 의
# 아키타입 공용 묘사 풀로 DESCRIBE/FOCUS rule 자동 구성.
# 이 파일의 유일한 morld 배선은 instantiate() 의 add_unit 호출 (시나리오 글루).

import morld

from engine.asset_base import CharacterBase
from engine.archetype_describe import build_describe_rules, build_focus_rules


class MiniCharacter(CharacterBase):
    """scenario_mini 공통 — instantiate 시 morld 등록 글루"""

    archetype = "stoic"
    actions = None
    props = None

    def instantiate(self, instance_id, region_id, location_id):
        super().instantiate(instance_id)
        morld.add_unit(
            instance_id, self.name, region_id, location_id,
            self.type,
            actions=list(self.actions or []),
            mood=list(self.mood or []),
            unique_id=self.unique_id,
        )
        if self.props:
            morld.set_unit_props(instance_id, dict(self.props))
        self.region_id = region_id
        self.location_id = location_id


class Traveler(MiniCharacter):
    """플레이어 — unique_id="player" 가 유일한 플레이어 지정 경로 (U0 계약)"""
    unique_id = "player"
    name = "여행자"
    type = "male"
    props = {"생존:체력": 100, "생존:체력max": 100}


class Mia(MiniCharacter):
    """광장 안내인 — cheerful 아키타입 (묘사/대사 전부 공용 풀 상속)"""
    unique_id = "mini_guide"
    name = "미아"
    type = "female"
    archetype = "cheerful"
    actions = ["call:talk:대화"]
    props = {"생존:체력": 80, "생존:체력max": 80}

    DESCRIBE_RULES = build_describe_rules(
        "cheerful",
        activities=[("안내", "{name}가 광장에서 안내를 하고 있다.")],
        default_text="{name}가 광장에 서 있다.",
    )
    FOCUS_RULES = build_focus_rules(
        "cheerful",
        activities=[("안내", "밝은 목소리로 마을을 소개하고 있다.")],
        default_text="밝은 미소의 안내인. 마을 이야기를 잘 안다.",
    )


class Ranger(MiniCharacter):
    """동행 가능한 순찰자 — stoic 아키타입 (모집 검증용)"""
    unique_id = "mini_ranger"
    name = "레인"
    type = "female"
    archetype = "stoic"
    actions = ["recruit:권유"]
    props = {"생존:체력": 90, "생존:체력max": 90, "리더십": 1}

    DESCRIBE_RULES = build_describe_rules(
        "stoic",
        activities=[("순찰", "{name}가 말없이 주변을 살피고 있다.")],
        default_text="{name}가 벽에 기대어 서 있다.",
    )
    FOCUS_RULES = build_focus_rules(
        "stoic",
        activities=[],
        default_text="과묵한 순찰자. 눈빛이 날카롭다.",
    )
