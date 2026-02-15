"""묘사 생성기 — 성격 아키타입 + 2D 좌표(감정×욕구) 기반 (:during 3인칭)

10종 아키타입 × 5 카테고리 × 4 관계톤 × 3 흥분단계 × 3 반발단계 = 풍부한 자동 반응.
네임드 NPC는 override + generator fallback, 모브 NPC는 REACTION_PROFILE만으로 전체 자동.

대사(:start 1인칭)는 romance_line_generator.py 참조.

2D 좌표 공간 (v2):
  X축: sentiment = 호감 - 반발*0.8  (-100 ~ +100)
  Y축: desire_axis = 욕망 - 순수도*0.6  (-100 ~ +100)
"""
import math
import random

# ─────────────────────────────────────────────
# 2D 좌표 공간 (v2: sentiment × desire_axis)
# ─────────────────────────────────────────────
#   욕구 ↑ (+100)
#        │
#   lust │      romance
# (-80,70)│     (80,70)
#        │
# ───────┼───────→ 감정 (+100)
#        │
# reject │     platonic
#(-80,-70)│    (80,-70)
#        │
#   순수 ↓ (-100)

TONE_COORDS = {
    "romance":   ( 80,  70),
    "platonic":  ( 80, -70),
    "lust":      (-80,  70),
    "rejection": (-80, -70),
}

REB_WEIGHT = 0.8
INN_WEIGHT = 0.6

ARCHETYPE_BASE_INNOCENCE = {
    "timid": 40, "cold": 30, "stoic": 20, "gentle": 15, "cheerful": 10,
    "innocent": 50, "devoted": 20, "seductive": 0, "fierce": 10, "proud": 25,
}


def _calc_innocence(state):
    """경험 기반 순수도 (0-100)."""
    base = ARCHETYPE_BASE_INNOCENCE.get(state.get("archetype", "stoic"), 20)
    if state.get("미경험:기억:첫키스"):
        base += 20
    if state.get("미경험:기억:첫절정"):
        base += 20
    base -= min(40, state.get("경험:총만남횟수", 0) * 2)
    return max(0, min(100, base))


def resolve_tone(state):
    """2D(sentiment × desire_axis) → nearest tone. 동률 시 랜덤.

    state dict에서 호감/반발/욕망 + 경험 플래그를 읽어
    sentiment(감정)과 desire_axis(욕구)를 계산한 뒤
    유클리드 거리로 가장 가까운 톤을 반환한다.
    """
    sentiment = max(-100, min(100,
        state.get("호감", 0) - state.get("반발", 0) * REB_WEIGHT))
    desire_axis = max(-100, min(100,
        state.get("욕망", 0) - _calc_innocence(state) * INN_WEIGHT))

    best_dist = float("inf")
    best_tones = []
    for tone, (tx, ty) in TONE_COORDS.items():
        d = math.hypot(sentiment - tx, desire_axis - ty)
        if d < best_dist - 0.01:
            best_dist = d
            best_tones = [tone]
        elif abs(d - best_dist) < 0.01:
            best_tones.append(tone)
    return random.choice(best_tones)


def resolve_arousal_tier(arousal):
    """성욕 → 흥분 단계"""
    if arousal >= 90:
        return "extreme"
    if arousal >= 70:
        return "high"
    if arousal >= 40:
        return "medium"
    return "low"


def resolve_rebellion_tier(rebellion):
    """반발 → 반발 단계 (대사 강도 cascade용). None이면 반발 무관."""
    if rebellion >= 60:
        return "rebellion_extreme"
    if rebellion >= 30:
        return "rebellion_high"
    if rebellion >= 15:
        return "rebellion_mild"
    return None


def _build_cascade_keys(base_key, arousal_tiers, rebellion_tier):
    """arousal + rebellion cascade 키 목록 (우선순위순).

    1. key:rebellion_tier:arousal_tier  (반발+흥분)
    2. key:rebellion_tier              (반발만)
    3. key:arousal_tier                (흥분만 — 기존 호환)
    4. key                             (기본)

    rebellion_tier가 None이면 3→4만 반환 (기존 동작 동일).
    """
    keys = []
    if rebellion_tier:
        for at in arousal_tiers:
            keys.append(f"{base_key}:{rebellion_tier}:{at}")
        keys.append(f"{base_key}:{rebellion_tier}")
    for at in arousal_tiers:
        keys.append(f"{base_key}:{at}")
    keys.append(base_key)
    return keys


# ─────────────────────────────────────────────
# 행위 카테고리 매핑
# ─────────────────────────────────────────────

ACTION_TO_CATEGORY = {
    # light — 가벼운 접촉
    "hug": "light", "deep_kiss": "light", "tongue_play": "light",
    "french_kiss": "light", "kiss": "light",
    "head_pat": "light", "cheek_caress": "light", "cheek_pinch": "light",
    "lip_lick": "light", "whisper": "light",
    # medium — 중간 수위
    "breast_touch": "medium", "breast_squeeze": "medium",
    "butt_squeeze": "medium", "breast_suck": "medium",
    "nipple_suck": "medium", "paizuri": "medium",
    "face_touch": "medium", "neck_touch": "medium",
    "ear_touch": "medium", "neck_kiss": "medium",
    "butt_caress": "medium", "breast_caress": "medium",
    "nipple_stimulation": "medium", "nipple_lick": "medium",
    "nipple_pinch": "medium", "breast_grab": "medium",
    # strong — 강한 자극
    "genital_touch": "strong", "clit_rub": "strong",
    "clit_lick": "strong", "cunnilingus": "strong",
    "finger_insertion": "strong", "fellatio": "strong",
    "penis_touch": "strong", "penis_rub": "strong",
    "genital_caress": "strong", "clit_stimulation": "strong",
    "anal_stimulation": "strong", "rough_finger": "strong",
    # penetration — 삽입
    "vaginal_penetration": "penetration",
    "anal_penetration": "penetration",
    "receive_penetration": "penetration",
    "receive_anal": "penetration",
    "thrust_deep": "penetration", "thrust_slow": "penetration",
    "grind": "penetration", "ejaculate": "penetration",
    # rough — 거친 행위
    "rough_thrust": "rough", "hard_anal": "rough",
}


# ─────────────────────────────────────────────
# CATEGORY_TEMPLATES — 10 아키타입 × 5 카테고리 × 4 톤 × base/high/extreme
# ─────────────────────────────────────────────

