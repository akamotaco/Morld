# Scenario01: 방 탈출 - 설계 문서

## 개요

플레이어가 미스터리한 저택에서 탈출하는 방 탈출 시나리오.
NPC 없이 오브젝트 상호작용과 퍼즐 풀이에 집중.

---

## 핵심 개념

### Asset vs Instance
- **Asset**: 구조체 정의 (템플릿). `unique_id: str`로 식별
- **Instance**: 게임 내 실체. `instance_id: int`로 식별 (morld API에서 사용)

```python
# Asset 정의 (assets/items/golden_key.py)
GOLDEN_KEY = {
    "unique_id": "golden_key",
    "name": "황금열쇠",
    ...
}

# Instance 생성 (world/mansion.py에서)
registry.instantiate_item("golden_key", instance_id=3)
```

---

## 폴더 구조

```
scenario01/
├── python/
│   ├── __init__.py           # 시나리오 진입점
│   ├── scripts.py            # 공통 스크립트 export (비밀번호 시스템 등)
│   │
│   ├── assets/               # Asset 정의 (템플릿)
│   │   ├── __init__.py       # AssetRegistry + load_all_assets()
│   │   │
│   │   ├── items/            # 아이템 Asset
│   │   │   ├── __init__.py   # register_all()
│   │   │   ├── keys.py       # 열쇠류 (rusty_key, silver_key)
│   │   │   ├── golden_key.py # 황금열쇠 + 파츠 + 조합
│   │   │   ├── notes.py      # 쪽지류
│   │   │   └── documents.py  # 일기장, 편지, 메모
│   │   │
│   │   ├── objects/          # 오브젝트 Asset (위치별 분류)
│   │   │   ├── __init__.py   # register_all()
│   │   │   ├── basement.py   # 지하실 오브젝트
│   │   │   ├── storage.py    # 창고 오브젝트
│   │   │   ├── living_room.py # 거실 오브젝트
│   │   │   ├── kitchen.py    # 주방 오브젝트
│   │   │   ├── bedroom.py    # 침실 오브젝트
│   │   │   ├── study.py      # 서재 오브젝트
│   │   │   ├── corridor.py   # 복도 오브젝트
│   │   │   ├── stairs.py     # 계단 오브젝트
│   │   │   └── entrance.py   # 정문 홀 오브젝트
│   │   │
│   │   └── characters/       # 캐릭터 Asset
│   │       ├── __init__.py   # register_all()
│   │       └── player.py     # 플레이어 정의
│   │
│   ├── world/                # 지형 + 인스턴스화 (Region별)
│   │   ├── __init__.py       # initialize_terrain(), instantiate_all()
│   │   └── mansion.py        # 저택 Region 전체 (지형 + 배치)
│   │
│   └── events/               # 이벤트 핸들러
│       ├── __init__.py       # on_event_list export
│       └── handlers.py       # game_start, on_reach 등
│
├── design.md                 # 이 문서
└── 시나리오.md               # 스토리/힌트 상세
```

---

## 맵 구조

```
                    ┌─────────┐
                    │ 서재(7) │
                    └────┬────┘
                         │ (서재 문, 비밀번호)
┌─────────┐    ┌─────────┴─────────┐    ┌─────────┐
│ 침실(6) ├────┤   복도 2층(8)     ├────┤ 그림액자│
└─────────┘    └─────────┬─────────┘    └─────────┘
                         │
                    ┌────┴────┐
                    │ 계단(5) │
                    └────┬────┘
                         │
┌─────────┐    ┌─────────┴─────────┐    ┌─────────┐
│ 거실(2) ├────┤   복도 1층(4)     ├────┤정문홀(9)│
└────┬────┘    └─────────┬─────────┘    └─────────┘
     │                   │                   │
┌────┴────┐         ┌────┴────┐         (정문, 황금열쇠)
│ 주방(3) │         │ 창고(1) │
└─────────┘         └────┬────┘
                         │ (배전함 ON 필요)
                    ┌────┴────┐
                    │지하실(0)│ ← 시작 위치
                    └─────────┘
```

---

## Instance ID 할당 규칙

```python
# world/mansion.py에서 정의
플레이어: 0
아이템: 1 ~ 99
오브젝트: 100 ~ 199
NPC: 200 ~ 299 (이 시나리오에서는 미사용)
바닥 유닛: 1000 + location_id
```

---

## 아이템 목록

