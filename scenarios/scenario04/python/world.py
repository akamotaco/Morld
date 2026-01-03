# world.py - 지도 및 시간 설정

import morld

WORLD_NAME = "숲속 저택"

REGIONS = [
    # Region 0: 저택
    {
        "id": 0,
        "name": "저택",
        "appearance": {
            "default": "오래되었지만 잘 관리된 저택이다."
        },
        "locations": [
            {
                "id": 0,
                "name": "현관",
                "appearance": {
                    "default": "저택의 입구. 무거운 나무 문이 달려 있다.",
                    "아침": "아침 햇살이 문틈으로 스며든다.",
                    "밤": "어둠 속에 문의 윤곽만 희미하게 보인다."
                }
            },
            {
                "id": 1,
                "name": "거실",
                "appearance": {
                    "default": "넓은 거실. 벽난로와 낡은 소파가 놓여 있다. 이곳에서 매일 아침 조회가 열린다.",
                    "아침": "창문으로 들어오는 햇살이 먼지 입자를 비춘다.",
                    "저녁": "벽난로에 불이 피워져 따뜻한 분위기다.",
                    "밤": "벽난로의 불씨가 은은하게 타오른다."
                }
            },
            {
                "id": 2,
                "name": "주방",
                "appearance": {
                    "default": "각종 조리도구가 걸려 있는 주방. 아궁이에서 연기가 피어오른다.",
                    "아침": "아침 식사를 준비하는 냄새가 난다.",
                    "낮": "점심 준비로 분주하다.",
                    "저녁": "저녁 식사 준비로 맛있는 냄새가 가득하다."
                }
            },
            {
                "id": 3,
                "name": "식당",
                "appearance": {
                    "default": "긴 나무 테이블이 놓인 식당. 여섯 개의 의자가 가지런히 놓여 있다.",
                    "아침": "아침 식사 시간. 테이블에 음식이 차려져 있다.",
                    "낮": "점심 시간. 따뜻한 음식 냄새가 풍긴다.",
                    "저녁": "저녁 식사 시간. 촛불이 테이블을 밝힌다."
                }
            },
            {
                "id": 4,
                "name": "욕실",
                "appearance": {
                    "default": "낡지만 깨끗하게 관리된 욕실. 큰 나무 욕조가 놓여 있다."
                }
            },
            {
                "id": 5,
                "name": "창고",
                "appearance": {
                    "default": "선반에 식량과 도구가 정리되어 있다. 약간 먼지 냄새가 난다."
                }
            },
            {
                "id": 6,
                "name": "주인공 방",
                "appearance": {
                    "default": "작지만 아늑한 방. 침대와 작은 책상이 놓여 있다.",
                    "아침": "창문으로 아침 햇살이 들어온다.",
                    "밤": "촛불 하나가 방을 희미하게 밝힌다."
                }
            },
            {
                "id": 7,
                "name": "리나의 방",
                "appearance": {
                    "default": "밝고 활기찬 분위기의 방. 창가에 작은 화분이 놓여 있다."
                }
            },
            {
                "id": 8,
                "name": "세라의 방",
                "appearance": {
                    "default": "검소하고 정돈된 방. 벽에 활과 화살통이 걸려 있다."
                }
            },
            {
                "id": 9,
                "name": "밀라의 방",
                "appearance": {
                    "default": "따뜻한 느낌의 방. 손수 만든 쿠션과 담요가 곳곳에 있다."
                }
            },
            {
                "id": 10,
                "name": "유키의 방",
                "appearance": {
                    "default": "조용하고 깔끔한 방. 책이 가지런히 정리되어 있다."
                }
            },
            {
                "id": 11,
                "name": "엘라의 방",
                "appearance": {
                    "default": "단정하고 권위있는 분위기의 방. 책상 위에 서류가 놓여 있다."
                }
            },
            {
                "id": 12,
                "name": "앞마당",
                "appearance": {
                    "default": "저택 앞에 펼쳐진 넓은 마당. 잘 가꿔진 정원이 있다.",
                    "아침": "아침 이슬이 풀잎에 맺혀 반짝인다.",
                    "낮": "햇살이 정원을 환하게 비춘다.",
                    "저녁": "석양빛이 정원을 황금빛으로 물들인다.",
                    "밤": "달빛 아래 정원이 고요하다."
                }
            },
            {
                "id": 13,
                "name": "뒷마당",
                "appearance": {
                    "default": "저택 뒤편의 넓은 공터. 텃밭을 가꿀 수 있을 것 같다.",
                    "아침": "아침 안개가 뒷마당을 감싸고 있다.",
                    "낮": "햇살이 따스하게 내리쬔다.",
                    "저녁": "저녁 노을이 아름답다.",
                    "밤": "고요한 밤. 풀벌레 소리가 들린다."
                }
            }
        ],
        "edges": [
            # 현관 - 거실
            {"a": 0, "b": 1, "timeAtoB": 1, "timeBtoA": 1},
            # 거실 - 주방
            {"a": 1, "b": 2, "timeAtoB": 1, "timeBtoA": 1},
            # 거실 - 식당
            {"a": 1, "b": 3, "timeAtoB": 1, "timeBtoA": 1},
            # 거실 - 욕실
            {"a": 1, "b": 4, "timeAtoB": 2, "timeBtoA": 2},
            # 거실 - 창고
            {"a": 1, "b": 5, "timeAtoB": 2, "timeBtoA": 2},
            # 거실 - 주인공 방
            {"a": 1, "b": 6, "timeAtoB": 1, "timeBtoA": 1},
            # 거실 - 리나 방
            {"a": 1, "b": 7, "timeAtoB": 1, "timeBtoA": 1},
            # 거실 - 세라 방
            {"a": 1, "b": 8, "timeAtoB": 1, "timeBtoA": 1},
            # 거실 - 밀라 방
            {"a": 1, "b": 9, "timeAtoB": 1, "timeBtoA": 1},
            # 거실 - 유키 방
            {"a": 1, "b": 10, "timeAtoB": 1, "timeBtoA": 1},
            # 거실 - 엘라 방
            {"a": 1, "b": 11, "timeAtoB": 1, "timeBtoA": 1},
            # 주방 - 식당
            {"a": 2, "b": 3, "timeAtoB": 1, "timeBtoA": 1},
            # 현관 - 앞마당
            {"a": 0, "b": 12, "timeAtoB": 1, "timeBtoA": 1},
            # 현관 - 뒷마당
            {"a": 0, "b": 13, "timeAtoB": 2, "timeBtoA": 2},
        ]
    },
    # Region 1: 야외
    {
        "id": 1,
        "name": "야외",
        "appearance": {
            "default": "저택을 둘러싼 깊은 숲이다.",
            "날씨:맑음": "맑은 하늘 아래 숲이 펼쳐져 있다.",
            "날씨:흐림": "흐린 하늘 아래 숲이 어둑하다.",
            "날씨:비": "비가 내리고 있다. 나뭇잎에서 빗방울이 떨어진다.",
            "날씨:눈": "눈이 소복이 쌓여 있다. 발자국 소리가 뽀드득 난다."
        },
        "locations": [
            {
                "id": 0,
                "name": "숲 입구",
                "stayDuration": 5,  # 경유지 지체: 넓은 숲 입구를 통과하는데 시간 소요
                "appearance": {
                    "default": "저택으로 이어지는 숲길. 오래된 나무들이 늘어서 있다.",
                    "아침": "아침 안개가 숲 입구를 감싸고 있다.",
                    "낮": "햇살이 나뭇잎 사이로 쏟아진다.",
                    "저녁": "석양빛이 나무 사이로 비친다.",
                    "밤": "어둠 속에 나무들의 실루엣만 보인다."
                }
            },
            {
                "id": 1,
                "name": "숲 깊은 곳",
                "appearance": {
                    "default": "울창한 나무들 사이. 낮에도 어둑하고 길을 잃기 쉽다.",
                    "낮": "나뭇잎 사이로 간간이 빛이 스며든다.",
                    "밤": "칠흑같이 어둡다. 부엉이 소리가 들린다."
                }
            },
            {
                "id": 2,
                "name": "강가",
                "appearance": {
                    "default": "맑은 물이 흐르는 작은 강. 물소리가 청량하게 들린다.",
                    "아침": "아침 햇살에 수면이 반짝인다.",
                    "낮": "햇빛에 물이 눈부시게 빛난다.",
                    "저녁": "노을빛이 수면에 비친다."
                }
            },
            {
                "id": 3,
                "name": "채집터",
                "appearance": {
                    "default": "야생 열매와 약초가 자라는 곳. 숲의 은혜를 느낄 수 있다.",
                    "봄": "새싹이 돋아나고 있다.",
                    "여름": "무성한 풀과 열매가 가득하다.",
                    "가을": "익은 열매가 주렁주렁 달려 있다.",
                    "겨울": "말라버린 풀만 남아 있다."
                }
            },
            {
                "id": 4,
                "name": "사냥터",
                "appearance": {
                    "default": "야생 동물의 흔적이 보이는 곳. 조심스럽게 움직여야 한다.",
                    "아침": "이슬 맺힌 풀 위에 동물 발자국이 보인다.",
                    "낮": "숲 속에서 동물 울음소리가 들린다.",
                    "밤": "어둠 속에서 눈빛이 반짝인다."
                }
            }
        ],
        "edges": [
            # 숲 입구 - 숲 깊은 곳
            {"a": 0, "b": 1, "timeAtoB": 15, "timeBtoA": 15},
            # 숲 입구 - 강가
            {"a": 0, "b": 2, "timeAtoB": 10, "timeBtoA": 10},
            # 숲 입구 - 채집터
            {"a": 0, "b": 3, "timeAtoB": 10, "timeBtoA": 10},
            # 숲 깊은 곳 - 사냥터
            {"a": 1, "b": 4, "timeAtoB": 10, "timeBtoA": 10},
            # 채집터 - 강가
            {"a": 3, "b": 2, "timeAtoB": 5, "timeBtoA": 5},
        ]
    }
]

