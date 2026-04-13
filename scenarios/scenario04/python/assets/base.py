# assets/base.py - S04 에셋 클래스 (Pi-World Engine 기반)
#
# engine/asset_base.py를 상속하여 S04 전용 속성 추가.

from engine.asset_base import (
    CharacterBase, ObjectBase, ItemBase, LocationBase,
    TextSelector, select_text,
    Asset, Unit,
)


class Character(CharacterBase):
    """S04 캐릭터 — 4스탯 + 클래스 시스템"""

    # 기본 스탯 (S04 전용: 근력/민첩/체력/정신)
    base_str = 10
    base_agi = 10
    base_vit = 10
    base_mnd = 10

    # 클래스
    character_class = None  # "척후", "타격수" 등

    # 특수 존재 여부 (던전의 힘 사용 가능)
    is_special = False

    # 무게
    weight = 70.0

    # 기본 액션 리스트 (폴백용 — get_available_actions가 덮어씀)
    # 포맷: "call:메서드이름:표시명"  — 표시명 뒤 '#'을 붙이면 확인 프롬프트 없이 즉시 실행
    actions = []

    # ========================================
    # 상태 기반 액션 필터링
    # ========================================

    def get_available_actions(self):
        """focus 시 노출될 액션 목록. '파티:리더' prop 기반 초대/이탈 토글."""
        import morld

        uid = self.instance_id
        if uid is None:
            return []

        player_id = morld.get_player_id()
        if player_id is None or uid == player_id:
            return []

        # 대상 NPC가 플레이어 파티에 속하는가?
        npc_leader = morld.get_unit_prop(uid, "파티:리더")
        if npc_leader == player_id:
            return ["call:dismiss_from_party:파티 이탈#"]

        # 플레이어가 리더인가?
        player_leader = morld.get_unit_prop(player_id, "파티:리더")
        if player_leader == player_id:
            return ["call:invite_to_party:파티 초대#"]

        return []

    def get_focus_text(self):
        """Focus 시 NPC 반응 — 최근 거절했으면 거절 라인, 아니면 인삿말."""
        import morld
        import npc_dialogue

        uid = self.instance_id
        if uid is None:
            return super().get_focus_text()

        if morld.get_unit_prop(uid, "최근:거절"):
            line = npc_dialogue.get_line(uid, "invite_decline", name=self.name)
        else:
            line = npc_dialogue.get_line(uid, "greeting", name=self.name)
        return f"[{self.name}] \"{line}\""

    # ========================================
    # 공용 액션 메서드
    # ========================================

    # recruit.recruit() 반환 사유 → npc_dialogue 상황 키 매핑
    _INVITE_REASON_TO_SITUATION = {
        "recruited":  "invite_accept",
        "declined":   "invite_decline",
        "party_full": "invite_full",
    }

    def invite_to_party(self):
        """플레이어 파티에 합류 요청. recruit 위임 + 아키타입 대사. Generator."""
        import morld
        import npc_dialogue
        import recruit
        import ui

        uid = self.instance_id
        if uid is None:
            return

        result = recruit.recruit(uid)
        reason = result["result"]
        situation = self._INVITE_REASON_TO_SITUATION.get(reason)
        if situation is None:
            print(f"[invite] LOGIC ERROR: unreachable reason={reason} on {self.name}")
            return

        # focus 텍스트 반영: 거절 → 최근:거절=1, 수락 → 해제
        if reason == "declined":
            morld.set_unit_prop(uid, "최근:거절", 1)
        elif reason == "recruited":
            morld.set_unit_prop(uid, "최근:거절", 0)

        line = npc_dialogue.get_line(uid, situation, name=self.name)
        yield ui.dialog(f"[{self.name}]\n\"{line}\"")

    def dismiss_from_party(self):
        """플레이어 파티에서 이 NPC를 내보낸다. Generator.

        UI 노출 조건(get_available_actions)이 이미 필터링하므로
        여기 도달했다면 대상은 플레이어 파티원 + 플레이어는 리더인 상태 전제.
        """
        import morld
        import npc_dialogue
        import ui
        from engine import party_group as _pg

        uid = self.instance_id
        if uid is None:
            return

        player_id = morld.get_player_id()
        party = _pg.get_party_of(player_id) if player_id else None

        if (
            party is None
            or uid == player_id
            or party.get_leader() != player_id
            or uid not in party.get_members()
        ):
            print(f"[dismiss] LOGIC ERROR: invalid state on {self.name}")
            return

        ok = _pg.remove_member(uid, reason="이탈")
        if ok:
            line = npc_dialogue.get_line(uid, "dismiss_leave", name=self.name)
            yield ui.dialog(f"[{self.name}]\n\"{line}\"")
        else:
            print(f"[dismiss] remove_member failed on {self.name}")


class Object(ObjectBase):
    """S04 오브젝트"""
    pass


class Item(ItemBase):
    """S04 아이템"""
    weight = 1.0
    category = "misc"


class Location(LocationBase):
    """S04 장소"""
    pass
