# creature_reactions.py — 생물체(Creature) 종별 반응 묘사
#
# 수간(bestiality) 세션 중 생물체의 물리 반응.
# NPC 아키타입 시스템의 creature 대응물.
#
# 구조:
#   - 종별(species) 반응 풀: arousal_tier × gauge_tier → 텍스트 리스트
#   - 즉시 행위 반응: action_id → 텍스트 리스트
#   - 절정/절정 후 반응
#
# species = Monster.unique_id ("wolf", "spider", "bat", ...)
# fallback: "default" 풀 사용

import random
import morld


# ============================================
# 단계 판정 (romance_body_reaction.py와 동일)
# ============================================

def _arousal_tier(arousal):
    if arousal >= 80:
        return "extreme"
    if arousal >= 60:
        return "high"
    if arousal >= 30:
        return "medium"
    return "low"


def _gauge_tier(gauge):
    if gauge >= 80:
        return "critical"
    if gauge >= 60:
        return "high"
    if gauge >= 30:
        return "medium"
    return "low"


# ============================================
# 종별 이름 조회
# ============================================

def _get_species(partner_id):
    """partner_id → species 문자열 (Monster.unique_id)"""
    info = morld.get_unit_info(partner_id)
    if not info:
        return "default"
    return info.get("unique_id", "default")


# ============================================
# 토글 반응 풀 (during — 3인칭 묘사)
# ============================================
# 키: (arousal_tier, gauge_tier) → [텍스트, ...]

