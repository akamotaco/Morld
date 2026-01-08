# events/scripts/npc_talk.py - NPC 대화 스크립트 함수

import morld
from assets.characters import get_character_event_handler


@morld.register_script
def npc_talk(context_unit_id):
    """NPC 대화 - Generator 기반"""
    unit_info = morld.get_unit_info(context_unit_id)
    if unit_info is None:
        yield morld.dialog(["...?"])
        return

    unit_id = unit_info.get("id")
    handler = get_character_event_handler(unit_id)

    if handler and hasattr(handler, "npc_talk"):
        # 캐릭터별 대화 핸들러 호출 (generator 위임)
        result = handler.npc_talk(context_unit_id)
        # generator인 경우 yield from으로 위임
        if hasattr(result, '__iter__') and hasattr(result, '__next__'):
            yield from result
        else:
            # 레거시 dict 반환인 경우 변환
            if isinstance(result, dict) and result.get("type") == "monologue":
                yield morld.dialog(result.get("pages", ["..."]))
        return

    name = unit_info.get("name", "???")
    yield morld.dialog([f"[{name}]", "......", "별 말이 없다."])
