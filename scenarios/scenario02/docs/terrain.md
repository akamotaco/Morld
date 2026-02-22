# 지형 시스템 (Pi-World)

## 현재 상태 요약

### Pi-World 개요

Pi-World는 Location을 1D 선형/원형 공간으로 확장한 지형 시스템입니다.

**핵심 개념:**
- **Location**: 점(0D) → 선형/원형 1D 공간
- **Gate**: Location 간 연결점 (통과 시간 기본 0, 설정 가능)
- **이동 시간**: 거리 기반 계산 (distance / speed)

### Region 구조
| Region ID | 이름 | Location 개수 | 설명 |
|-----------|------|--------------|------|
| 0 | 저택 | 19개 | 메인 거점, 캐릭터 거주 |
| 1 | 차량 | 4개 | 자전거, 자동차 |
| 2 | 황폐화된 도시 | 10개 | 도심 지역, 유키/엘라 거주 |
| 3 | 숲 | 6개 | 별도 Region (자원 채집, 사냥) |
| 4 | 폐광산 | 4개 | 채광, 몬스터 (도시 주차장에서 접근) |

---

## 1. Pi-World Location 속성

### Location 기본 속성
```python
class Location(Asset):
    geometry: int = 0         # 0 = ring (원형), 1 = line (선형)
    length: float = 0         # 0 = 레거시 모드 (점 형태)
```

