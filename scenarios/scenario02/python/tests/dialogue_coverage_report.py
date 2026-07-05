# dialogue_coverage_report.py — S02 hybrid 폴백 의존 커버리지 리포트 (U5, §2-5)
#
# S02 는 대화 정책 fixed(동적 생성 차단)를 선언한다. 이 도구는 차단으로
# 대사가 사라지는 지점을 두 축으로 산출한다:
#
#   [정적] 캐릭터별 ROMANCE_REACTIONS 에서 hybrid catch-all
#          (({}, "_generate_dialogue")) 에 의존하는 키 목록
#          + NPC_INITIATIVE_ACTIONS 대비 INITIATIVE_REACTIONS 의 during_ 갭
#   [동적] 기본 정책(fixed+fallback)으로 전체 테스트 스위트를 돌리며
#          실제 hybrid 생성기에 도달한 (캐릭터, action_id, timing) 캡처
#          — 테스트 도달 = 실플레이에서 빈발하는 경로로 간주
#
# 사용법:
#   python tests/dialogue_coverage_report.py            # 리포트 md 재생성
#
# 출력: scenarios/scenario02/docs/dialogue-fallback-coverage.md

import sys
import os
import io

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))
_common_dir = os.path.abspath(os.path.join(_tests_dir, "..", "..", "..", "common", "python"))
_docs_out = os.path.abspath(os.path.join(
    _python_dir, "..", "docs", "dialogue-fallback-coverage.md"))

for p in (_python_dir, _tests_dir):
    if p not in sys.path:
        sys.path.insert(0, p)
if _common_dir not in sys.path:
    sys.path.append(_common_dir)

from mock_morld import MockMorld  # noqa: E402

sys.modules["morld"] = MockMorld()


# ============================================
# 동적 캡처 훅 — hybrid 생성기 도달 기록
# ============================================

_dynamic_hits = {}  # (name, action_id, timing) → count


def _install_capture():
    from engine.dialogue_hybrid import s02_adapter

    orig_line = s02_adapter.LineGenerator.generate
    orig_reaction = s02_adapter.ReactionGenerator.generate

    def line_wrap(self, action_id, state):
        key = (self.name, action_id, "start")
        _dynamic_hits[key] = _dynamic_hits.get(key, 0) + 1
        return orig_line(self, action_id, state)

    def reaction_wrap(self, action_id, timing, state):
        key = (self.name, action_id, timing)
        _dynamic_hits[key] = _dynamic_hits.get(key, 0) + 1
        return orig_reaction(self, action_id, timing, state)

    s02_adapter.LineGenerator.generate = line_wrap
    s02_adapter.ReactionGenerator.generate = reaction_wrap


def _run_suite_captured():
    """전체 S02 스위트를 in-process 실행 (출력은 버퍼로 흡수)"""
    import run_tests
    saved_argv = sys.argv
    saved_stdout = sys.stdout
    sys.argv = ["run_tests.py"]
    sys.stdout = io.StringIO()
    try:
        run_tests.main()
    finally:
        sys.stdout = saved_stdout
        sys.argv = saved_argv


# ============================================
# 정적 분석
# ============================================

def _uses_generate_dialogue(rules):
    """rule 리스트에 '_generate_dialogue' 델리게이트가 포함되는지"""
    if isinstance(rules, str):
        return rules == "_generate_dialogue"
    if not isinstance(rules, list):
        return False
    for item in rules:
        if isinstance(item, tuple) and len(item) == 2:
            _cond, texts = item
            if texts == "_generate_dialogue":
                return True
    return False


def _analyze_character(cls):
    reactions = getattr(cls, "ROMANCE_REACTIONS", None) or {}
    fixed_keys = []
    hybrid_keys = []
    for key in sorted(reactions):
        if _uses_generate_dialogue(reactions[key]):
            hybrid_keys.append(key)
        else:
            fixed_keys.append(key)

    # initiative: NPC_INITIATIVE_ACTIONS 의 액션 대비 during_ rule 커버
    init_actions = set()
    for entry in getattr(cls, "NPC_INITIATIVE_ACTIONS", None) or []:
        if isinstance(entry, dict) and entry.get("action"):
            init_actions.add(entry["action"])
    init_rules = getattr(cls, "INITIATIVE_REACTIONS", None) or {}
    init_gaps = sorted(
        a for a in init_actions
        if f"during_{a}" not in init_rules
    )
    return fixed_keys, hybrid_keys, init_gaps


