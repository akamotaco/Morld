# parasite.py — 기생 시스템
#
# 기생체 부착/제거/조회 + 반응 대사
# - 전용 슬롯: 기생:{부위} (의류 슬롯과 독립)
# - 부착 조건: 신체 노출 or 내구도 낮은 옷 틈새 침투
# - 제거: 자력 확률 (근력 기반) or 특수 아이템 확실 제거
# - 반응: 아키타입 기반 부착 즉시 반응 + 주기적 대사

import morld

# 기생 슬롯 목록
PARASITE_SLOTS = [
    "기생:가슴", "기생:음부", "기생:항문", "기생:구강", "기생:페니스", "기생:전신",
]


# ========================================
# 부착
# ========================================

def attach_parasite(target_id, parasite_item_id):
    """기생체를 대상에 부착

    Returns: {"success": bool, "message": str}
    """
    from assets.items.parasites import ParasiteItem
    from assets.registry import get_instance
    item = get_instance(parasite_item_id)
    if not isinstance(item, ParasiteItem):
        return {"success": False, "message": "기생 아이템이 아니다."}

    slot = item.parasite_slot
    # 이미 해당 슬롯 점유 확인
    existing = morld.get_unit_prop(target_id, slot)
    if existing:
        return {"success": False, "message": "이미 기생체가 부착되어 있다."}

    # 노출 확인 (또는 내구도 낮은 옷 침투)
    can_attach, reason = _check_attachment_condition(target_id, item)
    if not can_attach:
        return {"success": False, "message": reason}

    # 부착
    morld.set_unit_prop(target_id, slot, parasite_item_id)
    morld.give_item(target_id, parasite_item_id, 1)

    # 패시브 효과 적용
    for prop_key, value in item.passive_effects.items():
        morld.modify_prop(target_id, prop_key, value)

    # 부착 즉시 반응 대사
    _emit_attachment_reaction(target_id, item)

    return {"success": True, "message": f"{item.name}이(가) 신체에 부착되었다!"}


def _check_attachment_condition(target_id, item):
    """부착 가능 조건 확인

    Returns: (bool, str)
    """
    # 노출 부위가 None이면 항상 가능 (구강, 전신)
    if item.required_exposure_part is None:
        return True, ""

    from assets.base import Character
    exposure = Character._calculate_exposure(target_id)
    exp_key = item.required_exposure_part  # "upper" or "lower"
    current_level = exposure.get(exp_key, 0)

    # 완전 노출이면 OK
    if current_level >= item.required_exposure_level:
        return True, ""

    # 내구도 낮은 옷 체크 (틈새 침투)
    if item.blocking_clothing_slot:
        import equipment
        for eq_id in equipment.get_equipped_items(target_id):
            info = morld.get_item_info(eq_id)
            if not info:
                continue
            ep = info.get("equip_props", {})
            if item.blocking_clothing_slot in ep:
                dur = morld.get_unit_prop(eq_id, "내구도")
                if dur is not None and dur <= item.durability_penetration_threshold:
                    return True, ""  # 틈새 침투!
                return False, "옷에 막혀 부착할 수 없다."

    return False, "신체가 노출되어 있지 않다."


# ========================================
# 제거
# ========================================

def attempt_self_removal(unit_id, slot):
    """자력 기생체 제거 시도

    Returns: {"success": bool, "message": str}
    """
    item_id = morld.get_unit_prop(unit_id, slot)
    if not item_id:
        return {"success": False, "message": "부착된 기생체가 없다."}

    from assets.registry import get_instance
    item = get_instance(item_id)
    if not item:
        _force_remove(unit_id, slot, item_id)
        return {"success": True, "message": "기생체를 제거했다."}

    # 옷 위에 있으면 먼저 벗어야
    blocking = getattr(item, 'blocking_clothing_slot', None)
    if blocking:
        import equipment
        for eq_id in equipment.get_equipped_items(unit_id):
            info = morld.get_item_info(eq_id)
            if info and blocking in info.get("equip_props", {}):
                return {"success": False, "message": "옷을 먼저 벗어야 한다."}

    # 확률 계산
    import random
    strength = morld.get_unit_prop(unit_id, "능력:근력") or 5
    difficulty = getattr(item, 'removal_difficulty', 50)
    # 확률 = 근력 / (근력 + 난이도) × 0.5 (최대 50%)
    chance = min(0.5, strength / (strength + difficulty) * 0.5)

    if random.random() < chance:
        name = getattr(item, 'name', '기생체')
        _force_remove(unit_id, slot, item_id)
        return {"success": True, "message": f"{name}을(를) 뜯어냈다!"}
    else:
        import survival
        survival.add_health(unit_id, -3)
        return {"success": False, "message": "제거에 실패했다. (HP -3)"}


