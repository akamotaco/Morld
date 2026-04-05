# S04 생물(Creature) 시스템 설계

> 상태: 설계 단계 (미구현)
> 
> 참조: S02 creature.md, spawner.py, combat.py, creature_agent.py

---

## 설계 원칙

**"던전은 생태계다. 고블린 따위는 없다."**

메트로 퀘스터/다키스트 던전/SCP 재단에서 영감.
던전은 자연 환경이 아니라 **이상 공간** — 생물도 이상하다.

- 일반적 판타지 몬스터(고블린/오크/드래곤) 금지
- 생물은 던전이 만들어낸 **변이체** 또는 **침식된 존재**
- 생물도 생태계 규칙을 따름 (포식/공생/영역)
- 침식(Erosion)이 생물의 근원 — 높은 층 = 높은 침식 = 기괴한 생물

---

## 1. 생물 분류 체계

### 1.1 기원별 분류

| 분류 | 설명 | 예시 |
|------|------|------|
| **변이종 (Mutant)** | 지상 동물이 던전 침식으로 변이 | 맹목쥐, 이빨개, 석화거미 |
| **적응종 (Adapted)** | 던전에서 태어나 적응한 토착종 | 점액충, 균사체, 공명충 |
| **침식체 (Eroded)** | 침식에 완전히 잠식된 존재 (전 인간 포함) | 배회자, 껍데기, 울부짖는 자 |
| **이형 (Anomaly)** | 설명 불가. 던전의 의지? | 거울, 그림자, 문지기 |

### 1.2 행동별 분류

| 행동 | 설명 | 비고 |
|------|------|------|
| **선공 (Aggressive)** | 감지 즉시 공격 | 영역 침범 시 |
| **수비 (Defensive)** | 공격받아야 반격 | 자원 획득 대상 |
| **회피 (Evasive)** | 감지 시 도주 | 추적해야 잡을 수 있음 |
| **잠복 (Ambush)** | 은신 상태로 대기, 근접 시 기습 | 은신 판정 필요 |
| **순찰 (Patrol)** | 방 사이를 이동하며 경계 | 규칙적 패턴 |
| **군집 (Swarm)** | 단독 약하나 무리로 출현 | 수량으로 위협 |

---

## 2. 층별 생태계

### 상층 (F1~F5) — "오염된 지하"

지상에서 흘러들어온 동물의 변이체. 아직 원형이 남아있다.
침식도 낮아서 비교적 예측 가능.

| 생물 | 기원 | 행동 | HP | ATK/DEF | 특징 |
|------|------|------|-----|---------|------|
| **맹목쥐 (Blind Rat)** | 변이종 | 군집 | 8 | 2/0 | 3~6마리 무리. 소음에 반응. 시각 없음 |
| **이빨개 (Fangdog)** | 변이종 | 선공 | 35 | 7/3 | 과잉 발달한 송곳니. 전 가축견 |
| **석화거미 (Petraspider)** | 변이종 | 잠복 | 25 | 5/6 | 돌처럼 굳어 위장. 실로 포획 |
| **점액충 (Slimeworm)** | 적응종 | 수비 | 40 | 3/2 | 느리고 무해. 채취 가능 (점액=소재) |

**보스 (F5): 감염견 (Plaguedog)**
이빨개의 상위종. 물린 자에게 침식 전이.

### 중층 (F6~F10) — "던전의 영역"

지상 흔적이 사라진다. 던전 고유 생물.
은신 판정이 중요해지는 구간.

| 생물 | 기원 | 행동 | HP | ATK/DEF | 특징 |
|------|------|------|-----|---------|------|
| **균사체 (Mycelium)** | 적응종 | 수비 | 60 | 4/8 | 벽/바닥에 붙어있음. 포자 공격 (침식+5) |
| **공명충 (Resonant)** | 적응종 | 회피 | 15 | 1/1 | 소리를 모방. 함정 유인. 잡으면 소재 |
| **배회자 (Wanderer)** | 침식체 | 순찰 | 50 | 10/5 | 전 모험가. 장비 착용. 드롭 좋음 |
| **포식균 (Predafungus)** | 적응종 | 잠복 | 45 | 12/3 | 바닥의 균에서 촉수 돌출. 기습 특화 |

