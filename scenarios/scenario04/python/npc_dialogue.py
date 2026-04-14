# npc_dialogue.py — S04 생성형 NPC(Tier-3) 상황별 대사 풀
#
# 아키타입 × 상황 → 라인 목록. get_line()으로 랜덤 1개 선택.
# 고정 NPC는 자체 Character 서브클래스에서 override 가능.
#
# Phase 1 범위 (2026-04-14):
#   - greeting, invite_accept/decline/full, dismiss_leave, dungeon_ambient
#   - vote_advance / vote_return (다수결 선호 표현)
#
# Phase 2 (성인 모드 시): romance_line_generator.py의 S02 tone_templates로 확장.

import random

import morld
from engine import persona as _persona


# ========================================
# 대사 풀 (아키타입 → 상황 → 라인 리스트)
# ========================================
# 라인은 "{name}" 등 format 키 지원 — get_line(context=…)로 주입.

_LINES = {
    "stoic": {
        "greeting": [
            "...무슨 일이지.",
            "할 말이 있다면 짧게.",
            "...듣고 있다.",
        ],
        "invite_accept": [
            "좋아. 함께 가지.",
            "...알겠다. 그럴 만한 이유가 있겠지.",
        ],
        "invite_decline": [
            "미안하지만, 그럴 생각 없다.",
            "...아니, 나는 빠지겠다.",
        ],
        "invite_switch": [
            "...이 파티에 미련은 없다. 간다.",
            "네 제안이 낫군. 여기서 빠지지.",
        ],
        "invite_loyalty_decline": [
            "...지금 리더와의 약속이 있다.",
            "이 파티는 떠날 수 없다.",
        ],
        "invite_full": [
            "자리가 없어 보이는군.",
        ],
        "dismiss_leave": [
            "...알겠다. 각자의 길을 가자.",
            "여기서 끝인가. 그래, 무운을.",
        ],
        "dungeon_ambient": [
            "...집중해.",
            "발소리에 주의해라.",
            "이 길, 냄새가 좋지 않군.",
        ],
        "vote_advance": [
            "아직 물러설 때가 아니다.",
            "계속 가자. 뒤돌아볼 이유가 없어.",
        ],
        "vote_return": [
            "무리하지 말자. 돌아가는 게 낫다.",
            "여기서 멈추는 게 현명해.",
        ],
    },
    "cheerful": {
        "greeting": [
            "오, 안녕! 무슨 일이야?",
            "헤이, 나 부른 거야?",
            "뭐 재밌는 얘기 있어?",
        ],
        "invite_accept": [
            "좋아좋아! 같이 가자!",
            "오케이, 내가 빠질 순 없지!",
        ],
        "invite_decline": [
            "아~ 미안, 지금은 좀 그래.",
            "헤헤, 오늘은 패스할래.",
        ],
        "invite_switch": [
            "오케이! 지금 파티는 좀 지루했거든.",
            "좋아, 새 출발이야!",
        ],
        "invite_loyalty_decline": [
            "미안~ 지금 파티가 재밌어서.",
            "헤헤, 이 사람들이랑 더 놀고 싶어.",
        ],
        "invite_full": [
            "이미 꽉 찬 거 아냐? 자리 없어 보이는데.",
        ],
        "dismiss_leave": [
            "아쉽다~ 또 보자!",
            "흐음, 알겠어. 잘 지내!",
        ],
        "dungeon_ambient": [
            "여기 분위기 죽이네!",
            "흐음~ 뭔가 나올 것 같은데?",
            "다들 너무 심각한 거 아냐?",
        ],
        "vote_advance": [
            "가자가자! 재밌을 것 같은데!",
            "여기서 물러나면 김새잖아!",
        ],
        "vote_return": [
            "음, 오늘은 여기까지 할까?",
            "배고파... 돌아가서 먹자.",
        ],
    },
    "timid": {
        "greeting": [
            "아, 저... 네?",
            "...왜, 왜 그러세요?",
            "제, 제가 뭐 잘못했나요?",
        ],
        "invite_accept": [
            "저, 정말요? 가, 갈게요...",
            "저 같은 게 도움이 될지 모르겠지만... 네.",
        ],
        "invite_decline": [
            "죄, 죄송해요. 저는 좀...",
            "무, 무리예요. 못 가요.",
        ],
        "invite_switch": [
            "저, 정말요? 옮겨도 되나요...?",
            "...네, 따라갈게요.",
        ],
        "invite_loyalty_decline": [
            "죄, 죄송해요. 이분들한테 받은 게 있어서요...",
            "...여기 리더한테 미안해서요.",
        ],
        "invite_full": [
            "이, 이미 다 찬 것 같은데요...",
        ],
        "dismiss_leave": [
            "아, 알겠어요... 조심히 다니세요.",
            "...네, 미안해요. 짐이 됐죠.",
        ],
        "dungeon_ambient": [
            "여, 여기 무서워요...",
            "...방금 뭔가 소리 안 났어요?",
            "빨리 지나가요, 네?",
        ],
        "vote_advance": [
            "...가, 가야 한다면 가겠지만...",
            "계속 가는 게 맞나요...?",
        ],
        "vote_return": [
            "돌, 돌아가요. 위험해요.",
            "여기까지만 해요, 네?",
        ],
    },
    "fierce": {
        "greeting": [
            "뭐야, 용건 있어?",
            "말해. 시간 없다.",
            "뭘 봐.",
        ],
        "invite_accept": [
            "흥, 좋아. 따라가 주지.",
            "재밌겠군. 가자.",
        ],
        "invite_decline": [
            "내키지 않는다. 꺼져.",
            "웃기지 마. 네 밑으론 안 가.",
        ],
        "invite_switch": [
            "흥, 이 파티도 한물갔지. 간다.",
            "네 쪽이 더 재밌어 보인다. 좋아.",
        ],
        "invite_loyalty_decline": [
            "웃기지 마. 내가 여길 왜 떠나?",
            "네 밑으로 가느니 여기가 낫다.",
        ],
        "invite_full": [
            "이미 똘마니 다 모은 거 아냐?",
        ],
        "dismiss_leave": [
            "흥, 알았다. 어디 잘해봐.",
            "그래, 여기까지군. 또 보지 말자.",
        ],
        "dungeon_ambient": [
            "덤벼라, 뭐든.",
            "...지루하군.",
            "한 놈이라도 나와 봐라.",
        ],
        "vote_advance": [
            "당연히 간다. 뭘 망설여?",
            "끝까지 밀어붙여!",
        ],
        "vote_return": [
            "...젠장, 오늘은 안 되겠다.",
            "쪽팔리지만, 후퇴다.",
        ],
    },
    "innocent": {
        "greeting": [
            "안녕하세요! 저에게 볼일이 있으신가요?",
            "와, 불러주셔서 감사해요!",
            "네! 무슨 일이세요?",
        ],
        "invite_accept": [
            "정말요? 제가 도움이 될게요!",
            "와, 같이 가도 돼요? 좋아요!",
        ],
        "invite_decline": [
            "죄송해요. 지금은 조금 어려워요.",
            "마음만 받을게요. 정말 감사해요.",
        ],
        "invite_switch": [
            "정말요? 가도 될까요...?",
            "궁금해요. 같이 가요!",
        ],
        "invite_loyalty_decline": [
            "이분들이 잘 대해주셔서요... 죄송해요.",
            "지금은 여기가 제 자리인 것 같아요.",
        ],
        "invite_full": [
            "어라, 자리가 없는 것 같아요.",
        ],
        "dismiss_leave": [
            "아쉽지만... 잘 지내세요!",
            "네, 알겠어요. 또 만나요!",
        ],
        "dungeon_ambient": [
            "이런 곳에도 꽃이 필까요?",
            "...조금 무서워요.",
            "모두 괜찮으세요?",
        ],
        "vote_advance": [
            "끝까지 가봐요! 분명 좋은 일이 있을 거예요.",
            "여기서 돌아가면 아쉬울 것 같아요.",
        ],
        "vote_return": [
            "다들 지친 것 같아요. 돌아가요.",
            "무리하지 않는 게 좋지 않을까요?",
        ],
    },
    "cold": {
        "greeting": [
            "...무슨 용건이지.",
            "짧게 말해.",
            "시간 낭비는 하지 마라.",
        ],
        "invite_accept": [
            "...이득이 있다면야. 좋다.",
            "흥, 뭐라도 건지겠지. 가지.",
        ],
        "invite_decline": [
            "내가 왜 네 밑에서? 됐다.",
            "그만한 가치가 없다. 거절한다.",
        ],
        "invite_switch": [
            "...네가 더 이득이군. 간다.",
            "이 파티는 성과가 시원찮았지. 갈아타자.",
        ],
        "invite_loyalty_decline": [
            "계약이 있다. 어길 수 없어.",
            "지금 리더가 쥐여준 게 있거든. 못 떠난다.",
        ],
        "invite_full": [
            "이미 다 찼군. 애쓰지 마.",
        ],
        "dismiss_leave": [
            "그래, 여기까지 쓸 만큼 썼지. 잘 가라.",
            "뭐, 예상대로군.",
        ],
        "dungeon_ambient": [
            "...이 근처에 뭐가 있을 텐데.",
            "쓸 만한 건 다 챙겨둬.",
            "흥, 함정이라도 있나.",
        ],
        "vote_advance": [
            "여기서 돌아가면 손해다. 간다.",
            "더 깊이. 전리품이 기다린다.",
        ],
        "vote_return": [
            "이득 없는 위험은 사양한다. 귀환이다.",
            "...철수하지. 감이 좋지 않다.",
        ],
    },
    "devoted": {
        "greeting": [
            "부르셨습니까?",
            "네, 여기 있습니다. 말씀하세요.",
            "...무엇을 도와드릴까요?",
        ],
        "invite_accept": [
            "당신이 원한다면 어디든.",
            "영광입니다. 함께 가겠습니다.",
        ],
        "invite_decline": [
            "...죄송합니다. 지금은 따를 수 없습니다.",
            "제 자리는 여기입니다. 용서하세요.",
        ],
        "invite_switch": [
            "...지금 리더를 배신하는 게 되겠지만, 당신이 원한다면.",
            "당신의 뜻이라면 따르겠습니다.",
        ],
        "invite_loyalty_decline": [
            "죄송합니다. 제 충성은 여기 리더에게 있습니다.",
            "...지금 섬기는 분을 두고 갈 수는 없습니다.",
        ],
        "invite_full": [
            "이미 동료가 가득하시군요.",
        ],
        "dismiss_leave": [
            "...알겠습니다. 당신의 결정을 존중합니다.",
            "그래야 한다면. 무운을 빕니다.",
        ],
        "dungeon_ambient": [
            "어느 쪽이든 당신을 따르겠습니다.",
            "제 걱정은 마십시오.",
            "앞서겠습니다.",
        ],
        "vote_advance": [
            "당신이 가신다면 저도 갑니다.",
            "원하시는 대로. 전진이든 뭐든.",
        ],
        "vote_return": [
            "...당신의 안위가 먼저입니다. 돌아가시죠.",
            "여기서 멈추시죠. 무리하지 마세요.",
        ],
    },
}


