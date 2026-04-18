"""Hybrid Template + Slot 대화 엔진.

설계 철학:
  - Template = 작가가 쓴 완성 문장 (빈 slot만 {name} 표기)
  - Slot pool = 치환될 토큰 리스트 (옵션 feature 태깅)
  - 조립 단계 없음 → 어색한 문법 조합 원천 차단
  - 다양성은 (template 수) × (slot 조합) × anti-repetition 으로 확보

Prior 레이어 (현재 구현):
  1. Template state-bias softmax (state 근접 선호)
  2. Slot token feature softmax (feature 제공 시)
  3. Anti-repetition penalty (최근 턴 감점)

미구현 (향후):
  - Slot-slot compatibility
  - 자동 feature inference
"""
from __future__ import annotations
import math
import random
import re
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple, Union

import yaml

_SLOT_RE = re.compile(r"\{(\w+)\}")


def _state_distance(state: Dict[str, float], bias: Dict[str, float]) -> float:
    """L2 거리. bias에 명시된 축 + state에 명시된 축의 합집합에서 계산."""
    keys = set(state.keys()) | set(bias.keys())
    if not keys:
        return 0.0
    acc = 0.0
    for k in keys:
        acc += (state.get(k, 0.0) - bias.get(k, 0.0)) ** 2
    return math.sqrt(acc)


