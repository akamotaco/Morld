"""사회 핸들러 (Tier 4 인터럽트)

NPC-NPC 대화: 그리움 기반 대상 탐색 → 이동 → 대화(30분) → 그리움 해소
NPC→NPC 선물: 그리움 기반 대상 탐색 → 이동 → 전달(5분) → 호감 증가
"""
import morld


# ========================================
# 상수
# ========================================

_LOVER_AFFECTION_THRESHOLD = 60  # 연인 판정 호감 임계치
_SOCIALIZE_COOLDOWN_MS = 3_600_000  # 1시간


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
# 이름 → unit_id 조회
# ========================================

def _resolve_unit_by_name(name):
    """이름으로 unit_id 조회 (NPC + 플레이어)"""
    player_id = morld.get_player_id()
    if player_id:
        player_info = morld.get_unit_info(player_id)
        if player_info and player_info.get("name") == name:
            return player_id
    from think import _agents
    for uid in _agents:
        info = morld.get_unit_info(uid)
        if info and info.get("name") == name:
            return uid
    return None


# ========================================
# 그리움 기반 대상 탐색
# ========================================

def _find_most_missed(agent, threshold=70):
    """가장 그리운 대상 탐색 (NPC + 플레이어)

    그리움 ≥ threshold인 대상 중 가장 높은 값의 대상을 반환.
    수면/기절 중인 대상은 제외.

    Returns: (target_unit_id, longing_value) or (None, 0)
    """
    props = morld.get_unit_props(agent.unit_id)
    if not props:
        return None, 0

    best_id, best_val = None, 0
    for key, val in props.items():
        if not key.startswith("그리움:"):
            continue
        if not isinstance(val, (int, float)) or val < threshold:
            continue
        if val <= best_val:
            continue
        name = key.split(":", 1)[1]
        uid = _resolve_unit_by_name(name)
        if uid is None or uid == agent.unit_id:
            continue
        # 수면/기절 중 대상 제외
        info = morld.get_unit_info(uid)
        if info:
            job_name = info.get("job_name", "")
            if job_name in ("sleep", "fainting"):
                continue
        best_id = uid
        best_val = val

    return best_id, best_val


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
        # 대화 완료 → 양측 그리움 해소
        target_id = agent._memory.get("socialize_target_id")
        try:
            import needs
            target_info = morld.get_unit_info(target_id) if target_id else None
            agent_info = morld.get_unit_info(agent.unit_id)
            if target_info and agent_info:
                needs.reduce_longing(agent.unit_id,
                                     target_info.get("name", ""))
                needs.reduce_longing(target_id,
                                     agent_info.get("name", ""))
        except ImportError:
            pass

        # 평판 전파 (양방향)
        if target_id:
            try:
                import reputation
                reputation.propagate(agent.unit_id, target_id)
                reputation.propagate(target_id, agent.unit_id)
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
    """선물 대상 탐색 (그리움 ≥ 80, cross-region)"""
    uid, _ = _find_most_missed(agent, threshold=80)
    return uid


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
                import inventory as inv_module
                inv_module.safe_give_item(target_id, item_id)

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