**보스 (F10): 울부짖는 자 (The Weeper)**
침식체. 전 모험가 파티의 리더였던 존재. 인간의 형태를 유지하지만 눈에서 검은 액체가 흐른다.
전투 중 동료였던 배회자 2체 소환.

### 하층 (F11~F15) — "심연의 입구"

공기가 무겁다. 조명이 통하지 않는 구간이 나타난다.
침식이 빠르게 올라간다.

| 생물 | 기원 | 행동 | HP | ATK/DEF | 특징 |
|------|------|------|-----|---------|------|
| **껍데기 (Husk)** | 침식체 | 선공 | 70 | 14/8 | 전 모험가. 무기 사용. 말을 하려 한다 |
| **그림자 (Shadow)** | 이형 | 잠복 | 40 | 18/2 | 어둠에서만 존재. 조명으로 약화 가능 |
| **혀 (The Tongue)** | 적응종 | 잠복 | 55 | 8/4 | 천장에서 늘어지는 촉수. 포획 후 끌어올림 |
| **거울 (Mirror)** | 이형 | 수비 | ? | 반사 | 공격을 반사. 비전투 해법 존재 |

**보스 (F15): 문지기 (The Gatekeeper)**
이형. 거대한 눈 하나. 질문을 한다. 전투를 피할 수 있다 (수수께끼).
전투 시 침식 공격 특화 (물리 대미지 낮음, 침식 대미지 극대).

### 최하층 (F16~F20) — "던전의 심장"

현실의 법칙이 흔들린다. 생물이라기보다 현상에 가깝다.

| 생물 | 기원 | 행동 | HP | ATK/DEF | 특징 |
|------|------|------|-----|---------|------|
| **반향 (Echo)** | 이형 | 순찰 | 90 | 20/10 | 파티원의 복제. 같은 스탯/기술 사용 |
| **구멍 (The Hole)** | 이형 | 선공 | ∞ | 즉사 | 도망만 가능. 접촉 = 즉사. 느림 |
| **합창 (Chorus)** | 이형 | 군집 | 5 | 2/0 | 작은 입들. 100마리+. 침식 공격 |
| **기억 (Memory)** | 이형 | 특수 | 가변 | 가변 | 플레이어의 과거 행동 재현. 행동 패턴 모방 |

**최종 보스 (F20): 심장 (The Heart)**
던전 자체의 핵. 형태 없음.
전투가 아니라 선택 — 소원을 빌 것인가, 파괴할 것인가.
선택에 따라 엔딩 분기.

---

## 3. 생물 데이터 구조

### 3.1 Asset 클래스 (S02 패턴)

```python
# assets/creatures/blind_rat.py
from assets.base import Character
from assets.registry import register_character

@register_character
class BlindRat(Character):
    unique_id = "blind_rat"
    name = "맹목쥐"
    
    # 기본 스탯
    base_str = 2
    base_agi = 12
    base_vit = 3
    base_mnd = 1
    
    # 전투 속성
    props = {
        "생존:체력": 8,
        "생존:최대체력": 8,
        "전투:공격력": 2,
        "전투:방어력": 0,
        "전투:감지거리": 50,
        "전투:공격속도": 0.5,
        "세력": "던전:상층",
    }
    
    # 행동 패턴
    BEHAVIOR = "swarm"          # aggressive/defensive/evasive/ambush/patrol/swarm
    SPAWN_COUNT = (3, 6)        # 군집: 3~6마리
    AGGRO_TRIGGER = "sound"     # sound/sight/proximity
    RETREAT_THRESHOLD = 0.3     # 30% HP 이하 도주
    
    # 드롭
    DROP_TABLE = [
        {"item": "rat_meat", "chance": 0.4, "count": (1, 1)},
    ]
    
    # 침식 관련
    EROSION_ON_HIT = 0          # 공격 시 침식 부여량
    EROSION_ON_DEATH = -1       # 처치 시 침식 변화 (약간 해소)
    
    # 전투 대사
    COMBAT_LINES = {
        "discover": ["어둠 속에서 발톱 긁는 소리가 들린다."],
        "attack": ["쥐떼가 일제히 달려든다!"],
        "death": ["쥐가 경련하며 쓰러진다."],
        "flee": ["쥐떼가 사방으로 흩어진다!"],
    }
```

