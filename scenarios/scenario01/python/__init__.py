# scenario01 Python 패키지 - 방 탈출 시나리오
#
# 폴더 구조:
# - assets/: Asset 정의 (items, objects, characters)
# - world/: 지형 + 인스턴스화 (Region별 파일)
# - events/: 이벤트 핸들러
# - scripts.py: 스크립트 함수 export

from assets import load_all_assets
from world import initialize_terrain, initialize_time, instantiate_all
import events


def initialize_scenario():
    """시나리오 데이터 초기화 - C#에서 호출"""
    print("[scenario01] Initializing escape room scenario...")

    # 1. 지형 데이터 초기화
    initialize_terrain()
    initialize_time()

    # 2. Asset 정의 로드 (정의만, 인스턴스화 X)
    load_all_assets()

    # 3. 인스턴스 생성 (캐릭터, 오브젝트, 아이템)
    instantiate_all()

    print("[scenario01] Scenario data initialization complete!")
