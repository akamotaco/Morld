"""사회 핸들러 (Tier 4 인터럽트)

NPC-NPC 대화: 대상 탐색 → 이동 → 대화(30분) → 사회욕 감소
NPC→NPC 선물: 대상 탐색 → 이동 → 전달(5분) → 호감 증가
"""
import morld


# ========================================
# 상수
# ========================================

_LOVER_AFFECTION_THRESHOLD = 60  # 연인 판정 호감 임계치
_SOCIALIZE_COOLDOWN_MS = 3_600_000  # 1시간
_SOCIALIZE_SOCIAL_THRESHOLD = 70    # 사회욕 임계치


# ========================================
# NPC-NPC 발각 헬퍼
# ========================================

def _is_lover_npc(npc_id, other_id):
    """other_id가 npc_id의 연인 NPC인지 판정

    플레이어가 아닌 NPC 간 연인 관계 확인.
    호감도가 임계치 이상이면 연인으로 간주.
    """
    if other_id is None:
        return False

    # 플레이어면 False (플레이어 발각은 별도 처리)
    player_id = morld.get_player_id()
    if other_id == player_id:
        return False

    # NPC인지 확인
    from think import _agents
    if other_id not in _agents:
        return False

    # NPC → NPC 호감 확인 (양방향 중 어느 쪽이든)
    other_info = morld.get_unit_info(other_id)
    if not other_info:
        return False
    other_name = other_info.get("name", "")

    npc_props = morld.get_unit_props(npc_id)
    if npc_props:
        affection = npc_props.get(f"관계:{other_name}:호감", 0)
        if affection >= _LOVER_AFFECTION_THRESHOLD:
            return True

    return False


# ========================================
# NPC-NPC 대화 (사회욕 기반)
# ========================================

def _find_socialize_target(agent):
    """대화 대상 NPC 탐색 (같은 location, 수면/기절 중 아닌 NPC)"""
    my_loc = agent.get_location()
    if my_loc is None:
        return None

    from think import _agents
    for uid, other_agent in _agents.items():
        if uid == agent.unit_id:
            continue
        other_loc = other_agent.get_location()
        if other_loc is None:
            continue
        if other_loc[0] == my_loc[0] and other_loc[1] == my_loc[1]:
            # 수면/기절 중이면 스킵
            info = morld.get_unit_info(uid)
            if info:
                job_name = info.get("job_name", "")
                if job_name in ("sleep", "fainting"):
                    continue
            return uid

    return None


def _handle_socialize(agent):
    """NPC-NPC 대화: 대상 위치 이동 → 대화(30분) → 사회욕 감소"""
    phase = agent._memory["socialize_phase"]

    if phase == "idle":
        target_id = agent._memory.get("socialize_target_id")
        if target_id is None:
            agent._memory["socialize_phase"] = None
            agent._do_instant_action("대기", "abort")
            return

        target_loc = morld.get_unit_location(target_id)
        if target_loc is None:
            agent._memory["socialize_phase"] = None
            agent._memory["socialize_target_id"] = None
            agent._do_instant_action("대기", "abort")
            return

        target = {"region_id": target_loc[0], "location_id": target_loc[1]}
        if agent._is_at(target):
            agent._memory["socialize_phase"] = "talking"
            agent._do_instant_action("대화", "socialize")
        else:
            agent._memory["socialize_phase"] = "going"
            _handle_socialize(agent)

    elif phase == "going":
        target_id = agent._memory.get("socialize_target_id")
        if target_id is None:
            agent._memory["socialize_phase"] = None
            agent._do_instant_action("대기", "abort")
            return

        target_loc = morld.get_unit_location(target_id)
        if target_loc is None:
            agent._memory["socialize_phase"] = None
            agent._memory["socialize_target_id"] = None
            agent._do_instant_action("대기", "abort")
            return

        target = {"region_id": target_loc[0], "location_id": target_loc[1]}
        if agent._is_at(target):
            agent._memory["socialize_phase"] = "talking"
            agent._do_instant_action("대화", "socialize")
        else:
            agent._move_to(target, "대화")

    elif phase == "talking":
        # 대화 완료 → 양측 사회욕 감소
        try:
            import needs
            needs.reduce_social(agent.unit_id, 30)
            target_id = agent._memory.get("socialize_target_id")
            if target_id:
                needs.reduce_social(target_id, 15)  # 상대방은 절반
        except ImportError:
            pass

        agent._memory["socialize_phase"] = None
        agent._memory["socialize_target_id"] = None
        agent._memory["socialize_cooldown"] = agent.get_time()
        agent._do_instant_action("대화완료", "brief")