# 방 타입별 선호 대사 (아키타입 공통 풀 — 차후 아키타입별 override 가능)
_ROOM_PREF_LINES = {
    "room_pref_battle": [
        "싸우자.",
        "한판 해보자.",
        "여긴 전투가 낫겠어.",
        "피가 끓는군.",
    ],
    "room_pref_rest": [
        "잠시 쉬자.",
        "피곤해... 쉬어가자.",
        "몸 상태가 안 좋아.",
        "회복부터 하자.",
    ],
    "room_pref_exit": [
        "이제 돌아가자.",
        "충분하다. 마을로.",
        "오늘은 여기까지.",
        "귀환이 낫겠어.",
    ],
}


# 폴백 (아키타입 풀이 없거나 상황 키 없을 때)
_FALLBACK = {
    "greeting":                ["...",],
    "invite_accept":           ["...알겠어. 함께 가지.",],
    "invite_decline":          ["...미안, 같이 가고 싶지 않아.",],
    "invite_switch":           ["...알겠어. 옮기지.",],
    "invite_loyalty_decline":  ["...지금 파티를 떠날 수 없어.",],
    "invite_full":             ["미안해. 내가 들어갈 자리는 없는 것 같네.",],
    "dismiss_leave":           ["...알겠어. 각자의 길을 가자.",],
    "dungeon_ambient":         ["...",],
    "vote_advance":            ["계속 가자.",],
    "vote_return":             ["돌아가자.",],
    "room_pref_battle":        _ROOM_PREF_LINES["room_pref_battle"],
    "room_pref_rest":          _ROOM_PREF_LINES["room_pref_rest"],
    "room_pref_exit":          _ROOM_PREF_LINES["room_pref_exit"],
}


