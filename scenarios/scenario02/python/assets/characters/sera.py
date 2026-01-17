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
    actions = ["call:talk:대화", "call:debug_props:속성 보기"]
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
