"""피격 반응 시스템 — 아키타입별 기본 피격 반응 + emit 함수

우선순위:
  1. COMBAT_LINES["hit_crit" / "hit_heavy" / "hit_light"]  (캐릭터 맞춤)
  2. ARCHETYPE_HIT_REACTIONS[archetype][tier]               (아키타입 기본)
  3. COMBAT_LINES["hit"]                                    (레거시 fallback)
"""

import random

# 데미지 등급 임계값 (최대체력 대비)
_HEAVY_THRESHOLD = 0.15   # ≥15% → 중상, <15% → 경미

# ── 아키타입별 피격 반응 (10개 아키타입 × 3 등급) ──
# {name} 플레이스홀더 → 실제 캐릭터 이름으로 치환
ARCHETYPE_HIT_REACTIONS = {
    "stoic": {
        "hit_light": [
            "{name}의 눈썹이 살짝 찌푸려진다.",
            "{name}가 조용히 이를 악문다.",
        ],
        "hit_heavy": [
            "{name}가 한 발 물러서며 자세를 고쳐잡는다.",
            "{name}의 몸이 흔들린다.",
        ],
        "hit_crit": [
            "{name}가 무릎을 짚으며 버텨낸다.",
            "{name}가 고통스럽게 입술을 꽉 깨문다.",
        ],
    },
    "gentle": {
        "hit_light": [
            "{name}가 작게 신음을 흘린다.",
            "{name}의 눈이 살짝 커진다.",
        ],
        "hit_heavy": [
            "{name}가 고통스럽게 신음하며 비틀거린다.",
            "{name}의 눈에 눈물이 맺힌다.",
        ],
        "hit_crit": [
            "{name}가 고통스럽게 울부짖는다.",
            "{name}가 주저앉으려 한다.",
        ],
    },
    "cheerful": {
        "hit_light": [
            "{name}가 '아야!' 하며 찡그린다.",
            "{name}가 움찔하며 상처를 확인한다.",
        ],
        "hit_heavy": [
            "{name}가 비틀거리며 얼굴을 찡그린다.",
            "{name}가 고통을 억지로 참아낸다.",
        ],
        "hit_crit": [
            "{name}가 크게 비명을 지른다.",
            "{name}가 신음하며 무릎을 꿇는다.",
        ],
    },
    "timid": {
        "hit_light": [
            "{name}가 작게 비명을 지른다.",
            "{name}가 움츠러들며 상처를 잡는다.",
        ],
        "hit_heavy": [
            "{name}가 비명을 지르며 비틀거린다.",
            "{name}가 공포에 질린 채 뒤로 물러선다.",
        ],
        "hit_crit": [
            "{name}가 절규하며 쓰러지려 한다.",
            "{name}의 눈이 두려움으로 가득 찬다.",
        ],
    },
    "cold": {
        "hit_light": [
            "{name}의 눈빛이 순간 날카로워진다.",
            "{name}가 미동도 없이 상처를 흘끗 내려본다.",
        ],
        "hit_heavy": [
            "{name}가 조용히 숨을 들이킨다.",
            "{name}가 냉정하게 균형을 다잡는다.",
        ],
        "hit_crit": [
            "{name}가 이를 악물며 버텨낸다.",
            "{name}의 무릎이 미세하게 떨린다.",
        ],
    },
    "seductive": {
        "hit_light": [
            "{name}의 입술에서 짧은 신음이 새어나온다.",
            "{name}가 살짝 몸을 비튼다.",
        ],
        "hit_heavy": [
            "{name}가 고통스럽게 신음하며 몸을 떤다.",
            "{name}가 비틀거리며 입술을 깨문다.",
        ],
        "hit_crit": [
            "{name}가 비명을 지르며 비틀거린다.",
            "{name}가 신음하며 쓰러지려 한다.",
        ],
    },
    "fierce": {
        "hit_light": [
            "{name}가 씩 웃으며 도발적으로 적을 노려본다.",
            "{name}가 피를 뱉으며 전투 자세를 잡는다.",
        ],
        "hit_heavy": [
            "{name}가 분노에 찬 눈빛으로 적을 노려본다.",
            "{name}가 격분하며 포효한다.",
        ],
        "hit_crit": [
            "{name}가 피를 흘리며 포효한다.",
            "{name}가 격렬하게 몸부림치며 버텨낸다.",
        ],
    },
    "proud": {
        "hit_light": [
            "{name}가 불쾌한 듯 눈살을 찌푸린다.",
            "{name}의 표정이 굳는다.",
        ],
        "hit_heavy": [
            "{name}가 자존심을 세우며 비틀거림을 참아낸다.",
            "{name}가 경멸하는 눈빛으로 적을 바라본다.",
        ],
        "hit_crit": [
            "{name}가 격분하며 비틀거린다.",
            "{name}가 패배를 인정하지 않으려 버텨낸다.",
        ],
    },
    "innocent": {
        "hit_light": [
            "{name}가 멍한 표정으로 상처를 내려본다.",
            "{name}가 작게 울음을 삼킨다.",
        ],
        "hit_heavy": [
            "{name}가 눈물을 글썽이며 비틀거린다.",
            "{name}가 혼란스러운 표정으로 고통을 참는다.",
        ],
        "hit_crit": [
            "{name}가 와락 울음을 터뜨리며 쓰러지려 한다.",
            "{name}가 두 손으로 상처를 감싼다.",
        ],
    },
    "devoted": {
        "hit_light": [
            "{name}가 묵묵히 고통을 삼킨다.",
            "{name}가 상처를 무시하고 전방을 주시한다.",
        ],
        "hit_heavy": [
            "{name}가 고통을 억누르며 버텨낸다.",
            "{name}가 비틀거리면서도 자리를 지킨다.",
        ],
        "hit_crit": [
            "{name}가 쓰러질 것 같으면서도 끝내 버텨낸다.",
            "{name}가 마지막 힘을 쥐어짜낸다.",
        ],
    },
}