_TOGGLE_REACTIONS = {
    # ─── 늑대 (wolf) — 야수적, 거친 호흡, 으르렁 ───
    "wolf": {
        ("medium", "low"): [
            "늑대의 호흡이 거칠어지고 있다.",
            "늑대가 낮게 으르렁거리고 있다.",
        ],
        ("medium", "medium"): [
            "늑대가 이빨을 드러내며 거칠게 숨을 몰아쉬고 있다.",
            "늑대의 몸이 미세하게 떨리고 있다.",
        ],
        ("high", "low"): [
            "늑대가 짧게 울부짖으며 몸을 떨고 있다.",
            "늑대의 턱이 벌어지며 혀가 늘어져 있다.",
        ],
        ("high", "medium"): [
            "늑대가 격하게 헐떡이며 몸을 비틀고 있다.",
            "늑대의 온몸이 떨리며 으르렁거리는 소리가 끊이지 않는다.",
        ],
        ("high", "high"): [
            "늑대가 미친 듯이 몸을 떨며 길게 울부짖고 있다.",
            "늑대의 눈이 풀리고 혀가 축 늘어져 있다.",
        ],
        ("extreme", "low"): [
            "늑대가 숨을 거칠게 몰아쉬며 몸 전체가 경련하고 있다.",
            "늑대의 동공이 풀려 있다. 거친 숨소리만이 울려 퍼진다.",
        ],
        ("extreme", "medium"): [
            "늑대가 격렬하게 헐떡이며 뒷다리가 떨리고 있다.",
            "늑대의 몸이 격하게 떨리며 낮은 신음을 내고 있다.",
        ],
        ("extreme", "high"): [
            "늑대가 길게 하울링하며 몸 전체가 경직되어 있다.",
            "늑대의 온몸이 경련하고 있다. 곧 한계에 이를 것 같다.",
        ],
        ("extreme", "critical"): [
            "늑대가 미친 듯이 울부짖으며 온몸이 떨리고 있다!",
            "늑대의 몸이 극도로 긴장되어 있다. 한계에 다다른 것 같다!",
        ],
    },

    # ─── 거미 (spider) — 섬뜩, 다리 경련, 거미줄 분비 ───
    "spider": {
        ("medium", "low"): [
            "거미의 여러 다리가 미세하게 꿈틀거리고 있다.",
            "거미의 배 부분이 느리게 수축하고 있다.",
        ],
        ("medium", "medium"): [
            "거미의 다리가 빠르게 움직이며 바닥을 긁고 있다.",
            "거미에게서 끈적한 액체가 스며 나오고 있다.",
        ],
        ("high", "low"): [
            "거미의 몸 전체가 경련하듯 떨리고 있다.",
            "거미의 다리가 불규칙하게 꿈틀거리고 있다.",
        ],
        ("high", "medium"): [
            "거미가 격하게 몸을 떨며 다리를 허우적대고 있다.",
            "거미의 배에서 거미줄이 분비되기 시작했다.",
        ],
        ("high", "high"): [
            "거미의 온몸이 경직되며 다리가 안쪽으로 말려들고 있다.",
            "거미가 격렬하게 몸을 떨며 끈적한 액체를 뿜고 있다.",
        ],
        ("extreme", "low"): [
            "거미의 여덟 다리가 모두 격하게 경련하고 있다.",
            "거미의 몸에서 이상한 소리가 나고 있다.",
        ],
        ("extreme", "medium"): [
            "거미의 다리가 미친 듯이 움직이며 주변을 할퀴고 있다.",
            "거미의 배 부분이 격하게 수축과 이완을 반복하고 있다.",
        ],
        ("extreme", "high"): [
            "거미의 모든 다리가 뻣뻣하게 뻗어 있다. 한계에 가까운 것 같다.",
            "거미가 격렬하게 몸부림치며 거미줄을 사방에 뿜고 있다!",
        ],
        ("extreme", "critical"): [
            "거미의 몸이 극도로 경직되어 있다. 곧 한계에 이를 것 같다!",
            "거미의 모든 다리가 동시에 경련하고 있다!",
        ],
    },

    # ─── 박쥐 (bat) — 날카로운 울음, 날개 파닥 ───
    "bat": {
        ("medium", "low"): [
            "박쥐가 높은 소리로 끽끽거리고 있다.",
            "박쥐의 날개가 미세하게 떨리고 있다.",
        ],
        ("medium", "medium"): [
            "박쥐가 날개를 파닥이며 몸을 떨고 있다.",
            "박쥐에게서 날카로운 초음파가 울려 퍼지고 있다.",
        ],
        ("high", "low"): [
            "박쥐가 격하게 날개를 파닥이고 있다.",
            "박쥐의 작은 몸이 경련하듯 떨리고 있다.",
        ],
        ("high", "medium"): [
            "박쥐가 미친 듯이 날개를 펄럭이며 끽끽거리고 있다.",
            "박쥐의 온몸이 떨리며 날카로운 울음을 내고 있다.",
        ],
        ("high", "high"): [
            "박쥐가 격렬하게 몸을 비틀며 짧은 비명을 지르고 있다.",
            "박쥐의 날개가 뻣뻣하게 펴지며 몸이 경직되어 있다.",
        ],
        ("extreme", "critical"): [
            "박쥐의 온몸이 경련하며 날카로운 울음이 끊이지 않는다!",
            "박쥐가 마지막 힘을 다해 날개를 펄럭이고 있다!",
        ],
    },

    # ─── 기본 (알 수 없는 종) ───
    "default": {
        ("medium", "low"): [
            "생물체의 호흡이 빨라지고 있다.",
            "생물체가 몸을 꿈틀거리고 있다.",
        ],
        ("medium", "medium"): [
            "생물체가 거칠게 숨을 몰아쉬고 있다.",
            "생물체의 몸이 미세하게 떨리고 있다.",
        ],
        ("high", "low"): [
            "생물체가 격하게 몸을 떨고 있다.",
            "생물체가 거친 숨소리를 내고 있다.",
        ],
        ("high", "medium"): [
            "생물체가 격렬하게 몸부림치고 있다.",
            "생물체의 온몸이 떨리고 있다.",
        ],
        ("high", "high"): [
            "생물체가 미친 듯이 몸을 떨고 있다.",
            "생물체의 몸 전체가 경련하고 있다.",
        ],
        ("extreme", "low"): [
            "생물체가 극심하게 몸을 떨며 거친 숨을 내쉬고 있다.",
        ],
        ("extreme", "medium"): [
            "생물체가 격렬하게 몸부림치며 몸이 경련하고 있다.",
        ],
        ("extreme", "high"): [
            "생물체가 한계에 가까운 듯 온몸이 경직되어 있다.",
        ],
        ("extreme", "critical"): [
            "생물체의 몸이 극도로 긴장되어 있다!",
        ],
    },
}


# ============================================
# 즉시 행위 반응 (start — 행위 발생 시점)
# ============================================
# action_id → [텍스트, ...]

