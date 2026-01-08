# events/scripts/player_creation.py - 캐릭터 생성 스크립트 함수
#
# 게임 시작 시 플레이어 이름/나이/체격/장비 선택
# 새 Dialog API (proc + result) 방식 사용

import morld
from assets.characters.player import (
    Player, NAME_OPTIONS, AGE_OPTIONS, BODY_OPTIONS, EQUIPMENT_OPTIONS
)
from assets import registry
from assets.items.equipment import (
    OldKnife, LeatherPouch, WritingTool, OldBook, SmallToolbox
)

# unique_id → 아이템 클래스 매핑
_ITEM_CLASSES = {
    "old_knife": OldKnife,
    "leather_pouch": LeatherPouch,
    "writing_tool": WritingTool,
    "old_book": OldBook,
    "small_toolbox": SmallToolbox,
}

# 아이템 ID 카운터 (동적 할당)
_next_item_id = 100


def run_character_creation(state=None):
    """
    캐릭터 생성 플로우 실행 (generator)

    Args:
        state: 초기 상태 (None이면 새로 생성)

    Yields:
        morld.dialog() 요청들

    Returns:
        완성된 state dict
    """
    if state is None:
        state = {
            "name": None,
            "age": None,
            "body": None,
            "equipment": None,
            "step": "name",  # name → age → body → equipment → confirm
        }

    # === 이름 → 나이 → 체격 → 장비 → 확인 루프 ===
    while True:
        # --- 이름 선택 ---
        if state["step"] == "name":
            def build_name_text():
                name_links = "\n".join([
                    f"[url=@proc:{name}]{name}[/url]"
                    for name in NAME_OPTIONS
                ])
                return f"내 이름은...?\n\n{name_links}"

            def handle_name(action):
                if action == "init":
                    return build_name_text()
                state["name"] = action
                state["step"] = "age"
                return True

            yield morld.dialog(
                build_name_text(),
                autofill="off",
                proc=handle_name,
                result=state
            )
            continue

        # --- 나이 선택 ---
        if state["step"] == "age":
            def build_age_text():
                age_links = "\n".join([
                    f"[url=@proc:{opt['value']}]{opt['label']}[/url]"
                    for opt in AGE_OPTIONS
                ])
                return (
                    f"그래, 나는 {state['name']}.\n\n"
                    f"내 나이는...?\n\n"
                    f"{age_links}\n\n"
                    f"[url=@proc:back]← 이름 다시 선택[/url]"
                )

            def handle_age(action):
                if action == "init":
                    return build_age_text()
                if action == "back":
                    state["step"] = "name"
                    return True
                state["age"] = int(action)
                state["step"] = "body"
                return True

            yield morld.dialog(
                build_age_text(),
                autofill="off",
                proc=handle_age,
                result=state
            )
            continue

        # --- 체격 선택 ---
        if state["step"] == "body":
            def build_body_text():
                body_links = "\n".join([
                    f"[url=@proc:{opt['value']}]{opt['label']}[/url]"
                    for opt in BODY_OPTIONS
                ])
                return (
                    f"내 체격은...?\n\n"
                    f"{body_links}\n\n"
                    f"[url=@proc:back]← 나이 다시 선택[/url]"
                )

            def handle_body(action):
                if action == "init":
                    return build_body_text()
                if action == "back":
                    state["step"] = "age"
                    return True
                state["body"] = action
                state["step"] = "equipment"
                return True

            yield morld.dialog(
                build_body_text(),
                autofill="off",
                proc=handle_body,
                result=state
            )
            continue

        # --- 장비 선택 ---
        if state["step"] == "equipment":
            def build_equipment_text():
                equip_links = "\n".join([
                    f"[url=@proc:{opt['id']}]{opt['label']}[/url] - {opt['desc']}"
                    for opt in EQUIPMENT_OPTIONS
                ])
                return (
                    f"손에 뭔가 익숙한 감각이...\n\n"
                    f"{equip_links}\n\n"
                    f"[url=@proc:back]← 체격 다시 선택[/url]"
                )

            def handle_equipment(action):
                if action == "init":
                    return build_equipment_text()
                if action == "back":
                    state["step"] = "body"
                    return True
                state["equipment"] = action
                state["step"] = "confirm"
                return True

            yield morld.dialog(
                build_equipment_text(),
                autofill="off",
                proc=handle_equipment,
                result=state
            )
            continue

        # --- 확인 ---
        if state["step"] == "confirm":
            equip_info = next(
                (opt for opt in EQUIPMENT_OPTIONS if opt["id"] == state["equipment"]),
                {"label": "???", "items": []}
            )
            body_label = next(
                (opt["label"] for opt in BODY_OPTIONS if opt["value"] == state["body"]),
                "???"
            )

            def build_confirm_text():
                return (
                    f"[b]캐릭터 확인[/b]\n\n"
                    f"이름: {state['name']}\n"
                    f"나이: {state['age']}세\n"
                    f"체격: {body_label}\n"
                    f"소지품: {equip_info['label']}\n\n"
                    f"이대로 시작하시겠습니까?\n\n"
                    f"[url=@proc:confirm]확인[/url]  [url=@proc:back]다시 선택[/url]"
                )

            def handle_confirm(action):
                if action == "init":
                    return build_confirm_text()
                if action == "back":
                    state["step"] = "equipment"
                    return True
                if action == "confirm":
                    state["step"] = "done"
                    return True
                return None

            yield morld.dialog(
                build_confirm_text(),
                autofill="off",
                proc=handle_confirm,
                result=state
            )

            if state["step"] != "done":
                continue

            # 확인 완료 - 루프 탈출
            break

    return state


def apply_character_creation(state):
    """
    캐릭터 생성 결과를 게임에 적용

    Args:
        state: run_character_creation()의 결과
    """
    global _next_item_id

    player_id = morld.get_player_id()

    # 이름 설정
    Player.name = state["name"]
    morld.set_unit(player_id, "name", state["name"])

    # 나이 저장 (prop)
    morld.set_prop("player_age", state["age"])

    # 신체 타입 저장 (인덱스)
    body_index = {"왜소": 0, "보통": 1, "장신": 2, "거구": 3}.get(state["body"], 1)
    morld.set_prop("player_body", body_index)

    # 이름 인덱스 저장
    name_index = NAME_OPTIONS.index(state["name"]) if state["name"] in NAME_OPTIONS else 0
    morld.set_prop("player_name_index", name_index)

    # 장비 지급 (아이템 동적 생성)
    for opt in EQUIPMENT_OPTIONS:
        if opt["id"] == state["equipment"]:
            for unique_id, count in opt["items"]:
                # 아이템이 아직 instantiate 안되었으면 생성
                item_id = registry.get_instance_id(unique_id)
                if item_id is None:
                    item_cls = _ITEM_CLASSES.get(unique_id)
                    if item_cls:
                        item = item_cls()
                        item.instantiate(_next_item_id)
                        item_id = _next_item_id
                        _next_item_id += 1

                if item_id is not None:
                    morld.give_item(player_id, item_id, count)
            break
