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
# 성인용품 헬퍼
# ========================================

def _try_use_toy(agent):
    """자위 시 삽입형 성인용품 사용 시도

    욕망 기반 사용 확률 + 캐릭터 선호도 + 감각 수치 기반 가중 랜덤 선택.
    삽입물 prop 설정 + 메모리에 기록.
    """
    import random
    try:
        from assets.items.adult_toys import INSERTABLE_ORIFICES
        import gender as gender_mod
    except ImportError:
        return

    # 욕망 기반 사용 확률: 욕망 40 미만이면 사용하지 않음
    from needs import _get_max_desire
    desire = _get_max_desire(agent.unit_id)
    arousal = morld.get_unit_prop(agent.unit_id, "상태:성욕") or 0
    # 사용 확률: desire 40→30%, 60→60%, 80→85%, 100→95%
    use_chance = max(0, min(0.95, (desire - 30) * 0.013 + (arousal - 50) * 0.003))
    if random.random() > use_chance:
        return

    inventory = morld.get_unit_items(agent.unit_id)
    if not inventory:
        return

    # 캐릭터 선호도 (없으면 기본값)
    toy_prefs = getattr(agent, 'toy_preferences', {})
    # 기본 선호: vibrator=0.5, dildo=0.3, rotor=0.4, anal_plug=0.2
    _DEFAULT_PREFS = {"vibrator": 0.5, "dildo": 0.3, "rotor": 0.4, "anal_plug": 0.2}

    # 후보 수집: (item_id, orifice, weight)
    candidates = []
    for item_id in inventory:
        item_info = morld.get_item_info(item_id)
        if not item_info:
            continue
        pp = item_info.get("passive_props", {})
        if not pp.get("성인용품:삽입형"):
            continue
        uid = item_info.get("unique_id", "")
        base_pref = toy_prefs.get(uid, _DEFAULT_PREFS.get(uid, 0.3))
        vib_rate = pp.get("성인용품:진동", 0) or item_info.get("vibration_rate", 0)

        for orifice in INSERTABLE_ORIFICES:
            # 해부학 호환 체크
            if orifice == "음부" and not gender_mod.has_anatomy(agent.unit_id, "V"):
                continue
            if orifice == "클리토리스" and not gender_mod.has_anatomy(agent.unit_id, "C"):
                continue
            if morld.get_unit_prop(agent.unit_id, f"삽입물:{orifice}"):
                continue
            # 가중치 계산: 선호도 × 욕망 보정 × 진동 보정
            weight = base_pref
            # 욕망 높을수록 강한 자극 선호
            if desire >= 70:
                weight *= (1.0 + vib_rate * 0.05)
            # 감각 수치 반영 (해당 부위 감각이 발달할수록 선호)
            _ORIFICE_STIM = {"음부": "V", "항문": "A", "클리토리스": "C"}
            stim_cat = _ORIFICE_STIM.get(orifice)
            if stim_cat:
                stim_val = morld.get_unit_prop(agent.unit_id,
                                               f"감각:{stim_cat}") or 0
                weight *= (1.0 + stim_val * 0.01)  # 감각 50 → +50%
            candidates.append((item_id, orifice, max(0.01, weight)))

    if not candidates:
        return

    # 가중 랜덤 선택
    total = sum(w for _, _, w in candidates)
    r = random.random() * total
    cumulative = 0
    for item_id, orifice, weight in candidates:
        cumulative += weight
        if r <= cumulative:
            morld.set_unit_prop(agent.unit_id, f"삽입물:{orifice}", item_id)
            agent._memory["self_comfort_toy"] = item_id
            agent._memory["self_comfort_toy_orifice"] = orifice
            return