def remove_with_item(unit_id, slot):
    """특수 아이템으로 확실한 제거

    Returns: {"success": bool, "message": str}
    """
    item_id = morld.get_unit_prop(unit_id, slot)
    if not item_id:
        return {"success": False, "message": "부착된 기생체가 없다."}
    _force_remove(unit_id, slot, item_id)
    return {"success": True, "message": "기생체가 안전하게 제거되었다."}


def _force_remove(unit_id, slot, item_id):
    """강제 제거 (패시브 효과 해제 + prop 클리어)"""
    from assets.registry import get_instance
    item = get_instance(item_id)
    if item:
        effects = getattr(item, 'passive_effects', {})
        for prop_key, value in effects.items():
            morld.modify_prop(unit_id, prop_key, -value)
    morld.clear_prop(unit_id, slot)
    morld.lost_item(unit_id, item_id, 1)


# ========================================
# 조회
# ========================================

def get_attached_parasites(unit_id):
    """부착된 기생체 목록

    Returns: [(slot, item_id, item_name), ...]
    """
    result = []
    for slot in PARASITE_SLOTS:
        item_id = morld.get_unit_prop(unit_id, slot)
        if item_id:
            info = morld.get_item_info(item_id)
            name = info.get("name", "기생체") if info else "기생체"
            result.append((slot, item_id, name))
    return result


def has_any_parasite(unit_id):
    """기생체 부착 여부"""
    for slot in PARASITE_SLOTS:
        if morld.get_unit_prop(unit_id, slot):
            return True
    return False


# ========================================
# 반응 대사
# ========================================

# 부착 즉시 반응 (아키타입별)
_ATTACHMENT_REACTIONS = {
    "stoic": "{name}(이)가 {part}에 기생체가 부착되자 이를 악문다.",
    "gentle": "'{part}에 뭔가가...!' {name}(이)가 놀란 표정을 짓는다.",
    "timid": "'싫어...!' {name}(이)가 {part}의 기생체에 비명을 지른다.",
    "cheerful": "'으악?! {part}에 뭔가 붙었어!' {name}(이)가 소리친다.",
    "cold": "{name}(이)가 {part}의 이질감에 미간을 찌푸린다.",
    "seductive": "'어머...' {name}(이)가 {part}의 감촉에 눈을 가늘게 뜬다.",
    "fierce": "'이 벌레가...!' {name}(이)가 {part}의 기생체에 분노한다.",
    "proud": "'이런 치욕이...!' {name}(이)가 굴욕감에 얼굴을 붉힌다.",
    "innocent": "'{part}에 이상한 게...' {name}(이)가 당황한다.",
    "devoted": "'{part}에...' {name}(이)가 주인을 바라보며 불안해한다.",
}


def _emit_attachment_reaction(target_id, item):
    """기생체 부착 시 즉시 반응 대사"""
    from assets.characters import get_instance
    char = get_instance(target_id)
    if not char:
        return
    archetype = getattr(char, 'archetype', None)
    name = getattr(char, 'name', '?')
    part = item.parasite_slot.split(":")[1]

    template = _ATTACHMENT_REACTIONS.get(archetype)
    if template:
        msg = template.format(name=name, part=part)
    else:
        msg = f"{name}의 {part}에 기생체가 부착되었다."
    morld.add_action_log(msg)


