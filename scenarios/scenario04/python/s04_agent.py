# s04_agent.py — S04 NPC Agent
#
# engine/think_base.BaseAgent 기반.
# LifeState → _on_think(): 기본 생활 (idle/배회)
# DungeonState push 시 → 생활 차단, 던전 전용 행동
#
# 등록: party.py _on_member_added에서 register
# 해제: party.py _on_member_removed에서 unregister

import morld
import random
from engine.think_base import BaseAgent
from engine import think as _think


# 배회 가능 장소 (마을)
_ROAM_LOCATIONS = [
    (0, 0),  # 광장
    (0, 1),  # 여관
    (0, 4),  # 술집
    (0, 7),  # 던전 입구
]

# 배회 간격 (ms)
_ROAM_INTERVAL_MIN = 10 * 60_000   # 10분
_ROAM_INTERVAL_MAX = 30 * 60_000   # 30분


class S04Agent(BaseAgent):
    """S04 NPC Agent — 기본 생활 + 던전 선택"""

    def _on_think(self):
        """LifeState pass-through 시 호출 — 기본 생활 행동"""
        # 파티 소속이면 리더(플레이어) 위치로 텔레포트 유지
        player_id = morld.get_player_id()
        if player_id is not None:
            player_loc = morld.get_unit_location(player_id)
            my_loc = self.get_location()
            if player_loc and my_loc:
                if player_loc[0] != my_loc[0] or player_loc[1] != my_loc[1]:
                    # 리더와 다른 위치 → 따라감
                    morld.set_unit_location(
                        self.unit_id, player_loc[0], player_loc[1],
                        x=random.randint(20, 150))
                    self._insert_idle_job("따라감", 5 * 60_000)
                    return

        # 같은 위치 → idle 대기
        duration = random.randint(_ROAM_INTERVAL_MIN, _ROAM_INTERVAL_MAX)
        self._insert_idle_job("대기", duration)

    def dungeon_choose(self, options):
        """던전 분기에서 이 NPC의 선호 선택. 현재: 랜덤.

        향후: 성격/상태 기반 가중 선택.
        """
        if not options:
            return None
        return random.choice(options)


# ============================================
# Agent 등록/해제 (party.py에서 호출)
# ============================================

def register_agent(unit_id):
    """NPC를 Agent로 등록 (think_all에서 think 호출 대상)"""
    existing = _think.get_agent(unit_id)
    if existing is not None:
        return  # 이미 등록됨
    agent = S04Agent(unit_id)
    _think.register_agent(unit_id, agent)
    name = morld.get_unit_name(unit_id) or str(unit_id)
    print("[s04_agent] Registered: " + name + " (id=" + str(unit_id) + ")")


def unregister_agent(unit_id):
    """NPC Agent 해제"""
    _think.unregister_agent(unit_id)
    name = morld.get_unit_name(unit_id) or str(unit_id)
    print("[s04_agent] Unregistered: " + name + " (id=" + str(unit_id) + ")")
