# engine/think — NPC AI 프레임워크 설계

## 목적

모든 시나리오에서 NPC AI가 동작하도록 엔진 레벨에 think 시스템을 제공한다.
시나리오별 구체적 행동은 서브클래스/콜백으로 확장.

## 엔진에 넣는 것

### 1. think.py (= registry + dispatcher)

```python
# engine/think.py

_agents = {}          # unit_id → Agent
_agent_classes = {}   # unique_id → Agent class

def think_all():
    """모든 Agent의 think() 호출 (C# ThinkSystem에서 호출)"""

def register_agent(unit_id, agent): ...
def unregister_agent(unit_id): ...
def get_agent(unit_id): ...
def get_all_agents(): ...
def clear_all(): ...

def register_agent_class(unique_id):
    """데코레이터: @register_agent_class("lina")"""

def create_agent_for(unique_id, unit_id): ...

def reset():
    """챕터 전환 초기화"""
    _agents.clear()
    _agent_classes.clear()
```

S02의 `think/registry.py`를 그대로 가져오되 단일 파일로.

### 2. think_base.py (= BaseAgent 골격)

```python
# engine/think_base.py

class BaseAgent:
    def __init__(self, unit_id):
        self.unit_id = unit_id
        self._action_taken = False

    def think(self):
        """매 Step 호출 — 서브클래스 오버라이드"""
        self._action_taken = False
        self._on_think()
        if not self._action_taken:
            self._insert_idle_job("할 일 없음", 600_000)

    def _on_think(self):
        """서브클래스에서 구현"""
        pass

    # --- Job 삽입 헬퍼 ---
    def _insert_idle_job(self, name, duration_ms):
        morld.insert_job(self.unit_id, {
            "name": name,
            "action": "stay",
            "duration": duration_ms,
        })
        self._action_taken = True

    def _move_to(self, region_id, location_id):
        morld.insert_job(self.unit_id, {
            "name": f"이동",
            "action": "move",
            "target_region": region_id,
            "target_location": location_id,
            "duration": 0,
        })
        self._action_taken = True

    def _do_instant_action(self, name, duration_key=None):
        duration = self._get_action_duration(duration_key or name)
        self._insert_idle_job(name, duration)

    def _get_action_duration(self, key):
        """시나리오별 오버라이드 가능"""
        return 600_000  # 기본 10분

    def get_info(self):
        return morld.get_unit_info(self.unit_id)
```

### 시나리오 확장 패턴

```python
# scenarios/scenario02/python/think/base.py
from engine.think_base import BaseAgent as _EngineBase

class BaseAgent(_EngineBase):
    ACTION_DURATION = { "식사": 900_000, "벌목": 1_800_000, ... }

    def _on_think(self):
        # 5-tier 우선순위 판정
        if self._check_tier1(): return
        if self._check_tier3(): return
        if self._check_tier5(): return

    def _get_action_duration(self, key):
        return self.ACTION_DURATION.get(key, 600_000)
```

## S02 마이그레이션

| S02 현재 | 엔진 이동 | S02 유지 |
|----------|-----------|----------|
| think/registry.py | engine/think.py | - |
| think/base.py (핵심 골격) | engine/think_base.py | 5-tier, mixin, 핸들러 |
| think/activities/ | - | 전부 유지 |
| think/handlers/ | - | 전부 유지 |
| think/__init__.py | sys.modules 래퍼 | - |

## S04에서의 사용

S04에 NPC AI가 없더라도:
- `import think` → engine/think.py 로드 성공
- `think_all()` → `_agents` 비어있음 → 아무것도 안 함 → 에러 없음
- 향후 NPC 추가 시 `register_agent`로 등록만 하면 동작

```python
# scenarios/scenario04/python/think.py
import sys
from engine import think as _m
sys.modules[__name__] = _m
```
