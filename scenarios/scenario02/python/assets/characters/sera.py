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
from assets.base import Character
from think import BaseAgent, register_agent_class


class Sera(Character):
    unique_id = "sera"
    name = "세라"
    type = "female"
    props = {
        "외모:흑발": 1, "외모:장발": 1, "외모:갈색눈": 1,
        "성격:과묵함": 1, "성격:듬직함": 1, "성격:리더십": 1,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 5,
    }
    actions = [
        "call:talk:대화",
        "call:errand:심부름#",         # 퀘스트 제안 가능 시만 표시
        "call:date:데이트 신청#",      # 데이트 중 아닐 때만 표시
        "call:end_date:데이트 종료#",  # 데이트 중일 때만 표시
        "call:hold_hands:손 잡기#",    # 조건 충족 시만 표시
        "call:date_hug:안아주기#",     # 조건 충족 시만 표시
        "call:date_kiss:키스#",        # 조건 충족 시만 표시
        "call:romance:스킨십",
        "call:debug_props*:속성 보기",
        "call:debug_affection_up*:호감도 +10",
        "call:debug_affection_down*:호감도 -10",
        "call:debug_arousal_up*:성욕 +20",
        "call:debug_arousal_down*:성욕 -20",
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
    DESCRIBE_RULES = [
        # 이동 중
        ({"is_traveling": True, "activity": "사냥"}, "{name}가 사냥터로 향하고 있다."),
        ({"is_traveling": True, "activity": "순찰"}, "{name}가 순찰을 위해 이동 중이다."),
        ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),

        # Activity 기반
        ({"activity": "사냥"}, "{name}가 활을 점검하고 있다."),
        ({"activity": "순찰"}, "{name}가 주변을 경계하고 있다."),
        ({"activity": "식사"}, "{name}가 조용히 식사 중이다."),
        ({"activity": "수면"}, "{name}가 조용히 잠들어 있다."),
        ({"activity": "휴식"}, "{name}가 벽에 기대어 쉬고 있다."),
        ({"activity": "정비"}, "{name}가 장비를 손보고 있다."),

        # 날씨 반응
        ({"weather": "비", "is_indoor": False}, "{name}가 비를 맞으며 서 있다."),

        # 위치 기반 (region_id, location_id)
        ({"location": (0, 24)}, "{name}가 사냥감을 추적하고 있다."),
        ({"location": (0, 12)}, "{name}가 앞마당을 순찰하고 있다."),
        ({"location": (0, 1)}, "{name}가 창가에 서서 밖을 바라본다."),

        # 성욕 기반 (높은 성욕 우선)
        ({"성욕": 80}, "{name}가 안절부절못하며 서 있다. 무언가 참고 있는 듯하다."),
        ({"성욕": 60}, "{name}가 평소보다 자주 이쪽을 힐끔거린다."),
        ({"성욕": 40}, "{name}가 조용히 서 있지만, 어딘가 불안해 보인다."),

        # 호감도/애정 기반
        ({"애정": 80}, "{name}가 곁에 다가와 가만히 서 있다. 눈빛이 부드럽다."),
        ({"애정": 50}, "{name}가 슬쩍 옆에 선다. 평소보다 거리가 가깝다."),
        ({"호감": 70}, "{name}가 이쪽을 보며 희미하게 고개를 끄덕인다."),
        ({"호감": 50}, "{name}가 경계하지 않는 눈으로 이쪽을 본다."),

        # 기본값
        ({}, "{name}가 과묵하게 서 있다."),
    ]

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = [
        # Activity 기반
        ({"activity": "사냥"}, "활을 들고 날카로운 눈으로 주변을 살핀다."),
        ({"activity": "순찰"}, "날카로운 눈으로 주변을 경계하고 있다."),
        ({"activity": "식사"}, "조용히 음식을 먹고 있다."),
        ({"activity": "수면"}, "경계심 없이 잠들어 있다."),
        ({"activity": "정비"}, "활과 화살을 꼼꼼히 점검하고 있다."),

        # mood 기반
        ({"mood": "기쁨"}, "표정 변화는 적지만, 눈가가 부드러워졌다."),
        ({"mood": "슬픔"}, "평소보다 더 말이 없다. 어딘가 먼 곳을 보고 있다."),
        ({"mood": "분노"}, "날카로운 눈빛이 더욱 차갑다."),

        # 성욕 기반 (높은 성욕 우선) - 세라: 참으려 하지만 티가 남
        ({"성욕": 80}, "얼굴이 살짝 붉어져 있다. 숨결이 평소보다 거칠고, 눈을 제대로 마주치지 못한다."),
        ({"성욕": 60}, "뭔가 신경 쓰이는 듯, 계속 시선을 피한다. 귀 끝이 붉다."),
        ({"성욕": 40}, "평소와 같아 보이지만, 가끔 멍하니 어딘가를 바라본다."),

        # 애정/호감도 기반 - 세라: 과묵하지만 눈빛으로 표현
        ({"애정": 80}, "눈빛이 많이 부드러워졌다. 무뚝뚝하지만 곁에 있으면 안심되는 표정이다."),
        ({"애정": 50}, "입은 다물고 있지만, 눈이 따뜻하게 이쪽을 보고 있다."),
        ({"호감": 70}, "눈빛이 조금 부드러워진 것 같다. 경계심이 많이 풀렸다."),
        ({"호감": 50}, "날카로운 눈매지만, 적대적이지 않다."),

        # 기본값
        ({}, "긴 흑발을 묶은 과묵한 여성. 저택의 리더로서 날카로운 갈색 눈이 인상적이다."),
    ]

    # ========================================
    # 스킨십 반응 (action_id → timing → 조건부 대사 리스트)
    # 세라: 과묵하지만 속으론 부끄러워함
    # ========================================
    ROMANCE_REACTIONS = {
        # 즉시형 행위
        "head_pat": {
            "start": [
                ({}, [
                    "......",
                    "...뭐하는 거냐.",
                    "...싫진 않다.",
                    "...그만해.",
                ]),
            ],
        },
        "cheek_caress": {
            "start": [
                ({}, [
                    "......",
                    "...간지럽다.",
                    "...뭐냐.",
                    "...손이 차군.",
                ]),
            ],
        },
        "cheek_pinch": {
            "start": [
                ({}, [
                    "...아파.",
                    "......",
                    "...뭐하는 짓이냐.",
                    "...죽고 싶냐.",
                ]),
            ],
        },
        "ear_touch": {
            "start": [
                ({}, [
                    "...!",
                    "...거기는... 만지지 마.",
                    "......(귀가 빨개진다)",
                    "...그만둬.",
                ]),
            ],
        },
        "french_kiss": {
            "start": [
                ({}, [
                    "...으응...",
                    "......(눈을 감는다)",
                    "...숨이...",
                    "...더...",
                ]),
            ],
        },
        "whisper": {
            "start": [
                ({"애정": 70}, [
                    "......(귀가 빨개진다)",
                    "...나도...",
                    "...바보.",
                ]),
                ({"애정": 50}, [
                    "......",
                    "...뭐라고?",
                    "...갑자기...",
                ]),
                ({}, [
                    "...뭐냐.",
                    "......",
                    "...시끄럽다.",
                ]),
            ],
        },
        "butt_caress": {
            "start": [
                ({}, [
                    "......!",
                    "...죽고 싶냐.",
                    "...거기는...",
                    "......(노려본다)",
                ]),
            ],
        },

        # 토글형 행위
        "hug": {
            "start": [
                ({"애정": 50}, ["...안아줘...", "...이대로 있자..."]),
                ({"호감": 80}, ["...좋다...", "...따뜻하군..."]),
                ({}, [
                    "......",
                    "...뭐냐.",
                    "...싫진 않다.",
                    "...놓아라.",
                ]),
            ],
            "during": [
                ({"성욕": 50}, ["세라의 심장이 빠르게 뛰는 게 느껴진다."]),
                ({"성욕": 30}, ["세라가 숨을 고르고 있다."]),
                ({"애정": 40}, ["세라가 조용히 안겨 있다."]),
                ({}, [
                    "세라가 뻣뻣하게 서 있다.",
                    "세라의 체온이 느껴진다.",
                    "세라가 가만히 있다.",
                    "세라가 어색하게 서 있다.",
                ]),
            ],
        },
        "deep_kiss": {
            "start": [
                ({"성욕": 40}, ["...으응... 더..."]),
                ({"애정": 30}, ["......(눈을 감는다)"]),
                ({}, [
                    "......",
                    "...키스...",
                    "...눈 감아.",
                ]),
            ],
            "during": [
                ({"성욕": 50}, ["세라가 거칠게 숨을 몰아쉬며 키스에 빠져 있다."]),
                ({"성욕": 30}, ["세라의 숨결이 거칠어진다."]),
                ({}, [
                    "세라와 깊은 키스를 나누고 있다.",
                    "세라가 눈을 감고 있다.",
                    "세라의 입술이 느껴진다.",
                ]),
            ],
        },
        "breast_touch": {
            "start": [
                ({}, [
                    "......!",
                    "...거기는...",
                    "...뭐하는...",
                ]),
            ],
            "during": [
                ({}, [
                    "세라가 고개를 돌리고 있다.",
                    "세라의 숨소리가 거칠어진다.",
                    "세라가 참고 있다.",
                    "세라의 귀가 빨갛다.",
                ]),
            ],
        },

        # 절정 반응
        "ecstasy": {
            "start": [
                ({}, [
                    "......!!",
                    "...으... 응...!",
                    "...(떨리고 있다)",
                    "...이상해...",
                ]),
            ],
        },
    }

    # ========================================
    # NPC 주도 스킨십 설정
    # ========================================
    INITIATIVE_CONFIG = {
        "arousal_threshold": 70,      # 성욕 70 이상
        "affection_threshold": 60,    # 호감도 60 이상
        "cooldown_minutes": 480,      # 8시간 쿨다운
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
        ({"애정": 80}, ["hug", "deep_kiss", "breast_touch"]),  # 애정 80 이상: 모든 행위
        ({"애정": 40}, ["hug", "deep_kiss"]),                   # 애정 40 이상: 키스까지
        ({}, ["hug"]),                                          # 기본: 포옹만
    ]

    # ========================================
    # 은신 성공 반응 (세라: 스릴에 흥분)
    # ========================================
    # 세라는 무뚝뚝하지만 위험한 상황에서 스릴을 느끼는 타입
    STEALTH_REACTIONS = {
        "text": [
            ({"성욕": 50}, ["...위험했어...", "...(숨을 거칠게 몰아쉰다)"]),
            ({"애정": 40}, ["......", "...조심해."]),
            ({}, ["......", "...(긴장한 표정)"]),
        ],
        "effects": {"성욕": 5},  # 스릴에 더 흥분
    }

    # ========================================
    # 이벤트 다이얼로그 정의
    # ========================================
    EVENT_DIALOGS = {
        "first_meet": {
            "pages": ["......", "...일어났군.", "...세라다. 사냥을 맡고 있다.", "...무리하지 마라."],
            "follow_duration": 2,  # 대화 후 2분간 플레이어 따라가기
        },
    }

    # 이벤트 플래그 (인스턴스별)
    _event_flags: dict

    def __init__(self):
        super().__init__()
        self._event_flags = {}

    # ========================================
    # 복잡한 대화 메서드 (Generator)
    # TALK_RULES에서 "_메서드명"으로 위임됨
    # ========================================

    def _talk_hunt_friendly(self, context):
        """사냥 중 + 호감 50 이상: 같이 사냥 제안"""
        name = context.get("name", self.name)

        choice = yield morld.dialog(
            f"[{name}]\n"
            "...같이 사냥할래?\n\n"
            "[url=@ret:yes]같이 가겠다[/url]\n"
            "[url=@ret:no]괜찮다[/url]",
            autofill="off"
        )

        if choice == "yes":
            yield morld.dialog([f"[{name}]", "...조용히만 해."])
            # 플레이어를 따라다니기 (30분)
            player_id = morld.get_player_id()
            morld.set_npc_job(self.instance_id, "follow", 30, player_id)
        else:
            yield morld.dialog([f"[{name}]", "...그래."])

    def _talk_patrol_friendly(self, context):
        """순찰 중 + 호감 50 이상: 같이 순찰 제안"""
        name = context.get("name", self.name)

        choice = yield morld.dialog(
            f"[{name}]\n"
            "...순찰 중이다.\n"
            "...같이 돌아볼래?\n\n"
            "[url=@ret:yes]같이 가겠다[/url]\n"
            "[url=@ret:no]괜찮다[/url]",
            autofill="off"
        )

        if choice == "yes":
            yield morld.dialog([f"[{name}]", "...따라와."])
            # 플레이어를 따라다니기 (60분)
            player_id = morld.get_player_id()
            morld.set_npc_job(self.instance_id, "follow", 60, player_id)
        else:
            yield morld.dialog([f"[{name}]", "...알았다."])

    # ========================================
    # 진척도 기반 대화 (일회성)
    # ========================================

    def _talk_friendly_mid(self, context):
        """호감도 50+ 일반 대화 - 진척도 증가"""
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        # 진척도 증가 (최대 3까지)
        props = morld.get_unit_props(self.instance_id)
        current_progress = props.get(f"관계:{player_name}:진척도", 0) if props else 0
        if current_progress < 3:
            morld.modify_prop(self.instance_id, f"관계:{player_name}:진척도", 1)

        yield morld.dialog([f"[{name}]", "......", "...무슨 일이야?"])

    def _talk_friendly_high(self, context):
        """호감도 70+ 일반 대화 - 진척도 증가"""
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        # 진척도 증가 (최대 3까지)
        props = morld.get_unit_props(self.instance_id)
        current_progress = props.get(f"관계:{player_name}:진척도", 0) if props else 0
        if current_progress < 3:
            morld.modify_prop(self.instance_id, f"관계:{player_name}:진척도", 1)

        yield morld.dialog([f"[{name}]", "......", "...뭐, 괜찮아?"])

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
            yield morld.dialog([f"[{name}]", "......", "...무슨 일이야?"])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)

        yield morld.dialog([
            f"[{name}]",
            "......",
            "...내 이름은 세라.",
            "...이 저택에서 사냥과 경비를 맡고 있다.",
            "...밀라와 리나도 여기 있지.",
            "......",
            "...그게 다야.",
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
            yield morld.dialog([f"[{name}]", "......", "...뭐, 괜찮아?"])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)

        yield morld.dialog([
            f"[{name}]",
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
            yield morld.dialog([f"[{name}]", "......", "...뭐, 괜찮아?"])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)

        yield morld.dialog([
            f"[{name}]",
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
        ])

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 만났을 때 - Generator 기반"""
        unit_info = morld.get_unit_info(self.instance_id)

        # 수면 중이면 반응 없음
        if unit_info and unit_info.get("activity") == "수면":
            return None

        # 첫 만남 여부 판정 (관계:세라:진척도 <= 0)
        if not self.is_first_meet(player_id):
            # NPC 주도 스킨십 체크 (첫 만남 이후에만)
            if self.should_initiate_skinship(player_id):
                # 쿨다운 기록
                self.mark_initiative_cooldown()
                # NPC 주도 시작
                from npc_initiative import start_npc_initiative
                return start_npc_initiative(player_id, self.instance_id)
            return None

        # 첫 만남 이벤트 - 완료 후 진척도 1로 설정
        return self._first_meet_handler(player_id)

    def _first_meet_handler(self, player_id):
        """첫 만남 이벤트 핸들러 - Generator"""
        # 대화 실행
        yield from self._run_event_dialog("first_meet", player_id=player_id)
        # 첫 만남 완료 처리 (관계:세라:진척도 = 1)
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
            morld.add_action_log("세라가 무기를 힐끗 보더니 고개를 끄덕인다.")
        else:
            morld.add_action_log("세라가 빈 손을 보고 살짝 고개를 갸웃한다.")

        return None

    # ========================================
    # 스킨십 반응
    # ========================================

    def get_romance_reaction(self, action_id: str, timing: str) -> str:
        """스킨십 행위에 대한 반응 텍스트 반환"""
        import random

        action_reactions = self.ROMANCE_REACTIONS.get(action_id)
        if not action_reactions:
            return None

        reactions = action_reactions.get(timing)
        if not reactions:
            return None

        props = morld.get_unit_props(self.instance_id)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get('name', '주인공') if player_info else '주인공'

        candidates = []
        for item in reactions:
            if isinstance(item, tuple) and len(item) == 2:
                condition, texts = item
                if self._check_romance_condition(condition, props, player_name):
                    if isinstance(texts, list):
                        candidates.extend(texts)
                    else:
                        candidates.append(texts)

        if not candidates:
            return None

        return random.choice(candidates)

    def _check_romance_condition(self, condition: dict, props: dict, player_name: str) -> bool:
        """조건 딕셔너리 체크"""
        if not condition:
            return True

        for key, required_value in condition.items():
            if key in ("호감", "애정"):
                prop_key = f"관계:{player_name}:{key}"
            elif key in ("성욕", "성적절정"):
                prop_key = f"상태:{key}"
            else:
                prop_key = key

            actual_value = props.get(prop_key, 0)
            if actual_value < required_value:
                return False

        return True

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

    SCHEDULE = [
        {"name": "기상", "region_id": 0, "location_id": 8, "start": 300, "end": 360, "activity": "준비"},
        {"name": "아침순찰", "region_id": 0, "location_id": 12, "start": 360, "end": 420, "activity": "순찰"},  # 앞마당
        {"name": "아침식사", "region_id": 0, "location_id": 3, "start": 420, "end": 480, "activity": "식사"},
        {"name": "사냥", "region_id": 0, "location_id": 24, "start": 540, "end": 720, "activity": "사냥"},
        {"name": "점심식사", "region_id": 0, "location_id": 3, "start": 720, "end": 780, "activity": "식사"},
        {"name": "사냥", "region_id": 0, "location_id": 24, "start": 840, "end": 1020, "activity": "사냥"},
        {"name": "저녁순찰", "region_id": 0, "location_id": 20, "start": 1020, "end": 1080, "activity": "순찰"},  # 숲 입구
        {"name": "저녁식사", "region_id": 0, "location_id": 3, "start": 1110, "end": 1170, "activity": "식사"},
        {"name": "장비정비", "region_id": 0, "location_id": 8, "start": 1200, "end": 1290, "activity": "정비"},
        {"name": "수면", "region_id": 0, "location_id": 8, "start": 1290, "end": 300, "activity": "수면"},
    ]

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self.SCHEDULE)

    def think(self):
        """세라의 행동 결정 - 스케줄 기반 Job 채우기"""
        schedule = self.get_current_schedule()
        self.fill_schedule_jobs_from(schedule)
        return None


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
