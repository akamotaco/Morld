# quest/__init__.py - 퀘스트 정의 (시나리오03 데모)
#
# 데모용 퀘스트 2개:
# - demo_explore_platform: 플랫폼 탐색 (Step 3)
# - demo_first_expedition: 첫 탐사 임무 (Step 7~13)
#
# 시나리오02의 quest 시스템을 공유합니다.
# TODO: quest_manager 연동 시 실제 등록 로직 추가

# 퀘스트 정의 (데이터만 — quest_manager 등록은 별도)
DEMO_QUESTS = {
    "demo_explore_platform": {
        "unique_id": "demo_explore_platform",
        "name": "플랫폼 탐색",
        "description": "플랫폼의 주요 시설을 확인하라. 승강장, 중앙 통로, 통신실을 둘러보자.",
        "category": "main",
        "conditions": [
            # 3개 Location 방문
            {"type": "visit", "region_id": 0, "location_id": 0},  # 승강장
            {"type": "visit", "region_id": 0, "location_id": 1},  # 중앙 통로
            {"type": "visit", "region_id": 0, "location_id": 2},  # 통신실
        ],
        "rewards": [],
        "giver": "secretary",
        "reporter": "secretary",
    },
    "demo_first_expedition": {
        "unique_id": "demo_first_expedition",
        "name": "첫 탐사: 보수 자재 수집",
        "description": "인근 구역에서 금속 파이프 5개, 콘크리트 블록 3개를 수집하라.",
        "category": "main",
        "conditions": [
            # TODO: "source": "squad" — 분대원 인벤토리 합산 (시나리오02 확장 필요)
            {"type": "collect", "item": "metal_pipe", "count": 5, "source": "squad"},
            {"type": "collect", "item": "concrete_block", "count": 3, "source": "squad"},
        ],
        "rewards": [
            {"type": "reputation", "amount": 10},
        ],
        "giver": "secretary",
        "reporter": "secretary",
    },
}

# 건축 레시피 정의 (데모용)
BUILD_RECIPES = {
    "barracks": {
        "name": "임시 막사",
        "materials": [("plank", 5), ("concrete_block", 3)],
        "progress_per_input": 10,  # 10%씩 진행
        "result_length": 60,       # 완성 시 Location 길이
        "description": "4인용 침실. 간이 침대와 사물함.",
    },
    "storage_room": {
        "name": "보관소",
        "materials": [("metal_pipe", 3), ("plank", 3)],
        "progress_per_input": 10,
        "result_length": 50,
        "description": "자재/장비 보관 공간.",
    },
    "med_bay": {
        "name": "의료실",
        "materials": [("metal_pipe", 2), ("wire", 3), ("plank", 2)],
        "progress_per_input": 10,
        "result_length": 40,
        "description": "치료 및 약물 관리.",
    },
    "armory": {
        "name": "무기고",
        "materials": [("metal_pipe", 5), ("concrete_block", 2)],
        "progress_per_input": 10,
        "result_length": 50,
        "description": "장비 보관 및 정비.",
    },
}
