# think/creature_agent.py — 생물(Creature) Agent
#
# BaseAgent를 상속하여 단순화된 스케줄 기반 행동 제공
# - survival/needs 미등록 (HP는 전투로만 관리)
# - 5-tier think: 사망 → 기절 → 전투 → 겁탈 → 스케줄
# - 활동: 순찰(wander) / 휴식(idle) / 수면(idle) / 복귀(return to lair)
# - 겁탈: bestiality ON + 유성 생물 + 무력화된 캐릭터 감지 시
# - 자연 소멸: spawner가 수명 체크 → 디스폰

import morld
import carry
import survival
from think import BaseAgent

MILLIS_PER_DAY = 86_400_000


class CreatureAgent(BaseAgent):
    """생물 Agent — 단순화된 스케줄 기반 행동

    NPC(BaseAgent)와의 차이:
    - survival/needs 등록 없음
    - think() 4-tier (사망/기절/전투/스케줄)
    - 활동: 순찰/휴식/수면/복귀
    """

    def __init__(self, unit_id, schedule=None):
        super().__init__(unit_id)
        # survival.register_npc() 호출 안 함
        # needs.register_character() 호출 안 함
        if schedule:
            self.set_base_schedule(schedule)

    def think(self):
        """생물 행동 결정 (5-tier)"""
        self._action_taken = False

        # Tier 0: 운반 중
        if carry.is_being_carried(self.unit_id):
            self._insert_idle_job("운반 중", 60_000)
            return

        # Tier 1: 사망 → 장시간 대기 (spawner 디스폰 대기)
        if morld.get_unit_prop(self.unit_id, "상태:사망"):
            self._insert_idle_job("사망", 3_600_000)
            return

        # Tier 2: 기절
        if survival.is_npc_fainted(self.unit_id):
            remain = survival.get_faint_remaining_millis(self.unit_id)
            self._insert_idle_job("기절", max(remain, 1_000))
            return

        # Tier 3: 전투 위협 감지 (BaseAgent._check_combat_threat 재사용)
        if self._check_combat_threat():
            return

        # Tier 3.5: 겁탈 기회 (bestiality ON + 무력화 대상 감지)
        if self._check_assault_opportunity():
            return

        # Tier 3.6: 성추행 기회 (harassment ON + 무력화 대상)
        if self._check_harassment_opportunity():
            return

        # Tier 4: 스케줄 기반 행동
        entry = self._get_creature_entry()
        if entry:
            activity = entry.get("activity", "순찰")
            self._handle_creature_activity(entry, activity)
            if self._action_taken:
                return

        # Safety net
        self._insert_idle_job("할 일 없음", 60_000)

    def _get_creature_entry(self):
        """현재 시간에 해당하는 스케줄 entry (수면/휴식 포함)

        BaseAgent._get_current_activity()는 수면/목욕을 건너뛰므로
        생물용 전용 탐색.
        """
        schedule = self.get_current_schedule()
        if not schedule:
            return None
        millis = self.get_time()
        for entry in schedule:
            start = entry["start"]
            end = entry["end"]
            if end < start:  # 자정 넘기기
                if millis >= start or millis < end:
                    return entry
            else:
                if start <= millis < end:
                    return entry
        return None

    def _handle_creature_activity(self, entry, activity):
        """스케줄 활동 분기"""
        if activity == "순찰":
            self._do_wander(entry)
        elif activity == "복귀":
            self._do_return_to_lair(entry)
        elif activity in ("수면", "휴식"):
            remaining = self._remaining_millis_in_entry(entry)
            self._insert_idle_job(entry["name"], max(remaining, 1_000))
            self._action_taken = True
        else:
            # 알 수 없는 활동 → 순찰 대체
            self._do_wander(entry)

    def _do_return_to_lair(self, entry):
        """spawn location(거처)으로 복귀"""
        spawn_region = morld.get_unit_prop(self.unit_id, "전투:홈리전")
        spawn_loc = morld.get_unit_prop(self.unit_id, "생물:스폰위치")
        if spawn_region is not None and spawn_loc is not None:
            target = {"region_id": int(spawn_region),
                      "location_id": int(spawn_loc)}
            if not self._is_at(target):
                self._move_to(target, entry["name"])
                return
        # 이미 도착했거나 스폰 정보 없음 → 제자리 대기
        remaining = self._remaining_millis_in_entry(entry)
        self._insert_idle_job(entry["name"], max(remaining, 1_000))
        self._action_taken = True

    # ========================================
    # 겁탈 AI (Bestiality)
    # ========================================

    def _check_assault_opportunity(self):
        """무력화된 캐릭터 감지 → 겁탈 시도"""
        import settings
        import gender as gender_mod

        if not settings.is_bestiality_enabled():
            return False

        # 무성 생물은 겁탈하지 않음
        creature_gender = gender_mod.get_gender(self.unit_id)
        if creature_gender == gender_mod.ASEXUAL:
            return False

        # 이미 겁탈 진행 중이면 계속
        phase = self._memory.get("assault_phase")
        if phase is not None:
            return self._handle_assault()

        # 쿨다운 중이면 패스 (절대 시각 기반)
        cooldown_until = self._memory.get("assault_cooldown_until", 0)
        if cooldown_until > 0 and morld.get_current_time() < cooldown_until:
            return False

        # 같은 Location의 무력화된 캐릭터 탐색
        loc = morld.get_unit_location(self.unit_id)
        if not loc or loc[0] < 0:
            return False

        import combat
        player_id = morld.get_player_id()
        characters = morld.get_characters_at_location(loc[0], loc[1])
        for char_id in (characters or []):
            if char_id == self.unit_id:
                continue
            if morld.get_unit_prop(char_id, "상태:사망"):
                continue
            # 무력화 조건: 기절 OR 마비 OR 거미줄
            is_fainted = survival.is_npc_fainted(char_id)
            if not is_fainted and char_id == player_id:
                is_fainted = survival.is_player_fainted()
            if (is_fainted or
                    combat.is_paralyzed(char_id) or
                    combat.is_web_bound(char_id)):
                self._memory["assault_phase"] = "assaulting"
                self._memory["assault_target"] = char_id
                return self._handle_assault()

        return False

    def _handle_assault(self):
        """겁탈 처리: aftermath + 사정/임신 + 처녀해제 + 경험기록"""
        phase = self._memory.get("assault_phase")
        target_id = self._memory.get("assault_target")

        if target_id is None:
            self._memory["assault_phase"] = None
            return False

        # 대상이 사망/디스폰 → 중단
        info = morld.get_unit_info(target_id)
        if info is None or morld.get_unit_prop(target_id, "상태:사망"):
            self._clear_assault()
            return False

        if phase == "assaulting":
            import gender as gender_mod
            from romance_core import record_first_experience, record_last_experience

            player_id = morld.get_player_id()
            is_player_target = (target_id == player_id)

            # NPC만: 성욕 감소 (플레이어는 needs 미등록)
            if not is_player_target:
                import needs
                needs.modify_need(target_id, "욕구:성욕", -30)

            # 수간 aftermath
            morld.set_unit_prop(target_id, "상태:수간피해", 3)
            morld.modify_prop(target_id, "기억:수간피해횟수", 1)

            # 사정/임신 (수컷 creature만)
            if gender_mod.has_anatomy(self.unit_id, "P"):
                from romance_core import _apply_internal_semen
                _apply_internal_semen(target_id, "음부", 50)
                if gender_mod.has_anatomy(target_id, "V"):
                    import pregnancy
                    pregnancy.check_conception(
                        target_id, self.unit_id, father_type="unknown")

            # 처녀 해제 + 부위별 첫경험 기록
            virginity_prop = "처녀:음부"
            if morld.get_unit_prop(target_id, virginity_prop):
                morld.set_unit_prop(target_id, virginity_prop, 0)
                record_first_experience(
                    target_id, self.unit_id, "bestiality", "음부")

            # 마지막 경험 기록
            record_last_experience(target_id, self.unit_id, "bestiality")

            # 플레이어 대상: HP 추가 감소 (20%)
            if is_player_target:
                hp = morld.get_unit_prop(target_id, "생존:체력") or 0
                penalty = max(1, hp // 5)
                survival.add_health(target_id, -penalty)

            self._insert_idle_job("겁탈 중", 30 * 60_000)  # 30분
            # 쿨다운 설정 (절대 시각: 현재 + 4시간)
            self._memory["assault_cooldown_until"] = (
                morld.get_current_time() + 4 * 3_600_000
            )
            self._clear_assault()
            self._action_taken = True
            return True

        # 알 수 없는 phase → 초기화
        self._clear_assault()
        return False

    def _clear_assault(self):
        """겁탈 상태 초기화"""
        self._memory.pop("assault_phase", None)
        self._memory.pop("assault_target", None)

    # ========================================
    # 성추행 AI (Harassment)
    # ========================================

    def _check_harassment_opportunity(self):
        """무력화된 캐릭터 감지 → 성추행 시도 (harassment ON)"""
        import settings
        if not settings.is_harassment_enabled():
            return False

        # 무성 생물 제외
        import gender as gender_mod
        if gender_mod.get_gender(self.unit_id) == gender_mod.ASEXUAL:
            return False

        # 쿨다운 (2시간)
        cooldown_until = self._memory.get("harass_cooldown_until", 0)
        now = morld.get_current_time()
        if cooldown_until > 0 and now < cooldown_until:
            return False

        # 같은 Location 무력화 캐릭터 탐색
        loc = morld.get_unit_location(self.unit_id)
        if not loc or loc[0] < 0:
            return False

        import combat
        player_id = morld.get_player_id()
        characters = morld.get_characters_at_location(loc[0], loc[1])
        targets = []
        for char_id in (characters or []):
            if char_id == self.unit_id:
                continue
            if morld.get_unit_prop(char_id, "상태:사망"):
                continue
            is_fainted = survival.is_npc_fainted(char_id)
            if not is_fainted and char_id == player_id:
                is_fainted = survival.is_player_fainted()
            if (is_fainted or
                    combat.is_paralyzed(char_id) or
                    combat.is_web_bound(char_id)):
                targets.append(char_id)

        if not targets:
            return False

        import random
        target_id = random.choice(targets)

        # 개별 스펙 기반 확률 (harassment_chance, 기본 0.3)
        chance = getattr(self, 'harassment_chance', 0.3)
        if random.random() > chance:
            self._memory["harass_cooldown_until"] = now + 2 * 3_600_000
            return False

        # 액션 선택 + 실행
        import harassment
        available = harassment.get_available_actions(self.unit_id, target_id)
        if not available:
            return False
        action_id = random.choice(available)
        result = harassment.execute_action(self.unit_id, target_id,
                                           action_id, is_combat=False)
        action_name = harassment.HARASSMENT_ACTIONS[action_id]["name"]
        target_name = (morld.get_unit_info(target_id) or {}).get("name", "?")
        morld.add_action_log(f"{self.name}이(가) {target_name}에게 {action_name}")
        self._insert_idle_job("성추행 중", 30 * 60_000)
        self._memory["harass_cooldown_until"] = now + 2 * 3_600_000
        self._action_taken = True
        return True
