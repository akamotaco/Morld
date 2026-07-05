# test_dialogue_compile.py — 대화 데이터 파이프라인 (yaml 저작 → 빌드타임 컴파일)
#
# 검증:
#   1. yaml 경로와 컴파일본 경로가 동일한 대사를 생성 (동등성)
#   2. 컴파일본 get()이 yaml 파싱 결과와 동일한 dict 반환
#   3. 컴파일러 검증기가 결함(중복 id/pattern 누락/비숫자 bias)을 잡아냄 (catch)
#   4. 로더가 불가능 상황에서 조용히 실패하지 않고 RuntimeError를 냄
import sys
import os
import random
import importlib.util

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _COMMON)


def _load_compiler():
    path = os.path.join(_COMMON, "dialogues", "compile_dialogues.py")
    spec = importlib.util.spec_from_file_location("compile_dialogues", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestEquivalence:
    """yaml 직독과 컴파일본이 같은 rng에서 같은 대사를 내는가."""

    def _gen_pairs(self, fn, *args, **kwargs):
        from engine.dialogue_hybrid import data_loader, stateless
        results = {}
        for forced in (False, True):
            data_loader.FORCE_COMPILED = forced
            data_loader.reset_for_test()
            stateless.clear_cache()
            outs = [fn(*args, rng=random.Random(i), **kwargs) for i in range(10)]
            results[forced] = outs
        data_loader.FORCE_COMPILED = False
        data_loader.reset_for_test()
        stateless.clear_cache()
        return results

    def test_daily_first_meet_identical(self):
        from engine.dialogue_hybrid.stateless import generate_daily_line
        r = self._gen_pairs(generate_daily_line, "proud", "도현", "first_meet")
        assert r[False] == r[True], f"yaml={r[False][:2]} vs compiled={r[True][:2]}"

    def test_daily_greet_identical(self):
        from engine.dialogue_hybrid.stateless import generate_daily_line
        r = self._gen_pairs(generate_daily_line, "proud", "도현", "greet",
                            state={"affinity": 0.3})
        assert r[False] == r[True]

    def test_romance_line_identical(self):
        from engine.dialogue_hybrid.stateless import generate_line
        r = self._gen_pairs(generate_line, "seductive", "밀라", "hug",
                            state={"affinity": 0.5, "arousal": 0.4})
        assert r[False] == r[True]

    def test_reaction_identical(self):
        from engine.dialogue_hybrid.stateless import generate_reaction
        r = self._gen_pairs(generate_reaction, "cold", "시호", "hug", "during",
                            state={"affinity": 0.5})
        assert r[False] == r[True]

    def test_compiled_dict_equals_yaml(self):
        import yaml as _yaml
        import dialogues_compiled as dc
        rel = "characters/도현.yaml"
        src = os.path.join(_COMMON, "dialogues", *rel.split("/"))
        with open(src, encoding="utf-8") as f:
            parsed = _yaml.safe_load(f)
        assert dc.get(rel) == parsed

    def test_compiled_covers_all_yaml(self):
        import dialogues_compiled as dc
        droot = os.path.join(_COMMON, "dialogues")
        count = 0
        for base, _dirs, files in os.walk(droot):
            for fname in files:
                if not fname.endswith(".yaml"):
                    continue
                rel = os.path.relpath(os.path.join(base, fname), droot) \
                    .replace(os.sep, "/")
                assert dc.get(rel) is not None, f"컴파일본에 없음: {rel}"
                count += 1
        assert count == dc.FILE_COUNT, f"yaml {count}개 vs FILE_COUNT {dc.FILE_COUNT}"


class TestValidatorCatches:
    """컴파일러 검증기가 결함을 에러로 잡는가 (조용한 통과 금지)."""

    def setUp(self):
        self.c = _load_compiler()
        self.c.errors.clear()
        self.c.warnings.clear()

    def test_duplicate_id_caught(self):
        self.c._check_templates("f.yaml", "greet", [
            {"id": "x", "pattern": "안녕"},
            {"id": "x", "pattern": "반가워"},
        ], {})
        assert any("중복 template id" in e for e in self.c.errors), self.c.errors

    def test_missing_pattern_caught(self):
        self.c._check_templates("f.yaml", "greet", [{"id": "x"}], {})
        assert any("pattern 누락" in e for e in self.c.errors), self.c.errors

    def test_non_numeric_bias_caught(self):
        self.c._check_templates("f.yaml", "greet", [
            {"id": "x", "pattern": "안녕", "state_bias": {"affinity": "높음"}},
        ], {})
        assert any("숫자가 아님" in e for e in self.c.errors), self.c.errors

    def test_unknown_slot_warned(self):
        self.c._check_intents("f.yaml", {
            "greet": {"templates": [{"id": "x", "pattern": "안녕 {없는슬롯}"}]},
        })
        assert any("없는 slot" in w for w in self.c.warnings), self.c.warnings

    def test_bad_slot_pool_caught(self):
        self.c._check_slots("f.yaml", "greet", {"end": "리스트아님"})
        assert any("list여야 함" in e for e in self.c.errors), self.c.errors


class TestLoaderErrors:
    """로더 실패 모드 — 조용한 빈 대사 대신 특정 가능한 에러."""

    def test_custom_root_without_yaml_raises(self):
        from engine.dialogue_hybrid import data_loader
        from pathlib import Path
        data_loader.FORCE_COMPILED = True
        data_loader.reset_for_test()
        try:
            try:
                data_loader.load_yaml_file(Path("C:/없는/커스텀/루트"),
                                           "characters/x.yaml")
                assert False, "RuntimeError가 나야 함"
            except RuntimeError as e:
                assert "커스텀 root" in str(e) or "기본 dialogues 루트" in str(e)
        finally:
            data_loader.FORCE_COMPILED = False
            data_loader.reset_for_test()

    def test_missing_archetype_file_returns_none_with_default_root(self):
        from engine.dialogue_hybrid import data_loader
        data_loader.FORCE_COMPILED = True
        data_loader.reset_for_test()
        try:
            out = data_loader.load_yaml_file(
                data_loader.default_root(),
                "archetype_dialogues/cheerful/없는컨텍스트.yaml")
            assert out is None  # WARN 로그 + None (호출측 _LINES 폴백 유지)
        finally:
            data_loader.FORCE_COMPILED = False
            data_loader.reset_for_test()