# 저택 앞마당 <-> 숲 입구 연결
REGION_EDGES = [
    {
        "id": 0,
        "name": "저택-숲",
        "regionA": 0,
        "localA": 12,  # 앞마당
        "regionB": 1,
        "localB": 0,   # 숲 입구
        "timeAtoB": 3,
        "timeBtoA": 3
    }
]

TIME_SETTINGS = {
    "year": 1,
    "month": 4,  # 봄
    "day": 1,
    "hour": 14,  # 오후 2시 시작 (숲에서 방황 중)
    "minute": 0
}


def initialize_world():
    """morld API를 사용하여 월드 데이터 등록"""
    for region_data in REGIONS:
        region_id = region_data["id"]
        region_name = region_data["name"]
        region_appearance = region_data.get("appearance")

        morld.add_region(region_id, region_name, region_appearance)

        for loc_data in region_data["locations"]:
            loc_id = loc_data["id"]
            loc_name = loc_data["name"]
            loc_appearance = loc_data.get("appearance")
            loc_stay_duration = loc_data.get("stayDuration", 0)
            morld.add_location(region_id, loc_id, loc_name, loc_appearance, loc_stay_duration)

        for edge_data in region_data.get("edges", []):
            from_id = edge_data["a"]
            to_id = edge_data["b"]
            time_a_to_b = edge_data.get("timeAtoB", 5)
            morld.add_edge(region_id, from_id, to_id, time_a_to_b)

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
