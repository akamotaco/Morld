# assets/characters/mila.py - 밀라 캐릭터 Asset
#
# ============================================================
# 캐릭터 설정
# ============================================================
# 이름: 밀라 (Mila)
# 성별: 여성
# 나이: 불명 (20대 중반으로 추정, 기억 없음)
#
# 외모:
#   - 갈색 중간머리, 갈색 눈
#   - 부드럽고 따뜻한 인상
#   - 포근한 분위기, 어머니 같은 느낌
#
# 성격:
#   - 다정함: 누구에게나 친절하고 배려심이 깊음
#   - 걱정많음: 다른 사람들의 안위를 늘 걱정
#   - 헌신적: 남을 돌보는 것에서 보람을 느낌
#   - 내면: 자신의 감정은 숨기는 경향, 속으로 외로울 때도
#
# 좋아하는 것:
#   - 요리, 특히 다른 사람이 맛있게 먹는 모습
#   - 깨끗하게 정돈된 집
#   - 따뜻한 차, 평화로운 시간
#   - 동료들이 건강하고 행복한 것
#
# 싫어하는 것:
#   - 다툼, 갈등 상황
#   - 누군가 다치거나 아픈 것
#   - 불안정하고 위험한 상황
#   - 낭비, 지저분한 것
#
# 취미:
#   - 요리 (매일 식사 준비)
#   - 청소, 정리 (집안 살림 전반)
#   - 차 마시며 휴식
#   - 다른 사람 돌보기
#
# 과거사:
#   - 기억 없음. 저택에서 가장 먼저 눈을 떴음
#   - 숲에서 쓰러져 있던 세라를 발견하여 데려옴
#   - 이후 리나도 합류하여 함께 지내게 됨
#   - 과거가 없어도 지금 함께하는 것이 소중하다고 생각
#
# (복선) 어두운 과거 암시:
#   - 방에 개인 물건이 거의 없음 - 과거를 의도적으로 지우려는 듯
#   - 따뜻한 성격과 달리 방은 건조하고 비어 있음
#   - 가끔 혼자 있을 때 멍하니 창밖을 바라봄
#   - "혼자 있는 시간이... 싫지 않아요." - 과거의 고독을 암시
#   - 다른 사람을 돌보는 것에 집착하는 이유가 있을 수 있음
#
# 현재 배경:
#   - 저택 그룹의 살림 담당
#   - 요리, 청소, 정리 등 가사 전반을 책임
#   - 그룹의 정서적 기둥 역할
#   - 세라를 깊이 신뢰하고 의지함
#
# 말투 특징:
#   - 존댓말 기본 (예의 바름)
#   - "~요", "~세요" 등 부드러운 어미
#   - 걱정하는 말투가 많음 ("괜찮으세요?", "조심하세요")
#   - 감사와 배려의 표현이 잦음
#
# 관계:
#   - 세라: 자신이 구한 사람, 깊이 신뢰하고 의지함
#   - 리나: 귀여운 동생 같은 존재, 잘 챙겨줌
#   - 플레이어: 처음엔 걱정, 점차 따뜻하게 대함
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