# 주기적 반응 대사 풀 (아키타입별, 슬롯별)
_PERIODIC_REACTIONS = {
    "stoic": {
        "기생:가슴": ["{name}(이)가 이를 악물며 가슴의 자극을 참는다."],
        "기생:음부": ["{name}(이)가 묵묵히 하반신의 불쾌감을 견딘다."],
        "기생:항문": ["{name}(이)가 표정 없이 자극을 무시한다."],
        "기생:구강": ["{name}(이)가 입안의 이물감에 인상을 찌푸린다."],
        "_default": ["{name}(이)가 담담하게 자극을 견디고 있다."],
    },
    "gentle": {
        "기생:가슴": ["{name}(이)가 '음...' 하며 가슴의 자극에 신음을 흘린다."],
        "기생:음부": ["{name}(이)가 다리를 오므리며 촉수의 움직임에 몸을 떤다."],
        "_default": ["{name}(이)가 작은 신음을 흘린다."],
    },
    "timid": {
        "기생:가슴": ["{name}(이)가 '히잉...' 하며 눈물을 글썽인다."],
        "기생:음부": ["{name}(이)가 겁먹은 표정으로 몸을 웅크린다."],
        "_default": ["{name}(이)가 겁에 질려 몸을 떤다."],
    },
    "cheerful": {
        "기생:가슴": ["'이, 이거 간지럽...' {name}(이)가 불안한 웃음을 짓는다."],
        "기생:음부": ["{name}(이)가 억지웃음을 지으며 자극을 견디려 한다."],
        "_default": ["{name}(이)가 어색하게 웃으며 자극을 견딘다."],
    },
    "cold": {
        "기생:가슴": ["{name}의 차가운 표정 뒤로 미세한 떨림이 보인다."],
        "기생:음부": ["{name}(이)가 무표정하지만 호흡이 거칠어져 있다."],
        "_default": ["{name}(이)가 감정을 드러내지 않지만 불쾌해하고 있다."],
    },
    "seductive": {
        "기생:가슴": ["{name}(이)가 도발적인 미소로 자극을 즐기는 듯하다."],
        "기생:음부": ["{name}(이)가 입술을 깨물며 촉수의 움직임에 반응한다."],
        "_default": ["{name}(이)가 여유로운 표정으로 감각을 받아들이고 있다."],
    },
    "fierce": {
        "기생:가슴": ["{name}(이)가 이를 악물며 기생체를 뜯어내려 한다."],
        "기생:음부": ["'이 벌레 같은...!' {name}(이)가 분노하며 자극에 저항한다."],
        "_default": ["{name}(이)가 분노에 찬 표정으로 기생체와 싸우고 있다."],
    },
    "proud": {
        "기생:가슴": ["{name}(이)가 굴욕감에 얼굴을 붉히며 고개를 돌린다."],
        "기생:음부": ["'이런 치욕...' {name}(이)가 자존심이 상한 표정이다."],
        "_default": ["{name}(이)가 굴욕적인 상황에 입술을 깨물고 있다."],
    },
    "innocent": {
        "기생:가슴": ["{name}(이)가 무슨 일인지 이해 못한 채 당황하고 있다."],
        "기생:음부": ["{name}(이)가 이상한 감각에 혼란스러워하고 있다."],
        "_default": ["{name}(이)가 무슨 생물인지 신기해하면서도 무서워한다."],
    },
    "devoted": {
        "기생:가슴": ["{name}(이)가 주인을 걱정하며 자극을 참고 있다."],
        "기생:음부": ["{name}(이)가 주인에게 폐가 될까 자극을 감추려 한다."],
        "_default": ["{name}(이)가 주인만 바라보며 기생체의 자극을 견디고 있다."],
    },
}


def emit_periodic_reaction(unit_id, active_slots):
    """기생체 주기적 반응 대사 출력 (아키타입 기반)

    needs._update_climax()에서 호출.
    """
    from assets.characters import get_instance
    import random

    char = get_instance(unit_id)
    if not char:
        return
    archetype = getattr(char, 'archetype', None)
    if not archetype:
        return
    name = getattr(char, 'name', '?')

    pool = _PERIODIC_REACTIONS.get(archetype,
                                   _PERIODIC_REACTIONS.get("gentle", {}))
    # 활성 슬롯 중 하나에서 대사 선택
    for slot in active_slots:
        lines = pool.get(slot)
        if lines:
            morld.add_action_log(random.choice(lines).format(name=name))
            return
    # fallback
    lines = pool.get("_default", [])
    if lines:
        morld.add_action_log(random.choice(lines).format(name=name))