# ========================================
# API
# ========================================

def get_line(unit_id, situation, **context) -> str:
    """유닛의 아키타입으로 상황 대사 1개 선택.

    Args:
        unit_id: 대상 NPC
        situation: 상황 키 (greeting / invite_accept / ...)
        context: format 플레이스홀더 주입 (예: name="세라")

    Returns:
        포맷 적용된 한 줄. 실패 시 "..."
    """
    archetype = _persona.get_archetype(unit_id)
    pool = _LINES.get(archetype, {})
    lines = pool.get(situation)
    if not lines:
        lines = _FALLBACK.get(situation, ["..."])

    line = random.choice(lines)
    if context:
        try:
            line = line.format(**context)
        except (KeyError, IndexError):
            pass
    return line


def get_preference(unit_id, context=None) -> str:
    """다수결 선호 1차 결정 — 'advance' 또는 'return'.

    Phase 1: 아키타입별 성향 기반 가중 랜덤.
      - cheerful/fierce/cold/devoted: advance 쪽으로 기움
      - timid/innocent: return 쪽으로 기움
      - stoic: 중립
    Phase 2(인텐션 시스템 이후): 현재 상태(HP/침식/관계)로 정교화 예정.
    """
    archetype = _persona.get_archetype(unit_id)
    advance_weight = {
        "fierce":    0.80,
        "cheerful":  0.65,
        "cold":      0.60,
        "devoted":   0.55,
        "stoic":     0.50,
        "innocent":  0.40,
        "timid":     0.25,
        "gentle":    0.45,
        "seductive": 0.50,
        "proud":     0.60,
    }.get(archetype, 0.50)

    return "advance" if random.random() < advance_weight else "return"