### 3.2 세력(Faction) 설계

| 세력 | 적대 대상 | 중립 대상 | 비고 |
|------|----------|----------|------|
| 모험가 | 던전:전체 | 마을 NPC | 플레이어+파티 |
| 던전:상층 | 모험가 | 던전:중층 | 변이종 위주 |
| 던전:중층 | 모험가, 던전:상층 | 던전:하층 | 적응종/침식체 |
| 던전:하층 | 모험가, 던전:중층 | 던전:심층 | 침식체/이형 |
| 던전:심층 | 모든 세력 | - | 이형. 적아 구분 없음 |

**층간 세력 관계**: 상층 ↔ 중층 중립 (공존), 중층 ↔ 하층 적대 (영역 다툼)
하층 이상은 모든 것에 적대적.

### 3.3 스포너 등록 (S02 패턴)

```python
# chapters/chapter_0.py 또는 dungeon.py에서
def _register_floor_creatures(floor, region_id):
    """층별 생물 스폰 소스 등록"""
    import spawner
    
    pool = FLOOR_CREATURE_POOL.get(floor, [])
    for entry in pool:
        spawner.register_spawn_source(
            source_id=f"f{floor}_{entry['unique_id']}",
            monster_class=entry["class"],
            max_count=entry["max"],
            interval_hours=entry["interval_h"],
            region_id=region_id,
            location_id=None,       # 방 내 랜덤 배치
            lifespan_hours=entry.get("lifespan_h", 24),  # 던전 내 수명 짧음
        )
```

---

## 4. 조우(Encounter) 시스템

### 4.1 조우 트리거

방 진입 시 자동 판정:

```
방 진입
  │
  ├─ has_monster == False → 안전 (탐색/아이템만)
  │
  ├─ has_monster == True
  │    │
  │    ├─ 은신 중? → stealth.calculate_party_detection_rate()
  │    │    ├─ 미감지 → 회피 성공. 선제 공격 or 우회 선택
  │    │    └─ 감지됨 → 조우 발생
  │    │
  │    └─ 은신 아님 → 즉시 조우
  │
  └─ 조우 발생
       │
       ├─ 적 생성: floor_pool에서 랜덤 선택 + 난이도 보정
       ├─ 적 행동에 따른 분기:
       │    ├─ aggressive/ambush → 즉시 전투
       │    ├─ defensive → 비전투 해법 가능 (무시하고 지나감)
       │    ├─ evasive → 추격 선택지
       │    └─ swarm → 수량 랜덤 (SPAWN_COUNT 범위)
       │
       └─ 전투 or 회피 or 대화 (이형 일부)
```

### 4.2 적 생성 로직

```python
FLOOR_CREATURE_POOL = {
    1: [
        {"class": BlindRat,     "weight": 40, "max": 6, "interval_h": 2},
        {"class": Fangdog,      "weight": 30, "max": 2, "interval_h": 4},
        {"class": Slimeworm,    "weight": 20, "max": 1, "interval_h": 6},
        {"class": Petraspider,  "weight": 10, "max": 1, "interval_h": 8},
    ],
    2: [ ... ],
    # ...
}

def generate_encounter(floor, room):
    """방의 적 그룹 생성"""
    pool = FLOOR_CREATURE_POOL.get(floor, [])
    if not pool:
        return None
    
    # 가중치 랜덤 선택
    entry = weighted_random(pool)
    cls = entry["class"]
    
    # 군집이면 SPAWN_COUNT 범위, 아니면 1체
    if cls.BEHAVIOR == "swarm":
        count = random.randint(*cls.SPAWN_COUNT)
    else:
        count = 1
    
    # 난이도 보정 (층 깊을수록 스탯 보정)
    floor_modifier = 1.0 + (floor - 1) * 0.05  # F1=1.0, F10=1.45, F20=1.95
    
    enemies = []
    for _ in range(count):
        enemy = {
            "name": cls.name,
            "stats": _scale_stats(cls.props, floor_modifier),
            "behavior": cls.BEHAVIOR,
            "erosion_on_hit": cls.EROSION_ON_HIT,
            "drop_table": cls.DROP_TABLE,
            "combat_lines": cls.COMBAT_LINES,
        }
        enemies.append(enemy)
    
    return enemies
```

