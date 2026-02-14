# assets/characters/sera.py - 세라 캐릭터 Asset
#
# ============================================================
# 캐릭터 설정
# ============================================================
# 이름: 세라 (Sera)
# 성별: 여성
# 나이: 불명 (20대 초중반으로 추정, 기억 없음)
#
# 외모:
#   - 흑발 장발, 갈색 눈
#   - 단단하고 균형 잡힌 체격 (사냥꾼)
#   - 날카로운 눈매, 과묵한 인상
#
# 성격:
#   - 과묵함: 말수가 적고, 필요한 말만 함. "..."이 기본 반응
#   - 듬직함: 묵묵히 자신의 역할을 수행, 신뢰할 수 있는 존재
#   - 리더십: 자연스럽게 그룹을 이끄는 카리스마
#   - 내면: 겉으로는 무심해 보이지만, 동료들을 깊이 아끼고 보호함
#
# 좋아하는 것:
#   - 사냥, 숲의 고요함, 새벽 공기
#   - 활을 정비하는 시간, 집중하는 순간
#   - 밀라의 요리 (표현은 안 하지만)
#   - (비밀) 귀여운 것 - 방에 낡은 곰 인형이 있음. 절대 인정 안 함
#
# 싫어하는 것:
#   - 쓸데없는 수다, 시끄러운 것
#   - 무의미한 질문, 방해받는 것
#   - 나약함을 드러내는 것
#
# 취미:
#   - 사냥 (생존 수단이자 특기)
#   - 장비 정비 (활, 화살 손질)
#   - 순찰 (저택 주변 경계)
#
# 과거사:
#   - 기억 없음. 어느 날 숲속에서 눈을 떴음
#   - 밀라에게 발견되어 저택에 합류
#   - 과거에 대해 묻지도 말하지도 않음
#
# 현재 배경:
#   - 저택 그룹의 리더 역할
#   - 사냥과 경비를 전담
#   - 밀라(요리/살림), 리나(채집/빨래)와 함께 생활
#   - 그룹의 안전을 최우선으로 생각
#
# 말투 특징:
#   - "..."으로 시작하거나 끝나는 경우 많음
#   - 짧고 간결한 문장
#   - 감정 표현이 적음 (하지만 행동으로 보여줌)
#   - 명령조보다는 단언하는 말투
#
# 관계:
#   - 밀라: 신뢰하는 동료. 자신을 발견해준 사람
#   - 리나: 지켜봐야 할 동생 같은 존재
#   - 플레이어: 처음엔 경계, 점차 인정하게 됨
#
# ============================================================
# Rule-based 텍스트 선택 시스템 사용
# - TALK_RULES: 대화 규칙
# - DESCRIBE_RULES: 장소에서 보이는 묘사 규칙
# - FOCUS_RULES: 클릭했을 때 상세 묘사 규칙
# ============================================================

import morld
import ui
from assets.base import Character, build_focus_rules, build_describe_rules
from think import BaseAgent, register_agent_class

_M = 60_000  # millis per minute


