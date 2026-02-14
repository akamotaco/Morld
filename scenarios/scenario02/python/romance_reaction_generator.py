"""묘사 생성기 — 성격 아키타입 + 2D 좌표(호감×욕망) 기반 (:during 3인칭)

10종 아키타입 × 5 카테고리 × 4 관계톤 × 3 흥분단계 = 풍부한 자동 반응.
네임드 NPC는 override + generator fallback, 모브 NPC는 REACTION_PROFILE만으로 전체 자동.

대사(:start 1인칭)는 romance_line_generator.py 참조.
"""
import math
import random

# ─────────────────────────────────────────────
# 2D 좌표 공간
# ─────────────────────────────────────────────
#   욕망 ↑
#   100 │
#       │    lust(20,70)       romance(80,70)
#    50 │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
#       │    rejection(20,20)  platonic(80,20)
#     0 └────────────────────────────────→ 호감
#       0                  50              100

TONE_COORDS = {
    "romance":   (80, 70),
    "platonic":  (80, 20),
    "lust":      (20, 70),
    "rejection": (20, 20),
}


def resolve_tone(affection, desire):
    """(호감, 욕망) → nearest tone. 동률 시 랜덤."""
    best_dist = float("inf")
    best_tones = []
    for tone, (tx, ty) in TONE_COORDS.items():
        d = math.hypot(affection - tx, desire - ty)
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


# ─────────────────────────────────────────────
# 행위 카테고리 매핑
# ─────────────────────────────────────────────

