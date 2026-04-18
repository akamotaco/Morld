"""Hybrid Template + Slot 대화 엔진 (Phase 1 최소 구현).

설계 철학:
  - Template = 작가가 쓴 완성 문장 (빈 slot만 {name} 표기)
  - Slot pool = 치환될 토큰 리스트 (옵션 feature 태깅)
  - 조립 단계 없음 → 어색한 문법 조합 원천 차단
  - 다양성은 (template 수) × (slot 조합) 로 확보

현재 지원:
  - Template state_bias 기반 softmax 선택
  - Slot uniform 선택 (토큰 단위 feature 있으면 softmax)
  - 같은 state에서도 rng seed 변화로 다양한 출력

향후 확장 (Prior 레이어):
  - Slot-slot compatibility
  - Turn-level anti-repetition
  - 자동 feature inference
"""
from __future__ import annotations
import math
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml

_SLOT_RE = re.compile(r"\{(\w+)\}")


def _state_distance(state: Dict[str, float], bias: Dict[str, float]) -> float:
    """L2 거리. bias에 명시된 축 + state에 명시된 축의 합집합에서 계산.

    미명시 축은 0 (중립)으로 간주. 거리 0 = 완벽 일치.
    """
    keys = set(state.keys()) | set(bias.keys())
    if not keys:
        return 0.0
    acc = 0.0
    for k in keys:
        acc += (state.get(k, 0.0) - bias.get(k, 0.0)) ** 2
    return math.sqrt(acc)


def _softmax_sample(rng: random.Random, options: List, logits: List[float],
                    temperature: float = 0.5) -> int:
    """logits에 온도 적용 후 softmax 샘플링. 선택된 index 반환."""
    if not options:
        raise ValueError("empty options")
    if len(options) == 1:
        return 0
    T = max(temperature, 1e-6)
    m = max(logits)
    exps = [math.exp((x - m) / T) for x in logits]
    total = sum(exps)
    if total <= 0:
        return rng.randrange(len(options))
    probs = [e / total for e in exps]
    r = rng.random()
    acc = 0.0
    for i, p in enumerate(probs):
        acc += p
        if r <= acc:
            return i
    return len(options) - 1


class HybridEngine:
    def __init__(self, yaml_path: str,
                 template_sigma: float = 0.6,
                 template_temp: float = 0.5,
                 slot_sigma: float = 0.6,
                 slot_temp: float = 0.5,
                 seed: int = 0):
        """
        template_sigma: state-bias 가우시안 bandwidth (작을수록 state 민감)
        template_temp: template softmax 온도 (작을수록 결정적)
        slot_sigma/temp: slot 선택에서 동일 역할 (feature 있는 slot만 적용)
        """
        data = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
        self.character: str = data["character"]
        self.archetype: str = data.get("archetype", "")
        self.era: str = data.get("era", "modern")
        self.sex: str = data.get("sex", "F")
        self.outer_profile: Dict[str, float] = data.get("outer_profile", {}) or {}
        self.inner_profile: Dict[str, float] = data.get("inner_profile", {}) or {}
        self.intents: Dict[str, Dict] = data.get("intents", {}) or {}

        self.template_sigma = template_sigma
        self.template_temp = template_temp
        self.slot_sigma = slot_sigma
        self.slot_temp = slot_temp
        self.rng = random.Random(seed)

    # -------------------- state 결합 --------------------
    def _effective_state(self, runtime_state: Optional[Dict[str, float]]) -> Dict[str, float]:
        """outer_profile 위에 runtime state 오버레이. (현재 template 선택은 outer 기반)"""
        s = dict(self.outer_profile)
        if runtime_state:
            s.update(runtime_state)
        return s

    # -------------------- 선택 로직 --------------------
    def _pick_template(self, templates: List[Dict], state: Dict[str, float]) -> Dict:
        logits = []
        for t in templates:
            bias = t.get("state_bias", {}) or {}
            d = _state_distance(state, bias)
            # log(exp(-d/sigma)) = -d/sigma → logit으로 사용
            logits.append(-d / max(self.template_sigma, 1e-6))
        idx = _softmax_sample(self.rng, templates, logits, self.template_temp)
        return templates[idx]

    def _pick_slot_token(self, pool: List[Union[str, Dict]],
                        state: Dict[str, float]) -> str:
        if not pool:
            return ""
        # pool은 str 또는 {token: str, feature: {axis: val}}의 혼합
        logits = []
        texts = []
        any_feature = False
        for item in pool:
            if isinstance(item, dict):
                texts.append(item.get("token", ""))
                feat = item.get("feature", {}) or {}
                if feat:
                    any_feature = True
                    d = _state_distance(state, feat)
                    logits.append(-d / max(self.slot_sigma, 1e-6))
                else:
                    logits.append(0.0)
            else:
                texts.append(str(item))
                logits.append(0.0)
        # feature가 하나도 없으면 uniform (logits 전부 0)
        idx = _softmax_sample(self.rng, texts, logits, self.slot_temp)
        return texts[idx]

    # -------------------- 메인 --------------------
    def generate(self, intent: str, state: Optional[Dict[str, float]] = None) -> str:
        intent_data = self.intents.get(intent)
        if not intent_data:
            return ""
        templates = intent_data.get("templates") or []
        slots: Dict[str, List] = intent_data.get("slots") or {}
        if not templates:
            return ""

        eff_state = self._effective_state(state)
        tpl = self._pick_template(templates, eff_state)
        pattern = tpl.get("pattern", "")

        # slot 치환 (순서대로, 같은 slot 여러 번 나와도 각자 샘플)
        def _fill(match):
            slot_name = match.group(1)
            pool = slots.get(slot_name)
            if pool is None:
                return ""
            return self._pick_slot_token(pool, eff_state)

        return _SLOT_RE.sub(_fill, pattern)

    def set_seed(self, seed: int):
        self.rng = random.Random(seed)
