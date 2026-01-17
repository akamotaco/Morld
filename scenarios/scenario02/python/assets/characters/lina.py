# assets/characters/lina.py - 리나 캐릭터 Asset
#
# Rule-based 텍스트 선택 시스템 사용
# - TALK_RULES: 대화 규칙
# - DESCRIBE_RULES: 장소에서 보이는 묘사 규칙
# - FOCUS_RULES: 클릭했을 때 상세 묘사 규칙

import morld
from assets.base import Character
from think import BaseAgent, register_agent_class


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
        ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

        # Activity 기반
        ({"activity": "채집"}, {"pages": ["지금 채집 중이야!", "조금만 기다려~"]}),
        ({"activity": "빨래"}, {"pages": ["빨래 중이야~", "금방 끝나!"]}),
        ({"activity": "식사"}, {"pages": ["(맛있게 먹고 있다)", "냠냠... 뭐야?"]}),
        ({"activity": "휴식"}, {"pages": ["후아~ 오늘 피곤하다~", "...뭐야, 나도 놀아줄까?"]}),
        ({"activity": "준비"}, {"pages": ["잠깐만! 준비 중이야!", "..."]}),

        # 호감도 기반
        ({"호감": 70}, {"pages": ["야호! 왔구나!", "오늘 뭐 하고 놀까?"]}),
        ({"호감": 50}, {"pages": ["안녕안녕!", "뭐 재밌는 거 없어?"]}),

        # mood 기반
        ({"mood": "기쁨"}, {"pages": ["오늘 기분 짱 좋아!", "같이 놀자!"]}),
        ({"mood": "슬픔"}, {"pages": ["...응?", "...아무것도 아니야."]}),

        # 기본값
        ({}, {"pages": ["응? 뭐야뭐야?", "...심심한 거야? 나도 좀 심심했는데!"]}),
    ]

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

        # 호감도 기반
        ({"호감": 70}, "당신을 보고 환하게 웃는다."),

        # 기본값
        ({}, "밝은 금발 단발머리의 활기찬 소녀. 녹색 눈이 반짝인다."),
    ]

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
                ({"성적흥분": 50}, ["리나가 숨을 거칠게 몰아쉬며 안겨 있다."]),
                ({"성적흥분": 30}, ["리나의 심장이 빠르게 뛰는 게 느껴진다."]),
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
                ({"성적흥분": 40}, ["...으응... 이상해...♡"]),
                ({"애정": 30}, ["...좋아해...♡"]),
                ({}, [
                    "...눈 감을게...",
                    "심장이 막 뛰어...",
                    "...키스...♡",
                ]),
            ],
            "during": [
                ({"성적흥분": 50}, ["리나가 몽롱한 눈으로 키스에 빠져 있다."]),
                ({"성적흥분": 30}, ["리나의 숨결이 거칠어진다."]),
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
            elif key in ("성적흥분", "성적절정"):
                prop_key = f"상태:{key}"
            else:
                prop_key = key

            actual_value = props.get(prop_key, 0)
            if actual_value < required_value:
                return False

        return True


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
        {"name": "기상", "region_id": 0, "location_id": 7, "start": 360, "end": 420, "activity": "준비"},
        {"name": "아침식사", "region_id": 0, "location_id": 3, "start": 420, "end": 480, "activity": "식사"},
        {"name": "빨래", "region_id": 0, "location_id": 13, "start": 480, "end": 540, "activity": "빨래"},  # 뒷마당
        {"name": "채집", "region_id": 0, "location_id": 23, "start": 540, "end": 720, "activity": "채집"},
        {"name": "점심식사", "region_id": 0, "location_id": 3, "start": 720, "end": 780, "activity": "식사"},
        {"name": "채집", "region_id": 0, "location_id": 23, "start": 840, "end": 1020, "activity": "채집"},
        {"name": "빨래걷기", "region_id": 0, "location_id": 13, "start": 1020, "end": 1080, "activity": "빨래"},  # 뒷마당
        {"name": "저녁식사", "region_id": 0, "location_id": 3, "start": 1110, "end": 1170, "activity": "식사"},
        {"name": "자유시간", "region_id": 0, "location_id": 1, "start": 1170, "end": 1320, "activity": "휴식"},
        {"name": "수면", "region_id": 0, "location_id": 7, "start": 1320, "end": 360, "activity": "수면"},
    ]

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self.SCHEDULE)

    def think(self):
        """리나의 행동 결정 - 스케줄 기반 Job 채우기"""
        schedule = self.get_current_schedule()
        self.fill_schedule_jobs_from(schedule)
        return None