ACTION_TO_CATEGORY = {
    # light — 가벼운 접촉
    "hug": "light", "deep_kiss": "light", "tongue_play": "light",
    "french_kiss": "light", "kiss": "light",
    # medium — 중간 수위
    "breast_touch": "medium", "breast_squeeze": "medium",
    "butt_squeeze": "medium", "breast_suck": "medium",
    "nipple_suck": "medium", "paizuri": "medium",
    "face_touch": "medium", "neck_touch": "medium",
    "ear_touch": "medium",
    # strong — 강한 자극
    "genital_touch": "strong", "clit_rub": "strong",
    "clit_lick": "strong", "cunnilingus": "strong",
    "finger_insertion": "strong", "fellatio": "strong",
    "penis_touch": "strong", "penis_rub": "strong",
    # penetration — 삽입
    "vaginal_penetration": "penetration",
    "anal_penetration": "penetration",
    "receive_penetration": "penetration",
    "receive_anal": "penetration",
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
            "platonic":  ["{name}가 조심스럽게 받아들이고 있다.", "{name}가 살짝 미소짓고 있다."],
            "lust":      ["{name}가 작은 소리를 내고 있다.", "{name}의 손이 당신을 잡고 있다."],
            "rejection": ["{name}가 당혹스러운 표정이다.", "{name}가 어찌할 줄 모르고 있다."],
        },
        "cheerful": {
            "romance":   ["{name}가 기분 좋게 안겨 있다.", "{name}가 콧노래를 흥얼거리고 있다."],
            "platonic":  ["{name}가 씩 웃고 있다.", "{name}가 장난스럽게 받아주고 있다."],
            "lust":      ["{name}가 숨을 참으며 안겨 있다.", "{name}의 심장이 빠르게 뛰고 있다."],
            "rejection": ["{name}가 어색하게 웃고 있다.", "{name}가 살짝 밀어내고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 조용히 눈을 감고 있다.", "{name}가 살짝 떨리며 안겨 있다."],
            "platonic":  ["{name}가 얼어붙은 듯 가만히 있다.", "{name}의 볼이 붉다."],
            "lust":      ["{name}가 몸을 떨며 기대어 있다.", "{name}가 작게 숨을 삼키고 있다."],
            "rejection": ["{name}가 굳어 있다.", "{name}가 눈을 내리깔고 있다."],
        },
        "cold": {
            "romance":   ["{name}가 조용히 허용하고 있다.", "{name}의 표정이 미세하게 풀려 있다."],
            "platonic":  ["{name}가 무표정하게 받아들이고 있다.", "{name}가 담담히 서 있다."],
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
            "platonic":  ["{name}가 신기한 듯 가만히 있다.", "{name}가 두리번거리고 있다."],
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
            "platonic":  ["{name}가 얼굴을 붉히며 참고 있다.", "{name}가 수줍게 눈을 피하고 있다."],
            "lust":      ["{name}가 당신의 손 위에 자기 손을 올리고 있다.", "{name}가 작은 신음을 내고 있다."],
            "rejection": ["{name}가 놀라서 몸을 움츠리고 있다.", "{name}가 당혹스러워하고 있다."],
        },
        "cheerful": {
            "romance":   ["{name}가 얼굴을 붉히며 웃고 있다.", "{name}가 장난스럽게 반응하고 있다."],
            "platonic":  ["{name}가 어색하게 웃고 있다.", "{name}가 호들갑을 떨고 있다."],
            "lust":      ["{name}가 크게 반응하고 있다.", "{name}가 감탄사를 내고 있다."],
            "rejection": ["{name}가 놀라서 소리를 지르고 있다.", "{name}가 밀어내고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 눈을 꽉 감고 받아들이고 있다.", "{name}가 조용히 떨리고 있다."],
            "platonic":  ["{name}가 얼어붙어 있다.", "{name}가 고개를 숙이고 있다."],
            "lust":      ["{name}가 눈물이 글썽이며 떨고 있다.", "{name}가 작은 소리를 참고 있다."],
            "rejection": ["{name}가 몸을 웅크리고 있다.", "{name}가 겁에 질려 있다."],
        },
        "cold": {
            "romance":   ["{name}가 눈을 감고 허용하고 있다.", "{name}의 표정이 미세하게 변하고 있다."],
            "platonic":  ["{name}가 무표정하게 참고 있다.", "{name}가 감정을 숨기고 있다."],
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
            "platonic":  ["{name}가 이게 뭔지 모르겠다는 표정이다.", "{name}가 눈을 깜빡이고 있다."],
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
            "platonic":  ["{name}가 부끄러운 듯 얼굴을 가리고 있다.", "{name}가 참으며 기다리고 있다."],
            "lust":      ["{name}가 참지 못하고 소리를 내고 있다.", "{name}가 당신에게 매달리고 있다."],
            "rejection": ["{name}가 몸을 움츠리고 있다.", "{name}가 눈물이 그렁그렁하다."],
        },
        "cheerful": {
            "romance":   ["{name}가 부끄러워하면서도 반응하고 있다.", "{name}가 당신을 바라보고 있다."],
            "platonic":  ["{name}가 소리를 참으려 입을 막고 있다.", "{name}가 얼굴이 빨갛다."],
            "lust":      ["{name}가 큰 소리로 반응하고 있다.", "{name}가 참지 못하고 있다."],
            "rejection": ["{name}가 비명을 지르며 밀어내고 있다.", "{name}가 놀라서 뒤로 빠지고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 떨리는 몸으로 받아들이고 있다.", "{name}가 눈물을 글썽이며 참고 있다."],
            "platonic":  ["{name}가 몸을 웅크리며 견디고 있다.", "{name}가 고개를 숙이고 있다."],
            "lust":      ["{name}가 온몸을 떨며 소리를 참고 있다.", "{name}가 시트를 움켜쥐고 있다."],
            "rejection": ["{name}가 겁에 질려 굳어 있다.", "{name}가 눈물이 흐르고 있다."],
        },
        "cold": {
            "romance":   ["{name}가 감정을 숨기려 하지만 숨소리가 흔들리고 있다.", "{name}가 눈을 감고 허용하고 있다."],
            "platonic":  ["{name}가 무표정을 유지하려 애쓰고 있다.", "{name}가 자세를 바로잡고 있다."],
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
            "platonic":  ["{name}가 혼란스러워하고 있다.", "{name}가 무슨 일인지 모르겠다는 표정이다."],
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
            "platonic":  ["{name}가 참으며 당신을 기다리고 있다.", "{name}가 눈을 감고 받아들이고 있다."],
            "lust":      ["{name}가 작은 소리를 내며 매달리고 있다.", "{name}가 당신의 이름을 부르고 있다."],
            "rejection": ["{name}가 눈물을 참으며 견디고 있다.", "{name}가 고통스러운 표정이다."],
        },
        "cheerful": {
            "romance":   ["{name}가 즐기듯 당신에게 반응하고 있다.", "{name}가 미소짓며 당신을 바라보고 있다."],
            "platonic":  ["{name}가 어색하지만 받아들이고 있다.", "{name}가 부끄러워하며 눈을 피하고 있다."],
            "lust":      ["{name}가 참지 못하고 크게 소리를 내고 있다.", "{name}가 당신에게 매달리고 있다."],
            "rejection": ["{name}가 고통에 비명을 참고 있다.", "{name}가 몸을 비틀고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 떨리지만 당신을 받아들이고 있다.", "{name}가 눈을 감고 매달려 있다."],
            "platonic":  ["{name}가 겁먹었지만 참고 있다.", "{name}가 시트를 움켜쥐고 있다."],
            "lust":      ["{name}가 온몸을 떨며 소리를 내고 있다.", "{name}가 당신의 등에 손톱자국을 내고 있다."],
            "rejection": ["{name}가 눈물을 흘리며 굳어 있다.", "{name}가 고통에 몸을 웅크리고 있다."],
        },
        "cold": {
            "romance":   ["{name}가 눈을 감고 당신에게 맡기고 있다.", "{name}가 미세하게 허리를 맞추고 있다."],
            "platonic":  ["{name}가 무표정하게 받아들이고 있다.", "{name}가 태연한 척하고 있다."],
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
            "platonic":  ["{name}가 당혹스러워하며 참고 있다.", "{name}가 이상한 표정을 짓고 있다."],
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
            "platonic":  ["{name}가 눈물을 흘리며 참고 있다."],
            "lust":      ["{name}가 고통과 쾌감 사이에서 흔들리고 있다."],
            "rejection": ["{name}가 비명을 참으며 견디고 있다."],
        },
        "cheerful": {
            "romance":   ["{name}가 놀랐지만 당신을 믿고 견디고 있다."],
            "platonic":  ["{name}가 소리를 참으려 입을 막고 있다."],
            "lust":      ["{name}가 거칠수록 크게 반응하고 있다."],
            "rejection": ["{name}가 비명을 지르고 있다."],
        },
        "timid": {
            "romance":   ["{name}가 울면서도 당신을 잡고 있다."],
            "platonic":  ["{name}가 겁에 질려 떨고 있다."],
            "lust":      ["{name}가 두렵지만 멈추지 말라는 듯 잡고 있다."],
            "rejection": ["{name}가 공포에 울음을 터뜨리고 있다."],
        },
        "cold": {
            "romance":   ["{name}가 무너지지 않으려 이를 악물고 있다."],
            "platonic":  ["{name}가 고통을 느끼지 않는 척하고 있다."],
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
            "platonic":  ["{name}가 무슨 일인지 모르겠다는 표정으로 울고 있다."],
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

        1) 캐릭터 override (arousal-specific → base)
        2) 행위별 아키타입 템플릿 (ARCHETYPE_TEMPLATES)
        3) 카테고리 fallback (CATEGORY_TEMPLATES)
        4) None
        """
        tone = resolve_tone(state.get("호감", 0), state.get("욕망", 0))
        arousal = resolve_arousal_tier(state.get("성욕", 0))
        key = f"{action_id}:{timing}"

        # 1) 캐릭터 override
        text = self._try_override(key, tone, arousal)
        if text:
            return text

        # 2) 행위별 아키타입 템플릿
        text = self._try_archetype_template(key, tone, arousal)
        if text:
            return text

        # 3) 카테고리 fallback
        text = self._try_category_fallback(action_id, timing, tone, arousal)
        if text:
            return text

        return None

    def _try_override(self, key, tone, arousal):
        """캐릭터 override에서 조회."""
        arch = self.archetype
        fmt = self._fmt_vars()

        # arousal-specific override
        if arousal in ("extreme", "high"):
            override = self._overrides.get(f"{key}:{arousal}", {})
            texts = override.get(arch, {}).get(tone)
            if texts:
                return random.choice(texts).format(**fmt)

        # base override
        override = self._overrides.get(key, {})
        texts = override.get(arch, {}).get(tone)
        if texts:
            return random.choice(texts).format(**fmt)

        return None

    def _try_archetype_template(self, key, tone, arousal):
        """ARCHETYPE_TEMPLATES에서 아키타입별 조회."""
        arch = self.archetype
        fmt = self._fmt_vars()

        # arousal-specific
        if arousal in ("extreme", "high"):
            templates = ARCHETYPE_TEMPLATES.get(f"{key}:{arousal}", {})
            texts = templates.get(arch, {}).get(tone)
            if texts:
                return random.choice(texts).format(**fmt)

        # base
        templates = ARCHETYPE_TEMPLATES.get(key, {})
        texts = templates.get(arch, {}).get(tone)
        if texts:
            return random.choice(texts).format(**fmt)

        return None

    def _try_category_fallback(self, action_id, timing, tone, arousal):
        """행위 카테고리별 fallback."""
        category = ACTION_TO_CATEGORY.get(action_id)
        if not category:
            return None

        cat_key = f"{category}:{timing}"
        arch = self.archetype
        fmt = self._fmt_vars()

        # arousal-specific category
        if arousal in ("extreme", "high"):
            templates = CATEGORY_TEMPLATES.get(f"{cat_key}:{arousal}", {})
            texts = templates.get(arch, {}).get(tone)
            if texts:
                return random.choice(texts).format(**fmt)

        # base category
        templates = CATEGORY_TEMPLATES.get(cat_key, {})
        texts = templates.get(arch, {}).get(tone)
        if texts:
            return random.choice(texts).format(**fmt)

        return None

    def _fmt_vars(self):
        """포맷 변수 딕트."""
        return {"name": self.name, **self.profile.get("vars", {})}