def _cleanup_toy(agent):
    """자위 완료 시 삽입물 정리"""
    toy_id = agent._memory.get("self_comfort_toy")
    if toy_id:
        orifice = agent._memory.get("self_comfort_toy_orifice")
        if orifice:
            morld.clear_prop(agent.unit_id, f"삽입물:{orifice}")
        agent._memory.pop("self_comfort_toy", None)
        agent._memory.pop("self_comfort_toy_orifice", None)


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
        # 상체 결박 중이면 자위 불가
        import restraint
        if not restraint.can_use_hands(agent.unit_id):
            agent._memory["self_comfort_phase"] = None
            agent._do_instant_action("대기", "abort")
            return
        # P anatomy + 정액 부족 → 자위 포기
        try:
            import gender as gender_mod
            import semen as semen_mod
            if gender_mod.has_natural_anatomy(agent.unit_id, "P"):
                if not semen_mod.can_erect(agent.unit_id):
                    agent._memory["self_comfort_phase"] = None
                    agent._do_instant_action("대기", "abort")
                    return
        except ImportError:
            pass
        target = _resolve_private_location(agent)
        if target is None:
            agent._memory["self_comfort_phase"] = None
            agent._do_instant_action("대기", "abort")
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
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(target):
            agent._memory["self_comfort_phase"] = "performing"
            _handle_self_comfort(agent)
        else:
            agent._move_to(target, "이동")  # 이동 중엔 발각 안 됨

    elif phase == "performing":
        # 성인용품 보유 여부 체크 → 삽입형 사용
        _try_use_toy(agent)
        # 15분 자위 job 삽입 — job 완료 후 finishing 단계에서 결과 처리
        agent._memory["self_comfort_phase"] = "finishing"
        agent._do_instant_action("자위", "self_comfort")

    elif phase == "finishing":
        # 성인용품 정리
        _cleanup_toy(agent)
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

        # 성인용품 사용 시 효과 증가
        toy_used = agent._memory.get("self_comfort_toy") is not None
        base_reduction = 70 if toy_used else 50

        # P anatomy: 정액 소모/발기 체크
        _has_p = False
        _can_ejac = True
        try:
            import gender as gender_mod
            import semen as semen_mod
            _has_p = gender_mod.has_natural_anatomy(agent.unit_id, "P")
            if _has_p:
                _can_ejac = semen_mod.can_ejaculate(agent.unit_id)
        except ImportError:
            pass

        if alone:
            # P anatomy 정액 소모 + 효과 분기
            if _has_p:
                if _can_ejac:
                    try:
                        semen_mod.consume_semen(agent.unit_id, semen_mod.MASTURBATION_COST)
                    except Exception:
                        pass
                else:
                    base_reduction = 20  # 사정 불가 → 작은 해소
            # 성공: 성욕 감소 + 정상 쿨다운
            arousal = morld.get_unit_prop(agent.unit_id, "상태:성욕") or 0
            morld.set_unit_prop(agent.unit_id, "상태:성욕", max(0, arousal - base_reduction))
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
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(target):
            # 도착 → on_meet이 C# 이벤트로 자동 발화
            agent._memory["seek_player_phase"] = None
            agent._memory["seek_player_target"] = None
            agent._memory["self_comfort_cooldown"] = agent.get_time()
            agent._do_instant_action("대기", "brief")
        else:
            agent._move_to(target, "이동")


# ========================================
# NPC-NPC 성행위 핸들러
# ========================================

_NPC_INTIMACY_COOLDOWN_MS = 7_200_000    # 2시간
_NPC_INTIMACY_DURATION_MS = 30 * 60_000  # 30분


