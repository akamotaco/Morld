# think/agents/ - 캐릭터별 AI Agent (캐릭터 표준 ③, infra-unification §2-4)
#
# 캐릭터 표준 포맷:
#   ① 데이터 파일 (필수): assets/characters/{이름}.py — props/스탯/선호/대사 rule
#   ② 대사 yaml (선택): dialogues/characters/{이름}.yaml — hybrid override
#   ③ AI 클래스 (선택): think/agents/{이름}_agent.py — @register_agent_class
#
# 이 패키지를 import 하는 시점(think/__init__.py 하단)에 각 모듈의
# @register_agent_class 데코레이터가 agent 레지스트리에 등록된다.

from think.agents import sera_agent  # noqa: F401
from think.agents import mila_agent  # noqa: F401
from think.agents import lina_agent  # noqa: F401
