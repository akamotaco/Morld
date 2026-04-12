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

    # 기본 액션 리스트 (focus 시 노출)
    # 포맷: "call:메서드이름:표시명"  — 표시명 뒤 '#'을 붙이면 확인 프롬프트 없이 즉시 실행
    actions = ["call:invite_to_party:파티 초대"]

    # ========================================
    # 공용 액션 메서드
    # ========================================

    def invite_to_party(self):
        """플레이어 파티에 합류 요청. recruit 모듈로 위임.

        플레이어가 리더일 때만 의미 있음. 결과 메시지는 print (UI 통합은 추후).
        """
        import recruit
        unit_id = self.instance_id
        if unit_id is None:
            print("[invite] no instance_id")
            return None

        result = recruit.recruit(unit_id)
        if result["success"]:
            print(f"[invite] {self.name}: 파티 합류 수락 — 새 파티원이 되었다.")
        else:
            reason = result["result"]
            reason_msg = {
                "no_player": "플레이어가 없습니다.",
                "no_party": "플레이어 파티가 없습니다.",
                "not_leader": "플레이어가 리더가 아닙니다 (현재 파티원 상태).",
                "party_full": "파티 정원이 찼습니다.",
                "already_member": "이미 파티원입니다.",
                "self": "자기 자신은 초대할 수 없습니다.",
                "declined": "거절당했다.",
            }.get(reason, reason)
            print(f"[invite] {self.name}: 실패 — {reason_msg}")
        return None


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
