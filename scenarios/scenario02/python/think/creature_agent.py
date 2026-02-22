# think/creature_agent.py — 생물(Creature) Agent
#
# BaseAgent를 상속하여 단순화된 스케줄 기반 행동 제공
# - survival/needs 미등록 (HP는 전투로만 관리)
# - 4-tier think: 사망 → 기절 → 전투 → 스케줄
# - 활동: 순찰(wander) / 휴식(idle) / 수면(idle) / 복귀(return to lair)
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
        """생물 행동 결정 (4-tier)"""
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
