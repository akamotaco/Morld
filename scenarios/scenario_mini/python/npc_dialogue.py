# npc_dialogue.py — hybrid 대화 어댑터 (scenario_mini)
#
# 캐릭터 yaml 없이 아키타입 공용 풀(engine.dialogue_hybrid)만으로 대사를
# 생성한다 — "캐릭터 데이터 파일 + 아키타입 지정"만으로 대화가 성립함을 검증.

import morld

from engine.dialogue_hybrid import stateless as _st

# unique_id → 아키타입 (assets/characters.py 와 동기)
CHAR_ARCHETYPES = {
    "mini_guide": "cheerful",
    "mini_ranger": "stoic",
}
DEFAULT_ARCHETYPE = "stoic"


def _name_and_archetype(unit_id):
    info = morld.get_unit_info(unit_id) or {}
    name = info.get("name", f"Unit-{unit_id}")
    archetype = CHAR_ARCHETYPES.get(info.get("unique_id"), DEFAULT_ARCHETYPE)
    return name, archetype


def daily_line(unit_id, intent, rng=None):
    """일상 발화. intent: greet/thank/complain 등.

    Returns: "이름: 「대사」" 형식, 생성 실패 시 "" (호출측에서 조용히 무시)
    """
    name, archetype = _name_and_archetype(unit_id)
    line = _st.generate_daily_line(archetype, name, intent, rng=rng)
    return f"{name}: 「{line}」" if line else ""
