"""
Phase 2 - Game Configuration
==============================
15축 상태 스키마. 게임 내에서는 고정, 다른 게임으로 이식 시 교체.

엔진은 축 이름을 모르고 차원 수만 다룬다. 이 파일이 유일한 "어떤 축이
있는가" 의 출처(single source of truth).
"""

from typing import Dict, List
import numpy as np


# 축 그룹. 순서가 state vector 의 dimension 순서가 된다.
AXES: Dict[str, List[str]] = {
    # --- TRAIT: 캐릭터 고정 성격 ---
    "trait": [
        "formality",     # 공손(+) ↔ 거침(-)
        "warmth",        # 친밀(+) ↔ 냉정(-)
        "aggression",    # 공격(+) ↔ 온화(-)
        "verbosity",     # 수다(+) ↔ 간결(-)
        "maturity",      # 성숙(+) ↔ 유치(-)
    ],
    # --- DYNAMIC: 실시간 신체·각성 상태 ---
    "dynamic": [
        "fatigue",       # 탈진(+) ↔ 쌩쌩(-)
        "arousal",       # 흥분(+) ↔ 차분(-)
        "confidence",    # 확신(+) ↔ 주저(-)
    ],
    # --- RELATION: 상대(플레이어)와의 관계 ---
    "relation": [
        "affinity",      # 호감(+)
        "hostility",     # 반발(+)
        "trust",         # 신뢰(+)
        "embarrassment", # 부끄러움(+) — dere 발동 핵심 축
    ],
    # --- DESIRE: 상황별 동기 ---
    "desire": [
        "money",         # 금전 욕구
        "attention",     # 관심 받고 싶음
        "safety",        # 안전 확보 욕구
    ],
}


def flat_axes() -> List[str]:
    """전체 축의 이름을 순서대로 반환."""
    out = []
    for group in AXES.values():
        out.extend(group)
    return out


AXIS_NAMES = flat_axes()
N_DIM = len(AXIS_NAMES)                        # 15
AXIS_INDEX = {name: i for i, name in enumerate(AXIS_NAMES)}


def zero_vector() -> np.ndarray:
    """상태 축의 기본값(중립)은 0. range: [-1, +1] 을 기본 가정."""
    return np.zeros(N_DIM, dtype=np.float32)


def to_vector(d: Dict[str, float]) -> np.ndarray:
    """sparse dict → dense vector. 명시되지 않은 축은 0."""
    v = zero_vector()
    for name, val in d.items():
        if name in AXIS_INDEX:
            v[AXIS_INDEX[name]] = float(val)
    return v


def from_vector(v: np.ndarray, threshold: float = 0.01) -> Dict[str, float]:
    """dense vector → sparse dict (threshold 이상만)."""
    return {name: float(v[i]) for i, name in enumerate(AXIS_NAMES)
            if abs(v[i]) > threshold}


# ------------------------------------------------------------------
# Intent 정의
# ------------------------------------------------------------------

INTENTS = [
    "greet", "farewell", "refuse_quest", "accept_quest",
    "complain", "warn", "ask_price", "thank",
]


if __name__ == "__main__":
    print(f"N_DIM = {N_DIM}")
    print(f"AXIS_NAMES = {AXIS_NAMES}")
    v = to_vector({"formality": 0.9, "embarrassment": 0.7})
    print(f"sparse → dense: {v}")
    print(f"dense → sparse: {from_vector(v)}")
