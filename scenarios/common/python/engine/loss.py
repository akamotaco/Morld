# loss.py — 결손 시스템 (binary, 영구, 보조구로 일부 복원)
#
# 결손은 영구 — 일반 회복 경로 없음 (수술/특수 사건만, 시나리오 책임).
# 보조구(의수/의족) 장착 시 능력 복원 — body_gate.is_part_lost가 보조구 검사.
#
# Prop schema:
#   결손:{part} = 1
#   결손:{part}:종류 = 자유 문자열
#   결손:{part}:보조구 = item_uid

import morld


_PROP_LOSS = "결손:{}"
_PROP_KIND = "결손:{}:종류"
_PROP_PROSTHETIC = "결손:{}:보조구"


def add_loss(uid, part: str, kind: str = None):
    """결손 부여 (영구). 이미 결손 시 idempotent (kind 갱신 없음)."""
    if has_loss(uid, part):
        return
    morld.set_unit_prop(uid, _PROP_LOSS.format(part), 1)
    if kind:
        morld.set_unit_prop(uid, _PROP_KIND.format(part), kind)
    name = morld.get_unit_name(uid) or f"id={uid}"
    kind_str = f" ({kind})" if kind else ""
    morld.add_action_log(f"[{name}]의 {part}에 결손{kind_str}")


def remove_loss(uid, part: str):
    """결손 제거 — 일반 호출 안 함. 디버그/특수 사건용."""
    morld.set_unit_prop(uid, _PROP_LOSS.format(part), None)
    morld.set_unit_prop(uid, _PROP_KIND.format(part), None)
    morld.set_unit_prop(uid, _PROP_PROSTHETIC.format(part), None)


def has_loss(uid, part: str) -> bool:
    return bool(morld.get_unit_prop(uid, _PROP_LOSS.format(part)))


def get_kind(uid, part: str) -> str:
    return morld.get_unit_prop(uid, _PROP_KIND.format(part)) or ""


def equip_prosthetic(uid, part: str, item_uid: int) -> bool:
    """보조구 장착 — 결손 부위에만 적용. 이미 장착돼 있으면 교체."""
    if not has_loss(uid, part):
        return False
    morld.set_unit_prop(uid, _PROP_PROSTHETIC.format(part), item_uid)
    return True


def remove_prosthetic(uid, part: str):
    morld.set_unit_prop(uid, _PROP_PROSTHETIC.format(part), None)


def has_prosthetic(uid, part: str) -> bool:
    return bool(morld.get_unit_prop(uid, _PROP_PROSTHETIC.format(part)))


def get_prosthetic(uid, part: str):
    """보조구 item_uid. 없으면 None."""
    return morld.get_unit_prop(uid, _PROP_PROSTHETIC.format(part))


def is_part_lost(uid, part: str) -> bool:
    """결손 + 보조구 없음 → 능력적으로 죽은 부위."""
    return has_loss(uid, part) and not has_prosthetic(uid, part)


def reset():
    """모듈 상태 초기화 — pi-world reset 계약 (가변 전역 없음, 규약 준수용)"""
    pass
