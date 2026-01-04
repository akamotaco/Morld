# entities/world/mansion.py - 미스터리 저택 Region 정의

from entities.world.base import BaseRegion, Location, Edge


class MysteryMansion(BaseRegion):
    """미스터리 저택 - 방 탈출 시나리오"""

    ID = 0
    NAME = "저택"
    CURRENT_WEATHER = "흐림"

    APPEARANCE = {
        "default": "으스스한 분위기의 오래된 저택이다."
    }

    # === 장소 목록 ===
    LOCATIONS = [
        Location(0, "지하실", is_indoor=True, appearance={
            "default": "어둡고 습한 지하실이다. 먼지 냄새가 코를 찌른다.",
            "불켜짐": "희미한 전등불이 지하실을 비추고 있다."
        }),
        Location(1, "창고", is_indoor=True, appearance={
            "default": "오래된 물건들이 여기저기 쌓여 있는 창고다. 거미줄이 가득하다."
        }),
        Location(2, "거실", is_indoor=True, appearance={
            "default": "낡은 소파와 먼지 쌓인 벽난로가 있다. 한때 화려했을 흔적이 보인다."
        }),
        Location(3, "주방", is_indoor=True, appearance={
            "default": "먼지 쌓인 주방이다. 녹슨 조리도구들이 선반에 놓여 있다."
        }),
        Location(4, "복도 1층", is_indoor=True, appearance={
            "default": "긴 복도가 여러 방으로 연결되어 있다. 바닥이 삐걱거린다."
        }),
        Location(5, "계단", is_indoor=True, appearance={
            "default": "2층으로 올라가는 나무 계단이다. 일부 계단이 부서져 있다."
        }),
        Location(6, "침실", is_indoor=True, appearance={
            "default": "먼지 덮인 침대와 낡은 화장대가 있다. 커튼이 찢어져 있다."
        }),
        Location(7, "서재", is_indoor=True, appearance={
            "default": "책장에 오래된 책들이 가득하다. 책상 위에 촛대가 놓여 있다."
        }),
        Location(8, "복도 2층", is_indoor=True, appearance={
            "default": "2층 복도다. 벽에 낡은 그림들이 걸려 있다."
        }),
        Location(9, "정문 홀", is_indoor=True, appearance={
            "default": "저택의 정문이 있는 넓은 홀이다. 탈출구가 바로 눈앞에 있다!"
        }),
    ]

    # === 장소 간 연결 (조건부 포함) ===
    EDGES = [
        # 지하실-창고 (배전함 스위치 필요)
        Edge(0, 1, travel_time=1,
             conditions_a_to_b={"power": 1},  # A→B (지하실→창고)
             conditions_b_to_a={}),            # B→A (창고→지하실) - 무조건

        # 일반 연결
        Edge(1, 4, travel_time=1),  # 창고-복도1층
        Edge(2, 4, travel_time=1),  # 거실-복도1층
        Edge(3, 4, travel_time=1),  # 주방-복도1층
        Edge(4, 5, travel_time=1),  # 복도1층-계단
        Edge(5, 8, travel_time=1),  # 계단-복도2층
        Edge(6, 8, travel_time=1),  # 침실-복도2층

        # 서재-복도2층 (비밀번호로 잠금 해제 필요)
        Edge(7, 8, travel_time=1,
             conditions_a_to_b={},                  # A→B (서재→복도2층) - 무조건
             conditions_b_to_a={"study_unlocked": 1}),  # B→A (복도2층→서재) - 잠금

        # 복도2층-정문홀 (황금열쇠 필요)
        Edge(8, 9, travel_time=1,
             conditions_a_to_b={"황금열쇠": 1},  # A→B (복도2층→정문홀)
             conditions_b_to_a={}),               # B→A (정문홀→복도2층) - 무조건
    ]

    # 날씨 패턴 (방 탈출이므로 비활성화)
    WEATHER_PATTERNS = []
