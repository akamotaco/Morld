# assets/characters/ella.py - 엘라 캐릭터 Asset
#
# ============================================================
# 캐릭터 설정
# ============================================================
# 이름: 엘라 (Ella)
# 성별: 여성
# 나이: 불명 (20대 중반으로 추정, 기억 없음)
#
# 외모:
#   - 흑발 올림머리, 보라색 눈
#   - 차갑고 날카로운 인상
#   - 단정하고 정돈된 분위기
#
# 성격:
#   - 냉정함: 감정을 잘 드러내지 않고, 이성적으로 판단
#   - 리더십: 상황을 분석하고 결정을 내리는 능력
#   - 완벽주의: 일처리에 빈틈이 없음
#   - 내면: 유키에게만 보이는 부드러운 면, 혼자 짊어지는 책임감
#
# 좋아하는 것:
#   - 질서, 계획대로 진행되는 일
#   - 효율적인 것, 명확한 것
#   - 유키가 안전하고 행복한 것
#   - 조용한 시간, 혼자 생각할 여유
#
# 싫어하는 것:
#   - 비효율, 낭비, 무질서
#   - 무능함, 약속을 어기는 것
#   - 방해받는 것, 쓸데없는 수다
#   - 유키가 위험에 처하는 것
#
# 취미:
#   - 관리 업무 (서류 정리, 물자 확인)
#   - 순찰, 정찰 (주변 상황 파악)
#   - 물자 탐색 (생존에 필요한 것 확보)
#
# 과거사:
#   - 도심의 빌딩에서 눈을 떴음
#   - 근처에서 쓰러져 있던 유키를 발견
#   - 유키를 보호하면서 생존해 옴
#   - 과거를 묻는 것을 싫어함 (단편적 기억은 있으나 말하지 않음)
#
# (복선) 귀족/고위직 가문 출신 암시:
#   - 장녀 또는 차녀로 동생들을 돌봤던 경험 → 유키를 돌보는 본능적 행동
#   - 완벽주의와 단정함 → 귀족 교육의 흔적
#   - 질서와 효율 중시 → 가문 경영에 익숙했던 습관
#   - 리더십과 책임감 → 가문의 기대를 짊어졌던 과거
#   - 가문의 몰락 또는 무언가로 인해 추락했지만 꿋꿋이 버팀
#   - 가끔 무의식적으로 나오는 격식 있는 말투나 행동
#
# 현재 배경:
#   - 도심 생존자 그룹의 리더 (사실상 둘뿐)
#   - 유키를 보호하는 것이 최우선 목표
#   - 은신처를 관리하고 물자를 확보
#   - 저택 그룹과는 별개로 활동
#
# 말투 특징:
#   - 짧고 단호한 문장
#   - 명령조, 단언하는 말투
#   - "...간단히 말해라", "...필요 없다" 등 차가운 표현
#   - 감정을 억제하는 느낌
#
# 관계:
#   - 유키: 유일하게 마음을 여는 존재, 보호 대상
#   - 플레이어: 처음엔 경계와 불신, 유용하다고 판단되면 인정
#   - 저택 그룹: 존재는 알지만 접촉 없음
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
        "생존 방법",
        "평소에 뭐 해?",
    ]

    # ========================================
    # 대화 규칙 (주제별 조건 → 대사 또는 메서드명)
    # ========================================
    TALK_RULES = {
        "잡담": [
            # 특수 상황 (최우선)
            ({"mood": "분노"}, {"pages": ["......", "...가까이 오지 마라."]}),
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

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
        ],

        "본인에 대해": [
            # 특수 상황
            ({"mood": "분노"}, {"pages": ["......", "...알 필요 없다."]}),
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 진척도별 사적인 대화 (플래그로 일회성 체크)
            ({"호감": 70, "진척도": 3}, "_talk_progress_3"),
            ({"호감": 60, "진척도": 2}, "_talk_progress_2"),
            ({"호감": 50, "진척도": 1}, "_talk_progress_1"),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "......",
                "...엘라다.",
                "...이곳에서 유키를 보호하며 지내고 있다.",
                "...그게 내가 해야 할 일이다.",
                "......더 이상 물을 건 없겠지?",
            ]}),
            ({"호감": 50}, {"pages": [
                "...엘라.",
                "...관리와 순찰을 맡고 있다.",
                "...그게 전부다.",
            ]}),
            ({"호감": 30}, {"pages": [
                "...엘라라고 한다.",
                "......",
            ]}),

            # 기본값
            ({}, {"pages": ["......", "...너에게 말할 이유가 없다."]}),
        ],

        "생존 방법": [
            # 특수 상황
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "...생존에 관심이 있나?",
                "...기본은 경계를 늦추지 않는 것이다.",
                "...물자는 아껴 써라. 언제 구할 수 있을지 모른다.",
                "...혼자 행동하지 마라. 위험하다.",
                "...상황 판단이 생존의 핵심이다.",
            ]}),
            ({"호감": 50}, {"pages": [
                "...생존?",
                "...주변을 잘 살펴라.",
                "...물자를 확보하고, 위험을 피해라.",
                "...기본적인 것이다.",
            ]}),
            ({"호감": 30}, {"pages": [
                "...생존은 스스로 터득하는 것이다.",
                "...쉽게 알려줄 건 없다.",
            ]}),

            # 기본값
            ({}, {"pages": ["......", "...네가 알 필요 없다."]}),
        ],

        "평소에 뭐 해?": [
            # 특수 상황
            ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "...평소?",
                "...순찰하고, 물자를 확인하고...",
                "...유키가 안전한지 살피고...",
                "...쉬는 시간엔 생각을 정리한다.",
                "...그게 다다.",
            ]}),
            ({"호감": 50}, {"pages": [
                "...순찰, 관리, 탐색.",
                "...할 일이 많다.",
            ]}),
            ({"호감": 30}, {"pages": [
                "...바쁘다.",
                "......",
            ]}),

            # 기본값
            ({}, {"pages": ["......", "...관심 가질 필요 없다."]}),
        ],
    }

    # ========================================
    # Describe 규칙 (장소에서 보이는 묘사)
    # ========================================
    DESCRIBE_RULES = [
        # 이동 중
        ({"is_traveling": True, "activity": "순찰"}, "{name}가 정찰을 위해 이동 중이다."),
        ({"is_traveling": True, "activity": "탐색"}, "{name}가 물자를 찾으러 이동 중이다."),
        ({"is_traveling": True}, "{name}(이)가 어딘가로 향하고 있다."),

        # 성욕 기반 (높을수록 우선)
        ({"성욕": 80}, "{name}가 뻣뻣하게 서 있다. 평소의 냉정함이 흔들리는 듯하다."),
        ({"성욕": 60}, "{name}가 이쪽을 힐끔 보더니 고개를 돌린다. 귀끝이 붉다."),
        ({"성욕": 40}, "{name}가 창밖을 바라보고 있다. 무언가 신경 쓰이는 듯하다."),

        # 애정/호감 기반
        ({"애정": 80}, "{name}가 곁에 다가와 말없이 서 있다. 거리가 평소보다 가깝다."),
        ({"애정": 50}, "{name}가 이쪽을 보며 희미하게 고개를 끄덕인다. 눈빛이 부드럽다."),
        ({"호감": 70}, "{name}가 경계를 풀고 있다. 표정이 평소보다 편안해 보인다."),
        ({"호감": 50}, "{name}가 이쪽을 인식하고 있다. 적대적이지 않은 시선이다."),

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
        "cooldown_millis": 600 * _M,      # 쿨다운 10시간 (세라보다 조금 김)
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
    # 스킨십 반응 (action:timing → 조건부 대사 리스트)
    # 엘라: 냉정하고 위엄있지만, 마음을 열면 조금씩 변화
    # ========================================
    ROMANCE_REACTIONS = {
        # 즉시형 행위
        "head_pat:start": [
            ({}, ["...뭐하는 거냐.", "...치워라.", "......(가만히 있는다)", "...싫지 않다."]),
        ],
        "cheek_caress:start": [
            ({}, ["......", "...뭐냐.", "...손이 거칠군.", "...(눈을 피한다)"]),
        ],
        "cheek_pinch:start": [
            ({}, ["......죽고 싶냐.", "...손 치워.", "......(미간을 찌푸린다)", "...아프다."]),
        ],
        "ear_touch:start": [
            ({}, ["...!", "...거기는 안 돼.", "......(귀끝이 붉어진다)", "...그만둬."]),
        ],
        "french_kiss:start": [
            ({}, ["...으응...", "......(눈을 감는다)", "...숨이...", "...더 해도 된다..."]),
        ],
        "butt_caress:start": [
            ({}, ["......!", "...죽고 싶냐.", "......(노려본다)", "...거기는..."]),
        ],

        # 토글형 행위
        "hug:start": [
            ({"애정": 50}, ["...안아줘...", "...이대로..."]),
            ({"호감": 80}, ["...괜찮다...", "...따뜻하군..."]),
            ({}, ["......", "...뭐냐.", "...놓아라.", "...(가만히 있는다)"]),
        ],
        "hug:during": [
            ({"성욕": 50}, ["엘라가 숨을 거칠게 몰아쉬고 있다."]),
            ({"성욕": 30}, ["엘라의 심장이 빠르게 뛰는 게 느껴진다."]),
            ({"애정": 40}, ["엘라가 조용히 기대어 있다."]),
            ({}, ["엘라가 뻣뻣하게 서 있다.", "엘라의 체온이 느껴진다.", "엘라가 가만히 있다.", "엘라의 손끝이 미세하게 떨린다."]),
        ],
        "deep_kiss:start": [
            ({"성욕": 40}, ["...으응... 더..."]),
            ({"애정": 30}, ["......(눈을 감는다)"]),
            ({}, ["......", "...키스...", "...눈 감아."]),
        ],
        "deep_kiss:during": [
            ({"성욕": 50}, ["엘라가 거칠게 숨을 몰아쉬며 키스에 빠져 있다."]),
            ({"성욕": 30}, ["엘라의 숨결이 거칠어진다."]),
            ({}, ["엘라와 깊은 키스를 나누고 있다.", "엘라가 눈을 감고 있다.", "엘라의 입술이 느껴진다."]),
        ],
        "breast_touch:start": [
            ({}, ["......!", "...거기는...", "...뭐하는..."]),
        ],
        "breast_touch:during": [
            ({}, ["엘라가 고개를 돌리고 있다.", "엘라의 숨소리가 거칠어진다.", "엘라가 이를 악물고 있다.", "엘라의 귀끝이 붉다."]),
        ],

        # 절정 반응
        "ecstasy:start": [
            ({}, ["......!!", "...크... 응...!", "...(몸을 떨고 있다)", "...이상해..."]),
        ],
    }

    # ========================================
    # Focus 규칙 (클릭했을 때 상세 묘사)
    # ========================================
    FOCUS_RULES = [
        # 성욕 기반 (높을수록 우선)
        ({"성욕": 80}, "숨결이 평소보다 거칠다. 냉정함을 유지하려 애쓰지만, 귀끝이 붉게 달아올라 있다."),
        ({"성욕": 60}, "시선을 피하고 있다. 평소의 날카로움이 조금 흔들린다."),
        ({"성욕": 40}, "평소와 같아 보이지만, 가끔 멍하니 어딘가를 바라본다."),

        # 애정/호감 기반
        ({"애정": 80}, "눈빛이 많이 부드러워졌다. 냉정한 표정이지만, 곁에 있으면 편안해 보인다."),
        ({"애정": 50}, "표정은 차갑지만, 눈에 따뜻함이 서려 있다."),
        ({"호감": 70}, "당신을 보고 살짝 고개를 끄덕인다. 경계심이 많이 풀린 듯하다."),
        ({"호감": 50}, "냉정한 눈빛이지만, 적대적이지 않다. 인정한 자에게 보이는 시선이다."),

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

        # 기본값
        ({}, "단정하게 올린 흑발의 위엄있는 여성. 보라색 눈이 냉정해 보인다."),
    ]

    # ========================================
    # 이벤트 핸들러
    # ========================================

    def on_meet_player(self, player_id):
        """플레이어와 처음 만났을 때 - Generator 기반 (묘사 형식)"""
        unit_info = morld.get_unit_info(self.instance_id)

        # 수면 중이면 반응 없음
        if unit_info and unit_info.get("activity") == "수면":
            return None

        # 프라이버시 체크 (수면 목적으로 자기 방 도착 시)
        privacy = self._check_room_privacy(player_id)
        if privacy is not None:
            return privacy

        # 첫 만남 여부 판정 (관계:엘라:진척도 <= 0)
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
        conv = ui.Conversation("엘라")

        # 도입: 엘라가 유키를 감싸며 경계
        conv.narration(
            "단정하게 올린 흑발의 여성이 있다.",
            "보라색 눈동자가 차갑게 당신을 훑어본다.",
            "본능적으로 유키를 등 뒤로 감싸며 한 걸음 앞으로 나선다."
        )

        conv.say(
            "......",
            "...누구지?"
        )

        # 첫 번째 선택지
        conv.ask([
            ("길을 잃었어", "lost"),
            ("적이 아니야", "not_enemy"),
            ("(헤어지기)", "@exit"),
        ])

        conv.respond("lost",
            "...그래?",
            "...여긴 은신처야. 우연히 찾아올 곳이 아닌데.",
            "...어디서 온 거지?"
        )

        conv.respond("not_enemy",
            "......",
            "...그건 네가 정하는 게 아니야.",
            "...유키, 뒤에 있어."
        )

        # 두 번째 선택지
        conv.say("...일단 물어볼 게 있어.")

        conv.ask([
            ("여긴 어디야?", "where"),
            ("너희는 누구야?", "who"),
            ("(헤어지기)", "@exit"),
        ])

        conv.respond("where",
            "...알 필요 없어.",
            "...이곳은 우리 둘의 은신처야.",
            "...그 이상은 말할 생각 없어."
        )

        conv.respond("who",
            "...나는 엘라.",
            "...뒤에 있는 건 유키.",
            "...그게 다야."
        )

        # 마무리
        conv.say(
            "......",
            "...경고해 둘게.",
            "...유키에게 해코지하면 가만두지 않아."
        )

        # 누적형 대화 시작
        yield conv.end()

        # 시간 경과 처리
        morld.set_npc_time_consume(self.instance_id, "stay", 1 * _M)
        morld.set_npc_job(self.instance_id, "stay", 2 * _M)

        # 첫 만남 완료 처리 (관계:엘라:진척도 = 1)
        self.mark_first_meet_done(player_id)

    def _on_room_privacy(self, player_id, activity):
        """엘라가 목욕 목적으로 도착했는데 플레이어가 있을 때"""
        if activity != "목욕":
            return None

        props = morld.get_unit_props(self.instance_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공") if player_info else "주인공"
        affection = props.get(f"관계:{player_name}:호감", 0) if props else 0
        info = morld.get_unit_info(self.instance_id)

        if affection >= 70:
            def handler():
                yield ui.dialog([
                    "[엘라]",
                    "...어?",
                    "...지금은 좀 나가 있어줄래?"
                ])
                morld.stand_up(player_id)
                if info:
                    morld.set_unit_location(player_id, info["region_id"], 1, 120)
                yield ui.dialog(["은신처 한쪽으로 물러났다."])
            return handler()
        else:
            def handler():
                yield ui.dialog([
                    "[엘라]",
                    "...뭐야.",
                    "엘라가 차갑게 쏘아붙였다."
                ])
                morld.stand_up(player_id)
                if info:
                    morld.set_unit_location(player_id, info["region_id"], 1, 120)
                yield ui.dialog(["은신처 한쪽으로 쫓겨났다."])
            return handler()

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

        yield ui.dialog([
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
            yield ui.dialog([f"[{name}]", "......", "...또 왔냐."])
            return

        # 플래그 설정 및 사적인 이야기
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield ui.dialog([
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
            yield ui.dialog([
                f"[{name}]",
                "......",
                "...창밖을 보고 있었다.",
                "...오늘은 조용하군."
            ])
            return

        # 플래그 설정
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield ui.dialog([
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
            yield ui.dialog([
                f"[{name}]",
                "......",
                "...(먼 곳을 바라보고 있다)",
                "...아무것도 아니다."
            ])
            return

        # 플래그 설정
        morld.set_unit_prop(self.instance_id, flag_key, 1)
        yield ui.dialog([
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
    # 침대 이벤트
    # ========================================

    def on_bed_awake(self, bed, player_id, slot, affection, region_id, owner_id):
        """
        엘라 침대 반응 (깨어있을 때)
        - 호감도 50 이상: 허용 (날카롭지만)
        - 호감도 50 미만: 강제 퇴출
        """
        if affection >= 50:
            yield ui.dialog([
                "[엘라]",
                "...뭐 하는 거지?",
                "...좋아. 잠깐만이야."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog([
                    "엘라의 침대에 누웠다.",
                    "은은한 가죽 냄새가 난다."
                ])
            else:
                return
        else:
            yield ui.dialog([
                "[엘라]",
                "+...뭐 하는 거야.",
                "[엘라]",
                "+내 침대에 함부로 눕지 마.",
                "+나가."
            ])
            # 약국으로 강제 이동 (은신처 → 약국 location 3, x=180)
            morld.set_unit_location(player_id, region_id, 3, 180)
            yield ui.dialog("엘라에게 쫓겨나 약국으로 나왔다...")
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
                    "손을 뻗어 엘라의 가슴에 살짝 닿았다.",
                    "[엘라]",
                    "+...!",
                    "+...대담하군.",
                    "엘라가 눈을 가늘게 떴지만...",
                    "+손을 치우지는 않았다."
                ])
            elif choice == "butt":
                yield ui.dialog([
                    "손을 뻗어 엘라의 엉덩이에 살짝 닿았다.",
                    "[엘라]",
                    "+......",
                    "+...한 번만 더 하면 팔을 분지르겠어.",
                    "엘라가 날카롭게 경고했다.",
                    "+...하지만 진심은 아닌 것 같다."
                ])
            elif choice == "kiss":
                yield ui.dialog([
                    "엘라의 얼굴에 가까이 다가갔다.",
                    "[엘라]",
                    "+...뭐야.",
                    "엘라의 입술에 가볍게 키스했다.",
                    "엘라가 잠시 굳었다가...",
                    "+조용히 눈을 감았다.",
                    "+\"...바보.\""
                ])
            elif choice == "hug":
                yield ui.dialog([
                    "엘라를 조용히 안아줬다.",
                    "[엘라]",
                    "+......",
                    "+...뭐야. 갑자기.",
                    "엘라가 잠시 뻣뻣하게 있더니...",
                    "+살짝 몸을 기댔다.",
                    "+\"...잠깐만.\""
                ])
        else:
            # 호감 50~79
            if choice == "breast":
                yield ui.dialog([
                    "손을 뻗어 엘라의 가슴에 닿으려는 순간—",
                    "[엘라]",
                    "+...건드리면 죽어.",
                    "엘라의 눈빛이 진심이다. 손을 거뒀다."
                ])
            elif choice == "butt":
                yield ui.dialog([
                    "손을 뻗어 엘라의 엉덩이에 닿으려는 순간—",
                    "[엘라]",
                    "+...손. 치워.",
                    "엘라가 차갑게 경고했다."
                ])
            elif choice == "kiss":
                yield ui.dialog([
                    "엘라의 얼굴에 가까이 다가갔다.",
                    "[엘라]",
                    "+...가까이 오지 마.",
                    "+아직 그럴 사이 아니야.",
                    "엘라가 고개를 돌렸다."
                ])
            elif choice == "hug":
                yield ui.dialog([
                    "엘라를 안으려 했지만—",
                    "[엘라]",
                    "+...만지지 마.",
                    "+아직은 안 돼.",
                    "엘라가 거리를 뒀다."
                ])

    def on_bed_sleeping(self, bed, player_id, slot, affection, owner_id):
        """엘라가 자고 있을 때 - 호감도별 묘사 + 행동 선택"""
        success = False
        if affection >= 50:
            yield ui.dialog([
                "엘라가 잠들어 있다.",
                "깨어있을 때와 다른, 편안한 얼굴."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog(["조심스럽게 옆에 누웠다."])
        else:
            yield ui.dialog([
                "엘라가 잠들어 있다.",
                "...잠이 얕아 보인다. 위험하다."
            ])
            success = morld.sit_on(player_id, bed.instance_id, slot)
            if success:
                yield ui.dialog([
                    "숨을 죽이며 옆에 누웠다.",
                    "(깨면 진짜 끝이다.)"
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
                    "손을 뻗어 엘라의 가슴에 살짝 닿았다.",
                    "+...단단하면서도 부드럽다.",
                    "엘라가 잠결에 살짝 미간을 찌푸렸다.",
                    "+\"...음...\"",
                    "+...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "손을 뻗어 엘라의 가슴에 살짝 닿았다.",
                    "+...단단하면서도 부드럽다.",
                    "엘라의 눈꺼풀이 움직였다.",
                    "+(이건 자살행위다.)",
                    "+...서둘러 손을 뗐다."
                ])
        elif choice == "butt":
            if affection >= 50:
                yield ui.dialog([
                    "손을 뻗어 엘라의 엉덩이에 살짝 닿았다.",
                    "+...탄력이 있다.",
                    "엘라가 잠결에 몸을 뒤척였다.",
                    "+...깨지 않았다. 다행이다."
                ])
            else:
                yield ui.dialog([
                    "손을 뻗어 엘라의 엉덩이에 살짝 닿았다.",
                    "+...탄력이 있다.",
                    "엘라가 잠결에 손목을 잡았다.",
                    "+(심장이 멎을 뻔했다.)",
                    "+...잠꼬대인 것 같다. 서둘러 빼냈다."
                ])
        elif choice == "kiss":
            if affection >= 50:
                yield ui.dialog([
                    "엘라의 얼굴에 가까이 다가갔다.",
                    "잠든 엘라의 이마에 살짝 키스했다.",
                    "+엘라의 표정이 살짝 부드러워졌다.",
                    "깨어있을 때는 보기 힘든 표정이다.",
                    "+...깨지 않았다."
                ])
            else:
                yield ui.dialog([
                    "엘라의 얼굴에 가까이 다가갔다.",
                    "잠든 엘라의 이마에 가볍게 키스했다.",
                    "+엘라의 미간이 움찔했다.",
                    "(깨면 팔이 분질러진다.)",
                    "+...서둘러 물러났다."
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
        # x: Location 내 목표 좌표 (Pi-World, 1unit/sec 기준)
        # 은신처(180), 약국(180), 편의점(180), 도시입구(600)
        {"name": "기상", "region_id": 2, "location_id": 5, "x": 90, "start": 360 * _M, "end": 390 * _M, "activity": "준비"},
        {"name": "목욕", "region_id": 2, "location_id": 5, "x": 150, "start": 390 * _M, "end": 420 * _M, "activity": "목욕"},
        {"name": "아침식사", "region_id": 2, "location_id": 5, "x": 90, "start": 420 * _M, "end": 480 * _M, "activity": "식사"},
        {"name": "정찰", "region_id": 2, "location_id": 3, "x": 90, "start": 540 * _M, "end": 660 * _M, "activity": "순찰"},  # 약국
        {"name": "물자수집", "region_id": 2, "location_id": 2, "x": 90, "start": 660 * _M, "end": 720 * _M, "activity": "탐색"},  # 편의점
        {"name": "점심식사", "region_id": 2, "location_id": 5, "x": 90, "start": 720 * _M, "end": 780 * _M, "activity": "식사"},
        {"name": "관리", "region_id": 2, "location_id": 5, "x": 90, "start": 780 * _M, "end": 960 * _M, "activity": "관리"},
        {"name": "정찰", "region_id": 2, "location_id": 0, "x": 300, "start": 960 * _M, "end": 1020 * _M, "activity": "순찰"},  # 도시입구
        {"name": "저녁식사", "region_id": 2, "location_id": 5, "x": 90, "start": 1080 * _M, "end": 1140 * _M, "activity": "식사"},
        {"name": "휴식", "region_id": 2, "location_id": 5, "x": 90, "start": 1140 * _M, "end": 1320 * _M, "activity": "휴식"},
        {"name": "수면", "action": "stay", "start": 1320 * _M, "end": 360 * _M, "activity": "수면"},
    ]

    owner_unique_id = "ella"
    sleep_location = {"region_id": 2, "location_id": 5, "x": 50}  # 은신처 (유키 침낭 공유)
    bath_location = {"region_id": 2, "location_id": 5, "x": 150}  # 은신처 드럼통

    def __init__(self, unit_id):
        super().__init__(unit_id)
        self.set_base_schedule(self.SCHEDULE)