# ========================================
# NPC→NPC 선물
# ========================================

def _find_gift_item(agent):
    """NPC 인벤토리에서 선물 가능한 아이템 탐색 (장착 중 제외)"""
    import equipment as eq
    from assets.items import get_instance as get_item_instance

    inventory = morld.get_unit_inventory(agent.unit_id)
    if not inventory:
        return None

    equipped = eq.get_equipped_items(agent.unit_id) if hasattr(eq, 'get_equipped_items') else []
    equipped_ids = set(equipped) if equipped else set()

    for item_id, count in inventory.items():
        item_id_int = int(item_id)
        if item_id_int in equipped_ids:
            continue
        item_instance = get_item_instance(item_id_int)
        if item_instance is None:
            continue
        cat = item_instance.category
        if cat in ("flower", "trinket", "food_ingredient"):
            return item_id_int

    return None


def _find_gift_target(agent):
    """선물 대상 NPC 탐색 (같은 region, 호감 높은 NPC)"""
    my_loc = agent.get_location()
    if my_loc is None:
        return None

    my_region = my_loc[0]
    my_name = None
    my_info = morld.get_unit_info(agent.unit_id)
    if my_info:
        my_name = my_info.get("name", "")

    best_target = None
    best_aff = 0

    from think import _agents
    for uid, other_agent in _agents.items():
        if uid == agent.unit_id:
            continue
        other_loc = other_agent.get_location()
        if other_loc is None:
            continue
        if other_loc[0] != my_region:
            continue

        # 수면/기절 중이면 스킵
        info = morld.get_unit_info(uid)
        if info:
            job_name = info.get("job_name", "")
            if job_name in ("sleep", "fainting"):
                continue

        # 호감도 확인
        if my_name:
            props = morld.get_unit_props(uid) or {}
            aff = props.get(f"관계:{my_name}:호감", 0)
            if aff > best_aff:
                best_aff = aff
                best_target = uid

    return best_target


def _handle_gift(agent):
    """NPC→NPC 선물: 대상 이동 → 전달(5분) → 호감 증가"""
    phase = agent._memory["gift_phase"]

    if phase == "idle":
        target_id = agent._memory.get("gift_target_id")
        if target_id is None:
            _reset_gift(agent)
            agent._do_instant_action("대기", "abort")
            return

        target_loc = morld.get_unit_location(target_id)
        if target_loc is None:
            _reset_gift(agent)
            agent._do_instant_action("대기", "abort")
            return

        target = {"region_id": target_loc[0], "location_id": target_loc[1]}
        if agent._is_at(target):
            agent._memory["gift_phase"] = "giving"
            agent._do_instant_action("선물", "gift")
        else:
            agent._memory["gift_phase"] = "going"
            _handle_gift(agent)

    elif phase == "going":
        target_id = agent._memory.get("gift_target_id")
        if target_id is None:
            _reset_gift(agent)
            agent._do_instant_action("대기", "abort")
            return

        target_loc = morld.get_unit_location(target_id)
        if target_loc is None:
            _reset_gift(agent)
            agent._do_instant_action("대기", "abort")
            return

        target = {"region_id": target_loc[0], "location_id": target_loc[1]}
        if agent._is_at(target):
            agent._memory["gift_phase"] = "giving"
            agent._do_instant_action("선물", "gift")
        else:
            agent._move_to(target, "선물")

    elif phase == "giving":
        target_id = agent._memory.get("gift_target_id")
        item_id = agent._memory.get("gift_item_id")

        if target_id and item_id:
            # 아이템 전달
            if morld.has_item(agent.unit_id, item_id):
                morld.remove_item(agent.unit_id, item_id)
                morld.give_item(target_id, item_id)

            # 호감도 변경 (양측 +3)
            agent_info = morld.get_unit_info(agent.unit_id)
            target_info = morld.get_unit_info(target_id)
            if agent_info and target_info:
                agent_name = agent_info.get("name", "")
                target_name = target_info.get("name", "")
                if target_name:
                    morld.modify_prop(agent.unit_id, f"관계:{target_name}:호감", 3)
                if agent_name:
                    morld.modify_prop(target_id, f"관계:{agent_name}:호감", 5)

        _reset_gift(agent)
        agent._do_instant_action("선물완료", "brief")


def _reset_gift(agent):
    """선물 상태 초기화"""
    agent._memory["gift_phase"] = None
    agent._memory["gift_target_id"] = None
    agent._memory["gift_item_id"] = None
    agent._memory["gift_cooldown"] = agent.get_time()
