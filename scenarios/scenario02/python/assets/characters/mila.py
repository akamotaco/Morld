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
from assets.base import Character
from think import BaseAgent, register_agent_class

_M = 60_000  # millis per minute


class Mila(Character):
    unique_id = "mila"
    name = "밀라"
    type = "female"
    props = {
        "외모:갈색머리": 1, "외모:중간머리": 1, "외모:갈색눈": 1,
        "성격:다정함": 1, "성격:걱정많음": 1,
        "관계:세라:신뢰": 1,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 6,
        "can:lie_down": 1,
        "can:sleep": 1,
        "can:bath": 1,
        "can:toggle_switch": 1,
    }
    actions = [
        "call:talk:대화",
        "call:errand:심부름#",         # 퀘스트 제안 가능 시만 표시
        "call:romance:스킨십",
        "call:debug_props:(디버그) 속성 보기#",
        "call:debug_affection_up:(디버그) 호감도 +10#",
        "call:debug_affection_down:(디버그) 호감도 -10#",
        "call:debug_arousal_up:(디버그) 성욕 +20#",
        "call:debug_arousal_down:(디버그) 성욕 -20#",
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
    DESCRIBE_RULES = [
        # 이동 중
        ({"is_traveling": True, "activity": "요리"}, "{name}가 부엌으로 향하고 있다."),
        ({"is_traveling": True, "activity": "청소"}, "{name}가 청소를 하러 이동 중이다."),
        ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),

        # Activity 기반
        ({"activity": "요리"}, "{name}가 분주하게 요리하고 있다."),
        ({"activity": "청소"}, "{name}가 열심히 청소하고 있다."),
        ({"activity": "식사"}, "{name}가 다른 사람들이 먹는 모습을 흐뭇하게 바라본다."),
        ({"activity": "수면"}, "{name}가 포근하게 잠들어 있다."),
        ({"activity": "휴식"}, "{name}가 따뜻한 차를 마시고 있다."),
        ({"activity": "설거지"}, "{name}가 설거지를 하고 있다."),
        ({"activity": "정리"}, "{name}가 정리 중이다."),

        # 위치 기반
        ({"location": (0, 2)}, "{name}가 요리에 열중하고 있다."),
        ({"location": (0, 3)}, "{name}가 식탁을 정리하고 있다."),

        # 성욕 기반 (높은 성욕 우선) - 밀라: 적극적이지만 숨기려 함
        ({"성욕": 80}, "{name}가 자꾸 가까이 다가온다. 얼굴이 상기되어 있다."),
        ({"성욕": 60}, "{name}가 뭔가 말하고 싶은 듯 입술을 달싹인다."),
        ({"성욕": 40}, "{name}가 평소보다 자주 이쪽을 쳐다본다. 손이 어딘가 바쁘다."),

        # 호감도/애정 기반 - 밀라: 다정하게 다가옴
        ({"애정": 80}, "{name}가 따스한 눈으로 곁에 다가와 팔을 살며시 잡는다."),
        ({"애정": 50}, "{name}가 다정하게 미소 짓는다. 눈에 애정이 가득하다."),
        ({"호감": 70}, "{name}가 온화하게 손을 흔든다. \"잘 지내셨어요?\""),
        ({"호감": 50}, "{name}가 반갑게 인사한다. 따뜻한 미소가 느껴진다."),

        # 기본값
        ({}, "{name}가 다정한 눈으로 주변을 살핀다."),
    ]

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = [
        # Activity 기반
        ({"activity": "요리"}, "앞치마를 두르고 열심히 요리하고 있다."),
        ({"activity": "청소"}, "걸레를 들고 구석구석 닦고 있다."),
        ({"activity": "식사"}, "다른 사람들이 맛있게 먹는지 살피고 있다."),
        ({"activity": "수면"}, "평화롭게 잠들어 있다."),
        ({"activity": "설거지"}, "정성스럽게 설거지를 하고 있다."),
        ({"activity": "휴식"}, "따뜻한 차를 마시며 여유를 즐기고 있다."),

        # mood 기반
        ({"mood": "기쁨"}, "온화하게 웃고 있다. 보는 사람도 기분이 좋아진다."),
        ({"mood": "슬픔"}, "걱정스러운 표정이다. 무언가 마음에 걸리는 것 같다."),

        # 성욕 기반 (높은 성욕 우선) - 밀라: 저돌적이지만 부끄러워함
        ({"성욕": 80}, "볼이 발그레하다. 눈동자가 흔들리고, 입술을 살짝 깨물고 있다."),
        ({"성욕": 60}, "평소보다 시선이 오래 머문다. 뭔가 말하려다 말았다."),
        ({"성욕": 40}, "조금 멍해 보인다. 손이 무의식적으로 옷깃을 매만진다."),

        # 애정/호감도 기반 - 밀라: 따뜻함과 걱정이 어우러짐
        ({"애정": 80}, "눈가가 촉촉하다. 사랑과 걱정이 가득한 표정으로 바라본다."),
        ({"애정": 50}, "따뜻한 눈빛이다. 보고만 있어도 마음이 편안해진다."),
        ({"호감": 70}, "따뜻한 눈빛으로 당신을 바라본다. 걱정과 애정이 느껴진다."),
        ({"호감": 50}, "친근하게 미소 짓는다. 편안한 분위기가 느껴진다."),

        # 기본값
        ({}, "부드러운 갈색 머리의 다정한 여성. 따뜻한 갈색 눈이 편안함을 준다."),
    ]

    # ========================================
    # NPC 주도 설정 (밀라: 저돌적/적극적)
    # ========================================
    INITIATIVE_CONFIG = {
        "arousal_threshold": 50,      # 성욕 임계값 (세라보다 낮음 - 더 적극적)
        "affection_threshold": 40,    # 호감도 임계값 (세라보다 낮음)
        "cooldown_millis": 360 * _M,   # 쿨다운 6시간 (세라보다 짧음)
    }

    # NPC 주도 시 허용 액션 필터 (캐릭터별)
    # 형식: [(조건dict, [허용_액션_리스트]), ...]
    # 밀라는 저돌적이므로 더 낮은 애정에서도 다양한 액션 허용
    INITIATIVE_ACTION_FILTERS = [
        ({"애정": 60}, ["hug", "deep_kiss", "breast_touch"]),  # 세라보다 낮은 조건
        ({"애정": 30}, ["hug", "deep_kiss"]),  # 세라보다 낮은 조건
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
        "escape_fail": [
            ({}, ["...가지 마세요...", "...조금만 더요..."]),
        ],
        "satisfied": [
            ({"애정": 50}, ["...사랑해요...", "...행복해요..."]),
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
            ({"애정": 40}, ["...무서웠어요...", "...다행이에요..."]),
            ({}, ["...휴... 다행이에요...", "...(가슴을 쓸어내린다)"]),
        ],
        "effects": {"호감": -1, "애정": 1},  # 부끄러워서 호감 감소, 하지만 사랑은 증가
    }

    # ========================================
    # 스킨십 반응 (action:timing → 조건부 대사 리스트)
    # 형식: (조건dict, [대사들]) - 조건 충족 시 대사들이 후보에 추가
    # ========================================
    ROMANCE_REACTIONS = {
        # 즉시형 행위
        "head_pat:start": [
            ({}, ["...고마워요.", "...따뜻해요.", "...좋아요, 이런 거.", "...부끄러워요...", "...더 해주세요..."]),
        ],
        "cheek_caress:start": [
            ({}, ["...간지러워요...", "...으응...", "손이... 따뜻해요.", "...부끄러워요."]),
        ],
        "cheek_pinch:start": [
            ({}, ["아얏! 아파요~", "으응... 그만요~", "...나빠요.", "왜 그러세요~ 아야~"]),
        ],
        "ear_touch:start": [
            ({}, ["...!!! 거, 거기는...!", "...으응... 간지러워요...", "...귀는... 약해요...", "...하앙..."]),
        ],
        "french_kiss:start": [
            ({}, ["...으응...♡", "...하앙... 숨이...", "...더... 해주세요...", "...음...♡"]),
        ],
        "butt_caress:start": [
            ({}, ["...!! 거, 거기는...!", "...부끄러워요...", "...누가 볼까봐...", "...으응..."]),
        ],

        # 토글형 행위
        "hug:start": [
            ({"애정": 50}, ["...사랑해요...", "...정말 행복해요..."]),
            ({"호감": 80}, ["...정말 좋아요... 이대로 있고 싶어요..."]),
            ({}, ["...꼭 안아주세요...", "...따뜻해요...", "...좋아요...", "...이대로 있고 싶어요..."]),
        ],
        "hug:during": [
            ({"성욕": 50}, ["밀라가 숨을 거칠게 몰아쉬며 안겨 있다."]),
            ({"성욕": 30}, ["밀라의 심장이 빠르게 뛰는 게 느껴진다."]),
            ({"애정": 40}, ["밀라가 행복한 표정으로 안겨 있다."]),
            ({}, ["밀라가 품 안에서 편안하게 안겨 있다.", "밀라의 따뜻한 체온이 느껴진다.", "밀라가 당신의 등을 가만히 쓰다듬는다.", "밀라가 조용히 눈을 감고 있다."]),
        ],
        "deep_kiss:start": [
            ({"성욕": 40}, ["...하앙... 더... 해주세요...♡"]),
            ({"애정": 30}, ["...사랑해요... 으응...♡"]),
            ({}, ["...으응...♡", "...키스... 해주세요...", "...눈 감을게요..."]),
        ],
        "deep_kiss:during": [
            ({"성욕": 50}, ["밀라가 거친 숨을 몰아쉬며 키스에 빠져 있다."]),
            ({"성욕": 30}, ["밀라의 숨결이 거칠어진다."]),
            ({}, ["밀라와 깊은 입맞춤을 나누고 있다.", "밀라의 부드러운 입술이 느껴진다.", "밀라가 눈을 감고 키스에 빠져 있다."]),
        ],
        "breast_touch:start": [
            ({}, ["...!! 거, 거기는...!", "...부끄러워요... 하지만...", "...으응... 살살요..."]),
        ],
        "breast_touch:during": [
            ({}, ["밀라가 얼굴을 붉히며 참고 있다.", "밀라가 작은 신음을 흘린다.", "밀라가 당신의 손을 부끄럽게 바라본다.", "밀라의 심장이 빠르게 뛰는 게 느껴진다."]),
        ],

        # 절정 반응
        "ecstasy:start": [
            ({}, ["...하앙...!! ♡♡♡", "...이, 이상해요... 머리가 하얘져요...♡", "...으응...!! 안 돼... 이러면...♡♡", "...사, 사랑해요...♡♡♡"]),
        ],
    }

    # ========================================
    # TALK_RULES에서 "_메서드명"으로 위임됨
    # ========================================

    def _talk_friendly_high(self, context):
        """호감도 70 이상 - 진척도 증가"""
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        # 진척도 체크 및 증가
        prop_key = f"관계:{player_name}:진척도"
        props = morld.get_unit_props(self.instance_id)
        progress = props.get(prop_key, 0) if props else 0

        if progress < 3:
            morld.modify_prop(self.instance_id, prop_key, 1)

        yield ui.dialog([
            f"[{name}]",
            "오셨군요~",
            "...괜찮으세요? 뭔가 필요하신 거 있으세요?",
        ])

    def _talk_friendly_mid(self, context):
        """호감도 50 이상 - 진척도 증가"""
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        # 진척도 체크 및 증가
        prop_key = f"관계:{player_name}:진척도"
        props = morld.get_unit_props(self.instance_id)
        progress = props.get(prop_key, 0) if props else 0

        if progress < 1:
            morld.modify_prop(self.instance_id, prop_key, 1)

        yield ui.dialog([
            f"[{name}]",
            "안녕하세요!",
            "...뭐 드시고 싶은 거 있으세요?",
        ])

    def _talk_progress_1(self, context):
        """진척도 1 - 자신에 대한 이야기 (일회성)"""
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        # 플래그 체크 (이미 들었으면 일반 대화)
        flag_key = f"대화:{player_name}:진척도1"
        props = morld.get_unit_props(self.instance_id)
        if props and props.get(flag_key):
            yield ui.dialog([f"[{name}]", "오셨군요~", "뭔가 필요하신 게 있으세요?"])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)

        yield ui.dialog([
            f"[{name}]",
            "저요?",
            "저는 밀라예요. 여기서 살림을 맡고 있어요.",
            "요리, 청소, 빨래... 뭐, 그런 것들이요.",
            "세라랑 리나도 여기 살고 있어요.",
            "세라는... 좀 무뚝뚝하지만, 마음은 따뜻한 아이예요.",
            "리나는 활발하고 귀여운 동생이에요.",
            "...다들 소중한 가족이에요.",
        ])

    def _talk_progress_2(self, context):
        """진척도 2 - 좋아하는 것 (일회성)"""
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        # 플래그 체크
        flag_key = f"대화:{player_name}:진척도2"
        props = morld.get_unit_props(self.instance_id)
        if props and props.get(flag_key):
            yield ui.dialog([f"[{name}]", "오셨군요~", "오늘은 뭐 해드릴까요?"])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)

        yield ui.dialog([
            f"[{name}]",
            "제가 좋아하는 거요?",
            "음... 요리하는 걸 좋아해요.",
            "누군가가 제가 만든 음식을 맛있게 먹을 때...",
            "그 표정을 보면 정말 행복해져요.",
            "특히 새로운 레시피가 성공했을 때!",
            "아, 그리고... 조용히 차 마시는 시간도 좋아요.",
            "혼자 있는 시간이... 싫지 않아요.",
            "...가끔은요.",
        ])

    def _talk_progress_3(self, context):
        """진척도 3 - 과거 이야기 (일회성)"""
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        # 플래그 체크
        flag_key = f"대화:{player_name}:진척도3"
        props = morld.get_unit_props(self.instance_id)
        if props and props.get(flag_key):
            yield ui.dialog([f"[{name}]", "오셨군요~", "...그냥 보고 싶었어요."])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)

        yield ui.dialog([
            f"[{name}]",
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
        ])

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 처음 만났을 때 - Generator 기반"""
        unit_info = morld.get_unit_info(self.instance_id)

        # 수면 중이면 반응 없음
        if unit_info and unit_info.get("activity") == "수면":
            return None

        # 프라이버시 체크 (수면 목적으로 자기 방 도착 시)
        privacy = self._check_room_privacy(player_id)
        if privacy is not None:
            return privacy

        # 첫 만남 여부 판정 (관계:밀라:진척도 <= 0)
        if not self.is_first_meet(player_id):
            # NPC 주도 스킨십 체크 (첫 만남 이후에만)
            if self.should_initiate_skinship(player_id):
                from npc_initiative import start_npc_initiative
                return start_npc_initiative(player_id, self.instance_id)
            return None

        # 첫 만남 이벤트 - 완료 후 진척도 1로 설정
        return self._first_meet_handler(player_id)

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

    def on_equip_change(self, player_id, item_id, is_equip):
        """플레이어 장비 변경 시 반응"""
        # 무기(장착:손) 체크
        item_info = morld.get_item_info(item_id)
        if not item_info:
            return None

        equip_props = item_info.get("equip_props", {})
        if not equip_props.get("장착:손"):
            return None  # 무기가 아니면 무시

        if is_equip:
            morld.add_action_log("밀라가 걱정스러운 눈으로 무기를 바라본다.")
        else:
            morld.add_action_log("밀라가 안심한 듯 미소를 짓는다.")

        return None

    # ========================================
    # 프라이버시 이벤트 (수면 시 방 퇴출)
    # ========================================

    def _on_room_privacy(self, player_id, activity):
        """밀라가 수면/목욕 목적으로 도착했는데 플레이어가 있을 때"""
        props = morld.get_unit_props(self.instance_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"
        affection = props.get(f"관계:{player_name}:호감", 0) if props else 0
        info = morld.get_unit_info(self.instance_id)

        if activity == "수면":
            if affection >= 50:
                def handler():
                    yield ui.dialog([
                        "[밀라]",
                        "어... 여기 있었어?",
                        "...괜찮아, 그냥 잘게."
                    ])
                return handler()
            else:
                def handler():
                    yield ui.dialog([
                        "[밀라]",
                        "...자려고 하는데, 나가줄 수 있어?"
                    ])
                    morld.stand_up(player_id)
                    if info:
                        morld.set_unit_location(player_id, info["region_id"], 1, 120)
                    yield ui.dialog(["밀라의 방에서 나왔다."])
                return handler()
        elif activity == "목욕":
            if affection >= 70:
                def handler():
                    yield ui.dialog([
                        "[밀라]",
                        "어엇!? 왜, 왜 여기 있어!?",
                        "...나, 나가줘! 지금 당장!"
                    ])
                    morld.stand_up(player_id)
                    if info:
                        morld.set_unit_location(player_id, info["region_id"], 1, 120)
                    yield ui.dialog(["욕실에서 나왔다."])
                return handler()
            else:
                def handler():
                    yield ui.dialog([
                        "[밀라]",
                        "......!!",
                        "밀라가 얼굴이 새빨개져서 소리를 질렀다."
                    ])
                    morld.stand_up(player_id)
                    if info:
                        morld.set_unit_location(player_id, info["region_id"], 1, 120)
                    yield ui.dialog(["욕실에서 쫓겨났다."])
                return handler()
        return None

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
            {"name": "아침준비", "region_id": 0, "location_id": 2, "x": 90, "start": 360 * _M, "end": 420 * _M, "activity": "요리"},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "설거지"},
            {"name": "청소", "region_id": 0, "location_id": 1, "x": 180, "start": 540 * _M, "end": 660 * _M, "activity": "청소"},
            {"name": "점심준비", "region_id": 0, "location_id": 2, "x": 90, "start": 660 * _M, "end": 720 * _M, "activity": "요리"},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "정원가꾸기", "region_id": 0, "location_id": 13, "x": 300, "start": 780 * _M, "end": 900 * _M, "activity": "정원"},  # 봄: 정원 가꾸기
            {"name": "저녁준비", "region_id": 0, "location_id": 2, "x": 90, "start": 1020 * _M, "end": 1110 * _M, "activity": "요리"},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1320 * _M, "end": 300 * _M, "activity": "수면"},
        ],
        "여름": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 240 * _M, "end": 270 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 270 * _M, "end": 300 * _M, "activity": "준비"},  # 여름: 일찍 기상
            {"name": "아침준비", "region_id": 0, "location_id": 2, "x": 90, "start": 300 * _M, "end": 360 * _M, "activity": "요리"},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 360 * _M, "end": 420 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "설거지"},
            {"name": "청소", "region_id": 0, "location_id": 1, "x": 180, "start": 480 * _M, "end": 600 * _M, "activity": "청소"},
            {"name": "점심준비", "region_id": 0, "location_id": 2, "x": 90, "start": 660 * _M, "end": 720 * _M, "activity": "요리"},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "낮잠", "region_id": 0, "location_id": 9, "x": 120, "start": 780 * _M, "end": 900 * _M, "activity": "휴식"},  # 여름: 더위 피해 낮잠
            {"name": "저녁준비", "region_id": 0, "location_id": 2, "x": 90, "start": 1020 * _M, "end": 1110 * _M, "activity": "요리"},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1380 * _M, "end": 240 * _M, "activity": "수면"},  # 여름: 늦게 잠
        ],
        "가을": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 300 * _M, "end": 330 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 330 * _M, "end": 360 * _M, "activity": "준비"},
            {"name": "아침준비", "region_id": 0, "location_id": 2, "x": 90, "start": 360 * _M, "end": 420 * _M, "activity": "요리"},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "설거지"},
            {"name": "청소", "region_id": 0, "location_id": 1, "x": 180, "start": 540 * _M, "end": 660 * _M, "activity": "청소"},
            {"name": "점심준비", "region_id": 0, "location_id": 2, "x": 90, "start": 660 * _M, "end": 720 * _M, "activity": "요리"},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
            {"name": "저장식품준비", "region_id": 0, "location_id": 2, "x": 90, "start": 780 * _M, "end": 960 * _M, "activity": "요리"},  # 가을: 저장식품
            {"name": "저녁준비", "region_id": 0, "location_id": 2, "x": 90, "start": 1020 * _M, "end": 1110 * _M, "activity": "요리"},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1320 * _M, "end": 300 * _M, "activity": "수면"},
        ],
        "겨울": [
            {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 360 * _M, "end": 390 * _M, "activity": "목욕"},
            {"name": "기상", "region_id": 0, "location_id": 9, "x": 120, "start": 390 * _M, "end": 420 * _M, "activity": "준비"},  # 겨울: 늦게 기상
            {"name": "아침준비", "region_id": 0, "location_id": 2, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "요리"},
            {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 480 * _M, "end": 540 * _M, "activity": "식사"},
            {"name": "설거지", "region_id": 0, "location_id": 2, "x": 90, "start": 540 * _M, "end": 600 * _M, "activity": "설거지"},
            {"name": "청소", "region_id": 0, "location_id": 1, "x": 180, "start": 600 * _M, "end": 720 * _M, "activity": "청소"},
            {"name": "점심준비", "region_id": 0, "location_id": 2, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "요리"},
            {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 780 * _M, "end": 840 * _M, "activity": "식사"},
            {"name": "휴식", "region_id": 0, "location_id": 1, "x": 210, "start": 840 * _M, "end": 960 * _M, "activity": "휴식"},  # 겨울: 실내 휴식 (소파)
            {"name": "저녁준비", "region_id": 0, "location_id": 2, "x": 90, "start": 1020 * _M, "end": 1110 * _M, "activity": "요리"},
            {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
            {"name": "정리", "region_id": 0, "location_id": 2, "x": 90, "start": 1170 * _M, "end": 1260 * _M, "activity": "정리"},
            {"name": "수면", "region_id": 0, "location_id": 9, "x": 120, "start": 1260 * _M, "end": 360 * _M, "activity": "수면"},  # 겨울: 일찍 잠
        ],
    }

    owner_unique_id = "mila"
    sleep_location = {"region_id": 0, "location_id": 9, "x": 120}  # 밀라방
    bath_location = {"region_id": 0, "location_id": 4, "x": 15}  # 욕실

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self._current_season = None
        # 초기 스케줄은 think()에서 계절 확인 후 설정

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
        if season != self._current_season:
            self._current_season = season
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
