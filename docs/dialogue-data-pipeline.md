# 대화 데이터 파이프라인 — yaml 저작 + 빌드타임 컴파일

> **한 줄 요약**: 대사는 yaml로 저작하고, 커밋 전에 `compile_dialogues.py`를 돌려
> `dialogues_compiled/` 패키지를 갱신한다. SharpPy 런타임(프로덕션)은 pyyaml이 없어서
> **컴파일본만** 읽는다. yaml만 고치고 컴파일을 잊으면 게임에는 반영되지 않는다.

도입 배경 (2026-07-05): SharpPy 런타임에 pyyaml이 없어 hybrid 대화 모듈이
프로덕션에서 import조차 실패하던 문제의 구조적 해소. Hybrid 엔진 자체는
[dialogue-hybrid.md](dialogue-hybrid.md) 참조.

---

## 1. 구조

```
[저작]  scenarios/common/python/dialogues/
        ├── characters/*.yaml               ← 사람이 편집
        └── archetype_dialogues/*/*.yaml    ← 사람이 편집
                    │
                    │  python compile_dialogues.py   (CPython/miniforge, 검증 포함)
                    ▼
[산출물] scenarios/common/python/dialogues_compiled/  ← 자동 생성, 수동 편집 금지, 커밋 대상
        ├── __init__.py        # get(rel) lazy 접근자 + SOURCE_HASH + FILE_COUNT
        ├── characters.py      # 캐릭터 yaml 전체
        └── arch_{아키타입}.py   # 아키타입별 분할 (10개 — SharpPy 파싱 부담 분산)
                    │
                    ▼
[런타임] engine/dialogue_hybrid/data_loader.py  — 2단 폴백:
        ① pyyaml 있음(CPython 개발/테스트) → yaml 직독 (항상 최신 소스)
        ② pyyaml 없음(SharpPy 프로덕션)     → dialogues_compiled 사용
```

- 산출물은 **결정적**(같은 소스 → 같은 바이트) — git diff로 리뷰 가능하다.
- `engine.py`/`stateless.py`는 yaml을 직접 import하지 않는다. **새 코드도 반드시
  `data_loader.load_yaml_file(root, rel)`을 경유할 것** (톱레벨 `import yaml` 금지 —
  SharpPy에서 모듈 import 자체가 죽는다).

## 2. 작업 절차 (대사 수정 시)

```powershell
# 1. yaml 편집 (characters/ 또는 archetype_dialogues/)
# 2. 컴파일 (검증 + 산출물 갱신)
& "C:\ProgramData\miniforge3\python.exe" scenarios\common\python\dialogues\compile_dialogues.py

# 3. 드리프트 확인 (커밋 전 / CI)
& "C:\ProgramData\miniforge3\python.exe" scenarios\common\python\dialogues\compile_dialogues.py --check

# 4. 테스트 (동등성 포함)
& "C:\ProgramData\miniforge3\python.exe" scenarios\common\python\tests\run_tests.py dialogue

# 5. yaml + dialogues_compiled/ 를 같은 커밋에 포함
```

`--strict`: 경고도 에러로 승격 (신규 대량 저작 후 권장).

## 3. 컴파일러 검증 규칙

에러 형식은 항상 `파일: 위치: 내용` — 어느 yaml의 어느 intent/template인지 특정된다.
**에러가 1건이라도 있으면 산출물을 쓰지 않는다** (부분 산출물 금지).

| 등급 | 규칙 |
|------|------|
| ERROR | yaml 파싱 실패 / 최상위가 dict 아님 |
| ERROR | template `pattern` 누락·빈 문자열 |
| ERROR | intent 내 **중복 template id** (replace/disable 대상이 모호해짐) |
| ERROR | `state_bias`/`inner_bias`/slot `feature` 값이 숫자 아님 |
| ERROR | slots가 dict 아님 / slot 풀이 list 아님 / dict 항목에 `token` 없음 |
| ERROR | 캐릭터 `archetype` 누락 또는 해당 `archetype_dialogues/{arch}/` 폴더 없음 |
| WARN | template `id` 없음 (override 대상 지정 불가) |
| WARN | 패턴이 참조하는 `{slot}`이 풀에도 컨텍스트 슬롯(name/floor/victim/target/item)에도 없음 → 런타임에 빈 문자열 치환 |
| WARN | 파일명과 `character` 필드 불일치 |
| WARN | `dialogue_overrides`에 알 수 없는 컨텍스트명 (병합되지 않음) |

