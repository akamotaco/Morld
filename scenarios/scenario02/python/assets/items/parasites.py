# assets/items/parasites.py — 기생 생물체 아이템 + 제거제
#
# ParasiteItem: 신체 부착형 living equipment
# - 전용 기생 슬롯 (기생:{부위}) — 의류 슬롯과 독립
# - 옷 아래 부착, 제거 시 옷 먼저 벗어야
# - stimulation_rate/climax_contribution: 시간당 미미한 자극
# - passive_effects: 버프/디버프 (prop 직접 적용)
# - 일반 벗기 불가 → 자력 확률 제거 or 특수 아이템 확실 제거

import morld
from assets.base import Item


class ParasiteItem(Item):
    """기생 생물체 아이템 — 신체 부착형 living equipment"""
    category = "parasite"

    # 기생 부위 (전용 슬롯)
    parasite_slot = None        # "기생:가슴", "기생:음부", etc.

    # 대응하는 의류 슬롯 (이 옷을 먼저 벗어야 제거 가능)
    blocking_clothing_slot = None  # "착용:속옷상의", etc.

    # 기생 부착 시 필요한 노출 조건
    required_exposure_part = None  # "upper" or "lower"
    required_exposure_level = 2    # 2=완전노출

    # 내구도 낮은 옷 틈새 침투 임계값
    durability_penetration_threshold = 5

    # 시간당 효과 (미미한 수준)
    stimulation_rate = 1         # 시간당 감각 증가량
    climax_contribution = 1      # 시간당 절정 게이지 기여
    exp_part = None              # 경험 축적 부위

    # 버프/디버프
    passive_effects = {}

    # 제거 난이도
    removal_difficulty = 50      # 0-100

    actions = [
        "call:look:살펴보기@inventory",
    ]

    # put 비활성화 (바닥에 놓기 불가)
    action_props = {"put": 0}


class BreastParasiteItem(ParasiteItem):
    """유두/가슴 부착 기생체"""
    unique_id = "breast_parasite"
    name = "유방 기생체"
    parasite_slot = "기생:가슴"
    blocking_clothing_slot = "착용:속옷상의"
    required_exposure_part = "upper"
    exp_part = "가슴"
    stimulation_rate = 1
    climax_contribution = 1
    removal_difficulty = 40
    passive_effects = {"생존:체력회복": 1}

    describe_text = {"default": "가슴에 부착된 반투명한 생물체. 촉수가 유두를 감싸고 있다."}


class GenitalParasiteItem(ParasiteItem):
    """질 부착 기생체 (외부 감싸기 + 촉수 삽입)"""
    unique_id = "genital_parasite"
    name = "음부 기생체"
    parasite_slot = "기생:음부"
    blocking_clothing_slot = "착용:속옷하의"
    required_exposure_part = "lower"
    exp_part = "음부"
    stimulation_rate = 2
    climax_contribution = 2
    removal_difficulty = 60
    passive_effects = {"생존:체력회복": 1}

    describe_text = {"default": "하반신에 부착된 끈적한 생물체. 촉수가 꿈틀거린다."}


class AnalParasiteItem(ParasiteItem):
    """항문 부착 기생체"""
    unique_id = "anal_parasite"
    name = "항문 기생체"
    parasite_slot = "기생:항문"
    blocking_clothing_slot = "착용:속옷하의"
    required_exposure_part = "lower"
    exp_part = "항문"
    stimulation_rate = 1
    climax_contribution = 1
    removal_difficulty = 50

    describe_text = {"default": "엉덩이에 달라붙은 기묘한 생물체."}


class OralParasiteItem(ParasiteItem):
    """구강 부착 기생체"""
    unique_id = "oral_parasite"
    name = "구강 기생체"
    parasite_slot = "기생:구강"
    blocking_clothing_slot = None
    required_exposure_part = None   # 항상 노출
    exp_part = "입"
    stimulation_rate = 1
    climax_contribution = 1
    removal_difficulty = 40
    passive_effects = {"결박:입": 1}

    describe_text = {"default": "입에 부착된 생물체. 말을 할 수 없게 만든다."}


class PenisParasiteItem(ParasiteItem):
    """페니스 감싸기 기생체"""
    unique_id = "penis_parasite"
    name = "남근 기생체"
    parasite_slot = "기생:페니스"
    blocking_clothing_slot = "착용:속옷하의"
    required_exposure_part = "lower"
    exp_part = "페니스"
    stimulation_rate = 2
    climax_contribution = 2
    removal_difficulty = 50

    describe_text = {"default": "남근을 감싼 끈적한 생물체."}


class BindingParasiteItem(ParasiteItem):
    """결박형 기생체 (삽입 + 상체/하체 결박)"""
    unique_id = "binding_parasite"
    name = "결박 기생체"
    parasite_slot = "기생:전신"
    blocking_clothing_slot = None
    required_exposure_part = None   # 노출 무관 (자체 구속력)
    exp_part = "음부"
    stimulation_rate = 3
    climax_contribution = 3
    removal_difficulty = 80
    passive_effects = {"결박:상체": 1, "결박:하체": 1, "결박:강도": 50}

    describe_text = {"default": "전신을 감싼 촉수형 생물체. 움직임을 봉쇄하고 있다."}


# 기생 아이템 레지스트리 (unique_id → class)
_PARASITE_REGISTRY = {
    "breast_parasite": BreastParasiteItem,
    "genital_parasite": GenitalParasiteItem,
    "anal_parasite": AnalParasiteItem,
    "oral_parasite": OralParasiteItem,
    "penis_parasite": PenisParasiteItem,
    "binding_parasite": BindingParasiteItem,
}


# ========================================
# 기생체 제거제
# ========================================

class ParasiteRemover(Item):
    """기생체 제거제 — 확실한 제거"""
    unique_id = "parasite_remover"
    name = "기생체 제거제"
    category = "consumable"
    actions = [
        "take@container",
        "call:use_remover:사용@inventory",
    ]

    describe_text = {"default": "기생체를 안전하게 제거할 수 있는 용액."}

    def use_remover(self):
        import parasite
        import ui
        player_id = morld.get_player_id()
        attached = parasite.get_attached_parasites(player_id)
        if not attached:
            morld.add_action_log("제거할 기생체가 없다.")
            return
        # 선택 UI
        lines = ["제거할 기생체를 선택하세요.\n"]
        for slot, item_id, name in attached:
            part = slot.split(":")[1]
            lines.append(f"[url=@ret:{slot}]{name} ({part})[/url]")
        lines.append("\n[url=@ret:cancel]취소[/url]")
        choice = yield ui.dialog("\n".join(lines))
        if choice == "cancel" or not choice:
            return
        result = parasite.remove_with_item(player_id, choice)
        morld.add_action_log(result["message"])
        morld.lost_item(player_id, self.instance_id, 1)  # 소모
