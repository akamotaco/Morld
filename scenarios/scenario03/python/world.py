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
            {
                "id": 0,
                "name": "주민1의 집",
                "appearance": {
                    "default": "소박하지만 정갈한 분위기의 작은 집이다. 나무 냄새가 은은하게 풍긴다.",
                    "아침": "창문으로 아침 햇살이 비스듬히 들어온다.",
                    "낮": "햇볕이 잘 드는 따뜻한 거실이다.",
                    "저녁": "은은한 조명이 집 안을 부드럽게 밝힌다.",
                    "밤": "고요한 밤, 집 안이 아늑하다."
                }
            },
            {
                "id": 1,
                "name": "마을 광장",
                "appearance": {
                    "default": "돌로 포장된 광장에 분수대가 서 있다.",
                    "아침": "이른 아침 안개가 광장을 감싸고 있다. 분수대에서 물소리가 청아하게 울린다.",
                    "낮": "햇살이 분수대 물방울을 반짝이게 한다. 지나가는 사람들이 간간이 보인다.",
                    "저녁": "노을빛이 돌바닥에 길게 드리워져 있다. 분수대가 붉게 물든다.",
                    "밤": "달빛 아래 분수대가 은은하게 빛난다. 광장은 고요하다.",
                    "봄,아침": "따스한 봄 햇살이 광장을 부드럽게 비춘다. 어디선가 새소리가 들린다."
                }
            },
            {
                "id": 2,
                "name": "주민2의 집",
                "appearance": {
                    "default": "수수한 외관의 조용한 집이다. 창문에 두꺼운 커튼이 쳐져 있다.",
                    "아침": "커튼 사이로 희미한 빛이 새어 나온다.",
                    "낮": "집 안은 어둡고 조용하다.",
                    "저녁": "집 안에서 희미한 불빛이 보인다.",
                    "밤": "완전히 어두워진 집. 주인이 잠든 것 같다."
                }
            },
            {
                "id": 3,
                "name": "공원",
                "appearance": {
                    "default": "푸른 잔디밭이 펼쳐진 공원이다. 나무 벤치가 군데군데 놓여 있다.",
                    "아침": "아침 이슬이 잔디 위에 맺혀 반짝인다.",
                    "낮": "따사로운 햇볕 아래 잔디밭이 눈부시다.",
                    "저녁": "석양이 공원을 황금빛으로 물들인다.",
                    "밤": "달빛 아래 공원이 고요하다. 풀벌레 소리가 들린다.",
                    "봄": "벚꽃이 흩날리는 아름다운 공원이다. 꽃향기가 가득하다.",
                    "여름": "나무 그늘 아래가 시원하다. 매미 소리가 요란하다.",
                    "가을": "단풍잎이 바닥에 수북이 쌓여 있다. 바스락거리는 소리가 난다.",
                    "겨울": "앙상한 나뭇가지에 눈이 소복이 쌓여 있다. 고요하다."
                }
            },
            {
                "id": 4,
                "name": "우물",
                "appearance": {
                    "default": "오래된 돌우물이다. 두레박이 걸려 있고, 물소리가 희미하게 들린다.",
                    "아침": "아침 안개가 우물 주변을 감싸고 있다.",
                    "낮": "햇빛이 우물 속을 비추자 수면이 반짝인다.",
                    "저녁": "석양빛이 우물의 돌벽을 붉게 물들인다.",
                    "밤": "어둠 속에서 우물이 검은 구멍처럼 보인다."
                }
            }
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
                    "default": "맛있는 냄새가 솔솔 풍긴다. 나무 테이블이 정갈하게 놓여 있다.",
                    "아침": "아침 식사를 준비하는 냄새가 난다. 주방에서 부산한 소리가 들린다.",
                    "낮": "점심 손님들로 북적인다. 접시 부딪히는 소리와 웃음소리가 가득하다.",
                    "저녁": "저녁 식사를 즐기는 사람들이 많다. 은은한 조명이 분위기를 더한다.",
                    "밤": "문이 닫혀 있다. 내일을 위해 정리된 테이블이 보인다."
                }
            },
            {
                "id": 1,
                "name": "잡화상점",
                "appearance": {
                    "default": "다양한 물건이 진열대에 가득하다. 살짝 먼지 냄새가 난다.",
                    "아침": "아침 햇살이 진열대의 물건들을 비춘다. 상점 문이 막 열렸다.",
                    "낮": "손님들이 물건을 구경하고 있다. 주인이 바쁘게 움직인다.",
                    "저녁": "하루 영업을 마무리하는 분위기다. 진열대를 정리하고 있다.",
                    "밤": "상점 문이 닫혀 있다. 진열대의 물건들이 어둠 속에 잠들어 있다."
                }
            },
            {
                "id": 2,
                "name": "창고",
                "appearance": {
                    "default": "각종 물건이 쌓여 있는 어수선한 창고다. 먼지가 떠다닌다.",
                    "아침": "창문 틈으로 들어온 빛이 먼지 입자를 비춘다.",
                    "낮": "바깥 빛이 들어와 창고 내부가 희미하게 보인다.",
                    "저녁": "어둑어둑해져서 물건 구별이 어렵다.",
                    "밤": "칠흑같이 어둡다. 무언가 부스럭거리는 소리가 들린다."
                }
            }
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
