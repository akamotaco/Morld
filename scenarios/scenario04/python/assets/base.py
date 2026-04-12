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
        """focus 시 노출될 액션 목록. '파티:리더' prop 기반으로 초대/이탈 토글.

        규칙:
          - 대상의 '파티:리더' == 플레이어 id → 플레이어 파티원 → "파티 이탈"
          - 플레이어의 '파티:리더' == 플레이어 id → 플레이어가 리더 → "파티 초대"
          - 그 외: 액션 없음

        액션에 '#'를 붙여 actor(플레이어)의 can: prop 검증으로 이중 확인 (추가 방어).
        """
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

    # ========================================
    # 공용 액션 메서드
    # ========================================

    # NPC 거절/수락 대사 — UI에서 실제 도달 가능한 사유만.
    # 나머지(already_member/self/not_leader 등)는 get_available_actions가 필터링하므로
    # 도달하면 로직 오류로 간주하고 에러 로그.
    INVITE_LINES = {
        "accepted": "좋아. 함께 가자.",
        "party_full": "미안해. 내가 들어갈 자리는 없는 것 같네.",
        "declined": "...미안, 너랑은 같이 가고 싶지 않아.",
    }

    def invite_to_party(self):
        """플레이어 파티에 합류 요청. recruit 모듈로 위임. Generator — 결과 메시지 표시."""
        import recruit
        import ui

        unit_id = self.instance_id
        if unit_id is None:
            return

        result = recruit.recruit(unit_id)
        reason = result["result"]

        line = self.INVITE_LINES.get(reason)
        if line:
            yield ui.dialog(f"[{self.name}]\n\"{line}\"")
            return

        # 여기 도달하면 get_available_actions 필터를 우회한 상태 → 로직 오류
        print(f"[invite] LOGIC ERROR: unreachable reason={reason} on {self.name}")

    # 이탈 시 NPC 대사 (서브클래스에서 오버라이드 가능)
    DISMISS_LINES = {
        "accepted": "...알겠어. 각자의 길을 가자.",
    }

    def dismiss_from_party(self):
        """플레이어 파티에서 이 NPC를 내보낸다. Generator.

        UI 노출 조건(get_available_actions)이 이미 필터링하므로
        여기 도달했다면 대상은 플레이어 파티원 + 플레이어는 리더인 상태 전제.
        그 외 상태는 로직 오류로 로그.
        """
        import morld
        import ui
        from engine import party_group as _pg

        uid = self.instance_id
        if uid is None:
            return

        player_id = morld.get_player_id()
        party = _pg.get_party_of(player_id) if player_id else None

        # 도달 불가 상태 가드 (로직 오류 감지)
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
            line = self.DISMISS_LINES.get("accepted", "")
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