_INSTANT_REACTIONS = {
    "wolf": {
        "vaginal_insert": [
            "늑대가 낮게 으르렁거리며 몸을 비틀었다.",
            "늑대가 이빨을 드러내며 짧게 울부짖었다.",
        ],
        "anal_insert": [
            "늑대가 날카롭게 울부짖으며 몸을 뒤틀었다.",
            "늑대가 격하게 으르렁거리며 뒷다리를 버둥거렸다.",
        ],
        "thrust_gentle": [
            "늑대가 낮게 신음하며 몸을 떨었다.",
        ],
        "thrust_normal": [
            "늑대가 거칠게 헐떡이기 시작했다.",
            "늑대가 격하게 숨을 내쉬었다.",
        ],
        "thrust_rough": [
            "늑대가 길게 울부짖으며 격하게 몸을 떨었다!",
            "늑대가 미친 듯이 으르렁거리며 몸부림쳤다!",
        ],
        "genital_caress": [
            "늑대가 낮게 으르렁거리며 반응했다.",
        ],
        "breast_caress": [
            "늑대가 짧게 낑낑거렸다.",
        ],
        "withdraw": [
            "늑대가 짧게 낑낑거리며 축 늘어졌다.",
        ],
    },

    "spider": {
        "vaginal_insert": [
            "거미의 다리가 동시에 움찔하며 경련했다.",
            "거미의 배 부분이 격하게 수축했다.",
        ],
        "anal_insert": [
            "거미가 격하게 몸을 떨며 다리를 버둥거렸다.",
        ],
        "thrust_gentle": [
            "거미의 다리가 느리게 꿈틀거렸다.",
        ],
        "thrust_normal": [
            "거미의 다리가 빠르게 움직이며 바닥을 긁었다.",
            "거미의 배에서 끈적한 액체가 흘러나왔다.",
        ],
        "thrust_rough": [
            "거미의 여덟 다리가 동시에 격렬하게 경련했다!",
            "거미가 몸을 뒤틀며 거미줄을 사방에 뿜었다!",
        ],
        "genital_caress": [
            "거미의 배 부분이 수축하며 반응했다.",
        ],
        "withdraw": [
            "거미의 다리가 축 늘어졌다.",
        ],
    },

    "bat": {
        "vaginal_insert": [
            "박쥐가 날카롭게 끽끽거리며 날개를 파닥였다.",
        ],
        "anal_insert": [
            "박쥐가 짧은 비명을 지르며 몸을 움츠렸다.",
        ],
        "thrust_gentle": [
            "박쥐가 높은 소리로 끽끽거렸다.",
        ],
        "thrust_normal": [
            "박쥐가 격하게 날개를 파닥이며 몸을 떨었다.",
        ],
        "thrust_rough": [
            "박쥐가 날카로운 비명을 지르며 격렬하게 몸부림쳤다!",
        ],
        "withdraw": [
            "박쥐가 축 늘어져 날개를 접었다.",
        ],
    },

    "default": {
        "vaginal_insert": [
            "생물체가 격하게 몸을 떨었다.",
        ],
        "anal_insert": [
            "생물체가 몸을 비틀며 반응했다.",
        ],
        "thrust_gentle": [
            "생물체가 미세하게 떨렸다.",
        ],
        "thrust_normal": [
            "생물체가 격하게 몸을 떨고 있다.",
        ],
        "thrust_rough": [
            "생물체가 격렬하게 몸부림쳤다!",
        ],
        "withdraw": [
            "생물체가 축 늘어졌다.",
        ],
    },
}


# ============================================
# 절정 반응
# ============================================

_CLIMAX_REACTIONS = {
    "wolf": [
        "늑대가 길게 울부짖으며 온몸을 떨었다...!",
        "늑대가 경련하듯 몸을 뒤틀며 하울링했다...!",
    ],
    "spider": [
        "거미의 모든 다리가 동시에 뻣뻣하게 뻗으며 경직됐다...!",
        "거미가 격렬하게 경련하며 거미줄을 뿜어냈다...!",
    ],
    "bat": [
        "박쥐가 날카로운 울음을 지르며 날개를 활짝 폈다...!",
        "박쥐의 온몸이 경련하며 작은 몸이 뻣뻣해졌다...!",
    ],
    "default": [
        "생물체의 온몸이 격렬하게 경련했다...!",
    ],
}

# 절정 후 반응
_POST_CLIMAX_REACTIONS = {
    "wolf": [
        "늑대가 축 늘어져 거칠게 숨을 고르고 있다...",
        "늑대가 탈진한 듯 엎드려 헐떡이고 있다...",
    ],
    "spider": [
        "거미의 다리가 힘없이 늘어져 있다...",
        "거미가 미동도 없이 배 부분만 느리게 수축하고 있다...",
    ],
    "bat": [
        "박쥐가 축 늘어져 날개를 접고 있다...",
        "박쥐의 작은 몸이 가늘게 떨리고 있다...",
    ],
    "default": [
        "생물체가 탈진한 듯 축 늘어져 있다...",
    ],
}


