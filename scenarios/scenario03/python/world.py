# world.py - 지도 및 시간 설정
# morld 모듈을 사용하여 직접 게임 시스템에 데이터 등록

import morld

WORLD_NAME = "시뮬레이션 마을"

REGIONS = [
    {
        "id": 0,
        "name": "주거지역",
        "appearance": {
            "default": "조용한 주거지역이다."
        },
        "locations": [
            {"id": 0, "name": "주민1의 집"},
            {
                "id": 1,
                "name": "마을 광장",
                "appearance": {
                    "default": "돌로 포장된 광장에 분수대가 서 있다.",
                    "아침": "이른 아침 안개가 광장을 감싸고 있다.",
                    "낮": "햇살이 분수대 물방울을 반짝이게 한다.",
                    "저녁": "노을빛이 돌바닥에 길게 드리워져 있다.",
                    "밤": "달빛 아래 분수대가 은은하게 빛난다.",
                    "봄,아침": "따스한 봄 햇살이 광장을 부드럽게 비춘다."
                }
            },
            {"id": 2, "name": "주민2의 집"},
            {
                "id": 3,
                "name": "공원",
                "appearance": {
                    "default": "푸른 잔디밭이 펼쳐진 공원이다.",
                    "봄": "벚꽃이 흩날리는 아름다운 공원이다.",
                    "여름": "나무 그늘 아래가 시원하다.",
                    "가을": "단풍잎이 바닥에 수북이 쌓여 있다.",
                    "겨울": "앙상한 나뭇가지에 눈이 소복이 쌓여 있다."
                }
            },
            {"id": 4, "name": "우물"}
        ],
        "edges": [
            {"a": 0, "b": 1, "timeAtoB": 10, "timeBtoA": 10},
            {"a": 1, "b": 2, "timeAtoB": 15, "timeBtoA": 15},
            {"a": 1, "b": 3, "timeAtoB": 5, "timeBtoA": 5},
            {"a": 3, "b": 4, "timeAtoB": 8, "timeBtoA": 8}
        ]
    },
    {
        "id": 1,
        "name": "상업지역",
        "appearance": {
            "default": "활기찬 상업지역이다.",
            "아침": "상인들이 가게를 열 준비를 하고 있다.",
            "밤": "불이 꺼진 상점들이 적막하다."
        },
        "locations": [
            {
                "id": 0,
                "name": "식당",
                "appearance": {
                    "default": "맛있는 냄새가 솔솔 풍긴다.",
                    "아침": "아침 식사를 준비하는 냄새가 난다.",
                    "낮": "점심 손님들로 북적인다.",
                    "저녁": "저녁 식사를 즐기는 사람들이 많다."
                }
            },
            {"id": 1, "name": "잡화상점"},
            {"id": 2, "name": "창고"}
        ],
        "edges": [
            {"a": 0, "b": 1, "timeAtoB": 5, "timeBtoA": 5},
            {"a": 1, "b": 2, "timeAtoB": 10, "timeBtoA": 10}
        ]
    }
]

REGION_EDGES = [
    {
        "id": 0,
        "name": "마을-상업지구 다리",
        "regionA": 0,
        "localA": 1,
        "regionB": 1,
        "localB": 0,
        "timeAtoB": 8,
        "timeBtoA": 8
    }
]

TIME_SETTINGS = {
    "year": 1,
    "month": 4,
    "day": 1,
    "hour": 6,
    "minute": 0
}


def initialize_world():
    """morld API를 사용하여 월드 데이터 등록"""
    # Region 및 Location 등록
    for region_data in REGIONS:
        region_id = region_data["id"]
        region_name = region_data["name"]
        region_appearance = region_data.get("appearance")

        # Region 추가
        morld.add_region(region_id, region_name, region_appearance)

        # Location 추가
        for loc_data in region_data["locations"]:
            loc_id = loc_data["id"]
            loc_name = loc_data["name"]
            loc_appearance = loc_data.get("appearance")
            morld.add_location(region_id, loc_id, loc_name, loc_appearance)

        # Edge 추가
        for edge_data in region_data.get("edges", []):
            from_id = edge_data["a"]
            to_id = edge_data["b"]
            time_a_to_b = edge_data.get("timeAtoB", 5)
            # 양방향 동일 시간이면 간단하게, 아니면 별도 처리 필요
            morld.add_edge(region_id, from_id, to_id, time_a_to_b)

    # Region 간 연결 추가
    for re_data in REGION_EDGES:
        morld.add_region_edge(
            re_data["regionA"], re_data["localA"],
            re_data["regionB"], re_data["localB"],
            re_data.get("timeAtoB", 30),
            re_data.get("timeBtoA", 30)
        )

    print("[world.py] World data initialized via morld API")


def initialize_time():
    """morld API를 사용하여 시간 설정"""
    t = TIME_SETTINGS
    morld.set_time(t["year"], t["month"], t["day"], t["hour"], t.get("minute", 0))
    print(f"[world.py] Time set to {t['year']}/{t['month']}/{t['day']} {t['hour']}:{t.get('minute', 0):02d}")