def _find_npc_lover(agent):
    """같은 location에 있는 합의/강제 대상 NPC 탐색

    Returns:
        (target_id, "consensual") — 양방향 호감 + 양쪽 성욕
        (target_id, "forced")     — 단방향 호감 + 체력 우위
        (None, None)              — 대상 없음
    """
    from .social import _is_lover_npc

    loc = agent.get_location()
    if not loc:
        return None, None
    chars = morld.get_characters_at_location(loc[0], loc[1])
    if not chars:
        return None, None

    player_id = morld.get_player_id()

    # Pass 1: 합의 (양방향 호감 + 양쪽 성욕)
    for char_id in chars:
        if char_id == agent.unit_id or char_id == player_id:
            continue
        if not _is_lover_npc(agent.unit_id, char_id):
            continue
        if not _is_lover_npc(char_id, agent.unit_id):
            continue  # 단방향 → pass 2
        info = morld.get_unit_info(char_id)
        if not info:
            continue
        job_name = info.get("job_name", "")
        if job_name in ("sleep", "fainting", "겁탈 중", "자위", "NPC 성행위"):
            continue
        if morld.get_unit_prop(char_id, "상태:NPC성행위중"):
            continue
        arousal = morld.get_unit_prop(char_id, "상태:성욕") or 0
        if arousal < 60:
            continue
        return char_id, "consensual"

    # Pass 2: 강제 (단방향 호감 + power 우위 + 성추행 모드)
    import settings
    if not settings.is_harassment_enabled():
        return None, None

    from romance_mode import get_unit_power
    import survival

    for char_id in chars:
        if char_id == agent.unit_id or char_id == player_id:
            continue
        if not _is_lover_npc(agent.unit_id, char_id):
            continue
        if _is_lover_npc(char_id, agent.unit_id):
            continue  # 양방향 → pass 1에서 처리됨
        # 수면/기절 제외 (의식 있는 상태여야)
        if survival.is_npc_fainted(char_id) or survival.is_npc_sleeping(char_id):
            continue
        info = morld.get_unit_info(char_id)
        if not info:
            continue
        job_name = info.get("job_name", "")
        if job_name in ("겁탈 중", "자위", "NPC 성행위"):
            continue
        if morld.get_unit_prop(char_id, "상태:NPC성행위중"):
            continue
        # 능력 체크: 이니시에이터 > 대상
        if get_unit_power(agent.unit_id) <= get_unit_power(char_id):
            continue
        return char_id, "forced"

    return None, None