def _softmax_sample(rng: random.Random, options: List, logits: List[float],
                    temperature: float = 0.5) -> int:
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
                 history_size: int = 5,
                 repetition_penalty: float = 1.5,
                 seed: int = 0):
        """
        template_sigma/temp: state-bias 가우시안 bandwidth + softmax 온도.
        slot_sigma/temp: slot 선택에서 동일 역할 (feature 있는 슬롯만 적용).
        history_size: anti-repetition 히스토리 길이 (최근 N턴).
        repetition_penalty: logit 감점 (0 = 비활성, 1~2 권장).
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
        self.history_size = history_size
        self.repetition_penalty = repetition_penalty
        self.rng = random.Random(seed)

        # Anti-repetition 히스토리
        # template_history: [(intent, template_id), ...]
        # slot_history: [(slot_name, value), ...]
        self._template_history: Deque[Tuple[str, str]] = deque(maxlen=history_size)
        self._slot_history: Deque[Tuple[str, str]] = deque(maxlen=history_size * 3)

    # -------------------- 히스토리 --------------------
    def reset_history(self):
        self._template_history.clear()
        self._slot_history.clear()

    def _template_repetition_penalty(self, intent: str, tid: str) -> float:
        """최근 사용 횟수에 비례한 페널티. 최근일수록 가중."""
        if not self.repetition_penalty or not self._template_history:
            return 0.0
        # 최근(마지막)에서 처음 쪽으로 decay
        n = len(self._template_history)
        hits = 0.0
        for i, (h_intent, h_tid) in enumerate(self._template_history):
            if h_intent == intent and h_tid == tid:
                # 최신(index n-1)일수록 weight=1, 오래된 것은 weight→0
                recency = (i + 1) / n
                hits += recency
        return hits * self.repetition_penalty

    def _slot_repetition_penalty(self, slot_name: str, value: str) -> float:
        if not self.repetition_penalty or not self._slot_history:
            return 0.0
        n = len(self._slot_history)
        hits = 0.0
        for i, (h_name, h_val) in enumerate(self._slot_history):
            if h_name == slot_name and h_val == value:
                recency = (i + 1) / n
                hits += recency
        return hits * self.repetition_penalty

    # -------------------- state 결합 --------------------
    def _outer_effective(self, runtime_state: Optional[Dict[str, float]]) -> Dict[str, float]:
        """outer_profile + runtime state 오버레이. Template state_bias 매칭용."""
        s = dict(self.outer_profile)
        if runtime_state:
            s.update(runtime_state)
        return s

    def _inner_effective(self, runtime_state: Optional[Dict[str, float]]) -> Dict[str, float]:
        """inner_profile + runtime state 오버레이. Template inner_bias 매칭용.

        inner_profile 비어있으면 outer_profile 을 써서 표리일체 캐릭터에 자연스럽게 대응.
        runtime state(dynamic)는 outer/inner 공통으로 적용.
        """
        base = self.inner_profile if self.inner_profile else self.outer_profile
        s = dict(base)
        if runtime_state:
            s.update(runtime_state)
        return s

    # -------------------- 선택 로직 --------------------
    def _pick_template(self, templates: List[Dict], intent: str,
                       outer_state: Dict[str, float],
                       inner_state: Dict[str, float]) -> Dict:
        """Template 거리 = outer_dist + inner_dist (inner_bias 있는 경우만).

        - state_bias 만: outer 만 매칭 (표리일체 또는 외면 중시)
        - inner_bias 만: inner 만 매칭 (속마음만 중시, 드문 케이스)
        - 둘 다: 합산 (괴리 템플릿 — 외면+내면 모두 조건 맞아야 선호)
        """
        logits = []
        sigma = max(self.template_sigma, 1e-6)
        for t in templates:
            state_bias = t.get("state_bias") or {}
            inner_bias = t.get("inner_bias") or {}
            d_total = 0.0
            has_any = False
            if state_bias:
                d_total += _state_distance(outer_state, state_bias)
                has_any = True
            if inner_bias:
                d_total += _state_distance(inner_state, inner_bias)
                has_any = True
            if not has_any:
                d_total = 0.0  # bias 없으면 거리 0 (어떤 state에도 중립)
            base = -d_total / sigma
            tid = t.get("id", t.get("pattern", ""))
            penalty = self._template_repetition_penalty(intent, tid)
            logits.append(base - penalty)
        idx = _softmax_sample(self.rng, templates, logits, self.template_temp)
        return templates[idx]

    def _pick_slot_token(self, slot_name: str,
                         pool: List[Union[str, Dict]],
                         state: Dict[str, float]) -> str:
        if not pool:
            return ""
        logits = []
        texts = []
        for item in pool:
            if isinstance(item, dict):
                text = item.get("token", "")
                feat = item.get("feature", {}) or {}
                if feat:
                    d = _state_distance(state, feat)
                    base = -d / max(self.slot_sigma, 1e-6)
                else:
                    base = 0.0
            else:
                text = str(item)
                base = 0.0
            texts.append(text)
            penalty = self._slot_repetition_penalty(slot_name, text)
            logits.append(base - penalty)
        idx = _softmax_sample(self.rng, texts, logits, self.slot_temp)
        return texts[idx]

    # -------------------- 메인 --------------------
    def generate(self, intent: str, state: Optional[Dict[str, float]] = None,
                 record: bool = True) -> str:
        """generate 한 문장 반환.

        record=False 면 히스토리에 기록 안 함 (ablation / 탐색용).
        """
        intent_data = self.intents.get(intent)
        if not intent_data:
            return ""
        templates = intent_data.get("templates") or []
        slots: Dict[str, List] = intent_data.get("slots") or {}
        if not templates:
            return ""

        outer_state = self._outer_effective(state)
        inner_state = self._inner_effective(state)
        tpl = self._pick_template(templates, intent, outer_state, inner_state)
        pattern = tpl.get("pattern", "")
        tid = tpl.get("id", pattern)

        chosen_slots: List[Tuple[str, str]] = []

        def _fill(match):
            slot_name = match.group(1)
            pool = slots.get(slot_name)
            if pool is None:
                return ""
            # Slot token은 outer state 기준 (외면에 드러나는 어휘)
            value = self._pick_slot_token(slot_name, pool, outer_state)
            chosen_slots.append((slot_name, value))
            return value

        output = _SLOT_RE.sub(_fill, pattern)

        if record:
            self._template_history.append((intent, tid))
            for s in chosen_slots:
                self._slot_history.append(s)

        return output

    def set_seed(self, seed: int, reset_history: bool = False):
        self.rng = random.Random(seed)
        if reset_history:
            self.reset_history()
