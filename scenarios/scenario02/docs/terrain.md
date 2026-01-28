# 지형 시스템 (Pi-World)

## 현재 상태 요약

### Pi-World 개요

Pi-World는 Location을 1D 선형/원형 공간으로 확장한 지형 시스템입니다.

**핵심 개념:**
- **Location**: 점(0D) → 선형/원형 1D 공간
- **Gate**: Location 간 연결점 (통과 시간 = 0)
- **이동 시간**: 거리 기반 계산 (distance / speed)

### Region 구조
| Region ID | 이름 | Location 개수 | 설명 |
|-----------|------|--------------|------|
| 0 | 저택 | 19개 | 메인 거점, 캐릭터 거주 |
| 1 | 차량 | 4개 | 자전거, 자동차 |
| 2 | 도시 | (미구현) | 향후 확장 |
| 3 | 숲 | 6개 | 별도 Region (자원 채집, 사냥) |

---

## 1. Pi-World Location 속성

### Location 기본 속성
```python
class Location(Asset):
    geometry: str = "line"    # "line" 또는 "ring"
    length: float = 0         # 0 = 레거시 모드 (점 형태)
    base_speed: float = 10    # 단위/분
```

### Geometry 타입
| 타입 | 설명 | 사용 예 |
|------|------|--------|
| `line` | 선형 공간 (0 ~ length) | 방, 숲길 등 |
| `ring` | 원형 공간 (순환 가능) | 복도, 거실 등 |

### 이동 시간 계산
```
이동 시간 = 거리 / (base_speed * speed_modifier)

Line: 거리 = |target_x - current_x|
Ring: 거리 = min(|dx|, length - |dx|)  # 최단 경로
```

---

## 2. 저택 Region (ID: 0)

### Location 목록 (Pi-World)
| ID | 이름 | Geometry | Length | 주요 오브젝트 |
|----|------|----------|--------|--------------|
| 0 | 현관 | line | 30 | 심부름 게시판(x=5) |
| 1 | 거실 | ring | 60 | 소파(x=35) |
| 2 | 주방 | line | 30 | 아궁이(x=10), 주전자(x=15), 찬장(x=25) |
| 3 | 식당 | line | 30 | 식탁 의자(x=15) |
| 4 | 욕실 | line | 30 | 거울(x=5), 욕조(x=15), 세면대(x=25) |
| 5 | 창고 | line | 30 | 제작대(x=10), 도구함(x=20) |
| 6 | 주인공 방 | line | 30 | 침대(x=20) |
| 7 | 리나 방 | line | 30 | 거울(x=5), 침대(x=20), 옷장(x=25) |
| 8 | 세라 방 | line | 30 | 침대(x=20), 인형(x=22), 옷장(x=25) |
| 9 | 밀라 방 | line | 30 | 침대(x=20), 옷장(x=25) |
| 10 | 빈 방 1 | line | 30 | 거울(x=5), 침대(x=20) |
| 11 | 빈 방 2 | line | 30 | 거울(x=5), 침대(x=20) |
| 12 | 앞마당 | line | 100 | - |
| 13 | 뒷마당 | line | 100 | 자전거(x=50) |
| 14 | 2층 복도 | ring | 60 | - |
| 15 | 1층 화장실 | line | 30 | 변기(x=15) |
| 16 | 2층 화장실 | line | 30 | 변기(x=15) |
| 20 | 숲 입구 | line | 300 | - |
| 21 | 숲 깊은 곳 | line | 300 | - |
| 22 | 강가 | line | 200 | 낚시터(x=100) |
| 23 | 채집터 | line | 150 | - |
| 24 | 사냥터 | line | 300 | - |

### 저택 Gate 연결
```
=== 1층 ===
현관(0) ←Gate→ 거실(1)
거실(1) ←Gate→ 주방(2), 식당(3), 욕실(4), 주인공방(6), 리나방(7), 밀라방(9), 1층화장실(15), 2층복도(14)
주방(2) ←Gate→ 식당(3)

=== 2층 ===
2층복도(14) ←Gate→ 세라방(8), 빈방1(10), 빈방2(11), 창고(5), 2층화장실(16)

=== 마당 ===
현관(0) ←Gate→ 앞마당(12), 뒷마당(13)

=== 야외/숲 ===
앞마당(12) ←Gate→ 숲입구(20)
숲입구(20) ←Gate→ 숲깊은곳(21), 강가(22), 채집터(23)
숲깊은곳(21) ←Gate→ 사냥터(24)
채집터(23) ←Gate→ 강가(22)
```