def main():
    _install_capture()
    print("[report] 전체 스위트 실행 중 (동적 캡처)...")
    _run_suite_captured()
    print(f"[report] hybrid 도달 지점: {len(_dynamic_hits)}종")

    from assets.characters import Sera, Mila, Lina, Yuki, Ella, Faye

    lines = []
    w = lines.append
    w("# S02 hybrid 폴백 의존 커버리지 리포트")
    w("")
    w("> 생성 도구: `python/tests/dialogue_coverage_report.py` (재생성 가능)")
    w("> 배경: [infra-unification-plan-2026-07.md](../../../docs/infra-unification-plan-2026-07.md) §2-5")
    w("")
    w("S02 는 대화 정책 **fixed** 를 선언한다 (`python/__init__.py`) — hybrid")
    w("동적 생성 폴백 3경로(톤 접두사 위임 / `_generate_dialogue` catch-all /")
    w("initiative `during_` 폴백)가 프로덕션에서 차단된다. 아래는 차단으로")
    w("대사가 생략되는 지점의 전수 목록이다. **갭을 메우려면 해당 키에 고정")
    w("rule 을 추가하면 된다** (차단 지점은 런타임에 `[DialoguePolicy]` 로그로도")
    w("키당 1회 출력됨).")
    w("")
    w("동작 보증: 게이트는 대사만 생략하며 흐름은 유지된다 — romance 호출부는")
    w("None 을 조용히 건너뛰고, 접두사 키는 기본 키의 고정 rule 로, 트랜스는")
    w("공용 트랜스 풀로 폴백한다.")
    w("")

    w("## 1. 캐릭터별 ROMANCE_REACTIONS 정적 분석")
    w("")
    w("| 캐릭터 | 고정 rule 키 | hybrid catch-all 키 | initiative during_ 갭 |")
    w("|--------|------------:|--------------------:|----------------------:|")
    details = []
    for cls in (Sera, Mila, Lina, Yuki, Ella, Faye):
        fixed_keys, hybrid_keys, init_gaps = _analyze_character(cls)
        w(f"| {cls.name} | {len(fixed_keys)} | {len(hybrid_keys)} | {len(init_gaps)} |")
        details.append((cls.name, hybrid_keys, init_gaps))
    w("")
    w("hybrid catch-all 키 = 고정 rule 이 일부 있어도 최종 기본값이")
    w("`_generate_dialogue` 인 키. fixed 정책에서는 앞선 고정 rule 미매치 시")
    w("대사가 생략된다.")
    w("")

    w("## 2. hybrid catch-all 키 상세 (캐릭터별)")
    w("")
    for name, hybrid_keys, init_gaps in details:
        w(f"### {name}")
        w("")
        if hybrid_keys:
            w("- catch-all 의존: " + ", ".join(f"`{k}`" for k in hybrid_keys))
        else:
            w("- catch-all 의존 없음")
        if init_gaps:
            w("- initiative 갭: " + ", ".join(f"`{a}`" for a in init_gaps))
        w("")

    w("## 3. 동적 캡처 — 테스트 스위트에서 실제 hybrid 도달 지점")
    w("")
    w("기본 정책(fixed+fallback)으로 전체 스위트를 돌렸을 때 hybrid 생성기에")
    w("실제 도달한 지점. **실플레이에서 빈발하는 경로이므로 고정 rule 채움")
    w("우선순위가 가장 높다.**")
    w("")
    w("> 참고: 동적 캡처는 테스트 커버리지 기준의 **하한선**이다 — e2e 테스트")
    w("> 다수가 생성기를 스텁으로 대체하므로, 실플레이 노출 범위는 §1·§2 의")
    w("> 정적 목록 전체로 간주할 것.")
    w("")
    if _dynamic_hits:
        w("| 캐릭터 | action_id | timing | 도달 횟수 |")
        w("|--------|-----------|--------|----------:|")
        for (name, action_id, timing), count in sorted(
                _dynamic_hits.items(), key=lambda kv: -kv[1]):
            w(f"| {name} | `{action_id}` | {timing} | {count} |")
    else:
        w("(도달 없음)")
    w("")
    w("## 4. 갭 채움 가이드")
    w("")
    w("1. §3 (테스트 도달) 키부터: 해당 캐릭터 `ROMANCE_REACTIONS[key]` 의")
    w("   `({}, \"_generate_dialogue\")` 를 고정 텍스트 rule 로 교체하거나 앞에 추가")
    w("2. 톤 접두사(forced_/trance_/ecstasy_) 키는 개별 rule 대신 기본 키의")
    w("   고정 rule 이 폴백으로 쓰인다 — 톤 구분이 필요할 때만 접두사 키를 명시")
    w("3. initiative 갭은 `INITIATIVE_REACTIONS[\"during_<action>\"]` 추가")
    w("")

    with io.open(_docs_out, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[report] 작성 완료: {_docs_out}")


if __name__ == "__main__":
    main()
