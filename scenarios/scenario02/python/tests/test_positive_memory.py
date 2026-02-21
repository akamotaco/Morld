# test_positive_memory.py — 긍정 기억 템플릿 시스템 테스트
"""
positive_memory_templates.py의 텍스트 풀 완전성 + get_positive_memory_text() API 검증.
"""
import sys
import os
import types

# 경로 설정
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))
if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)

# morld mock
if "morld" not in sys.modules:
    sys.modules["morld"] = types.ModuleType("morld")

import positive_memory_templates as pm


# ============================================
# 상수
# ============================================

ALL_ARCHETYPES = [
    "stoic", "gentle", "cheerful", "timid", "cold",
    "seductive", "fierce", "proud", "innocent", "devoted",
]

ALL_GIFT_TYPES = ["gift_favorite", "gift_liked", "gift_normal"]


# ============================================
# 템플릿 완전성 테스트
# ============================================

class TestTemplateCompleteness:
    """모든 gift_type × archetype 조합에 텍스트가 존재하는지 검증."""

    def test_all_templates_exist(self):
        """3 gift_type × 10 archetype 전부 텍스트 존재"""
        for gt in ALL_GIFT_TYPES:
            for arch in ALL_ARCHETYPES:
                pool = pm.TEMPLATES.get(gt, {}).get(arch)
                assert pool is not None, f"Missing TEMPLATES[{gt}][{arch}]"
                assert len(pool) > 0, f"Empty pool: TEMPLATES[{gt}][{arch}]"

    def test_all_templates_have_name_placeholder(self):
        """모든 텍스트에 {name} 플레이스홀더 존재"""
        for gt in ALL_GIFT_TYPES:
            for arch in ALL_ARCHETYPES:
                for text in pm.TEMPLATES[gt][arch]:
                    assert "{name}" in text, (
                        f"Missing {{name}}: TEMPLATES[{gt}][{arch}] = {text!r}"
                    )

    def test_favorite_templates_have_item_placeholder(self):
        """gift_favorite 텍스트에 {item} 플레이스홀더 존재"""
        for arch in ALL_ARCHETYPES:
            for text in pm.TEMPLATES["gift_favorite"][arch]:
                assert "{item}" in text, (
                    f"Missing {{item}}: TEMPLATES[gift_favorite][{arch}] = {text!r}"
                )

    def test_favorite_has_multiple_variants(self):
        """gift_favorite는 아키타입당 2개 이상 변형"""
        for arch in ALL_ARCHETYPES:
            pool = pm.TEMPLATES["gift_favorite"][arch]
            assert len(pool) >= 2, (
                f"TEMPLATES[gift_favorite][{arch}] has only {len(pool)} variant(s)"
            )


# ============================================
# API 테스트
# ============================================

class TestGetPositiveMemoryText:
    """get_positive_memory_text() 함수 동작 검증."""

    def test_name_formatting(self):
        """이름 플레이스홀더가 올바르게 치환"""
        text = pm.get_positive_memory_text("밀라", "gift_favorite", "gentle", "사냥활")
        assert "밀라" in text
        assert "{name}" not in text

    def test_item_formatting(self):
        """아이템 플레이스홀더가 올바르게 치환 (favorite)"""
        text = pm.get_positive_memory_text("세라", "gift_favorite", "stoic", "사냥활")
        assert "사냥활" in text
        assert "{item}" not in text

    def test_item_none_fallback(self):
        """item_name=None → '선물'로 대체"""
        text = pm.get_positive_memory_text("세라", "gift_favorite", "stoic", None)
        assert "선물" in text

    def test_all_gift_types_work(self):
        """3개 gift_type 모두 정상 반환"""
        for gt in ALL_GIFT_TYPES:
            text = pm.get_positive_memory_text("테스트", gt, "stoic", "아이템")
            assert text
            assert "테스트" in text

    def test_all_archetypes_work(self):
        """10개 아키타입 모두 정상 반환"""
        for arch in ALL_ARCHETYPES:
            text = pm.get_positive_memory_text("테스트", "gift_liked", arch)
            assert text
            assert "테스트" in text

    def test_fallback_for_unknown_archetype(self):
        """존재하지 않는 아키타입은 fallback 텍스트 반환"""
        text = pm.get_positive_memory_text("테스트", "gift_favorite", "nonexistent", "검")
        assert text
        assert "테스트" in text

    def test_fallback_for_unknown_memory_type(self):
        """존재하지 않는 memory_type은 fallback 텍스트 반환"""
        text = pm.get_positive_memory_text("테스트", "unknown_type", "stoic")
        assert text
        assert "테스트" in text