CATEGORY_TEMPLATES = {
    # ─────────────────────────────────────────────
    # LIGHT (가벼운 접촉: 포옹, 키스, 혀)
    # ─────────────────────────────────────────────
    "light:during": {
        "stoic": {
            "romance":   ["{name}가 조용히 당신에게 몸을 맡기고 있다.", "{name}의 어깨에서 힘이 빠져 있다."],
            "platonic":  ["{name}가 가만히 있다.", "{name}의 체온이 느껴진다."],
            "lust":      ["{name}가 숨을 고르고 있다.", "{name}의 호흡이 불규칙하다."],
            "rejection": ["{name}가 뻣뻣하게 서 있다.", "{name}가 미동도 없다."],
        },
        "gentle": {
            "romance":   ["{name}가 살며시 기대어 있다.", "{name}의 표정이 편안하다."],
            "platonic":  ["{name}가 조심스럽게 받아들이고 있다.", "{name}가 살짝 미소짓고 있다.", "{name}가 고개를 살짝 숙이며 수줍어하고 있다.", "{name}가 어떻게 해야 할지 몰라하고 있다."],
            "lust":      ["{name}가 작은 소리를 내고 있다.", "{name}의 손이 당신을 잡고 있다."],
            "rejection": ["{name}가 당혹스러운 표정이다.", "{name}가 어찌할 줄 모르고 있다."],
        },
        "cheerful": {
            "romance":   ["{name}가 기분 좋게 안겨 있다.", "{name}가 콧노래를 흥얼거리고 있다."],
            "platonic":  ["{name}가 씩 웃고 있다.", "{name}가 장난스럽게 받아주고 있다.", "{name}가 분위기를 모르고 히히 웃고 있다.", "{name}가 갸우뚱하며 당신을 보고 있다."],
            "lust":      ["{name}가 숨을 참으며 안겨 있다.", "{name}의 심장이 빠르게 뛰고 있다."],
            "rejection": ["{name}가 어색하게 웃고 있다.", "{name}가 살짝 밀어내고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 조용히 눈을 감고 있다.", "{name}가 살짝 떨리며 안겨 있다."],
            "platonic":  ["{name}가 얼어붙은 듯 가만히 있다.", "{name}의 볼이 붉다.", "{name}가 무슨 상황인지 이해하지 못하는 표정이다.", "{name}가 당황한 듯 눈을 깜빡이고 있다."],
            "lust":      ["{name}가 몸을 떨며 기대어 있다.", "{name}가 작게 숨을 삼키고 있다."],
            "rejection": ["{name}가 굳어 있다.", "{name}가 눈을 내리깔고 있다."],
        },
        "cold": {
            "romance":   ["{name}가 조용히 허용하고 있다.", "{name}의 표정이 미세하게 풀려 있다."],
            "platonic":  ["{name}가 무표정하게 받아들이고 있다.", "{name}가 담담히 서 있다.", "{name}가 의미를 이해 못한 듯 미간을 찌푸리고 있다.", "{name}가 무심한 듯 시선을 돌리고 있다."],
            "lust":      ["{name}의 호흡이 미세하게 흔들리고 있다.", "{name}가 태연한 척하고 있다."],
            "rejection": ["{name}가 차가운 눈으로 바라보고 있다.", "{name}가 가만히 서 있다."],
        },
        "seductive": {
            "romance":   ["{name}가 여유롭게 미소짓고 있다.", "{name}가 당신의 목에 팔을 감고 있다."],
            "platonic":  ["{name}가 의미심장하게 바라보고 있다.", "{name}가 느긋하게 받아주고 있다."],
            "lust":      ["{name}가 입술을 핥으며 당신을 바라보고 있다.", "{name}가 능숙하게 몸을 밀착하고 있다."],
            "rejection": ["{name}가 시큰둥하게 서 있다.", "{name}가 비웃듯 바라보고 있다."],
        },
        "fierce": {
            "romance":   ["{name}가 거칠게 안고 있다.", "{name}가 힘주어 끌어당기고 있다."],
            "platonic":  ["{name}가 투덜거리며 서 있다.", "{name}가 딴 곳을 보고 있다."],
            "lust":      ["{name}가 거친 숨을 내쉬고 있다.", "{name}가 당신을 움켜쥐고 있다."],
            "rejection": ["{name}가 밀어내려 하고 있다.", "{name}가 이를 드러내고 있다."],
        },
        "proud": {
            "romance":   ["{name}가 눈을 감고 허용하고 있다.", "{name}가 고개를 살짝 기울이고 있다."],
            "platonic":  ["{name}가 무관심한 척하고 있다.", "{name}가 시선을 피하고 있다."],
            "lust":      ["{name}가 입술을 깨물며 참고 있다.", "{name}의 체면이 흔들리고 있다."],
            "rejection": ["{name}가 코웃음을 치고 있다.", "{name}가 차갑게 내려다보고 있다."],
        },
        "innocent": {
            "romance":   ["{name}가 어리둥절하지만 행복해 보인다.", "{name}가 고개를 갸웃하며 미소짓고 있다."],
            "platonic":  ["{name}가 신기한 듯 가만히 있다.", "{name}가 두리번거리고 있다.", "{name}가 고개를 갸웃하며 당신을 올려다보고 있다.", "{name}가 이게 무슨 의미인지 모르는 눈이다."],
            "lust":      ["{name}가 당혹스러워하고 있다.", "{name}가 낯선 감각에 눈을 깜빡이고 있다."],
            "rejection": ["{name}가 겁먹은 표정이다.", "{name}가 뒷걸음치고 있다."],
        },
        "devoted": {
            "romance":   ["{name}가 기쁜 표정으로 안겨 있다.", "{name}가 당신에게 전적으로 기대고 있다."],
            "platonic":  ["{name}가 조심스럽게 따르고 있다.", "{name}가 눈을 반짝이고 있다."],
            "lust":      ["{name}가 당신의 옷을 움켜쥐고 있다.", "{name}가 더 가까이 붙으려 하고 있다."],
            "rejection": ["{name}가 고개를 숙이고 있다.", "{name}가 슬픈 표정이다."],
        },
    },
    "light:during:high": {
        "stoic":     {"romance": ["{name}의 심장이 빠르게 뛰는 게 느껴진다."], "lust": ["{name}가 숨을 몰아쉬고 있다."]},
        "gentle":    {"romance": ["{name}가 당신의 이름을 작게 부르고 있다."], "lust": ["{name}가 매달리듯 안겨 있다."]},
        "cheerful":  {"romance": ["{name}가 기분 좋은 소리를 내고 있다."], "lust": ["{name}의 숨소리가 거칠어지고 있다."]},
        "timid":     {"romance": ["{name}가 살짝 떨리며 당신을 잡고 있다."], "lust": ["{name}가 눈물이 글썽이고 있다."]},
        "cold":      {"romance": ["{name}의 경어가 흔들리고 있다."], "lust": ["{name}가 가드를 유지하려 애쓰고 있다."]},
        "seductive": {"romance": ["{name}가 당신의 귓볼에 숨을 불어넣고 있다."], "lust": ["{name}가 노골적으로 밀착하고 있다."]},
        "fierce":    {"romance": ["{name}가 당신을 세게 끌어당기고 있다."], "lust": ["{name}가 거칠게 숨쉬고 있다."]},
        "proud":     {"romance": ["{name}의 귀가 빨갛게 달아올라 있다."], "lust": ["{name}가 자존심과 싸우고 있다."]},
        "innocent":  {"romance": ["{name}가 따뜻함에 눈을 감고 있다."], "lust": ["{name}가 몸의 변화에 당황하고 있다."]},
        "devoted":   {"romance": ["{name}가 행복한 듯 작은 소리를 내고 있다."], "lust": ["{name}가 간절하게 매달리고 있다."]},
    },
    "light:during:extreme": {
        "stoic":     {"romance": ["{name}가 당신을 꽉 안고 놓지 않고 있다."], "lust": ["{name}의 몸이 미세하게 떨리고 있다."]},
        "gentle":    {"romance": ["{name}가 당신의 이름을 반복해서 부르고 있다."], "lust": ["{name}가 멈출 수 없다는 듯 매달려 있다."]},
        "cheerful":  {"romance": ["{name}가 웃으면서도 눈이 촉촉하다."], "lust": ["{name}가 참지 못하고 소리를 내고 있다."]},
        "timid":     {"romance": ["{name}가 당신의 옷을 꽉 잡고 놓지 않고 있다."], "lust": ["{name}가 온몸을 떨며 기대어 있다."]},
        "cold":      {"romance": ["{name}의 목소리가 떨리고 있다."], "lust": ["{name}의 냉정함이 무너지고 있다."]},
        "seductive": {"romance": ["{name}가 더 깊이 끌어들이고 있다."], "lust": ["{name}가 거칠게 당신을 탐하고 있다."]},
        "fierce":    {"romance": ["{name}가 목소리를 죽이며 안기고 있다."], "lust": ["{name}가 이성을 잃어가고 있다."]},
        "proud":     {"romance": ["{name}의 체면이 완전히 무너진 상태다."], "lust": ["{name}가 수치심에 떨며 매달리고 있다."]},
        "innocent":  {"romance": ["{name}가 이 감정이 뭔지 모르겠다는 듯 혼란스러워하고 있다."], "lust": ["{name}가 낯선 감각에 정신을 놓고 있다."]},
        "devoted":   {"romance": ["{name}가 감격한 듯 눈물을 글썽이고 있다."], "lust": ["{name}가 모든 것을 맡기고 있다."]},
    },

    # ─────────────────────────────────────────────
    # MEDIUM (중간 수위: 가슴/엉덩이 터치/주무르기/빨기)
    # ─────────────────────────────────────────────
    "medium:during": {
        "stoic": {
            "romance":   ["{name}가 고개를 돌리고 있다. 귀가 빨갛다.", "{name}가 이를 악물며 참고 있다."],
            "platonic":  ["{name}가 눈을 감고 참고 있다.", "{name}의 귀끝이 빨갛다."],
            "lust":      ["{name}가 참지 못하고 작은 소리를 내고 있다.", "{name}의 숨소리가 거칠어지고 있다."],
            "rejection": ["{name}가 불쾌한 듯 눈살을 찌푸리고 있다.", "{name}가 당신의 손을 밀어내려 하고 있다."],
        },
        "gentle": {
            "romance":   ["{name}가 작은 소리를 내며 받아들이고 있다.", "{name}가 부끄럽지만 거부하지 않고 있다."],
            "platonic":  ["{name}가 얼굴을 붉히며 참고 있다.", "{name}가 수줍게 눈을 피하고 있다.", "{name}가 놀랐지만 당신을 믿고 있는 눈이다.", "{name}가 부끄러워하면서도 거부하지 않고 있다."],
            "lust":      ["{name}가 당신의 손 위에 자기 손을 올리고 있다.", "{name}가 작은 신음을 내고 있다."],
            "rejection": ["{name}가 놀라서 몸을 움츠리고 있다.", "{name}가 당혹스러워하고 있다."],
        },
        "cheerful": {
            "romance":   ["{name}가 얼굴을 붉히며 웃고 있다.", "{name}가 장난스럽게 반응하고 있다."],
            "platonic":  ["{name}가 어색하게 웃고 있다.", "{name}가 호들갑을 떨고 있다.", "{name}가 놀라면서도 호기심 어린 눈이다.", "{name}가 뭘 하는 건지 모르겠다며 웃고 있다."],
            "lust":      ["{name}가 크게 반응하고 있다.", "{name}가 감탄사를 내고 있다."],
            "rejection": ["{name}가 놀라서 소리를 지르고 있다.", "{name}가 밀어내고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 눈을 꽉 감고 받아들이고 있다.", "{name}가 조용히 떨리고 있다."],
            "platonic":  ["{name}가 얼어붙어 있다.", "{name}가 고개를 숙이고 있다.", "{name}가 무슨 느낌인지 이해하지 못하고 떨고 있다.", "{name}가 부끄러워서 얼굴을 가리고 있다."],
            "lust":      ["{name}가 눈물이 글썽이며 떨고 있다.", "{name}가 작은 소리를 참고 있다."],
            "rejection": ["{name}가 몸을 웅크리고 있다.", "{name}가 겁에 질려 있다."],
        },
        "cold": {
            "romance":   ["{name}가 눈을 감고 허용하고 있다.", "{name}의 표정이 미세하게 변하고 있다."],
            "platonic":  ["{name}가 무표정하게 참고 있다.", "{name}가 감정을 숨기고 있다.", "{name}가 아무렇지 않은 척 눈을 돌리고 있다.", "{name}가 동요하지 않으려 애쓰고 있다."],
            "lust":      ["{name}의 호흡이 흔들리고 있다.", "{name}가 냉정을 유지하려 애쓰고 있다."],
            "rejection": ["{name}가 차가운 시선으로 제지하고 있다.", "{name}가 손목을 잡고 있다."],
        },
        "seductive": {
            "romance":   ["{name}가 만족스럽게 눈을 감고 있다.", "{name}가 당신의 손을 이끌고 있다."],
            "platonic":  ["{name}가 의미심장하게 미소짓고 있다.", "{name}가 도발적으로 바라보고 있다."],
            "lust":      ["{name}가 능숙하게 반응하고 있다.", "{name}가 당신을 유혹하듯 바라보고 있다."],
            "rejection": ["{name}가 지루하다는 듯 한숨을 쉬고 있다.", "{name}가 시선을 돌리고 있다."],
        },
        "fierce": {
            "romance":   ["{name}가 투덜거리면서도 거부하지 않고 있다.", "{name}가 이를 악물고 있다."],
            "platonic":  ["{name}가 으르렁거리듯 반응하고 있다.", "{name}가 험한 표정을 짓고 있다."],
            "lust":      ["{name}가 거칠게 숨쉬며 당신을 잡고 있다.", "{name}가 공격적으로 반응하고 있다."],
            "rejection": ["{name}가 손목을 비틀며 저항하고 있다.", "{name}가 밀쳐내고 있다."],
        },
        "proud": {
            "romance":   ["{name}가 시선을 피하며 허용하고 있다.", "{name}가 체면을 지키려 참고 있다."],
            "platonic":  ["{name}가 무심한 표정을 꾸미고 있다.", "{name}가 초연한 척하고 있다."],
            "lust":      ["{name}가 입술을 깨물며 자존심과 싸우고 있다.", "{name}의 체면이 흔들리고 있다."],
            "rejection": ["{name}가 경멸하듯 내려다보고 있다.", "{name}가 비웃고 있다."],
        },
        "innocent": {
            "romance":   ["{name}가 신기한 듯 가만히 있다.", "{name}가 고개를 갸웃하며 당신을 바라보고 있다."],
            "platonic":  ["{name}가 이게 뭔지 모르겠다는 표정이다.", "{name}가 눈을 깜빡이고 있다.", "{name}가 이상한 느낌이라며 고개를 갸웃하고 있다.", "{name}가 왜 이러는 건지 모르겠다는 표정이다."],
            "lust":      ["{name}가 낯선 감각에 놀라고 있다.", "{name}가 이상한 느낌에 눈이 커지고 있다."],
            "rejection": ["{name}가 무서운 듯 몸을 움츠리고 있다.", "{name}가 뒤로 물러나고 있다."],
        },
        "devoted": {
            "romance":   ["{name}가 기쁜 표정으로 받아들이고 있다.", "{name}가 행복한 듯 눈을 감고 있다."],
            "platonic":  ["{name}가 고분고분 따르고 있다.", "{name}가 조심스럽게 허용하고 있다."],
            "lust":      ["{name}가 더 해달라는 듯 몸을 내밀고 있다.", "{name}가 간절하게 바라보고 있다."],
            "rejection": ["{name}가 슬픈 표정으로 참고 있다.", "{name}가 고개를 떨구고 있다."],
        },
    },
    "medium:during:high": {
        "stoic":     {"romance": ["{name}가 참지 못하고 작은 소리를 냈다."], "lust": ["{name}의 숨소리가 거칠어지고 있다."]},
        "gentle":    {"romance": ["{name}가 당신의 이름을 부르며 기대고 있다."], "lust": ["{name}가 매달리듯 손을 잡고 있다."]},
        "cheerful":  {"romance": ["{name}가 부끄러워하면서도 즐기고 있다."], "lust": ["{name}가 참지 못하고 소리를 내고 있다."]},
        "timid":     {"romance": ["{name}가 떨리는 손으로 당신을 잡고 있다."], "lust": ["{name}가 눈물을 글썽이며 떨고 있다."]},
        "cold":      {"romance": ["{name}의 표정에 균열이 가고 있다."], "lust": ["{name}가 경어를 유지하지 못하고 있다."]},
        "seductive": {"romance": ["{name}가 만족스러운 숨소리를 내고 있다."], "lust": ["{name}가 노골적으로 유혹하고 있다."]},
        "fierce":    {"romance": ["{name}가 거칠게 당신을 끌어당기고 있다."], "lust": ["{name}가 이를 드러내며 숨쉬고 있다."]},
        "proud":     {"romance": ["{name}의 체면이 무너지기 시작하고 있다."], "lust": ["{name}가 수치심에 얼굴을 묻고 있다."]},
        "innocent":  {"romance": ["{name}가 이상한 느낌에 눈이 커지고 있다."], "lust": ["{name}가 모르는 감각에 당황하고 있다."]},
        "devoted":   {"romance": ["{name}가 감격한 듯 숨을 삼키고 있다."], "lust": ["{name}가 더 해달라고 조르고 있다."]},
    },
    "medium:during:extreme": {
        "stoic":     {"romance": ["{name}가 당신의 손 위에 자기 손을 올리고 있다."], "lust": ["{name}의 몸이 떨리고 있다."]},
        "gentle":    {"romance": ["{name}가 당신의 머리를 감싸안고 있다."], "lust": ["{name}가 멈추지 말라고 작게 말하고 있다."]},
        "cheerful":  {"romance": ["{name}가 감탄하며 당신에게 안기고 있다."], "lust": ["{name}가 통제를 잃고 있다."]},
        "timid":     {"romance": ["{name}가 당신의 옷을 꽉 잡고 놓지 않고 있다."], "lust": ["{name}가 소리를 참지 못하고 있다."]},
        "cold":      {"romance": ["{name}의 냉정함이 완전히 무너졌다."], "lust": ["{name}가 정신을 놓고 있다."]},
        "seductive": {"romance": ["{name}가 더 과감하게 이끌고 있다."], "lust": ["{name}가 거칠게 당신을 탐하고 있다."]},
        "fierce":    {"romance": ["{name}가 소유하듯 잡고 있다."], "lust": ["{name}가 이성을 잃어가고 있다."]},
        "proud":     {"romance": ["{name}가 체면도 잊고 매달리고 있다."], "lust": ["{name}가 자존심을 완전히 버리고 있다."]},
        "innocent":  {"romance": ["{name}가 처음 느끼는 감각에 눈물이 나고 있다."], "lust": ["{name}가 이게 뭔지 모르지만 멈추고 싶지 않아하고 있다."]},
        "devoted":   {"romance": ["{name}가 행복에 겨워 눈물을 흘리고 있다."], "lust": ["{name}가 전적으로 당신에게 맡기고 있다."]},
    },

    # ─────────────────────────────────────────────
    # STRONG (강한 자극: 음부 터치, 클리토리스, 커닐, 펠라)
    # ─────────────────────────────────────────────
    "strong:during": {
        "stoic": {
            "romance":   ["{name}가 이를 악물며 견디고 있다.", "{name}가 얼굴을 묻고 있다."],
            "platonic":  ["{name}가 눈을 꽉 감고 참고 있다.", "{name}의 귀끝이 새빨갛다."],
            "lust":      ["{name}가 입술을 깨물며 신음을 참고 있다.", "{name}의 몸이 떨리고 있다."],
            "rejection": ["{name}가 고개를 돌리며 견디고 있다.", "{name}가 몸을 경직시키고 있다."],
        },
        "gentle": {
            "romance":   ["{name}가 작은 신음을 내며 받아들이고 있다.", "{name}가 당신의 손을 잡고 있다."],
            "platonic":  ["{name}가 부끄러운 듯 얼굴을 가리고 있다.", "{name}가 참으며 기다리고 있다.", "{name}가 수줍게 눈을 감고 참고 있다.", "{name}가 부끄럽지만 당신을 믿고 있다."],
            "lust":      ["{name}가 참지 못하고 소리를 내고 있다.", "{name}가 당신에게 매달리고 있다."],
            "rejection": ["{name}가 몸을 움츠리고 있다.", "{name}가 눈물이 그렁그렁하다."],
        },
        "cheerful": {
            "romance":   ["{name}가 부끄러워하면서도 반응하고 있다.", "{name}가 당신을 바라보고 있다."],
            "platonic":  ["{name}가 소리를 참으려 입을 막고 있다.", "{name}가 얼굴이 빨갛다.", "{name}가 놀라서 어쩔 줄 몰라하고 있다.", "{name}가 뭐야 이거! 하며 당황하고 있다."],
            "lust":      ["{name}가 큰 소리로 반응하고 있다.", "{name}가 참지 못하고 있다."],
            "rejection": ["{name}가 비명을 지르며 밀어내고 있다.", "{name}가 놀라서 뒤로 빠지고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 떨리는 몸으로 받아들이고 있다.", "{name}가 눈물을 글썽이며 참고 있다."],
            "platonic":  ["{name}가 몸을 웅크리며 견디고 있다.", "{name}가 고개를 숙이고 있다.", "{name}가 이상한 느낌에 겁먹고 당황하고 있다.", "{name}가 무슨 일이 일어나는 건지 모르겠다는 표정이다."],
            "lust":      ["{name}가 온몸을 떨며 소리를 참고 있다.", "{name}가 시트를 움켜쥐고 있다."],
            "rejection": ["{name}가 겁에 질려 굳어 있다.", "{name}가 눈물이 흐르고 있다."],
        },
        "cold": {
            "romance":   ["{name}가 감정을 숨기려 하지만 숨소리가 흔들리고 있다.", "{name}가 눈을 감고 허용하고 있다."],
            "platonic":  ["{name}가 무표정을 유지하려 애쓰고 있다.", "{name}가 자세를 바로잡고 있다.", "{name}가 감정을 드러내지 않으려 이를 악물고 있다.", "{name}가 초연한 척 눈을 감고 있다."],
            "lust":      ["{name}의 냉정한 가면에 균열이 가고 있다.", "{name}가 경어를 잃어가고 있다."],
            "rejection": ["{name}가 차갑게 손목을 잡고 있다.", "{name}가 눈빛으로 경고하고 있다."],
        },
        "seductive": {
            "romance":   ["{name}가 만족스러운 표정으로 받아들이고 있다.", "{name}가 유혹하듯 당신을 바라보고 있다."],
            "platonic":  ["{name}가 여유롭게 반응하고 있다.", "{name}가 가이드하듯 손을 이끌고 있다."],
            "lust":      ["{name}가 노골적으로 반응하고 있다.", "{name}가 능숙하게 몸을 맡기고 있다."],
            "rejection": ["{name}가 하품하듯 시큰둥하다.", "{name}가 조롱하듯 바라보고 있다."],
        },
        "fierce": {
            "romance":   ["{name}가 이를 악물면서도 손을 놓지 않고 있다.", "{name}가 거칠게 숨쉬고 있다."],
            "platonic":  ["{name}가 으르렁거리며 참고 있다.", "{name}가 주먹을 쥐고 있다."],
            "lust":      ["{name}가 공격적으로 당신을 잡고 있다.", "{name}가 이를 드러내며 헐떡이고 있다."],
            "rejection": ["{name}가 발버둥치고 있다.", "{name}가 물어뜯으려 하고 있다."],
        },
        "proud": {
            "romance":   ["{name}가 시선을 피하며 참고 있다. 자존심이 허용하지 않는 표정이다.", "{name}가 입술을 깨물고 있다."],
            "platonic":  ["{name}가 초연함을 유지하려 애쓰고 있다.", "{name}의 표정이 굳어 있다."],
            "lust":      ["{name}의 자존심이 무너지고 있다.", "{name}가 수치심에 몸을 떨고 있다."],
            "rejection": ["{name}가 경멸하듯 당신을 내려다보고 있다.", "{name}가 코웃음을 치고 있다."],
        },
        "innocent": {
            "romance":   ["{name}가 낯선 감각에 놀라면서도 당신을 믿고 있다.", "{name}가 이게 뭔지 물어보고 싶은 표정이다."],
            "platonic":  ["{name}가 혼란스러워하고 있다.", "{name}가 무슨 일인지 모르겠다는 표정이다.", "{name}가 이상하다며 눈을 깜빡이고 있다.", "{name}가 낯선 감각에 몸을 움찔하고 있다."],
            "lust":      ["{name}가 처음 느끼는 감각에 눈이 커지고 있다.", "{name}가 이상한 소리를 내며 당황하고 있다."],
            "rejection": ["{name}가 무서워서 울려고 하고 있다.", "{name}가 뒷걸음치며 떨고 있다."],
        },
        "devoted": {
            "romance":   ["{name}가 기꺼이 받아들이고 있다.", "{name}가 행복한 표정으로 당신을 바라보고 있다."],
            "platonic":  ["{name}가 순순히 따르고 있다.", "{name}가 당신을 위해 참고 있다."],
            "lust":      ["{name}가 더 해달라고 간청하고 있다.", "{name}가 몸을 내밀며 갈구하고 있다."],
            "rejection": ["{name}가 슬프지만 거부하지 못하고 있다.", "{name}가 눈물을 참으며 받아들이고 있다."],
        },
    },
    "strong:during:high": {
        "stoic":     {"romance": ["{name}가 참지 못하고 작은 신음을 흘리고 있다."], "lust": ["{name}의 몸이 점점 달아오르고 있다."]},
        "gentle":    {"romance": ["{name}가 당신의 머리를 감싸안고 있다."], "lust": ["{name}가 멈추지 말라고 속삭이고 있다."]},
        "cheerful":  {"romance": ["{name}가 부끄러워하면서도 소리를 참지 못하고 있다."], "lust": ["{name}가 크게 소리를 내고 있다."]},
        "timid":     {"romance": ["{name}가 당신의 팔을 잡으며 떨고 있다."], "lust": ["{name}가 소리를 참지 못해 입을 막고 있다."]},
        "cold":      {"romance": ["{name}의 경어가 완전히 무너지고 있다."], "lust": ["{name}가 참으려 하지만 몸이 반응하고 있다."]},
        "seductive": {"romance": ["{name}가 능숙하게 허리를 맞추고 있다."], "lust": ["{name}가 당신을 거칠게 이끌고 있다."]},
        "fierce":    {"romance": ["{name}가 거칠게 당신을 끌어안고 있다."], "lust": ["{name}가 공격적으로 매달리고 있다."]},
        "proud":     {"romance": ["{name}의 자존심이 완전히 무너져 매달리고 있다."], "lust": ["{name}가 부끄러움에 얼굴을 묻으며 떨고 있다."]},
        "innocent":  {"romance": ["{name}가 처음 느끼는 쾌감에 눈물이 나고 있다."], "lust": ["{name}가 이상한 감각에 정신이 없다."]},
        "devoted":   {"romance": ["{name}가 황홀한 표정으로 당신을 바라보고 있다."], "lust": ["{name}가 모든 것을 맡기며 갈구하고 있다."]},
    },

    # ─────────────────────────────────────────────
    # PENETRATION (삽입)
    # ─────────────────────────────────────────────
    "penetration:during": {
        "stoic": {
            "romance":   ["{name}가 편안하게 몸을 맡기고 있다.", "{name}가 허리를 맞추고 있다."],
            "platonic":  ["{name}가 눈을 감고 받아들이고 있다.", "{name}가 참으며 기다리고 있다."],
            "lust":      ["{name}가 이를 악물면서도 몸이 반응하고 있다.", "{name}의 안에서 조여오고 있다."],
            "rejection": ["{name}가 이를 악물며 견디고 있다.", "{name}가 고개를 돌리고 있다."],
        },
        "gentle": {
            "romance":   ["{name}가 부드럽게 당신을 감싸고 있다.", "{name}가 당신과 호흡을 맞추고 있다."],
            "platonic":  ["{name}가 참으며 당신을 기다리고 있다.", "{name}가 눈을 감고 받아들이고 있다.", "{name}가 아프지만 당신을 위해 참고 있다.", "{name}가 눈물을 글썽이며 당신을 올려다보고 있다."],
            "lust":      ["{name}가 작은 소리를 내며 매달리고 있다.", "{name}가 당신의 이름을 부르고 있다."],
            "rejection": ["{name}가 눈물을 참으며 견디고 있다.", "{name}가 고통스러운 표정이다."],
        },
        "cheerful": {
            "romance":   ["{name}가 즐기듯 당신에게 반응하고 있다.", "{name}가 미소짓며 당신을 바라보고 있다."],
            "platonic":  ["{name}가 어색하지만 받아들이고 있다.", "{name}가 부끄러워하며 눈을 피하고 있다.", "{name}가 놀라서 소리를 참으려 입을 막고 있다.", "{name}가 어색하게 웃으며 참고 있다."],
            "lust":      ["{name}가 참지 못하고 크게 소리를 내고 있다.", "{name}가 당신에게 매달리고 있다."],
            "rejection": ["{name}가 고통에 비명을 참고 있다.", "{name}가 몸을 비틀고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 떨리지만 당신을 받아들이고 있다.", "{name}가 눈을 감고 매달려 있다."],
            "platonic":  ["{name}가 겁먹었지만 참고 있다.", "{name}가 시트를 움켜쥐고 있다.", "{name}가 무슨 일인지 이해하지 못하고 겁먹어 있다.", "{name}가 아프지만 참으려고 시트를 잡고 있다."],
            "lust":      ["{name}가 온몸을 떨며 소리를 내고 있다.", "{name}가 당신의 등에 손톱자국을 내고 있다."],
            "rejection": ["{name}가 눈물을 흘리며 굳어 있다.", "{name}가 고통에 몸을 웅크리고 있다."],
        },
        "cold": {
            "romance":   ["{name}가 눈을 감고 당신에게 맡기고 있다.", "{name}가 미세하게 허리를 맞추고 있다."],
            "platonic":  ["{name}가 무표정하게 받아들이고 있다.", "{name}가 태연한 척하고 있다.", "{name}가 감정 없는 눈으로 참고 있다.", "{name}가 아무렇지 않은 척 천장을 보고 있다."],
            "lust":      ["{name}의 냉정함이 완전히 무너지고 있다.", "{name}가 참지 못하고 소리를 내고 있다."],
            "rejection": ["{name}가 차갑게 견디고 있다.", "{name}가 천장을 바라보고 있다."],
        },
        "seductive": {
            "romance":   ["{name}가 능숙하게 허리를 맞추고 있다.", "{name}가 만족스러운 표정이다."],
            "platonic":  ["{name}가 여유롭게 당신을 이끌고 있다.", "{name}가 가이드하듯 움직이고 있다."],
            "lust":      ["{name}가 적극적으로 당신을 탐하고 있다.", "{name}가 도발적으로 허리를 흔들고 있다."],
            "rejection": ["{name}가 지루한 듯 한숨을 쉬고 있다.", "{name}가 냉담하게 받아들이고 있다."],
        },
        "fierce": {
            "romance":   ["{name}가 거칠게 당신을 끌어안고 있다.", "{name}가 이를 악물면서도 놓지 않고 있다."],
            "platonic":  ["{name}가 으르렁거리며 참고 있다.", "{name}가 통증을 참으며 이를 악물고 있다."],
            "lust":      ["{name}가 공격적으로 허리를 맞추고 있다.", "{name}가 당신의 어깨를 물고 있다."],
            "rejection": ["{name}가 격렬하게 저항하고 있다.", "{name}가 발버둥치고 있다."],
        },
        "proud": {
            "romance":   ["{name}가 체면도 잊고 당신에게 매달리고 있다.", "{name}가 자존심을 내려놓고 받아들이고 있다."],
            "platonic":  ["{name}가 무심한 척하지만 몸이 반응하고 있다.", "{name}가 입술을 깨물고 있다."],
            "lust":      ["{name}의 자존심이 산산조각 나고 있다.", "{name}가 수치심과 쾌감 사이에서 흔들리고 있다."],
            "rejection": ["{name}가 경멸의 눈빛을 보내고 있다.", "{name}가 이를 악물며 굴욕을 참고 있다."],
        },
        "innocent": {
            "romance":   ["{name}가 낯선 감각에 놀라면서도 당신을 꽉 잡고 있다.", "{name}가 이게 어떤 건지 느끼고 있다."],
            "platonic":  ["{name}가 당혹스러워하며 참고 있다.", "{name}가 이상한 표정을 짓고 있다.", "{name}가 이상하다며 눈이 커져 있다.", "{name}가 무슨 일이 일어나는지 이해하지 못하고 있다."],
            "lust":      ["{name}가 처음 느끼는 감각에 정신을 놓고 있다.", "{name}가 이해할 수 없는 소리를 내고 있다."],
            "rejection": ["{name}가 무서워서 울고 있다.", "{name}가 뭐가 뭔지 모르겠다는 표정이다."],
        },
        "devoted": {
            "romance":   ["{name}가 행복한 표정으로 당신을 받아들이고 있다.", "{name}가 당신과 하나가 된 듯 눈을 감고 있다."],
            "platonic":  ["{name}가 순순히 따르고 있다.", "{name}가 당신을 위해 기꺼이 받아들이고 있다."],
            "lust":      ["{name}가 더 깊이를 갈구하고 있다.", "{name}가 당신의 이름을 반복하며 매달리고 있다."],
            "rejection": ["{name}가 고통스럽지만 거부하지 못하고 있다.", "{name}가 눈물을 참으며 받아들이고 있다."],
        },
    },
    "penetration:during:high": {
        "stoic":     {"romance": ["{name}가 당신을 끌어안으며 신음하고 있다."], "lust": ["{name}의 안이 뜨겁게 조여온다."]},
        "gentle":    {"romance": ["{name}가 당신의 이름을 반복하며 감싸고 있다."], "lust": ["{name}가 멈추지 말라고 간청하고 있다."]},
        "cheerful":  {"romance": ["{name}가 웃으면서도 눈물이 나고 있다."], "lust": ["{name}가 통제를 잃고 소리를 내고 있다."]},
        "timid":     {"romance": ["{name}가 당신을 꽉 안으며 작은 소리를 내고 있다."], "lust": ["{name}가 온몸을 떨며 매달리고 있다."]},
        "cold":      {"romance": ["{name}가 처음으로 이름을 불러주고 있다."], "lust": ["{name}가 완전히 무너져 소리를 내고 있다."]},
        "seductive": {"romance": ["{name}가 당신을 깊이 받아들이며 미소짓고 있다."], "lust": ["{name}가 거칠게 당신을 조이고 있다."]},
        "fierce":    {"romance": ["{name}가 소유하듯 안으며 이를 악물고 있다."], "lust": ["{name}가 물어뜯으며 매달리고 있다."]},
        "proud":     {"romance": ["{name}가 눈물을 보이며 매달리고 있다."], "lust": ["{name}가 자존심도 잊고 갈구하고 있다."]},
        "innocent":  {"romance": ["{name}가 처음 느끼는 연결감에 눈물이 나고 있다."], "lust": ["{name}가 이해 못하는 쾌감에 떠내려가고 있다."]},
        "devoted":   {"romance": ["{name}가 황홀한 표정으로 당신에게 맡기고 있다."], "lust": ["{name}가 전적으로 당신 것이라는 듯 안겨 있다."]},
    },
    "penetration:during:extreme": {
        "stoic":     {"romance": ["{name}가 당신의 이름을 부르며 매달리고 있다."], "lust": ["{name}의 온몸이 떨리며 조여오고 있다."]},
        "gentle":    {"romance": ["{name}가 눈물을 흘리며 당신을 감싸안고 있다."], "lust": ["{name}가 정신을 놓고 당신에게 맡기고 있다."]},
        "cheerful":  {"romance": ["{name}가 미소와 눈물이 섞인 표정으로 당신을 바라보고 있다."], "lust": ["{name}가 소리를 참을 수 없어 비명에 가까운 신음을 내고 있다."]},
        "timid":     {"romance": ["{name}가 말없이 눈물을 흘리며 당신을 꽉 잡고 있다."], "lust": ["{name}가 의식이 날아가는 듯한 표정이다."]},
        "cold":      {"romance": ["{name}가 모든 벽을 허물고 당신에게 매달리고 있다."], "lust": ["{name}가 원래 모습을 잃고 본능에 맡기고 있다."]},
        "seductive": {"romance": ["{name}가 진심으로 당신을 원하며 끌어안고 있다."], "lust": ["{name}도 여유를 잃고 거칠어지고 있다."]},
        "fierce":    {"romance": ["{name}가 눈물을 보이며 당신을 놓지 않고 있다."], "lust": ["{name}가 야수처럼 당신에게 매달리고 있다."]},
        "proud":     {"romance": ["{name}가 완전히 무너져 울면서 당신 이름을 부르고 있다."], "lust": ["{name}가 수치도 자존심도 잊고 본능에 맡기고 있다."]},
        "innocent":  {"romance": ["{name}가 태어나서 처음 느끼는 감정에 정신을 놓고 있다."], "lust": ["{name}가 무엇이 일어나는지도 모른 채 몸이 반응하고 있다."]},
        "devoted":   {"romance": ["{name}가 세상에서 가장 행복한 표정으로 당신에게 맡기고 있다."], "lust": ["{name}가 당신 외에는 아무것도 모른다는 듯 매달리고 있다."]},
    },

    # ─────────────────────────────────────────────
    # ROUGH (거친 행위)
    # ─────────────────────────────────────────────
    "rough:during": {
        "stoic": {
            "romance":   ["{name}가 이를 악물며 당신을 받아들이고 있다."],
            "platonic":  ["{name}가 고통을 참으며 견디고 있다."],
            "lust":      ["{name}가 거칠수록 더 반응하고 있다."],
            "rejection": ["{name}가 고통에 몸을 비틀고 있다."],
        },
        "gentle": {
            "romance":   ["{name}가 아프지만 당신을 놓지 않고 있다."],
            "platonic":  ["{name}가 눈물을 흘리며 참고 있다.", "{name}가 아파하면서도 불평하지 않고 있다.", "{name}가 눈물을 참으며 당신을 잡고 있다."],
            "lust":      ["{name}가 고통과 쾌감 사이에서 흔들리고 있다."],
            "rejection": ["{name}가 비명을 참으며 견디고 있다."],
        },
        "cheerful": {
            "romance":   ["{name}가 놀랐지만 당신을 믿고 견디고 있다."],
            "platonic":  ["{name}가 소리를 참으려 입을 막고 있다.", "{name}가 울면서도 괜찮다고 하려 하고 있다.", "{name}가 아프다고 소리치고 있다."],
            "lust":      ["{name}가 거칠수록 크게 반응하고 있다."],
            "rejection": ["{name}가 비명을 지르고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 울면서도 당신을 잡고 있다."],
            "platonic":  ["{name}가 겁에 질려 떨고 있다.", "{name}가 겁에 질려 작아져 있다.", "{name}가 아프다고 말하고 싶지만 목소리가 나오지 않는다."],
            "lust":      ["{name}가 두렵지만 멈추지 말라는 듯 잡고 있다."],
            "rejection": ["{name}가 공포에 울음을 터뜨리고 있다."],
        },
        "cold": {
            "romance":   ["{name}가 무너지지 않으려 이를 악물고 있다."],
            "platonic":  ["{name}가 고통을 느끼지 않는 척하고 있다.", "{name}가 고통을 숨기려 이를 악물고 있다.", "{name}가 감정 없는 표정으로 버티고 있다."],
            "lust":      ["{name}의 냉정함이 완전히 깨지고 있다."],
            "rejection": ["{name}가 차가운 눈으로 당신을 노려보고 있다."],
        },
        "seductive": {
            "romance":   ["{name}가 거친 것도 받아들이며 당신을 감싸고 있다."],
            "platonic":  ["{name}가 놀랐지만 여유를 유지하려 하고 있다."],
            "lust":      ["{name}가 더 거칠게 해달라고 도발하고 있다."],
            "rejection": ["{name}가 냉소적으로 견디고 있다."],
        },
        "fierce": {
            "romance":   ["{name}가 마주잡으며 거칠게 반응하고 있다."],
            "platonic":  ["{name}가 으르렁거리며 이를 악물고 있다."],
            "lust":      ["{name}가 당신만큼 거칠게 반응하고 있다."],
            "rejection": ["{name}가 격렬하게 저항하며 물어뜯고 있다."],
        },
        "proud": {
            "romance":   ["{name}가 굴욕감에 눈물을 참으며도 놓지 못하고 있다."],
            "platonic":  ["{name}가 자존심에 상처를 받고 있다."],
            "lust":      ["{name}가 수치심에 무너지면서도 몸이 반응하고 있다."],
            "rejection": ["{name}가 굴욕적인 눈빛으로 당신을 바라보고 있다."],
        },
        "innocent": {
            "romance":   ["{name}가 아프지만 당신을 믿고 견디고 있다."],
            "platonic":  ["{name}가 무슨 일인지 모르겠다는 표정으로 울고 있다.", "{name}가 왜 이렇게 아픈 건지 모르겠다는 표정이다.", "{name}가 무서워서 눈을 꽉 감고 있다."],
            "lust":      ["{name}가 고통과 낯선 감각 사이에서 혼란스러워하고 있다."],
            "rejection": ["{name}가 두려움에 울며 떨고 있다."],
        },
        "devoted": {
            "romance":   ["{name}가 당신을 위해 기꺼이 견디고 있다."],
            "platonic":  ["{name}가 아프지만 불평 없이 참고 있다."],
            "lust":      ["{name}가 더 해달라고 눈물로 간청하고 있다."],
            "rejection": ["{name}가 아프지만 거부하지 못하고 있다."],
        },
    },

    # ─────────────────────────────────────────────
    # REBELLION CASCADE — 반발 단계별 강제 상호작용 묘사
    # ─────────────────────────────────────────────

    # ── LIGHT × rebellion ────────────────────────
    "light:during:rebellion_mild": {
        "stoic": {
            "rejection": ["{name}가 굳은 표정으로 서 있다.", "{name}가 시선을 피하고 있다."],
            "lust":      ["{name}가 싫은데도 몸이 미세하게 반응하고 있다."],
        },
        "gentle": {
            "rejection": ["{name}가 불안한 눈으로 당신을 보고 있다.", "{name}가 살짝 몸을 뒤로 빼고 있다."],
        },
        "cheerful": {
            "rejection": ["{name}의 미소가 사라지고 있다.", "{name}가 어색하게 웃으며 거리를 두려 하고 있다."],
            "lust":      ["{name}가 싫으면서도 심장이 빠르게 뛰고 있다."],
        },
        "timid": {
            "rejection": ["{name}가 얼어붙은 듯 굳어 있다.", "{name}가 눈을 내리깔고 몸을 움츠리고 있다."],
            "lust":      ["{name}가 싫은데 몸이 떨리며 반응하고 있다."],
        },
        "cold": {
            "rejection": ["{name}가 차가운 눈으로 당신의 손을 바라보고 있다.", "{name}가 미동도 없이 서 있다."],
        },
        "seductive": {
            "rejection": ["{name}가 시큰둥하게 한숨을 쉬고 있다.", "{name}가 역겨운 듯 고개를 돌리고 있다."],
        },
        "fierce": {
            "rejection": ["{name}가 이를 드러내며 경고하고 있다.", "{name}가 손목을 비틀며 벗어나려 하고 있다."],
        },
        "proud": {
            "rejection": ["{name}가 불쾌한 듯 눈살을 찌푸리고 있다.", "{name}가 경멸하듯 내려다보고 있다."],
        },
        "innocent": {
            "rejection": ["{name}가 뭔가 이상하다는 듯 고개를 갸웃하고 있다.", "{name}가 불안한 표정으로 당신을 바라보고 있다."],
        },
        "devoted": {
            "rejection": ["{name}가 슬픈 표정으로 당신을 바라보고 있다.", "{name}가 고개를 떨구고 있다."],
        },
    },
    "light:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 이를 악물고 노려보고 있다.", "{name}가 당신의 손을 떨쳐내고 있다."]},
        "gentle":    {"rejection": ["{name}가 눈물을 글썽이며 고개를 젓고 있다.", "{name}가 떨리는 목소리로 하지 말라고 하고 있다."]},
        "cheerful":  {"rejection": ["{name}가 얼굴이 일그러지며 소리를 지르고 있다.", "{name}가 당신의 손을 세게 밀어내고 있다."]},
        "timid":     {"rejection": ["{name}가 겁에 질려 뒷걸음치고 있다.", "{name}가 과호흡을 하며 떨고 있다."]},
        "cold":      {"rejection": ["{name}가 살기 어린 눈으로 당신을 바라보고 있다.", "{name}가 얼음장 같은 목소리로 경고하고 있다."]},
        "seductive": {"rejection": ["{name}가 역겨운 듯 비웃고 있다.", "{name}가 차가운 경멸을 담아 바라보고 있다."]},
        "fierce":    {"rejection": ["{name}가 당신의 손을 물어뜯으려 하고 있다.", "{name}가 격렬하게 밀어내고 있다."]},
        "proud":     {"rejection": ["{name}가 분노에 찬 눈빛으로 노려보고 있다.", "{name}가 굴욕감에 온몸을 떨고 있다."]},
        "innocent":  {"rejection": ["{name}가 겁먹은 눈으로 울기 시작하고 있다.", "{name}가 무서워서 고개를 세차게 젓고 있다."]},
        "devoted":   {"rejection": ["{name}가 배신감에 눈물을 흘리고 있다.", "{name}가 믿을 수 없다는 표정으로 당신을 바라보고 있다."]},
    },
    "light:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 살의가 담긴 눈으로 당신을 노려보고 있다.", "{name}가 감정을 완전히 죽인 채 서 있다."]},
        "gentle":    {"rejection": ["{name}가 소리 없이 눈물을 흘리며 멍하니 서 있다.", "{name}가 해리된 듯 초점 없는 눈을 하고 있다."]},
        "cheerful":  {"rejection": ["{name}가 비명을 지르며 폭력적으로 밀어내고 있다.", "{name}가 히스테리를 일으키고 있다."]},
        "timid":     {"rejection": ["{name}가 과호흡으로 의식을 잃어가고 있다.", "{name}가 공포에 완전히 굳어 있다."]},
        "cold":      {"rejection": ["{name}의 눈에서 살의가 느껴진다.", "{name}가 죽은 듯한 눈으로 당신을 관통하고 있다."]},
        "seductive": {"rejection": ["{name}가 구역질하듯 얼굴을 돌리고 있다.", "{name}가 극도의 혐오감을 드러내고 있다."]},
        "fierce":    {"rejection": ["{name}가 야수처럼 당신에게 덤벼들고 있다.", "{name}가 이를 드러내며 살의를 뿜고 있다."]},
        "proud":     {"rejection": ["{name}가 눈물 속에서 복수를 다짐하고 있다.", "{name}가 분노로 온몸을 떨며 당신을 저주하고 있다."]},
        "innocent":  {"rejection": ["{name}가 정신이 멀어지며 반응을 멈추고 있다.", "{name}가 아무것도 이해하지 못한 채 눈물만 흘리고 있다."]},
        "devoted":   {"rejection": ["{name}가 절망에 빠져 멍하니 서 있다.", "{name}가 신뢰가 완전히 무너진 표정이다."]},
    },

    # ── MEDIUM × rebellion ───────────────────────
    "medium:during:rebellion_mild": {
        "stoic": {
            "rejection": ["{name}가 불쾌한 듯 당신의 손을 잡아 멈추고 있다.", "{name}가 고개를 돌리며 참고 있다."],
            "lust":      ["{name}가 싫은데도 몸이 미세하게 반응하고 있다."],
        },
        "gentle": {
            "rejection": ["{name}가 떨리는 목소리로 멈춰달라고 하고 있다.", "{name}가 눈물을 글썽이며 몸을 움츠리고 있다."],
        },
        "cheerful": {
            "rejection": ["{name}의 표정이 완전히 굳어 있다.", "{name}가 놀라서 당신의 손을 밀어내고 있다."],
            "lust":      ["{name}가 싫으면서도 몸이 반응해서 혼란스러워하고 있다."],
        },
        "timid": {
            "rejection": ["{name}가 겁에 질려 몸을 웅크리고 있다.", "{name}가 작은 비명을 삼키고 있다."],
            "lust":      ["{name}가 싫은데 몸이 떨리며 열이 오르고 있다."],
        },
        "cold": {
            "rejection": ["{name}가 차가운 시선으로 손목을 잡으며 제지하고 있다.", "{name}가 경고하듯 눈빛을 보내고 있다."],
        },
        "seductive": {
            "rejection": ["{name}가 역겨운 듯 한숨을 쉬고 있다.", "{name}가 냉소적으로 당신을 바라보고 있다."],
        },
        "fierce": {
            "rejection": ["{name}가 손목을 비틀며 밀어내고 있다.", "{name}가 이를 드러내며 으르렁거리고 있다."],
        },
        "proud": {
            "rejection": ["{name}가 모욕감에 얼굴이 붉어지고 있다.", "{name}가 차갑게 당신의 손을 걷어내고 있다."],
        },
        "innocent": {
            "rejection": ["{name}가 무서운 듯 몸을 움츠리며 뒤로 빠지고 있다.", "{name}가 어리둥절하면서도 불안해하고 있다."],
        },
        "devoted": {
            "rejection": ["{name}가 상처받은 표정으로 참고 있다.", "{name}가 슬픈 눈으로 고개를 떨구고 있다."],
        },
    },
    "medium:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 이를 악물며 당신의 손을 강제로 떼어내고 있다.", "{name}가 분노를 억누르며 노려보고 있다."]},
        "gentle":    {"rejection": ["{name}가 울면서 하지 말라고 애원하고 있다.", "{name}가 몸을 사리며 빠져나가려 하고 있다."],
                      "lust": ["{name}가 싫은데 몸이 반응하는 게 수치스러운 듯 울고 있다."]},
        "cheerful":  {"rejection": ["{name}가 비명을 지르며 당신을 밀어내고 있다.", "{name}가 공포에 얼굴이 일그러져 있다."]},
        "timid":     {"rejection": ["{name}가 과호흡을 하며 공포에 떨고 있다.", "{name}가 제발이라고 울며 빌고 있다."],
                      "lust": ["{name}가 반응하는 자기 몸이 미워서 울고 있다."]},
        "cold":      {"rejection": ["{name}가 살기 어린 눈으로 당신의 손목을 꺾으려 하고 있다.", "{name}가 얼음장 같은 목소리로 죽여버리겠다고 하고 있다."]},
        "seductive": {"rejection": ["{name}가 극도의 혐오감을 담아 침을 뱉으려 하고 있다.", "{name}가 냉소적으로 비웃으며 경멸하고 있다."]},
        "fierce":    {"rejection": ["{name}가 당신을 물어뜯으며 격렬하게 저항하고 있다.", "{name}가 발톱으로 할퀴고 있다."]},
        "proud":     {"rejection": ["{name}가 분노와 굴욕에 온몸을 떨며 저주하고 있다.", "{name}가 두 번 다시 용서하지 않겠다는 눈빛이다."]},
        "innocent":  {"rejection": ["{name}가 무서워서 울음을 터뜨리고 있다.", "{name}가 이게 뭔지 모르겠다며 떨고 있다."]},
        "devoted":   {"rejection": ["{name}가 배신감에 멍하니 눈물을 흘리고 있다.", "{name}가 왜 이러는지 모르겠다며 울고 있다."]},
    },
    "medium:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 감정이 완전히 사라진 눈으로 당신을 보고 있다.", "{name}가 죽은 듯이 반응을 멈추고 있다."]},
        "gentle":    {"rejection": ["{name}가 소리 없이 눈물만 흘리며 해리되고 있다.", "{name}가 영혼이 빠져나간 듯 멍하다."]},
        "cheerful":  {"rejection": ["{name}가 날카로운 비명을 지르며 발악하고 있다.", "{name}가 히스테리를 일으키며 밀어내고 있다."]},
        "timid":     {"rejection": ["{name}가 과호흡으로 의식이 흐려지고 있다.", "{name}가 정신적으로 완전히 셧다운되고 있다."]},
        "cold":      {"rejection": ["{name}의 눈에서 인간적인 감정이 완전히 사라졌다.", "{name}가 당신을 죽일 방법을 생각하고 있는 눈빛이다."]},
        "seductive": {"rejection": ["{name}가 극도의 구역질을 참고 있다.", "{name}가 완전한 경멸과 혐오만 남은 눈빛이다."]},
        "fierce":    {"rejection": ["{name}가 야수처럼 당신에게 이를 드러내고 있다.", "{name}가 죽이겠다는 살의를 뿜으며 저항하고 있다."]},
        "proud":     {"rejection": ["{name}가 분노로 온몸을 떨며 침묵하고 있다.", "{name}가 복수의 불꽃을 눈에 담고 있다."]},
        "innocent":  {"rejection": ["{name}가 정신이 멀어지며 아무런 반응도 하지 않고 있다.", "{name}가 현실을 거부하듯 눈을 감고 있다."]},
        "devoted":   {"rejection": ["{name}가 완전히 무너져 빈 껍데기처럼 서 있다.", "{name}가 절망에 빠져 눈에서 빛이 사라졌다."]},
    },

    # ── STRONG × rebellion ───────────────────────
    "strong:during:rebellion_mild": {
        "stoic": {
            "rejection": ["{name}가 이를 악물며 몸을 경직시키고 있다.", "{name}가 고개를 돌리며 참고 있다."],
            "lust":      ["{name}가 혐오스럽지만 몸이 미세하게 달아오르고 있다."],
        },
        "gentle": {
            "rejection": ["{name}가 눈물을 글썽이며 멈춰달라고 작게 말하고 있다.", "{name}가 몸을 움츠리며 떨고 있다."],
            "lust":      ["{name}가 싫은데 몸이 반응해서 더 괴로워하고 있다."],
        },
        "cheerful": {
            "rejection": ["{name}가 비명을 참으며 몸을 비틀고 있다.", "{name}가 얼굴이 창백해지고 있다."],
            "lust":      ["{name}가 싫으면서도 몸이 반응하는 게 당혹스러운 표정이다."],
        },
        "timid": {
            "rejection": ["{name}가 공포에 떨며 울고 있다.", "{name}가 눈물을 흘리며 벗어나려 하고 있다."],
            "lust":      ["{name}가 두려운데도 몸이 반응해서 자기가 싫은 표정이다."],
        },
        "cold": {
            "rejection": ["{name}가 눈빛으로 살의를 드러내며 견디고 있다.", "{name}가 차갑게 굳은 채 참고 있다."],
        },
        "seductive": {
            "rejection": ["{name}가 역겨운 듯 몸을 비틀고 있다.", "{name}가 냉소적으로 한숨을 내쉬고 있다."],
        },
        "fierce": {
            "rejection": ["{name}가 발버둥치며 격렬하게 저항하고 있다.", "{name}가 물어뜯으려 하고 있다."],
        },
        "proud": {
            "rejection": ["{name}가 굴욕감에 이를 갈고 있다.", "{name}가 분노에 찬 눈빛으로 참고 있다."],
        },
        "innocent": {
            "rejection": ["{name}가 무서워서 울며 뒤로 빠지려 하고 있다.", "{name}가 뭐가 뭔지 모르겠다며 겁먹고 있다."],
        },
        "devoted": {
            "rejection": ["{name}가 상처받은 눈으로 참으며 견디고 있다.", "{name}가 슬프지만 거부하지 못하고 있다."],
        },
    },
    "strong:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 분노를 억누르며 주먹을 떨고 있다.", "{name}가 살의를 담은 눈으로 참고 있다."],
                      "lust": ["{name}가 혐오하면서도 몸이 반응하는 자신에게 분노하고 있다."]},
        "gentle":    {"rejection": ["{name}가 울면서 제발 멈춰달라고 애원하고 있다.", "{name}가 고통에 몸을 사리며 흐느끼고 있다."],
                      "lust": ["{name}가 반응하는 자기 몸이 수치스러워 더 크게 울고 있다."]},
        "cheerful":  {"rejection": ["{name}가 소리를 지르며 발버둥치고 있다.", "{name}가 고통에 얼굴이 일그러져 울고 있다."]},
        "timid":     {"rejection": ["{name}가 공포에 울부짖으며 빠져나가려 하고 있다.", "{name}가 겁에 질려 과호흡을 하고 있다."],
                      "lust": ["{name}가 자기 몸의 반응에 자기혐오로 몸서리치고 있다."]},
        "cold":      {"rejection": ["{name}가 살기 어린 눈으로 죽여버리겠다고 속삭이고 있다.", "{name}가 빙점 이하의 눈빛으로 당신을 꿰뚫고 있다."]},
        "seductive": {"rejection": ["{name}가 극도의 혐오감에 구역질하고 있다.", "{name}가 차가운 경멸을 담아 당신을 바라보고 있다."]},
        "fierce":    {"rejection": ["{name}가 이를 물어뜯으며 격렬하게 발버둥치고 있다.", "{name}가 할퀴고 물며 필사적으로 저항하고 있다."]},
        "proud":     {"rejection": ["{name}가 굴욕에 분노의 눈물을 흘리며 복수를 맹세하고 있다.", "{name}가 치를 떨며 당신을 저주하고 있다."]},
        "innocent":  {"rejection": ["{name}가 겁에 질려 울부짖고 있다.", "{name}가 왜 이러는지 모르겠다며 패닉 상태다."]},
        "devoted":   {"rejection": ["{name}가 배신감에 무너지며 울고 있다.", "{name}가 왜 이런 짓을 하냐며 절규하고 있다."]},
    },
    "strong:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 감정이 완전히 꺼진 눈으로 천장을 바라보고 있다.", "{name}가 인형처럼 반응을 멈추고 있다."]},
        "gentle":    {"rejection": ["{name}가 해리된 채 소리 없이 눈물만 흘리고 있다.", "{name}가 영혼이 빠져나간 듯 아무 반응이 없다."]},
        "cheerful":  {"rejection": ["{name}가 날카로운 비명을 지르며 정신이 나가고 있다.", "{name}가 웃음과 울음이 뒤섞인 히스테리 상태다."]},
        "timid":     {"rejection": ["{name}가 의식을 잃어가며 눈이 풀리고 있다.", "{name}가 공포에 완전히 정신이 나간 상태다."]},
        "cold":      {"rejection": ["{name}가 인간의 감정을 완전히 버린 눈빛이다.", "{name}가 죽은 듯 고요하지만 살의만 남아 있다."]},
        "seductive": {"rejection": ["{name}가 완전히 해리된 채 구역질만 하고 있다.", "{name}가 살아있는 시체 같은 눈빛이다."]},
        "fierce":    {"rejection": ["{name}가 생존 본능만 남은 채 물어뜯고 발톱을 세우고 있다.", "{name}가 야수처럼 필사적으로 저항하고 있다."]},
        "proud":     {"rejection": ["{name}가 분노조차 사라진 빈 눈빛이다.", "{name}가 모든 감정이 타버린 채 복수만 되뇌고 있다."]},
        "innocent":  {"rejection": ["{name}가 정신적으로 완전히 셧다운되어 인형처럼 있다.", "{name}가 현실을 거부하며 의식이 멀어지고 있다."]},
        "devoted":   {"rejection": ["{name}가 완전히 무너져 빈 껍데기가 되어 있다.", "{name}가 모든 신뢰가 산산조각 난 눈빛이다."]},
    },

    # ── PENETRATION × rebellion ──────────────────
    "penetration:during:rebellion_mild": {
        "stoic": {
            "rejection": ["{name}가 이를 악물며 고통을 참고 있다.", "{name}가 고개를 돌린 채 견디고 있다."],
            "lust":      ["{name}가 혐오스럽지만 몸 깊은 곳이 반응하고 있다."],
        },
        "gentle": {
            "rejection": ["{name}가 눈물을 흘리며 고통스러워하고 있다.", "{name}가 떨리는 몸으로 참고 있다."],
            "lust":      ["{name}가 싫은데 몸이 감싸오는 것에 수치심을 느끼고 있다."],
        },
        "cheerful": {
            "rejection": ["{name}가 고통에 비명을 참으며 몸을 비틀고 있다.", "{name}가 눈물을 흘리며 빠져나가려 하고 있다."],
            "lust":      ["{name}가 싫으면서도 몸이 맞추고 있는 자신이 당혹스러운 표정이다."],
        },
        "timid": {
            "rejection": ["{name}가 공포에 질린 채 울며 굳어 있다.", "{name}가 고통에 시트를 움켜쥐며 떨고 있다."],
            "lust":      ["{name}가 두려운데도 몸이 반응해서 멈출 수가 없어 보인다."],
        },
        "cold": {
            "rejection": ["{name}가 차갑게 천장을 바라보며 견디고 있다.", "{name}가 감정을 완전히 차단한 채 참고 있다."],
        },
        "seductive": {
            "rejection": ["{name}가 역겨운 듯 얼굴을 돌리고 있다.", "{name}가 냉소적으로 한숨을 쉬며 참고 있다."],
        },
        "fierce": {
            "rejection": ["{name}가 격렬하게 몸을 비틀며 저항하고 있다.", "{name}가 이를 악물며 발버둥치고 있다."],
        },
        "proud": {
            "rejection": ["{name}가 굴욕감에 이를 악물며 눈물을 참고 있다.", "{name}가 분노에 찬 눈빛으로 당신을 노려보고 있다."],
        },
        "innocent": {
            "rejection": ["{name}가 무서워서 울며 뭐가 뭔지 모르고 있다.", "{name}가 고통에 눈이 커지며 겁에 질려 있다."],
        },
        "devoted": {
            "rejection": ["{name}가 고통스럽지만 거부하지 못하고 눈물을 흘리고 있다.", "{name}가 왜 이러는지 모르겠다는 표정으로 참고 있다."],
        },
    },
    "penetration:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 살의를 담은 눈으로 고통을 참고 있다.", "{name}가 피가 나도록 입술을 깨물며 견디고 있다."]},
        "gentle":    {"rejection": ["{name}가 울부짖으며 제발 멈춰달라고 간청하고 있다.", "{name}가 고통에 정신을 잃어가며 흐느끼고 있다."],
                      "lust": ["{name}가 고통 속에서도 반응하는 몸에 절망하며 울고 있다."]},
        "cheerful":  {"rejection": ["{name}가 비명을 지르며 필사적으로 빠져나가려 하고 있다.", "{name}가 고통에 얼굴이 창백해지며 울고 있다."]},
        "timid":     {"rejection": ["{name}가 공포에 울부짖다 목이 쉬어가고 있다.", "{name}가 겁에 질려 의식이 흐려지고 있다."],
                      "lust": ["{name}가 고통 속 반응에 자기혐오로 목놓아 울고 있다."]},
        "cold":      {"rejection": ["{name}가 빙점 이하의 살의를 눈에 담고 견디고 있다.", "{name}가 죽음보다 차가운 눈빛으로 당신을 보고 있다."]},
        "seductive": {"rejection": ["{name}가 극도의 구역질을 하며 고개를 돌리고 있다.", "{name}가 혐오에 찬 눈빛으로 침묵하고 있다."]},
        "fierce":    {"rejection": ["{name}가 필사적으로 물어뜯고 할퀴며 저항하고 있다.", "{name}가 생존 본능으로 격렬하게 발버둥치고 있다."]},
        "proud":     {"rejection": ["{name}가 굴욕과 분노의 눈물을 흘리며 이를 갈고 있다.", "{name}가 치를 떨며 반드시 보복하겠다는 눈빛이다."]},
        "innocent":  {"rejection": ["{name}가 극심한 공포에 비명을 지르며 패닉 상태다.", "{name}가 고통에 의미 없는 소리만 내며 울고 있다."]},
        "devoted":   {"rejection": ["{name}가 신뢰가 무너지며 절규하고 있다.", "{name}가 왜 이러냐며 울부짖고 있다."]},
    },
    "penetration:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 감정이 완전히 꺼진 채 인형처럼 누워 있다.", "{name}가 영혼이 빠져나간 듯 천장만 바라보고 있다."]},
        "gentle":    {"rejection": ["{name}가 완전히 해리되어 아무 반응도 하지 않고 있다.", "{name}가 소리 없이 눈물만 흘리며 의식이 멀어지고 있다."]},
        "cheerful":  {"rejection": ["{name}가 비명조차 나오지 않는 상태로 경련하고 있다.", "{name}가 정신이 완전히 나간 채 헛웃음을 짓고 있다."]},
        "timid":     {"rejection": ["{name}가 의식을 잃은 듯 축 늘어져 있다.", "{name}가 완전히 셧다운되어 눈만 멍하게 뜨고 있다."]},
        "cold":      {"rejection": ["{name}가 인간이기를 포기한 눈빛으로 누워 있다.", "{name}의 눈에 살의만 남은 채 모든 감정이 사라졌다."]},
        "seductive": {"rejection": ["{name}가 살아있는 시체처럼 축 늘어져 있다.", "{name}가 해리된 채 구역질만 반복하고 있다."]},
        "fierce":    {"rejection": ["{name}가 생존 본능만으로 경련하며 저항하고 있다.", "{name}가 짐승처럼 울부짖으며 발톱을 세우고 있다."]},
        "proud":     {"rejection": ["{name}가 모든 자존심이 부서진 채 빈 눈빛이다.", "{name}가 분노조차 타버린 재 같은 표정이다."]},
        "innocent":  {"rejection": ["{name}가 정신이 완전히 나간 채 아무것도 인지하지 못하고 있다.", "{name}가 현실을 거부하며 무의식 속으로 빠져들고 있다."]},
        "devoted":   {"rejection": ["{name}가 모든 신뢰와 사랑이 산산조각 나 빈 껍데기가 되어 있다.", "{name}가 절망 너머의 무 속에서 멍하니 있다."]},
    },

    # ── ROUGH × rebellion ────────────────────────
    "rough:during:rebellion_mild": {
        "stoic": {
            "rejection": ["{name}가 고통을 참으며 살의 어린 눈빛을 보내고 있다.", "{name}가 이를 악물어 피가 나도록 참고 있다."],
            "lust":      ["{name}가 고통 속에서도 몸이 거칠게 반응하고 있다."],
        },
        "gentle": {
            "rejection": ["{name}가 울면서 아프다고 호소하고 있다.", "{name}가 고통에 시트를 움켜쥐며 견디고 있다."],
            "lust":      ["{name}가 고통과 쾌감이 뒤섞여 혼란스러워하며 울고 있다."],
        },
        "cheerful": {
            "rejection": ["{name}가 비명을 지르며 밀어내려 하고 있다.", "{name}가 고통에 미소가 완전히 사라지고 있다."],
            "lust":      ["{name}가 거칠수록 몸이 반응하는 것에 충격받은 표정이다."],
        },
        "timid": {
            "rejection": ["{name}가 공포에 비명을 지르며 울고 있다.", "{name}가 고통에 정신을 잃을 것 같은 표정이다."],
            "lust":      ["{name}가 공포 속에서도 몸이 반응해 자기혐오에 떨고 있다."],
        },
        "cold": {
            "rejection": ["{name}가 차가운 분노를 담은 눈으로 견디고 있다.", "{name}가 감정을 완전히 차단하고 참고 있다."],
        },
        "seductive": {
            "rejection": ["{name}가 극도의 혐오감에 구역질하고 있다.", "{name}가 냉소와 분노가 섞인 눈빛이다."],
        },
        "fierce": {
            "rejection": ["{name}가 이를 물어뜯으며 격렬하게 반격하고 있다.", "{name}가 야수처럼 발톱을 세우고 있다."],
        },
        "proud": {
            "rejection": ["{name}가 굴욕에 분노의 눈물을 흘리며 이를 갈고 있다.", "{name}가 자존심이 짓밟히는 고통에 떨고 있다."],
        },
        "innocent": {
            "rejection": ["{name}가 무슨 일인지 모르겠다며 공포에 울고 있다.", "{name}가 고통에 비명을 지르며 벗어나려 하고 있다."],
        },
        "devoted": {
            "rejection": ["{name}가 고통스럽지만 배신감이 더 크다는 표정이다.", "{name}가 왜 이렇게까지 하느냐며 눈물을 흘리고 있다."],
        },
    },
    "rough:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 살의를 품은 채 피가 나도록 입술을 깨물고 있다.", "{name}가 인간의 한계를 넘은 분노로 견디고 있다."]},
        "gentle":    {"rejection": ["{name}가 고통에 비명을 지르며 정신을 잃어가고 있다.", "{name}가 울부짖으며 누군가 도와달라고 하고 있다."]},
        "cheerful":  {"rejection": ["{name}가 날카로운 비명을 지르며 필사적으로 발버둥치고 있다.", "{name}가 고통에 미소의 흔적조차 사라진 상태다."]},
        "timid":     {"rejection": ["{name}가 공포에 울부짖다 목이 쉬어 소리가 나오지 않고 있다.", "{name}가 의식이 오락가락하며 경련하고 있다."]},
        "cold":      {"rejection": ["{name}가 살의만 남은 눈빛으로 당신을 꿰뚫고 있다.", "{name}가 모든 고통을 기억에 새기고 있다는 눈빛이다."]},
        "seductive": {"rejection": ["{name}가 완전한 혐오와 분노에 몸을 떨고 있다.", "{name}가 구역질하며 극도의 경멸을 보내고 있다."]},
        "fierce":    {"rejection": ["{name}가 생존 본능으로 물어뜯고 할퀴며 필사적으로 싸우고 있다.", "{name}가 짐승 같은 울음소리를 내며 저항하고 있다."]},
        "proud":     {"rejection": ["{name}가 굴욕과 분노로 이성을 잃어가고 있다.", "{name}가 목놓아 울며 반드시 대가를 치르게 하겠다고 하고 있다."]},
        "innocent":  {"rejection": ["{name}가 극심한 고통에 비명을 지르며 의식을 잃어가고 있다.", "{name}가 공포에 말도 못 하고 경련만 하고 있다."]},
        "devoted":   {"rejection": ["{name}가 신뢰가 완전히 무너지며 절규하고 있다.", "{name}가 절망과 고통에 정신이 나가고 있다."]},
    },
    "rough:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 감정이 모두 꺼진 채 시체처럼 누워 있다.", "{name}가 살의만 남긴 채 의식이 멀어지고 있다."]},
        "gentle":    {"rejection": ["{name}가 완전히 해리되어 인형처럼 축 늘어져 있다.", "{name}가 의식을 잃었지만 눈물만 계속 흘리고 있다."]},
        "cheerful":  {"rejection": ["{name}가 정신이 완전히 나간 채 경련하고 있다.", "{name}가 의미 없는 웃음과 울음이 뒤섞여 나오고 있다."]},
        "timid":     {"rejection": ["{name}가 완전히 의식을 잃고 축 늘어져 있다.", "{name}가 과호흡 끝에 기절한 상태다."]},
        "cold":      {"rejection": ["{name}가 인간이기를 완전히 포기한 눈빛으로 누워 있다.", "{name}의 눈에 감정이라곤 살의 하나만 남아 있다."]},
        "seductive": {"rejection": ["{name}가 완전히 해리되어 살아있는 시체 같다.", "{name}가 의식이 없지만 구역질만 반복하고 있다."]},
        "fierce":    {"rejection": ["{name}가 의식을 잃어가면서도 본능적으로 저항하고 있다.", "{name}가 생존 본능만으로 경련하며 발톱을 세우고 있다."]},
        "proud":     {"rejection": ["{name}가 자존심도 분노도 모두 부서진 채 빈 눈빛이다.", "{name}가 인간으로서의 존엄이 완전히 짓밟힌 표정이다."]},
        "innocent":  {"rejection": ["{name}가 완전히 의식을 잃고 아무런 반응도 없다.", "{name}가 정신이 현실을 거부하며 셧다운된 상태다."]},
        "devoted":   {"rejection": ["{name}가 사랑과 신뢰가 모두 소멸한 빈 껍데기가 되어 있다.", "{name}가 절망 너머 무의 세계로 빠져들고 있다."]},
    },
}