class Mila(Character):
    unique_id = "mila"
    name = "밀라"
    type = "female"
    sexual_orientation = "heterosexual"
    props = {
        "성별": "female", "성적지향": "heterosexual",
        "외모:갈색머리": 1, "외모:중간머리": 1, "외모:갈색눈": 1,
        "성격:다정함": 1, "성격:걱정많음": 1,
        "관계:세라:신뢰": 1,
        "나이": 25,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 6,
        "can:lie_down": 1,
        "can:sleep": 1,
        "can:bath": 1,
        "can:toggle_switch": 1,
        "생존:체력": 100, "생존:최대체력": 100,
        "생존:포만감": 80, "생존:최대포만감": 100,
        "처녀:구강": 1,
        "처녀:음부": 1,
        "처녀:항문": 1,
        "근력": 4, "체력": 5,
        "체격": 2, "가슴:크기": 3,
    }
    actions = [
        "call:talk:대화",
        "call:errand:심부름#",         # 퀘스트 제안 가능 시만 표시
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
        "요리 방법",
        "살림 팁",
    ]

    # ========================================
    # 대화 규칙 (주제별 조건 → 대사 또는 메서드명)
    # ========================================
    TALK_RULES = {
        "잡담": [
            # 특수 상황 (최우선)
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # Activity 기반
            ({"activity": "요리"}, {"pages": ["(요리 중이다)", "잠시만요, 지금 손을 뗄 수가 없어요!"]}),
            ({"activity": "식사"}, {"pages": ["맛있게 드셨으면 좋겠어요.", "더 필요하시면 말씀해 주세요!"]}),
            ({"activity": "설거지"}, {"pages": ["설거지 중이에요.", "금방 끝날 거예요~"]}),
            ({"activity": "청소"}, {"pages": ["청소 중이에요~", "깨끗한 집이 좋잖아요!"]}),
            ({"activity": "정리"}, {"pages": ["지금 정리 중이에요.", "조금만 기다려 주세요."]}),
            ({"activity": "휴식"}, {"pages": ["후~ 잠시 쉬고 있어요.", "오늘 뭐 드시고 싶은 거 있으세요?"]}),
            ({"activity": "정원"}, {"pages": ["정원이 점점 예뻐지고 있어요~", "이 꽃, 예쁘지 않나요?"]}),
            ({"activity": "목욕"}, {"pages": ["(목욕 중이다)", "저, 잠시만요...!"]}),
            ({"activity": "준비"}, {"pages": ["지금 준비 중이에요~", "조금만 기다려 주세요!"]}),

            # 호감도 기반 (진척도 증가 로직 포함)
            ({"호감": 70}, "_talk_friendly_high"),
            ({"호감": 50}, "_talk_friendly_mid"),

            # mood 기반
            ({"mood": "기쁨"}, {"pages": ["안녕하세요~", "오늘 기분이 좋아요!"]}),
            ({"mood": "슬픔"}, {"pages": ["...안녕하세요.", "...아, 아무것도 아니에요."]}),

            # 기본값
            ({}, {"pages": ["안녕하세요!", "뭔가 필요하신 게 있으세요?"]}),
        ],

        "본인에 대해": [
            # 특수 상황
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 진척도별 사적인 대화 (플래그로 일회성 체크)
            ({"호감": 70, "진척도": 3}, "_talk_progress_3"),
            ({"호감": 60, "진척도": 2}, "_talk_progress_2"),
            ({"호감": 50, "진척도": 1}, "_talk_progress_1"),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "저요?",
                "음... 저는 여기서 요리랑 살림을 맡고 있어요.",
                "다들 맛있게 먹어주시면 그게 제일 행복해요.",
                "...아, 부끄러워라.",
            ]}),
            ({"호감": 50}, {"pages": [
                "밀라예요!",
                "이 저택에서 요리랑 청소를 하고 있어요.",
                "필요한 게 있으시면 말씀해 주세요~",
            ]}),
            ({"호감": 30}, {"pages": [
                "제 이름은 밀라예요.",
                "여기서 살림을 맡고 있어요.",
            ]}),

            # 기본값
            ({}, {"pages": ["저는... 그냥 여기서 일하고 있어요.", "더 알고 싶으시면... 나중에요."]}),
        ],

        "요리 방법": [
            # 특수 상황
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "요리에 관심 있으세요?",
                "기본은 재료를 아끼지 않는 거예요.",
                "그리고 먹는 사람을 생각하면서 만들면 더 맛있어져요.",
                "불 조절이 중요하고요, 간은 조금씩 맞춰가세요.",
                "원하시면 같이 해볼까요?",
            ]}),
            ({"호감": 50}, {"pages": [
                "요리요?",
                "스튜는 재료를 푹 끓이면 돼요. 시간이 맛을 내죠.",
                "구이는 겉이 타지 않게 불 조절이 중요해요.",
                "기본만 알면 누구나 할 수 있어요!",
            ]}),
            ({"호감": 30}, {"pages": [
                "요리... 배우고 싶으세요?",
                "일단 불 쓰는 법부터 익히세요.",
                "위험하니까요.",
            ]}),

            # 기본값
            ({}, {"pages": ["요리요?", "음... 나중에 시간 되면 알려드릴게요."]}),
        ],

        "살림 팁": [
            # 특수 상황
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "살림 팁이요?",
                "청소는 매일 조금씩 하는 게 좋아요. 한꺼번에 하려면 힘들거든요.",
                "환기도 중요해요. 공기가 탁하면 기분도 안 좋아지잖아요.",
                "그리고 물건은 제자리에! 찾기 쉬워요.",
                "작은 것부터 정리하면 마음도 편해져요.",
            ]}),
            ({"호감": 50}, {"pages": [
                "살림이요?",
                "먼지는 위에서 아래로 털어야 해요.",
                "빨래는 햇볕에 말리면 냄새도 없어지고 좋아요.",
                "기본만 지키면 어렵지 않아요!",
            ]}),
            ({"호감": 30}, {"pages": [
                "살림 팁요?",
                "음... 일단 정리 정돈부터 해보세요.",
            ]}),

            # 기본값
            ({}, {"pages": ["살림이요?", "...관심이 있으시구나.", "나중에 천천히 알려드릴게요."]}),
        ],
    }

    # ========================================
    # Describe 규칙 (장소에서 보이는 묘사)
    # ========================================
    DESCRIBE_RULES = build_describe_rules(
        "gentle",
        traveling=[
            ({"is_traveling": True, "activity": "요리"}, "{name}가 부엌으로 향하고 있다."),
            ({"is_traveling": True, "activity": "청소"}, "{name}가 청소를 하러 이동 중이다."),
            ({"is_traveling": True, "activity": "정원"}, "{name}가 정원으로 향하고 있다."),
            ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),
        ],
        activities=[
            ("요리", "{name}가 분주하게 요리하고 있다."),
            ("청소", "{name}가 열심히 청소하고 있다."),
            ("정원", "{name}가 정원을 가꾸고 있다."),
            ("식사", "{name}가 다른 사람들이 먹는 모습을 흐뭇하게 바라본다."),
            ("수면", "{name}가 포근하게 잠들어 있다."),
            ("휴식", "{name}가 따뜻한 차를 마시고 있다."),
            ("설거지", "{name}가 설거지를 하고 있다."),
            ("정리", "{name}가 정리 중이다."),
            ("목욕", "{name}가 목욕 중이다."),
        ],
        locations=[
            ({"location": (0, 2)}, "{name}가 요리에 열중하고 있다."),
            ({"location": (0, 3)}, "{name}가 식탁을 정리하고 있다."),
        ],
        default_text="{name}가 다정한 눈으로 주변을 살핀다.",
    )

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = build_focus_rules(
        "gentle",
        activities=[
            ("요리", "앞치마를 두르고 열심히 요리하고 있다."),
            ("청소", "걸레를 들고 구석구석 닦고 있다."),
            ("식사", "다른 사람들이 맛있게 먹는지 살피고 있다."),
            ("수면", "평화롭게 잠들어 있다."),
            ("설거지", "정성스럽게 설거지를 하고 있다."),
            ("휴식", "따뜻한 차를 마시며 여유를 즐기고 있다."),
            ("정원", "꽃에 물을 주며 환하게 웃고 있다."),
            ("정리", "부엌을 말끔하게 정리하고 있다."),
            ("준비", "머리를 단정히 빗고 있다."),
        ],
        default_text="부드러운 갈색 머리의 다정한 여성. 따뜻한 갈색 눈이 편안함을 준다.",
    )

    # ========================================
    # NPC 주도 설정 (밀라: 저돌적/적극적)
    # ========================================
    self_comfort_threshold = 70       # 감정적/민감
    self_comfort_max_length = 150     # 침실/욕실/화장실만 (length=150)

    INITIATIVE_CONFIG = {
        "arousal_threshold": 50,      # 성욕 임계값 (세라보다 낮음 - 더 적극적)
        "affection_threshold": 40,    # 호감도 임계값 (세라보다 낮음)
        "cooldown_millis": 360 * _M,   # 쿨다운 6시간 (세라보다 짧음)
    }

    # NPC 주도 시 허용 액션 필터 (캐릭터별)
    # 형식: [(조건dict, [허용_액션_리스트]), ...]
    # 밀라는 저돌적이므로 더 낮은 애정에서도 다양한 액션 허용
    INITIATIVE_ACTION_FILTERS = [
        ({"호감": 85}, ["hug", "deep_kiss", "breast_touch", "genital_touch", "clit_rub", "penis_touch", "penis_rub"]),
        ({"호감": 70}, ["hug", "deep_kiss", "breast_touch", "genital_touch", "penis_touch"]),
        ({"호감": 60}, ["hug", "deep_kiss", "breast_touch"]),  # 세라보다 낮은 조건
        ({"호감": 30}, ["hug", "deep_kiss"]),  # 세라보다 낮은 조건
        ({}, ["hug"]),  # 기본: 포옹
    ]

    # NPC 주도 중 반응 텍스트
    INITIATIVE_REACTIONS = {
        "start": [
            ({"성욕": 70}, ["...보고 싶었어요...", "...가만히 있어줘요..."]),
            ({}, ["...잠깐만요...", "...가까이 와도 될까요...?"]),
        ],
        "during_hug": [
            ({"성욕": 50}, ["밀라가 숨을 거칠게 몰아쉬며 안아온다."]),
            ({}, ["밀라가 따뜻하게 안아온다.", "밀라의 심장 소리가 느껴진다."]),
        ],
        "during_deep_kiss": [
            ({"성욕": 60}, ["밀라가 거친 숨을 몰아쉬며 키스를 이어간다."]),
            ({}, ["밀라가 부드럽게 입술을 맞대고 있다."]),
        ],
        "during_breast_touch": [
            ({}, ["밀라가 얼굴을 붉히며 가만히 있다."]),
        ],
        "during_genital_touch": [
            ({"성욕": 80}, ["밀라가 부드럽게 당신을 어루만지고 있다.", "밀라가 달콤한 신음을 흘린다."]),
            ({}, ["밀라가 조심스럽게 당신의 아래를 만지고 있다."]),
        ],
        "during_clit_rub": [
            ({"성욕": 90}, ["밀라의 손길이 점점 대담해지고 있다.", "밀라가 당신의 반응에 미소짓고 있다."]),
            ({}, ["밀라가 수줍게 당신을 자극하고 있다."]),
        ],
        "escape_fail": [
            ({}, ["...가지 마세요...", "...조금만 더요..."]),
        ],
        "satisfied": [
            ({"호감": 50}, ["...사랑해요...", "...행복해요..."]),
            ({}, ["...고마워요...", "...기분이 좋아요..."]),
        ],
    }

    # ========================================
    # 은신 성공 반응 (밀라: 부끄러움에 애정 감소, 사랑 증가)
    # ========================================
    # 밀라는 다정하지만 들킬 뻔한 상황에 부끄러워하는 타입
    STEALTH_REACTIONS = {
        "text": [
            ({"성욕": 50}, ["...어떡해요... 심장이 너무 빨리 뛰어요...", "...(얼굴이 빨개진다)"]),
            ({"호감": 40}, ["...무서웠어요...", "...다행이에요..."]),
            ({}, ["...휴... 다행이에요...", "...(가슴을 쓸어내린다)"]),
        ],
        "effects": {},  # 기존: 호감-1/애정+1 → 통합으로 상쇄
    }

    EQUIP_CHANGE_REACTIONS = {
        "equip": "밀라가 걱정스러운 눈으로 무기를 바라본다.",
        "unequip": "밀라가 안심한 듯 미소를 짓는다.",
    }

    FRIENDLY_TALK_CONFIG = {
        "high": {
            "dialog": [
                "오셨군요~",
                "...괜찮으세요? 뭔가 필요하신 거 있으세요?",
            ],
            "progress_cap": 3,
        },
        "mid": {
            "dialog": [
                "안녕하세요!",
                "...뭐 드시고 싶은 거 있으세요?",
            ],
            "progress_cap": 1,
        },
    }

    PROGRESS_DIALOGS = {
        1: {
            "fallback": ["오셨군요~", "뭔가 필요하신 게 있으세요?"],
            "dialog": [
                "저요?",
                "저는 밀라예요. 여기서 살림을 맡고 있어요.",
                "요리, 청소, 빨래... 뭐, 그런 것들이요.",
                "세라랑 리나도 여기 살고 있어요.",
                "세라는... 좀 무뚝뚝하지만, 마음은 따뜻한 아이예요.",
                "리나는 활발하고 귀여운 동생이에요.",
                "...다들 소중한 가족이에요.",
            ],
        },
        2: {
            "fallback": ["오셨군요~", "오늘은 뭐 해드릴까요?"],
            "dialog": [
                "제가 좋아하는 거요?",
                "음... 요리하는 걸 좋아해요.",
                "누군가가 제가 만든 음식을 맛있게 먹을 때...",
                "그 표정을 보면 정말 행복해져요.",
                "특히 새로운 레시피가 성공했을 때!",
                "아, 그리고... 조용히 차 마시는 시간도 좋아요.",
                "혼자 있는 시간이... 싫지 않아요.",
                "...가끔은요.",
            ],
        },
        3: {
            "fallback": ["오셨군요~", "...그냥 보고 싶었어요."],
            "dialog": [
                "예전 일이요...?",
                "...기억나는 게 많지 않아요.",
                "어느 날 눈을 떴을 때, 이미 이 저택에 있었어요.",
                "...혼자였어요.",
                "그래서... 누군가를 돌보는 게 좋았나 봐요.",
                "세라를 발견했을 때, 정말 기뻤어요.",
                "리나도... 그 애도 혼자였거든요.",
                "...다들 기억이 없대요.",
                "하지만 괜찮아요.",
                "지금 이렇게... 함께 있으니까요.",
            ],
        },
    }

    ROOM_PRIVACY_CONFIG = {
        "수면": {
            "threshold": 50,
            "high": {
                "dialog": ["[밀라]", "어... 여기 있었어?", "...괜찮아, 그냥 잘게."],
            },
            "low": {
                "dialog": ["[밀라]", "...자려고 하는데, 나가줄 수 있어?"],
                "teleport": 1,
                "after": "밀라의 방에서 나왔다.",
            },
        },
        "목욕": {
            "threshold": 70,
            "high": {
                "dialog": ["[밀라]", "어엇!? 왜, 왜 여기 있어!?", "...나, 나가줘! 지금 당장!"],
                "teleport": 1,
                "after": "욕실에서 나왔다.",
            },
            "low": {
                "dialog": ["[밀라]", "......!!", "밀라가 얼굴이 새빨개져서 소리를 질렀다."],
                "teleport": 1,
                "after": "욕실에서 쫓겨났다.",
            },
        },
        "화장실": {
            "threshold": 0,
            "low": {
                "dialog": ["[밀라]", "잠깐! 나가 주세요!"],
                "teleport": 1,
                "after": "화장실에서 쫓겨났다.",
            },
        },
    }

    # 흥분도 단계별 소음 강도 — 조용 → 중간 정도
    ROMANCE_SOUND_PROFILE = {"levels": [5, 15, 25], "ecstasy": 40}

    # 애정행위 발각 시 반응 (목격자로서) — 밀라: 조용히 상처받음
    ROMANCE_DISCOVERY_REACTIONS = {
        "default": {
            "text": ["...아...", "...그렇구나...", "...(조용히 돌아선다)"],
            "exposed_text": ["...아...!", "...(황급히 눈을 가린다)", "...죄, 죄송해요...!"],
            "effects": {"호감": -3, "반발": 3},
        },
        "sera": {
            "text": ["...세라랑...?", "...그래요... 그럴 수도 있죠..."],
            "exposed_text": ["...세라가... 벗은 채로...?", "...(입을 가린다)"],
            "effects": {"호감": -4, "반발": 4},
        },
        "lina": {
            "text": ["...리나랑...?", "...아... 네...", "...(눈을 내리깐다)"],
            "exposed_text": ["...리나가...!", "...(눈물이 고인다)", "...이건 너무..."],
            "effects": {"호감": -5, "반발": 5},
        },
    }

    # ========================================
    # 선물 선호도
    # ========================================
    GIFT_PREFERENCES = {
        "liked_categories": ["food_ingredient", "flower"],
        "favorite_items": ["food_fruit_salad", "food_mushroom_stew"],
        "disliked_categories": ["trinket"],
        "favorite_foods": ["food_fruit_salad", "food_apple_jam"],
    }

    # ========================================
    # 성적 선호 (체위/부위)
    # ========================================
    SEXUAL_PREFERENCES = {
        "preferred_positions": ["missionary", "face_sitting"],
        "preferred_parts": ["B", "V"],
    }

    # ========================================
    # 반응 생성기 프로필 (archetype="gentle": 다정형)
    REACTION_PROFILE = {
        "name": "밀라",
        "archetype": "gentle",
        "speech_level": "formal",
        "speech_shifts": {"arousal": {"extreme": "casual"}},
        "vars": {},
        "line_overrides": {},
        "overrides": {},
    }

    # ========================================
    # 스킨십 반응 (action:timing → 조건부 대사 리스트)
    # 형식: (조건dict, [대사들]) - 조건 충족 시 대사들이 후보에 추가
    # ========================================
    ROMANCE_REACTIONS = {
        # ── 특수 조건 반응 ──
        "french_kiss:start": [
            ({"미경험:기억:첫키스": 1}, ["...!!! 처, 처음이에요...!", "...(얼굴이 새빨개진다)", "...부끄러워요... 하지만 행복해요..."]),
            ({"경험:키스": 5}, ["...으응...♡ 키스 좋아해요...", "...(눈을 감으며 다가온다)♡"]),
            ({}, ["...으응...♡", "...(살짝 입술을 맞댄다)"]),
        ],
        "deep_kiss:start": [
            ({"성욕": 40}, ["...하앙... 더... 해주세요...♡"]),
            ({"호감": 30}, ["...사랑해요... 으응...♡"]),
            ({}, ["...으응...♡", "...키스... 해주세요...", "...눈 감을게요..."]),
        ],
        "nipple_lick:start": [
            ({"상태:수유": 1}, ["응...? 나오고 있어...?", "핥으면... 나와요... 괜찮아요...♡"]),
        ],
        "nipple_suck:start": [
            ({"상태:수유": 1}, ["...빨면 나와요... 괜찮아요?", "응... 모유... 마셔도 돼요...♡"]),
        ],

        # ── :during ──
        "nipple_suck:during": [
            ({"상태:수유": 1}, ["밀라가 당신의 머리를 부드럽게 감싸며 젖을 먹이고 있다.", "계속 나오네요... 많이 마셔요...♡"]),
            ({}, ["밀라가 당신의 머리를 어루만지며 참고 있다.", "으응... 계속 빨면... 이상해요..."]),
        ],
        "vaginal_penetration:during": [
            ({"크기통증": 1}, ["밀라가 이를 물며 참고 있다. \"...괜찮아... 조금만...\"", "\"아... 좀 아프지만... 괜찮아...\""]),
            ({"성욕": 90}, ["밀라가 당신을 꽉 끌어안으며 달콤하게 신음하고 있다.", "밀라의 안이 뜨겁게 감싸고 있다."]),
            ({}, ["밀라가 눈물을 글썽이며 견디고 있다.", "밀라가 당신의 등을 꽉 잡고 있다."]),
        ],
        "anal_penetration:during": [
            ({"크기통증": 1}, ["밀라가 움찔한다. \"...뒤는 좀... 무리일 수도...\""]),
            ({"성욕": 90}, ["밀라가 눈물을 흘리며 떨고 있다.", "밀라가 당신의 손을 꽉 잡으며 견디고 있다."]),
            ({}, ["밀라가 울먹이며 참고 있다.", "밀라가 시트를 움켜쥐고 있다."]),
        ],

        # ── 사정 참기 ──
        "hold_back_success:start": [
            ({}, ["밀라가 부드럽게 미소 짓는다. \"잘 참았어...\"", "\"괜찮아... 천천히.\" 밀라가 머리를 쓰다듬는다."]),
        ],
        "hold_back_failure:start": [
            ({}, ["밀라가 눈을 크게 뜬다. \"...안에...?\"", "\"아... 안에 나왔어...\" 밀라가 놀라면서도 받아들인다."]),
        ],

        # ── 내부 사정 (특수 조건) ──
        "ejaculation_internal_음부:start": [
            ({"욕망": 80, "경험:질내사정": 5}, ["안에... 가득... 따뜻해요...♡", "...아이가 생겨도... 괜찮아요..."]),
            ({"경험:질내사정": 3}, ["또 안에... 쏟았어요...", "...이제... 익숙해졌어요..."]),
        ],

        # ── 절정 (특수 조건) ──
        "ecstasy:start": [
            ({"미경험:기억:첫절정": 1}, ["...!! 뭐, 뭐예요 이거...?!", "...몸이... 이상해요...!", "...(처음 느끼는 감각에 눈물이 글썽인다)"]),
            ({"경험:절정:V": 10}, ["...또... 가요...♡♡", "...(익숙한 듯 몸을 맡기며) ...하앙...♡"]),
        ],

        # ── 정액 삼킴 (3인칭 서술) ──
        "swallow_semen_spit:start": [
            ({}, ["밀라가 조심스럽게 뱉어낸다. \"...미안해, 아직은...\"", "\"...삼킬 수가 없어...\" 밀라가 고개를 돌린다."]),
        ],
        "swallow_semen_drip:start": [
            ({}, ["밀라의 입에서 정액이 흘러나온다. \"...으...\"", "\"...미안... 아직 익숙하지 않아서...\""]),
        ],
        "swallow_semen_vomit:start": [
            ({}, ["밀라가 구역질을 하며 눈물을 글썽인다. \"...으... 미안...\"", "\"...으엑... 미안해...\" 밀라가 힘들어한다."]),
        ],

        # ── 강제 모드 ──
        "forced_start:start": [
            ({"경험:강제횟수": 5}, ["...(조용히 눈물을 흘린다.)", "...(힘없이 눈을 감는다.)"]),
            ({}, ["안 돼... 제발 그러지 마..."]),
        ],
        "forced_ecstasy:start": [
            ({"경험:강제횟수": 5}, ["...(울면서도 몸이 반응하고 있다.)"]),
            ({}, ["왜...? 왜 이런 거 느끼는 거야...?"]),
        ],
        "forced_break_free:start": [
            ({}, ["... (울면서 도망친다)"]),
        ],

        # ── 트랜스 ──
        "trance:start": [
            ({"성욕": 80}, ["...하아...♡ 더... 해주세요... 멈추지 마세요...♡", "...이상해요... 머리가... 뜨거워요...♡"]),
            ({}, ["...으...! 몸이... 이상해요...", "...왜... 이렇게... 느껴지는 거..."]),
        ],
        "trance_insert:start": [
            ({"성욕": 80}, ["...안에... 넣어주세요... 참을 수 없어요...♡", "...빈 곳이... 아파요... 채워줘요...♡"]),
            ({}, ["...(무의식적으로 다리를 벌리고 있다.)", "...몸이... 말을 안 들어요..."]),
        ],
    }

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def _first_meet_handler(self, player_id):
        """첫 만남 이벤트 핸들러 - 누적형 대화 (Conversation)"""
        # 누적형 대화 빌더 사용
        conv = ui.Conversation("밀라")

        # 도입: 밀라가 플레이어를 발견
        conv.narration(
            "눈앞에 따뜻한 인상의 여성이 있다.",
            "갈색 머리에 다정한 눈빛. 걱정스러운 표정으로 이쪽을 바라본다."
        )

        conv.say(
            "어머! 깨어나셨군요!",
            "다행이에요... 정말 걱정했어요.",
            "몸은 괜찮으세요? 아픈 데는 없어요?"
        )

        # 첫 번째 선택지: 상태에 대해
        conv.ask([
            ("괜찮아요", "fine"),
            ("무슨 일이 있었던 거죠?", "what_happened"),
            ("당신은 누구예요?", "who"),
            ("(헤어지기)", "@exit"),
        ])

        conv.respond("fine",
            "정말요? 다행이에요!",
            "숲에서 쓰러져 계셨거든요...",
            "많이 놀랐어요."
        )

        conv.respond("what_happened",
            "저도 자세히는 몰라요...",
            "숲 근처에서 쓰러져 계신 걸 발견했거든요.",
            "혼자 두면 위험할 것 같아서 데려왔어요."
        )

        conv.respond("who",
            "아, 저도 소개를 안 했네요!"
        )

        # 밀라 자기소개
        conv.say(
            "저는 밀라예요.",
            "이 저택에서 요리랑 살림을 맡고 있어요."
        )

        # 두 번째 선택지: 추가 질문
        conv.say("궁금한 거 있으시면 말씀해 주세요~")

        conv.ask([
            ("다른 사람도 있어요?", "others"),
            ("기억이 없어요...", "memory"),
            ("감사해요", "thanks"),
            ("(헤어지기)", "@exit"),
        ])

        conv.respond("others",
            "네! 저 말고도 두 명 더 있어요.",
            "세라는... 좀 무뚝뚝하지만 믿음직한 사람이에요.",
            "리나는 밝고 활발한 아이예요.",
            "셋이서 사이좋게 지내고 있어요~"
        )

        conv.respond("memory",
            "...그렇군요.",
            "사실... 저희도 그래요.",
            "세라도, 리나도, 저도... 아무것도 기억 못 해요.",
            "어느 날 눈을 떴을 때 이미 여기 있었어요.",
            "당신도... 같은 건지도 모르겠네요."
        )

        conv.respond("thanks",
            "에헤헤, 아니에요~",
            "당연히 해야 할 일이었어요.",
            "혼자 쓰러져 계시는데 그냥 지나칠 수 없잖아요."
        )

        # 마무리
        conv.say(
            "천천히 회복하세요.",
            "필요한 게 있으시면 언제든 말씀해 주세요!",
            "밥 먹을 시간에 부를게요~"
        )

        # 누적형 대화 시작
        yield conv.end()

        # 시간 경과 처리
        morld.set_npc_time_consume(self.instance_id, "stay", 1 * _M)
        morld.set_npc_job(self.instance_id, "stay", 2 * _M)

        # 첫 만남 완료 처리 (관계:밀라:진척도 = 1)
        self.mark_first_meet_done(player_id)

    # ========================================
    # 임신/모드 후유증 반응
    # ========================================

    def _handle_pregnancy_event(self, player_id, event_key):
        """밀라 임신 이벤트 반응"""
        import pregnancy as _preg
        week = _preg.get_pregnancy_week(self.instance_id)

        if event_key == "conception:discovery":
            yield ui.dialog(f"[{self.name}]\n\"...아이가 생긴 것 같아요.\"\n\"...당신의 아이예요... 기뻐요...\"")
        elif event_key == "conception:unknown_father":
            yield ui.dialog(f"[{self.name}]\n\"...몸이 좀 이상해요...\"\n\"...혹시... 임신...?\"")
        elif event_key == "pregnancy:announcement":
            yield ui.dialog(f"[{self.name}]\n\"{week}주차래요.\"\n\"...함께 지켜봐 주세요... 네?\"")
        elif event_key == "pregnancy:unknown_father":
            yield ui.dialog(f"[{self.name}]\n\"{week}주차... 래요.\"\n\"...아빠가 누구인지는... 모르겠어요...\"")

    def _handle_mode_aftermath(self, player_id, event_key):
        """밀라 모드 피해 후유증 반응"""
        if event_key == "forced_aftermath":
            yield ui.dialog(f"[{self.name}]\n\"...오지 마세요...\"\n밀라가 몸을 움츠리며 눈물을 흘린다.")
        elif event_key == "unconscious_aftermath":
            yield ui.dialog(f"[{self.name}]\n\"...어젯밤에 뭔가... 이상한 꿈을 꿨어요...\"\n밀라가 불안한 표정을 짓는다.")
        elif event_key == "frozen_aftermath":
            yield ui.dialog(f"[{self.name}]\n\"...어...? 시간이 갑자기...\"\n밀라가 고개를 갸웃거린다. \"...몸이 좀 이상한 것 같아요...\"")

    # ========================================
    # 침대 이벤트
    # ========================================

    def on_bed_awake(self, bed, player_id, slot, affection, region_id, owner_id):
        """
        밀라 방 침대 반응 (깨어있을 때)
        - 호감도 50 이상: 허용 + 행동 선택
        - 호감도 50 미만: 강제 퇴출
        """
        if affection >= 50:
            yield ui.dialog([
                "[밀라]",
                "어머, 피곤해? 잠깐 누워도 돼~"
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog([
                    "밀라의 침대에 누웠다.",
                    "은은한 꽃향기가 난다."
                ])
            else:
                return
        else:
            # 강제 퇴출 이벤트
            yield ui.dialog([
                "[밀라]",
                "...뭐 하는 거야?"
            ])
            yield ui.dialog([
                "[밀라]",
                "남의 침대에 함부로 눕는 건 좀 아니지 않아?",
                "나가줘."
            ])
            # 거실로 강제 이동 (밀라 방은 1층 → 거실 location 1)
            morld.set_unit_location(player_id, region_id, 1, 120)
            yield ui.dialog(["밀라에게 쫓겨나 거실로 나왔다..."])
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

        if affection >= 80:
            if choice == "breast":
                yield ui.dialog([
                    "손을 뻗어 밀라의 가슴에 살짝 닿았다.",
                    "[밀라]",
                    "+앗...! 뭐, 뭐야~",
                    "+...갑자기 그러면 놀라잖아.",
                    "밀라가 얼굴을 붉히면서도...",
                    "+손을 치우지는 않았다."
                ])
            elif choice == "butt":
                yield ui.dialog([
                    "손을 뻗어 밀라의 엉덩이에 살짝 닿았다.",
                    "[밀라]",
                    "+까악! 어디 만지는 거야!",
                    "+...진짜 나쁜 사람이네.",
                    "밀라가 이불로 얼굴을 가렸다.",
                    "+...하지만 화난 것 같지는 않다."
                ])
            elif choice == "kiss":
                yield ui.dialog([
                    "밀라의 얼굴에 가까이 다가갔다.",
                    "[밀라]",
                    "+...어...?",
                    "+......",
                    "밀라의 입술에 가볍게 키스했다.",
                    "밀라가 눈을 감았다.",
                    "+얼굴이 새빨갛다.",
                    "+\"...바보.\""
                ])
            elif choice == "hug":
                yield ui.dialog([
                    "밀라를 부드럽게 안아줬다.",
                    "[밀라]",
                    "+...에헤헤.",
                    "+갑자기 왜 이래~",
                    "밀라가 행복하게 안겨왔다.",
                    "+따뜻하고 포근한 체온이 느껴진다."
                ])
        else:
            # 호감 50~79 - 당황하지만 허용
            if choice == "breast":
                yield ui.dialog([
                    "손을 뻗어 밀라의 가슴에 닿으려는 순간—",
                    "[밀라]",
                    "+...!! 뭐, 뭐 하는 거야!?",
                    "밀라가 얼굴을 붉히며 손을 쳐냈다.",
                    "+\"그런 건 아직... 이르다고!\""
                ])
            elif choice == "butt":
                yield ui.dialog([
                    "손을 뻗어 밀라의 엉덩이에 닿으려는 순간—",
                    "[밀라]",
                    "+어딜 만져!?",
                    "+이 사람 진짜...!",
                    "밀라가 화를 내면서도 쫓아내지는 않았다.",
                    "+...다행이다."
                ])
            elif choice == "kiss":
                yield ui.dialog([
                    "밀라의 얼굴에 가까이 다가갔다.",
                    "[밀라]",
                    "+으, 응...? 갑자기 왜...?",
                    "밀라가 당황해서 눈을 질끈 감았다.",
                    "+...이마에 가볍게 키스했다.",
                    "[밀라]",
                    "+...바, 바보!! 놀라잖아!!"
                ])
            elif choice == "hug":
                yield ui.dialog([
                    "밀라를 살짝 안아줬다.",
                    "[밀라]",
                    "+엇, 갑자기...!",
                    "+...뭐야, 좀 부끄럽잖아.",
                    "밀라가 어색하게 웃으며 안겼다.",
                    "+심장 소리가 빠르게 뛰는 게 느껴진다."
                ])

    def on_bed_sleeping(self, bed, player_id, slot, affection, owner_id):
        """밀라가 자고 있을 때 - 호감도 무관하게 허용 (자고 있으니 모름)"""
        success = False
        if affection >= 50:
            yield ui.dialog([
                "밀라가 새근새근 잠들어 있다.",
                "평소의 활기찬 모습과는 다른, 고요한 얼굴."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog(["살며시 옆에 누웠다."])
        else:
            yield ui.dialog([
                "밀라가 잠들어 있다.",
                "...깨우면 안 된다."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog([
                    "숨을 죽이며 옆에 누웠다.",
                    "(들키면 죽는다.)"
                ])

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
                    "손을 뻗어 밀라의 가슴에 살짝 닿았다.",
                    "+...풍만하고 부드럽다.",
                    "밀라가 잠결에 \"음...\" 하고 신음했다.",
                    "+...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "손을 뻗어 밀라의 가슴에 살짝 닿았다.",
                    "+...풍만하고 부드럽다.",
                    "밀라의 눈꺼풀이 파르르 떨렸다.",
                    "+(이건 진짜 죽는다.)",
                    "+...서둘러 손을 뗐다."
                ])
        elif choice == "butt":
            if affection >= 50:
                yield ui.dialog([
                    "손을 뻗어 밀라의 엉덩이에 살짝 닿았다.",
                    "+...탱글탱글하다.",
                    "밀라가 잠결에 살짝 몸을 뒤척였다.",
                    "+...깨지 않았다. 다행이다."
                ])
            else:
                yield ui.dialog([
                    "손을 뻗어 밀라의 엉덩이에 살짝 닿았다.",
                    "+...탱글탱글하다.",
                    "밀라가 \"으...\" 하며 인상을 찌푸렸다.",
                    "+(심장이 멎을 뻔했다.)",
                    "+...서둘러 손을 뗐다."
                ])
        elif choice == "kiss":
            if affection >= 50:
                yield ui.dialog([
                    "밀라의 얼굴에 가까이 다가갔다.",
                    "잠든 밀라의 볼에 살짝 키스했다.",
                    "+밀라가 잠결에 \"음...\" 하고 웃었다.",
                    "잠결에도 행복한 표정이다.",
                    "+...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "밀라의 얼굴에 가까이 다가갔다.",
                    "잠든 밀라의 이마에 가볍게 키스했다.",
                    "+밀라의 미간이 살짝 움직였다.",
                    "(깨면 진짜 끝이다.)",
                    "+...서둘러 물러났다."
                ])


# ========================================
# AI Agent
# ========================================

@register_agent_class("mila")
class MilaAgent(BaseAgent):
    """
    밀라 AI - 요리 + 실내 관리 담당

    특징:
    - 다정하고 걱정 많음
    - 식사 준비와 실내 청소를 담당
    - 세라를 리더로 신뢰하고 따름
    - 플레이어가 아프면 걱정하며 지켜봄
    - 계절별로 스케줄이 달라짐
    """

    # 계절별 스케줄
    # x: Location 내 목표 좌표 (Pi-World, 1unit/sec 기준)
    # 밀라방(180), 주방(180), 식당(180), 거실(360), 뒷마당(600)
    SCHEDULES = {
        "봄": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 300 * _M, "end": 330 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 330 * _M, "end": 360 * _M, "activity": "준비"},
            {"name": "아침준비", "start": 360 * _M, "end": 420 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "설거지"},
            {"name": "청소", "start": 540 * _M, "end": 660 * _M, "dynamic": True, "candidates": [
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심준비", "start": 660 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "정원가꾸기", "region_id": 0, "location_id": 13, "x": 300, "start": 780 * _M, "end": 900 * _M, "activity": "정원"},  # 봄: 정원 가꾸기
            {"name": "저녁준비", "start": 1020 * _M, "end": 1110 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "저택 소등", "start": 1290 * _M, "end": 1320 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1320 * _M, "end": 300 * _M, "activity": "수면"},
        ],
        "여름": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 240 * _M, "end": 270 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 270 * _M, "end": 300 * _M, "activity": "준비"},  # 여름: 일찍 기상
            {"name": "아침준비", "start": 300 * _M, "end": 360 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 360 * _M, "end": 420 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "설거지"},
            {"name": "청소", "start": 480 * _M, "end": 600 * _M, "dynamic": True, "candidates": [
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심준비", "start": 660 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "낮잠", "region_id": 0, "location_id": 9, "x": 120, "start": 780 * _M, "end": 900 * _M, "activity": "휴식"},  # 여름: 더위 피해 낮잠
            {"name": "저녁준비", "start": 1020 * _M, "end": 1110 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "저택 소등", "start": 1350 * _M, "end": 1380 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1380 * _M, "end": 240 * _M, "activity": "수면"},  # 여름: 늦게 잠
        ],
        "가을": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 300 * _M, "end": 330 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 330 * _M, "end": 360 * _M, "activity": "준비"},
            {"name": "아침준비", "start": 360 * _M, "end": 420 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "설거지"},
            {"name": "청소", "start": 540 * _M, "end": 660 * _M, "dynamic": True, "candidates": [
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심준비", "start": 660 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "저장식품준비", "start": 780 * _M, "end": 960 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "저녁준비", "start": 1020 * _M, "end": 1110 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "저택 소등", "start": 1290 * _M, "end": 1320 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1320 * _M, "end": 300 * _M, "activity": "수면"},
        ],
        "겨울": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 360 * _M, "end": 390 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 390 * _M, "end": 420 * _M, "activity": "준비"},  # 겨울: 늦게 기상
            {"name": "아침준비", "start": 420 * _M, "end": 480 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 540 * _M, "end": 600 * _M, "activity": "설거지"},
            {"name": "청소", "start": 600 * _M, "end": 720 * _M, "dynamic": True, "candidates": [
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심준비", "start": 720 * _M, "end": 780 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 780 * _M, "end": 840 * _M, "activity": "식사"},
            {"name": "휴식", "region_id": 0, "location_id": 1, "x": 210, "start": 840 * _M, "end": 960 * _M, "activity": "휴식"},  # 겨울: 실내 휴식 (소파)
            {"name": "저녁준비", "start": 1020 * _M, "end": 1110 * _M, "dynamic": True, "candidates": [
                {"activity": "요리", "condition": "can_cook"},
                {"activity": "청소", "condition": "should_clean"},
                {"activity": "휴식", "condition": None},
            ]},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1230 * _M, "activity": "정리"},
            {"name": "저택 소등", "start": 1230 * _M, "end": 1260 * _M, "activity": "소등"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1260 * _M, "end": 360 * _M, "activity": "수면"},  # 겨울: 일찍 잠
        ],
    }

    owner_unique_id = "mila"
    sleep_location = {"region_id": 0, "location_id": 9, "x": 120}  # 밀라방
    bath_location = {"region_id": 0, "location_id": 4, "x": 15}  # 욕실
    wardrobe_location = {"region_id": 0, "location_id": 9, "x": 25}  # 밀라방 옷장
    toilet_location = {"region_id": 0, "location_id": 15, "x": 15}  # 1층 화장실

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self._memory["current_season"] = None
        # 초기 스케줄은 think()에서 계절 확인 후 설정
        import survival
        survival.register_npc(unit_id)
        import temperature
        temperature.register_character(unit_id)
        import needs
        needs.register_character(unit_id)
        import pregnancy
        pregnancy.register_character(unit_id)

    def _get_current_season(self):
        """현재 계절 반환 (게임 날짜 기반)"""
        time_info = morld.get_time_info()
        month = time_info.get("month", 3)  # 기본값: 3월 (봄)

        # 월 -> 계절 매핑 (3-5: 봄, 6-8: 여름, 9-11: 가을, 12-2: 겨울)
        if month in (3, 4, 5):
            return "봄"
        elif month in (6, 7, 8):
            return "여름"
        elif month in (9, 10, 11):
            return "가을"
        else:  # 12, 1, 2
            return "겨울"

    def think(self):
        """밀라의 행동 결정 - 계절에 따라 스케줄 변경"""
        # 계절이 바뀌면 기본 스케줄 교체
        season = self._get_current_season()
        if season != self._memory["current_season"]:
            self._memory["current_season"] = season
            new_schedule = self.SCHEDULES.get(season, self.SCHEDULES["봄"])
            self.set_base_schedule(new_schedule)
            print(f"[MilaAgent] 계절 변경: {season}")

        # 나머지는 BaseAgent.think()에 위임
        return super().think()


# ========================================
# 캐릭터 개인 퀘스트 (CHARACTER_QUESTS)
# ========================================
# 밀라 관련 퀘스트는 캐릭터 파일에서 직접 정의

Mila.CHARACTER_QUESTS = [
    # ========================================
    # 허브티 연쇄 퀘스트 1: 허브 채집
    # ========================================
    {
        "unique_id": "mila_herb_gather",
        "name": "허브 채집",
        "description": "밀라를 위해 정원에서 허브를 채집하자.",
        "category": "personal",

        "prerequisites": ["sub_meet_mila"],
        "giver": "mila",
        "reporter": "mila",

        "conditions": [
            {"type": "collect", "item": "herb", "count": 3},
        ],

        "rewards": [
            {"type": "prop", "target": "player", "prop": "관계:밀라:호감", "value": 5},
            {"type": "unlock_quest", "quest": "mila_herb_dry"},
        ],

        "dialogs": {
            "offer": [
                "[밀라]",
                "저... 부탁 하나 해도 될까요?",
                "정원에서 허브를 좀 구해올 수 있어요?",
                "허브티를 만들고 싶은데, 재료가 부족해서요.",
                "허브 3개만 있으면 될 것 같아요!",
            ],
            "accept": [
                "[밀라]",
                "감사해요!",
                "정원 쪽에 허브가 자라고 있을 거예요.",
            ],
            "decline": [
                "[밀라]",
                "...알겠어요.",
                "(조금 아쉬운 표정이다)",
            ],
            "progress": [
                "[밀라]",
                "허브는 구했어요...?",
                "정원에 있을 거예요!",
            ],
            "complete": [
                "[밀라]",
                "와! 좋은 허브네요!",
                "(밀라에게 허브 3개를 건넸다)",
                "이제 말려서 차를 만들어야 해요.",
                "조금 기다려 주실래요?",
            ],
        },
    },

    # ========================================
    # 허브티 연쇄 퀘스트 2: 허브 건조
    # ========================================
    {
        "unique_id": "mila_herb_dry",
        "name": "허브 건조",
        "description": "밀라가 허브를 말리는 동안 기다리자.",
        "category": "personal",

        "prerequisites": ["mila_herb_gather"],
        "giver": None,  # 자동 시작
        "reporter": "mila",

        "conditions": [
            {"type": "wait", "hours": 2},  # 2시간 대기
        ],

        "rewards": [
            {"type": "prop", "target": "player", "prop": "관계:밀라:호감", "value": 3},
            {"type": "unlock_quest", "quest": "mila_herb_tea"},
        ],

        "dialogs": {
            "offer": [
                "[밀라]",
                "허브를 말리는 데 2시간 정도 걸려요.",
                "그동안 다른 일 하셔도 괜찮아요!",
            ],
            "progress": [
                "[밀라]",
                "아직 말리는 중이에요~",
                "조금만 더 기다려 주세요!",
            ],
            "complete": [
                "[밀라]",
                "다 말랐어요!",
                "이제 차를 끓이면 되겠네요.",
            ],
        },
    },

    # ========================================
    # 허브티 연쇄 퀘스트 3: 허브티 조리
    # ========================================
    {
        "unique_id": "mila_herb_tea",
        "name": "허브티 조리",
        "description": "밀라에게 말린 허브를 전달하고 허브티를 만들어 달라고 하자.",
        "category": "personal",

        "prerequisites": ["mila_herb_dry"],
        "giver": None,  # 자동 시작
        "reporter": "mila",

        "conditions": [
            {"type": "talk", "target": "mila"},
        ],

        "rewards": [
            {"type": "prop", "target": "player", "prop": "관계:밀라:호감", "value": 7},
            {"type": "item", "item": "herb_tea", "count": 2},
        ],

        "dialogs": {
            "offer": [
                "밀라에게 허브티를 만들어 달라고 하자.",
            ],
            "complete": [
                "[밀라]",
                "허브티 완성이에요!",
                "(향긋한 허브 향이 퍼진다)",
                "같이 마셔요!",
                "(밀라와 함께 따뜻한 허브티를 마셨다)",
                "(허브티 2잔을 받았다)",
            ],
        },
    },

    # ========================================
    # 사과 파이 퀘스트 (기존 side_quests에서 이동)
    # ========================================
    {
        "unique_id": "mila_apple_pie",
        "name": "밀라의 요리 재료",
        "description": "밀라가 요리에 쓸 사과 5개를 모아오자.",
        "category": "personal",

        "prerequisites": ["mila_herb_tea"],  # 허브티 연쇄 완료 후
        "giver": "mila",
        "reporter": "mila",

        "conditions": [
            {"type": "collect", "item": "apple", "count": 5},
        ],

        "rewards": [
            {"type": "item", "item": "apple_pie", "count": 1},
            {"type": "prop", "target": "player", "prop": "관계:밀라:호감", "value": 10},
        ],

        "dialogs": {
            "offer": [
                "[밀라]",
                "저... 사과를 좀 구해올 수 있어요?",
                "파이를 만들고 싶은데, 재료가 부족해서요.",
                "5개만 있으면 될 것 같아요!",
            ],
            "accept": [
                "[밀라]",
                "고마워요!",
                "숲에 사과나무가 있을 거예요.",
            ],
            "decline": [
                "[밀라]",
                "...알겠어요.",
                "(조금 아쉬운 표정이다)",
            ],
            "progress": [
                "[밀라]",
                "사과는 모았어요...?",
                "5개면 충분해요!",
            ],
            "complete": [
                "[밀라]",
                "와! 고마워요!",
                "(밀라에게 사과 5개를 건넸다)",
                "이걸로 맛있는 파이를 만들어 드릴게요!",
                "(밀라에게서 사과 파이를 받았다)",
            ],
        },
    },

    # ========================================
    # 밀라의 신뢰 퀘스트: 호감도 70 이상
    # ========================================
    {
        "unique_id": "mila_trust",
        "name": "밀라의 신뢰",
        "description": "밀라와 더 친해지자.",
        "category": "personal",

        "prerequisites": ["mila_apple_pie"],
        "giver": None,
        "reporter": "mila",

        "conditions": [
            {"type": "prop", "target": "player", "prop": "관계:밀라:호감", "min_value": 70},
        ],

        "rewards": [
            {"type": "item", "item": "mila_recipe_book", "count": 1},
            {"type": "prop", "target": "player", "prop": "관계:밀라:신뢰", "value": 1},
        ],

        "dialogs": {
            "complete": [
                "[밀라]",
                "저기...!",
                "이거... 받아주세요!",
                "(밀라가 레시피 북을 건넨다)",
                "제가 모은 요리법이에요.",
                "같이... 요리하고 싶어서...",
                "(밀라가 얼굴을 붉힌다)",
            ],
        },
    },
]