실전 사례: 도입 첫 컴파일에서 `cold/action_lines.yaml`의 중복 id 22건을 검출
(두 생성 배치가 같은 id 좌표계를 사용) → 후행 배치 id에 `b` 접미사로 해소.

## 4. 문제 진단 표 (증상 → 원인 → 조치)

| 증상 | 원인 | 조치 |
|------|------|------|
| 게임(SharpPy)에서 `RuntimeError: pyyaml 도 dialogues_compiled 도 없음` | 컴파일본 미생성/미배포 | `compile_dialogues.py` 실행 후 산출물 커밋 |
| 게임에서 아키타입 대사 대신 `_LINES` 폴백/`...`만 나옴 | yaml만 고치고 재컴파일 누락 (게임은 옛 컴파일본 사용) | `--check`로 확인 → 재컴파일 |
| 로그 `[dialogue_data] WARN compiled 데이터에 없음: <rel>` | yaml 파일 신규 추가/이동 후 재컴파일 누락 | 재컴파일 |
| `--check`가 `DRIFT` 보고 | yaml과 산출물 불일치 (위와 동일 부류) | 재컴파일 + 같은 커밋에 포함 |
| 컴파일러가 `ERROR 파일: 위치: ...` 출력 후 exit 1 | yaml 저작 결함 | 보고된 파일·intent·template 수정 (§3 규칙 참조) |
| 로그 `[dialogue_data] ERROR yaml 파싱 실패: <rel>` (CPython) | 해당 yaml 문법 오류 — **그 파일만 격리**되고 나머지는 동작 | 해당 파일 수정 |
| CPython 테스트는 통과인데 게임 대사만 다름 | yaml(개발)↔컴파일본(게임) 불일치 | `data_loader.FORCE_COMPILED=True`로 재현 → 동등성 테스트(`test_dialogue_compile`) 실행 |
| 시작 로그에 `[dialogue_data] compiled 데이터 사용 (files=N, source_hash=…)` | (정상) 컴파일본 경로로 동작 중이라는 표시 | source_hash로 어느 빌드인지 특정 가능 |

## 5. 테스트

`scenarios/common/python/tests/test_dialogue_compile.py` (러너에 등록됨):

- **동등성 4종**: 같은 rng에서 yaml 경로와 컴파일본 경로(`FORCE_COMPILED`)가
  동일 대사 생성 (daily/romance/reaction)
- **전수 커버리지**: 모든 yaml이 컴파일본 `get()`으로 조회 가능 + `FILE_COUNT` 일치
- **검증기 catch 5종**: 중복 id / pattern 누락 / 비숫자 bias / 잘못된 slot 풀 / 미지 slot 경고
- **로더 실패 모드**: 커스텀 root + pyyaml 없음 → RuntimeError (조용한 실패 금지)

## 6. 규약 (미래 Claude 포함 필수 준수)

1. `dialogues_compiled/`는 **수동 편집 금지** — 항상 컴파일러로만 갱신
2. yaml 변경 커밋에는 **반드시 재컴파일된 산출물을 함께 포함** (`--check`로 확인)
3. 대화 데이터를 읽는 새 코드는 `data_loader` 경유 — `import yaml` 톱레벨 금지
4. 새 컨텍스트 yaml 종류를 추가하면: `compile_dialogues.py`의 `KNOWN_CONTEXTS`,
   `stateless.py`의 `_*_CONTEXTS`에 등록
5. 새 컨텍스트 제공 슬롯({name} 류)을 추가하면: `compile_dialogues.py`의
   `CONTEXT_SLOTS`에 등록 (아니면 W2 경고 발생)
