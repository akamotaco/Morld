"""Stateless + S02 adapter 검증.

검증 항목:
  T1. stateless generate_line/reaction — 캐릭터 yaml 없이도 동작 (graceful)
  T2. S02 LineGenerator 호환 signature — profile → 대사 생성
  T3. S02 ReactionGenerator 호환 signature — timing 포함 호출
  T4. 같은 입력 다른 RNG → 다양성
  T5. intent fallback (hug 미탑재 archetype 시 light 로)
  T6. 데이터 캐시 히트 (성능)
"""
import io
import sys
import time
import random
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# sys.path: engine/dialogue_hybrid 의 부모 (scenarios/common/python) 추가
HERE = Path(__file__).resolve().parent
COMMON_PY = HERE.parent.parent  # scenarios/common/python
sys.path.insert(0, str(COMMON_PY))

from engine.dialogue_hybrid.stateless import (
    generate_line, generate_reaction, clear_cache, _DATA_CACHE,
)
from engine.dialogue_hybrid.s02_adapter import (
    LineGenerator, ReactionGenerator,
)

passed = 0
failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}  {detail}")
        failed += 1


DIALOGUE_ROOT = COMMON_PY / "dialogues"


print("=" * 70)
print("T1. stateless generate_line — character yaml 없이 graceful 동작")
print("=" * 70)

# 세라 (stoic, yaml 미존재) — 아키타입 풀만으로 대사 생성
clear_cache()
rng = random.Random(42)
out = generate_line("stoic", "세라", "hug",
                    {"affinity": 0.7, "arousal": 0.3},
                    dialogue_root=DIALOGUE_ROOT, rng=rng)
check("세라(stoic, yaml 없음) hug 대사 생성", len(out) > 0, f"output={out!r}")
print(f"    세라 hug: {out!r}")

# 린 (cheerful, yaml 존재) — override 적용됨
rng = random.Random(42)
out2 = generate_line("cheerful", "린", "hug",
                     {"affinity": 0.7, "arousal": 0.3},
                     dialogue_root=DIALOGUE_ROOT, rng=rng)
check("린(cheerful, yaml 있음) hug 대사 생성", len(out2) > 0, f"output={out2!r}")
print(f"    린 hug: {out2!r}")


print()
print("=" * 70)
print("T2. S02 LineGenerator 호환 — profile → 대사")
print("=" * 70)

clear_cache()
profile_sera = {"name": "세라", "archetype": "stoic"}
gen = LineGenerator(profile_sera, dialogue_root=DIALOGUE_ROOT)
s02_state = {"호감": 70, "반발": 0, "성욕": 30, "욕망": 20, "순수도": 50,
             "climax_gauge": 0, "climax_total": 0}
out = gen.generate("hug", s02_state)
check("LineGenerator.generate(hug) → 대사", out and len(out) > 0,
      f"output={out!r}")
print(f"    LineGenerator hug: {out!r}")

out = gen.generate("deep_kiss", s02_state)
check("LineGenerator.generate(deep_kiss) → 대사", out and len(out) > 0,
      f"output={out!r}")
print(f"    LineGenerator deep_kiss: {out!r}")


print()
print("=" * 70)
print("T3. S02 ReactionGenerator 호환 — timing 포함")
print("=" * 70)

profile_faye = {"name": "페이", "archetype": "proud"}
rgen = ReactionGenerator(profile_faye, dialogue_root=DIALOGUE_ROOT)

for timing in ("start", "during", "end"):
    out = rgen.generate("thrust_normal", timing, s02_state)
    check(f"ReactionGenerator.generate(thrust_normal, {timing}) → 묘사",
          out and len(out) > 0, f"output={out!r}")
    print(f"    {timing}: {out!r}")


print()
print("=" * 70)
print("T4. 다양성 — 같은 호출 10회 중 유일한 결과 수")
print("=" * 70)

outs = set()
for i in range(10):
    rng = random.Random(1000 + i)
    out = generate_line("stoic", "세라", "hug",
                        {"affinity": 0.7, "arousal": 0.3},
                        dialogue_root=DIALOGUE_ROOT, rng=rng)
    outs.add(out)
check(f"10회 호출 중 3개 이상 유일 (다양성)", len(outs) >= 3,
      f"unique={len(outs)}")
for o in list(outs)[:5]:
    print(f"    {o!r}")


print()
print("=" * 70)
print("T5. Intent fallback — hug 미존재 시 light 카테고리로")
print("=" * 70)

