# assets/characters/faye.py - 페이 캐릭터 Asset
#
# ============================================================
# 캐릭터 설정
# ============================================================
# 이름: 페이 (Faye)
# 성별: 여성
# 나이: 20대 후반 (추정)
#
# 외모:
#   - 붉은 단발, 황금색 눈
#   - 날렵하고 자신감 넘치는 인상
#
# 성격:
#   - 자신만만·실용적·직선적
#   - 내면적 외로움 (떠돌이 상인의 고독)
#   - 호감이 쌓이면 devoted 반전 (의지하기 시작함)
#
# 말투:
#   - 반말·상인 구어체 ("나쁘지 않네", "얼마짜린지 알아?")
#   - 자신감 있는 어조, 가끔 상인 특유의 능글맞음
#
# 스케줄 (떠돌이 상인):
#   - 월/화/수 08:00~20:00 → 도시 입구 (Region 2, Location 0)
#   - 목/금 08:00~20:00   → 숲 오두막 (Region 3, Location 5)
#   - 야간 / 토/일         → 상인 대기소 (Region 10) — 사라짐
#
# 거래 아이템: 씨앗류 + 성인용품 (매일 아침 리셋)
# 세력: "행상" (독립 중립)
#
# ============================================================

import morld
import ui
from assets.base import Character, build_focus_rules, build_describe_rules
from think import BaseAgent, register_agent_class

_M = 60_000  # millis per minute

# ========================================
# 거래 아이템 (매일 아침 리셋)
# (unique_id, count, price_gold)
# ========================================
TRADE_STOCK = [
    # ── 씨앗류 ──
    ("seed_potato",        2, 15),
    ("seed_tomato",        2, 15),
    ("seed_carrot",        2, 15),
    ("seed_herb",          2, 20),
    ("seed_cabbage",       2, 15),
    ("seed_sweet_potato",  1, 20),
    ("seed_corn",          1, 20),
    ("seed_garlic",        1, 25),
    ("seed_onion",         1, 15),
    ("seed_pumpkin",       1, 20),
    # ── 성인용품 (소모성) ──
    ("condom",             3, 15),
    ("contraceptive_pill", 2, 25),
    ("aphrodisiac",        1, 50),
    ("lubricant",          2, 15),
    ("stamina_potion",     1, 40),
    ("ovulation_inducer",  1, 50),
    # ── 성인용품 (삽입형) — 재사용 가능, 1개씩 ──
    ("vibrator",           1, 65),
    ("dildo",              1, 40),
    ("rotor",              1, 30),
    ("anal_plug",          1, 25),
    # ── 성인용품 (착용형 소품) ──
    ("nipple_clamp",       1, 25),
    ("blindfold",          1, 15),
    # ── 실용품 ──
    ("simple_water_bottle", 2, 10),
]

# 가격 조회용 딕셔너리
_TRADE_PRICES = {uid: price for uid, _count, price in TRADE_STOCK}

# ========================================
# 재구매(Buyback) 설정
# ========================================
BUYBACK_MAX_ITEMS  = 10    # 일반 아이템 보관 한도 (퀘스트 아이템 제외)
_TRADE_STOCK_IDS   = {uid for uid, _, _ in TRADE_STOCK}  # 판매 불가 아이템
_BUYBACK_SELL_RATIO = 0.5  # 판매 가격 = 정가 × 50%


# ========================================
# FayeAgent 스케줄 헬퍼 함수 (모듈 레벨)
# ========================================

LIMBO_REGION   = 10
LIMBO_LOCATION = 0

_SCHEDULE = [
    # 월/화/수 (0~2): 도시 입구 (Region 2, Location 0)
    {"days": {0, 1, 2}, "region_id": 2, "location_id": 0},
    # 목/금 (3~4): 숲 오두막 (Region 3, Location 5)
    {"days": {3, 4}, "region_id": 3, "location_id": 5},
    # 토/일 (5~6): 비활성 (None)
]

_WORK_START_MINUTES = 8 * 60    # 08:00
_WORK_END_MINUTES   = 20 * 60   # 20:00


def _get_day_of_week(time_info):
    """게임 내부 날짜 → 요일 (0=월, ..., 6=일)"""
    year  = time_info.get("year",  1)
    month = time_info.get("month", 1)
    day   = time_info.get("day",   1)
    total = (year - 1) * 365 + (month - 1) * 30 + (day - 1)
    return total % 7


def _get_absolute_day(time_info):
    """전체 날 수 (리셋 판정용)"""
    year  = time_info.get("year",  1)
    month = time_info.get("month", 1)
    day   = time_info.get("day",   1)
    return (year - 1) * 365 + (month - 1) * 30 + (day - 1)


def _get_time_minutes(time_info):
    """현재 시각을 분 단위로 반환 (0~1439)"""
    hour   = time_info.get("hour",   0)
    minute = time_info.get("minute", 0)
    return hour * 60 + minute


