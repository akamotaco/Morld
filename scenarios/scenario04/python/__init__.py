# scenario04 Python 패키지 - 마을과 던전
#
# 폴더 구조:
# - assets/: Asset 클래스 정의 (locations, objects, characters, items)
# - chapters/: 챕터별 초기화 모듈
# - (향후) think/: NPC Agent 시스템
# - (향후) minigame/: 미니게임 모듈 (전투, 낚시 등)

# morld API 호환 레이어 (누락 API 설치, 반드시 최초 import)
import morld_compat

# 에셋 로드 (데코레이터 등록 → 반드시 chapters 전에)
import assets.characters
import assets.items

import events
import survival
import temperature
import pollution  # S04에서는 던전 오염으로 재해석
import humidity

from chapters import load_chapter
from events import on_single_event, collect_event_handlers  # C#에서 Eval로 직접 호출


def initialize_scenario():
    """시나리오 데이터 초기화 - C#에서 호출"""
    print("[scenario04] Initializing scenario data via chapter system...")

    # 챕터 0 (마을 시작)
    load_chapter("chapter_0")

    print("[scenario04] Scenario data initialization complete!")
