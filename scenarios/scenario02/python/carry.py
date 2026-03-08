# carry.py - 유닛 운반 시스템
#
# 통합 Limbo + Pointer Item 방식:
#   pick_up: target을 Limbo로 텔레포트 + 포인터 아이템을 carrier 인벤토리에 추가
#   put_down: target을 carrier 현재 위치로 텔레포트 + 포인터 아이템 제거
#
# 포인터 아이템:
#   - unique_id = "carry:{unit_unique_id}:{unit_id}" (유일)
#   - passive_props = {"운반:참조": unit_id}
#   - 인벤토리에서 "내려놓기" 액션 제공
#
# Props:
#   운반자: 운반:대상 = carried_unit_id, 운반:방식 = carry_rescue|carry_forced|carry_object
#   피운반자: 운반:운반자 = carrier_unit_id
#
# 용량 제한: 1명/1개
#
# TODO (향후 확장):
#   - 복수 운반: 용량 제한 해제 + UI 변경
#   - NPC AI 운반: think activity handler (구조/어부바)
#   - 건설 시스템: 오브젝트 배치/회수 (건설 아이템 에셋)
#   - 시체 시스템: 사망→시체 전환 연동 (전투 시스템 의존)
#   - 수면 중 운반: 수면 유형 prop 추가 (자연수면 vs 탈진수면)
#   - 운반 중 NPC 목격 반응: 이벤트 시스템 연동
#   - 포인터 아이템 cleanup: RemoveItem Python API 노출 후 정의 제거

import morld

# Limbo region 상수 (chapters/__init__.py와 공유)
LIMBO_REGION = 99
LIMBO_LOCATION = 0

# 운반 방식
METHOD_RESCUE = "carry_rescue"      # 구조 (기절/탈진)
METHOD_FORCED = "carry_forced"      # 강제 (결박)
METHOD_OBJECT = "carry_object"      # 오브젝트 운반

# Props
PROP_CARRIED_BY = "운반:운반자"     # 피운반자에 설정 (value = carrier unit_id)
PROP_CARRYING = "운반:대상"         # 운반자에 설정 (value = carried unit_id)
PROP_CARRY_METHOD = "운반:방식"     # 운반자에 설정 (value = method hash)

# 포인터 아이템 레지스트리: item_id → carried unit_id
_carry_registry = {}


def reset():
    """챕터 전환 시 호출 — 레지스트리 초기화"""
    _carry_registry.clear()


# ========================================
# 조회 API
# ========================================

def is_being_carried(unit_id):
    """unit이 현재 운반 중인가?"""
    return bool(morld.get_unit_prop(unit_id, PROP_CARRIED_BY))


def get_carrier(unit_id):
    """unit을 운반 중인 carrier의 unit_id (없으면 None)"""
    carrier_id = morld.get_unit_prop(unit_id, PROP_CARRIED_BY)
    return carrier_id if carrier_id else None


def is_carrying(carrier_id):
    """carrier가 현재 무언가를 운반 중인가?"""
    return bool(morld.get_unit_prop(carrier_id, PROP_CARRYING))


def get_carried_unit(carrier_id):
    """carrier가 운반 중인 unit_id (없으면 None)"""
    carried_id = morld.get_unit_prop(carrier_id, PROP_CARRYING)
    return carried_id if carried_id else None


def get_carry_method(carrier_id):
    """carrier의 운반 방식 (hash → string 변환은 향후)"""
    return morld.get_unit_prop(carrier_id, PROP_CARRY_METHOD)


# ========================================
# 검증 API
# ========================================

def can_pick_up(carrier_id, target_id):
    """
    운반 가능 여부 검증

    Returns:
        (bool, str): (가능 여부, 사유 메시지)
    """
    # 1. carrier가 이미 운반 중
    if is_carrying(carrier_id):
        return False, "이미 무언가를 들고 있다."

    # 2. target이 이미 운반 중
    if is_being_carried(target_id):
        return False, "이미 누군가가 들고 있다."

    # 3. 자기 자신
    if carrier_id == target_id:
        return False, "자기 자신은 들 수 없다."

    # 4. target 상태 검증 (캐릭터 vs 오브젝트)
    target_info = morld.get_unit_info(target_id)
    if not target_info:
        return False, "대상을 찾을 수 없다."

    is_object = target_info.get("is_object", False)

    if is_object:
        # 오브젝트: 사용 중(좌석 점유)이면 불가
        seated_by = morld.get_unit_props_by_type(target_id, "seated_by")
        if seated_by:
            for slot_name, occupant_id in seated_by.items():
                if occupant_id != -1:
                    return False, "누군가 사용 중이라 들 수 없다."
        return True, ""
    else:
        # 캐릭터: 기절 OR 하체결박 상태만 가능
        import survival
        import restraint

        if survival.is_npc_fainted(target_id):
            return True, ""
        if survival.is_npc_exhausted(target_id):
            return True, ""
        if restraint.is_lower_restrained(target_id):
            return True, ""

        # TODO: 수면 유형 prop 추가 시 자연수면도 운반 허용
        return False, "의식이 있고 움직일 수 있는 상대는 들 수 없다."


# ========================================
# 실행 API
# ========================================

