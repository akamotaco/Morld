"""성욕 핸들러 (Tier 4 인터럽트)

자위: 은밀 장소 탐색 → 이동 → 수행(15분) → 완료 확인
플레이어 탐색: 위치로 이동 → on_meet 자동 트리거
"""
import morld


# ========================================
# 상수
# ========================================

_SELF_COMFORT_COOLDOWN_MS = 7_200_000  # 2시간 (완료/플레이어 발각)
_SELF_COMFORT_INTERRUPT_COOLDOWN_MS = 1_800_000  # 30분 (NPC 방해로 중단)


# ========================================
# 은밀 장소 탐색
# ========================================

def _resolve_private_location(agent):
    """은밀 장소 탐색 — length 기반

    조건 (모두 충족):
      - 현재 NPC와 같은 region
      - length ≤ self_comfort_max_length
      - 현재 아무도 없는 location (본인 제외)
      - 실내 location
      - 오염도 낮은 location (오염 > 10 제외)

    우선순위: 현재 위치 → 침실 → 화장실 → region 내 가장 가까운 후보
    """
    from assets.registry import get_unique_id, get_location_class
    import pollution

    max_length = getattr(agent, 'self_comfort_max_length', 200)
    loc = agent.get_location()
    if not loc:
        return None
    cur_r, cur_l = loc[0], loc[1]

    def _is_valid(r, l):
        """location이 자위 장소로 적합한지 검사"""
        if r != cur_r:
            return False
        # length 조회 (registry → Location 클래스)
        uid = get_unique_id(l)
        if not uid:
            return False
        cls = get_location_class(uid)
        if not cls:
            return False
        length = getattr(cls, 'length', 0)
        if length <= 0 or length > max_length:
            return False
        # 실내만
        if not getattr(cls, 'is_indoor', True):
            return False
        # 오염도
        pol = pollution.get_location_pollution(r, l)
        if pol > 10:
            return False
        # 비어있는지 (본인 제외)
        units = morld.get_characters_at_location(r, l)
        if units and any(u != agent.unit_id for u in units):
            return False
        return True

    # 1. 현재 위치 (이동 불필요)
    if _is_valid(cur_r, cur_l):
        return {"region_id": cur_r, "location_id": cur_l, "x": 0}

    # 2. 침실 (소유 침대 위치)
    owner = getattr(agent, 'owner_unique_id', None)
    if owner:
        from think.facility_resolver import _find_facilities_by_prop
        beds = _find_facilities_by_prop(f"bed_owner:{owner}", 1)
        if beds:
            bed = beds[0]
            if _is_valid(bed["region_id"], bed["location_id"]):
                return bed

    # 3. 화장실
    from think.facility_resolver import resolve_toilet
    toilet = resolve_toilet(agent)
    if toilet:
        if _is_valid(toilet["region_id"], toilet["location_id"]):
            return toilet

    # 4. region 내 가장 가까운 후보
    region_info = morld.get_region_info(cur_r)
    if region_info and "locations" in region_info:
        best = None
        best_dist = 999999
        for loc_info in region_info["locations"]:
            lid = loc_info["id"]
            if lid == cur_l:
                continue  # 이미 체크함
            if not _is_valid(cur_r, lid):
                continue
            dist = abs(lid - cur_l)  # location_id 거리 (인접 기준)
            if dist < best_dist:
                best_dist = dist
                best = {"region_id": cur_r, "location_id": lid, "x": 0}
        if best is not None:
            return best

    return None


# ========================================
# 자위 핸들러
# ========================================

def _handle_self_comfort(agent):
    """자위: 은밀 장소 이동 → 수행 → 완료 확인

    Phase: idle → going → performing → finishing
    - performing: 15분 job 삽입 (job name="자위" → 플레이어 발각 대상)
    - finishing: job 완료 후 주변 확인 → 혼자면 성욕 감소, 타인 있으면 중단
    """
    phase = agent._memory["self_comfort_phase"]

    if phase == "idle":
        target = _resolve_private_location(agent)
        if target is None:
            agent._memory["self_comfort_phase"] = None
            return
        if agent._is_at(target):
            agent._memory["self_comfort_phase"] = "performing"
            _handle_self_comfort(agent)
        else:
            agent._memory["self_comfort_phase"] = "going"
            _handle_self_comfort(agent)
        return

    elif phase == "going":
        target = _resolve_private_location(agent)
        if target is None:
            agent._memory["self_comfort_phase"] = None
            return
        if agent._is_at(target):
            agent._memory["self_comfort_phase"] = "performing"
            _handle_self_comfort(agent)
        else:
            agent._move_to(target, "이동")  # 이동 중엔 발각 안 됨

    elif phase == "performing":
        # 15분 자위 job 삽입 — job 완료 후 finishing 단계에서 결과 처리
        agent._memory["self_comfort_phase"] = "finishing"
        agent._do_instant_action("자위", "self_comfort")

    elif phase == "finishing":
        # job 완료 → 주변 확인
        loc = agent.get_location()
        alone = True
        discovered_by = None
        if loc:
            units = morld.get_characters_at_location(loc[0], loc[1])
            if units:
                for u in units:
                    if u != agent.unit_id:
                        alone = False
                        discovered_by = u
                        break

        if alone:
            # 성공: 성욕 감소 + 정상 쿨다운
            arousal = morld.get_unit_prop(agent.unit_id, "상태:성욕") or 0
            morld.set_unit_prop(agent.unit_id, "상태:성욕", max(0, arousal - 50))
            agent._memory["self_comfort_phase"] = None
            agent._memory["self_comfort_cooldown"] = agent.get_time()
            agent._do_instant_action("대기", "brief")
        else:
            # 발각 — 발각자가 연인 NPC인지 확인
            from .social import _is_lover_npc
            is_lover = _is_lover_npc(agent.unit_id, discovered_by)
            if is_lover:
                # 연인 발각: 성욕 절반 감소 + 정상 쿨다운 (수치심 경감)
                arousal = morld.get_unit_prop(agent.unit_id, "상태:성욕") or 0
                morld.set_unit_prop(agent.unit_id, "상태:성욕", max(0, arousal - 25))
                agent._memory["self_comfort_phase"] = None
                agent._memory["self_comfort_cooldown"] = agent.get_time()
                agent._do_instant_action("대기", "brief")
            else:
                # 비연인 발각 — 성욕 감소 없음, 짧은 쿨다운으로 재시도 유도
                agent._memory["self_comfort_phase"] = None
                agent._memory["self_comfort_cooldown"] = (
                    agent.get_time() - _SELF_COMFORT_COOLDOWN_MS + _SELF_COMFORT_INTERRUPT_COOLDOWN_MS
                )
                agent._do_instant_action("대기", "brief")


# ========================================
# 플레이어 탐색 핸들러
# ========================================

def _handle_seek_player(agent):
    """플레이어 탐색: 위치로 이동 → on_meet 자동 트리거"""
    phase = agent._memory["seek_player_phase"]

    if phase == "idle":
        agent._memory["seek_player_phase"] = "going"
        _handle_seek_player(agent)
        return

    elif phase == "going":
        target = agent._memory.get("seek_player_target")
        if target is None:
            agent._memory["seek_player_phase"] = None
            return
        if agent._is_at(target):
            # 도착 → on_meet이 C# 이벤트로 자동 발화
            agent._memory["seek_player_phase"] = None
            agent._memory["seek_player_target"] = None
            agent._memory["self_comfort_cooldown"] = agent.get_time()
            agent._do_instant_action("대기", "brief")
        else:
            agent._move_to(target, "이동")