def _handle_npc_intimacy(agent):
    """NPC-NPC 성행위: 은밀 장소 이동 → 수행(30분) → 완료

    Phase: idle → going → performing → finishing
    - 이니시에이터만 핸들러 실행
    - 파트너는 props로 상태 추적 (think에서 건너뜀)
    """
    phase = agent._memory["npc_intimacy_phase"]

    if phase == "idle":
        partner_id = agent._memory.get("npc_intimacy_partner")
        if partner_id is None:
            agent._memory["npc_intimacy_phase"] = None
            agent._do_instant_action("대기", "abort")
            return

        # 은밀 장소 탐색 (자위와 동일한 로직)
        target = _resolve_private_location(agent)
        if target is None:
            agent._memory["npc_intimacy_phase"] = None
            agent._do_instant_action("대기", "abort")
            return

        if agent._is_at(target):
            agent._memory["npc_intimacy_phase"] = "performing"
            _handle_npc_intimacy(agent)
        else:
            agent._memory["npc_intimacy_phase"] = "going"
            # 파트너도 따라오게
            from think import get_agent
            partner_agent = get_agent(partner_id)
            if partner_agent:
                partner_agent._move_to(target, "이동")
            agent._move_to(target, "이동")

    elif phase == "going":
        partner_id = agent._memory.get("npc_intimacy_partner")
        if partner_id is None:
            agent._memory["npc_intimacy_phase"] = None
            agent._do_instant_action("대기", "abort")
            return
        target = _resolve_private_location(agent)
        if target is None:
            _cleanup_npc_intimacy(agent)
            agent._do_instant_action("대기", "abort")
            return
        if agent._is_at(target):
            agent._memory["npc_intimacy_phase"] = "performing"
            _handle_npc_intimacy(agent)
        else:
            agent._move_to(target, "이동")

    elif phase == "performing":
        partner_id = agent._memory.get("npc_intimacy_partner")
        if partner_id is None:
            _cleanup_npc_intimacy(agent)
            agent._do_instant_action("대기", "abort")
            return

        mode = agent._memory.get("npc_intimacy_mode", "consensual")

        # props 설정 (describe 가시성)
        morld.set_unit_prop(agent.unit_id, "상태:NPC성행위중", 1)
        morld.set_unit_prop(agent.unit_id, "성행위:상대", partner_id)
        morld.set_unit_prop(partner_id, "상태:NPC성행위중", 1)
        morld.set_unit_prop(partner_id, "성행위:상대", agent.unit_id)

        # 강제 모드 추가 props
        if mode == "forced":
            morld.set_unit_prop(partner_id, "상태:NPC강제피해중", 1)
            morld.set_unit_prop(agent.unit_id, "상태:NPC강제가해중", 1)

        # 파트너 job 삽입 (30분)
        morld.clear_jobs(partner_id)
        morld.insert_job(partner_id, "NPC 성행위", "stay",
                         _NPC_INTIMACY_DURATION_MS, 0, 0)

        # 이니시에이터 job
        agent._memory["npc_intimacy_phase"] = "finishing"
        agent._do_instant_action("NPC 성행위", "npc_intimacy")

    elif phase == "finishing":
        partner_id = agent._memory.get("npc_intimacy_partner")
        mode = agent._memory.get("npc_intimacy_mode", "consensual")

        if partner_id:
            # 이니시에이터 성욕 감소 (공통)
            arousal_init = morld.get_unit_prop(agent.unit_id, "상태:성욕") or 0
            morld.set_unit_prop(agent.unit_id, "상태:성욕",
                                max(0, arousal_init - 50))

            if mode == "consensual":
                # 대상 성욕 감소 + 그리움 해소
                arousal_tgt = morld.get_unit_prop(partner_id, "상태:성욕") or 0
                morld.set_unit_prop(partner_id, "상태:성욕",
                                    max(0, arousal_tgt - 50))
                try:
                    import needs
                    partner_info = morld.get_unit_info(partner_id)
                    agent_info = morld.get_unit_info(agent.unit_id)
                    if partner_info and agent_info:
                        needs.reduce_longing(agent.unit_id,
                                             partner_info.get("name", ""))
                        needs.reduce_longing(partner_id,
                                             agent_info.get("name", ""))
                except ImportError:
                    pass
            else:
                # 강제: 피해자 페널티
                _apply_npc_forced_penalty(agent.unit_id, partner_id)

        _cleanup_npc_intimacy(agent)
        agent._memory["npc_intimacy_cooldown"] = agent.get_time()
        agent._do_instant_action("대기", "brief")


def _cleanup_npc_intimacy(agent):
    """NPC-NPC 성행위 상태 정리"""
    partner_id = agent._memory.get("npc_intimacy_partner")
    if partner_id:
        morld.clear_prop(partner_id, "상태:NPC성행위중")
        morld.clear_prop(partner_id, "성행위:상대")
        morld.clear_prop(partner_id, "상태:NPC강제피해중")
    morld.clear_prop(agent.unit_id, "상태:NPC성행위중")
    morld.clear_prop(agent.unit_id, "성행위:상대")
    morld.clear_prop(agent.unit_id, "상태:NPC강제가해중")
    agent._memory["npc_intimacy_phase"] = None
    agent._memory["npc_intimacy_partner"] = None
    agent._memory["npc_intimacy_mode"] = None


def _apply_npc_forced_penalty(initiator_id, victim_id):
    """NPC-NPC 강제 성행위 피해자 페널티

    기존 aftermath 시스템(상태:강제피해 3단계) 재사용.
    """
    initiator_info = morld.get_unit_info(initiator_id)
    initiator_name = initiator_info.get("name", "") if initiator_info else ""

    if initiator_name:
        # 반발 +15, 호감 -10
        morld.modify_prop(victim_id, f"관계:{initiator_name}:반발", 15)
        morld.modify_prop(victim_id, f"관계:{initiator_name}:호감", -10)

    # 기존 aftermath 3단계 재사용 → on_meet_player에서 자동 표시
    morld.set_unit_prop(victim_id, "상태:강제피해", 3)
    morld.modify_prop(victim_id, "기억:강제피해횟수", 1)