def get_hit_tier(damage: int, max_hp: int, is_crit: bool) -> str:
    """피해 등급 판정 → "hit_crit" / "hit_heavy" / "hit_light" """
    if is_crit:
        return "hit_crit"
    if max_hp > 0 and damage / max_hp >= _HEAVY_THRESHOLD:
        return "hit_heavy"
    return "hit_light"


def emit_hit_reaction(target_id: int, damage: int, max_hp: int, is_crit: bool):
    """피격 반응 출력

    우선순위:
      1. COMBAT_LINES["hit_crit"/"hit_heavy"/"hit_light"]  (캐릭터 맞춤)
      2. ARCHETYPE_HIT_REACTIONS[archetype][tier]           (아키타입 기본)
      3. COMBAT_LINES["hit"]                                (레거시 fallback)
    """
    import morld
    from assets.characters import get_instance

    tier = get_hit_tier(damage, max_hp, is_crit)
    char = get_instance(target_id)
    target_info = morld.get_unit_info(target_id)
    name = target_info.get("name", "?") if target_info else "?"

    combat_lines = getattr(char, 'COMBAT_LINES', None) if char else None

    # 1. 캐릭터 맞춤 COMBAT_LINES 체크
    if combat_lines:
        lines = combat_lines.get(tier, [])
        if lines:
            morld.add_action_log(random.choice(lines).format(name=name))
            return

    # 2. 아키타입 fallback
    #    NPC: REACTION_PROFILE["archetype"] (로맨스 시스템과 공유)
    #    Monster(HumanoidCreature): archetype 인스턴스 속성
    if char:
        profile = getattr(char, 'REACTION_PROFILE', None) or {}
        archetype = profile.get("archetype") or getattr(char, 'archetype', None)
        if archetype:
            tier_lines = ARCHETYPE_HIT_REACTIONS.get(archetype, {}).get(tier, [])
            if tier_lines:
                morld.add_action_log(random.choice(tier_lines).format(name=name))
                return

    # 3. 레거시 fallback ("hit" 키)
    if combat_lines:
        lines = combat_lines.get("hit", [])
        if lines:
            morld.add_action_log(random.choice(lines))
