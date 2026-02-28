# think/combat_mixin.py - 전투 + Tier 2 반응형 Mixin
#
# 전투 위협 감지, 구출, 간호, 소리 반응

import random
import morld


class CombatMixin:
    """전투 위협 감지/대응 + Tier 2 반응형 행동"""

    # ========================================
    # 전투 위협 감지 + 대응 (Tier 2)
    # ========================================

    COMBAT_ATTACK_DURATION = 6_000       # NPC 근접 공격 시간 (ms)
    COMBAT_END_COOLDOWN = 10 * 60_000    # 전투 종료 쿨다운 10분 (ms), 서브클래스 override 가능
    COMBAT_REGROUP_HP_THRESHOLD = 0.75   # 정비 종료 HP 비율 (75%), 서브클래스 override 가능
    COMBAT_DESPERATE_CHANCE = 0.5        # 포위 시 필사의 저항 확률 (0.0~1.0), 서브클래스 override

    def _check_combat_threat(self) -> bool:
        """전투 위협 감지 -> CombatState push

        FSM 기반: 전투 진행은 CombatState/FleeState 등이 처리.
        이 메서드는 새 적 감지 시 CombatState push만 담당.
        """
        behavior = getattr(self, 'BATTLE_BEHAVIOR', None)
        if not behavior:
            return False

        # 이미 전투 FSM 상태이면 (FSM dispatch가 처리, 여기 도달 불가. 안전장치)
        if any(s.state_type == "combat" for s in self._fsm_stack):
            return True

        # 적 탐색
        enemy_id = self._scan_nearest_enemy()
        if enemy_id is None:
            return False

        # evasive + HP 낮으면 즉시 도주
        style = behavior.get("combat_style", "aggressive")
        if style == "evasive":
            import survival as _surv
            my_hp = _surv.get_health(self.unit_id)
            my_max = _surv.get_max_health(self.unit_id)
            threshold = behavior.get("retreat_threshold", 0.5)
            if my_hp <= my_max * threshold:
                from think.fsm import CombatState, FleeState
                self._fsm_push(CombatState(enemy_id))
                self._fsm_push(FleeState())
                self._action_taken = True
                return True

        # 전투 개시
        from think.fsm import CombatState
        self._fsm_push(CombatState(enemy_id))
        self._action_taken = True
        return True

    def _scan_nearest_enemy(self):
        """현재 location에서 가장 가까운 적 unit_id 반환 (없으면 None)"""
        import combat as _combat

        my_loc = morld.get_unit_location(self.unit_id)
        if not my_loc:
            return None

        units = morld.get_units_at_location(my_loc[0], my_loc[1])
        enemy_id = None
        enemy_dist = float('inf')

        my_faction = morld.get_unit_prop(self.unit_id, "전투:세력")
        detect_range = morld.get_unit_prop(self.unit_id, "전투:감지거리") or 100

        for uid in units:
            if uid == self.unit_id:
                continue
            if morld.get_unit_prop(uid, "상태:사망"):
                continue
            their_faction = morld.get_unit_prop(uid, "전투:세력")
            is_enemy = _combat.is_faction_hostile(my_faction, their_faction)
            if not is_enemy:
                hostile_to = _combat.is_hostile_to(self.unit_id, uid)
                uid_info = morld.get_unit_info(uid)
                uid_name = uid_info.get("name", "?") if uid_info else "?"
                h = _combat.get_hostility(self.unit_id, uid_name)
                my_info = morld.get_unit_info(self.unit_id)
                my_name = my_info.get("name", "?") if my_info else "?"
                print(f"[DEBUG combat_threat] {my_name}(id={self.unit_id}) vs {uid_name}(id={uid}): faction_hostile=False, hostility={h}, hostile_to={hostile_to}")
                if hostile_to:
                    is_enemy = True
            if is_enemy:
                import survival as _surv
                if _surv.is_npc_fainted(uid):
                    continue
                dist = _combat.get_distance(self.unit_id, uid)
                if dist <= detect_range and dist < enemy_dist:
                    enemy_id = uid
                    enemy_dist = dist

        return enemy_id

    def _should_end_combat(self, last_enemy_ms=None) -> bool:
        """전투 종료 3-조건 판정 (모두 AND)

        1. 현재 location에 적 없음
        2. 전투 소리 미청취
        3. 마지막 적 목격/소리 + COMBAT_END_COOLDOWN 경과

        Args:
            last_enemy_ms: 마지막 적 목격 시각 (CombatState가 전달).
                           None이면 현재 시각 사용.
        """
        import combat as _combat

        my_loc = morld.get_unit_location(self.unit_id)
        if not my_loc:
            return True

        # 조건 1: 현재 location에 적 없음
        if _combat.has_enemies_at_location(self.unit_id, my_loc[0], my_loc[1]):
            return False

        # 조건 2: 전투 소리 미청취
        if _combat.hears_combat_sound(self.unit_id):
            return False

        # 조건 3: 쿨다운 경과
        if last_enemy_ms is None:
            last_enemy_ms = self.get_time()
        if self.get_time() - last_enemy_ms < self.COMBAT_END_COOLDOWN:
            return False

        return True

    # _handle_combat() 제거 - FSM states (CombatState/FleeState 등)로 대체

    def _is_valid_combat_target(self, target_id) -> bool:
        """전투 대상이 유효한지 (같은 location + 생존)"""
        import survival as _surv
        info = morld.get_unit_info(target_id)
        if not info:
            return False
        if morld.get_unit_prop(target_id, "상태:사망"):
            return False
        if _surv.is_npc_fainted(target_id):
            return False
        my_loc = morld.get_unit_location(self.unit_id)
        target_loc = morld.get_unit_location(target_id)
        if not my_loc or not target_loc:
            return False
        if my_loc[0] != target_loc[0] or my_loc[1] != target_loc[1]:
            return False
        return True

    def _make_location_target(self, region_id, location_id):
        """(region_id, location_id)를 _move_to용 dict로 변환"""
        region_info = morld.get_region_info(region_id)
        if not region_info:
            return None
        for loc in region_info.get("locations", []):
            if loc["id"] == location_id:
                return {
                    "region_id": region_id,
                    "location_id": location_id,
                    "length": loc.get("length", 0),
                }
        return None

    def _pick_safe_location(self):
        """안전한 도주 location 선택 (1~2 hop, 전투 소리 방향 제외)"""
        import combat as _combat

        my_loc = self.get_location()
        if not my_loc:
            return None

        # 전투 소리가 들리는 location (제외 대상)
        danger_locs = _combat.get_combat_sound_locations(self.unit_id)

        home_region = self._get_home_region()
        region_info = morld.get_region_info(home_region)
        if not region_info or "locations" not in region_info:
            return None

        # Gate 인접 정보로 1-hop 후보 수집
        loc_map = {}
        for loc in region_info["locations"]:
            loc_map[loc["id"]] = loc

        cur_loc_info = loc_map.get(my_loc[1])
        if not cur_loc_info:
            return None

        # 1-hop: 현재 location의 gate 연결
        hop1_ids = set()
        for gate in cur_loc_info.get("gates", []):
            cr = gate.get("connected_region", home_region)
            cl = gate.get("connected_local")
            if cl is not None and cr == home_region:
                if (cr, cl) not in danger_locs:
                    hop1_ids.add(cl)

        # 2-hop: 1-hop location의 gate 연결
        hop2_ids = set()
        for lid in hop1_ids:
            li = loc_map.get(lid)
            if not li:
                continue
            for gate in li.get("gates", []):
                cr = gate.get("connected_region", home_region)
                cl = gate.get("connected_local")
                if cl is not None and cr == home_region:
                    if cl != my_loc[1] and (cr, cl) not in danger_locs:
                        hop2_ids.add(cl)

        # 현재 위치 제외
        hop1_ids.discard(my_loc[1])
        hop2_ids.discard(my_loc[1])
        hop2_ids -= hop1_ids  # 중복 제거

        # 1-hop 우선, 없으면 2-hop
        candidates = list(hop1_ids) or list(hop2_ids)
        if not candidates:
            # 위험 지역 포함해서라도 도망
            candidates = [
                loc["id"] for loc in region_info["locations"]
                if loc["id"] != my_loc[1]
            ]

        if not candidates:
            return None

        target_lid = random.choice(candidates)
        target_loc_info = loc_map.get(target_lid, {})
        return {
            "region_id": home_region,
            "location_id": target_lid,
            "length": target_loc_info.get("length", 0),
        }

    # _end_combat() 제거 - CombatState.exit()로 대체

    def _is_surrounded(self) -> bool:
        """포위 판정: 현재 location에 적 존재 + 인접 모든 location에 적 기척

        포위 = (현재 위치에 적) AND (인접 전부에 전투 소리)
        """
        import combat as _combat

        my_loc = morld.get_unit_location(self.unit_id)
        if not my_loc:
            return False

        # 조건 1: 현재 location에 적 존재
        if not _combat.has_enemies_at_location(
                self.unit_id, my_loc[0], my_loc[1]):
            return False

        # 조건 2: 인접 모든 location에 전투 소리
        danger_locs = _combat.get_combat_sound_locations(self.unit_id)
        home_region = self._get_home_region()
        region_info = morld.get_region_info(home_region)
        if not region_info:
            return True  # 정보 없으면 포위로 간주

        # 현재 location의 인접 gate 목록
        cur_loc_info = None
        for loc in region_info.get("locations", []):
            if loc["id"] == my_loc[1]:
                cur_loc_info = loc
                break
        if not cur_loc_info:
            return True

        adjacent_ids = set()
        for gate in cur_loc_info.get("gates", []):
            cr = gate.get("connected_region", home_region)
            cl = gate.get("connected_local")
            if cl is not None:
                adjacent_ids.add((cr, cl))

        if not adjacent_ids:
            return True  # 인접 location 없음 = 막다른 곳

        # 모든 인접 location에 전투 소리가 들리는지
        for adj in adjacent_ids:
            if adj not in danger_locs:
                return False  # 하나라도 안전하면 포위 아님

        return True

    # _resolve_surrounded() 제거 - FleeState._resolve_surrounded()로 대체
    # _log_combat_phase() 제거 - 각 FSM State의 _log()로 대체

    # ========================================
    # 결박된 동료 발견 + 해제 (Tier 2)
    # ========================================

    RESCUE_DURATION = 3 * 60 * 1000  # 해제 소요 3분

    def _check_restrained_nearby(self):
        """같은 location에 결박된 비적대 유닛 발견 시 해제 시도

        Returns:
            True if action was taken (해제 진행/완료).
        """
        import restraint

        phase = self._memory.get("rescue_phase")
        if phase is None:
            # 탐색: 같은 location에 결박된 유닛 있는지
            my_loc = morld.get_unit_location(self.unit_id)
            if not my_loc:
                return False
            restrained = restraint.get_restrained_units_at(my_loc[0], my_loc[1])
            target = None
            for uid in restrained:
                if uid != self.unit_id:
                    target = uid
                    break
            if not target:
                return False
            self._memory["rescue_phase"] = "releasing"
            self._memory["rescue_target"] = target
            self._insert_idle_job("구출", self.RESCUE_DURATION)
            self._action_taken = True
            return True

        if phase == "releasing":
            target = self._memory.get("rescue_target")
            if target and restraint.is_restrained(target):
                restraint.release_unit(target)
                # 구출 대상의 restrained 메모리 정리
                from think.registry import _agents
                target_agent = _agents.get(target)
                if target_agent:
                    target_agent._memory["restrained_phase"] = None
                    target_agent._memory.pop("restrained_wait_until", None)
            self._memory.pop("rescue_phase", None)
            self._memory.pop("rescue_target", None)
            self._insert_idle_job("구출 완료", 1 * 60 * 1000)
            self._action_taken = True
            return True

        return False

    # ========================================
    # 탈진자 간호 (Tier 2)
    # ========================================

    _NURSING_REACTIONS = {
        "gentle": ["괜찮아? 좀 쉬어...", "내가 옆에 있을게."],
        "cheerful": ["이런, 무리하면 안 되지!", "금방 나을 거야!"],
        "stoic": ["...쉬어.", "무리하지 마."],
        "timid": ["저, 저기... 괜찮으세요...?", "어, 어떡하지..."],
        "cold": ["...바보.", "쓸데없이 무리해서."],
        "seductive": ["이런 모습도 귀엽네~", "내가 돌봐줄게♡"],
        "fierce": ["뭐야, 벌써 쓰러졌어?", "정신 차려!"],
        "proud": ["...어쩔 수 없지, 간호해주지.", "감사히 여겨."],
        "innocent": ["힘내요! 금방 나을 거예요!", "옆에 있어줄게요!"],
        "devoted": ["주인님, 괜찮으신가요?!", "제가 돌봐드릴게요..."],
    }

    def _check_exhausted_nearby(self):
        """같은 Location에 탈진된 캐릭터 → 간호"""
        import survival as _surv

        # 진행 중 → 계속
        if self._memory.get("nursing_phase") is not None:
            return self._handle_nursing()

        # 쿨다운 (1시간)
        now = self.get_time()
        last = self._memory.get("nursing_cooldown", 0)
        if now - last < 3_600_000:
            return False

        # 같은 Location 탈진자 탐색
        my_loc = morld.get_unit_location(self.unit_id)
        if not my_loc:
            return False
        chars = morld.get_characters_at_location(my_loc[0], my_loc[1])
        target_id = None
        for cid in (chars or []):
            if cid == self.unit_id:
                continue
            if morld.get_unit_prop(cid, "상태:사망"):
                continue
            if _surv.is_npc_exhausted(cid):
                target_id = cid
                break

        if target_id is None:
            return False

        self._memory["nursing_phase"] = "nursing"
        self._memory["nursing_target"] = target_id
        return self._handle_nursing()

    def _handle_nursing(self):
        """간호 실행 — 단일 phase"""
        import survival as _surv

        target_id = self._memory.get("nursing_target")
        if target_id is None:
            self._memory["nursing_phase"] = None
            return False

        if not _surv.is_npc_exhausted(target_id):
            # 대상이 이미 회복됨
            self._memory["nursing_phase"] = None
            self._memory["nursing_target"] = None
            self._memory["nursing_cooldown"] = self.get_time()
            return False

        # 간호 대사
        profile = getattr(self, 'REACTION_PROFILE', None) or {}
        archetype = profile.get("archetype", "stoic")
        texts = self._NURSING_REACTIONS.get(archetype,
                                            self._NURSING_REACTIONS["stoic"])
        reaction = random.choice(texts)
        morld.add_action_log(f"{self.name}: \"{reaction}\"")

        # HP 소폭 회복 (10)
        target_name = (morld.get_unit_info(target_id) or {}).get("name", "누군가")
        hp = morld.get_unit_prop(target_id, "생존:체력") or 0
        max_hp = morld.get_unit_prop(target_id, "생존:최대체력") or 100
        morld.set_unit_prop(target_id, "생존:체력", min(max_hp, hp + 10))

        # 간호 job (30분)
        self._insert_idle_job(f"{target_name} 간호", 30 * 60_000)

        # 완료
        self._memory["nursing_phase"] = None
        self._memory["nursing_target"] = None
        self._memory["nursing_cooldown"] = self.get_time()
        self._action_taken = True
        return True

    # ========================================
    # 소리 반응 (Tier 2)
    # ========================================

    # 소리 반응 상수
    SOUND_REACTION_COOLDOWN = 30 * 60 * 1000      # 30분
    SOUND_REACTION_COOLDOWN_MIN = 5 * 60 * 1000   # 최소 5분

    # 아키타입별 기본 소리 반응 프로필
    # investigate: 소리 원천으로 이동, cautious: 이동 (경계), avoid: 무시, ignore: 완전 무시
    _SOUND_REACTION_DEFAULTS = {
        "stoic":    {"전투": "investigate", "사고": "investigate"},
        "gentle":   {"전투": "cautious",    "사고": "investigate"},
        "cheerful": {"전투": "cautious",    "사고": "investigate"},
        "timid":    {"전투": "avoid",       "사고": "cautious"},
        "cold":     {"전투": "investigate", "사고": "investigate"},
    }

    # 서브클래스에서 오버라이드 가능 (dict: category → reaction)
    _sound_reaction_profile = None

    def _check_tier2_reactive(self):
        """Tier 2: 소리 반응 (비명, 전투, 사고)

        소리를 감지하고 아키타입에 따라 반응:
        - scream(비명): 모든 NPC 조사 (sound_type 레벨 오버라이드)
        - 전투/사고: 아키타입별 investigate/cautious/avoid/ignore

        Returns:
            True if action was taken.
        """
        try:
            import sound
        except ImportError:
            return False

        phase = self._memory.get("sound_reaction_phase")

        # --- phase: investigating (이동 완료 → 현장 확인) ---
        if phase == "investigating":
            self._memory.pop("sound_reaction_phase", None)
            self._memory.pop("sound_reaction_target", None)
            self._insert_idle_job("현장 확인", 1 * 60 * 1000)
            self._action_taken = True
            return True

        # --- 쿨다운 체크 ---
        cooldown = self._memory.get("sound_reaction_cooldown", 0)
        now = self.get_time()
        if now < cooldown:
            # 쿨다운 중 — 긴박한 소리 반복 시 쿨다운 단축
            heard_urgent = sound.get_heard_by_category(self.unit_id, "전투")
            if heard_urgent:
                remaining = cooldown - now
                if remaining > self.SOUND_REACTION_COOLDOWN_MIN:
                    new_cooldown = now + max(
                        self.SOUND_REACTION_COOLDOWN_MIN,
                        remaining // 2)
                    self._memory["sound_reaction_cooldown"] = new_cooldown
            return False

        # --- 소리 수집 ---
        heard_combat = sound.get_heard_by_category(self.unit_id, "전투")
        heard_accident = sound.get_heard_by_category(self.unit_id, "사고")
        all_events = heard_combat + heard_accident
        if not all_events:
            return False

        # 같은 location 소리 제외 (시각으로 이미 확인)
        my_loc = self.get_location()
        remote = [e for e in all_events if e.source_location != my_loc]
        if not remote:
            return False

        # 가장 강한 이벤트
        strongest = max(remote, key=lambda e: e.intensity)

        # 같은 소스에 이미 반응했으면 무시
        prev_source = self._memory.get("sound_reaction_source_id")
        if prev_source == strongest.source_id:
            return False

        # --- 반응 결정 ---
        # scream(비명)은 모든 NPC가 조사 (sound_type 레벨 오버라이드)
        if strongest.sound_type == "scream":
            reaction = "investigate"
        else:
            reaction = self._get_sound_reaction(strongest.category)

        if reaction in ("ignore", "avoid"):
            # 쿨다운 설정 + 소스 기록
            self._memory["sound_reaction_cooldown"] = (
                now + self.SOUND_REACTION_COOLDOWN)
            self._memory["sound_reaction_source_id"] = strongest.source_id
            return False

        # investigate / cautious → 소리 원천으로 이동
        target = {
            "region_id": strongest.source_location[0],
            "location_id": strongest.source_location[1],
        }
        self._memory["sound_reaction_phase"] = "investigating"
        self._memory["sound_reaction_target"] = strongest.source_location
        self._memory["sound_reaction_source_id"] = strongest.source_id
        self._memory["sound_reaction_cooldown"] = (
            now + self.SOUND_REACTION_COOLDOWN)

        self._move_to(target, "소리 조사")
        return True

    def _get_sound_reaction(self, category):
        """아키타입 기반 소리 반응 결정

        Args:
            category: 소리 카테고리 ("전투", "사고" 등)

        Returns:
            "investigate" / "cautious" / "avoid" / "ignore"
        """
        # 서브클래스 오버라이드 우선
        if self._sound_reaction_profile:
            return self._sound_reaction_profile.get(category, "ignore")
        # 아키타입에서 조회
        archetype = "stoic"
        try:
            profile = self.REACTION_PROFILE
            archetype = profile.get("archetype", "stoic")
        except AttributeError:
            pass
        defaults = self._SOUND_REACTION_DEFAULTS.get(archetype, {})
        return defaults.get(category, "ignore")