---

## 5. 특수 메커니즘

### 5.1 침식 공격

일부 생물은 물리 대미지 외에 **침식 대미지**를 준다.

```
피격 시:
  물리 대미지 → HP 감소
  침식 대미지 → erosion.add_erosion(target, amount)
```

| 생물 | 침식/타격 | 비고 |
|------|----------|------|
| 균사체 | +5 | 포자 공격 |
| 배회자 | +2 | 잔류 침식 |
| 그림자 | +8 | 순수 침식 공격 |
| 문지기 | +15 | 보스 특화 |
| 합창 | +1 (×100) | 개체당 낮지만 무리가 위협 |

### 5.2 조명 연동

**그림자 (Shadow)**: `lighting.get_location_brightness()` < 0.3일 때만 존재.
조명이 밝아지면 약화 (ATK/DEF 반감) 또는 소멸.

→ 횃불/랜턴이 전투 도구가 됨.

### 5.3 소음 연동

**맹목쥐**: 시각 없음. `sound` 기반 감지.
은신 + 저소음 이동 시 완전 회피 가능.
전투 소음 → 인접 방 군집 추가 소환.

### 5.4 비전투 해법

| 생물 | 해법 | 조건 |
|------|------|------|
| 점액충 | 무시 가능 | 수비형, 건드리지 않으면 무해 |
| 공명충 | 도주 추적 | 회피형, 잡으면 소재 |
| 거울 | 무시/대화 | 수수께끼 정답 시 보상 |
| 문지기 (보스) | 수수께끼 | 정답 시 전투 없이 통과 |
| 구멍 | 도주만 가능 | 접촉 = 즉사, 느림 |

---

## 6. 로그라이트 연동

### 사망 시 리셋 규칙

| 항목 | 리셋? | 비고 |
|------|-------|------|
| 던전 구조 | O | 시드 재생성 |
| 생물 배치 | O | 스포너 재등록 |
| 플레이어 스탯 | O | 기본값으로 초기화 |
| 플레이어 장비 | O | 전부 소실 (또는 일부 회수 가능) |
| 마을 건물/시설 | X | 유지 |
| NPC 관계/명성 | X | 유지 |
| 숏컷 해금 | X | 유지 (F5/F10/F15 엘리베이터) |
| 도감 (발견한 생물) | X | 유지 — 재도전 정보 |
| 소지금 | △ | 절반 소실, 절반 유지 |

### 도감 시스템

처치/조우한 생물의 정보가 마을 도서관/게시판에 축적.
- 약점, 드롭, 행동 패턴
- 재도전 시 유리 (정보 = 영구 자산)
- NPC도 도감 정보를 공유 (관계 유지)

---

## 7. 구현 우선순위

| 순위 | 작업 | 비고 |
|------|------|------|
| 1 | 생물 Asset 클래스 4종 (F1 풀) | BlindRat, Fangdog, Petraspider, Slimeworm |
| 2 | 스포너 연동 (engine/spawner.py 활용) | dungeon 방 진입 → 적 생성 |
| 3 | 조우 트리거 (방 진입 → encounter) | encounter_handler 연결 |
| 4 | 세력 등록 + 선공/수비 분기 | combat.register_faction_relation |
| 5 | F5 보스 (감염견) | 보스전 테스트 |
| 6 | 중층 생물 4종 (F6~F10) | 배회자, 균사체 등 |
| 7 | 침식 공격 연동 | erosion.add_erosion on hit |
| 8 | 조명/소음 연동 | 그림자/맹목쥐 특수 메커니즘 |
| 9 | 비전투 해법 (거울/문지기) | 대화/수수께끼 분기 |
| 10 | 하층/심층 생물 | 이형 계열 |
