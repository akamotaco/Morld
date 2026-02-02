# assets/characters/lina.py - 리나 캐릭터 Asset
#
# ============================================================
# 캐릭터 설정
# ============================================================
# 이름: 리나 (Lina)
# 성별: 여성
# 나이: 불명 (10대 후반~20대 초반으로 추정, 기억 없음)
#
# 외모:
#   - 금발 단발, 녹색 눈
#   - 작고 귀여운 인상
#   - 밝은 표정, 활기찬 분위기
#
# 성격:
#   - 명랑함: 항상 밝고 긍정적, 분위기 메이커
#   - 활발함: 가만히 있지 못함, 에너지가 넘침
#   - 호기심: 새로운 것에 관심이 많음
#   - 내면: 외로움을 잘 탐, 혼자 있으면 불안해함
#
# 좋아하는 것:
#   - 수다 떨기, 친구들과 노는 것
#   - 과일, 열매 (특히 딸기)
#   - 칭찬받는 것, 인정받는 것
#
# 싫어하는 것:
#   - 지루한 것, 심심한 상황
#   - 혼자 있는 것, 무시당하는 것
#   - 어려운 일, 복잡한 생각
#
# 취미:
#   - 채집 (열매, 약초 등)
#   - 빨래 (의외로 좋아함, 물장난 가능)
#   - 노래 부르기, 수다
#
# 과거사:
#   - 기억 없음. 눈을 떴을 때 저택 근처에 있었음
#   - 세라와 밀라를 만나 함께 지내게 됨
#   - 과거에 대해 별로 신경 안 씀 (지금이 재밌으니까!)
#
# 현재 배경:
#   - 저택 그룹의 막내 같은 존재
#   - 채집과 빨래를 담당
#   - 세라를 언니처럼 따르고 신뢰함
#   - 밀라와도 친하게 지냄
#
# 말투 특징:
#   - 반말, 친근한 어투
#   - "~야", "~거야?", "~자!" 등 활기찬 어미
#   - 이모티콘 느낌의 표현 (와아, 에헤헤, 흐흐)
#   - 물음표와 느낌표를 자주 사용
#
# 관계:
#   - 세라: 믿음직한 언니 같은 존재, 깊이 신뢰
#   - 밀라: 다정한 언니, 밥 잘 해줘서 좋아함
#   - 플레이어: 처음부터 친근하게 대함, 금방 친해짐
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


