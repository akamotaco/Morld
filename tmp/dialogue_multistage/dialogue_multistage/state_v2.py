"""
Phase 2 - NPCState v2
=======================
15축 상태 벡터. 캐릭터 고유 trait + interaction term 을 평가.

주요 변경:
- 6축 → 15축
- 관계·욕망 축 추가
- interaction rules 를 캐릭터별로 선언해 비선형 변조
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import numpy as np

from game_config import (
    AXES, AXIS_NAMES, AXIS_INDEX, N_DIM,
    to_vector, from_vector, zero_vector,
)


# ------------------------------------------------------------------
# Interaction Rule
# ------------------------------------------------------------------

@dataclass
class Interaction:
    """
    조건부 축 변조 규칙.

    conditions: 각 (axis_name, op, threshold) 들이 모두 만족될 때 활성화
                op in {"min", "max"}:
                    min -> state[axis] >= threshold
                    max -> state[axis] <= threshold
    boost: 활성화 시 state에 추가될 델타 (같은 축이든 다른 축이든)
    """
    name: str
    conditions: List[Dict[str, Any]]
    boost: Dict[str, float]

    def activated(self, state_vec: np.ndarray) -> bool:
        for cond in self.conditions:
            axis = cond.get("axis")
            if axis not in AXIS_INDEX:
                return False
            v = float(state_vec[AXIS_INDEX[axis]])
            if "min" in cond and v < cond["min"]:
                return False
            if "max" in cond and v > cond["max"]:
                return False
        return True

    def apply(self, state_vec: np.ndarray) -> np.ndarray:
        """활성화된 경우 boost 를 더해 새 벡터 반환."""
        out = state_vec.copy()
        for axis, delta in self.boost.items():
            if axis in AXIS_INDEX:
                i = AXIS_INDEX[axis]
                out[i] = np.clip(out[i] + float(delta), -1.0, 1.0)
        return out


# ------------------------------------------------------------------
# NPCState v2
# ------------------------------------------------------------------

@dataclass
class NPCStateV2:
    """
    캐릭터 한 명의 상태. 3개 부분으로 구성:
      - default_trait: 변하지 않는 성격 (yaml 에 선언)
      - dynamic overrides: 런타임에 덮어쓰는 값들 (fatigue, affinity 등)
      - interactions: 상태에 따라 추가로 boost 되는 규칙들
    """
    name: str
    archetype: str
    era: str = "modern"
    sex: str = "F"
    default_trait: Dict[str, float] = field(default_factory=dict)
    dynamic: Dict[str, float] = field(default_factory=dict)
    interactions: List[Interaction] = field(default_factory=list)

    # --- sparse → dense ---
    def base_vector(self) -> np.ndarray:
        """trait + dynamic (interaction 전). trait이 dynamic 위를 덮어쓰지 않고 합쳐짐."""
        v = zero_vector()
        for axis, val in self.default_trait.items():
            if axis in AXIS_INDEX:
                v[AXIS_INDEX[axis]] = float(val)
        for axis, val in self.dynamic.items():
            if axis in AXIS_INDEX:
                v[AXIS_INDEX[axis]] = float(val)  # dynamic 이 trait 을 덮어씀
        return np.clip(v, -1.0, 1.0)

    def effective_vector(self) -> np.ndarray:
        """interaction 규칙을 모두 적용한 최종 상태 벡터."""
        v = self.base_vector()
        for rule in self.interactions:
            if rule.activated(v):
                v = rule.apply(v)
        return np.clip(v, -1.0, 1.0)

    # --- 상태 override helper ---
    def with_state(self, **overrides: float) -> "NPCStateV2":
        """일부 축을 덮어쓴 새 state. dict 복사본으로."""
        new_dynamic = dict(self.dynamic)
        for k, v in overrides.items():
            if k in AXIS_INDEX:
                new_dynamic[k] = v
        return NPCStateV2(
            name=self.name, archetype=self.archetype,
            era=self.era, sex=self.sex,
            default_trait=dict(self.default_trait),
            dynamic=new_dynamic,
            interactions=list(self.interactions),
        )


# ------------------------------------------------------------------
# YAML → Character 로더
# ------------------------------------------------------------------

def load_character(yaml_path: str) -> tuple[NPCStateV2, list]:
    """
    yaml 파일에서 캐릭터 + 예시 대사 리스트를 로드.
    Returns (NPCState, samples) where samples = [{text, intent, state}, ...]
    """
    import yaml
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    inter = [Interaction(
        name=i.get("name", ""),
        conditions=i.get("conditions", []),
        boost=i.get("boost", {}),
    ) for i in (data.get("interactions") or [])]

    npc = NPCStateV2(
        name=data["character"],
        archetype=data["archetype"],
        era=data.get("era", "modern"),
        sex=data.get("sex", "F"),
        default_trait=data.get("default_trait", {}),
        interactions=inter,
    )
    samples = data.get("samples", [])
    return npc, samples


if __name__ == "__main__":
    # 시호 로딩 테스트
    shiho, samples = load_character(
        "/home/claude/dialogue_study/phase2/examples/01_shiho.yaml"
    )
    print(f"캐릭터: {shiho.name} ({shiho.archetype})")
    print(f"기본 벡터: {shiho.base_vector().round(2)}")

    # 츤 모드 발동 확인
    stsun = shiho.with_state(embarrassment=0.8, affinity=0.7)
    print(f"\n[츤 모드: embarrassment=0.8, affinity=0.7]")
    print(f"  base:      {stsun.base_vector().round(2)}")
    print(f"  effective: {stsun.effective_vector().round(2)}")
    # aggression 이 0.3 → 0.9 로 증가해야 함

    # 호감 순간 솔직 모드
    ssweet = shiho.with_state(affinity=0.8, embarrassment=0.1)
    print(f"\n[호감 솔직: affinity=0.8, embarrassment=0.1]")
    print(f"  base:      {ssweet.base_vector().round(2)}")
    print(f"  effective: {ssweet.effective_vector().round(2)}")
    # warmth 가 -0.1 → 0.4 로 증가해야 함

    print(f"\n샘플 수: {len(samples)}")
    print(f"첫 샘플: {samples[0]}")
