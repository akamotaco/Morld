"""
Multi-stage - NPCState (Inner/Outer 이중 구조)
================================================
핵심:
  - inner_vector: 구조(N-gram)가 참조. 캐릭터의 "진짜 의도".
  - outer_vector: 어휘(WFC)가 참조. 표면에 드러나는 어조.
  - 표리일체면 둘은 같거나 비슷.
  - 표리 괴리 (tsundere, yandere) 면 서로 다른 축에서 반대 부호.

yaml 확장:
  inner_profile: Dict[axis, float]    # 내면 고유 bias (선택)
  outer_profile == default_trait       # 기존 trait (그대로 유지)

runtime override:
  state.dynamic  → outer_vector 에 직접 반영
  state.inner    → inner_vector 에만 반영 (선택적)
  관계 축(affinity, trust, ...) 은 둘 다 반영하되 각기 다른 해석.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import numpy as np

from game_config import AXIS_NAMES, AXIS_INDEX, N_DIM, zero_vector, to_vector


@dataclass
class Interaction:
    """conditions 가 모두 만족되면 boost 를 더함."""
    name: str
    conditions: List[Dict[str, Any]]
    boost: Dict[str, float]
    # 어느 vector 에 영향을 줄지 ("inner" / "outer" / "both")
    target: str = "outer"

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
        out = state_vec.copy()
        for axis, delta in self.boost.items():
            if axis in AXIS_INDEX:
                i = AXIS_INDEX[axis]
                out[i] = np.clip(out[i] + float(delta), -1.0, 1.0)
        return out


@dataclass
class NPCStateMS:
    """Multi-stage state. inner/outer 를 분리 보관."""
    name: str
    archetype: str
    era: str = "modern"
    sex: str = "F"

    # 표면 성격 (외면, 어휘에 반영)
    outer_profile: Dict[str, float] = field(default_factory=dict)

    # 속마음 (내면, 구조에 반영). 기본은 outer_profile 과 같음 (표리일체).
    inner_profile: Dict[str, float] = field(default_factory=dict)

    # runtime 상태 override (fatigue, affinity 등) — outer/inner 공통
    dynamic: Dict[str, float] = field(default_factory=dict)

    # inner 전용 override — inner_vector 계산에만 추가 적용
    # (per-sample 학습 태깅 및 런타임 내면 편차 표현 용도)
    inner_dynamic: Dict[str, float] = field(default_factory=dict)

    interactions: List[Interaction] = field(default_factory=list)

    def _base(self, profile: Dict[str, float],
              extra_override: Optional[Dict[str, float]] = None) -> np.ndarray:
        v = zero_vector()
        for axis, val in profile.items():
            if axis in AXIS_INDEX:
                v[AXIS_INDEX[axis]] = float(val)
        # dynamic 이 profile 위를 덮어씀
        for axis, val in self.dynamic.items():
            if axis in AXIS_INDEX:
                v[AXIS_INDEX[axis]] = float(val)
        # inner 전용 추가 override (inner_vector 호출 시에만 전달됨)
        if extra_override:
            for axis, val in extra_override.items():
                if axis in AXIS_INDEX:
                    v[AXIS_INDEX[axis]] = float(val)
        return np.clip(v, -1.0, 1.0)

    def outer_vector(self) -> np.ndarray:
        """Stage 2/3 (WFC content/function) 이 참조."""
        v = self._base(self.outer_profile)
        for r in self.interactions:
            if r.target in ("outer", "both") and r.activated(v):
                v = r.apply(v)
        return np.clip(v, -1.0, 1.0)

    def inner_vector(self) -> np.ndarray:
        """Stage 1 (N-gram structural) 이 참조."""
        # inner_profile 이 비어있으면 outer 와 동일 (표리일체)
        profile = self.inner_profile if self.inner_profile else self.outer_profile
        v = self._base(profile, extra_override=self.inner_dynamic)
        for r in self.interactions:
            if r.target in ("inner", "both") and r.activated(v):
                v = r.apply(v)
        return np.clip(v, -1.0, 1.0)

    def is_sincere(self) -> bool:
        """표리일체 여부 (inner와 outer가 실질적으로 같은가)."""
        if not self.inner_profile:
            return True
        return np.allclose(self.inner_vector(), self.outer_vector(), atol=0.15)

    def divergence(self) -> float:
        """inner-outer 괴리 정도 (0=일체, 높을수록 괴리)."""
        return float(np.linalg.norm(self.inner_vector() - self.outer_vector()))

    def with_state(self, **overrides: float) -> "NPCStateMS":
        new_dyn = dict(self.dynamic)
        for k, v in overrides.items():
            if k in AXIS_INDEX:
                new_dyn[k] = v
        return NPCStateMS(
            name=self.name, archetype=self.archetype,
            era=self.era, sex=self.sex,
            outer_profile=dict(self.outer_profile),
            inner_profile=dict(self.inner_profile),
            dynamic=new_dyn,
            inner_dynamic=dict(self.inner_dynamic),
            interactions=list(self.interactions),
        )

    def with_inner(self, **overrides: float) -> "NPCStateMS":
        """inner 전용 override. outer_vector 에는 영향 없음.

        Per-sample 학습 시 yaml 의 `inner:` 필드, 또는 런타임 내면 편차 표현.
        """
        new_inner_dyn = dict(self.inner_dynamic)
        for k, v in overrides.items():
            if k in AXIS_INDEX:
                new_inner_dyn[k] = v
        return NPCStateMS(
            name=self.name, archetype=self.archetype,
            era=self.era, sex=self.sex,
            outer_profile=dict(self.outer_profile),
            inner_profile=dict(self.inner_profile),
            dynamic=dict(self.dynamic),
            inner_dynamic=new_inner_dyn,
            interactions=list(self.interactions),
        )


def load_character_ms(yaml_path: str) -> tuple[NPCStateMS, list]:
    """yaml 에서 multi-stage 용 character + samples 로드.

    Backward-compat: default_trait 만 있으면 outer_profile 로 사용.
    """
    import yaml
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    inter = [Interaction(
        name=i.get("name", ""),
        conditions=i.get("conditions", []),
        boost=i.get("boost", {}),
        target=i.get("target", "outer"),
    ) for i in (data.get("interactions") or [])]

    outer = data.get("outer_profile") or data.get("default_trait") or {}
    inner = data.get("inner_profile") or {}

    npc = NPCStateMS(
        name=data["character"],
        archetype=data["archetype"],
        era=data.get("era", "modern"),
        sex=data.get("sex", "F"),
        outer_profile=outer,
        inner_profile=inner,
        interactions=inter,
    )
    samples = data.get("samples", [])
    return npc, samples


if __name__ == "__main__":
    # 표리일체 (현 yaml 은 inner_profile 없음)
    shiho, _ = load_character_ms(
        "/home/claude/dialogue_study/phase2/examples/01_shiho.yaml")
    print(f"시호: sincere={shiho.is_sincere()}, divergence={shiho.divergence():.2f}")
    print(f"  outer: {shiho.outer_vector().round(2)}")
    print(f"  inner: {shiho.inner_vector().round(2)}")