# ─────────────────────────────────────────────
# ARCHETYPE_TEMPLATES — 행위별 고유 묘사
# 카테고리 fallback으로 대부분 커버, 특히 묘사가 고유한 행위만 정의
# ─────────────────────────────────────────────

ARCHETYPE_TEMPLATES = {
    # 포옹 — 카테고리와 별개로 고유한 터치감
    "hug:during": {
        "stoic":     {"romance": ["{name}가 당신에게 기대어 있다.", "{name}가 편안하게 안겨 있다."],
                      "rejection": ["{name}가 뻣뻣하게 서 있다.", "{name}가 어색하게 서 있다."]},
        "gentle":    {"romance": ["{name}가 당신의 가슴에 얼굴을 묻고 있다.", "{name}가 살며시 안기며 체온을 나누고 있다."]},
        "timid":     {"romance": ["{name}가 조용히 눈을 감고 안겨 있다.", "{name}가 살짝 떨리며 안겨 있다."]},
        "cheerful":  {"romance": ["{name}가 기분 좋게 안겨 있다. 콧노래가 들린다."]},
        "fierce":    {"romance": ["{name}가 힘주어 안고 있다. 팔에 힘이 들어가 있다."]},
        "seductive": {"romance": ["{name}가 느긋하게 안기며 당신의 목에 얼굴을 묻고 있다."]},
        "devoted":   {"romance": ["{name}가 당신의 심장 소리에 귀를 기울이고 있다."]},
    },

    # 딥키스 — 호흡/혀 묘사가 고유
    "deep_kiss:during": {
        "stoic":     {"romance": ["{name}와 깊은 키스를 나누고 있다. {name}가 눈을 감고 있다."],
                      "lust": ["{name}가 거칠게 숨을 몰아쉬며 키스에 빠져 있다."]},
        "gentle":    {"romance": ["{name}가 부드럽게 당신의 입술을 따르고 있다."],
                      "lust": ["{name}가 숨을 삼키며 더 깊이 키스하고 있다."]},
        "cheerful":  {"romance": ["{name}가 눈을 감고 행복하게 키스에 응하고 있다."]},
        "seductive": {"romance": ["{name}가 능숙하게 키스를 이끌고 있다."],
                      "lust": ["{name}가 도발적으로 혀를 내밀고 있다."]},
        "fierce":    {"romance": ["{name}가 거칠게 당신의 입술을 물고 있다."]},
    },

    # 펠라치오 — 특수 묘사
    "fellatio:during": {
        "stoic":     {"romance": ["{name}가 서툴지만 열심히 하고 있다.", "{name}가 때때로 당신을 올려다본다."],
                      "rejection": ["{name}가 눈을 피하며 하고 있다.", "{name}가 묵묵히 따르고 있다."]},
        "gentle":    {"romance": ["{name}가 조심스럽게 하고 있다.", "{name}가 당신의 반응을 살피며 하고 있다."],
                      "lust": ["{name}가 점점 열심히 하고 있다."]},
        "cheerful":  {"romance": ["{name}가 호기심 어린 눈으로 하고 있다."],
                      "lust": ["{name}가 크게 소리를 내며 하고 있다."]},
        "timid":     {"romance": ["{name}가 눈물이 글썽이며 하고 있다.", "{name}가 떨리는 손으로 잡고 있다."],
                      "rejection": ["{name}가 겁먹은 채 하고 있다."]},
        "cold":      {"romance": ["{name}가 담담하게 하고 있다. 귀만 빨갛다."],
                      "lust": ["{name}가 냉정함을 잃고 점점 빠져들고 있다."]},
        "seductive": {"romance": ["{name}가 능숙하게 당신을 만족시키고 있다."],
                      "lust": ["{name}가 도발적으로 바라보며 하고 있다."]},
        "fierce":    {"lust": ["{name}가 거칠게 하고 있다."]},
        "proud":     {"romance": ["{name}가 굴욕적이지만 하고 있다. 귀끝이 빨갛다."],
                      "lust": ["{name}의 자존심이 무너지고 있다."]},
        "innocent":  {"romance": ["{name}가 어떻게 하는 건지 모르겠다는 표정으로 하고 있다."]},
        "devoted":   {"romance": ["{name}가 기쁜 마음으로 봉사하고 있다."],
                      "lust": ["{name}가 열심히 해서 당신을 만족시키려 하고 있다."]},
    },

    # 삽입 — 크기통증 특수 처리는 override에서
    "vaginal_penetration:during": {
        "stoic":     {"romance": ["{name}가 편안하게 몸을 맡기고 있다.", "{name}가 허리를 맞추고 있다."],
                      "rejection": ["{name}가 이를 악물며 견디고 있다.", "{name}가 얼굴을 묻고 있다."]},
    },

    # ── 반발 템플릿 (rebellion) ──────────────────────────────

    # 포옹 반발
    "hug:during:rebellion_mild": {
        "stoic":     {"rejection": ["{name}가 뻣뻣하게 경직되어 밀어내고 있다.", "{name}가 불쾌한 듯 몸을 비틀고 있다."]},
        "gentle":    {"rejection": ["{name}가 조심스럽게 손으로 밀어내고 있다.", "{name}가 불편한 표정으로 몸을 움츠리고 있다."]},
        "cheerful":  {"rejection": ["{name}가 억지 웃음을 지으며 빠져나가려 하고 있다.", "{name}가 어색하게 몸을 빼고 있다."]},
        "timid":     {"rejection": ["{name}가 겁먹은 듯 몸을 굳히고 있다.", "{name}가 떨리는 손으로 약하게 밀어내고 있다."]},
        "cold":      {"rejection": ["{name}가 차갑게 어깨를 밀어내고 있다.", "{name}가 눈도 마주치지 않고 몸을 비틀고 있다."]},
    },
    "hug:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 양 팔로 강하게 밀어내고 있다.", "{name}가 주먹으로 가슴팍을 치고 있다."]},
        "gentle":    {"rejection": ["{name}가 발버둥치며 '놓아주세요'라고 외치고 있다.", "{name}가 울면서 양손으로 밀어내고 있다."]},
        "cheerful":  {"rejection": ["{name}가 소리를 지르며 몸부림치고 있다.", "{name}가 필사적으로 밀치며 빠져나가려 하고 있다."]},
        "timid":     {"rejection": ["{name}가 공포에 질려 발버둥치고 있다.", "{name}가 울부짖으며 주먹으로 때리고 있다."]},
        "cold":      {"rejection": ["{name}가 이를 악물고 팔꿈치로 밀어내고 있다.", "{name}가 살기 어린 눈으로 노려보며 밀치고 있다."]},
    },
    "hug:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 이빨로 어깨를 물어뜯고 있다.", "{name}가 돌처럼 굳어 아무 반응도 보이지 않고 있다."]},
        "gentle":    {"rejection": ["{name}가 손톱으로 할퀴며 비명을 지르고 있다.", "{name}가 체념한 듯 축 늘어져 있다."]},
        "cheerful":  {"rejection": ["{name}가 미친 듯이 할퀴고 물어뜯고 있다.", "{name}가 눈이 풀린 채 멍하게 있다."]},
        "timid":     {"rejection": ["{name}가 과호흡하며 의식이 흐려지고 있다.", "{name}가 혼이 빠진 듯 축 늘어져 있다."]},
        "cold":      {"rejection": ["{name}가 손톱으로 살을 파며 저항하고 있다.", "{name}가 눈빛이 완전히 꺼진 채 굳어 있다."]},
    },

    # 딥키스 반발
    "deep_kiss:during:rebellion_mild": {
        "stoic":     {"rejection": ["{name}가 고개를 돌려 입술을 피하고 있다.", "{name}가 입을 꾹 다문 채 견디고 있다."]},
        "gentle":    {"rejection": ["{name}가 눈물을 흘리며 고개를 젓고 있다.", "{name}가 입술을 꽉 다물고 얼굴을 돌리고 있다."]},
        "cheerful":  {"rejection": ["{name}가 불편한 듯 고개를 비틀고 있다.", "{name}가 입을 다문 채 눈을 질끈 감고 있다."]},
        "timid":     {"rejection": ["{name}가 겁에 질려 입술을 꾹 깨물고 있다.", "{name}가 울먹이며 고개를 돌리고 있다."]},
        "cold":      {"rejection": ["{name}가 차갑게 고개를 돌리며 입술을 피하고 있다.", "{name}가 이를 악물고 입을 열지 않고 있다."]},
    },
    "deep_kiss:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 입술을 깨물어 피가 맺히고 있다.", "{name}가 격렬하게 고개를 흔들며 거부하고 있다."]},
        "gentle":    {"rejection": ["{name}가 구역질하며 얼굴을 돌리고 있다.", "{name}가 울부짖으며 입을 막고 있다."]},
        "cheerful":  {"rejection": ["{name}가 이를 악물고 혀를 깨물려 하고 있다.", "{name}가 구역질하며 격렬하게 저항하고 있다."]},
        "timid":     {"rejection": ["{name}가 숨이 막혀 발버둥치고 있다.", "{name}가 울면서 격렬하게 고개를 흔들고 있다."]},
        "cold":      {"rejection": ["{name}가 상대의 입술을 깨물어 찢으려 하고 있다.", "{name}가 구역질하며 침을 뱉고 있다."]},
    },
    "deep_kiss:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 상대의 혀를 이빨로 물어뜯고 있다.", "{name}가 눈이 풀린 채 입을 벌리고 있다."]},
        "gentle":    {"rejection": ["{name}가 구토하며 온몸을 떨고 있다.", "{name}가 의식을 잃은 듯 반응이 없다."]},
        "cheerful":  {"rejection": ["{name}가 헛구역질하며 미친 듯이 몸부림치고 있다.", "{name}가 눈동자의 초점이 사라져 있다."]},
        "timid":     {"rejection": ["{name}가 호흡이 멎은 듯 축 늘어져 있다.", "{name}가 눈이 뒤집힌 채 경련하고 있다."]},
        "cold":      {"rejection": ["{name}가 상대의 혀를 깨물어 피를 맛보고 있다.", "{name}가 눈빛이 완전히 죽은 채 멍하게 있다."]},
    },

    # 성기 애무 반발
    "genital_caress:during:rebellion_mild": {
        "stoic":     {"rejection": ["{name}가 다리를 꽉 오므리며 거부하고 있다.", "{name}가 눈물을 참으며 몸을 움츠리고 있다."]},
        "gentle":    {"rejection": ["{name}가 울면서 다리를 닫으려 하고 있다.", "{name}가 손을 떨며 밀어내려 하고 있다."]},
        "cheerful":  {"rejection": ["{name}가 치를 떨며 다리를 모으고 있다.", "{name}가 눈물을 흘리며 손목을 잡으려 하고 있다."]},
        "timid":     {"rejection": ["{name}가 공포에 질려 다리를 꼬고 있다.", "{name}가 흐느끼며 '하지 마세요'라고 애원하고 있다."]},
        "cold":      {"rejection": ["{name}가 차가운 눈으로 다리를 오므리고 있다.", "{name}가 이를 악물며 손을 비틀어 잡고 있다."]},
    },
    "genital_caress:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 발로 걷어차며 저항하고 있다.", "{name}가 비명을 지르며 손목을 비틀고 있다."]},
        "gentle":    {"rejection": ["{name}가 울부짖으며 발길질하고 있다.", "{name}가 절규하며 온몸으로 저항하고 있다."]},
        "cheerful":  {"rejection": ["{name}가 비명을 지르며 발로 차고 있다.", "{name}가 울부짖으며 할퀴고 있다."]},
        "timid":     {"rejection": ["{name}가 공포에 비명을 지르며 발버둥치고 있다.", "{name}가 히스테리를 일으키며 울고 있다."]},
        "cold":      {"rejection": ["{name}가 무릎으로 가격하며 저항하고 있다.", "{name}가 살기를 드러내며 할퀴고 있다."]},
    },
    "genital_caress:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 눈빛이 꺼진 채 아무 반응도 없다.", "{name}가 해리된 듯 천장만 바라보고 있다."]},
        "gentle":    {"rejection": ["{name}가 의식이 흐려져 축 늘어져 있다.", "{name}가 눈물도 마른 채 멍하게 있다."]},
        "cheerful":  {"rejection": ["{name}가 완전히 풀이 죽어 반응이 없다.", "{name}가 빈 눈으로 허공을 바라보고 있다."]},
        "timid":     {"rejection": ["{name}가 의식을 잃은 듯 눈이 감겨 있다.", "{name}가 실신 직전처럼 가늘게 떨고 있다."]},
        "cold":      {"rejection": ["{name}가 모든 감정이 사라진 채 인형처럼 있다.", "{name}가 눈빛에 살의만 남아 있다."]},
    },

    # 삽입 반발
    "vaginal_penetration:during:rebellion_mild": {
        "stoic":     {"rejection": ["{name}가 고통에 이를 악물며 눈물을 참고 있다.", "{name}가 부드럽게 해달라고 간신히 말하고 있다."]},
        "gentle":    {"rejection": ["{name}가 아파서 울면서 살살 해달라고 애원하고 있다.", "{name}가 눈물범벅이 되어 끙끙대고 있다."]},
        "cheerful":  {"rejection": ["{name}가 고통에 얼굴을 일그러뜨리며 눈물을 흘리고 있다.", "{name}가 이를 악물며 멈춰달라고 하고 있다."]},
        "timid":     {"rejection": ["{name}가 두려움에 떨며 울먹이고 있다.", "{name}가 고통에 '그만'이라고 애원하고 있다."]},
        "cold":      {"rejection": ["{name}가 이를 악물고 고통을 참으며 눈물이 흐르고 있다.", "{name}가 차가운 눈으로 노려보며 견디고 있다."]},
    },
    "vaginal_penetration:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 비명을 지르며 밀어내고 있다.", "{name}가 온몸으로 저항하며 발버둥치고 있다."]},
        "gentle":    {"rejection": ["{name}가 절규하며 필사적으로 도망치려 하고 있다.", "{name}가 울부짖으며 발길질하고 있다."]},
        "cheerful":  {"rejection": ["{name}가 날카로운 비명과 함께 할퀴고 있다.", "{name}가 미친 듯이 몸부림치며 빠져나가려 하고 있다."]},
        "timid":     {"rejection": ["{name}가 찢어질 듯한 비명을 지르고 있다.", "{name}가 공포에 질려 경련하며 울고 있다."]},
        "cold":      {"rejection": ["{name}가 살기 어린 눈으로 손톱을 세워 할퀴고 있다.", "{name}가 이를 악물고 머리를 들이받으려 하고 있다."]},
    },
    "vaginal_penetration:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 의식이 끊긴 듯 눈이 풀려 있다.", "{name}가 영혼이 빠진 채 인형처럼 있다."]},
        "gentle":    {"rejection": ["{name}가 실신하여 축 늘어져 있다.", "{name}가 눈물도 말라 빈 눈으로 멍하게 있다."]},
        "cheerful":  {"rejection": ["{name}가 완전히 무너져 의식이 흐려지고 있다.", "{name}가 눈동자가 풀린 채 반응이 없다."]},
        "timid":     {"rejection": ["{name}가 실신하여 완전히 축 늘어져 있다.", "{name}가 의식 없이 가늘게 경련하고 있다."]},
        "cold":      {"rejection": ["{name}가 눈빛이 완전히 죽은 채 미동도 없다.", "{name}가 해리된 채 허공을 응시하고 있다."]},
    },

    # 펠라치오 반발
    "fellatio:during:rebellion_mild": {
        "stoic":     {"rejection": ["{name}가 마지못해 하면서 구역질을 참고 있다.", "{name}가 눈물을 글썽이며 억지로 하고 있다."]},
        "gentle":    {"rejection": ["{name}가 울면서 마지못해 하고 있다.", "{name}가 구역질하며 눈물을 흘리고 있다."]},
        "cheerful":  {"rejection": ["{name}가 굴욕감에 눈물을 흘리며 하고 있다.", "{name}가 구역질을 참으며 얼굴을 찡그리고 있다."]},
        "timid":     {"rejection": ["{name}가 떨면서 겁먹은 채 억지로 하고 있다.", "{name}가 울먹이며 구역질하고 있다."]},
        "cold":      {"rejection": ["{name}가 차가운 눈으로 노려보며 마지못해 하고 있다.", "{name}가 구역질을 참으며 이를 악물고 있다."]},
    },
    "fellatio:during:rebellion_high": {
        "stoic":     {"rejection": ["{name}가 이빨로 깨물려고 하며 격렬하게 거부하고 있다.", "{name}가 구역질하며 머리를 빼려고 발버둥치고 있다."]},
        "gentle":    {"rejection": ["{name}가 숨이 막혀 기침하며 도망치려 하고 있다.", "{name}가 구토하며 울부짖고 있다."]},
        "cheerful":  {"rejection": ["{name}가 이빨을 세우며 격렬하게 저항하고 있다.", "{name}가 기침하며 필사적으로 빠져나가려 하고 있다."]},
        "timid":     {"rejection": ["{name}가 숨이 막혀 공포에 질린 채 발버둥치고 있다.", "{name}가 구토하며 히스테리를 일으키고 있다."]},
        "cold":      {"rejection": ["{name}가 이빨을 세워 깨물려는 살기를 드러내고 있다.", "{name}가 기침하며 머리를 격렬하게 흔들고 있다."]},
    },
    "fellatio:during:rebellion_extreme": {
        "stoic":     {"rejection": ["{name}가 완전히 무너져 멍하게 입을 벌리고 있다.", "{name}가 의식이 끊긴 듯 아무 반응 없이 있다."]},
        "gentle":    {"rejection": ["{name}가 의식을 잃은 듯 축 늘어져 있다.", "{name}가 눈물도 마른 채 인형처럼 있다."]},
        "cheerful":  {"rejection": ["{name}가 눈이 완전히 풀린 채 반응이 없다.", "{name}가 영혼이 빠진 듯 멍하게 있다."]},
        "timid":     {"rejection": ["{name}가 실신 직전으로 눈이 감겨가고 있다.", "{name}가 의식 없이 축 늘어져 있다."]},
        "cold":      {"rejection": ["{name}가 눈빛에 순수한 살의만 남아 있다.", "{name}가 모든 감정이 사라진 채 비어 있다."]},
    },
}