def pick_up(carrier_id, target_id, method=None):
    """
    target을 들어올리기

    Args:
        carrier_id: 운반자 unit_id
        target_id: 대상 unit_id
        method: 운반 방식 (None이면 자동 판정)

    Returns:
        bool: 성공 여부
    """
    ok, reason = can_pick_up(carrier_id, target_id)
    if not ok:
        print(f"[carry] pick_up failed: {reason}")
        return False

    # 자동 방식 판정
    if method is None:
        target_info = morld.get_unit_info(target_id)
        is_object = target_info.get("is_object", False) if target_info else False
        if is_object:
            method = METHOD_OBJECT
        else:
            import restraint
            if restraint.is_lower_restrained(target_id):
                method = METHOD_FORCED
            else:
                method = METHOD_RESCUE

    # 1. Target을 Limbo로 텔레포트
    morld.set_unit_location(target_id, LIMBO_REGION, LIMBO_LOCATION)

    # 2. 포인터 아이템 생성
    item_id = _create_carry_item(target_id)
    if item_id is None:
        # 실패 시 복구: target을 carrier 위치로 되돌림
        carrier_info = morld.get_unit_info(carrier_id)
        if carrier_info:
            morld.set_unit_location(
                target_id,
                carrier_info["region_id"],
                carrier_info["location_id"]
            )
        return False

    # 3. 포인터를 carrier 인벤토리에 추가
    morld.give_item(carrier_id, item_id, 1)

    # 4. Props 설정
    morld.set_unit_prop(carrier_id, PROP_CARRYING, target_id)
    morld.set_unit_prop(carrier_id, PROP_CARRY_METHOD, hash(method) % 1000)
    morld.set_unit_prop(target_id, PROP_CARRIED_BY, carrier_id)

    print(f"[carry] pick_up: carrier={carrier_id} target={target_id} method={method}")
    return True


def put_down(carrier_id):
    """
    운반 중인 unit을 내려놓기

    Returns:
        bool: 성공 여부
    """
    carried_id = get_carried_unit(carrier_id)
    if not carried_id:
        print("[carry] put_down failed: nothing being carried")
        return False

    # 1. Carrier의 현재 위치 확인
    carrier_info = morld.get_unit_info(carrier_id)
    if not carrier_info:
        return False

    region_id = carrier_info["region_id"]
    location_id = carrier_info["location_id"]

    # 2. Target을 carrier 현재 위치로 텔레포트
    morld.set_unit_location(carried_id, region_id, location_id)

    # 3. 포인터 아이템 제거
    item_id = _find_carry_item(carrier_id, carried_id)
    if item_id is not None:
        morld.lost_item(carrier_id, item_id, 1)
        _carry_registry.pop(item_id, None)

    # 4. Props 해제
    morld.set_unit_prop(carrier_id, PROP_CARRYING, 0)
    morld.set_unit_prop(carrier_id, PROP_CARRY_METHOD, 0)
    morld.set_unit_prop(carried_id, PROP_CARRIED_BY, 0)

    # TODO: 캐릭터 의식 상태에 따른 이벤트 발화 (기절 해제 시 대사/반응)
    print(f"[carry] put_down: carrier={carrier_id} target={carried_id} at {region_id}:{location_id}")
    return True


# ========================================
# 포인터 아이템 관리
# ========================================

def _create_carry_item(target_id):
    """
    운반 대상에 대한 포인터 아이템을 동적 생성

    Returns:
        int: 생성된 item_id (실패 시 None)
    """
    target_info = morld.get_unit_info(target_id)
    if not target_info:
        return None

    target_name = target_info.get("name", "???")
    target_unique_id = target_info.get("unique_id", str(target_id))

    # 고유 item_id 발급
    item_id = morld.create_id("item")
    carry_unique_id = f"carry:{target_unique_id}:{target_id}"

    # C# ItemSystem에 아이템 정의 등록
    morld.add_item(
        item_id,
        f"[{target_name}]",                      # 인벤토리 표시명
        {"운반:참조": target_id},                 # passive_props
        {},                                        # equip_props
        0,                                         # value
        ["call:put_down:내려놓기"],                # actions
        None,                                      # owner
        carry_unique_id,                           # unique_id
        {},                                        # action_props
    )

    # Python 인스턴스 등록 (call: 액션 해석용)
    from assets.items import register_instance
    token = _CarryToken(item_id, target_id, target_name)
    register_instance(item_id, token)

    # 레지스트리 등록
    _carry_registry[item_id] = target_id

    return item_id


def _find_carry_item(carrier_id, carried_id):
    """carrier 인벤토리에서 carried_id에 대한 포인터 아이템 찾기"""
    for item_id, unit_id in _carry_registry.items():
        if unit_id == carried_id:
            # carrier가 실제로 소유하고 있는지 확인
            if morld.has_item(carrier_id, item_id):
                return item_id
    return None


class _CarryToken:
    """
    운반 포인터 아이템의 Python 인스턴스

    call:put_down 액션을 처리하기 위해 존재.
    Item 클래스를 상속하지 않고 최소한의 인터페이스만 구현.
    """

    def __init__(self, instance_id, carried_unit_id, carried_name):
        self.instance_id = instance_id
        self._carried_unit_id = carried_unit_id
        self._carried_name = carried_name
        self.name = f"[{carried_name}]"

    def put_down(self):
        """내려놓기 — 인벤토리 액션에서 호출"""
        import ui
        player_id = morld.get_player_id()
        success = put_down(player_id)
        if success:
            yield ui.dialog([f"{self._carried_name}을(를) 내려놓았다."])
        else:
            yield ui.dialog(["내려놓을 수 없다."])
