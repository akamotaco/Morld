# scenario04 Python 패키지 - 마을과 던전
#
# 폴더 구조:
# - assets/: Asset 클래스 정의 (locations, objects, characters, items)
# - chapters/: 챕터별 초기화 모듈
# - (향후) think/: NPC Agent 시스템
# - (향후) minigame/: 미니게임 모듈 (전투, 낚시 등)

import events
import survival
import temperature
import pollution  # S04에서는 던전 오염으로 재해석
import humidity

from chapters import load_chapter


def initialize_scenario():
    """시나리오 데이터 초기화 - C#에서 호출"""
    print("[scenario04] Initializing scenario data via chapter system...")

    # 챕터 0 (마을 시작)
    load_chapter("chapter_0")

    print("[scenario04] Scenario data initialization complete!")
