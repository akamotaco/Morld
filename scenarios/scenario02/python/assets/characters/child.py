# assets/characters/child.py - 아이 NPC 캐릭터 Asset
#
# 출산 시 동적 생성되는 아이 NPC.
# pregnancy.spawn_child()에서 인스턴스 생성 후 속성 설정.

from assets.base import Character, build_focus_rules, build_describe_rules


class Child(Character):
    """아이 NPC — 출산 시 동적 생성"""
    unique_id = "child"
    name = "아이"
    type = "character"

    props = {
        "성별": 1,  # 1=male, 출산 시 랜덤 결정
        "나이": 0,
        "생존:체력": 50,
        "생존:최대체력": 50,
        "생존:포만감": 100,
        "부모:어머니": "",
        "부모:아버지": "",
    }

    DESCRIBE_RULES = build_describe_rules(
        "child",
        activities=[
            ("수면", "{name}(이)가 새근새근 자고 있다."),
            ("식사", "{name}(이)가 음식을 먹고 있다."),
            ("산책", "{name}(이)가 주변을 돌아다니고 있다."),
        ],
        default_text="{name}(이)가 주변을 두리번거리고 있다.",
        order=["activity", "default", "fatigue"],
    )

    FOCUS_RULES = build_focus_rules(
        "child",
        activities=[
            ("수면", "평화롭게 잠들어 있다."),
            ("식사", "열심히 먹고 있다."),
            ("산책", "호기심 가득한 눈으로 돌아다니고 있다."),
        ],
        default_text="어린아이다. 호기심 가득한 눈으로 주변을 바라보고 있다.",
        order=["activity", "mood", "default"],
    )
