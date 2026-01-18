# assets/characters/ella.py - 엘라 캐릭터 Asset
#
# Rule-based 텍스트 선택 시스템 사용
# - TALK_RULES: 대화 규칙
# - DESCRIBE_RULES: 장소에서 보이는 묘사 규칙
# - FOCUS_RULES: 클릭했을 때 상세 묘사 규칙

import morld
from assets.base import Character
from think import BaseAgent, register_agent_class


class Ella(Character):
    unique_id = "ella"
    name = "엘라"
    type = "female"
    props = {
        "외모:흑발": 1, "외모:올림머리": 1, "외모:보라색눈": 1,
        "성격:냉정함": 1, "성격:리더십": 1,
        "관계:유키:보호": 1,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 5,
    }
    actions = [
        "call:talk:대화",
        "call:romance:스킨십",
        "call:debug_props:속성 보기",
        "call:debug_affection_up:호감도 +10",
        "call:debug_affection_down:호감도 -10",
    ]
    mood = []

    # ========================================
    # 대화 규칙 (조건 → 대사 또는 메서드명)
    # ========================================
    TALK_RULES = [
        # 특수 상황 (최우선)
        ({"mood": "분노"}, {"pages": ["......", "...가까이 오지 마라."]}),
        ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

        # 진척도별 사적인 대화 (플래그로 일회성 체크)
        # 진척도 3 - 과거 이야기
        ({"호감": 70, "진척도": 3}, "_talk_progress_3"),
        # 진척도 2 - 좋아하는 것
        ({"호감": 60, "진척도": 2}, "_talk_progress_2"),
        # 진척도 1 - 자신에 대해
        ({"호감": 50, "진척도": 1}, "_talk_progress_1"),

        # Activity 기반
        ({"activity": "관리"}, {"pages": ["지금 바쁘다.", "...급한 일이 아니라면 나중에 와라."]}),
        ({"activity": "조회"}, {"pages": ["지금 조회 중이다.", "잠시 기다려라."]}),
        ({"activity": "순찰"}, {"pages": ["순찰 중이다.", "무슨 일이냐?"]}),
        ({"activity": "탐색"}, {"pages": ["물자를 찾고 있다.", "...방해하지 마라."]}),
        ({"activity": "식사"}, {"pages": ["(식사 중이다)", "...나중에 와라."]}),
        ({"activity": "휴식"}, {"pages": ["......", "무슨 일이냐?"]}),
        ({"activity": "준비"}, {"pages": ["지금 준비 중이다.", "잠시 후에 와라."]}),

        # 호감도 기반 (진척도 증가 로직 포함)
        ({"호감": 70}, "_talk_friendly_high"),
        ({"호감": 50}, "_talk_friendly_mid"),

        # mood 기반
        ({"mood": "기쁨"}, {"pages": ["......", "...특별한 일이라도 있었나?"]}),
        ({"mood": "슬픔"}, {"pages": ["............", "..."]}),

        # 기본값
        ({}, {"pages": ["무슨 용건이냐?", "...간단히 말해라."]}),
    ]

    # ========================================
    # Describe 규칙 (장소에서 보이는 묘사)
    # ========================================
    DESCRIBE_RULES = [
        # 이동 중
        ({"is_traveling": True, "activity": "순찰"}, "{name}가 정찰을 위해 이동 중이다."),
        ({"is_traveling": True, "activity": "탐색"}, "{name}가 물자를 찾으러 이동 중이다."),
        ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),

        # Activity 기반
        ({"activity": "관리"}, "{name}가 서류를 검토하고 있다."),
        ({"activity": "조회"}, "{name}가 모두에게 지시를 내리고 있다."),
        ({"activity": "순찰"}, "{name}가 주변을 경계하고 있다."),
        ({"activity": "탐색"}, "{name}가 물자를 찾고 있다."),
        ({"activity": "식사"}, "{name}가 우아하게 식사 중이다."),
        ({"activity": "수면"}, "{name}가 단정한 자세로 잠들어 있다."),
        ({"activity": "휴식"}, "{name}가 창밖을 바라보고 있다."),

        # 위치 기반
        ({"location": (0, 1)}, "{name}가 거실 중앙에 서서 상황을 파악하고 있다."),
        ({"location": (0, 11)}, "{name}가 책상에서 서류를 정리하고 있다."),
        ({"location": (2, 5)}, "{name}가 은신처에서 유키를 지키고 있다."),  # 도심 은신처

        # 기본값
        ({}, "{name}가 위엄있게 서 있다."),
    ]

    # ========================================
    # NPC 주도 설정 (엘라: 냉정함 - 높은 임계값, 세라와 비슷)
    # ========================================
    INITIATIVE_CONFIG = {
        "arousal_threshold": 75,      # 성욕 임계값 (세라와 비슷하게 높음)
        "affection_threshold": 65,    # 호감도 임계값 (세라와 비슷)
        "cooldown_minutes": 600,      # 쿨다운 10시간 (세라보다 조금 김)
    }

    # NPC 주도 시 허용 액션 필터
    # 엘라는 냉정해서 마음을 열기 어렵지만, 열리면 직접적
    INITIATIVE_ACTION_FILTERS = [
        ({"애정": 80}, ["hug", "deep_kiss", "breast_touch"]),  # 높은 애정 필요
        ({"애정": 50}, ["hug", "deep_kiss"]),
        ({}, ["hug"]),  # 기본: 포옹만
    ]

    # NPC 주도 중 반응 텍스트
    INITIATIVE_REACTIONS = {
        "start": [
            ({"성욕": 80}, ["...가만히 있어.", "......(다가온다)"]),
            ({}, ["......", "...잠깐."]),
        ],
        "during_hug": [
            ({"성욕": 60}, ["엘라가 거칠게 숨을 몰아쉬며 안아온다."]),
            ({}, ["엘라가 조용히 안아온다.", "엘라의 심장이 빠르게 뛴다."]),
        ],
        "during_deep_kiss": [
            ({"성욕": 70}, ["엘라가 거친 숨을 몰아쉬며 키스를 이어간다."]),
            ({}, ["엘라가 조용히 키스하고 있다."]),
        ],
        "during_breast_touch": [
            ({}, ["엘라가 고개를 돌린 채 가만히 있다."]),
        ],
        "escape_fail": [
            ({}, ["...도망치려고?", "...안 돼."]),
        ],
        "satisfied": [
            ({"애정": 60}, ["...나쁘지 않았다.", "......(희미하게 웃는다)"]),
            ({}, ["...됐다.", "...가도 좋다."]),
        ],
    }

    # ========================================
    # 은신 성공 반응 (엘라: 냉정하게 경계)
    # ========================================
    # 엘라는 냉정하고 경계심이 강해서 위험한 상황에 더 긴장
    STEALTH_REACTIONS = {
        "text": [
            ({"성욕": 50}, ["......", "...(경계하며 주위를 살핀다)"]),
            ({"애정": 40}, ["...위험했다.", "...조심해야 한다."]),
            ({}, ["......", "...(차갑게 주위를 경계한다)"]),
        ],
        "effects": {"애정": 1},  # 함께 위기를 넘겨서 유대감 증가
    }

    # ========================================
    # 스킨십 반응 (action_id → timing → 조건부 대사 리스트)
    # 엘라: 냉정하고 위엄있지만, 마음을 열면 조금씩 변화
    # ========================================
    ROMANCE_REACTIONS = {
        # 즉시형 행위
        "head_pat": {
            "start": [
                ({}, [
                    "...뭐하는 거냐.",
                    "...치워라.",
                    "......(가만히 있는다)",
                    "...싫지 않다.",
                ]),
            ],
        },
        "cheek_caress": {
            "start": [
                ({}, [
                    "......",
                    "...뭐냐.",
                    "...손이 거칠군.",
                    "...(눈을 피한다)",
                ]),
            ],
        },
        "cheek_pinch": {
            "start": [
                ({}, [
                    "......죽고 싶냐.",
                    "...손 치워.",
                    "......(미간을 찌푸린다)",
                    "...아프다.",
                ]),
            ],
        },
        "ear_touch": {
            "start": [
                ({}, [
                    "...!",
                    "...거기는 안 돼.",
                    "......(귀끝이 붉어진다)",
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
                    "...더 해도 된다...",
                ]),
            ],
        },
        "butt_caress": {
            "start": [
                ({}, [
                    "......!",
                    "...죽고 싶냐.",
                    "......(노려본다)",
                    "...거기는...",
                ]),
            ],
        },

        # 토글형 행위
        "hug": {
            "start": [
                ({"애정": 50}, ["...안아줘...", "...이대로..."]),
                ({"호감": 80}, ["...괜찮다...", "...따뜻하군..."]),
                ({}, [
                    "......",
                    "...뭐냐.",
                    "...놓아라.",
                    "...(가만히 있는다)",
                ]),
            ],
            "during": [
                ({"성욕": 50}, ["엘라가 숨을 거칠게 몰아쉬고 있다."]),
                ({"성욕": 30}, ["엘라의 심장이 빠르게 뛰는 게 느껴진다."]),
                ({"애정": 40}, ["엘라가 조용히 기대어 있다."]),
                ({}, [
                    "엘라가 뻣뻣하게 서 있다.",
                    "엘라의 체온이 느껴진다.",
                    "엘라가 가만히 있다.",
                    "엘라의 손끝이 미세하게 떨린다.",
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
                ({"성욕": 50}, ["엘라가 거칠게 숨을 몰아쉬며 키스에 빠져 있다."]),
                ({"성욕": 30}, ["엘라의 숨결이 거칠어진다."]),
                ({}, [
                    "엘라와 깊은 키스를 나누고 있다.",
                    "엘라가 눈을 감고 있다.",
                    "엘라의 입술이 느껴진다.",
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
                    "엘라가 고개를 돌리고 있다.",
                    "엘라의 숨소리가 거칠어진다.",
                    "엘라가 이를 악물고 있다.",
                    "엘라의 귀끝이 붉다.",
                ]),
            ],
        },

        # 절정 반응
        "ecstasy": {
            "start": [
                ({}, [
                    "......!!",
                    "...크... 응...!",
                    "...(몸을 떨고 있다)",
                    "...이상해...",
                ]),
            ],
        },
    }

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = [
        # Activity 기반
        ({"activity": "관리"}, "서류를 검토하며 무언가 기록하고 있다."),
        ({"activity": "조회"}, "모두를 둘러보며 하루 일과를 지시하고 있다."),
        ({"activity": "순찰"}, "날카로운 눈으로 주변을 경계하고 있다."),
        ({"activity": "탐색"}, "주변을 살피며 쓸 만한 것을 찾고 있다."),
        ({"activity": "식사"}, "우아하게 식사 중이다."),
        ({"activity": "수면"}, "단정한 자세로 잠들어 있다."),
        ({"activity": "휴식"}, "창밖을 바라보며 생각에 잠겨 있다."),

        # mood 기반
        ({"mood": "기쁨"}, "표정 변화는 적지만, 눈빛이 부드러워졌다."),
        ({"mood": "슬픔"}, "평소보다 더 차가워 보인다. 무언가 생각에 잠겨 있다."),
        ({"mood": "분노"}, "눈빛이 날카롭다. 함부로 다가가기 어렵다."),

        # 호감도 기반
        ({"호감": 70}, "당신을 보고 살짝 고개를 끄덕인다."),

        # 기본값
        ({}, "단정하게 올린 흑발의 위엄있는 여성. 보라색 눈이 냉정해 보인다."),
    ]

    # ========================================
    # 이벤트 다이얼로그 정의
    # ========================================
    EVENT_DIALOGS = {
        "first_meet": {
            "pages": [
                "단정하게 올린 흑발의 여성이 있다.",
                "보라색 눈동자가 차갑게 당신을 훑어본다.",
                "본능적으로 유키를 등 뒤로 감싸며 한 걸음 앞으로 나선다.",
                "외부인에 대한 경계와 불신이 온몸에서 느껴진다.",
                "그녀의 눈빛은 '가까이 오지 마라'라고 말하고 있다.",
                "유키를 지키려는 듯, 굳건히 그 자리에 서 있다."
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
        # 첫 만남 이벤트
        if not self._event_flags.get("first_meet"):
            unit_info = morld.get_unit_info(self.instance_id)
            if not (unit_info and unit_info.get("activity") == "수면"):
                self._event_flags["first_meet"] = True
                return self._run_event_dialog("first_meet", player_id=player_id)

        # NPC 주도 스킨십 체크
        if self.should_initiate_skinship(player_id):
            from npc_initiative import start_npc_initiative
            return start_npc_initiative(player_id, self.instance_id)

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

        yield morld.dialog([
            f"[{name}]",
            "......",
            "...무슨 일이냐?",
            "...네가 오면... 나쁘지 않군."
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
            "......",
            "...할 말이 있으면 빨리 해라.",
            "...그래도... 네 얼굴을 보는 건 싫지 않다."
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
            yield morld.dialog([f"[{name}]", "......", "...또 왔냐."])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield morld.dialog([
            f"[{name}]",
            "...나에 대해?",
            "......",
            "...엘라다.",
            "...유키와 둘이 살고 있다.",
            "...유키는 내가 지킨다.",
            "...그게 내 역할이니까.",
            "...이 도시에서... 살아남으려면 누군가는 해야 할 일이다.",
            "...물자를 찾고, 위험을 피하고, 안전을 확보하고...",
            "...전부 내가 해야 한다.",
            "...유키는... 혼자서는 못 살아.",
            "...그러니까 내가 지켜야 한다."
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
                "......",
                "...창밖을 보고 있었다.",
                "...오늘은 조용하군."
            ])
            return

        # 플래그 설정
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield morld.dialog([
            f"[{name}]",
            "...좋아하는 것?",
            "......",
            "...그런 거 생각할 여유가 없다.",
            "...살아남는 게 먼저니까.",
            "...",
            "...굳이 말하자면...",
            "...조용한 밤.",
            "...아무 일도 없이... 하루가 끝나는 것.",
            "...그게 가장 좋다.",
            "...",
            "...그리고...",
            "...유키가 웃는 것.",
            "...유키가 편하게 자는 것.",
            "...그게... 좋다.",
            "......",
            f"...{player_name}.",
            "...너에게 말한 건 처음이군.",
            "...아무에게도 말하지 마라."
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
                "......",
                "...(먼 곳을 바라보고 있다)",
                "...아무것도 아니다."
            ])
            return

        # 플래그 설정
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield morld.dialog([
            f"[{name}]",
            "...",
            "...과거?",
            "...",
            "...기억이 없다.",
            "...눈을 떴을 때... 여기였다.",
            "...도시 한가운데.",
            "...아무도 없었다.",
            "...누구인지도, 왜 여기 있는지도...",
            "...아무것도 모르겠었다.",
            "...",
            "...그때 유키를 만났다.",
            "...유키도... 나처럼 혼자였다.",
            "...아무것도 기억하지 못하고...",
            "...무서워하고 있었다.",
            "...",
            "...그래서 결정했다.",
            "...내가 지키겠다고.",
            "...유키를. 이 아이를.",
            "...혼자 두지 않겠다고.",
            "...",
            f"...{player_name}.",
            "...너도... 마찬가지냐?",
            "...기억이 없는 거.",
            "...우리 모두... 같은 상황이군.",
            "...이 세계가 뭔지는 모르겠지만...",
            "...살아남아야 한다.",
            "...그게 우리가 할 수 있는 전부다."
        ])


# ========================================
# AI Agent
# ========================================

@register_agent_class("ella")
class EllaAgent(BaseAgent):
    """
    엘라 AI - 도심 생존자 리더

    특징:
    - 냉정하고 리더십 있음
    - 유키를 보호하고 돌봄
    - 외부인에 대한 불신
    """

    # 도심 은신처 스케줄 (region_id=2)
    SCHEDULE = [
        {"name": "기상", "region_id": 2, "location_id": 5, "start": 360, "end": 420, "activity": "준비"},
        {"name": "아침식사", "region_id": 2, "location_id": 5, "start": 420, "end": 480, "activity": "식사"},
        {"name": "정찰", "region_id": 2, "location_id": 3, "start": 540, "end": 660, "activity": "순찰"},  # 약국
        {"name": "물자수집", "region_id": 2, "location_id": 2, "start": 660, "end": 720, "activity": "탐색"},  # 편의점
        {"name": "점심식사", "region_id": 2, "location_id": 5, "start": 720, "end": 780, "activity": "식사"},
        {"name": "관리", "region_id": 2, "location_id": 5, "start": 780, "end": 960, "activity": "관리"},
        {"name": "정찰", "region_id": 2, "location_id": 0, "start": 960, "end": 1020, "activity": "순찰"},  # 도시입구
        {"name": "저녁식사", "region_id": 2, "location_id": 5, "start": 1080, "end": 1140, "activity": "식사"},
        {"name": "휴식", "region_id": 2, "location_id": 5, "start": 1140, "end": 1320, "activity": "휴식"},
        {"name": "수면", "region_id": 2, "location_id": 5, "start": 1320, "end": 360, "activity": "수면"},
    ]

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self.SCHEDULE)

    def think(self):
        """엘라의 행동 결정 - 스케줄 기반 Job 채우기"""
        schedule = self.get_current_schedule()
        self.fill_schedule_jobs_from(schedule)
        return None