| Instance ID | Unique ID | 이름 | 획득 위치 | 용도 |
|-------------|-----------|------|-----------|------|
| 1 | rusty_key | 녹슨 열쇠 | 낡은 상자(100) | 캐비닛 해제 |
| 2 | silver_key | 은열쇠 | 캐비닛(103) | 찬장 해제 |
| 3 | golden_key | 황금열쇠 | 조합 | 정문 해제 |
| 4 | note1 | 쪽지 1 | 선반(102) | 비밀번호 힌트 |
| 5 | note2 | 쪽지 2 | 소파(105) | 비밀번호 힌트 |
| 6 | note3 | 쪽지 3 | 책상서랍(112) | 금고 비밀번호 |
| 7 | diary | 일기장 | 침대밑(108) | 스토리/힌트 |
| 8 | old_letter | 오래된 편지 | 침대밑(108) | 스토리 |
| 9 | study_memo | 서재 메모 | 화장대(109) | 서재문 비밀번호 |
| 10 | golden_key_head | 황금열쇠 머리 | 찬장(107) | 조합 재료 |
| 11 | golden_key_body | 황금열쇠 몸통 | 금고(111) | 조합 재료 |

---

## 오브젝트 목록

### 지하실 (Location 0)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 100 | old_box | 낡은 상자 | 녹슨 열쇠 획득 |
| 101 | power_panel | 배전함 | 전원 ON/OFF |

### 창고 (Location 1)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 102 | shelf | 선반 | 쪽지1 획득 |
| 103 | old_cabinet | 낡은 캐비닛 | 녹슨열쇠 → 은열쇠 |

### 거실 (Location 2)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 104 | fireplace | 벽난로 | 숫자 힌트 "3" |
| 105 | sofa_cushion | 소파 쿠션 | 쪽지2 획득 |

### 주방 (Location 3)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 106 | refrigerator | 냉장고 | 숫자 힌트 "7" |
| 107 | cupboard | 찬장 | 은열쇠 → 황금열쇠 머리 |

### 복도 1층 (Location 4)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 115 | grandfather_clock | 괘종시계 | 힌트 "1842년" |
| 116 | umbrella_stand | 우산꽂이 | 플레이버 텍스트 |

### 계단 (Location 5)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 117 | broken_step | 부서진 계단 | 플레이버 텍스트 |
| 118 | stair_window | 창문 | 탈출 불가 확인 |

### 침실 (Location 6)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 108 | bed_under | 침대 밑 | 일기장 + 편지 획득 |
| 109 | vanity_drawer | 화장대 서랍 | 비밀번호 "3749" → 서재 메모 |

### 서재 (Location 7)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 111 | safe | 금고 | 비밀번호 "1842" → 황금열쇠 몸통 |
| 112 | desk_drawer | 책상 서랍 | 쪽지3 획득 |

### 복도 2층 (Location 8)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 110 | picture_frame | 그림 액자 | 숫자 힌트 "4", "9" |
| 114 | study_door | 서재 문 | 비밀번호 "2847" → 서재 입장 |

### 정문 홀 (Location 9)
| Instance ID | Unique ID | 이름 | 상호작용 |
|-------------|-----------|------|----------|
| 113 | front_door | 정문 | 황금열쇠 → 탈출! |

---

## 퍼즐 흐름

```
[시작: 지하실]
     │
     ▼
[배전함 ON] ─────────────────────────────────┐
     │                                       │
     ▼                                       │
[낡은 상자] → 녹슨 열쇠                       │
     │                                       │
     ▼                                       │
[캐비닛] → 은열쇠                             │
     │                                       │
     ▼                                       │
[찬장] → 황금열쇠 머리                        │
     │                                       │
     ├─────────────────────┐                 │
     │                     │                 │
     ▼                     ▼                 │
[벽난로]="3"          [냉장고]="7"            │
[그림액자]="4","9"                           │
     │                                       │
     ▼                                       │
[화장대 서랍] 비밀번호: 3749                  │
     │                                       │
     ▼                                       │
[서재 메모] → 서재 문 비밀번호: 2847          │
     │                                       │
     ▼                                       │
[서재 문] → 서재 입장                         │
     │                                       │
     ▼                                       │
[금고] 비밀번호: 1842 (괘종시계/일기장 힌트)  │
     │                                       │
     ▼                                       │
[황금열쇠 몸통]                               │
     │                                       │
     ▼                                       │
[머리 + 몸통 조합] → 황금열쇠                 │
     │                                       │
     ▼                                       │
[정문] → 탈출 성공!                           │
                                             │
         ◀──────────────────────────────────┘
              (전원 ON이 선행 조건)
```