# ============================================
# 공개 API
# ============================================

def get_creature_toggle_reaction(partner_id, stim_state):
    """토글 행위 중 creature 반응 (during 묘사)

    Args:
        partner_id: 생물체 유닛 ID
        stim_state: 자극 상태 dict

    Returns:
        str or None: 반응 텍스트
    """
    if not stim_state:
        return None

    arousal = stim_state.get("arousal", 0)
    gauge = stim_state.get("climax_gauge", 0)
    climax_total = stim_state.get("climax_total", 0)

    # 절정 후 저각성
    if climax_total >= 1 and arousal < 30:
        return _pick_post_climax(partner_id)

    a_tier = _arousal_tier(arousal)
    g_tier = _gauge_tier(gauge)

    if a_tier == "low" and g_tier == "low":
        return None

    species = _get_species(partner_id)
    pool = _TOGGLE_REACTIONS.get(species, _TOGGLE_REACTIONS["default"])
    texts = pool.get((a_tier, g_tier))

    # fallback: gauge 한 단계 낮춤 → arousal 한 단계 낮춤
    if not texts:
        for fallback_key in _fallback_keys(a_tier, g_tier):
            texts = pool.get(fallback_key)
            if texts:
                break

    # 최종 fallback: default 풀
    if not texts:
        default_pool = _TOGGLE_REACTIONS["default"]
        texts = default_pool.get((a_tier, g_tier))
        if not texts:
            for fallback_key in _fallback_keys(a_tier, g_tier):
                texts = default_pool.get(fallback_key)
                if texts:
                    break

    return random.choice(texts) if texts else None


def get_creature_instant_reaction(partner_id, action_id):
    """즉시 행위 발생 시 creature 반응 (start 대사)

    Args:
        partner_id: 생물체 유닛 ID
        action_id: 행위 ID ("vaginal_insert", "thrust_normal" 등)

    Returns:
        str or None: 반응 텍스트
    """
    species = _get_species(partner_id)
    pool = _INSTANT_REACTIONS.get(species, _INSTANT_REACTIONS["default"])
    texts = pool.get(action_id)
    if not texts:
        texts = _INSTANT_REACTIONS["default"].get(action_id)
    return random.choice(texts) if texts else None


def get_creature_climax_reaction(partner_id):
    """절정 시 creature 반응

    Returns:
        str or None: 반응 텍스트
    """
    species = _get_species(partner_id)
    texts = _CLIMAX_REACTIONS.get(species, _CLIMAX_REACTIONS["default"])
    return random.choice(texts) if texts else None


def _pick_post_climax(partner_id):
    """절정 후 저각성 반응"""
    species = _get_species(partner_id)
    texts = _POST_CLIMAX_REACTIONS.get(species, _POST_CLIMAX_REACTIONS["default"])
    return random.choice(texts) if texts else None


# ============================================
# Fallback 키 생성
# ============================================

_TIER_ORDER_A = ["extreme", "high", "medium", "low"]
_TIER_ORDER_G = ["critical", "high", "medium", "low"]


def _fallback_keys(a_tier, g_tier):
    """가장 가까운 fallback (arousal_tier, gauge_tier) 키 순서"""
    a_idx = _TIER_ORDER_A.index(a_tier) if a_tier in _TIER_ORDER_A else 3
    g_idx = _TIER_ORDER_G.index(g_tier) if g_tier in _TIER_ORDER_G else 3

    keys = []
    # gauge 한 단계 낮춤
    if g_idx + 1 < len(_TIER_ORDER_G):
        keys.append((a_tier, _TIER_ORDER_G[g_idx + 1]))
    # arousal 한 단계 낮춤
    if a_idx + 1 < len(_TIER_ORDER_A):
        keys.append((_TIER_ORDER_A[a_idx + 1], g_tier))
    # 둘 다 한 단계 낮춤
    if a_idx + 1 < len(_TIER_ORDER_A) and g_idx + 1 < len(_TIER_ORDER_G):
        keys.append((_TIER_ORDER_A[a_idx + 1], _TIER_ORDER_G[g_idx + 1]))
    return keys
