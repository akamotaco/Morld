# scenario02 Python 패키지 - 인스턴스 기반 Asset 구조
#
# 폴더 구조:
# - assets/: Asset 클래스 정의 (locations, objects, characters, items)
# - world/: 지형 + 인스턴스화
# - events/: 이벤트 핸들러
# - think/: NPC Agent 시스템
# - chapters/: 챕터별 초기화 모듈
# - quest/: 퀘스트 시스템

# 대화 정책: S02 = 고정 대사 전용 (infra-unification §2-5)
# hybrid 폴백(톤 접두사 위임 / _generate_dialogue catch-all / initiative 폴백)을
# 전면 차단한다. 차단으로 노출되는 갭: docs/dialogue-fallback-coverage.md
from engine import dialogue_policy as _dialogue_policy
_dialogue_policy.set_policy(_dialogue_policy.POLICY_FIXED)

import events
import survival  # 시간 경과 이벤트 구독
import temperature  # 온도 시스템 (시간 경과 이벤트 구독)
import pollution  # 오염도 시스템 (시간 경과 이벤트 구독)
import humidity  # 습도 시스템 (시간 경과 이벤트 구독)
import sound  # 소리 전파 시스템
import congestion  # 혼잡도 시스템 (시간 경과 이벤트 구독)

from assets.characters import get_character_event_handler
from chapters import load_chapter

# 전역 함수로 노출 (C#에서 호출)
from quest import show_quest_ui, initialize_quest_system


def initialize_scenario():
    """시나리오 데이터 초기화 - C#에서 호출 (챕터 0 시작)"""
    print("[scenario02] Initializing scenario data via chapter system...")

    # 챕터 0 (프롤로그) 로드
    load_chapter("chapter_0")

    # 퀘스트 시스템 초기화 (퀘스트 등록)
    initialize_quest_system()

    print("[scenario02] Scenario data initialization complete!")


def start_chapter1():
    """챕터 1 전환 (Python에서 호출 가능)"""
    load_chapter("chapter_1")
    print("[scenario02] Chapter 1 started!")