def _get_active_schedule(time_info):
    """현재 시간에 활성화된 스케줄 반환. 비활성이면 None."""
    dow     = _get_day_of_week(time_info)
    minutes = _get_time_minutes(time_info)

    if minutes < _WORK_START_MINUTES or minutes >= _WORK_END_MINUTES:
        return None  # 야간

    for entry in _SCHEDULE:
        if dow in entry["days"]:
            return entry

    return None  # 토/일


def _teleport_to_limbo(unit_id, current_loc):
    """퇴근 텔레포트 — 플레이어가 같은 위치에 있으면 행동 로그 출력"""
    player_id = morld.get_player_id()
    if player_id and current_loc:
        player_loc = morld.get_unit_location(player_id)
        if (player_loc
                and player_loc[0] == current_loc[0]
                and player_loc[1] == current_loc[1]):
            morld.add_action_log("페이가 어디론가 사라졌습니다.")
    morld.set_unit_location(unit_id, LIMBO_REGION, LIMBO_LOCATION)


def _reset_trade_items(unit_id, keep_item_ids=None):
    """
    거래 아이템 리셋 + HP 최대치 회복
    호감도·욕망·관계 props는 유지됨

    keep_item_ids: 삭제하지 않을 아이템 ID 집합 (buyback 아이템)
    """
    max_hp = morld.get_unit_prop(unit_id, "생존:최대체력") or 100
    morld.set_unit_prop(unit_id, "생존:체력", max_hp)

    keep = keep_item_ids or set()
    inventory = morld.get_unit_inventory(unit_id) or {}
    for item_id_str, count in list(inventory.items()):
        item_id = int(item_id_str)
        if item_id not in keep:
            morld.remove_item(unit_id, item_id, count)

    from assets.registry import get_or_create_item_id
    for unique_id, count, _price in TRADE_STOCK:
        item_id = get_or_create_item_id(unique_id)
        if item_id:
            morld.give_item(unit_id, item_id, count)


# ========================================
# 캐릭터 오버레이: 3인칭 묘사 (CHARACTER_REACTIONS)
# ========================================


# ========================================
# Faye 캐릭터 클래스
# ========================================