> **이동 속도**: `Location.BaseSpeed` = 1 unit/sec (C# const, 시나리오에서 변경 불가)

### Geometry 타입
| 값 | 타입 | 설명 | 사용 예 |
|----|------|------|--------|
| 0 | `ring` | 원형 공간 (순환 가능) | 복도, 거실 등 |
| 1 | `line` | 선형 공간 (0 ~ length) | 방, 숲길 등 |

> **기본값**: `geometry=0` (ring). length=0이면 레거시 점 형태.

### 이동 시간 계산
```
이동 시간(ms) = 거리 / (BaseSpeed * speed_modifier)
# BaseSpeed = 1 unit/sec = 0.001 unit/ms

Line: 거리 = |target_x - current_x|
Ring: 거리 = min(|dx|, length - |dx|)  # 최단 경로
```

---

## 2. 저택 Region (ID: 0)

### Location 목록 (Pi-World)
| ID | 이름 | Geometry | Length | 주요 오브젝트 |
|----|------|----------|--------|--------------|
| 0 | 현관 | line | 180 | 심부름 게시판(x=30) |
| 1 | 거실 | ring | 360 | 소파(x=210) |
| 2 | 주방 | line | 180 | 아궁이(x=60), 주전자(x=90), 찬장(x=150) |
| 3 | 식당 | line | 180 | 식탁 의자(x=90) |
| 4 | 욕실 | line | 180 | 거울(x=5), 욕조(x=15), 세면대(x=25), 세탁기(x=50), 건조기(x=70) |
| 5 | 창고 | line | 180 | 제작대(x=60), 도구함(x=120) |
| 6 | 주인공 방 | line | 180 | 침대(x=120) |
| 7 | 리나 방 | line | 180 | 거울(x=30), 침대(x=120), 옷장(x=150) |
| 8 | 세라 방 | line | 180 | 침대(x=120), 인형(x=132), 옷장(x=150) |
| 9 | 밀라 방 | line | 180 | 침대(x=120), 옷장(x=150) |
| 10 | 빈 방 1 | line | 180 | 거울(x=30), 침대(x=120) |
| 11 | 빈 방 2 | line | 180 | 거울(x=30), 침대(x=120) |
| 12 | 앞마당 | line | 600 | - |
| 13 | 뒷마당 | line | 600 | 자전거(x=300) |
| 14 | 2층 복도 | ring | 360 | - |
| 15 | 1층 화장실 | line | 180 | 변기(x=90) |
| 16 | 2층 화장실 | line | 180 | 변기(x=90) |
| 20 | 숲 입구 | line | 1800 | - |
| 21 | 숲 깊은 곳 | line | 1800 | - |
| 22 | 강가 | line | 1200 | 낚시터(x=600) |
| 23 | 채집터 | line | 900 | - |
| 24 | 사냥터 | line | 1800 | - |

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

## 3. 도시 Region (ID: 2) - 황폐화된 도시

### Location 목록 (Pi-World)
| ID | 이름 | Geometry | Length | 주요 오브젝트 |
|----|------|----------|--------|--------------|
| 0 | 도시 입구 | line | 600 | 벤치(x=200), 가로수(x=450) |
| 1 | 주유소 | line | 300 | 가판대(x=100), 수도꼭지(x=200) |
| 2 | 편의점 | line | 180 | 선반(도시지도), 냉장고×3, 수도꼭지(x=170) |
| 3 | 약국 | line | 180 | 약품진열대(x=50) |
| 4 | 주차장 | line | 360 | 자판기(x=100), 야생열매(x=220), 야생약초(x=250) |
| 5 | 은신처 | line | 180 | 침낭(x=50), 램프(x=90), 소파(x=90), 화로(x=130), 욕조(x=150), 텃밭(x=160) |
| 6 | 의류점 | line | 240 | 옷걸이(의류 다수) |
| 7 | 성인용품점 | line | 180 | 진열대(성인용품 20종) — 로맨스 모드 전용 |
| 8 | 코인세탁소 | line | 180 | 세탁기×2(x=40,80), 건조기×2(x=120,140) |

### 도시 Gate 연결
```
도시입구(0) ←Gate→ 주유소(1), 편의점(2), 약국(3), 의류점(6), 코인세탁소(8)
주유소(1) ←Gate→ 주차장(4)
편의점(2) ←Gate→ 의류점(6)
약국(3) ←Gate→ 은신처(5)
주차장(4) ←Gate→ 성인용품점(7)  ← 조건부: can:romance# (로맨스 모드 OFF 시 숨김)
```

---

## 4. 숲 Region (ID: 3) - 별도 Region

### Location 목록 (Pi-World)
| ID | 이름 | Geometry | Length | 주요 오브젝트 |
|----|------|----------|--------|--------------|
| 0 | 숲 입구 | line | 1200 | - |
| 1 | 소나무 숲 | line | 1800 | 소나무(x=900) |
| 2 | 참나무 숲 | line | 1800 | 참나무(x=900) |
| 3 | 숲속 | line | 2400 | 토끼굴(x=1200) |
| 4 | 늑대굴 | line | 600 | - |
| 5 | 오두막 | line | 180 | 옷장(x=120) |

### 숲 Gate 연결
```
숲입구(0) ←Gate→ 소나무숲(1), 참나무숲(2)
소나무숲(1) ←Gate→ 숲속(3), 참나무숲(2)
참나무숲(2) ←Gate→ 늑대굴(4), 오두막(5)
```

---

## 5. Gate 시스템

### Gate 정의 형식
```python
# 기본 (travel_time=0, 즉시 통과)
# (region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x)
morld.add_gate(REGION_ID, 0, 0, 180, REGION_ID, 1, 0)   # 현관 끝(x=180) -> 거실(x=0)에 도착

# travel_time 지정 (통과에 시간 소요)
# add_gate(..., arrival_y=0, conditions_forward=None, conditions_backward=None, is_blocked=False, name="", travel_time=0)
morld.add_gate(REGION_ID, 0, 0, 180, REGION_ID, 1, 0, 0, None, None, False, "", 5000)  # 5초 통과
```

### Gate 속성
- **x**: Gate 위치 (Location 내 좌표)
- **arrival_x**: 통과 시 도착 좌표 (연결된 Location 내)
- **connected_region/location**: 연결된 Location 정보
- **travel_time**: 통과 시간 (밀리초, 기본값 0 = 즉시 통과)

### 이동 흐름
```
[현재 위치] → 이동(거리 기반) → [Gate(x)] → [통과 시간] → [연결된 Location(arrival_x)] → 이동 → [목적지]
```

> **이동 시간 합산**: Location 내 이동 시간 + Gate 통과 시간의 합이 전체 경로 이동 시간

---

## 6. 오브젝트 위치 배치

### 배치 규칙
- 오브젝트는 Location 내 특정 x 좌표에 배치
- 같은 위치에 여러 오브젝트 배치 가능
- 오브젝트 위치는 `add_object(obj, x=10)` 형태로 지정

### 배치 예시
```python
def instantiate(self, location_id: int, region_id: int):
    super().instantiate(location_id, region_id)
    self.add_ground(GroundWooden())
    self.add_object(Mirror(), x=30)    # 문 옆
    self.add_object(Bed(), x=120)     # 방 안쪽
    self.add_object(Wardrobe(), x=150) # 침대 옆
```

---

## 7. 테스트 체크리스트

### Location 이동 테스트
1. [ ] 현관에서 시작 (x=0)
2. [ ] 거실 Gate로 이동 → 이동 시간(ms) = distance / BaseSpeed
3. [ ] Gate 통과 → 거실(1)의 Gate 위치(x=0)에 도착
4. [ ] 소파(x=210)로 이동

### Gate 연결 테스트
1. [ ] 거실 → 주방 Gate 통과
2. [ ] 주방 내 이동 (아궁이 x=60 → 찬장 x=150)
3. [ ] 주방 → 식당 Gate 통과

### Ring Geometry 테스트
1. [ ] 거실(ring, length=360) 내 이동
2. [ ] 최단 경로 선택 확인 (x=0 → x=300: 직접 또는 순환)
3. [ ] 2층 복도(ring, length=360) 내 이동

### 오브젝트 상호작용 테스트
1. [ ] 침대(x=120) 위치로 이동
2. [ ] 침대 액션 실행
3. [ ] 옷장(x=150) 위치로 이동
4. [ ] 옷장 열기

---

## 참고: 기존 시스템과 비교

### 이전 (Legacy Edge 기반, 삭제됨)
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
    (REGION_ID, 0, 0, 180, REGION_ID, 1, 0),   # 현관(x=180) -> 거실(x=0)
    (REGION_ID, 1, 0, 0, REGION_ID, 0, 180),   # 거실(x=0) -> 현관(x=180)
]
```

### 차이점
| 항목 | Legacy Edge | Gate |
|------|------|------|
| 이동 시간 | 고정값 | 거리 기반 계산 + Gate 통과 시간 |
| Location 내 위치 | 없음 | x 좌표 |
| 오브젝트 배치 | 위치 없음 | x 좌표 지정 |
| 연결 | 양방향 암묵적 | 각 방향 명시 |
| 도착 위치 | Gate 참조 | 직접 좌표 지정 |
