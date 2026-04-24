# think/interrupt_mixin.py - 인터럽트 + 욕구 체크 Mixin
#
# Tier 1 (비자발적), 결박, Tier 3 (생존), Tier 4 (쾌적) 처리
# BaseAgent에서 분리된 Mixin 클래스.

import morld

from think.handlers import (
    _handle_eat, _handle_excretion,
    _handle_cold, _handle_hot, _handle_clothing, _is_dressed,
    _handle_self_comfort, _handle_seek_player,
    _handle_npc_intimacy, _find_npc_lover,
    _NPC_INTIMACY_COOLDOWN_MS,
    _SELF_COMFORT_COOLDOWN_MS,
    _handle_socialize, _handle_gift,
    _find_most_missed, _find_gift_item, _find_gift_target,
)
from think.handlers.self_comfort import _resolve_private_location
from think.handlers.laundry import _handle_laundry, _find_dirty_equipped_clothing


class InterruptMixin:
    """Tier 1 (비자발적), 결박, Tier 3 (생존), Tier 4 (쾌적) 인터럽트"""

    # ========================================
    # Tier 1: 비자발적 상태
    # ========================================

    def _check_tier1_involuntary(self):
        """Tier 1: 비자발적 상태 (기절, 수면 중)

        이 상태의 NPC는 어떤 인터럽트도 받지 않음.
        _ensure_standing() 호출 전이므로 침대에 누운 상태 유지.

        Returns:
            True if action was taken.
        """
        # 1a. 기절
        import survival
        if survival.is_npc_fainted(self.unit_id):
            remaining = survival.get_faint_remaining_millis(self.unit_id)
            self._insert_idle_job("fainting", max(remaining, 1))  # 기절 잔여 시간 — survival 시스템 연동
            self._action_taken = True
            return True

        # 1a-2. 탈진
        if survival.is_npc_exhausted(self.unit_id):
            remaining = survival.get_exhaustion_remaining_millis(self.unit_id)
            self._insert_idle_job("exhaustion", max(remaining, 1))
            self._action_taken = True
            return True

        # 1b. 이미 침대에서 자는 중
        already_sleeping, sleep_entry = self._is_already_sleeping()
        if already_sleeping:
            # 추위 기상: 체온이 위험 수준이면 깨어남
            try:
                import temperature
                if temperature.is_cold(self.unit_id, threshold=35.0):
                    # 침대에서 일어남 → tier 3 cold 처리로 이관
                    return False
            except ImportError:
                pass
            remaining = self._remaining_millis_in_entry(sleep_entry)
            self._insert_idle_job("sleep", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            self._action_taken = True
            return True

        return False

    # ========================================
    # 결박 상태 처리 (Tier 0)
    # ========================================

    RESTRAINED_ESCAPE_INTERVAL = 30 * 60 * 1000  # 30분마다 해제 시도

    def _handle_being_carried(self):
        """운반 중 상태 처리 — Limbo에서 대기

        운반자가 들고 있는 동안 idle job만 삽입.
        기절 상태가 해제되면 의식 회복 → 비결박 시 자동 해방.
        """
        import survival
        import carry

        # 기절/탈진 해제 확인
        if not survival.is_npc_fainted(self.unit_id) and not survival.is_npc_exhausted(self.unit_id):
            # 의식 회복 + 행동 가능
            import restraint
            if not restraint.is_lower_restrained(self.unit_id):
                # 비결박 → 자동 해방
                carrier_id = carry.get_carrier(self.unit_id)
                if carrier_id:
                    carry.put_down(carrier_id)
                    info = self.get_info()
                    name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
                    print(f"[think] {name}: 의식 회복 → 운반에서 해방")
                # 해방 후 일반 think 재호출되므로 여기서는 idle만
                self._insert_idle_job("의식 회복", 60_000)
                self._action_taken = True
                return
            # TODO: 결박 상태 저항 대사 (의식 있음 + 결박 → 운반 계속하되 반응)

        # TODO: 운반 중 NPC 목격 반응 이벤트 발화
        # 운반 중 대기 (1시간)
        self._insert_idle_job("운반 중", 3_600_000)
        self._action_taken = True

    def _handle_restrained(self):
        """결박 상태 처리 — 모든 일상 행동 차단

        3-phase: idle → escaping → waiting
        - idle: 해제 시도 가능 여부 체크
        - escaping: 자력 해제 시도
        - waiting: 대기 (30분마다 재시도). 입 자유 시 소리치기
        """
        import restraint
        import survival

        # 방어: 외부에서 이미 해제된 경우 (구출 등) — 메모리 정리
        if not restraint.is_restrained(self.unit_id):
            self._memory["restrained_phase"] = None
            self._memory.pop("restrained_wait_until", None)
            return

        # 행동불능(기절/탈진/수면) → 탈출 시도 없이 대기
        if survival.is_npc_incapacitated(self.unit_id) or survival.is_npc_sleeping(self.unit_id):
            if survival.is_npc_fainted(self.unit_id):
                remaining = survival.get_faint_remaining_millis(self.unit_id)
                self._insert_idle_job("fainting", max(remaining, 1))
            elif survival.is_npc_exhausted(self.unit_id):
                remaining = survival.get_exhaustion_remaining_millis(self.unit_id)
                self._insert_idle_job("exhaustion", max(remaining, 1))
            else:
                self._insert_idle_job("결박", self.RESTRAINED_ESCAPE_INTERVAL)
            self._action_taken = True
            return

        phase = self._memory.get("restrained_phase", "idle")

        if phase == "idle":
            # 처음 결박됨 or 대기 후 재시도
            self._memory["restrained_phase"] = "escaping"
            self._insert_idle_job("결박 해제 시도", 5 * 60 * 1000)  # 5분 걸림
            self._action_taken = True
            return

        if phase == "escaping":
            if restraint.attempt_self_escape(self.unit_id):
                # 성공: 사지 결박 해제
                restraint.release_self(self.unit_id)
                # 사지 해제 후 입/눈도 해제
                if not restraint.is_restrained(self.unit_id):
                    if restraint.is_gagged(self.unit_id):
                        restraint.release_mouth(self.unit_id)
                    if restraint.is_blindfolded(self.unit_id):
                        restraint.release_eyes(self.unit_id)
                self._memory["restrained_phase"] = "idle"
                self._insert_idle_job("결박 해제됨", 1 * 60 * 1000)
            else:
                # 실패: 대기 상태로 전환
                self._memory["restrained_phase"] = "waiting"
                self._memory["restrained_wait_until"] = (
                    self.get_time() + self.RESTRAINED_ESCAPE_INTERVAL
                )
                self._insert_idle_job("결박", self.RESTRAINED_ESCAPE_INTERVAL)
            self._action_taken = True
            return

        if phase == "waiting":
            # 입이 자유로우면 도움 요청
            if not restraint.is_gagged(self.unit_id):
                try:
                    import sound
                    sound.emit_sound(self.unit_id, "scream", 80)
                except ImportError:
                    pass

            # 결박 중 복종 소폭 상승 (+0.5/30분)
            player_id = morld.get_player_id()
            if player_id:
                player_info = morld.get_unit_info(player_id)
                if player_info:
                    pname = player_info.get("name", "주인공")
                    sub_key = f"관계:{pname}:복종"
                    sub_val = morld.get_unit_prop(self.unit_id, sub_key) or 0
                    morld.set_unit_prop(self.unit_id, sub_key,
                                        min(100, sub_val + 0.5))

            wait_until = self._memory.get("restrained_wait_until", 0)
            if self.get_time() >= wait_until:
                # 재시도
                self._memory["restrained_phase"] = "idle"
            self._insert_idle_job("결박", self.RESTRAINED_ESCAPE_INTERVAL)
            self._action_taken = True
            return

    def _handle_upper_restrained(self):
        """상체만 결박 — 이동 가능하지만 손 사용 불가

        이동은 가능하므로 도움을 요청하며 돌아다닌다.
        30분마다 자력 해제를 시도한다.
        """
        import restraint
        import survival

        # 방어: 외부에서 이미 해제된 경우 (구출 등) — 메모리 정리
        if not restraint.is_upper_restrained(self.unit_id):
            self._memory["restrained_phase"] = None
            self._memory.pop("restrained_wait_until", None)
            return

        # 행동불능(기절/탈진/수면) → 탈출 시도 없이 대기
        if survival.is_npc_incapacitated(self.unit_id) or survival.is_npc_sleeping(self.unit_id):
            if survival.is_npc_fainted(self.unit_id):
                remaining = survival.get_faint_remaining_millis(self.unit_id)
                self._insert_idle_job("fainting", max(remaining, 1))
            elif survival.is_npc_exhausted(self.unit_id):
                remaining = survival.get_exhaustion_remaining_millis(self.unit_id)
                self._insert_idle_job("exhaustion", max(remaining, 1))
            else:
                self._insert_idle_job("결박", self.RESTRAINED_ESCAPE_INTERVAL)
            self._action_taken = True
            return

        phase = self._memory.get("restrained_phase", "idle")

        if phase == "idle":
            self._memory["restrained_phase"] = "escaping"
            self._insert_idle_job("결박 해제 시도", 5 * 60 * 1000)
            self._action_taken = True
            return

        if phase == "escaping":
            if restraint.attempt_self_escape(self.unit_id):
                restraint.release_self(self.unit_id)
                if not restraint.is_restrained(self.unit_id):
                    if restraint.is_gagged(self.unit_id):
                        restraint.release_mouth(self.unit_id)
                    if restraint.is_blindfolded(self.unit_id):
                        restraint.release_eyes(self.unit_id)
                self._memory["restrained_phase"] = "idle"
                self._insert_idle_job("결박 해제됨", 1 * 60 * 1000)
            else:
                self._memory["restrained_phase"] = "wandering"
                self._memory["restrained_wait_until"] = (
                    self.get_time() + self.RESTRAINED_ESCAPE_INTERVAL
                )
                # 입이 자유로우면 소리치기
                if not restraint.is_gagged(self.unit_id):
                    try:
                        import sound
                        sound.emit_sound(self.unit_id, "scream", 80)
                    except ImportError:
                        pass
                # 이동 가능 — 랜덤 배회
                self._do_wander()
            self._action_taken = True
            return

        if phase == "wandering":
            # 상체 결박 중 복종 소폭 상승 (+0.3/30분)
            player_id = morld.get_player_id()
            if player_id:
                player_info = morld.get_unit_info(player_id)
                if player_info:
                    pname = player_info.get("name", "주인공")
                    sub_key = f"관계:{pname}:복종"
                    sub_val = morld.get_unit_prop(self.unit_id, sub_key) or 0
                    morld.set_unit_prop(self.unit_id, sub_key,
                                        min(100, sub_val + 0.3))

            wait_until = self._memory.get("restrained_wait_until", 0)
            if self.get_time() >= wait_until:
                self._memory["restrained_phase"] = "idle"
                self._insert_idle_job("결박", 1 * 60 * 1000)
            else:
                self._do_wander()
            self._action_taken = True
            return

    # ========================================
    # Tier 3: 생존 욕구
    # ========================================

    def _check_tier3_survival(self):
        """Tier 3: 생존 욕구 (배고픔, 추위, 더위, HP 회복)

        스케줄보다 우선하는 긴급 욕구.
        기존 _check_hunger/_check_cold/_check_hot 그대로 호출.

        Returns:
            True if action was taken.
        """
        if self._check_hunger():
            return True
        if self._check_cold():
            return True
        if self._check_hot():
            return True
        if self._check_hp_recovery():
            return True
        return False

    def _check_hp_recovery(self) -> bool:
        """HP < 50% → 음식 섭취로 HP 회복 (multi-phase)"""
        import survival
        hp = survival.get_health(self.unit_id)
        max_hp = survival.get_max_health(self.unit_id)
        if hp <= 0 or max_hp <= 0 or hp >= max_hp * 0.5:
            # HP 충분하면 진행 중인 phase도 정리
            if self._memory.get("hp_recovery_phase"):
                self._memory["hp_recovery_phase"] = None
                self._memory.pop("hp_recovery_target", None)
            return False
        return self._handle_hp_recovery()

    def _handle_hp_recovery(self) -> bool:
        """HP 회복을 위한 음식 섭취 (multi-phase, _handle_eat 패턴)"""
        import survival
        from think.activities.helpers import (
            find_npc_food, find_food_in_container, resolve_storage_container,
        )
        phase = self._memory.get("hp_recovery_phase")

        # Phase 1: idle — 인벤토리 체크 → storage 탐색
        if phase is None or phase == "idle":
            food = find_npc_food(self.unit_id)
            if food:
                # 이미 소지 중 → 바로 섭취
                hp_recover = max(5, food["satiety"] // 2)
                survival.add_health(self.unit_id, hp_recover)
                survival.npc_eat(self.unit_id, food["satiety"])
                morld.remove_item(self.unit_id, food["item_id"], 1)
                self._do_instant_action("응급 식사", "eat")
                self._memory["hp_recovery_phase"] = None
                return True
            # storage 탐색
            storage = resolve_storage_container(self, "food")
            if not storage:
                storage = resolve_storage_container(self, "food_ingredient")
            if not storage:
                self._memory["hp_recovery_phase"] = None
                return False
            self._memory["hp_recovery_phase"] = "going"
            self._memory["hp_recovery_target"] = storage
            self._move_to(storage, "응급 식사")
            return True

        # Phase 2: going → 도착 시 음식 꺼내기
        if phase == "going":
            target = self._memory.get("hp_recovery_target")
            if target and not self._is_at(target):
                self._move_to(target, "응급 식사")
                return True
            # 도착 — 컨테이너에서 음식 꺼내기
            container_id = target.get("object_id") if target else None
            if container_id:
                food_uid = find_food_in_container(container_id)
                if food_uid:
                    from assets.objects import get_instance
                    obj = get_instance(container_id)
                    if obj and hasattr(obj, 'npc_take_item'):
                        obj.npc_take_item(self.unit_id, food_uid, 1)
            self._memory["hp_recovery_phase"] = "eating"
            self._do_instant_action("음식 꺼내기", "take_item")
            return True

        # Phase 3: eating → 섭취
        if phase == "eating":
            food = find_npc_food(self.unit_id)
            if food:
                hp_recover = max(5, food["satiety"] // 2)
                survival.add_health(self.unit_id, hp_recover)
                survival.npc_eat(self.unit_id, food["satiety"])
                morld.remove_item(self.unit_id, food["item_id"], 1)
            self._do_instant_action("응급 식사", "eat")
            self._memory["hp_recovery_phase"] = None
            self._memory.pop("hp_recovery_target", None)
            return True

        # unknown phase → reset
        self._memory["hp_recovery_phase"] = None
        return False

    # ========================================
    # Tier 4: 쾌적 욕구
    # ========================================

    def _check_tier4_comfort(self):
        """Tier 4: 쾌적 욕구 (착의, 배변, 피로, 목욕/청결, 취침 이동)

        생존보다 낮은 우선순위.
        착의: 상의/하의 미착용 → _handle_clothing()
        배변: needs 임계치 → _handle_excretion()
        피로: needs 임계치 → _handle_sleep() (비스케줄)
        목욕: 스케줄 OR 청결 임계치 → _handle_bath()
        취침: 스케줄 → _handle_sleep()

        Returns:
            True if action was taken.
        """
        # 4a-pre. 임시노출 정리 (옷매무새)
        if self._check_exposure_recovery():
            return True

        # 4a. 착의 인터럽트
        if self._check_clothing():
            return True

        # 4b. 배변 인터럽트
        if self._check_excretion():
            return True

        # 4c. 피로 인터럽트 (비스케줄 수면)
        if self._check_fatigue():
            return True

        # 4d. 성욕 (플레이어 탐색 → 자위)
        if self._check_arousal():
            return True

        # 4e. 목욕 (스케줄 OR 청결 기반)
        is_bath, _ = self._is_bath_time()
        is_dirty = False
        is_semen_dirty = False
        try:
            import needs
            is_dirty = needs.is_npc_need_bath(self.unit_id)
        except ImportError:
            pass
        try:
            import romance
            is_semen_dirty = romance.get_semen_total(self.unit_id) > 20
        except ImportError:
            pass
        if is_bath or is_dirty or is_semen_dirty:
            self._handle_bath()
            self._action_taken = True
            return True

        # 4e-2. 빨래 (의류 오염도 기반)
        if self._check_laundry():
            return True

        # 4f. 출산 인터럽트 (임신 40주+)
        if self._check_childbirth():
            return True

        # 4g. 모성 인터럽트 (아이 탐색)
        if self._check_maternal():
            return True

        # 4h. 사회욕 (NPC-NPC 대화)
        if self._check_social():
            return True

        # 4h-2. NPC→NPC 선물
        if self._check_gift():
            return True

        # 4i. 취침 이동 (수면 시간이지만 아직 침대 아님)
        # (이미 침대에 누운 경우는 tier 1에서 처리됨)
        is_sleep, _ = self._is_sleep_time()
        if is_sleep:
            self._handle_sleep()
            self._action_taken = True
            return True

        return False

    def _check_excretion(self):
        """배변욕 확인 → 화장실 이동. Returns True if handling."""
        # 이미 진행 중이면 계속
        if self._memory["excretion_phase"] is not None:
            _handle_excretion(self)
            return True

        try:
            import needs
            if not needs.is_npc_need_excretion(self.unit_id):
                return False
        except ImportError:
            return False

        # 화장실 탐색
        from think.facility_resolver import resolve_toilet
        toilet = resolve_toilet(self)
        if not toilet:
            return False

        self._memory["excretion_phase"] = "idle"
        self._memory["excretion_target"] = toilet
        _handle_excretion(self)
        return True

    def _check_fatigue(self):
        """피로로 인한 수면. Returns True if handling.

        스케줄 수면 시간이면 skip (4d에서 처리).
        피로 임계치 초과 시 비스케줄 수면 시작.
        """
        is_sleep, _ = self._is_sleep_time()
        if is_sleep:
            return False  # 스케줄 수면은 4d에서 처리

        try:
            import needs
            if not needs.is_npc_need_sleep(self.unit_id):
                return False
        except ImportError:
            return False

        # 피로로 인한 비스케줄 수면 → _handle_sleep 재사용
        # (fallback duration 2시간이 적용됨)
        self._handle_sleep()
        self._action_taken = True
        return True

    def _check_arousal(self):
        """성욕 처리: 플레이어 탐색 / NPC-NPC 성행위 / 자위. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory["seek_player_phase"] is not None:
            _handle_seek_player(self)
            return True
        if self._memory.get("npc_intimacy_phase") is not None:
            _handle_npc_intimacy(self)
            return True
        if self._memory["self_comfort_phase"] is not None:
            _handle_self_comfort(self)
            return True

        # 쿨다운
        last = self._memory.get("self_comfort_cooldown")
        if last is not None and self.get_time() - last < _SELF_COMFORT_COOLDOWN_MS:
            return False

        # 임계치 (성격:정조에 따라 ±20 조정 — Phase 2 Slice F)
        threshold = getattr(self, 'self_comfort_threshold', 80)
        try:
            from romance_core import get_personality_value
            chastity = get_personality_value(self.unit_id, "정조")
            threshold += chastity * 20  # +1 → 100 (거의 안 함), -1 → 60 (더 자주)
        except Exception:
            pass
        arousal = morld.get_unit_prop(self.unit_id, "상태:성욕") or 0
        if arousal < threshold:
            return False

        # 0순위: 플레이어 탐색 (단둘 → NPC 주도 로맨스)
        can_seek, target = self._can_seek_player()
        if can_seek:
            self._memory["seek_player_phase"] = "idle"
            self._memory["seek_player_target"] = target
            _handle_seek_player(self)
            return True

        # 0.5순위: NPC-NPC 성행위 (합의: 양방향 호감+성욕 / 강제: 단방향+power 우위)
        npc_int_last = self._memory.get("npc_intimacy_cooldown")
        if npc_int_last is None or self.get_time() - npc_int_last >= _NPC_INTIMACY_COOLDOWN_MS:
            partner, mode = _find_npc_lover(self)
            if partner is not None:
                self._memory["npc_intimacy_phase"] = "idle"
                self._memory["npc_intimacy_partner"] = partner
                self._memory["npc_intimacy_mode"] = mode
                _handle_npc_intimacy(self)
                return True

        # 1순위: 유혹 (다른 NPC 있을 때 → 자발적 노출) + NPC→플레이어 성추행
        if self._try_self_exposure():
            return True
        if self._try_harass_player():
            return True

        # 2순위: 자위
        private = _resolve_private_location(self)
        if private is not None:
            self._memory["self_comfort_phase"] = "idle"
            _handle_self_comfort(self)
            return True

        return False

    _SELF_EXPOSURE_COOLDOWN_MS = 3_600_000   # 유혹 쿨다운 1시간
    _SELF_EXPOSURE_CHANCE = 0.5              # 유혹 확률 50%
    _SELF_EXPOSURE_AROUSAL_RELIEF = 10       # 유혹 후 성욕 감소량

    def _try_self_exposure(self):
        """높은 성욕 + 호감 + 다른 NPC 있을 때 → 자발적 옷 들추기 (유혹)"""
        import settings
        if not settings.is_romance_enabled():
            return False
        player_id = morld.get_player_id()
        if player_id is None or player_id < 0:
            return False
        # 같은 location 확인
        my_loc = morld.get_unit_location(self.unit_id)
        pl_loc = morld.get_unit_location(player_id)
        if not my_loc or not pl_loc or my_loc[:2] != pl_loc[:2]:
            return False
        # 쿨다운
        now = self.get_time()
        last = self._memory.get("self_exposure_cooldown", 0)
        if now - last < self._SELF_EXPOSURE_COOLDOWN_MS:
            return False
        # 다른 NPC가 있을 때만 유혹 (단둘이면 NPC 주도 로맨스가 우선)
        chars = morld.get_characters_at_location(my_loc[0], my_loc[1])
        others = [c for c in (chars or [])
                  if c != self.unit_id and c != player_id]
        if not others:
            return False  # 단둘 → 유혹 대신 플레이어 탐색/성추행 경로
        # 호감 임계치 (INITIATIVE_CONFIG 재활용)
        config = getattr(self, 'INITIATIVE_CONFIG', None)
        if not config:
            return False
        player_name = (morld.get_unit_info(player_id) or {}).get("name", "")
        affection = morld.get_unit_prop(self.unit_id,
                                        f"관계:{player_name}:호감") or 0
        if affection < config.get("affection_threshold", 60):
            return False
        # 이미 노출 상태면 skip
        if (morld.get_unit_prop(self.unit_id, "임시노출:상체") or 0) > 0:
            return False
        if (morld.get_unit_prop(self.unit_id, "임시노출:하체") or 0) > 0:
            return False
        # 확률 판정
        import random
        if random.random() > self._SELF_EXPOSURE_CHANCE:
            self._memory["self_exposure_cooldown"] = now
            return False
        # 자발적 노출 설정 (상체 or 하체 랜덤)
        part = random.choice(["상체", "하체"])
        morld.set_unit_prop(self.unit_id, f"임시노출:{part}", 2)
        morld.set_unit_prop(self.unit_id, "상태:자발적노출", 1)
        # 성욕 감소 (유혹 행위로 약간의 성적 만족감)
        morld.modify_prop(self.unit_id, "상태:성욕",
                          -self._SELF_EXPOSURE_AROUSAL_RELIEF)
        self._memory["self_exposure_cooldown"] = now
        self._do_instant_action("유혹", "seduce")
        return True

    def _try_harass_player(self):
        """NPC가 자발적으로 플레이어를 성추행 (호감 높을 때)"""
        import settings
        if not settings.is_romance_enabled():
            return False
        player_id = morld.get_player_id()
        if player_id is None or player_id < 0:
            return False
        # 같은 location 확인
        my_loc = morld.get_unit_location(self.unit_id)
        pl_loc = morld.get_unit_location(player_id)
        if not my_loc or not pl_loc or my_loc[:2] != pl_loc[:2]:
            return False
        # 호감 임계치 (환영 모드에서만)
        player_name = (morld.get_unit_info(player_id) or {}).get("name", "")
        affection = morld.get_unit_prop(self.unit_id,
                                        f"관계:{player_name}:호감") or 0
        if affection < 60:
            return False
        # 쿨다운 (2시간)
        now = self.get_time()
        last = self._memory.get("harass_player_cooldown", 0)
        if now - last < 2 * 3_600_000:
            return False
        # 랜덤 액션 선택
        import harassment
        import random
        available = harassment.get_available_actions(self.unit_id, player_id)
        if not available:
            return False
        action_id = random.choice(available)
        result = harassment.execute_action(self.unit_id, player_id,
                                           action_id, is_combat=False)
        action_name = harassment.HARASSMENT_ACTIONS[action_id]["name"]
        morld.add_action_log(f"{self.name}이(가) 당신에게 {action_name}")
        self._memory["harass_player_cooldown"] = now
        self._do_instant_action("성추행", "harass_player")
        return True

    def _check_childbirth(self):
        """출산 인터럽트: 임신 40주+ 또는 출산 진행 중. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory.get("childbirth_phase") is not None:
            from think.activities.childbirth import handle_childbirth
            handle_childbirth(self, None)
            return True

        try:
            import pregnancy
            week = pregnancy.get_pregnancy_week(self.unit_id)
            if week is not None and week >= 40:
                self._memory["childbirth_phase"] = "idle"
                from think.activities.childbirth import handle_childbirth
                handle_childbirth(self, None)
                return True
        except ImportError:
            pass

        return False

    def _check_maternal(self):
        """모성 인터럽트: 아이가 있고 모성 욕구 임계치 초과. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory.get("maternal_phase") is not None:
            from think.activities.childbirth import handle_maternal
            handle_maternal(self, None)
            return True

        # 아이 없으면 스킵
        child_id = self._memory.get("last_child_id")
        if not child_id:
            return False

        # 모성 욕구 임계치 (60)
        maternal = morld.get_unit_prop(self.unit_id, "욕구:모성") or 0
        if maternal < 60:
            return False

        self._memory["maternal_phase"] = "idle"
        from think.activities.childbirth import handle_maternal
        handle_maternal(self, None)
        return True

    def _check_social(self):
        """그리움 인터럽트: 가장 보고싶은 대상 탐색 → 찾아감. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory.get("socialize_phase") is not None:
            _handle_socialize(self)
            return True

        # 쿨다운 (1시간)
        last = self._memory.get("socialize_cooldown")
        if last is not None and self.get_time() - last < 3_600_000:
            return False

        # 가장 그리운 대상 탐색 (그리움 ≥ 70)
        target_id, _ = _find_most_missed(self)
        if target_id is None:
            return False

        self._memory["socialize_phase"] = "idle"
        self._memory["socialize_target_id"] = target_id
        _handle_socialize(self)
        return True

    def _check_gift(self):
        """NPC→NPC 선물 인터럽트. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory.get("gift_phase") is not None:
            _handle_gift(self)
            return True

        # 쿨다운 (24시간)
        last = self._memory.get("gift_cooldown")
        if last is not None and self.get_time() - last < 86_400_000:
            return False

        # 그리움 80+ 필요
        try:
            import needs
            longing = needs.get_max_longing(self.unit_id)
        except ImportError:
            return False
        if longing < 80:
            return False

        # 인벤토리에 선물 가능 아이템 확인
        gift_item_id = _find_gift_item(self)
        if gift_item_id is None:
            return False

        # 같은 region에서 호감 높은 NPC 탐색
        target_id = _find_gift_target(self)
        if target_id is None:
            return False

        self._memory["gift_phase"] = "idle"
        self._memory["gift_target_id"] = target_id
        self._memory["gift_item_id"] = gift_item_id
        _handle_gift(self)
        return True

    def _check_laundry(self):
        """의류 오염도 확인 → 세탁/건조 처리. Returns True if handling."""
        phase = self._memory["laundry_phase"]

        # 이미 진행 중 — waiting 상태는 False 반환 (NPC 자유)
        if phase == "waiting_wash":
            import laundry
            washer = self._memory["laundry_washer"]
            if washer and laundry.get_machine_state(washer["object_id"]) == 2:
                self._memory["laundry_phase"] = "collecting_wash"
                _handle_laundry(self)
                return True
            return False  # 아직 작동 중 → 다른 활동 허용
        if phase == "waiting_dry":
            import laundry
            dryer = self._memory["laundry_dryer"]
            if dryer and laundry.get_machine_state(dryer["object_id"]) == 2:
                self._memory["laundry_phase"] = "collecting_dry"
                _handle_laundry(self)
                return True
            return False  # 아직 건조 중 → 다른 활동 허용
        if phase is not None:
            _handle_laundry(self)
            return True

        # 쿨다운 체크 (3시간)
        cd = self._memory.get("laundry_cooldown")
        if cd is not None:
            elapsed = (self.get_time() or 0) - cd
            if elapsed < 3 * 3_600_000:
                return False

        # 오염된 착용 의류 체크
        dirty_items = _find_dirty_equipped_clothing(self.unit_id)
        if not dirty_items:
            return False

        # 세탁기 탐색
        from think.facility_resolver import resolve_washer
        washer = resolve_washer(self)
        if not washer:
            return False

        self._memory["laundry_phase"] = "going_to_washer"
        self._memory["laundry_washer"] = washer
        self._memory["laundry_items"] = dirty_items
        _handle_laundry(self)
        return True

    def _can_seek_player(self):
        """플레이어 탐색 가능 여부 (INITIATIVE_CONFIG 조건 재사용)"""
        if not self.INITIATIVE_CONFIG:
            return False, None

        # initiative 쿨다운
        props = morld.get_unit_props(self.unit_id)
        if props:
            last = props.get("상태:마지막_주도_시각", -99999)
            cd = self.INITIATIVE_CONFIG.get("cooldown_millis", 480 * 60_000)
            if self.get_time() - last < cd:
                return False, None

        player_id = morld.get_player_id()
        if player_id is None:
            return False, None
        player_info = morld.get_unit_info(player_id)
        if not player_info:
            return False, None

        # 호감/성욕 체크 (desire_threshold → 상태:성욕으로 이관, Phase 0)
        player_name = player_info.get("name", "주인공")
        affection = props.get(f"관계:{player_name}:호감", 0) if props else 0
        if affection < self.INITIATIVE_CONFIG.get("affection_threshold", 60):
            return False, None
        desire_th = self.INITIATIVE_CONFIG.get("desire_threshold", 0)
        if desire_th > 0:
            arousal = props.get("상태:성욕", 0) if props else 0
            if arousal < desire_th:
                return False, None

        # 같은 region만 (교차 리전 이동 미지원)
        npc_loc = self.get_location()
        if npc_loc and npc_loc[0] != player_info["region_id"]:
            return False, None

        # 이미 같은 location → on_meet이 처리 (seek 불필요)
        if npc_loc and npc_loc[1] == player_info["location_id"]:
            return False, None

        target = {"region_id": player_info["region_id"],
                  "location_id": player_info["location_id"], "x": 0}
        return True, target

    # ========================================
    # 배고픔 인터럽트
    # ========================================

    def _check_hunger(self):
        """배고픔 확인 → 식사 활동 시작. Returns True if handling hunger."""
        import survival
        if not survival.is_npc_hungry(self.unit_id):
            self._memory["hunger_phase"] = None
            return False
        # 배고프면 식사 핸들러 실행
        if self._memory["hunger_phase"] is None:
            self._memory["hunger_phase"] = "idle"
        _handle_eat(self)
        return True

    # ========================================
    # 추위/더위 인터럽트
    # ========================================

    COLD_COOLDOWN_MILLIS = 3_600_000  # 추위 대응 실패 후 1시간 쿨다운

    def _check_cold(self):
        """추위/젖음 확인 → 방한 활동 시작. Returns True if handling cold."""
        # 이미 진행 중이면 계속
        if self._memory["cold_phase"] is not None:
            _handle_cold(self)
            return True

        import temperature
        import humidity

        insulation = temperature.get_insulation_total(self.unit_id)

        # 조건 1: 체온 낮고 보온 부족
        cold_trigger = temperature.is_cold(self.unit_id) and insulation < 2

        # 조건 2: 비 맞고 방수 부족
        wet_trigger = False
        if humidity.is_raining():
            wetness = humidity.get_unit_wetness(self.unit_id)
            waterproof = temperature._get_equip_prop_total(self.unit_id, "방수")
            if wetness and wetness > 30 and waterproof < 1:
                wet_trigger = True

        if not (cold_trigger or wet_trigger):
            return False

        # 쿨다운 체크
        last_attempt = self._memory.get("cold_last_attempt")
        if last_attempt is not None:
            current_time = morld.get_game_time()
            if current_time - last_attempt < self.COLD_COOLDOWN_MILLIS:
                return False

        # 옷장 접근 가능 여부
        from think.facility_resolver import resolve_wardrobe
        if not resolve_wardrobe(self):
            return False

        self._memory["cold_phase"] = "idle"
        _handle_cold(self)
        return True

    def _check_hot(self):
        """더위 확인 → 보온 의류 벗기. Returns True if handling hot."""
        # 이미 진행 중이면 계속
        if self._memory["hot_phase"] is not None:
            _handle_hot(self)
            return True

        import temperature
        if not temperature.is_hot(self.unit_id):
            return False
        if temperature.get_insulation_total(self.unit_id) <= 0:
            return False

        # 옷장 접근 가능 여부
        from think.facility_resolver import resolve_wardrobe
        if not resolve_wardrobe(self):
            return False

        self._memory["hot_phase"] = "idle"
        _handle_hot(self)
        return True

    def _find_wardrobe_id(self):
        """옷장 오브젝트 ID 반환 (facility_resolver로 탐색)"""
        from think.facility_resolver import resolve_wardrobe
        result = resolve_wardrobe(self)
        return result["object_id"] if result else None

    # ========================================
    # 착의 인터럽트
    # ========================================

    CLOTHING_COOLDOWN_MILLIS = 3_600_000  # 착의 실패 후 1시간 쿨다운

    def _check_exposure_recovery(self):
        """임시노출 → 옷매무새 정리. Returns True if handling."""
        upper = morld.get_unit_prop(self.unit_id, "임시노출:상체") or 0
        lower = morld.get_unit_prop(self.unit_id, "임시노출:하체") or 0
        if not upper and not lower:
            return False
        import restraint
        if not restraint.can_use_hands(self.unit_id):
            return False
        morld.clear_prop(self.unit_id, "임시노출:상체")
        morld.clear_prop(self.unit_id, "임시노출:하체")
        morld.clear_prop(self.unit_id, "상태:자발적노출")
        self._do_instant_action("옷매무새 정리", "fix_clothes")
        return True

    def _check_clothing(self):
        """착의 확인 → 옷장 이동. Returns True if handling."""
        # 이미 진행 중이면 계속
        if self._memory["clothing_phase"] is not None:
            _handle_clothing(self)
            return True

        # 다른 의류 핸들러 활성 중이면 스킵
        if self._memory["cold_phase"] is not None:
            return False
        if self._memory["hot_phase"] is not None:
            return False

        # 이미 착의 상태면 불필요
        if _is_dressed(self.unit_id):
            return False

        # 쿨다운 체크
        last = self._memory.get("clothing_last_attempt")
        if last is not None:
            current_time = morld.get_game_time()
            if current_time - last < self.CLOTHING_COOLDOWN_MILLIS:
                return False

        # 옷장 접근 가능 여부
        from think.facility_resolver import resolve_wardrobe
        if not resolve_wardrobe(self):
            return False

        self._memory["clothing_phase"] = "idle"
        _handle_clothing(self)
        return True
