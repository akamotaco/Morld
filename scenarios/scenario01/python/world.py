# world.py - 시나리오01 월드 초기화
# entities 모듈을 통한 자동 로딩 대신 직접 등록 방식 사용

import morld


def initialize_world():
    """월드 데이터 초기화 - 저택 Region"""

    # === Region 등록 ===
    morld.add_region(
        0,                # region_id
        "저택",           # name
        {"default": "으스스한 분위기의 오래된 저택이다."},  # appearance
        "흐림"            # weather
    )

    # === Location 등록 ===
    locations = [
        (0, "지하실", {
            "default": "어둡고 습한 지하실이다. 먼지 냄새가 코를 찌른다.",
            "불켜짐": "희미한 전등불이 지하실을 비추고 있다."
        }),
        (1, "창고", {
            "default": "오래된 물건들이 여기저기 쌓여 있는 창고다. 거미줄이 가득하다."
        }),
        (2, "거실", {
            "default": "낡은 소파와 먼지 쌓인 벽난로가 있다. 한때 화려했을 흔적이 보인다."
        }),
        (3, "주방", {
            "default": "먼지 쌓인 주방이다. 녹슨 조리도구들이 선반에 놓여 있다."
        }),
        (4, "복도 1층", {
            "default": "긴 복도가 여러 방으로 연결되어 있다. 바닥이 삐걱거린다."
        }),
        (5, "계단", {
            "default": "2층으로 올라가는 나무 계단이다. 일부 계단이 부서져 있다."
        }),
        (6, "침실", {
            "default": "먼지 덮인 침대와 낡은 화장대가 있다. 커튼이 찢어져 있다."
        }),
        (7, "서재", {
            "default": "책장에 오래된 책들이 가득하다. 책상 위에 촛대가 놓여 있다."
        }),
        (8, "복도 2층", {
            "default": "2층 복도다. 벽에 낡은 그림들이 걸려 있다."
        }),
        (9, "정문 홀", {
            "default": "저택의 정문이 있는 넓은 홀이다. 탈출구가 바로 눈앞에 있다!"
        }),
    ]

    for loc_id, name, appearance in locations:
        morld.add_location(
            0,           # region_id
            loc_id,      # local_id
            name,        # name
            appearance,  # appearance
            0,           # stay_duration
            True         # is_indoor
        )

    # === Edge 등록 (조건부 포함) ===

    # 지하실-창고 (배전함 스위치 필요)
    morld.add_edge_with_conditions(
        0, 0, 1,      # region_id, from_id, to_id
        1, 1,          # time_a_to_b, time_b_to_a
        {"power": 1},  # conditions_a_to_b (지하실→창고)
        {}             # conditions_b_to_a (창고→지하실) - 무조건
    )

    # 일반 연결
    morld.add_edge(0, 1, 4, 1)  # 창고-복도1층
    morld.add_edge(0, 2, 4, 1)  # 거실-복도1층
    morld.add_edge(0, 3, 4, 1)  # 주방-복도1층
    morld.add_edge(0, 4, 5, 1)  # 복도1층-계단
    morld.add_edge(0, 5, 8, 1)  # 계단-복도2층
    morld.add_edge(0, 6, 8, 1)  # 침실-복도2층

    # 서재-복도2층 (비밀번호로 잠금 해제 필요)
    morld.add_edge_with_conditions(
        0, 7, 8,              # region_id, from_id, to_id
        1, 1,                  # time_a_to_b, time_b_to_a
        {},                    # conditions_a_to_b (서재→복도2층) - 무조건
        {"study_unlocked": 1}  # conditions_b_to_a (복도2층→서재) - 잠금
    )

    # 복도2층-정문홀 (황금열쇠 필요)
    morld.add_edge_with_conditions(
        0, 8, 9,             # region_id, from_id, to_id
        1, 1,                 # time_a_to_b, time_b_to_a
        {"황금열쇠": 1},      # conditions_a_to_b (복도2층→정문홀)
        {}                    # conditions_b_to_a (정문홀→복도2층) - 무조건
    )

    print("[world] Initialized: 저택 (10 locations)")


def initialize_time():
    """게임 시간 초기화"""
    # 방 탈출은 시간이 중요하지 않으므로 임의의 시간 설정
    morld.set_time(1842, 10, 31, 18, 0)  # 저택이 지어진 해, 18시
    print("[world] Time set to 1842-10-31 18:00")