---

## 비밀번호 목록

| 오브젝트 | 비밀번호 | 힌트 위치 |
|----------|----------|-----------|
| 화장대 서랍 (109) | 3749 | 벽난로=3, 냉장고=7, 그림=4,9 |
| 서재 문 (114) | 2847 | 서재 메모 (id:9) |
| 금고 (111) | 1842 | 괘종시계, 일기장 |

---

## 이벤트

### game_start
- 게임 시작 시 모놀로그 표시
- "...어디지, 여기는?" 등 플레이어 혼란 연출

### on_reach: 침실(6)
- 첫 방문 시 희미한 목소리 이벤트
- "...나...가..." 음산한 분위기 연출

---

## Asset Registry 시스템

```python
# assets/__init__.py

class AssetRegistry:
    """Asset ↔ Instance ID 매핑 관리"""

    def __init__(self):
        self._items = {}           # unique_id → asset data
        self._objects = {}
        self._characters = {}
        self._instance_map = {}    # unique_id → instance_id
        self._reverse_map = {}     # instance_id → unique_id

    def register_item(self, asset_data):
        """Item Asset 등록"""
        ...

    def instantiate_item(self, unique_id, instance_id):
        """Item을 Instance로 생성 (morld.add_item 호출)"""
        ...

    def get_instance_id(self, unique_id):
        """unique_id → instance_id"""
        return self._instance_map.get(unique_id)

# 전역 레지스트리
registry = AssetRegistry()
```

---

## 파일 작성 규칙

### Item Asset
```python
# assets/items/{name}.py

ITEM_NAME = {
    "unique_id": "item_name",
    "name": "아이템 이름",
    "passiveProps": {},
    "equipProps": {},
    "value": 0,
    "actions": ["take@container", "script:함수명:표시명@context"]
}

def register():
    registry.register_item(ITEM_NAME)

# 스크립트 함수 (선택적)
def 함수명(context_unit_id):
    return {
        "type": "monologue",
        "pages": [...],
        "time_consumed": 0,
        "button_type": "ok"
    }
```

### Object Asset
```python
# assets/objects/{location}.py

OBJECT_NAME = {
    "unique_id": "object_name",
    "name": "오브젝트 이름",
    "actions": ["script:함수명:표시명"],
    "appearance": {"default": "설명..."}
}

def register():
    registry.register_object(OBJECT_NAME)

def 함수명(context_unit_id):
    # 플래그 체크, 아이템 지급 등
    return {...}
```

### World 배치
```python
# world/mansion.py

ITEMS = {
    # instance_id: unique_id
    1: "rusty_key",
    2: "silver_key",
    ...
}

OBJECTS = [
    # (instance_id, region_id, location_id, unique_id)
    (100, 0, 0, "old_box"),
    (101, 0, 0, "power_panel"),
    ...
]

def instantiate():
    for instance_id, unique_id in ITEMS.items():
        registry.instantiate_item(unique_id, instance_id)
    for instance_id, region_id, location_id, unique_id in OBJECTS:
        registry.instantiate_object(unique_id, instance_id, region_id, location_id)
```

---

## 초기화 흐름

```python
# __init__.py - initialize_scenario()

1. initialize_terrain()    # 지형 데이터 (Region, Location, Edge)
2. initialize_time()       # 게임 시간 설정
3. load_all_assets()       # Asset 정의 로드 (정의만, 인스턴스화 X)
4. instantiate_all()       # 캐릭터, 오브젝트, 아이템 인스턴스 생성
```

---

## 확장 포인트

1. **새 오브젝트 추가**:
   - `assets/objects/`에 정의 추가 → `world/mansion.py`의 OBJECTS에 배치

2. **새 아이템 추가**:
   - `assets/items/`에 정의 추가 → `world/mansion.py`의 ITEMS에 배치

3. **새 이벤트 추가**:
   - `events/handlers.py`의 `REACH_EVENTS` 딕셔너리에 추가

4. **새 비밀번호 오브젝트**:
   - `scripts.py`의 `PASSWORD_OBJECTS` 딕셔너리에 등록

5. **새 Region 추가** (시나리오 확장 시):
   - `world/`에 새 파일 생성 → `world/__init__.py`에서 import