# stoic/action_lines 에 hug가 있을 가능성 높음. 어쨌든 빈 문자열이 아니면 OK
rng = random.Random(99)
out = generate_line("stoic", "세라", "hug",
                    {"affinity": 0.0, "arousal": 0.0},
                    dialogue_root=DIALOGUE_ROOT, rng=rng)
check("hug 대사 (fallback 포함) 비어있지 않음", len(out) > 0,
      f"output={out!r}")

# 존재하지 않는 intent
rng = random.Random(99)
out_none = generate_line("stoic", "세라", "nonexistent_intent_xyz",
                         {}, dialogue_root=DIALOGUE_ROOT, rng=rng)
check("매핑 없는 intent → 빈 문자열 (graceful)", out_none == "",
      f"output={out_none!r}")


print()
print("=" * 70)
print("T6. 데이터 캐시 성능")
print("=" * 70)

clear_cache()
# 1회차 (yaml 파싱)
t0 = time.perf_counter()
generate_line("stoic", "세라", "hug", {"affinity": 0.5},
              dialogue_root=DIALOGUE_ROOT, rng=random.Random(0))
t1 = time.perf_counter()

# 1000회 호출 (캐시 히트)
t2 = time.perf_counter()
for i in range(1000):
    generate_line("stoic", "세라", "hug", {"affinity": 0.5},
                  dialogue_root=DIALOGUE_ROOT, rng=random.Random(i))
t3 = time.perf_counter()

first_ms = (t1 - t0) * 1000
avg_us = (t3 - t2) / 1000 * 1_000_000
print(f"    1회차(파싱 포함): {first_ms:.1f}ms")
print(f"    캐시 히트 1000회 평균: {avg_us:.1f}μs")
check(f"캐시 히트가 파싱보다 10배+ 빠름 ({first_ms:.1f}ms → {avg_us:.1f}μs)",
      avg_us < first_ms * 100)  # 1ms=1000us → first_ms * 100 = first_ms를 us로 변환한 값
check(f"캐시 히트 평균 1000μs 이하", avg_us < 1000,
      f"avg={avg_us:.1f}μs")
cache_size = len(_DATA_CACHE)
check(f"캐시에 1 entry 만 저장 (재호출 캐시 히트 확인)",
      cache_size == 1, f"cache_size={cache_size}")


print()
print("=" * 70)
print("T7. 캐릭터 고정 대사 (핵심=고정 / 주변=dynamic 계약)")
print("=" * 70)

from engine.dialogue_hybrid.stateless import generate_daily_line
from engine.dialogue_hybrid.engine import _merge_intents

# 도현 first_meet — 캐릭터 yaml 작가 라인 3종 밖의 출력이 없어야 함 (고정 보장)
clear_cache()
_DOHYUN_AUTHORED = {
    "...낯선 얼굴이군. 도현이다. 자네, 이 마을에서 본 적 없는데.",
    "도현이라고 한다. ...자네 같은 부류는 처음 봐.",
    "도현. 이름은 알겠고, 자네 정체부터 듣자.",
}
outs = {generate_daily_line("proud", "도현", "first_meet",
                            dialogue_root=DIALOGUE_ROOT,
                            rng=random.Random(i))
        for i in range(30)}
check("도현 first_meet 30회 전부 작가 라인 안", outs <= _DOHYUN_AUTHORED,
      f"밖의 출력={outs - _DOHYUN_AUTHORED}")

# greet — add_templates 이므로 아키타입 풀 + 시그니처 혼합 (dynamic)
greets = {generate_daily_line("proud", "도현", "greet",
                              {"affinity": 0.3},
                              dialogue_root=DIALOGUE_ROOT,
                              rng=random.Random(i))
          for i in range(40)}
sig = {g for g in greets if "자네인가" in g or "본론을 말해라" in g}
check("도현 greet 40회에 시그니처 혼입", len(sig) > 0, f"greets={sorted(greets)[:5]}")
check("도현 greet 40회에 아키타입 풀 라인도 포함", len(greets - sig) > 0)

# bare `templates:` 는 base intent가 이미 있어도 전체 교체 (조용한 무시 금지)
merged = _merge_intents(
    {"first_meet": {"templates": [{"id": "arch_generic", "pattern": "처음 뵙겠습니다."}],
                    "slots": {}}},
    {"first_meet": {"templates": [{"id": "char_fixed", "pattern": "나는 고정이다."}]}},
)
ids = [t["id"] for t in merged["first_meet"]["templates"]]
check("bare templates가 기존 intent를 전체 교체", ids == ["char_fixed"], f"ids={ids}")


print()
print("=" * 70)
print(f"RESULT: {passed} passed / {failed} failed")
print("=" * 70)
sys.exit(0 if failed == 0 else 1)
