# entities/world/mansion.py - 숲속 저택 Region 정의

from entities.world.base import BaseRegion, Location, Edge


class Mansion(BaseRegion):
    """숲속 저택 - 저택과 주변 숲을 포함하는 단일 Region"""

    ID = 0
    NAME = "숲속 저택"
    CURRENT_WEATHER = "맑음"

    APPEARANCE = {
        "default": "깊은 숲 속에 자리한 저택과 그 주변이다."
    }

    # === 장소 목록 ===
    LOCATIONS = [
        # === 저택 1층 (실내) ===
        Location(0, "현관", is_indoor=True, appearance={
            "default": "저택의 입구. 무거운 나무 문이 달려 있다.",
            "아침": "아침 햇살이 문틈으로 스며든다.",
            "밤": "어둠 속에 문의 윤곽만 희미하게 보인다."
        }),
        Location(1, "거실", is_indoor=True, appearance={
            "default": "넓은 거실. 벽난로와 낡은 소파가 놓여 있다. 이곳에서 매일 아침 조회가 열린다.",
            "아침": "창문으로 들어오는 햇살이 먼지 입자를 비춘다.",
            "저녁": "벽난로에 불이 피워져 따뜻한 분위기다.",
            "밤": "벽난로의 불씨가 은은하게 타오른다."
        }),
        Location(2, "주방", is_indoor=True, appearance={
            "default": "각종 조리도구가 걸려 있는 주방. 아궁이에서 연기가 피어오른다.",
            "아침": "아침 식사를 준비하는 냄새가 난다.",
            "낮": "점심 준비로 분주하다.",
            "저녁": "저녁 식사 준비로 맛있는 냄새가 가득하다."
        }),
        Location(3, "식당", is_indoor=True, appearance={
            "default": "긴 나무 테이블이 놓인 식당. 여섯 개의 의자가 가지런히 놓여 있다.",
            "아침": "아침 식사 시간. 테이블에 음식이 차려져 있다.",
            "낮": "점심 시간. 따뜻한 음식 냄새가 풍긴다.",
            "저녁": "저녁 식사 시간. 촛불이 테이블을 밝힌다."
        }),
        Location(4, "욕실", is_indoor=True, appearance={
            "default": "낡지만 깨끗하게 관리된 욕실. 큰 나무 욕조가 놓여 있다."
        }),
        Location(5, "창고", is_indoor=True, appearance={
            "default": "선반에 식량과 도구가 정리되어 있다. 약간 먼지 냄새가 난다."
        }),
        Location(6, "주인공 방", is_indoor=True, appearance={
            "default": "작지만 아늑한 방. 침대와 작은 책상이 놓여 있다.",
            "아침": "창문으로 아침 햇살이 들어온다.",
            "밤": "촛불 하나가 방을 희미하게 밝힌다."
        }),
        Location(7, "리나의 방", is_indoor=True, appearance={
            "default": "밝고 활기찬 분위기의 방. 창가에 작은 화분이 놓여 있다."
        }),
        Location(8, "세라의 방", is_indoor=True, appearance={
            "default": "검소하고 정돈된 방. 벽에 활과 화살통이 걸려 있다."
        }),
        Location(9, "밀라의 방", is_indoor=True, appearance={
            "default": "따뜻한 느낌의 방. 손수 만든 쿠션과 담요가 곳곳에 있다."
        }),
        Location(10, "유키의 방", is_indoor=True, appearance={
            "default": "조용하고 깔끔한 방. 책이 가지런히 정리되어 있다."
        }),
        Location(11, "엘라의 방", is_indoor=True, appearance={
            "default": "단정하고 권위있는 분위기의 방. 책상 위에 서류가 놓여 있다."
        }),
        Location(14, "2층 복도", is_indoor=True, appearance={
            "default": "2층으로 올라오면 나오는 넓은 복도. 창문으로 저택 앞마당이 내려다보인다.",
            "아침": "아침 햇살이 창문을 통해 복도를 비춘다.",
            "밤": "복도 양쪽에 걸린 촛불이 희미하게 길을 밝힌다."
        }),

        # === 마당 (실외) ===
        Location(12, "앞마당", is_indoor=False, appearance={
            "default": "저택 앞에 펼쳐진 넓은 마당. 잘 가꿔진 정원이 있다.",
            "아침": "아침 이슬이 풀잎에 맺혀 반짝인다.",
            "낮": "햇살이 정원을 환하게 비춘다.",
            "저녁": "석양빛이 정원을 황금빛으로 물들인다.",
            "밤": "달빛 아래 정원이 고요하다.",
            "날씨:비": "빗줄기가 정원을 적시고 있다.",
            "날씨:눈": "눈이 정원을 하얗게 덮고 있다."
        }),
        Location(13, "뒷마당", is_indoor=False, appearance={
            "default": "저택 뒤편의 넓은 공터. 텃밭을 가꿀 수 있을 것 같다.",
            "아침": "아침 안개가 뒷마당을 감싸고 있다.",
            "낮": "햇살이 따스하게 내리쬔다.",
            "저녁": "저녁 노을이 아름답다.",
            "밤": "고요한 밤. 풀벌레 소리가 들린다.",
            "날씨:비": "빗방울이 텃밭을 적시고 있다.",
            "날씨:눈": "눈이 소복이 쌓여 있다."
        }),

        # === 야외/숲 (실외) ===
        Location(20, "숲 입구", is_indoor=False, stay_duration=5, appearance={
            "default": "저택으로 이어지는 숲길. 오래된 나무들이 늘어서 있다.",
            "아침": "아침 안개가 숲 입구를 감싸고 있다.",
            "낮": "햇살이 나뭇잎 사이로 쏟아진다.",
            "저녁": "석양빛이 나무 사이로 비친다.",
            "밤": "어둠 속에 나무들의 실루엣만 보인다.",
            "날씨:비": "빗방울이 나뭇잎을 두드린다.",
            "날씨:눈": "눈이 소복이 쌓여 발자국이 선명하다."
        }),
        Location(21, "숲 깊은 곳", is_indoor=False, appearance={
            "default": "울창한 나무들 사이. 낮에도 어둑하고 길을 잃기 쉽다.",
            "낮": "나뭇잎 사이로 간간이 빛이 스며든다.",
            "밤": "칠흑같이 어둡다. 부엉이 소리가 들린다.",
            "날씨:비": "빗물이 나뭇잎을 타고 흘러내린다.",
            "날씨:눈": "눈이 쌓여 숲이 고요하다."
        }),
        Location(22, "강가", is_indoor=False, appearance={
            "default": "맑은 물이 흐르는 작은 강. 물소리가 청량하게 들린다.",
            "아침": "아침 햇살에 수면이 반짝인다.",
            "낮": "햇빛에 물이 눈부시게 빛난다.",
            "저녁": "노을빛이 수면에 비친다.",
            "날씨:비": "빗방울이 수면에 파문을 만든다.",
            "날씨:눈": "강가에 눈이 쌓여 있다."
        }),
        Location(23, "채집터", is_indoor=False, appearance={
            "default": "야생 열매와 약초가 자라는 곳. 숲의 은혜를 느낄 수 있다.",
            "봄": "새싹이 돋아나고 있다.",
            "여름": "무성한 풀과 열매가 가득하다.",
            "가을": "익은 열매가 주렁주렁 달려 있다.",
            "겨울": "말라버린 풀만 남아 있다.",
            "날씨:비": "비에 젖은 풀잎이 반짝인다.",
            "날씨:눈": "눈 아래 겨울잠을 자는 듯하다."
        }),
        Location(24, "사냥터", is_indoor=False, appearance={
            "default": "야생 동물의 흔적이 보이는 곳. 조심스럽게 움직여야 한다.",
            "아침": "이슬 맺힌 풀 위에 동물 발자국이 보인다.",
            "낮": "숲 속에서 동물 울음소리가 들린다.",
            "밤": "어둠 속에서 눈빛이 반짝인다.",
            "날씨:비": "비 오는 날은 사냥하기 어렵다.",
            "날씨:눈": "눈 위에 선명한 발자국이 보인다."
        }),
    ]

    # === 장소 간 연결 ===
    EDGES = [
        # === 저택 1층 연결 ===
        Edge(0, 1, travel_time=1),   # 현관 - 거실
        Edge(1, 2, travel_time=1),   # 거실 - 주방
        Edge(1, 3, travel_time=1),   # 거실 - 식당
        Edge(1, 4, travel_time=2),   # 거실 - 욕실
        Edge(1, 5, travel_time=2),   # 거실 - 창고
        Edge(1, 6, travel_time=1),   # 거실 - 주인공 방 (1층)
        Edge(1, 7, travel_time=1),   # 거실 - 리나 방 (1층)
        Edge(1, 9, travel_time=1),   # 거실 - 밀라 방 (1층)
        Edge(2, 3, travel_time=1),   # 주방 - 식당

        # === 저택 2층 연결 ===
        Edge(1, 14, travel_time=1),  # 거실 - 2층 복도 (계단)
        Edge(14, 8, travel_time=1),  # 2층 복도 - 세라 방
        Edge(14, 10, travel_time=1), # 2층 복도 - 유키 방
        Edge(14, 11, travel_time=1), # 2층 복도 - 엘라 방

        # === 마당 연결 ===
        Edge(0, 12, travel_time=1),  # 현관 - 앞마당
        Edge(0, 13, travel_time=2),  # 현관 - 뒷마당

        # === 야외/숲 연결 ===
        Edge(12, 20, travel_time=3), # 앞마당 - 숲 입구
        Edge(20, 21, travel_time=15), # 숲 입구 - 숲 깊은 곳
        Edge(20, 22, travel_time=10), # 숲 입구 - 강가
        Edge(20, 23, travel_time=10), # 숲 입구 - 채집터
        Edge(21, 24, travel_time=10), # 숲 깊은 곳 - 사냥터
        Edge(23, 22, travel_time=5),  # 채집터 - 강가
    ]

    # === 날씨 패턴 (현재는 비활성화) ===
    WEATHER_PATTERNS = []