class Lina(Character):
    unique_id = "lina"
    name = "리나"
    type = "female"
    props = {
        "외모:금발": 1, "외모:단발": 1, "외모:녹색눈": 1,
        "성격:명랑함": 1, "성격:활발함": 1,
        "관계:세라:신뢰": 1,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 7,
        "can:sleep": 1,
        "can:bath": 1,
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
        "뭐하고 놀아?",
        "채집 방법",
    ]

    # ========================================
    # 대화 규칙 (주제별 조건 → 대사 또는 메서드명)
    # ========================================
    TALK_RULES = {
        "잡담": [
            # 특수 상황 (최우선)
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # Activity 기반
            ({"activity": "채집"}, {"pages": ["지금 채집 중이야!", "조금만 기다려~"]}),
            ({"activity": "빨래"}, {"pages": ["빨래 중이야~", "금방 끝나!"]}),
            ({"activity": "식사"}, {"pages": ["(맛있게 먹고 있다)", "냠냠... 뭐야?"]}),
            ({"activity": "휴식"}, {"pages": ["후아~ 오늘 피곤하다~", "...뭐야, 나도 놀아줄까?"]}),
            ({"activity": "준비"}, {"pages": ["잠깐만! 준비 중이야!", "..."]}),

            # 호감도 기반 (진척도 증가 로직 포함)
            ({"호감": 70}, "_talk_friendly_high"),
            ({"호감": 50}, "_talk_friendly_mid"),

            # mood 기반
            ({"mood": "기쁨"}, {"pages": ["오늘 기분 짱 좋아!", "같이 놀자!"]}),
            ({"mood": "슬픔"}, {"pages": ["...응?", "...아무것도 아니야."]}),

            # 기본값
            ({}, {"pages": ["응? 뭐야뭐야?", "...심심한 거야? 나도 좀 심심했는데!"]}),
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
                "나? 에헤헤~",
                "리나야! 여기서 채집이랑 빨래 담당하고 있어!",
                "세라 언니랑 밀라 언니랑 같이 살고 있거든~",
                "완전 재밌어! 매일매일 신나!",
            ]}),
            ({"호감": 50}, {"pages": [
                "나는 리나!",
                "열매 따고 빨래하고 그런 거 해~",
                "어때, 멋지지?",
            ]}),
            ({"호감": 30}, {"pages": [
                "응? 나?",
                "리나야~ 그것만 알면 돼!",
            ]}),

            # 기본값
            ({}, {"pages": ["왜 궁금해~?", "나중에 알려줄게!"]}),
        ],

        "뭐하고 놀아?": [
            # 특수 상황
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "뭐하고 노냐고?",
                "음~ 열매 따러 다니는 것도 좋아하고!",
                "빨래할 때 물장난 치는 것도 재밌어!",
                "아, 노래 부르는 것도 좋아해!",
                "같이 놀래? 뭐 할까뭐 할까?",
            ]}),
            ({"호감": 50}, {"pages": [
                "노는 거?",
                "숲에서 열매 따는 거 좋아해~",
                "가끔 혼자 노래도 부르고!",
                "같이 놀면 더 재밌을 것 같은데?",
            ]}),
            ({"호감": 30}, {"pages": [
                "놀기?",
                "어... 숲 돌아다니는 거?",
                "심심하면 같이 놀자!",
            ]}),

            # 기본값
            ({}, {"pages": ["놀 거 물어보는 거야?", "관심 있어? 에헤~"]}),
        ],

        "채집 방법": [
            # 특수 상황
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "채집? 내가 알려줄까?",
                "일단 숲에 가면 열매가 엄청 많아!",
                "빨간 열매는 맛있고, 파란 건 좀 신맛 나~",
                "버섯은 조심해야 해! 이상한 건 먹으면 안 돼!",
                "같이 가면 내가 알려줄게!",
            ]}),
            ({"호감": 50}, {"pages": [
                "채집?",
                "숲에 가면 열매가 많아~",
                "바구니 들고 가서 따면 돼!",
                "어렵지 않아!",
            ]}),
            ({"호감": 30}, {"pages": [
                "채집?",
                "그냥... 숲에 가서 따면 되는데?",
            ]}),

            # 기본값
            ({}, {"pages": ["채집 궁금해?", "음... 나중에!"]}),
        ],
    }

    # ========================================
    # Describe 규칙 (장소에서 보이는 묘사)
    # ========================================
    DESCRIBE_RULES = [
        # 이동 중
        ({"is_traveling": True, "activity": "채집"}, "{name}가 채집터로 향하고 있다."),
        ({"is_traveling": True, "activity": "빨래"}, "{name}가 빨래를 하러 이동 중이다."),
        ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),

        # Activity 기반
        ({"activity": "채집"}, "{name}가 채집 준비를 하고 있다."),
        ({"activity": "빨래"}, "{name}가 빨래를 널고 있다."),
        ({"activity": "식사"}, "{name}가 맛있게 밥을 먹고 있다."),
        ({"activity": "수면"}, "{name}가 새근새근 잠들어 있다."),
        ({"activity": "휴식"}, "{name}가 기지개를 켜며 쉬고 있다."),

        # 위치 기반
        ({"location": (0, 23)}, "{name}가 열매를 따고 있다."),
        ({"location": (0, 1)}, "{name}가 소파에 앉아 발을 흔들고 있다."),

        # 성욕 기반 (높은 성욕 우선) - 리나: 겉으론 밝지만 안절부절
        ({"성욕": 80}, "{name}가 어딘가 안절부절못하고 있다. 평소보다 말이 없다."),
        ({"성욕": 60}, "{name}가 자꾸 이쪽을 힐끔힐끔 쳐다본다. 뭔가 할 말이 있는 듯."),
        ({"성욕": 40}, "{name}가 조금 산만해 보인다. 집중을 못 하는 것 같다."),

        # 호감도/애정 기반 - 리나: 적극적으로 다가옴
        ({"애정": 80}, "{name}가 활짝 웃으며 손을 흔들고 있다. 눈에 하트가 가득하다."),
        ({"애정": 50}, "{name}가 반갑게 다가오며 팔짱을 끼려 한다."),
        ({"호감": 70}, "{name}가 신나게 손을 흔든다. \"여기야, 여기!\""),
        ({"호감": 50}, "{name}가 이쪽을 보며 환하게 웃는다."),

        # 기본값
        ({}, "{name}가 밝은 표정으로 주변을 둘러본다."),
    ]

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = [
        # Activity 기반
        ({"activity": "채집"}, "바구니를 들고 열심히 열매를 따고 있다."),
        ({"activity": "빨래"}, "콧노래를 흥얼거리며 빨래를 널고 있다."),
        ({"activity": "식사"}, "맛있게 음식을 먹고 있다."),
        ({"activity": "수면"}, "새근새근 잠들어 있다. 평화로운 얼굴이다."),
        ({"activity": "휴식"}, "기지개를 켜며 쉬고 있다."),

        # mood 기반
        ({"mood": "기쁨"}, "환하게 웃고 있다. 에너지가 넘쳐 보인다."),
        ({"mood": "슬픔"}, "평소와 달리 기운이 없어 보인다."),

        # 성욕 기반 (높은 성욕 우선) - 리나: 부끄러워하며 안절부절
        ({"성욕": 80}, "볼이 빨갛게 달아올라 있다. 시선을 어디 둬야 할지 모르는 듯 두리번거린다."),
        ({"성욕": 60}, "평소보다 말이 적다. 눈을 피하며 손가락을 만지작거린다."),
        ({"성욕": 40}, "어딘가 산만해 보인다. 집중하려 하지만 자꾸 딴 생각에 빠지는 듯."),

        # 애정/호감도 기반 - 리나: 적극적이고 애정 표현이 솔직함
        ({"애정": 80}, "눈이 하트처럼 반짝인다. 온몸으로 좋아하는 마음이 느껴진다."),
        ({"애정": 50}, "볼을 살짝 붉히며 수줍게 웃는다. \"에헤헤...\""),
        ({"호감": 70}, "당신을 보고 환하게 웃는다. 눈빛이 반짝반짝 빛난다."),
        ({"호감": 50}, "친근하게 손을 흔든다. 밝은 에너지가 느껴진다."),

        # 기본값
        ({}, "밝은 금발 단발머리의 활기찬 소녀. 녹색 눈이 반짝인다."),
    ]

    # ========================================
    # NPC 주도 설정 (리나: 활발하지만 연애엔 수줍음)
    # ========================================
    INITIATIVE_CONFIG = {
        "arousal_threshold": 65,      # 성욕 임계값 (세라와 비슷)
        "affection_threshold": 55,    # 호감도 임계값 (세라와 비슷)
        "cooldown_millis": 480 * _M,      # 쿨다운 8시간
    }

    # NPC 주도 시 허용 액션 필터
    # 리나는 활발하지만 연애엔 수줍어서 천천히 진행
    INITIATIVE_ACTION_FILTERS = [
        ({"애정": 70}, ["hug", "deep_kiss", "breast_touch"]),
        ({"애정": 45}, ["hug", "deep_kiss"]),
        ({}, ["hug"]),  # 기본: 포옹만
    ]

    # NPC 주도 중 반응 텍스트
    INITIATIVE_REACTIONS = {
        "start": [
            ({"성욕": 70}, ["...이리 와...", "...가만히 있어..."]),
            ({}, ["...저기...", "...잠깐만..."]),
        ],
        "during_hug": [
            ({"성욕": 50}, ["리나가 숨을 거칠게 몰아쉬며 안아온다."]),
            ({}, ["리나가 수줍게 안아온다.", "리나의 심장이 빠르게 뛴다."]),
        ],
        "during_deep_kiss": [
            ({"성욕": 60}, ["리나가 거친 숨을 몰아쉬며 키스를 이어간다."]),
            ({}, ["리나가 부끄러워하며 키스하고 있다."]),
        ],
        "during_breast_touch": [
            ({}, ["리나가 얼굴을 붉히며 눈을 감고 있다."]),
        ],
        "escape_fail": [
            ({}, ["...가지 마!", "...조금만 더..."]),
        ],
        "satisfied": [
            ({"애정": 50}, ["에헤헤... 좋아해...♡", "...행복해..."]),
            ({}, ["...고마워...", "...에헤헤..."]),
        ],
    }

    # ========================================
    # 은신 성공 반응 (리나: 무서워하면서도 두근두근)
    # ========================================
    # 리나는 활발하지만 들킬 뻔한 상황에 무서워하면서도 흥분
    STEALTH_REACTIONS = {
        "text": [
            ({"성욕": 50}, ["으앙...! 심장 터지는 줄 알았어...!", "...(심장을 쥐어짠다)"]),
            ({"애정": 40}, ["무...무서웠어...!", "다행이다..."]),
            ({}, ["히익...!", "...(심장이 두근두근)"]),
        ],
        "effects": {"호감": 1, "성욕": 3},  # 스릴에 두근거려서 호감/성욕 증가
    }

    # ========================================
    # 스킨십 반응 (action_id → timing → 조건부 대사 리스트)
    # 리나: 활발하고 명랑함, 부끄러워하면서도 즐거워함
    # ========================================
    ROMANCE_REACTIONS = {
        # 즉시형 행위
        "head_pat": {
            "start": [
                ({}, [
                    "에헤헤~ 좋아!",
                    "더 해줘!",
                    "간지러워~",
                    "나 어린애 아니거든?!",
                ]),
            ],
        },
        "cheek_caress": {
            "start": [
                ({}, [
                    "왜왜? 뭐 묻었어?",
                    "에헤헤~",
                    "간지러워!",
                    "손이 따뜻하다~",
                ]),
            ],
        },
        "cheek_pinch": {
            "start": [
                ({}, [
                    "아야야야!",
                    "왜 꼬집어!! 아파!",
                    "나빠~!",
                    "으으~ 그만해!",
                ]),
            ],
        },
        "ear_touch": {
            "start": [
                ({}, [
                    "꺄악! 거, 거기 안 돼!",
                    "간지러워어어!",
                    "왜 귀야!",
                    "...이상해...",
                ]),
            ],
        },
        "french_kiss": {
            "start": [
                ({}, [
                    "으응...♡",
                    "숨... 못 쉬어...",
                    "...더... 해도 돼...",
                    "심장이 막 뛰어...♡",
                ]),
            ],
        },
        "butt_caress": {
            "start": [
                ({}, [
                    "꺄악! 거, 거기는!!",
                    "변태야?!",
                    "...부끄러워...",
                    "누, 누가 볼라!",
                ]),
            ],
        },

        # 토글형 행위
        "hug": {
            "start": [
                ({"애정": 50}, ["...좋아해... 정말로...", "이대로 있자..."]),
                ({"호감": 80}, ["에헤헤~ 안아줘!", "포근해..."]),
                ({}, [
                    "와! 갑자기?",
                    "에헤헤~",
                    "따뜻해!",
                    "...좋아.",
                ]),
            ],
            "during": [
                ({"성욕": 50}, ["리나가 숨을 거칠게 몰아쉬며 안겨 있다."]),
                ({"성욕": 30}, ["리나의 심장이 빠르게 뛰는 게 느껴진다."]),
                ({"애정": 40}, ["리나가 행복한 표정으로 안겨 있다."]),
                ({}, [
                    "리나가 기분 좋게 안겨 있다.",
                    "리나의 따뜻한 체온이 느껴진다.",
                    "리나가 콧노래를 흥얼거린다.",
                    "리나가 품 안에서 꼼지락거린다.",
                ]),
            ],
        },
        "deep_kiss": {
            "start": [
                ({"성욕": 40}, ["...으응... 이상해...♡"]),
                ({"애정": 30}, ["...좋아해...♡"]),
                ({}, [
                    "...눈 감을게...",
                    "심장이 막 뛰어...",
                    "...키스...♡",
                ]),
            ],
            "during": [
                ({"성욕": 50}, ["리나가 몽롱한 눈으로 키스에 빠져 있다."]),
                ({"성욕": 30}, ["리나의 숨결이 거칠어진다."]),
                ({}, [
                    "리나와 깊은 키스를 나누고 있다.",
                    "리나가 눈을 꼭 감고 있다.",
                    "리나의 부드러운 입술이 느껴진다.",
                ]),
            ],
        },
        "breast_touch": {
            "start": [
                ({}, [
                    "꺄악! 거, 거기는...!",
                    "부, 부끄러워...!",
                    "...살살해...",
                ]),
            ],
            "during": [
                ({}, [
                    "리나가 얼굴을 붉히고 있다.",
                    "리나가 작은 신음을 흘린다.",
                    "리나가 당신의 손을 부끄럽게 바라본다.",
                    "리나가 눈을 질끈 감고 있다.",
                ]),
            ],
        },

        # 절정 반응
        "ecstasy": {
            "start": [
                ({}, [
                    "꺄아앙...!! ♡♡♡",
                    "이, 이상해... 머리가 하얘져...♡",
                    "...으으응...!! ♡♡",
                    "좋, 좋아해...!! ♡♡♡",
                ]),
            ],
        },
    }

    # ========================================
    # 이벤트 다이얼로그 정의
    # ========================================
    EVENT_DIALOGS = {
        "first_meet": {
            "pages": [
                "안녕! 넌 누구야?",
                "처음 보는 얼굴인데... 혹시 밖에서 온 거야?",
                "나는 리나! 여기서 채집을 맡고 있어!",
                "앞으로 잘 지내자~!"
            ],
        },
    }

    # 이벤트 플래그 (인스턴스별)
    _event_flags: dict

    def __init__(self):
        super().__init__()
        self._event_flags = {}

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

        # 첫 만남 여부 판정 (관계:리나:진척도 <= 0)
        if not self.is_first_meet(player_id):
            # NPC 주도 스킨십 체크 (첫 만남 이후에만)
            if self.should_initiate_skinship(player_id):
                from npc_initiative import start_npc_initiative
                return start_npc_initiative(player_id, self.instance_id)
            return None

        # 첫 만남 이벤트 - 완료 후 진척도 1로 설정
        return self._first_meet_handler(player_id)

    def _first_meet_handler(self, player_id):
        """첫 만남 이벤트 핸들러 - Generator"""
        # 대화 실행
        yield from self._run_event_dialog("first_meet", player_id=player_id)
        # 첫 만남 완료 처리 (관계:리나:진척도 = 1)
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
            morld.add_action_log("리나가 눈을 반짝이며 무기를 구경한다.")
        else:
            morld.add_action_log("리나가 빈 손을 보고 고개를 갸웃거린다.")

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
    # 사적인 대화 (진척도 시스템)
    # ========================================

    def _talk_friendly_high(self, context):
        """호감도 70 이상 - 진척도 증가 기회"""
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        # 진척도 증가 (최대 3)
        props = morld.get_unit_props(self.instance_id)
        progress_key = f"관계:{player_name}:진척도"
        current_progress = props.get(progress_key, 0) if props else 0

        if current_progress < 3:
            morld.set_unit_prop(self.instance_id, progress_key, current_progress + 1)

        yield ui.dialog([
            f"[{name}]",
            "야호! 왔구나!",
            "오늘 뭐 하고 놀까? 나 채집 끝났거든!",
            "아, 아니면 같이 산책할래? 숲이 진짜 예뻐!"
        ])

    def _talk_friendly_mid(self, context):
        """호감도 50 이상 - 진척도 증가 기회"""
        name = context.get("name", self.name)
        player_id = morld.get_player_id()
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"

        # 진척도 증가 (최대 3)
        props = morld.get_unit_props(self.instance_id)
        progress_key = f"관계:{player_name}:진척도"
        current_progress = props.get(progress_key, 0) if props else 0

        if current_progress < 3:
            morld.set_unit_prop(self.instance_id, progress_key, current_progress + 1)

        yield ui.dialog([
            f"[{name}]",
            "안녕안녕!",
            "뭐 재밌는 거 없어?",
            "나 심심했거든~"
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
            yield ui.dialog([f"[{name}]", "뭐야뭐야? 또 놀러 온 거야?", "좋아좋아! 환영!"])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield ui.dialog([
            f"[{name}]",
            "응? 나에 대해 알고 싶어?",
            "에헤헤, 좋아!",
            "나는 리나야! 여기서 채집이랑 빨래를 담당하고 있어!",
            "세라 언니랑 밀라 언니가 있는데...",
            "세라 언니는 되게 멋있어! 사냥도 잘하고, 진짜 강하거든!",
            "근데 좀 무서울 때도 있어... 말이 없어서...",
            "밀라 언니는 진짜 다정해! 맛있는 거 많이 해줘!",
            "...우리 셋이서 이 저택에서 살고 있어.",
            "가족 같은 거지!"
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
            yield ui.dialog([
                f"[{name}]",
                "오늘 날씨 진짜 좋다!",
                "같이 밖에 나갈래?"
            ])
            return

        # 플래그 설정
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield ui.dialog([
            f"[{name}]",
            "내가 좋아하는 거?",
            "음... 채집! 열매 따는 거 진짜 재밌어!",
            "숲에 가면 새소리도 들리고, 바람도 시원하고...",
            "혼자 있으면 좀 무섭긴 한데, 그래도 좋아!",
            "아, 그리고 밀라 언니가 해주는 베리 잼!",
            "달콤하고 맛있어~ 빵에 발라 먹으면 최고야!",
            "...",
            "그리고... 사람들이랑 노는 것도 좋아!",
            "혼자 있으면 심심하거든...",
            f"...{player_name}(이)랑 같이 있는 것도 좋아... 에헤헤."
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
            yield ui.dialog([
                f"[{name}]",
                "...",
                "...그냥 옛날 생각하고 있었어.",
                "아무것도 아니야!"
            ])
            return

        # 플래그 설정
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield ui.dialog([
            f"[{name}]",
            "...",
            "...옛날 이야기?",
            "...",
            "사실... 나도 기억이 별로 없어.",
            "어느 날 눈을 떴는데, 혼자였어.",
            "여기가 어딘지도 모르겠고, 내가 누군지도...",
            "무서웠어. 진짜 무서웠어...",
            "그러다가 세라 언니를 만났어.",
            "언니도 나처럼 혼자 있었대.",
            "그리고 밀라 언니도...",
            "우리 셋 다 아무것도 기억 못 해.",
            "그래서 셋이서 같이 살기로 했어.",
            "...",
            "무섭지 않아? 혼자가 아니니까.",
            f"...{player_name}(이)도 그렇지?",
            "...같이 있으면 괜찮아."
        ])


    # ========================================
    # 프라이버시 이벤트 (수면 시 방 퇴출)
    # ========================================

    def _on_room_privacy(self, player_id, activity):
        """리나가 수면/목욕 목적으로 도착했는데 플레이어가 있을 때"""
        props = morld.get_unit_props(self.instance_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"
        affection = props.get(f"관계:{player_name}:호감", 0) if props else 0
        info = morld.get_unit_info(self.instance_id)

        if activity == "수면":
            if affection >= 50:
                def handler():
                    yield ui.dialog([
                        "[리나]",
                        "앗, 여기 있었구나?",
                        "나 좀 졸린데... 같이 있어도 돼?"
                    ])
                return handler()
            else:
                def handler():
                    yield ui.dialog([
                        "[리나]",
                        "으으... 나 자야 하는데.",
                        "저기... 나가줄래?"
                    ])
                    morld.stand_up(player_id)
                    if info:
                        morld.set_unit_location(player_id, info["region_id"], 1, 120)
                    yield ui.dialog(["리나의 방에서 나왔다."])
                return handler()
        elif activity == "목욕":
            if affection >= 70:
                def handler():
                    yield ui.dialog([
                        "[리나]",
                        "꺄앗! 보, 보지 마...!",
                        "나, 나가줘... 제발..."
                    ])
                    morld.stand_up(player_id)
                    if info:
                        morld.set_unit_location(player_id, info["region_id"], 1, 120)
                    yield ui.dialog(["욕실에서 나왔다."])
                return handler()
            else:
                def handler():
                    yield ui.dialog([
                        "[리나]",
                        "...!!!",
                        "리나가 비명을 지르며 물건을 던졌다."
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
        리나 방 침대 반응 (깨어있을 때)
        - 호감도에 따라 반응만 달라짐 (내쫓지는 않음)
        """
        success = False
        if affection >= 50:
            yield ui.dialog([
                "[리나]",
                "에헤헤, 오빠도 누울래?"
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog([
                    "리나의 침대에 누웠다.",
                    "리나가 환하게 웃었다."
                ])
        elif affection >= 20:
            yield ui.dialog([
                "[리나]",
                "어... 오빠? 내 침대에...?"
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog([
                    "리나의 침대에 누웠다.",
                    "(리나가 어색하게 웃으며 비켜줬다.)"
                ])
        else:
            yield ui.dialog([
                "[리나]",
                "아, 네... 괜찮아요.",
                "(리나가 조금 긴장한 표정으로 비켜섰다.)"
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog(["리나의 침대에 누웠다."])

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
                yield ui.dialog(["손을 뻗어 리나의 가슴에 살짝 닿았다."])
                yield ui.dialog([
                    "[리나]",
                    "히잇...! 오, 오빠...!?",
                    "거, 거기는...!"
                ])
                yield ui.dialog([
                    "리나가 새빨개진 얼굴로 이불을 끌어당겼다.",
                    "...하지만 오빠의 손을 밀어내지는 않았다."
                ])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 리나의 엉덩이에 살짝 닿았다."])
                yield ui.dialog([
                    "[리나]",
                    "으앗...! 오빠 변태...!",
                    "...그래도 싫지는... 않아."
                ])
                yield ui.dialog([
                    "리나가 얼굴을 이불에 파묻었다.",
                    "귀까지 빨갛다."
                ])
            elif choice == "kiss":
                yield ui.dialog(["리나의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[리나]",
                    "오, 오빠...? 왜 그렇게 가까이..."
                ])
                yield ui.dialog(["리나의 이마에 가볍게 키스했다."])
                yield ui.dialog([
                    "[리나]",
                    "...!!",
                    "...에헤헤... 오빠..."
                ])
                yield ui.dialog([
                    "리나가 행복하게 눈을 감았다."
                ])
            elif choice == "hug":
                yield ui.dialog(["리나를 부드럽게 안아줬다."])
                yield ui.dialog([
                    "[리나]",
                    "...!",
                    "에헤헤... 오빠 따뜻해."
                ])
                yield ui.dialog([
                    "리나가 작은 몸을 꼭 안겨왔다.",
                    "심장 소리가 들린다."
                ])
        elif affection >= 20:
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 리나의 가슴에 닿으려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "으잇!? 오, 오빠...!?",
                    "그, 그건 좀...!"
                ])
                yield ui.dialog([
                    "리나가 당황해서 이불로 몸을 감쌌다.",
                    "...아직은 이르다."
                ])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 리나의 엉덩이에 닿으려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "엇, 오빠!?",
                    "그, 그런 건 안 돼요...!"
                ])
                yield ui.dialog(["리나가 후다닥 이불 속으로 들어갔다."])
            elif choice == "kiss":
                yield ui.dialog(["리나의 얼굴에 가까이 다가갔다."])
                yield ui.dialog([
                    "[리나]",
                    "으...! 가, 가까워...!",
                    "아직 마음의 준비가..."
                ])
                yield ui.dialog(["리나가 새빨갛게 달아올라 고개를 숙였다."])
            elif choice == "hug":
                yield ui.dialog(["리나를 살짝 안으려 했다."])
                yield ui.dialog([
                    "[리나]",
                    "어...! 오빠...?",
                    "...어색하지만... 싫지는 않아요."
                ])
                yield ui.dialog(["리나가 뻣뻣하게 안겨 있다."])
        else:
            # 호감도 낮을 때 - 놀라서 거부 (쫓아내지는 않음)
            if choice == "breast":
                yield ui.dialog(["손을 뻗어 리나의 가슴에 닿으려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "...!!! 저, 저기...!",
                    "그, 그런 건... 안 돼요..."
                ])
                yield ui.dialog(["리나가 겁먹은 표정으로 몸을 움츠렸다."])
            elif choice == "butt":
                yield ui.dialog(["손을 뻗어 리나의 엉덩이에 닿으려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "히잇...!",
                    "제, 제발 그러지 마세요..."
                ])
                yield ui.dialog(["리나가 떨리는 목소리로 부탁했다."])
            elif choice == "kiss":
                yield ui.dialog(["리나의 얼굴에 가까이 다가가려는 순간—"])
                yield ui.dialog([
                    "[리나]",
                    "으...! 너무 가까워요...!"
                ])
                yield ui.dialog(["리나가 얼굴을 가리며 뒤로 물러났다."])
            elif choice == "hug":
                yield ui.dialog(["리나를 안으려 했지만—"])
                yield ui.dialog([
                    "[리나]",
                    "어...! 저, 저는... 괜찮아요..."
                ])
                yield ui.dialog([
                    "리나가 긴장한 표정으로 살짝 몸을 피했다.",
                    "...아직은 친해지는 게 먼저인 것 같다."
                ])

    def on_bed_sleeping(self, bed, player_id, slot, affection, owner_id):
        """리나가 자고 있을 때 - 호감도별 묘사 + 행동 선택"""
        success = False
        if affection >= 50:
            yield ui.dialog([
                "리나가 곤히 잠들어 있다.",
                "작은 체구가 이불 속에 동그랗게 말려 있다."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog(["조심스럽게 옆에 누웠다."])
        elif affection >= 20:
            yield ui.dialog([
                "리나가 잠들어 있다.",
                "작은 입에서 잔잔한 숨소리가 새어 나온다."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog(["조심스럽게 옆에 누웠다."])
        else:
            yield ui.dialog([
                "리나가 잠들어 있다.",
                "...깨우면 놀라겠지."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog(["조용히 옆에 누웠다."])

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
            yield ui.dialog([
                "손을 뻗어 리나의 가슴에 살짝 닿았다.",
                "...작고 부드럽다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "리나가 잠결에 \"으응...\" 하고 작게 신음했다.",
                    "얼굴이 살짝 붉어졌다.",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "리나가 잠결에 움찔했다.",
                    "\"...오빠...?\"",
                    "...아직 잠꼬대인 것 같다."
                ])
        elif choice == "butt":
            yield ui.dialog([
                "손을 뻗어 리나의 엉덩이에 살짝 닿았다.",
                "...작고 동글동글하다."
            ])
            if affection >= 50:
                yield ui.dialog([
                    "리나가 잠결에 몸을 동그랗게 말았다.",
                    "\"음...\"",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "리나가 잠결에 살짝 몸을 떨었다.",
                    "...이 이상은 위험할 것 같다."
                ])
        elif choice == "kiss":
            yield ui.dialog(["리나의 얼굴에 가까이 다가갔다."])
            if affection >= 50:
                yield ui.dialog([
                    "잠든 리나의 이마에 살짝 키스했다.",
                    "리나가 잠결에 \"에헤헤...\" 하고 웃었다."
                ])
                yield ui.dialog([
                    "행복한 꿈을 꾸는 것 같다.",
                    "...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "잠든 리나의 이마에 가볍게 키스했다.",
                    "리나가 잠결에 \"음... 오빠...\" 하고 중얼거렸다."
                ])
                yield ui.dialog(["...잠꼬대인 것 같다."])


# ========================================
# AI Agent
# ========================================

@register_agent_class("lina")
class LinaAgent(BaseAgent):
    """
    리나 AI - 채집 + 빨래 담당

    특징:
    - 활발하고 명랑함
    - 채집과 빨래를 담당
    - 세라를 리더로 신뢰하고 따름
    - 플레이어 호감도 높으면 근처에 머무름
    """

    SCHEDULE = [
        # x: Location 내 목표 좌표 (Pi-World, 1unit/sec 기준)
        # terrain.md 참고: 리나방 침대(x=120), 식당 식탁(x=90), 뒷마당 length=600, 채집터 length=900, 거실 소파(x=210)
        {"name": "아침목욕", "region_id": 0, "location_id": 4, "x": 15, "start": 360 * _M, "end": 390 * _M, "activity": "목욕"},
        {"name": "기상", "region_id": 0, "location_id": 7, "x": 120, "start": 390 * _M, "end": 420 * _M, "activity": "준비"},
        {"name": "아침식사", "region_id": 0, "location_id": 3, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
        {"name": "빨래", "region_id": 0, "location_id": 13, "x": 300, "start": 480 * _M, "end": 540 * _M, "activity": "빨래"},  # 뒷마당
        {"name": "채집", "region_id": 0, "location_id": 23, "x": 450, "start": 540 * _M, "end": 720 * _M, "activity": "채집"},
        {"name": "점심식사", "region_id": 0, "location_id": 3, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
        {"name": "채집", "region_id": 0, "location_id": 23, "x": 450, "start": 840 * _M, "end": 1020 * _M, "activity": "채집"},
        {"name": "빨래걷기", "region_id": 0, "location_id": 13, "x": 300, "start": 1020 * _M, "end": 1080 * _M, "activity": "빨래"},  # 뒷마당
        {"name": "저녁식사", "region_id": 0, "location_id": 3, "x": 90, "start": 1110 * _M, "end": 1170 * _M, "activity": "식사"},
        {"name": "자유시간", "region_id": 0, "location_id": 1, "x": 210, "start": 1170 * _M, "end": 1320 * _M, "activity": "휴식"},
        {"name": "수면", "action": "stay", "start": 1320 * _M, "end": 360 * _M, "activity": "수면"},
    ]

    owner_unique_id = "lina"
    sleep_location = {"region_id": 0, "location_id": 7, "x": 120}  # 리나방
    bath_location = {"region_id": 0, "location_id": 4, "x": 15}  # 욕실

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self.SCHEDULE)


# ========================================
# 캐릭터 개인 퀘스트 (CHARACTER_QUESTS)
# ========================================
# 리나 관련 퀘스트는 캐릭터 파일에서 직접 정의

Lina.CHARACTER_QUESTS = [
    # ========================================
    # 편지 전달 퀘스트 (기존 side_quests에서 이동)
    # ========================================
    {
        "unique_id": "lina_letter",
        "name": "리나의 편지",
        "description": "리나가 세라에게 전해달라는 편지를 전달하자.",
        "category": "personal",

        "prerequisites": ["sub_meet_lina"],
        "giver": "lina",
        "reporter": "lina",

        "conditions": [
            {"type": "deliver", "item": "lina_letter", "target": "sera", "count": 1},
        ],

        "rewards": [
            {"type": "prop", "target": "player", "prop": "관계:리나:호감", "value": 10},
            {"type": "prop", "target": "player", "prop": "관계:세라:호감", "value": 3},
        ],

        "dialogs": {
            "offer": [
                "[리나]",
                "저기저기! 부탁 하나만!",
                "세라 언니한테 이 편지 전해줄 수 있어?",
                "직접 주기 좀 부끄러워서...",
            ],
            "accept": [
                "[리나]",
                "에헤헤~ 고마워!",
                "(리나에게서 편지를 받았다)",
            ],
            "decline": [
                "[리나]",
                "에에~ 왜...?",
                "(풀이 죽은 표정이다)",
            ],
            "progress": [
                "[리나]",
                "편지 전해줬어...?",
                "세라 언니가 뭐래...?",
            ],
            "complete": [
                "[리나]",
                "진짜!? 전해줬어!?",
                "세라 언니가 뭐래!?",
                "......",
                "...아무 말 없었어? 그래도 받긴 했지?",
                "에헤헤... 고마워!",
            ],
        },
    },

    # ========================================
    # 베리 채집 퀘스트
    # ========================================
    {
        "unique_id": "lina_berry",
        "name": "베리 채집 도우미",
        "description": "리나와 함께 숲에서 베리를 채집하자.",
        "category": "personal",

        "prerequisites": ["lina_letter"],
        "giver": "lina",
        "reporter": "lina",

        "conditions": [
            {"type": "collect", "item": "berry", "count": 10},
        ],

        "rewards": [
            {"type": "prop", "target": "player", "prop": "관계:리나:호감", "value": 8},
            {"type": "item", "item": "berry_jam", "count": 2},
        ],

        "dialogs": {
            "offer": [
                "[리나]",
                "저기! 같이 채집하러 갈래?",
                "베리를 10개만 모으면 잼을 만들 수 있어!",
                "밀라 언니가 만들어주거든!",
            ],
            "accept": [
                "[리나]",
                "야호! 같이 가자!",
                "숲에 베리나무가 많아!",
            ],
            "decline": [
                "[리나]",
                "에에... 알겠어...",
                "(풀이 죽은 표정이다)",
            ],
            "progress": [
                "[리나]",
                "베리 다 모았어?",
                "10개만 있으면 돼!",
            ],
            "complete": [
                "[리나]",
                "와! 다 모았다!",
                "(리나에게 베리 10개를 건넸다)",
                "밀라 언니한테 잼 만들어달라고 하자!",
                "...",
                "(잠시 후)",
                "(리나가 베리 잼을 가져왔다)",
                "짜잔! 베리 잼이야!",
                "에헤헤~ 맛있어!",
            ],
        },
    },

    # ========================================
    # 숨바꼭질 퀘스트 (미니게임 형식)
    # ========================================
    {
        "unique_id": "lina_hide_seek",
        "name": "숨바꼭질",
        "description": "리나와 숨바꼭질을 하자. 리나가 숨은 곳을 찾아야 한다.",
        "category": "personal",

        "prerequisites": ["lina_berry"],
        "giver": "lina",
        "reporter": "lina",

        "conditions": [
            {"type": "reach", "region_id": 0, "location_id": 7},  # 리나의 방
        ],

        "rewards": [
            {"type": "prop", "target": "player", "prop": "관계:리나:호감", "value": 12},
            {"type": "prop", "target": "player", "prop": "관계:리나:신뢰", "value": 1},
        ],

        "dialogs": {
            "offer": [
                "[리나]",
                "심심해~ 같이 놀자!",
                "숨바꼭질 할래?",
                "내가 숨을 테니까, 찾아봐!",
                "저택 안 어딘가에 숨을 거야~",
            ],
            "accept": [
                "[리나]",
                "좋아! 그럼 눈 감고 100까지 세!",
                "...에헤헤, 농담이야. 잠깐만 기다려!",
                "(리나가 어디론가 달려간다)",
            ],
            "decline": [
                "[리나]",
                "에에... 재미없어...",
            ],
            "progress": [
                "(리나가 어디 숨었는지 찾아야 한다)",
                "(저택 안을 둘러보자)",
            ],
            "complete": [
                "[리나]",
                "앗! 찾았다!",
                "(리나가 옷장에서 뛰어나온다)",
                "에헤헤~ 여기 숨은 거 어떻게 알았어?",
                "다음엔 더 좋은 데 숨을 거야!",
                "(리나가 재미있었다며 웃는다)",
            ],
        },
    },

    # ========================================
    # 리나의 신뢰 퀘스트
    # ========================================
    {
        "unique_id": "lina_trust",
        "name": "리나의 신뢰",
        "description": "리나와 더 친해지자.",
        "category": "personal",

        "prerequisites": ["lina_hide_seek"],
        "giver": None,
        "reporter": "lina",

        "conditions": [
            {"type": "prop", "target": "player", "prop": "관계:리나:호감", "min_value": 70},
        ],

        "rewards": [
            {"type": "item", "item": "lina_bracelet", "count": 1},
            {"type": "prop", "target": "player", "prop": "관계:리나:신뢰", "value": 1},
        ],

        "dialogs": {
            "complete": [
                "[리나]",
                "저기저기...!",
                "이거! 받아!",
                "(리나가 손목에서 팔찌를 푼다)",
                "내가 만든 거야!",
                "못생겼지만... 진심이야!",
                "...앞으로도 같이 있어 줄 거지?",
                "(리나가 뾰로통하지만 기대하는 눈으로 바라본다)",
            ],
        },
    },
]