class Faye(Character):
    unique_id = "faye"
    name = "페이"

    def __init__(self):
        super().__init__()
        self._buyback_queue    = []   # [item_id, ...] FIFO (오래된 것 앞)
        self._buyback_quest_ids = set()  # quest 아이템 item_id (영구 보관)

    def _add_buyback_item(self, item_id: int, is_quest: bool):
        """판매된 아이템을 buyback 목록에 추가"""
        if is_quest:
            self._buyback_quest_ids.add(item_id)
        else:
            self._buyback_queue.append(item_id)

    type = "character"
    sexual_orientation = "heterosexual"
    shame_sensitivity = 0.5
    _DEFAULT_ARCHETYPE = "proud"

    props = {
        "성별": 2, "성적지향": 1,
        "외모:붉은단발": 1, "외모:황금색눈": 1,
        "성격:자신만만": 1, "성격:실용적": 1,
        "나이": 17,
        "상태:성욕": 0, "상태:질투": 0,
        "상태:피로": 0, "상태:기분": 5,
        "can:lie_down": 1,
        "can:sleep": 0,
        "can:bath": 0,
        "생존:체력": 80, "생존:최대체력": 80,
        "처녀:구강": 1,
        "처녀:음부": 1,
        "처녀:항문": 1,
        "근력": 3, "체력": 4,
        "체격": 2, "가슴:크기": 2,
        "전투:공격력": 4, "전투:방어력": 3, "전투:명중": 70,
        "전투:회피": 15, "전투:치명타": 3, "전투:사거리": 50, "전투:공격속도": 1.0,
        "세력": "행상",
        "소지금": 500,  # 페이 자신의 소지금
    }

    actions = [
        "call:talk:대화",
        "call:buy_items:구매",
        "call:sell_items:판매",
        "call:buyback_items:재구매",
        "call:give_gift:선물하기",
        "call:recruit:분대 모집#",
        "call:assign_leader:분대장 지정#",
        "call:set_order:지시#",
        "call:romance:애정행위#",
        "call:force_romance:강제 행위#",
        "call:debug_props:(디버그) 속성 보기#",
        "call:debug_affection_up:(디버그) 호감도 +10#",
        "call:debug_affection_down:(디버그) 호감도 -10#",
        "call:debug_arousal_up:(디버그) 성욕 +20#",
        "call:debug_arousal_down:(디버그) 성욕 -20#",
        "call:debug_work_order:(디버그) 작업지시#",
    ]

    COMBAT_LINES = {
        "attack":  ["페이가 날쌔게 공격한다.", "페이의 황금색 눈이 번뜩인다."],
        "low_hp":  ["\"...이거 좀 불리한데.\" 페이가 중얼거린다."],
        "death":   ["페이가 쓰러지며 '...나쁜 장사였어.' 라고 중얼거린다."],
        "flee":    ["페이가 재빠르게 물러난다."],
    }

    # ========================================
    # 대화 주제 목록
    # ========================================
    TALK_TOPICS = [
        "잡담",
        "본인에 대해",
    ]

    # ========================================
    # 대화 규칙
    # ========================================
    TALK_RULES = {
        "잡담": [
            ({"activity": "수면"}, {"pages": ["(자고 있다)"]}),
            # 환경/flavor 반응
            ({"flavor": "자세정리"}, {"pages": ["뭐야, 쳐다보지 마.", "...볼 거 없어."]}),
            ({"flavor": "시선"}, {"pages": ["...뭔가 할 말 있어?", "...쳐다보지 마."]}),
            ({"flavor": "경계"}, {"pages": ["...조용히 해.", "...뭔가 이상한 기척이..."]}),
            ({"flavor": "불멍"}, {"pages": ["......", "...불은 좋지."]}),
            # 호감도 기반
            ({"호감": 70}, {"pages": [
                "왔네.",
                "...뭐야, 얼굴 보러 온 거야?",
                "나쁘지 않은데.",
            ]}),
            ({"호감": 40}, {"pages": [
                "어, 왔어.",
                "또 뭐 살 거야?",
            ]}),
            ({}, {"pages": [
                "어서 와.",
                "뭐 필요한 거 있어?",
            ]}),
        ],
        "본인에 대해": [
            ({"activity": "수면"}, {"pages": ["(자고 있다)"]}),
            ({"호감": 70}, {"pages": [
                "나?",
                "...이것저것 돌아다니며 파는 상인이야.",
                "대단한 건 없어.",
                "근데 뭐가 궁금한 거야? 쑥스럽게.",
            ]}),
            ({"호감": 40}, {"pages": [
                "페이야.",
                "떠돌이 상인.",
                "좋은 물건 있으면 사.",
            ]}),
            ({}, {"pages": [
                "페이.",
                "상인이야. 그 이상은 딱히 없어.",
            ]}),
        ],
    }

    # ========================================
    # Describe 규칙
    # ========================================
    DESCRIBE_RULES = build_describe_rules(
        "proud",
        traveling=[
            ({"is_traveling": True}, "{name}(이)가 어딘가로 이동 중이다."),
        ],
        activities=[
            ("영업", "{name}가 무언가를 늘어놓으며 손님을 기다리고 있다."),
            ("대기", "{name}가 어딘가 먼 곳을 보고 있다."),
            ("휴식", "{name}가 벽에 기대어 쉬고 있다."),
        ],
        default_text="{name}가 자신만만하게 서 있다.",
        order=["specials", "traveling", "semen", "internal_semen",
               "desire", "affection", "activity", "default", "fatigue"],
    )

    # ========================================
    # NPC 주도 설정
    # ========================================
    self_comfort_threshold = 80
    self_comfort_max_length = 150
    toy_preferences = {"vibrator": 0.5, "rotor": 0.4, "dildo": 0.3}

    INITIATIVE_CONFIG = {
        "arousal_threshold": 70,
        "affection_threshold": 60,
        "cooldown_millis": 480 * _M,
    }

    NPC_THRUST_CONFIG = {
        "entry_arousal": 55,
        "entry_gauge": 40,
        "gentle_arousal": 55,
        "normal_arousal": 65,
        "rough_arousal": 80,
        "escalation_chance": 0.2,
    }

    INITIATIVE_ACTION_FILTERS = [
        ({"호감": 95}, ["hug", "deep_kiss", "breast_touch", "genital_caress", "clit_rub", "penis_touch", "penis_rub", "fellatio"]),
        ({"호감": 85}, ["hug", "deep_kiss", "breast_touch", "genital_caress", "clit_rub", "penis_touch"]),
        ({"호감": 75}, ["hug", "deep_kiss", "breast_touch", "genital_caress"]),
        ({"호감": 60}, ["hug", "deep_kiss"]),
        ({}, ["hug"]),
    ]

    INITIATIVE_REACTIONS = {
        "start": [
            ({"성욕": 80}, ["...이리 와.", "......(다가와 팔을 잡아당긴다)"]),
            ({}, ["...잠깐 비는 거야?", "...(슬쩍 다가온다)"]),
        ],
        "during_hug": [
            ({"성욕": 60}, ["페이가 거칠게 안아오고 있다."]),
            ({}, ["페이가 조용히 안아온다.", "페이의 심장이 빠르게 뛰고 있다."]),
        ],
        "during_deep_kiss": [
            ({"성욕": 70}, ["페이가 거친 숨을 몰아쉬며 키스를 이어가고 있다."]),
            ({}, ["페이가 눈을 감고 키스하고 있다. 자신만만한 표정이 사라졌다."]),
        ],
        "escape_fail": [
            ({}, ["...어딜 가려고?", "...아직이야."]),
        ],
        "satisfied": [
            ({"호감": 60}, ["...나쁘지 않았어.", "......(조용히 웃는다)"]),
            ({}, ["...됐어.", "...가도 돼."]),
        ],
    }

    STEALTH_REACTIONS = {
        "text": [
            ({"성욕": 50}, ["...심장 떨렸잖아.", "...(슬쩍 당신 쪽으로 다가온다)"]),
            ({}, ["...위험했네.", "...조심해."]),
        ],
        "effects": {"호감": 1},
    }

    FRIENDLY_TALK_CONFIG = {
        "high": {
            "dialog": [
                "...",
                "어, 왔어.",
                "...얼굴 보러 온 거지, 뭐.",
            ],
            "progress_cap": 3,
        },
        "mid": {
            "dialog": [
                "어.",
                "또 왔네.",
                "...나쁘지 않아.",
            ],
            "progress_cap": 3,
        },
    }

    PROGRESS_DIALOGS = {
        1: {
            "fallback": ["어, 왔어.", "...뭐야."],
            "dialog": [
                "나에 대해 궁금해?",
                "...뭐 특별한 건 없어.",
                "이것저것 돌아다니며 파는 거야.",
                "이 동네 저 동네 다 다녀봤어.",
                "...근데 항상 혼자야.",
                "그게 편하기도 하고 불편하기도 하고.",
                "......",
                "뭐야, 왜 그런 눈으로 봐.",
            ],
        },
        2: {
            "fallback": [
                "어.",
                "...왔어.",
            ],
            "dialog": [
                "좋아하는 거?",
                "...돈이지, 뭐.",
                "근데...",
                "...사람들이 물건 사고 기뻐하는 거 보는 것도 싫지 않아.",
                "씨앗 사서 뭔가 키운다고 하면...",
                "...뭔가 뿌듯하더라고.",
                "......",
                "웃기지? 상인 주제에.",
                "...{player_name}한테는 말해도 될 것 같아서.",
            ],
        },
        3: {
            "fallback": [
                "......",
                "...(먼 곳을 보고 있다)",
            ],
            "dialog": [
                "외롭냐고?",
                "......",
                "...뭐, 그럴 때도 있지.",
                "이 동네 저 동네 다니다 보면...",
                "...어디가 내 자리인지 모르겠을 때가 있어.",
                "......",
                "근데 여기 오면...",
                "...조금은 괜찮은 것 같아.",
                "...뭐, 그냥 장사가 잘 돼서 그런 거겠지.",
                "......",
            ],
        },
    }

    ROMANCE_SOUND_PROFILE = {"levels": [5, 15, 25], "ecstasy": 45}

    ROMANCE_DISCOVERY_REACTIONS = {
        "default": {
            "text": ["...", "...(슬쩍 눈을 돌린다)", "...자기들끼리 잘 하네."],
            "exposed_text": ["...", "...문 잠그는 법은 알지?", "...장사 방해하지 마."],
            "effects": {"호감": -2, "반발": 2},
        },
    }

    GIFT_PREFERENCES = {
        "liked_categories": ["food_ingredient", "drink_ingredient", "trinket"],
        "favorite_items": [],
        "disliked_categories": [],
        "favorite_foods": [],
    }

    SEXUAL_PREFERENCES = {
        "preferred_positions": ["cowgirl", "missionary"],
        "preferred_parts": ["V", "C"],
        "dominance": 0.6,
        "restraint_preference": 0.1,
    }

    REACTION_PROFILE = {
        "name": "페이",
        "archetype": "proud",
    }

    ROMANCE_REACTIONS = {
        "hug:start": [
            ({"once": True, "호감": 50}, ["...뭐야. ...놓지 마."]),
            ({"once": True}, ["...허락한 적 없는데."]),
            ({}, "_generate_dialogue"),
        ],
        "french_kiss:start": [
            ({"반발": 30}, ["...한 번 더 하면 후회해.", "...(날카로운 눈빛)", "...입술 치워."]),
            ({"반발": 15}, ["...그만해.", "...쓸데없잖아."]),
            ({"미경험:기억:첫키스": 1}, ["......!", "...이건... 예상 밖이야.", "...(동요를 숨기려 하지만 귀끝이 빨갛다)"]),
            ({"경험:총만남횟수": 10}, ["...키스하고 싶었어.", "...(눈을 감으며) ...응..."]),
            ({"호감": 50}, ["...으응...", "...놓지 마...", "...더... 해줘..."]),
            ({}, ["...으응...", "......(눈을 감는다)", "...더 해도 돼..."]),
        ],
        "deep_kiss:start": [
            ({"반발": 30}, ["...죽는다.", "...(이를 악물며 밀어낸다)", "...경고했어."]),
            ({"반발": 15}, ["...놔.", "...관심 없어."]),
            ({"성욕": 40}, ["...으응... 더... 해줘..."]),
            ({"호감": 30}, ["......(눈을 감으며 다가온다)"]),
            ({}, ["......", "...키스...", "...눈 감아."]),
        ],
        "thrust_normal:during": [
            ({"반발": 30}, ["페이가 차갑게 굳어 있다.", "페이가 천장을 응시하고 있다."]),
            ({"크기통증": 1}, ["\"...커...! 아프지만... 좋아!\"", "\"으앗... 아파... 근데 이상해...\""]),
            ({"성욕": 90}, ["페이가 자제력을 완전히 잃고 매달리고 있다."]),
            ({}, ["페이가 이를 악물며 견디고 있다."]),
        ],
        "anal_insert:during": [
            ({"반발": 30}, ["페이의 눈에서 빛이 사라졌다."]),
            ({"크기통증": 1}, ["\"으...! 뒤는 좀 더 아파...!\"", "페이가 시트를 움켜쥐며 버티고 있다."]),
            ({"성욕": 90}, ["페이가 자제력을 잃고 떨고 있다."]),
            ({}, ["페이가 이를 악물며 참고 있다."]),
        ],
        "hold_back_success:start": [
            ({"반발": 30}, ["페이가 차갑게 본다. \"...당연하지.\"", "\"...그 정도는 해야지.\""]),
            ({}, ["페이가 웃는다. \"참았네! 대단한데?\"", "\"으응, 잘 참았어!\" 페이가 안심한다."]),
        ],
        "hold_back_failure:start": [
            ({"반발": 30}, ["페이가 날카롭게 내려다본다. \"...또?\"", "\"...각오해.\""]),
            ({}, ["페이가 놀란다. \"에...!? 안에...!?\"", "\"아, 안에 나왔어...!\" 페이가 당황한다."]),
        ],
        "ejaculation_internal_음부:start": [
            ({"반발": 30}, ["...안에...? ...죽여버린다.", "...(살기가 폭발한다)"]),
            ({"성욕": 80, "경험:질내사정": 5}, ["...안에 쏟아. 상관없어.", "...또 임신이라도 하는 거야?"]),
            ({"경험:질내사정": 3}, ["...또야? ...이제 익숙해.", "...예상 범위야."]),
            ({}, "_generate_dialogue"),
        ],
        "ecstasy:start": [
            ({"반발": 30}, ["...이런 몸으로... 경멸스러워.", "...용서 안 해."]),
            ({"반발": 15}, ["...가게 하다니... 굴욕이야.", "...잊지 않을 거야."]),
            ({"미경험:기억:첫절정": 1}, ["......?!", "...이런 건... 처음이야...", "...(동요를 감추려 하지만 몸이 떨리고 있다)"]),
            ({"경험:절정:V": 10}, ["...또... 가잖아...", "...(담담하게 몸을 맡기며) ...놓지 마..."]),
            ({}, "_generate_dialogue"),
        ],
        "forced_start:start": [
            ({"경험:강제횟수": 5}, ["...또? ...(냉정한 눈으로 노려본다.)"]),
            ({}, ["미쳤어?! 당장 놔!"]),
        ],
        "forced_ecstasy:start": [
            ({"경험:강제횟수": 5}, ["...젠장... (이를 악문다.)"]),
            ({}, ["이런...! 죽여버릴 거야...!"]),
        ],
        "forced_break_free:start": [
            ({}, ["한 번만 더 이러면 진짜 죽는다.", "...다음은 없어."]),
        ],
        "trance:start": [
            ({"반발": 30}, ["...몸이 반응한다고... 마음까지 열린 건 아니야.", "...죽여버릴 거야."]),
            ({"성욕": 80}, ["...하...! 멈추지 마... 더...", "...자신만만함 따위... 이미 무너졌어..."]),
            ({}, ["...! 몸이... 말을 안 들어...", "...(이를 악물지만 몸이 반응하고 있다.)"]),
        ],
        "trance_insert:start": [
            ({"반발": 30}, ["...몸이 제멋대로... 하지만 네 탓이야.", "...(날카로운 눈으로) ...끝나면 죽는다."]),
            ({"성욕": 80}, ["...안에 넣어. 지금 당장.", "...참을 수 없어... 넣을게..."]),
            ({}, ["...(무의식적으로 허리를 밀착하고 있다.)", "...몸이... 제멋대로..."]),
        ],
        "npc_thrust_trance:start": [
            ({"성욕": 80}, ["페이가 자신만만한 표정으로 허리를 흔들기 시작했다.", "\"...내가 해줄게.\" 페이가 스스로 움직이기 시작했다."]),
            ({}, ["페이가 말없이 스스로 허리를 움직이기 시작했다."]),
        ],
        "npc_position_request:cowgirl": [
            ({"성욕": 80}, ["\"...내가 위에서 할 거야. 넌 잠자코 있어.\"", "\"...주도권은 내가 가져갈게.\" 페이가 몸을 일으키려 한다."]),
            ({}, ["페이가 당당히 몸을 일으키려 한다.", "페이가 위에 올라타려는 몸짓..."]),
        ],
        "npc_position_request:missionary": [
            ({"성욕": 80}, ["\"...제대로 해. 마주보고.\"", "\"...당당히. 얼굴 보면서 하자.\""]),
            ({}, ["페이가 몸을 뒤로 누웠다.", "페이가 마주보기를 요구하는 듯한 눈빛..."]),
        ],
        "npc_block_player:start": [
            ({"호감": 60}, [
                "...급한 거야? 내가 해줄게.",
                "...기다려. 내가 하겠어.",
            ]),
            ({"반발": 30}, ["...닿지 마.", "...(날카로운 눈빛으로 손을 비튼다)"]),
            ({}, ["...허락한 적 없어.", "...건드리지 마.", "...(손을 치운다)"]),
        ],
        "demand_dirty_talk:start": [
            ({"성욕": 70, "호감": 50}, [
                "...느껴... 안에... 가득... 더 줘...",
                "...뜨거워... 안이... 조여져...",
            ]),
            ({"호감": 50}, ["...그런 거 왜 요구해.", "...원하면... 거기... 느껴..."]),
            ({}, ["...거부야.", "...역겨워."]),
        ],
        "beg:start": [
            ({"성욕": 70}, ["...알았어. 원하는 대로.", "...(한숨) ...어쩔 수 없네."]),
            ({}, ["...애원해봤자야.", "...초라하네."]),
        ],
        "afterglow_sensitive:start": [
            "...건드리지 마... 아직...",
            "...(입술을 깨물며) ...만지지 마...",
        ],
        "afterglow_trembling:start": [
            "...아직... 됐어...",
            "...(떨림을 억누르며 침묵한다)",
        ],
        "afterglow_fading:start": [
            "...(자신만만한 표정을 되찾는다)",
        ],
        "afterglow_end:start": [
            "...됐어.",
            "...(아무 일도 없었다는 듯)",
        ],
    }

    # ========================================
    # Focus 규칙
    # ========================================
    FOCUS_RULES = build_focus_rules(
        "proud",
        activities=[
            ("영업", "무언가를 늘어놓으며 손님을 기다리고 있다."),
            ("대기", "팔짱을 끼고 먼 곳을 보고 있다."),
            ("휴식", "벽에 기대어 쉬고 있다."),
        ],
        default_text="붉은 단발의 자신만만한 여성. 황금색 눈이 인상적이다.",
        order=["specials", "semen", "internal_semen",
               "desire", "affection", "activity", "mood", "default"],
    )

    # ========================================
    # 첫 만남 이벤트
    # ========================================
    def _first_meet_handler(self, player_id):
        """첫 만남 — 상인 자기소개"""
        conv = ui.Conversation("페이")

        conv.narration(
            "붉은 단발의 여성이 무언가를 늘어놓고 있다.",
            "황금색 눈이 당신을 훑어본다.",
            "자신만만한 웃음이 번진다."
        )

        conv.say(
            "어, 처음 보는 얼굴이네.",
            "나는 페이. 여기저기 돌아다니는 상인이야.",
            "좋은 물건 많으니까 구경해봐.",
            "뭐, 살 만한 거 있으면 사고."
        )

        conv.ask([
            ("뭘 팔아?", "what"),
            ("여기 자주 와?", "often"),
            ("(헤어지기)", "@exit"),
        ])

        conv.respond("what",
            "씨앗이랑... 뭐, 이것저것.",
            "필요한 거 있으면 '구매' 눌러봐.",
            "매일 아침 새 물건 들어오니까 자주 와도 돼."
        )

        conv.respond("often",
            "월수금... 아니, 월화수는 여기, 목금은 숲 오두막 쪽에 있어.",
            "주말이나 밤에는... 뭐, 쉬어야지.",
            "일정 잘 기억해둬. 헛걸음하면 귀찮잖아."
        )

        yield conv.end()

        morld.set_npc_time_consume(self.instance_id, "stay", 1 * _M)
        morld.set_npc_job(self.instance_id, "stay", 2 * _M)
        self.mark_first_meet_done(player_id)

    # ========================================
    # 거래 UI (focus 직접 액션 — while 루프형)
    # ========================================
    def buy_items(self, context):
        """구매 UI — 닫기 전까지 반복 거래 가능"""
        player_id = morld.get_player_id()
        if not player_id:
            return

        while True:
            player_gold = morld.get_unit_prop(player_id, "소지금") or 0
            inventory   = morld.get_unit_inventory(self.instance_id) or {}

            item_entries = []
            for item_id_str, count in inventory.items():
                item_id = int(item_id_str)
                info = morld.get_item_info(item_id)
                if not info:
                    continue
                uid   = info.get("unique_id", "")
                name  = info.get("name", "???")
                price = _TRADE_PRICES.get(uid, info.get("value", 10))
                item_entries.append((item_id, uid, name, price, count))

            if not item_entries:
                morld.add_action_log("페이: ...오늘 재고가 다 나갔어. 내일 다시 와.")
                return

            lines = [f"[페이]\n소지금: {player_gold}G\n"]
            for item_id, uid, name, price, count in item_entries:
                affordable = "★" if player_gold >= price else "  "
                lines.append(f"{affordable}[url=@ret:{item_id}]{name}[/url] — {price}G (x{count})")
            lines.append("\n[url=@ret:]닫기[/url]")

            result = yield ui.dialog("\n".join(lines), autofill="off")
            if not result:
                return

            selected_id = int(result)
            info = morld.get_item_info(selected_id)
            if not info:
                continue

            uid   = info.get("unique_id", "")
            name  = info.get("name", "???")
            price = _TRADE_PRICES.get(uid, info.get("value", 10))

            player_gold = morld.get_unit_prop(player_id, "소지금") or 0
            if player_gold < price:
                morld.add_action_log(f"페이: 소지금이 부족해. {price}G 필요해.")
                continue

            if not morld.has_item(self.instance_id, selected_id):
                morld.add_action_log("페이: ...방금 다 팔렸어. 내일 다시 와.")
                continue

            morld.set_unit_prop(player_id, "소지금", player_gold - price)
            morld.remove_item(self.instance_id, selected_id, 1)
            morld.give_item(player_id, selected_id, 1)
            morld.add_action_log(f"[구매] {name} — {price}G 지불. 페이: \"...좋은 선택이네.\"")

    def sell_items(self, context):
        """판매 UI — 닫기 전까지 반복 거래 가능"""
        player_id = morld.get_player_id()
        if not player_id:
            return

        while True:
            player_gold = morld.get_unit_prop(player_id, "소지금") or 0
            inventory   = morld.get_unit_inventory(player_id) or {}

            sellable = []
            for item_id_str, count in inventory.items():
                item_id = int(item_id_str)
                info = morld.get_item_info(item_id)
                if not info:
                    continue
                uid = info.get("unique_id", "")
                if uid in _TRADE_STOCK_IDS:
                    continue  # 페이 재고 아이템은 판매 불가
                name       = info.get("name", "???")
                base_price = _TRADE_PRICES.get(uid, info.get("value", 10) or 10)
                sell_price = max(1, int(base_price * _BUYBACK_SELL_RATIO))
                sellable.append((item_id, uid, name, sell_price, count))

            if not sellable:
                morld.add_action_log("페이: ...팔 물건이 없는 것 같은데.")
                return

            lines = [f"[페이]\n소지금: {player_gold}G\n"]
            for item_id, uid, name, sell_price, count in sellable:
                lines.append(f"[url=@ret:{item_id}]{name}[/url] — {sell_price}G (x{count})")
            lines.append("\n[url=@ret:]닫기[/url]")

            result = yield ui.dialog("\n".join(lines), autofill="off")
            if not result:
                return

            selected_id = int(result)
            info = morld.get_item_info(selected_id)
            if not info or not morld.has_item(player_id, selected_id):
                continue

            uid        = info.get("unique_id", "")
            name       = info.get("name", "???")
            base_price = _TRADE_PRICES.get(uid, info.get("value", 10) or 10)
            sell_price = max(1, int(base_price * _BUYBACK_SELL_RATIO))

            player_gold = morld.get_unit_prop(player_id, "소지금") or 0
            morld.remove_item(player_id, selected_id, 1)
            morld.give_item(self.instance_id, selected_id, 1)
            morld.set_unit_prop(player_id, "소지금", player_gold + sell_price)

            is_quest = (morld.get_unit_prop(selected_id, "quest") or 0) > 0
            self._add_buyback_item(selected_id, is_quest)
            morld.add_action_log(f"[판매] {name} — {sell_price}G 수령. 페이: \"...언제든 되살 수 있어.\"")

    def buyback_items(self, context):
        """재구매 UI — 닫기 전까지 반복 거래 가능"""
        player_id = morld.get_player_id()
        if not player_id:
            return

        while True:
            all_buyback = list(self._buyback_quest_ids) + list(self._buyback_queue)
            if not all_buyback:
                morld.add_action_log("페이: ...맡겨둔 물건이 없어.")
                return

            player_gold = morld.get_unit_prop(player_id, "소지금") or 0
            lines = [f"[페이]\n소지금: {player_gold}G\n맡겨둔 물건:\n"]
            shown = []
            for item_id in all_buyback:
                if not morld.has_item(self.instance_id, item_id):
                    continue
                info = morld.get_item_info(item_id)
                if not info:
                    continue
                uid           = info.get("unique_id", "")
                name          = info.get("name", "???")
                is_quest      = item_id in self._buyback_quest_ids
                base_price    = _TRADE_PRICES.get(uid, info.get("value", 10) or 10)
                buyback_price = max(1, int(base_price * _BUYBACK_SELL_RATIO))
                affordable    = "★" if player_gold >= buyback_price else "  "
                quest_tag     = "[퀘] " if is_quest else ""
                lines.append(
                    f"{affordable}[url=@ret:{item_id}]{quest_tag}{name}[/url]"
                    f" — {buyback_price}G"
                )
                shown.append(item_id)

            if not shown:
                morld.add_action_log("페이: ...맡겨둔 물건이 없어.")
                return

            lines.append("\n[url=@ret:]닫기[/url]")
            result = yield ui.dialog("\n".join(lines), autofill="off")
            if not result:
                return

            selected_id = int(result)
            info = morld.get_item_info(selected_id)
            if not info or not morld.has_item(self.instance_id, selected_id):
                continue

            uid           = info.get("unique_id", "")
            name          = info.get("name", "???")
            base_price    = _TRADE_PRICES.get(uid, info.get("value", 10) or 10)
            buyback_price = max(1, int(base_price * _BUYBACK_SELL_RATIO))

            player_gold = morld.get_unit_prop(player_id, "소지금") or 0
            if player_gold < buyback_price:
                morld.add_action_log(f"페이: 소지금이 부족해. {buyback_price}G 필요해.")
                continue

            morld.remove_item(self.instance_id, selected_id, 1)
            morld.give_item(player_id, selected_id, 1)
            morld.set_unit_prop(player_id, "소지금", player_gold - buyback_price)

            self._buyback_quest_ids.discard(selected_id)
            if selected_id in self._buyback_queue:
                self._buyback_queue.remove(selected_id)
            morld.add_action_log(f"[재구매] {name} — {buyback_price}G 지불. 페이: \"...잘 쓰게.\"")


