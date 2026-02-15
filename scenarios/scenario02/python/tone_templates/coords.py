"""좌표 기반 톤 시스템 — 2D 감정공간(sentiment × desire) + K-nearest 블렌딩

좌표 공간:
  X축 (sentiment): 호감 - 반발*0.8          (-100 ~ +100)
  Y축 (desire):    (성욕*0.5 + 욕망*0.5) - 순수도*0.5  (-100 ~ +100)

10개 좌표 포인트:
  #   흥분/욕구 ↑ (Y=+100)
  #        │
  #  (-80,0)  (-60,30) (-30,60)   (30,60)    (80,80)
  #  극한저항  강한저항  거부속흥분  기꺼운흥분  열정적환희
  #        │   +반응
  #  (-60,-30) (-30,0)  (30,0)     (80,30)
  #  공포/혐오  소극적   편안한수용  따뜻한쾌감
  #        │   저항
  #                                (80,-30)
  #                                수줍은애정
  #   순수 ↓ (Y=-100)
  # ─────────────────────────────────────────→ 감정 (X=+100)
"""
import random

# ─────────────────────────────────────────────
# 좌표 톤 정의
# ─────────────────────────────────────────────

COORD_TONES = {
    ( 80,  80): "열정적 환희",     # 높은 호감 + 강한 흥분
    ( 80,  30): "따뜻한 쾌감",     # 높은 호감 + 적당한 흥분
    ( 80, -30): "수줍은 애정",     # 높은 호감 + 순수/부끄러움
    ( 30,  60): "기꺼운 흥분",     # 적당한 호감 + 흥분
    ( 30,   0): "편안한 수용",     # 적당한 호감 + 평온
    (-30,  60): "거부 속 흥분",    # 약한 반발 + 신체 반응
    (-30,   0): "소극적 저항",     # 약한 반발
    (-60,  30): "강한 저항+반응",  # 강한 반발 + 약간의 반응
    (-60, -30): "공포/혐오",       # 강한 반발 + 위축
    (-80,   0): "극한 저항",       # 극심한 반발
}

# ─────────────────────────────────────────────
# 좌표 계산
# ─────────────────────────────────────────────

REB_WEIGHT = 0.8
INN_WEIGHT = 0.5

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


def calc_coordinates(state):
    """state dict → (sx, sy) 좌표.

    X = clamp(호감 - 반발*0.8, -100, 100)
    Y = clamp((성욕*0.5 + 욕망*0.5) - 순수도*0.5, -100, 100)
    """
    sx = max(-100, min(100,
        state.get("호감", 0) - state.get("반발", 0) * REB_WEIGHT))
    sy = max(-100, min(100,
        (state.get("성욕", 0) * 0.5 + state.get("욕망", 0) * 0.5)
        - _calc_innocence(state) * INN_WEIGHT))
    return sx, sy


def select_by_coord(coord_pool, sx, sy, k=3):
    """가장 가까운 k개 좌표의 텍스트풀 병합 → 랜덤 선택.

    coord_pool: {(x, y): [text, ...], ...}
    반환: 선택된 텍스트 문자열 또는 None.
    """
    if not coord_pool:
        return None

    distances = []
    for key, texts in coord_pool.items():
        if not isinstance(key, tuple) or not texts:
            continue
        dist_sq = (sx - key[0]) ** 2 + (sy - key[1]) ** 2
        distances.append((dist_sq, texts))

    if not distances:
        return None

    distances.sort(key=lambda x: x[0])
    merged = []
    for _, texts in distances[:k]:
        merged.extend(texts)
    return random.choice(merged) if merged else None


# ─────────────────────────────────────────────
# 행위 → 카테고리 매핑
# ─────────────────────────────────────────────

ACTION_TO_CATEGORY = {
    # light
    "hug": "light", "deep_kiss": "light", "tongue_play": "light",
    "french_kiss": "light", "kiss": "light",
    "head_pat": "light", "cheek_caress": "light", "cheek_pinch": "light",
    "lip_lick": "light", "whisper": "light",
    # medium
    "breast_touch": "medium", "breast_squeeze": "medium",
    "butt_squeeze": "medium", "breast_suck": "medium",
    "nipple_suck": "medium", "paizuri": "medium",
    "face_touch": "medium", "neck_touch": "medium",
    "ear_touch": "medium", "neck_kiss": "medium",
    "butt_caress": "medium", "breast_caress": "medium",
    "nipple_stimulation": "medium", "nipple_lick": "medium",
    "nipple_pinch": "medium", "breast_grab": "medium",
    # strong
    "genital_touch": "strong", "clit_rub": "strong",
    "clit_lick": "strong", "cunnilingus": "strong",
    "finger_insertion": "strong", "fellatio": "strong",
    "penis_touch": "strong", "penis_rub": "strong",
    "genital_caress": "strong", "clit_stimulation": "strong",
    "anal_stimulation": "strong", "rough_finger": "strong",
    # penetration
    "vaginal_penetration": "penetration",
    "anal_penetration": "penetration",
    "receive_penetration": "penetration",
    "receive_anal": "penetration",
    "thrust_deep": "penetration", "thrust_slow": "penetration",
    "grind": "penetration", "ejaculate": "penetration",
    # rough
    "rough_thrust": "rough", "hard_anal": "rough",
}