# ─────────────────────────────────────────────
# ReactionGenerator 클래스
# ─────────────────────────────────────────────

class ReactionGenerator:
    """성격 아키타입 + 2D 좌표(호감×욕망) 기반 반응 생성기.

    네임드 NPC: REACTION_PROFILE의 override로 고유 대사 유지 + 나머지 generator.
    모브 NPC: REACTION_PROFILE만으로 전체 반응 자동 생성.
    """

    def __init__(self, profile):
        self.profile = profile
        self.name = profile["name"]
        self.archetype = profile.get("archetype", "stoic")
        self._overrides = profile.get("overrides", {})

    def generate(self, action_id, timing, state):
        """반응 텍스트 생성 — 4단계 fallback chain.

        1) 캐릭터 override (cascade: rebellion+arousal → rebellion → arousal → base)
        2) 행위별 아키타입 템플릿 (ARCHETYPE_TEMPLATES)
        3) 카테고리 fallback (CATEGORY_TEMPLATES)
        4) None
        """
        tone = resolve_tone(state)
        arousal = resolve_arousal_tier(state.get("성욕", 0))
        rebellion_tier = resolve_rebellion_tier(state.get("반발", 0))
        key = f"{action_id}:{timing}"

        # 1) 캐릭터 override
        text = self._try_override(key, tone, arousal, rebellion_tier)
        if text:
            return text

        # 2) 행위별 아키타입 템플릿
        text = self._try_archetype_template(key, tone, arousal, rebellion_tier)
        if text:
            return text

        # 3) 카테고리 fallback
        text = self._try_category_fallback(action_id, timing, tone, arousal, rebellion_tier)
        if text:
            return text

        return None

    def _try_override(self, key, tone, arousal, rebellion_tier):
        """캐릭터 override에서 cascade 조회."""
        arch = self.archetype
        fmt = self._fmt_vars()
        arousal_tiers = [arousal] if arousal in ("extreme", "high") else []

        for cascade_key in _build_cascade_keys(key, arousal_tiers, rebellion_tier):
            override = self._overrides.get(cascade_key, {})
            texts = override.get(arch, {}).get(tone)
            if texts:
                return random.choice(texts).format(**fmt)

        return None

    def _try_archetype_template(self, key, tone, arousal, rebellion_tier):
        """ARCHETYPE_TEMPLATES에서 cascade 조회."""
        arch = self.archetype
        fmt = self._fmt_vars()
        arousal_tiers = [arousal] if arousal in ("extreme", "high") else []

        for cascade_key in _build_cascade_keys(key, arousal_tiers, rebellion_tier):
            templates = ARCHETYPE_TEMPLATES.get(cascade_key, {})
            texts = templates.get(arch, {}).get(tone)
            if texts:
                return random.choice(texts).format(**fmt)

        return None

    def _try_category_fallback(self, action_id, timing, tone, arousal, rebellion_tier):
        """행위 카테고리별 cascade fallback."""
        category = ACTION_TO_CATEGORY.get(action_id)
        if not category:
            return None

        cat_key = f"{category}:{timing}"
        arch = self.archetype
        fmt = self._fmt_vars()
        arousal_tiers = [arousal] if arousal in ("extreme", "high") else []

        for cascade_key in _build_cascade_keys(cat_key, arousal_tiers, rebellion_tier):
            templates = CATEGORY_TEMPLATES.get(cascade_key, {})
            texts = templates.get(arch, {}).get(tone)
            if texts:
                return random.choice(texts).format(**fmt)

        return None

    def _fmt_vars(self):
        """포맷 변수 딕트."""
        return {"name": self.name, **self.profile.get("vars", {})}