# ========================================
# AI Agent
# ========================================

@register_agent_class("faye")
class FayeAgent(BaseAgent):
    """
    페이 AI — 떠돌이 상인

    특징:
    - 요일/시간대에 따라 도시 ↔ 숲 오두막 텔레포트
    - 야간/주말엔 대기소(Region 10)로 이동 — 사라짐
    - survival/needs/temperature 미등록 (HP만 관리)
    - romance 시스템 자연 상속
    """

    owner_unique_id = "faye"

    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",
        "retreat_threshold": 0.8,
        "join_combat": False,
    }

    def __init__(self, unit_id):
        super().__init__(unit_id)
        # survival/needs/temperature 미등록 → 포만감 감소·욕구 없음
        # romance 시스템은 Character 기반으로 자동 상속
        self._last_trade_day = -1

    def _trim_buyback(self, faye_char):
        """buyback 큐 정리: BUYBACK_MAX_ITEMS 초과분 제거 (퀘스트 아이템 제외)"""
        while len(faye_char._buyback_queue) > BUYBACK_MAX_ITEMS:
            old_id = faye_char._buyback_queue.pop(0)
            if morld.has_item(self.unit_id, old_id):
                morld.remove_item(self.unit_id, old_id, 1)

    def think(self):
        time_info = morld.get_time_info()
        if not time_info:
            self._insert_idle_job("대기", _M)
            self._action_taken = True
            return

        schedule    = _get_active_schedule(time_info)
        my_loc      = self.get_location()
        current_day = _get_absolute_day(time_info)

        # ── 비활성 시간 (야간 or 주말) ──
        if schedule is None:
            if my_loc and my_loc[0] != LIMBO_REGION:
                _teleport_to_limbo(self.unit_id, my_loc)
            self._insert_idle_job("대기", _M * 60)  # 1시간 후 재판정
            self._action_taken = True
            return

        # ── 활성 시간: 날짜 변경 → 거래 아이템·HP 리셋 ──
        if current_day != self._last_trade_day:
            from assets.characters import get_instance
            faye_char = get_instance(self.unit_id)
            if faye_char:
                self._trim_buyback(faye_char)
                keep_ids = (
                    set(faye_char._buyback_quest_ids)
                    | set(faye_char._buyback_queue)
                )
            else:
                keep_ids = set()
            _reset_trade_items(self.unit_id, keep_item_ids=keep_ids)
            self._last_trade_day = current_day

        # ── 목적지 다르면 즉시 텔레포트 (출근) ──
        target_region   = schedule["region_id"]
        target_location = schedule["location_id"]
        if not my_loc or my_loc[0] != target_region or my_loc[1] != target_location:
            morld.set_unit_location(self.unit_id, target_region, target_location)

        # ── 영업 대기 ──
        self._insert_idle_job("영업", _M * 30)
        self._action_taken = True
