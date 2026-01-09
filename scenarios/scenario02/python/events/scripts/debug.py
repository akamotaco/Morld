# events/scripts/debug.py - 디버그용 스크립트 함수

import morld


def _get_all_unit_props(unit_id):
    """유닛의 모든 props를 타입별로 정리해서 반환"""
    all_props = {}
    prop_types = morld.get_unit_prop_types(unit_id)

    for prop_type in prop_types:
        props = morld.get_unit_props_by_type(unit_id, prop_type)
        if props:
            all_props[prop_type] = props

    return all_props


def _format_props_text(unit_name, all_props):
    """props를 보기 좋은 텍스트로 포맷팅"""
    lines = [f"[b]{unit_name}[/b]의 속성\n"]

    if not all_props:
        lines.append("(속성 없음)")
        return "\n".join(lines)

    # 타입별로 정렬해서 표시
    for prop_type in sorted(all_props.keys()):
        props = all_props[prop_type]
        lines.append(f"[color=yellow][{prop_type}][/color]")

        # 속성명으로 정렬
        for name in sorted(props.keys()):
            value = props[name]
            lines.append(f"  {name}: {value}")

        lines.append("")  # 빈 줄로 구분

    return "\n".join(lines)


@morld.register_script
def debug_props(context_unit_id):
    """유닛의 모든 속성(props) 표시 - 디버그용"""
    unit_info = morld.get_unit_info(context_unit_id)
    if not unit_info:
        yield morld.dialog("유닛 정보를 찾을 수 없습니다.")
        return

    unit_name = unit_info.get("name", f"유닛#{context_unit_id}")
    all_props = _get_all_unit_props(context_unit_id)
    text = _format_props_text(unit_name, all_props)

    yield morld.dialog(text, autofill="scroll")


@morld.register_script
def debug_self_props(context_unit_id):
    """플레이어 자신의 속성(props) 표시 - 거울용"""
    player_id = morld.get_player_id()
    unit_info = morld.get_unit_info(player_id)
    if not unit_info:
        yield morld.dialog("플레이어 정보를 찾을 수 없습니다.")
        return

    unit_name = unit_info.get("name", "???")
    all_props = _get_all_unit_props(player_id)
    text = _format_props_text(unit_name, all_props)

    yield morld.dialog(text, autofill="scroll")