class Sera(Character):
    unique_id = "sera"
    name = "세라"
    type = "female"
    hearing_type = "keen"
    sexual_orientation = "bisexual"
    props = {
        "성별": "female", "성적지향": "bisexual",
        "외모:흑발": 1, "외모:장발": 1, "외모:갈색눈": 1,
        "성격:과묵함": 1, "성격:듬직함": 1, "성격:리더십": 1,
        "나이": 23,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 5,
        "can:lie_down": 1,
        "can:sleep": 1,
        "can:bath": 1,
        "can:toggle_switch": 1,
        "can:chop": 1,
        "생존:체력": 100, "생존:최대체력": 100,
        "생존:포만감": 80, "생존:최대포만감": 100,
        "처녀:구강": 1,
        "처녀:음부": 1,
        "처녀:항문": 1,
        "근력": 6, "체력": 6,
        "체격": 3, "가슴:크기": 2,
    }
    actions = [
        "call:talk:대화",
        "call:errand:심부름#",         # 퀘스트 제안 가능 시만 표시
        "call:date:데이트 신청#",      # 데이트 중 아닐 때만 표시
        "call:end_date:데이트 종료#",  # 데이트 중일 때만 표시
        "call:hold_hands:손 잡기#",    # 조건 충족 시만 표시
        "call:date_hug:안아주기#",     # 조건 충족 시만 표시
        "call:date_kiss:키스#",        # 조건 충족 시만 표시
        "call:give_gift:선물하기",
        "call:romance:스킨십",
        "call:force_romance:강제 행위",
        "call:debug_props:(디버그) 속성 보기#",
        "call:debug_affection_up:(디버그) 호감도 +10#",
        "call:debug_affection_down:(디버그) 호감도 -10#",
        "call:debug_arousal_up:(디버그) 성욕 +20#",
        "call:debug_arousal_down:(디버그) 성욕 -20#",
        "call:debug_submission_up:(디버그) 복종 +20#",
        "call:debug_submission_down:(디버그) 복종 -20#",
        "call:debug_work_order:(디버그) 작업지시#",
        "call:debug_pregnancy_info:(디버그) 임신 정보#",
        "call:debug_force_conceive:(디버그) 강제 임신#",
        "call:debug_force_birth:(디버그) 강제 출산#",
    ]
    mood = []

    # ========================================
    # 대화 주제 목록 (주제 선택 메뉴)
    # ========================================
    TALK_TOPICS = [
        "잡담",
        "본인에 대해",
        "사냥 방법",
        "장비 관리",
    ]

    # ========================================
    # 대화 규칙 (주제별 조건 → 대사 또는 메서드명)
    # 위에서부터 순서대로 체크, 첫 번째 매칭 사용
    # - dict: {"pages": [...]} 형태의 간단한 대사
    # - str: "_"로 시작하는 메서드명 → 복잡한 대화 처리
    # ========================================
    TALK_RULES = {
        "잡담": [
            # 특수 상황 (최우선)
            ({"mood": "분노"}, {"pages": ["...", "...말 걸지 마."]}),
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 데이트 중 대화 (우선)
            ({"on_date": True, "호감": 70}, {"pages": ["......", "...같이 있으니 좋군."]}),
            ({"on_date": True, "호감": 50}, {"pages": ["......", "...어디로 갈까?"]}),
            ({"on_date": True}, {"pages": ["......", "...뭐가 보고 싶어?"]}),

            # Activity + 호감도 조합 (복잡한 대화는 메서드로 위임)
            ({"activity": "사냥", "호감": 50}, "_talk_hunt_friendly"),
            ({"activity": "사냥"}, {"pages": ["...조용히 해.", "사냥감이 달아나잖아."]}),
            ({"activity": "순찰", "호감": 50}, "_talk_patrol_friendly"),
            ({"activity": "순찰"}, {"pages": ["...순찰 중이다.", "이상 없다."]}),
            ({"activity": "식사"}, {"pages": ["(조용히 먹고 있다)", "...뭔가?"]}),
            ({"activity": "정비"}, {"pages": ["...활을 손보는 중이다.", "나중에 와라."]}),
            ({"activity": "벌목"}, {"pages": ["...보다시피 바쁘다.", "...위험하니 뒤로 가라."]}),
            ({"activity": "낚시"}, {"pages": ["...쉿.", "...물고기가 달아나잖아."]}),
            ({"activity": "독서"}, {"pages": ["...읽는 중이다.", "...조용히 해라."]}),
            ({"activity": "휴식"}, {"pages": ["......", "...뭐냐."]}),
            ({"activity": "목욕"}, {"pages": ["(목욕 중이다)", "...나중에 와라."]}),
            ({"activity": "준비"}, {"pages": ["...지금 준비 중이다.", "..."]}),

            # 날씨 반응
            ({"weather": "비", "호감": 30}, {"pages": ["...비가 오는군.", "...안에 들어가 있어."]}),
            ({"weather": "비"}, {"pages": ["...비다."]}),
            ({"weather": "눈"}, {"pages": ["...눈이 온다.", "...사냥감이 줄겠군."]}),

            # 호감도 기반 (진척도 증가 로직 포함)
            ({"호감": 70}, "_talk_friendly_high"),
            ({"호감": 50}, "_talk_friendly_mid"),

            # mood 기반
            ({"mood": "기쁨"}, {"pages": ["......", "...오늘은 기분이 좋군."]}),
            ({"mood": "슬픔"}, {"pages": ["......", "..."]}),

            # 기본값
            ({}, {"pages": ["......", "...할 말이 있으면 빨리."]}),
        ],

        "본인에 대해": [
            # 특수 상황
            ({"mood": "분노"}, {"pages": ["...", "...지금은 아니다."]}),
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 진척도별 사적인 대화 (플래그로 일회성 체크)
            ({"호감": 70, "진척도": 3}, "_talk_progress_3"),
            ({"호감": 60, "진척도": 2}, "_talk_progress_2"),
            ({"호감": 50, "진척도": 1}, "_talk_progress_1"),

            # 호감도 기반
            ({"호감": 70}, {"pages": ["......", "...왜 내가 궁금한 거지?", "......", "...이상한 녀석이군."]}),
            ({"호감": 50}, {"pages": ["...세라다.", "...이 저택의 경비와 사냥을 맡고 있다.", "...그게 다야."]}),
            ({"호감": 30}, {"pages": ["......", "...왜 궁금해하는 건데?"]}),

            # 기본값
            ({}, {"pages": ["......", "...너한테 말할 건 없어."]}),
        ],

        "사냥 방법": [
            # 특수 상황
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "...사냥을 배우고 싶어?",
                "...일단 기본은 인내심이다.",
                "...사냥감이 나타날 때까지 기다려야 해.",
                "...그리고 한 번 겨냥하면 흔들리면 안 돼.",
                "...원하면 다음에 같이 가도 좋다.",
            ]}),
            ({"호감": 50}, {"pages": [
                "...사냥은 활이 필요해.",
                "...활이 없으면 덫을 써도 된다.",
                "...토끼굴에 덫을 놓으면 잡을 수 있다.",
            ]}),
            ({"호감": 30}, {"pages": [
                "...사냥을 배우고 싶어?",
                "...일단 조용히 하는 법부터 배워.",
            ]}),

            # 기본값
            ({}, {"pages": ["......", "...너한테 가르쳐줄 이유가 없어."]}),
        ],

        "장비 관리": [
            # 특수 상황
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "...장비 관리가 궁금해?",
                "...활은 습기에 약해. 건조한 곳에 보관해야 해.",
                "...현은 끊어지기 전에 미리 교체하고.",
                "...칼날은 매일 점검해. 무딘 칼은 위험하다.",
                "...도구는 생명과 직결되니까.",
            ]}),
            ({"호감": 50}, {"pages": [
                "...장비는 항상 점검해.",
                "...사용 후엔 닦고 말려둬.",
                "...기본적인 거다.",
            ]}),
            ({"호감": 30}, {"pages": [
                "...장비는 소중히 다뤄.",
                "...그게 다야.",
            ]}),

            # 기본값
            ({}, {"pages": ["......", "...네 장비는 네가 관리해."]}),
        ],
    }

    # ========================================
    # Describe 규칙 (장소에서 보이는 묘사)
    # {name}은 자동으로 캐릭터 이름으로 치환됨
    # ========================================
    DESCRIBE_RULES = build_describe_rules(
        "stoic",
        specials=[
            ({"도구분실:can:chop": 1, "activity": "순찰"},
             "{name}가 순찰하고 있다. 벌목 도구를 찾지 못한 것 같다."),
            ({"도구분실:can:fish": 1, "activity": "순찰"},
             "{name}가 순찰하고 있다. 낚시 도구가 없어 낚시를 못 하는 모양이다."),
        ],
        traveling=[
            ({"is_traveling": True, "activity": "사냥"}, "{name}가 사냥터로 향하고 있다."),
            ({"is_traveling": True, "activity": "순찰"}, "{name}가 순찰을 위해 이동 중이다."),
            ({"is_traveling": True, "activity": "벌목"}, "{name}가 벌목터로 향하고 있다."),
            ({"is_traveling": True, "activity": "낚시"}, "{name}가 낚시터로 향하고 있다."),
            ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),
        ],
        activities=[
            ("사냥", "{name}가 활을 점검하고 있다."),
            ("순찰", "{name}가 주변을 경계하고 있다."),
            ("벌목", "{name}가 묵묵히 나무를 베고 있다."),
            ("낚시", "{name}가 낚싯대를 드리우고 앉아 있다."),
            ("독서", "{name}가 조용히 책을 읽고 있다."),
            ("식사", "{name}가 조용히 식사 중이다."),
            ("수면", "{name}가 조용히 잠들어 있다."),
            ("휴식", "{name}가 벽에 기대어 쉬고 있다."),
            ("정비", "{name}가 장비를 손보고 있다."),
            ("목욕", "{name}가 목욕 중이다."),
        ],
        weather=[
            ({"weather": "비", "is_indoor": False}, "{name}가 비를 맞으며 서 있다."),
        ],
        locations=[
            ({"location": (0, 24)}, "{name}가 사냥감을 추적하고 있다."),
            ({"location": (0, 12)}, "{name}가 앞마당을 순찰하고 있다."),
            ({"location": (0, 1)}, "{name}가 창가에 서서 밖을 바라본다."),
        ],
        default_text="{name}가 과묵하게 서 있다.",
    )

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = build_focus_rules(
        "stoic",
        activities=[
            ("사냥", "활을 들고 날카로운 눈으로 주변을 살핀다."),
            ("순찰", "날카로운 눈으로 주변을 경계하고 있다."),
            ("벌목", "도끼를 휘두르며 나무를 베고 있다. 정확한 동작이다."),
            ("낚시", "물 위에 시선을 고정하고 조용히 앉아 있다."),
            ("독서", "책장을 넘기며 집중하고 있다. 의외로 진지하다."),
            ("식사", "조용히 음식을 먹고 있다."),
            ("수면", "경계심 없이 잠들어 있다."),
            ("휴식", "벽에 기대어 쉬고 있다. 경계는 풀지 않았다."),
            ("정비", "활과 화살을 꼼꼼히 점검하고 있다."),
        ],
        default_text="긴 흑발을 묶은 과묵한 여성. 저택의 리더로서 날카로운 갈색 눈이 인상적이다.",
        specials=[
            ({"도구분실:can:chop": 1}, "뭔가 찾는 듯한 표정이다. 벌목 도구가 보이지 않는 모양이다."),
            ({"도구분실:can:fish": 1}, "뭔가 찾는 듯한 표정이다. 낚시 도구가 없어 낚시를 못 하는 모양이다."),
        ],
    )

    # 흥분도 단계별 소음 강도 — 초반 조용, 후반 시끄러움
    ROMANCE_SOUND_PROFILE = {"levels": [5, 15, 50], "ecstasy": 70}

    # 애정행위 발각 시 반응 — 과묵하게 한마디
    ROMANCE_DISCOVERY_REACTIONS = {
        "default": {
            "text": ["......", "...그래.", "...(무표정으로 돌아선다)"],
            "exposed_text": ["......!", "...(눈을 돌린다)", "...옷이라도 입혀."],
            "effects": {"호감": -3, "반발": 3},
        },
        "lina": {
            "text": ["...리나랑?", "......(눈을 가늘게 뜬다)"],
            "exposed_text": ["...리나를...!", "......(이를 악문다)"],
            "effects": {"호감": -5, "반발": 5},
        },
        "mila": {
            "text": ["...밀라...", "......"],
            "exposed_text": ["...밀라가... 저 꼴로...", "......"],
            "effects": {"호감": -4, "반발": 4},
        },
    }

    # ========================================
    # 선물 선호도
    # ========================================
    GIFT_PREFERENCES = {
        "liked_categories": ["equipment", "material"],
        "favorite_items": ["hunting_bow", "wooden_sword"],
        "disliked_categories": ["trinket"],
        "favorite_foods": ["food_roasted_rabbit", "food_fish_set_meal"],
    }

    requires_condom = True  # 삽입 시 콘돔 요구 (경험:콘돔속임 ≥ 3이면 체념)

    # ========================================
    # 성적 선호 (체위/부위)
    # ========================================
    SEXUAL_PREFERENCES = {
        "preferred_positions": ["standing_face", "doggy"],
        "preferred_parts": ["V", "A"],
    }

    # ========================================
    # 스킨십 반응 (action:timing → 조건부 대사 리스트)
    # 세라: 과묵하지만 속으론 부끄러워함
    # ========================================
    # 반응 생성기 프로필 (archetype="stoic": 과묵형)
    REACTION_PROFILE = {
        "name": "세라",
        "archetype": "stoic",
        "speech_level": "rough",
        "speech_shifts": {},
        "vars": {},
        "line_overrides": {},
        "overrides": {
            # 크기통증: generator에 없는 세라 고유 반응
            "vaginal_penetration:during": {
                "stoic": {
                    "romance": ["세라가 찡그리며 숨을 참는다. \"...커, 아파...\"", "\"으... 아파, 그런데... 으응...\""],
                    "lust": ["세라가 찡그리며 숨을 참는다. \"...커, 아파...\""],
                },
            },
        },
    }

    # ========================================
    # 스킨십 반응 (action:timing → 2D좌표/조건부 대사)
    # 세라: 과묵하지만 속으론 부끄러워함
    #
    # 2D좌표: (호감, 욕망) → nearest-neighbor
    #   romance(80,70): 감정+흥분 / platonic(80,20): 수용
    #   lust(20,70): 몸만 반응 / rejection(20,20): 거부
    #
    # :during 항목은 generator(stoic 아키타입)가 자동 처리
    # ========================================
    ROMANCE_REACTIONS = {
        # ── 특수 조건 반응 ──
        "french_kiss:start": [
            ({"미경험:기억:첫키스": 1}, [
                ((80, 70), ["......!", "......(얼굴이 빨개진다)"]),
                ((20, 20), ["...갑자기 뭐하는...!"]),
            ]),
            ((80, 70), ["...응...", "...좋다...", "...또 해도 돼."]),
            ((80, 20), ["......(눈을 감는다)"]),
            ((20, 70), ["...으응...", "...숨이...", "...더..."]),
            ((20, 20), ["......", "...뭐냐."]),
        ],
        "deep_kiss:start": [
            ((80, 70), ["...으응... 더...", "...좋다..."]),
            ((80, 20), ["......(눈을 감는다)", "...키스..."]),
            ((20, 70), ["...숨이...", "...더..."]),
            ((20, 20), ["......", "...눈 감아."]),
        ],
        "nipple_lick:start": [
            ({"상태:수유": 1}, ["...! 거기, 나와...?!", "바보, 핥지 마... 나온다고..."]),
        ],
        "nipple_suck:start": [
            ({"상태:수유": 1}, ["빨지 마...! 나, 나오잖아...", "...이 바보... 모유가..."]),
        ],

        # ── :during ──
        "vaginal_penetration:during": [
            ({"크기통증": 1}, ["세라가 찡그리며 숨을 참는다. \"...커, 아파...\"", "\"으... 아파, 그런데... 으응...\""]),
        ],
        "anal_penetration:during": [
            ({"크기통증": 1}, ["세라가 찡그린다. \"뒤는... 더 아파...\""]),
        ],
        "nipple_suck:during": [
            ({"상태:수유": 1}, ["...계속 나오잖아...", "...이상해... 빨리면 더..."]),
        ],

        # ── 사정 참기 ──
        "hold_back_success:start": [
            ({}, ["세라가 안도한다. \"...참았구나.\"", "\"...무리하지 마.\" 세라가 숨을 고른다."]),
        ],
        "hold_back_failure:start": [
            ({}, ["세라가 놀란다. \"...! 안에...!?\"", "\"어...!? 안에 쏟았잖아...!\" 세라가 화들짝 놀란다."]),
        ],

        # ── 내부 사정 (특수 조건) ──
        "ejaculation_internal_음부:start": [
            ({"욕망": 80, "경험:질내사정": 5}, ["...안에 쏟아도... 괜찮아...", "...더... 안에..."]),
            ({"경험:질내사정": 3}, ["...또... 안에...", "...뜨거워... 이제 익숙해..."]),
        ],

        # ── 절정 (특수 조건) ──
        "ecstasy:start": [
            ({"미경험:기억:첫절정": 1}, ["......?! ...이게 뭐...야...?!", "...몸이... 갑자기...!", "...(처음 느끼는 감각에 당황하고 있다)"]),
            ({"경험:절정:V": 10}, ["...또... 가...!", "...(익숙한 듯 몸을 맡기며) ...으응..."]),
        ],

        # ── 정액 삼킴 (3인칭 서술) ──
        "swallow_semen_spit:start": [
            ({}, ["\"...삼킬 수 없어.\" 세라가 고개를 돌려 뱉는다.", "세라가 입에서 흘리며 고개를 숙인다. \"...못 삼키겠어.\""]),
        ],
        "swallow_semen_drip:start": [
            ({}, ["세라의 입에서 정액이 흘러내린다. \"...으...\"", "\"...무리야.\" 세라가 입을 열어 정액을 흘린다."]),
        ],
        "swallow_semen_vomit:start": [
            ({}, ["세라가 구역질을 하며 고개를 돌린다. \"...으엑...!\"", "\"...기분 나빠...!\" 세라가 구역질한다."]),
        ],

        # ── 강제 모드 ──
        "forced_start:start": [
            ({"경험:강제횟수": 5}, ["...(눈을 감고 체념한다.)", "...(저항을 포기한 듯 힘을 뺀다.)"]),
            ({}, ["하지 마...! 놓으라고!"]),
        ],
        "forced_ecstasy:start": [
            ({"경험:강제횟수": 5}, ["...(울먹이며 몸을 떨고 있다.)"]),
            ({}, ["싫어...! 이런 거... 느끼기 싫어...!"]),
        ],
        "forced_break_free:start": [
            ({}, ["다시는... 가까이 오지 마!"]),
        ],

        # ── 트랜스 ──
        "trance:start": [
            ({"성욕": 80}, ["...하아...! 멈추지 마...! ...더...!", "...머리가... 하얘져... 멈추면... 죽어..."]),
            ({}, ["...으...! ...몸이... 말을 안 들어...", "...싫어... 이런 거... 느끼는 거..."]),
        ],
        "trance_insert:start": [
            ({"성욕": 80}, ["...안에... 넣어... 빨리...", "...참을 수 없어... 넣을게..."]),
            ({}, ["...(무의식적으로 허리를 움직이고 있다.)", "...몸이... 제멋대로..."]),
        ],
    }

    # ========================================
    # NPC 주도 스킨십 설정
    # ========================================
    self_comfort_threshold = 85       # 자제력 높음
    self_comfort_max_length = 150     # 침실/욕실/화장실만 (length=150)

    INITIATIVE_CONFIG = {
        "arousal_threshold": 70,      # 성욕 70 이상
        "affection_threshold": 60,    # 호감도 60 이상
        "cooldown_millis": 480 * _M,   # 8시간 쿨다운
    }

    # 조건별 액션 시퀀스 (위에서부터 매칭)
    NPC_INITIATIVE_ACTIONS = [
        # 성욕 90 이상: 격렬한 시퀀스
        ({"성욕": 90, "호감": 50}, [
            {"action": "hug", "duration": 10},
            {"action": "deep_kiss", "duration": 15},
            {"action": "breast_touch", "duration": 10},
        ]),
        # 성욕 80 이상: 중간 시퀀스
        ({"성욕": 80}, [
            {"action": "hug", "duration": 15},
            {"action": "deep_kiss", "duration": 10},
        ]),
        # 기본: 포옹만
        ({}, [
            {"action": "hug", "duration": 20},
        ]),
    ]

    # 주도 중 반응 텍스트 (조건, 텍스트 리스트)
    INITIATIVE_REACTIONS = {
        "start": [
            ({"호감": 80}, ["...가만히 있어...", "...좀만...", "...네가 필요해..."]),
            ({}, ["......", "...가만히 있어.", "...움직이지 마."]),
        ],
        "during_hug": [
            ({"성욕": 80}, ["세라가 강하게 안고 있다. 숨소리가 거칠다."]),
            ({}, ["세라가 조용히 안고 있다.", "세라의 체온이 느껴진다."]),
        ],
        "during_deep_kiss": [
            ({}, ["세라가 깊이 키스하고 있다.", "세라의 숨결이 거칠다."]),
        ],
        "during_breast_touch": [
            ({}, ["세라가 몸을 밀착하고 있다.", "세라가 손을 잡아 끌고 있다."]),
        ],
        "during_genital_touch": [
            ({"성욕": 80}, ["세라가 거칠게 숨을 몰아쉬며 손을 움직인다."]),
            ({}, ["세라가 조용히 당신의 아래를 만지고 있다."]),
        ],
        "during_clit_rub": [
            ({"성욕": 90}, ["세라의 손놀림이 거칠어지고 있다.", "세라가 당신의 반응을 살피고 있다."]),
            ({}, ["세라가 조심스럽게 당신을 자극하고 있다."]),
        ],
        "escape_fail": [
            ({}, ["...도망가려고?", "...안 돼.", "...싫어.", "...놓아주지 않을 거야."]),
        ],
        "satisfied": [
            ({"호감": 80}, ["...고마워...", "...좀 나아졌어."]),
            ({}, ["...끝이다.", "...가도 돼.", "......(물러선다)"]),
        ],
    }

    # NPC 주도 시 허용되는 행위 (진척도/캐릭터 성격 기반)
    # 세라: 애정도에 따라 점진적으로 행위 범위 확장
    INITIATIVE_ACTION_FILTERS = [
        ({"호감": 95}, ["hug", "deep_kiss", "breast_touch", "genital_touch", "clit_rub", "penis_touch", "penis_rub"]),
        ({"호감": 85}, ["hug", "deep_kiss", "breast_touch", "genital_touch", "penis_touch"]),
        ({"호감": 80}, ["hug", "deep_kiss", "breast_touch"]),
        ({"호감": 40}, ["hug", "deep_kiss"]),
        ({}, ["hug"]),
    ]

    # ========================================
    # 은신 성공 반응 (세라: 스릴에 흥분)
    # ========================================
    # 세라는 무뚝뚝하지만 위험한 상황에서 스릴을 느끼는 타입
    STEALTH_REACTIONS = {
        "text": [
            ({"성욕": 50}, ["...위험했어...", "...(숨을 거칠게 몰아쉰다)"]),
            ({"호감": 40}, ["......", "...조심해."]),
            ({}, ["......", "...(긴장한 표정)"]),
        ],
        "effects": {"성욕": 5},  # 스릴에 더 흥분
    }

    EQUIP_CHANGE_REACTIONS = {
        "equip": "세라가 무기를 힐끗 보더니 고개를 끄덕인다.",
        "unequip": "세라가 빈 손을 보고 살짝 고개를 갸웃한다.",
    }

    FRIENDLY_TALK_CONFIG = {
        "mid": {
            "dialog": ["......", "...무슨 일이야?"],
            "progress_cap": 3,
        },
        "high": {
            "dialog": ["......", "...뭐, 괜찮아?"],
            "progress_cap": 3,
        },
    }

    PROGRESS_DIALOGS = {
        1: {
            "fallback": ["......", "...무슨 일이야?"],
            "dialog": [
                "......",
                "...내 이름은 세라.",
                "...이 저택에서 사냥과 경비를 맡고 있다.",
                "...밀라와 리나도 여기 있지.",
                "......",
                "...그게 다야.",
            ],
        },
        2: {
            "fallback": ["......", "...뭐, 괜찮아?"],
            "dialog": [
                "...좋아하는 거?",
                "......",
                "...사냥할 때가 좋다.",
                "...숲의 냄새, 바람의 방향...",
                "...그런 것들에 집중할 때.",
                "......",
                "...머리가 맑아지거든.",
                "...싫어하는 건...",
                "...쓸데없는 수다.",
                "......",
                "...지금 하고 있는 것 같지만.",
            ],
        },
        3: {
            "fallback": ["......", "...뭐, 괜찮아?"],
            "dialog": [
                "......",
                "...예전 일?",
                "......",
                "...기억나는 건 별로 없어.",
                "...눈을 떴을 때, 이미 여기였다.",
                "...밀라가 날 발견했고...",
                "...그때부터 같이 살았다.",
                "......",
                "...그 전의 일은...",
                "...모른다.",
                "......",
                "...알고 싶지도 않아.",
            ],
        },
    }

    ROOM_PRIVACY_CONFIG = {
        "수면": {
            "threshold": 50,
            "high": {
                "dialog": ["[세라]", "...아직 여기 있었어?", "신경 쓰지 마. 그냥 잘게."],
            },
            "low": {
                "dialog": ["[세라]", "...나가줘. 자야 하니까."],
                "teleport": 1,
                "after": "세라의 방에서 나왔다.",
            },
        },
        "목욕": {
            "threshold": 70,
            "high": {
                "dialog": ["[세라]", "......", "...나가줘. 지금은 안 돼."],
                "teleport": 1,
                "after": "욕실에서 나왔다.",
            },
            "low": {
                "dialog": ["[세라]", "...뭐 해. 나가.", "세라의 시선이 차갑다."],
                "teleport": 1,
                "after": "욕실에서 쫓겨났다.",
            },
        },
        "화장실": {
            "threshold": 0,
            "low": {
                "dialog": ["[세라]", "...나가."],
                "teleport": 1,
                "after": "화장실에서 쫓겨났다.",
            },
        },
    }

    # ========================================
    # 복잡한 대화 메서드 (Generator)
    # TALK_RULES에서 "_메서드명"으로 위임됨
    # ========================================

    def _talk_hunt_friendly(self, context):
        """사냥 중 + 호감 50 이상: 같이 사냥 제안"""
        name = context.get("name", self.name)

        choice = yield ui.dialog(
            f"[{name}]\n"
            "...같이 사냥할래?\n\n"
            "[url=@ret:yes]같이 가겠다[/url]\n"
            "[url=@ret:no]괜찮다[/url]",
            autofill="off"
        )

        if choice == "yes":
            yield ui.dialog([f"[{name}]", "...조용히만 해."])
            # 플레이어를 따라다니기 (30분)
            player_id = morld.get_player_id()
            morld.set_npc_job(self.instance_id, "follow", 30 * _M, player_id)
        else:
            yield ui.dialog([f"[{name}]", "...그래."])

    def _talk_patrol_friendly(self, context):
        """순찰 중 + 호감 50 이상: 같이 순찰 제안"""
        name = context.get("name", self.name)

        choice = yield ui.dialog(
            f"[{name}]\n"
            "...순찰 중이다.\n"
            "...같이 돌아볼래?\n\n"
            "[url=@ret:yes]같이 가겠다[/url]\n"
            "[url=@ret:no]괜찮다[/url]",
            autofill="off"
        )

        if choice == "yes":
            yield ui.dialog([f"[{name}]", "...따라와."])
            # 플레이어를 따라다니기 (60분)
            player_id = morld.get_player_id()
            morld.set_npc_job(self.instance_id, "follow", 60 * _M, player_id)
        else:
            yield ui.dialog([f"[{name}]", "...알았다."])

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 만남 — 도구 분실 시 30% 확률 언급"""
        base_result = super().on_meet_player(player_id)
        if base_result is not None:
            return base_result

        # 도구 분실 언급 (30% 확률)
        import random
        if random.random() < 0.3:
            props = morld.get_unit_props(self.instance_id)
            if props:
                cap_msgs = {
                    "can:chop": "...도끼가 도구함에 없더라.\n...혹시 봤으면 돌려놔.",
                    "can:fish": "...낚시대가 보이지 않아.\n...어디 갔는지 모르겠군.",
                }
                for key, val in props.items():
                    if key.startswith("도구분실:") and val == 1:
                        cap = key[len("도구분실:"):]
                        msg = cap_msgs.get(cap)
                        if msg:
                            return self._tool_missing_dialog(msg)
        return None

    def _tool_missing_dialog(self, message):
        """도구 분실 언급 다이얼로그"""
        yield ui.dialog([f"[{self.name}]", message])

    def _first_meet_handler(self, player_id):
        """첫 만남 이벤트 핸들러 - 누적형 대화 (Conversation)"""
        # 누적형 대화 빌더 사용
        conv = ui.Conversation("세라")

        # 도입: 세라가 플레이어를 발견
        conv.narration(
            "......",
            "눈앞에 낯선 여성이 서 있다.",
            "긴 흑발을 묶은 과묵한 인상. 날카로운 눈이 이쪽을 관찰한다."
        )

        conv.say(
            "...일어났군.",
            "......",
            "...기억은 있나?"
        )

        # 첫 번째 선택지: 기억에 대해 (세라는 선택지 적게)
        conv.ask([
            ("기억이 없다", "no_memory"),
            ("여기가 어디야?", "where"),
        ])

        conv.respond("no_memory",
            "......",
            "...그렇군.",
            "...너만 그런 건 아니다."
        )

        conv.respond("where",
            "...저택이다.",
            "...숲 속에 있는.",
            "...밀라가 널 데려왔다."
        )

        # 세라 자기소개
        conv.say(
            "......",
            "...세라다.",
            "...이 저택에서 사냥을 맡고 있다."
        )

        # 두 번째 선택지: 추가 질문
        conv.say("...질문이 있으면 해라.")

        conv.ask([
            ("다른 사람들은?", "others"),
            ("됐어", "done"),
        ])

        conv.respond("others",
            "...밀라와 리나가 있다.",
            "...밀라는 요리를 맡고 있다.",
            "...리나는... 어린 편이다. 채집을 한다.",
            "...셋이서 살고 있다."
        )

        conv.respond("done",
            "...그래."
        )

        # 마무리
        conv.say(
            "...무리하지 마라.",
            "......",
            "...필요한 게 있으면 밀라에게 말해라."
        )

        # 누적형 대화 시작
        yield conv.end()

        # 시간 경과 처리
        morld.set_npc_time_consume(self.instance_id, "stay", 1 * _M)
        morld.set_npc_job(self.instance_id, "stay", 2 * _M)

        # 첫 만남 완료 처리 (관계:세라:진척도 = 1)
        self.mark_first_meet_done(player_id)

    # ========================================
    # 데이트 반응
    # ========================================

    def get_date_accept_text(self):
        """데이트 수락"""
        return f"[{self.name}]\n\"...좋아. 같이 가지.\""

    def get_date_reject_text(self, reason):
        """데이트 거절"""
        return f"[{self.name}]\n\"...{reason}\"\n\"...미안하다.\""

    def get_date_end_text(self):
        """데이트 종료"""
        return f"[{self.name}]\n\"...즐거웠다.\"\n\"...또 가자.\""

    def get_date_action_reaction(self, action_id):
        """데이트 중 애정 표현 반응"""
        reactions = {
            "hold_hands": "세라가 손을 꼭 쥐어준다.",
            "hug": "세라가 조용히 안긴다.\n\"...따뜻하군.\"",
            "kiss": "세라가 살짝 얼굴을 붉힌다.\n\"......\"",
        }
        return reactions.get(action_id)

    def get_date_action_reject(self, action_id):
        """데이트 중 애정 표현 거부 반응"""
        rejects = {
            "hold_hands": f"[{self.name}]\n\"...아직은.\"",
            "hug": f"[{self.name}]\n\"...그건... 아직 이르다.\"",
            "kiss": f"[{self.name}]\n\"...!!\"\n세라가 뒤로 물러선다.",
        }
        return rejects.get(action_id)

    # ========================================
    # 데이트 외 애정 표현 반응
    # ========================================

    def get_casual_action_reaction(self, action_id):
        """데이트 외 애정 표현 반응 - 더 쑥스러운 반응"""
        reactions = {
            "hold_hands": f"[{self.name}]\n\"...갑자기 왜 이래.\"\n세라가 당황하면서도 손을 뿌리치지 않는다.",
            "hug": f"[{self.name}]\n\"...!!\"\n\"...여기서...?\"\n세라가 주변을 두리번거린다.",
            "kiss": f"[{self.name}]\n\"......!!\"\n세라의 얼굴이 새빨갛게 물든다.\n\"...미쳤냐...\"",
        }
        return reactions.get(action_id)

    def get_casual_action_reject(self, action_id):
        """데이트 외 애정 표현 거부 반응"""
        rejects = {
            "hold_hands": f"[{self.name}]\n\"...뭐 하는 거냐.\"\n세라가 손을 뺀다.",
            "hug": f"[{self.name}]\n\"...가까이 오지 마.\"\n세라가 한 발 물러선다.",
            "kiss": f"[{self.name}]\n\"......\"\n세라가 차갑게 노려본다.",
        }
        return rejects.get(action_id)


    # ========================================
    # 임신/모드 후유증 반응
    # ========================================

    def _handle_pregnancy_event(self, player_id, event_key):
        """세라 임신 이벤트 반응"""
        import pregnancy as _preg
        week = _preg.get_pregnancy_week(self.instance_id)

        if event_key == "conception:discovery":
            yield ui.dialog(f"[{self.name}]\n\"...아이가 생겼어.\"\n\"...너 때문이야. ...책임져.\"")
        elif event_key == "conception:unknown_father":
            yield ui.dialog(f"[{self.name}]\n\"...몸이 이상해. ...뭔가 달라.\"\n\"...설마...\"")
        elif event_key == "pregnancy:announcement":
            yield ui.dialog(f"[{self.name}]\n\"...{week}주차야.\"\n\"...어떻게 할 건지... 정해.\"")
        elif event_key == "pregnancy:unknown_father":
            yield ui.dialog(f"[{self.name}]\n\"...{week}주차래.\"\n\"...누구 아이인지는... 모르겠어.\"")

    def _handle_mode_aftermath(self, player_id, event_key):
        """세라 모드 피해 후유증 반응"""
        if event_key == "forced_aftermath":
            yield ui.dialog(f"[{self.name}]\n\"...가까이 오지 마.\"\n세라가 차갑게 노려본다. 눈에 분노와 치욕이 서려 있다.")
        elif event_key == "unconscious_aftermath":
            yield ui.dialog(f"[{self.name}]\n\"...몸이 이상해.\"\n세라가 미간을 찌푸린다. \"...뭔가 있었어...?\"")
        elif event_key == "frozen_aftermath":
            yield ui.dialog(f"[{self.name}]\n\"...시간이 이상하게 흘렀어.\"\n\"...설명해. 지금 당장.\"")

    # ========================================
    # 침대 이벤트
    # ========================================

    def on_bed_awake(self, bed, player_id, slot, affection, region_id, owner_id):
        """
        세라 방 침대 반응 (깨어있을 때)
        - 호감도 무관하게 내쫓지 않음 (눕는 것 자체는 허용)
        - 호감도 낮을 때 만지면 쫓아냄
        """
        success = False
        if affection >= 50:
            yield ui.dialog([
                "[세라]",
                "...뭐해."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog([
                    "세라의 침대에 누웠다.",
                    "세라가 별 말 없이 자리를 내줬다."
                ])
        elif affection >= 20:
            yield ui.dialog([
                "[세라]",
                "......",
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog([
                    "세라의 침대에 누웠다.",
                    "(세라가 아무 말 없이 비켜줬다.)"
                ])
        else:
            yield ui.dialog([
                "[세라]",
                "...마음대로 해.",
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog([
                    "세라의 침대에 누웠다.",
                    "(세라가 무관심하게 고개를 돌렸다.)"
                ])

        if not success:
            return

        # 행동 선택지
        lines = "...\n\n"
        lines += "[url=@ret:breast]가슴 만지기[/url]\n"
        lines += "[url=@ret:butt]엉덩이 만지기[/url]\n"
        lines += "[url=@ret:kiss]키스하기[/url]\n"
        lines += "[url=@ret:hug]안아주기[/url]\n"
        if affection >= 50:
            lines += "[url=@ret:romance]스킨십[/url]\n"
        lines += "[url=@ret:nothing]가만히 있기[/url]"
        choice = yield ui.dialog(lines, autofill="off")

        if choice == "nothing" or not choice:
            return

        if choice == "romance":
            from romance import start_romance
            yield from start_romance(player_id, owner_id)
            return

        if affection >= 50:
            if choice == "breast":
                yield ui.dialog([
                    "손을 뻗어 세라의 가슴에 살짝 닿았다.",
                    "[세라]",
                    "+...!",
                    "+...뭐 하는 거야.",
                    "세라가 고개를 돌렸다.",
                    "+귀끝이 살짝 붉어져 있다."
                ])
            elif choice == "butt":
                yield ui.dialog([
                    "손을 뻗어 세라의 엉덩이에 살짝 닿았다.",
                    "[세라]",
                    "+......!",
                    "+...한 번만 더 하면 죽어.",
                    "세라가 이불을 끌어당기며 등을 돌렸다.",
                    "+...하지만 내쫓지는 않았다."
                ])
            elif choice == "kiss":
                yield ui.dialog([
                    "세라의 얼굴에 가까이 다가갔다.",
                    "[세라]",
                    "+...뭐야.",
                    "세라의 입술에 가볍게 키스했다.",
                    "세라가 눈을 피했다.",
                    "+...하지만 피하지는 않았다.",
                    "+귀끝까지 붉어져 있다."
                ])
            elif choice == "hug":
                yield ui.dialog([
                    "세라를 조용히 안아줬다.",
                    "[세라]",
                    "+......",
                    "+...뭐냐.",
                    "세라가 뻣뻣하게 있다가...",
                    "+살짝 몸을 기댔다."
                ])
        elif affection >= 20:
            if choice == "breast":
                yield ui.dialog([
                    "손을 뻗어 세라의 가슴에 닿으려는 순간—",
                    "[세라]",
                    "+...건드리지 마.",
                    "세라의 차가운 눈빛에 손을 거뒀다."
                ])
            elif choice == "butt":
                yield ui.dialog([
                    "손을 뻗어 세라의 엉덩이에 닿으려는 순간—",
                    "[세라]",
                    "+...손 치워.",
                    "세라가 날카롭게 경고했다."
                ])
            elif choice == "kiss":
                yield ui.dialog([
                    "세라의 얼굴에 가까이 다가갔다.",
                    "[세라]",
                    "+...가까이 오지 마.",
                    "세라가 차갑게 고개를 돌렸다."
                ])
            elif choice == "hug":
                yield ui.dialog([
                    "세라를 안으려 했지만—",
                    "[세라]",
                    "+......만지지 마.",
                    "세라가 몸을 비켜 거리를 뒀다."
                ])
        else:
            # 호감도 낮으면 강제 퇴출
            action_text = ""
            if choice == "breast":
                action_text = "손을 뻗어 세라의 가슴에 닿으려는 순간—"
            elif choice == "butt":
                action_text = "손을 뻗어 세라의 엉덩이에 닿으려는 순간—"
            elif choice == "kiss":
                action_text = "세라의 얼굴에 가까이 다가가려는 순간—"
            elif choice == "hug":
                action_text = "세라를 안으려는 순간—"
            yield ui.dialog([
                action_text,
                "[세라]",
                "+...나가.",
                "세라가 조용히, 하지만 단호하게 말했다.",
                "+눈빛이 얼음장같다."
            ])
            # 2층 복도로 강제 이동 (세라 방은 2층 → 2층 복도 location 14)
            morld.set_unit_location(player_id, region_id, 14, 60)
            yield ui.dialog("세라에게 쫓겨나 복도로 나왔다...")

    def on_bed_sleeping(self, bed, player_id, slot, affection, owner_id):
        """세라가 자고 있을 때 - 호감도별 묘사 + 행동 선택"""
        success = False
        if affection >= 50:
            yield ui.dialog([
                "세라가 조용히 잠들어 있다.",
                "편안한 숨소리가 들린다."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog(["조심스럽게 옆에 누웠다."])
        elif affection >= 20:
            yield ui.dialog([
                "세라가 잠들어 있다.",
                "...잠꼬대를 하진 않는다."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog(["살짝 옆에 누웠다."])
        else:
            yield ui.dialog([
                "세라가 잠들어 있다.",
                "...남의 침대에 눕는 건 좀 그렇지만."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog(["슬며시 옆자리에 누웠다."])

        if not success:
            return

        # 수면 중 행동 선택지
        choice = yield ui.dialog(
            "...\n\n"
            "[url=@ret:breast]가슴 만지기[/url]\n"
            "[url=@ret:butt]엉덩이 만지기[/url]\n"
            "[url=@ret:kiss]키스하기[/url]\n"
            "[url=@ret:nothing]가만히 있기[/url]",
            autofill="off"
        )

        if choice == "nothing" or not choice:
            return

        if choice == "breast":
            if affection >= 50:
                yield ui.dialog([
                    "손을 뻗어 세라의 가슴에 살짝 닿았다.",
                    "+...부드럽다.",
                    "세라가 잠결에 가볍게 몸을 뒤척였다.",
                    "+\"...음...\"",
                    "+...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "손을 뻗어 세라의 가슴에 살짝 닿았다.",
                    "+...부드럽다.",
                    "세라가 살짝 미간을 찌푸렸다.",
                    "+...위험하다. 그만두는 게 좋겠다."
                ])
        elif choice == "butt":
            if affection >= 50:
                yield ui.dialog([
                    "손을 뻗어 세라의 엉덩이에 살짝 닿았다.",
                    "+...탄력이 있다.",
                    "세라가 살짝 몸을 움츠렸다.",
                    "+\"...ん...\"",
                    "+...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "손을 뻗어 세라의 엉덩이에 살짝 닿았다.",
                    "+...탄력이 있다.",
                    "세라가 잠결에 손을 쳐냈다.",
                    "+...심장이 쿵 내려앉았다."
                ])
        elif choice == "kiss":
            if affection >= 50:
                yield ui.dialog([
                    "세라의 얼굴에 가까이 다가갔다.",
                    "잠든 세라의 입술에 살짝 키스했다.",
                    "+세라의 입술이 부드럽게 떨렸다.",
                    "\"...음...\"",
                    "+세라가 잠결에 살짝 미소 짓는 것 같다.",
                    "+...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "세라의 얼굴에 가까이 다가갔다.",
                    "잠든 세라의 이마에 가볍게 키스했다.",
                    "+세라의 눈꺼풀이 파르르 떨렸다.",
                    "...깨기 전에 그만두는 게 좋겠다."
                ])


# ========================================
# AI Agent
# ========================================

@register_agent_class("sera")
class SeraAgent(BaseAgent):
    """
    세라 AI - 저택 리더 + 사냥 + 경비 담당

    특징:
    - 과묵하고 듬직함
    - 저택 생존자들의 리더 (밀라, 리나가 신뢰함)
    - 사냥과 저택 순찰을 담당
    - 플레이어에게 무관심하지만 위험시 보호
    """

    SCHEDULES = {
        "평일": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 300 * _M, "end": 330 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 8, "x": 120, "start": 330 * _M, "end": 360 * _M, "activity": "준비"},
            {"name": "아침순찰", "region_id": 0, "location_id": 12, "x": 300, "start": 360 * _M, "end": 420 * _M, "activity": "순찰"},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "오전활동", "start": 540 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
                {"activity": "낚시", "condition": "need_fish"},
                {"activity": "벌목", "condition": "need_logs"},
                {"activity": "순찰", "condition": None},
            ]},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "오후활동", "start": 840 * _M, "end": 1020 * _M, "dynamic": True, "candidates": [
                {"activity": "벌목", "condition": "need_logs"},
                {"activity": "낚시", "condition": "need_fish"},
                {"activity": "순찰", "condition": None},
            ]},
            {"name": "저녁순찰", "region_id": 0, "location_id": 20, "x": 900, "start": 1020 * _M, "end": 1080 * _M, "activity": "순찰"},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "장비정비", "region_id": 0, "location_id": 8, "x": 90, "start": 1200 * _M, "end": 1260 * _M, "activity": "정비"},
            {"name": "저택 소등", "start": 1260 * _M, "end": 1290 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 8, "x": 90, "start": 1290 * _M, "end": 300 * _M, "activity": "수면"},
        ],
        "주말": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 300 * _M, "end": 330 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 8, "x": 120, "start": 330 * _M, "end": 360 * _M, "activity": "준비"},
            {"name": "아침순찰", "region_id": 0, "location_id": 12, "x": 300, "start": 360 * _M, "end": 420 * _M, "activity": "순찰"},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "독서", "start": 540 * _M, "end": 720 * _M, "activity": "독서"},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "순찰", "region_id": 0, "location_id": 12, "x": 300, "start": 840 * _M, "end": 960 * _M, "activity": "순찰"},
            {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 960 * _M, "end": 1080 * _M, "activity": "휴식"},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "저택 소등", "start": 1260 * _M, "end": 1290 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 8, "x": 90, "start": 1290 * _M, "end": 300 * _M, "activity": "수면"},
        ],
    }

    owner_unique_id = "sera"

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self._memory["current_day_type"] = None
        import survival
        survival.register_npc(unit_id)
        import temperature
        temperature.register_character(unit_id)
        import needs
        needs.register_character(unit_id)
        import pregnancy
        pregnancy.register_character(unit_id)

    def think(self):
        """주말/평일 감지 → 스케줄 전환"""
        time_info = morld.get_time_info()
        day = time_info.get("day", 0)
        day_type = "주말" if day % 7 >= 5 else "평일"
        if self._memory["current_day_type"] != day_type:
            self._memory["current_day_type"] = day_type
            self.set_base_schedule(self.SCHEDULES[day_type])
        return super().think()


# ========================================
# 캐릭터 개인 퀘스트 (CHARACTER_QUESTS)
# ========================================
# 세라 관련 퀘스트는 캐릭터 파일에서 직접 정의

Sera.CHARACTER_QUESTS = [
    # ========================================
    # 낚시 퀘스트: 2층 창고에서 낚시 → 물고기 전달
    # ========================================
    {
        "unique_id": "sera_fishing",
        "name": "저녁 식사 준비",
        "description": "세라가 저녁 재료로 쓸 물고기를 잡아달라고 했다.",
        "category": "personal",

        "prerequisites": ["sub_meet_sera"],
        "giver": "sera",
        "reporter": "sera",

        "conditions": [
            {"type": "deliver", "item": "fish", "target": "sera", "count": 2},
        ],

        "rewards": [
            {"type": "prop", "target": "player", "prop": "관계:세라:호감", "value": 10},
            {"type": "item", "item": "smoked_fish", "count": 1},
        ],

        "dialogs": {
            "offer": [
                "[세라]",
                "......",
                "...저녁 재료가 부족해.",
                "...물고기 2마리만 잡아올 수 있나?",
                "...2층 창고에 낚싯대가 있다.",
            ],
            "accept": [
                "[세라]",
                "...고맙다.",
                "...연못에서 낚으면 된다.",
            ],
            "decline": [
                "[세라]",
                "......",
                "...그래.",
            ],
            "progress": [
                "[세라]",
                "...물고기는?",
                "...연못에 있을 거다.",
            ],
            "complete": [
                "[세라]",
                "...잘 잡았군.",
                "...고맙다.",
                "(세라에게 물고기 2마리를 건넸다)",
                "(세라가 훈제 물고기를 건네준다)",
                "...맛있게 먹어.",
            ],
        },
    },

    # ========================================
    # 사냥 동행 퀘스트: 세라와 함께 숲 깊은 곳까지 사냥
    # ========================================
    {
        "unique_id": "sera_hunting",
        "name": "사냥 동행",
        "description": "세라와 함께 숲으로 사냥을 나가자.",
        "category": "personal",

        "prerequisites": ["sera_fishing"],  # 낚시 퀘스트 완료 후
        "giver": "sera",
        "reporter": "sera",

        "conditions": [
            {"type": "all", "conditions": [
                {"type": "meet", "target": "sera"},
                {"type": "reach", "region_id": 0, "location_id": 24},  # 숲 깊은 곳
            ]},
        ],

        "rewards": [
            {"type": "prop", "target": "player", "prop": "관계:세라:호감", "value": 15},
            {"type": "prop", "target": "player", "prop": "관계:세라:신뢰", "value": 1},
            {"type": "item", "item": "wolf_pelt", "count": 1},
        ],

        "dialogs": {
            "offer": [
                "[세라]",
                "......",
                "...같이 사냥 갈래?",
                "...숲 깊은 곳에 좋은 사냥터가 있어.",
                "...위험하니까... 뒤처지지 마.",
            ],
            "accept": [
                "[세라]",
                "...따라와.",
                "(세라가 활을 들고 앞장선다)",
            ],
            "decline": [
                "[세라]",
                "......",
                "...그래. 다음에.",
            ],
            "progress": [
                "[세라]",
                "...아직 멀었어.",
                "...서둘러.",
            ],
            "complete": [
                "[세라]",
                "......",
                "(세라가 늑대를 쓰러뜨렸다)",
                "...잘했어.",
                "(세라가 희미하게 미소 짓는다)",
                "...이건 네 몫이다.",
                "(늑대 가죽을 받았다)",
            ],
        },
    },

    # ========================================
    # 세라의 신뢰 퀘스트: 호감도 70 이상 달성
    # ========================================
    {
        "unique_id": "sera_trust",
        "name": "세라의 신뢰",
        "description": "세라와 더 친해지자.",
        "category": "personal",

        "prerequisites": ["sera_hunting"],
        "giver": None,  # 자동 해금
        "reporter": "sera",

        "conditions": [
            {"type": "prop", "target": "player", "prop": "관계:세라:호감", "min_value": 70},
        ],

        "rewards": [
            {"type": "item", "item": "sera_pendant", "count": 1},
            {"type": "prop", "target": "player", "prop": "관계:세라:신뢰", "value": 1},
        ],

        "dialogs": {
            "complete": [
                "[세라]",
                "......",
                "...너.",
                "......",
                "...이거.",
                "(세라가 목걸이를 건넨다)",
                "...어머니가 주신 거야.",
                "...너한테 주고 싶었어.",
                "......",
                "...잃어버리지 마.",
            ],
        },
    },
]
