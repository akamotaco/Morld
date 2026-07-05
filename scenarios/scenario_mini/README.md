# scenario_mini — 인수 검증용 미니 시나리오

**목적**: "신규 시나리오 = 콘텐츠 팩" 증명 (infra-unification U6 인수 기준).
이 팩은 **엔진 모듈만 사용하며 시스템 코드를 복사하지 않는다.**

| 축 | 사용 엔진 모듈 | 팩이 작성한 것 |
|----|----------------|----------------|
| Asset/캐릭터 | `engine.asset_base` + `engine.archetype_describe` | 캐릭터 데이터 파일 1개 (`assets/characters.py`) |
| AI | `engine.think` + `engine.think_base` | 에이전트 1개 (`think/agents/mia_agent.py`) |
| 파티 | `engine.party` | 없음 (그대로 사용) |
| 대화 | `engine.dialogue_hybrid` 아키타입 공용 풀 + `engine.dialogue_policy` | 어댑터 1개 (`npc_dialogue.py`) — 캐릭터 yaml 없이 순수 동적 |
| 지형/배치 | morld API | `world.py` (region 1개, location 1개, 유닛 3개) |

## 구성

```
python/
  __init__.py          # C# 패키지 진입 (scenario.py 재수출)
  scenario.py          # 부트스트랩: 대화 정책 선언 + initialize_scenario()
  think/               # C# 규약: import think; think.think_all() — 엔진 재수출
    agents/mia_agent.py  # 캐릭터 표준 ③: AI 클래스 (@register_agent_class)
  assets/characters.py # 캐릭터 표준 ①: 데이터 파일 (props/아키타입/묘사 rule)
  npc_dialogue.py      # hybrid 어댑터 (아키타입 풀 daily 대사)
  world.py             # 지형 + 배치 + 파티/에이전트 등록
  tests/test_acceptance.py  # 인수 테스트 (심 구동)
```

캐릭터 표준 ②(대사 yaml, `common/python/dialogues/characters/{이름}.yaml`)는
선택 사항이라 이 팩에서는 생략 — 아키타입 공용 풀만으로 대사가 생성됨을
검증한다 (yaml override 실증은 S03 비서.yaml 참조).

## 실행

```powershell
& "C:\ProgramData\miniforge3\python.exe" scenarios\scenario_mini\python\tests\test_acceptance.py
```

인수 기준 (요구 4항 대응):
- (a) 통합 인프라만 사용 — 팩에 시스템 코드 없음
- (b) 대화 정책 선택제 — 이 팩은 hybrid 선언 (S02는 fixed로 구동됨)
- (c) 캐릭터 = 별도 파일 — 데이터/AI 분리, 표준 ①③ 준수
- (d) 파티 시스템 공용 — 플레이어 파티 + 무플레이어 구동 양쪽 검증
