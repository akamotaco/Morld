# assets/characters/yuki.py - 유키 캐릭터 Asset
#
# Rule-based 텍스트 선택 시스템 사용
# - TALK_RULES: 대화 규칙
# - DESCRIBE_RULES: 장소에서 보이는 묘사 규칙
# - FOCUS_RULES: 클릭했을 때 상세 묘사 규칙

import morld
from assets.base import Character
from think import BaseAgent, register_agent_class


class Yuki(Character):
    unique_id = "yuki"
    name = "유키"
    type = "female"
    props = {
        "외모:은발": 1, "외모:장발": 1, "외모:붉은눈": 1,
        "성격:수줍음": 1, "성격:얌전함": 1,
        "관계:엘라:의지": 1,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 5,
    }
    actions = [
        "call:talk:대화",
        "call:errand:심부름#",         # 퀘스트 제안 가능 시만 표시
        "call:romance:스킨십",
        "call:debug_props*:속성 보기",
        "call:debug_affection_up*:호감도 +10",
        "call:debug_affection_down*:호감도 -10",
    ]
    mood = []

    # ========================================
    # 대화 규칙 (조건 → 대사 또는 메서드명)
    # ========================================
    TALK_RULES = [
        # 특수 상황 (최우선)
        ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

        # 진척도별 사적인 대화 (플래그로 일회성 체크)
        # 진척도 3 - 과거 이야기
        ({"호감": 70, "진척도": 3}, "_talk_progress_3"),
        # 진척도 2 - 좋아하는 것
        ({"호감": 60, "진척도": 2}, "_talk_progress_2"),
        # 진척도 1 - 자신에 대해
        ({"호감": 50, "진척도": 1}, "_talk_progress_1"),

        # Activity 기반
        ({"activity": "청소"}, {"pages": ["...청소 중이에요...", "..."]}),
        ({"activity": "빨래"}, {"pages": ["...빨래를 널고 있어요...", "...조금만 기다려 주세요..."]}),
        ({"activity": "식사"}, {"pages": ["(조용히 먹고 있다)", "...맛있어요..."]}),
        ({"activity": "휴식"}, {"pages": ["(책을 읽고 있다)", "...아, 네..."]}),
        ({"activity": "준비"}, {"pages": ["...지금 준비 중이에요...", "..."]}),

        # 호감도 기반 (진척도 증가 로직 포함)
        ({"호감": 70}, "_talk_friendly_high"),
        ({"호감": 50}, "_talk_friendly_mid"),

        # mood 기반
        ({"mood": "기쁨"}, {"pages": ["...네...", "...(희미하게 웃는다)"]}),
        ({"mood": "슬픔"}, {"pages": ["............", "..."]}),

        # 기본값
        ({}, {"pages": ["...네?", "...무슨 일이세요...?"]}),
    ]

    # ========================================
    # Describe 규칙 (장소에서 보이는 묘사)
    # ========================================
    DESCRIBE_RULES = [
        # 이동 중
        ({"is_traveling": True}, "{name}(이)가 조용히 어딘가로 향하고 있다."),

        # Activity 기반
        ({"activity": "청소"}, "{name}가 조용히 청소하고 있다."),
        ({"activity": "빨래"}, "{name}가 빨래를 널고 있다."),
        ({"activity": "식사"}, "{name}가 조용히 식사 중이다."),
        ({"activity": "수면"}, "{name}가 새근새근 잠들어 있다."),
        ({"activity": "휴식"}, "{name}가 책을 읽고 있다."),

        # 위치 기반
        ({"location": (0, 4)}, "{name}가 욕실을 청소하고 있다."),
        ({"location": (0, 1)}, "{name}가 소파 구석에 앉아 책을 읽고 있다."),
        ({"location": (2, 5)}, "{name}가 조용히 앉아 있다."),  # 도심 은신처

        # 성욕 기반 (높은 성욕 우선) - 유키: 말없이 다가오는 타입
        ({"성욕": 80}, "{name}가 말없이 곁에 다가와 있다. 귀와 볼이 새빨갛다."),
        ({"성욕": 60}, "{name}가 계속 이쪽을 쳐다본다. 눈을 마주치면 황급히 피한다."),
        ({"성욕": 40}, "{name}가 평소보다 어딘가 안절부절못하고 있다."),

        # 호감도/애정 기반 - 유키: 조용히 곁에 있으려 함
        ({"애정": 80}, "{name}가 살며시 옆에 서 있다. 눈빛이 따뜻하다."),
        ({"애정": 50}, "{name}가 가까이 있다. 존재만으로 안심하는 표정이다."),
        ({"호감": 70}, "{name}가 슬쩍 이쪽을 본다. 고개를 살짝 끄덕인다."),
        ({"호감": 50}, "{name}가 경계하지 않는 눈으로 이쪽을 본다."),

        # 기본값
        ({}, "{name}가 조용히 서 있다."),
    ]

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = [
        # Activity 기반
        ({"activity": "청소"}, "열심히 청소하고 있다."),
        ({"activity": "빨래"}, "빨래를 정성스럽게 널고 있다."),
        ({"activity": "식사"}, "조용히 음식을 먹고 있다."),
        ({"activity": "수면"}, "새근새근 잠들어 있다. 인형 같다."),
        ({"activity": "휴식"}, "조용히 책을 읽고 있다."),

        # mood 기반
        ({"mood": "기쁨"}, "살짝 볼이 붉어지며 희미하게 웃는다."),
        ({"mood": "슬픔"}, "고개를 숙이고 있다. 말을 걸기 어려워 보인다."),

        # 성욕 기반 (높은 성욕 우선) - 유키: 내성적이라 더 티가 남
        ({"성욕": 80}, "얼굴 전체가 붉어져 있다. 입술을 달싹이지만 말이 나오지 않는 듯."),
        ({"성욕": 60}, "평소보다 시선이 자주 마주친다. 볼과 귀가 빨갛다."),
        ({"성욕": 40}, "어딘가 초조해 보인다. 손으로 옷자락을 꼭 쥐고 있다."),

        # 애정/호감도 기반 - 유키: 신뢰와 의지
        ({"애정": 80}, "붉은 눈에 신뢰가 가득하다. 조용하지만 깊은 애정이 느껴진다."),
        ({"애정": 50}, "눈이 마주치자 살짝 미소 짓는다. 마음을 열고 있다."),
        ({"호감": 70}, "당신을 보고 살짝 미소 짓는다. 경계심이 풀렸다."),
        ({"호감": 50}, "눈을 피하지 않는다. 조금씩 마음을 열고 있는 듯하다."),

        # 기본값
        ({}, "은빛 긴 머리의 조용한 소녀. 붉은 눈이 신비로운 느낌을 준다."),
    ]

    # ========================================
    # NPC 주도 설정 (유키: 매우 수줍음 - 높은 임계값)
    # ========================================
    INITIATIVE_CONFIG = {
        "arousal_threshold": 80,      # 성욕 임계값 (세라보다 높음 - 더 소극적)
        "affection_threshold": 70,    # 호감도 임계값 (세라보다 높음)
        "cooldown_minutes": 720,      # 쿨다운 12시간 (가장 김)
    }

    # NPC 주도 시 허용 액션 필터
    # 유키는 매우 수줍어서 애정 높아도 제한적
    INITIATIVE_ACTION_FILTERS = [
        ({"애정": 85}, ["hug", "deep_kiss"]),  # 세라보다 높은 조건, breast_touch 없음
        ({"애정": 60}, ["hug"]),
        ({}, ["hug"]),  # 기본: 포옹만
    ]

    # NPC 주도 중 반응 텍스트
    INITIATIVE_REACTIONS = {
        "start": [
            ({"성욕": 80}, ["......", "...(말없이 다가온다)"]),
            ({}, ["......", "...저기요..."]),
        ],
        "during_hug": [
            ({"성욕": 60}, ["유키가 떨리는 숨을 내쉬며 안아온다."]),
            ({}, ["유키가 조용히 안아온다.", "유키의 심장 소리가 들린다."]),
        ],
        "during_deep_kiss": [
            ({"성욕": 70}, ["유키가 거친 숨을 몰아쉬며 키스를 이어간다."]),
            ({}, ["유키가 떨리며 키스하고 있다."]),
        ],
        "escape_fail": [
            ({}, ["...(말없이 붙잡는다)", "...가지 마세요..."]),
        ],
        "satisfied": [
            ({"애정": 60}, ["...좋아해요...", "...행복해요..."]),
            ({}, ["...고마워요...", "..."]),
        ],
    }

    # ========================================
    # 은신 성공 반응 (유키: 무서워서 움츠러듦)
    # ========================================
    # 유키는 수줍고 겁이 많아서 들킬 뻔한 상황에 크게 무서워함
    STEALTH_REACTIONS = {
        "text": [
            ({"성욕": 50}, ["...으으... 무서웠어요...", "...(몸을 떨고 있다)"]),
            ({"애정": 40}, ["...다행이에요...", "...(작게 안도한다)"]),
            ({}, ["...!", "...(숨을 죽인다)"]),
        ],
        "effects": {"호감": 2},  # 무서워서 더 의지하게 됨
    }

    # ========================================
    # 스킨십 반응 (action_id → timing → 조건부 대사 리스트)
    # 유키: 수줍고 내성적, 조용히 받아들이지만 속으론 기뻐함
    # ========================================
    ROMANCE_REACTIONS = {
        # 즉시형 행위
        "head_pat": {
            "start": [
                ({}, [
                    "...네...",
                    "...(고개를 살짝 숙인다)",
                    "...좋아요...",
                    "...부끄러워요...",
                ]),
            ],
        },
        "cheek_caress": {
            "start": [
                ({}, [
                    "...앗...",
                    "...따뜻해요...",
                    "...(볼이 붉어진다)",
                    "...네...",
                ]),
            ],
        },
        "cheek_pinch": {
            "start": [
                ({}, [
                    "...앗... 아파요...",
                    "...(눈물이 맺힌다)",
                    "...왜요...?",
                    "...그만해 주세요...",
                ]),
            ],
        },
        "ear_touch": {
            "start": [
                ({}, [
                    "...! 거, 거기는...",
                    "...이상해요...",
                    "...(몸을 떤다)",
                    "...앗...",
                ]),
            ],
        },
        "french_kiss": {
            "start": [
                ({}, [
                    "...으응...",
                    "...숨이...",
                    "...(눈을 꼭 감는다)",
                    "...더...요...",
                ]),
            ],
        },
        "butt_caress": {
            "start": [
                ({}, [
                    "...!! ...",
                    "...부끄러워요...",
                    "...(얼굴이 빨개진다)",
                    "...거기는...",
                ]),
            ],
        },

        # 토글형 행위
        "hug": {
            "start": [
                ({"애정": 50}, ["...좋아요... 이대로...", "...안심돼요..."]),
                ({"호감": 80}, ["...따뜻해요...", "...행복해요..."]),
                ({}, [
                    "...앗...",
                    "...(가만히 있는다)",
                    "...네...",
                    "...따뜻해요...",
                ]),
            ],
            "during": [
                ({"성욕": 50}, ["유키가 숨을 거칠게 몰아쉬며 안겨 있다."]),
                ({"성욕": 30}, ["유키의 심장이 빠르게 뛰는 게 느껴진다."]),
                ({"애정": 40}, ["유키가 안심한 표정으로 안겨 있다."]),
                ({}, [
                    "유키가 조용히 안겨 있다.",
                    "유키의 체온이 느껴진다.",
                    "유키가 눈을 감고 있다.",
                    "유키가 작게 떨고 있다.",
                ]),
            ],
        },
        "deep_kiss": {
            "start": [
                ({"성욕": 40}, ["...으응... 이상해요..."]),
                ({"애정": 30}, ["...(눈을 감는다)"]),
                ({}, [
                    "...네...",
                    "...눈... 감을게요...",
                    "...",
                ]),
            ],
            "during": [
                ({"성욕": 50}, ["유키가 몽롱한 눈으로 키스에 빠져 있다."]),
                ({"성욕": 30}, ["유키의 숨결이 거칠어진다."]),
                ({}, [
                    "유키와 깊은 키스를 나누고 있다.",
                    "유키가 눈을 꼭 감고 있다.",
                    "유키의 입술이 살짝 떨린다.",
                ]),
            ],
        },
        "breast_touch": {
            "start": [
                ({}, [
                    "...!! ...",
                    "...거기는...",
                    "...부끄러워요...",
                ]),
            ],
            "during": [
                ({}, [
                    "유키가 고개를 숙이고 있다.",
                    "유키가 작은 신음을 흘린다.",
                    "유키의 귀가 빨갛다.",
                    "유키가 눈물이 맺힌 채 참고 있다.",
                ]),
            ],
        },

        # 절정 반응
        "ecstasy": {
            "start": [
                ({}, [
                    "...앗...!! ♡",
                    "...이상해요... 머리가...♡",
                    "...(말없이 떨고 있다)",
                    "...좋아요...♡",
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
                "은빛 머리카락의 소녀가 있다.",
                "낯선 이의 등장에 경계하는 눈빛을 보낸다.",
                "붉은 눈동자가 차갑게 빛난다.",
                "입술을 굳게 다문 채 한 발짝 뒤로 물러선다.",
                "엘라 뒤에 숨듯 서서, 여전히 경계를 풀지 않는다."
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
        """플레이어와 처음 만났을 때 - Generator 기반 (묘사 형식)"""
        unit_info = morld.get_unit_info(self.instance_id)

        # 수면 중이면 반응 없음
        if unit_info and unit_info.get("activity") == "수면":
            return None

        # 첫 만남 여부 판정 (관계:유키:진척도 <= 0)
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
        # 첫 만남 완료 처리 (관계:유키:진척도 = 1)
        self.mark_first_meet_done(player_id)

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

        yield morld.dialog([
            f"[{name}]",
            "...안녕하세요...",
            "...기다리고 있었어요...",
            "...같이 있으면... 안심돼요..."
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

        yield morld.dialog([
            f"[{name}]",
            "...안녕하세요...",
            "...뭔가 필요하세요...?",
            "...저라도 괜찮으시다면..."
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
            yield morld.dialog([f"[{name}]", "...네...", "...무슨 일이세요...?"])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield morld.dialog([
            f"[{name}]",
            "...저요...?",
            "...유키예요...",
            "...특별한 건... 없어요...",
            "...엘라랑 둘이서 여기 살아요...",
            "...엘라는... 좋은 사람이에요...",
            "...저를 돌봐줘요...",
            "...말이 많진 않지만... 다정해요...",
            "...이 은신처도... 엘라가 찾았어요...",
            "...덕분에... 안전하게 지낼 수 있어요..."
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
            yield morld.dialog([
                f"[{name}]",
                "...",
                "...오늘도... 조용하네요...",
                "...좋아요..."
            ])
            return

        # 플래그 설정
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield morld.dialog([
            f"[{name}]",
            "...좋아하는 것요...?",
            "...",
            "...책이요...",
            "...글자를 읽으면... 마음이 편해져요...",
            "...다른 세계로 가는 것 같아요...",
            "...",
            "...그리고... 조용한 게 좋아요...",
            "...시끄러운 건... 무서워요...",
            "...여기는... 조용해서 좋아요...",
            "...",
            f"...{player_name}씨도... 조용해서... 좋아요...",
            "...(고개를 숙인다)"
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
            yield morld.dialog([
                f"[{name}]",
                "...",
                "...(조용히 창밖을 바라본다)",
                "..."
            ])
            return

        # 플래그 설정
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield morld.dialog([
            f"[{name}]",
            "...",
            "...옛날 이야기요...?",
            "...",
            "...기억이... 없어요...",
            "...눈을 떴을 때... 혼자였어요...",
            "...무서웠어요... 너무 무서웠어요...",
            "...아무것도 모르겠고...",
            "...어디로 가야 할지도...",
            "...",
            "...그때 엘라를 만났어요...",
            "...엘라도... 혼자였어요...",
            "...아무것도 기억 못 한대요...",
            "...",
            "...그래서... 같이 있기로 했어요...",
            "...혼자보다... 나으니까...",
            f"...{player_name}씨도... 그런 거죠...?",
            "...기억이... 없는 거...",
            "...같이 있으면... 덜 무서워요..."
        ])


# ========================================
# AI Agent
# ========================================

@register_agent_class("yuki")
class YukiAgent(BaseAgent):
    """
    유키 AI - 도심 은신처 생활

    특징:
    - 수줍고 얌전함
    - 은신처에서 조용히 지냄
    - 엘라를 의지함
    """

    # 도심 은신처 스케줄 (region_id=2, location_id=5=은신처)
    SCHEDULE = [
        {"name": "기상", "region_id": 2, "location_id": 5, "start": 420, "end": 480, "activity": "준비"},
        {"name": "아침식사", "region_id": 2, "location_id": 5, "start": 480, "end": 540, "activity": "식사"},
        {"name": "청소", "region_id": 2, "location_id": 5, "start": 540, "end": 660, "activity": "청소"},
        {"name": "독서", "region_id": 2, "location_id": 5, "start": 660, "end": 720, "activity": "휴식"},
        {"name": "점심식사", "region_id": 2, "location_id": 5, "start": 720, "end": 780, "activity": "식사"},
        {"name": "휴식", "region_id": 2, "location_id": 5, "start": 780, "end": 1020, "activity": "휴식"},
        {"name": "저녁식사", "region_id": 2, "location_id": 5, "start": 1080, "end": 1140, "activity": "식사"},
        {"name": "독서", "region_id": 2, "location_id": 5, "start": 1140, "end": 1320, "activity": "휴식"},
        {"name": "수면", "region_id": 2, "location_id": 5, "start": 1320, "end": 420, "activity": "수면"},
    ]

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self.SCHEDULE)

    def think(self):
        """유키의 행동 결정 - 스케줄 기반 Job 채우기"""
        schedule = self.get_current_schedule()
        self.fill_schedule_jobs_from(schedule)
        return None
