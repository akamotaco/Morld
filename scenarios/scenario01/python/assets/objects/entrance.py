# assets/objects/entrance.py - 정문 홀 오브젝트 (정문)

import morld
from assets.base import Object
from assets.items.golden_key import get_item_instance


class FrontDoor(Object):
    """정문"""
    unique_id = "front_door"
    name = "정문"
    actions = ["script:escape:열기"]
    focus_text = {
        "default": "저택의 거대한 정문이다. 황금빛 자물쇠가 빛나고 있다. 이 문만 열면 자유다!"
    }
    lock_key = "golden_key"


# ========================================
# 스크립트 함수
# ========================================

def escape(context_unit_id):
    """정문으로 탈출 - Generator 기반"""
    player_id = morld.get_player_id()

    # 황금열쇠 확인
    key = get_item_instance(FrontDoor.lock_key)
    if not key or not morld.has_item(player_id, key.instance_id):
        yield morld.dialog([
            "정문이 굳게 잠겨 있다.",
            "황금빛 자물쇠가 달려 있다. 특별한 열쇠가 필요해 보인다."
        ])
        return

    # 황금열쇠 소모
    morld.lost_item(player_id, key.instance_id, 1)
    morld.add_action_log("정문이 열렸다")

    # 탈출 성공!
    yield morld.dialog([
        "황금열쇠를 자물쇠에 꽂았다.",
        "철커덕-!",
        "묵직한 자물쇠가 떨어져 나간다.",
        "오래된 경첩이 삐걱거리며...",
        "마침내... 문이 열렸다!"
    ])

    # 엔딩 스토리로 이어짐
    yield from show_ending(context_unit_id)


@morld.register_script
def show_ending(context_unit_id):
    """엔딩 화면 표시 - 1단계 (스토리) - Generator 기반"""
    yield morld.dialog([
        "차가운 바깥 공기가 폐부 깊숙이 밀려들어온다.",

        "한 발짝.\n\n그리고 또 한 발짝.\n\n무거웠던 다리가 저택의 문턱을 넘는다.",

        "뒤를 돌아보니, 어둠에 잠긴 저택이\n마치 거대한 괴물처럼 웅크리고 있다.\n\n하지만 더 이상 두렵지 않다.",

        "새벽녘의 희미한 빛이 지평선 너머로 번지기 시작한다.\n\n밤새 이 저택에 갇혀 있었던 것일까.\n기억은 여전히 흐릿하지만...",

        "중요한 건 살아남았다는 것.\n\n그리고 이제 자유라는 것.",

        "발걸음이 자갈길을 밟을 때마다\n작은 소리가 정적을 깨뜨린다.\n\n그 소리마저도 지금은 음악처럼 들린다.",

        "저택의 정원을 지나 철문에 다다른다.\n\n녹슨 문고리를 잡아당기자,\n의외로 쉽게 열린다.",

        "바깥세상.\n\n익숙한 듯, 낯선 듯한 풍경이 눈앞에 펼쳐진다.",

        "차가운 아침 공기를 깊이 들이마신다.\n\n살아있음을 온몸으로 느끼며."
    ])

    # 크레딧으로 이어짐
    yield from show_ending_credits(context_unit_id)


@morld.register_script
def show_ending_credits(context_unit_id):
    """엔딩 화면 표시 - 2단계 (크레딧) - Generator 기반"""
    yield morld.dialog(
        "━━━━━━━━━━━━━━━━━━━━\n\n[b]탈출 성공![/b]\n\n당신은 미스터리한 저택에서\n무사히 빠져나왔습니다.\n\n━━━━━━━━━━━━━━━━━━━━\n\n플레이해주셔서 감사합니다.",
        autofill="off"
    )
