# assets/characters/sera.py - 세라 캐릭터 Asset
#
# Rule-based 텍스트 선택 시스템 사용
# - TALK_RULES: 대화 규칙
# - DESCRIBE_RULES: 장소에서 보이는 묘사 규칙
# - FOCUS_RULES: 클릭했을 때 상세 묘사 규칙

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
        "call:date:데이트 신청#",      # 데이트 중 아닐 때만 표시
        "call:end_date:데이트 종료#",  # 데이트 중일 때만 표시
        "call:hold_hands:손 잡기#",    # 데이트 중일 때만 표시
        "call:date_hug:안아주기#",     # 데이트 중일 때만 표시
        "call:date_kiss:키스#",        # 데이트 중일 때만 표시
        "call:romance:스킨십",
        "call:debug_props:속성 보기",
        "call:debug_affection_up:호감도 +10",
        "call:debug_affection_down:호감도 -10",
    ]
    mood = []

    # ========================================
    # 대화 규칙 (조건 → 대사 또는 메서드명)
    # 위에서부터 순서대로 체크, 첫 번째 매칭 사용
    # - dict: {"pages": [...]} 형태의 간단한 대사
    # - str: "_"로 시작하는 메서드명 → 복잡한 대화 처리
    # ========================================
    TALK_RULES = [
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

        # 호감도 기반
        ({"호감": 70}, {"pages": ["......", "...뭐, 괜찮아?"]}),
        ({"호감": 50}, {"pages": ["......", "...무슨 일이야?"]}),

        # mood 기반
        ({"mood": "기쁨"}, {"pages": ["......", "...오늘은 기분이 좋군."]}),
        ({"mood": "슬픔"}, {"pages": ["......", "..."]}),

        # 기본값
        ({}, {"pages": ["......", "...할 말이 있으면 빨리."]}),
    ]

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

        # 호감도 기반
        ({"호감": 70}, "눈빛이 조금 부드러워진 것 같다."),

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
                ({"성적흥분": 50}, ["세라의 심장이 빠르게 뛰는 게 느껴진다."]),
                ({"성적흥분": 30}, ["세라가 숨을 고르고 있다."]),
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
                ({"성적흥분": 40}, ["...으응... 더..."]),
                ({"애정": 30}, ["......(눈을 감는다)"]),
                ({}, [
                    "......",
                    "...키스...",
                    "...눈 감아.",
                ]),
            ],
            "during": [
                ({"성적흥분": 50}, ["세라가 거칠게 숨을 몰아쉬며 키스에 빠져 있다."]),
                ({"성적흥분": 30}, ["세라의 숨결이 거칠어진다."]),
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
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 처음 만났을 때 - Generator 기반"""
        # 첫 만남 이벤트
        if self._event_flags.get("first_meet"):
            return None

        unit_info = morld.get_unit_info(self.instance_id)
        if unit_info and unit_info.get("activity") == "수면":
            return None

        self._event_flags["first_meet"] = True
        return self._run_event_dialog("first_meet", player_id=player_id)

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
            elif key in ("성적흥분", "성적절정"):
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