---

## 3. 숲 Region (ID: 3) - 별도 Region

### Location 목록 (Pi-World)
| ID | 이름 | Geometry | Length | 주요 오브젝트 |
|----|------|----------|--------|--------------|
| 0 | 숲 입구 | line | 200 | - |
| 1 | 소나무 숲 | line | 300 | 소나무(x=150) |
| 2 | 참나무 숲 | line | 300 | 참나무(x=150) |
| 3 | 숲속 | line | 400 | 토끼굴(x=200) |
| 4 | 늑대굴 | line | 100 | - |
| 5 | 오두막 | line | 30 | 옷장(x=20) |

### 숲 Gate 연결
```
숲입구(0) ←Gate→ 소나무숲(1), 참나무숲(2)
소나무숲(1) ←Gate→ 숲속(3), 참나무숲(2)
참나무숲(2) ←Gate→ 늑대굴(4), 오두막(5)
```

---

## 4. Gate 시스템

### Gate 정의 형식
```python
# (region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x)
(REGION_ID, 0, 0, 30, REGION_ID, 1, 0),   # 현관 끝(x=30) -> 거실(x=0)에 도착
(REGION_ID, 1, 0, 0, REGION_ID, 0, 30),   # 거실 입구(x=0) -> 현관(x=30)에 도착
```

### Gate 속성
- **x**: Gate 위치 (Location 내 좌표)
- **arrival_x**: 통과 시 도착 좌표 (연결된 Location 내)
- **connected_region/location**: 연결된 Location 정보
- **통과 시간**: 0 (즉시 통과)

### 이동 흐름
```
[현재 위치] → 이동(거리 기반) → [Gate(x)] → [즉시] → [연결된 Location(arrival_x)] → 이동 → [목적지]
```

---

## 5. 오브젝트 위치 배치

### 배치 규칙
- 오브젝트는 Location 내 특정 x 좌표에 배치
- 같은 위치에 여러 오브젝트 배치 가능
- 오브젝트 위치는 `add_object(obj, x=10)` 형태로 지정

### 배치 예시
```python
def instantiate(self, location_id: int, region_id: int):
    super().instantiate(location_id, region_id)
    self.add_ground(GroundWooden())
    self.add_object(Mirror(), x=5)    # 문 옆
    self.add_object(Bed(), x=20)      # 방 안쪽
    self.add_object(Wardrobe(), x=25) # 침대 옆
```

---

## 6. 테스트 체크리스트

### Location 이동 테스트
1. [ ] 현관에서 시작 (x=0)
2. [ ] 거실 Gate로 이동 → 이동 시간 = distance / speed
3. [ ] Gate 통과 → 거실(1)의 Gate 위치(x=0)에 도착
4. [ ] 소파(x=35)로 이동

### Gate 연결 테스트
1. [ ] 거실 → 주방 Gate 통과
2. [ ] 주방 내 이동 (아궁이 x=10 → 찬장 x=25)
3. [ ] 주방 → 식당 Gate 통과

### Ring Geometry 테스트
1. [ ] 거실(ring, length=60) 내 이동
2. [ ] 최단 경로 선택 확인 (x=0 → x=50: 직접 또는 순환)
3. [ ] 2층 복도(ring, length=60) 내 이동

### 오브젝트 상호작용 테스트
1. [ ] 침대(x=20) 위치로 이동
2. [ ] 침대 액션 실행
3. [ ] 옷장(x=25) 위치로 이동
4. [ ] 옷장 열기

---

## 참고: 기존 Edge 시스템과 비교

### 이전 (Edge 기반)
```python
EDGES = [
    (0, 1, 1),   # 현관-거실, 1분
    (1, 2, 1),   # 거실-주방, 1분
]
```

### 현재 (Gate 기반)
```python
# (region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x)
GATES = [
    (REGION_ID, 0, 0, 30, REGION_ID, 1, 0),   # 현관(x=30) -> 거실(x=0)
    (REGION_ID, 1, 0, 0, REGION_ID, 0, 30),   # 거실(x=0) -> 현관(x=30)
]
```

### 차이점
| 항목 | Edge | Gate |
|------|------|------|
| 이동 시간 | 고정값 | 거리 기반 계산 |
| Location 내 위치 | 없음 | x 좌표 |
| 오브젝트 배치 | 위치 없음 | x 좌표 지정 |
| 연결 | 양방향 암묵적 | 각 방향 명시 |
| 도착 위치 | Gate 참조 | 직접 좌표 지정 |
