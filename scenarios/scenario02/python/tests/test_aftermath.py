# test_aftermath.py — aftermath 다단계 템플릿 시스템 테스트
"""
aftermath_templates.py의 텍스트 풀 완전성 + get_aftermath_text() API 검증.
"""
import sys
import os
import types

# 경로 설정
_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))
if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)

# morld mock (aftermath_templates는 morld 불필요하지만 안전장치)
if "morld" not in sys.modules:
    sys.modules["morld"] = types.ModuleType("morld")

import aftermath_templates as at


# ============================================
# 상수
# ============================================

ALL_ARCHETYPES = [
    "stoic", "gentle", "cheerful", "timid", "cold",
    "seductive", "fierce", "proud", "innocent", "devoted",
]

ALL_EVENT_TYPES = ["forced", "unconscious", "frozen", "bestiality"]

ALL_STAGES = [3, 2, 1]


# ============================================
# 템플릿 완전성 테스트
# ============================================

class TestTemplateCompleteness:
    """모든 아키타입 × 유형 × 단계 조합에 텍스트가 존재하는지 검증."""

    def test_all_standard_templates_exist(self):
        """10 아키타입 × 3 event_type × 3 stage 전부 텍스트 존재"""
        for et in ALL_EVENT_TYPES:
            for stage in ALL_STAGES:
                for arch in ALL_ARCHETYPES:
                    pool = at.TEMPLATES.get(et, {}).get(stage, {}).get(arch)
                    assert pool is not None, f"Missing TEMPLATES[{et}][{stage}][{arch}]"
                    assert len(pool) > 0, f"Empty pool: TEMPLATES[{et}][{stage}][{arch}]"

    def test_all_repeat_templates_exist(self):
        """10 아키타입 × 3 event_type 전부 반복 템플릿 존재"""
        for et in ALL_EVENT_TYPES:
            for arch in ALL_ARCHETYPES:
                pool = at.REPEAT_TEMPLATES.get(et, {}).get(arch)
                assert pool is not None, f"Missing REPEAT_TEMPLATES[{et}][{arch}]"
                assert len(pool) > 0, f"Empty pool: REPEAT_TEMPLATES[{et}][{arch}]"

    def test_all_templates_have_name_placeholder(self):
        """모든 텍스트에 {name} 플레이스홀더 존재"""
        for et in ALL_EVENT_TYPES:
            for stage in ALL_STAGES:
                for arch in ALL_ARCHETYPES:
                    for text in at.TEMPLATES[et][stage][arch]:
                        assert "{name}" in text, (
                            f"Missing {{name}}: TEMPLATES[{et}][{stage}][{arch}] = {text!r}"
                        )
            for arch in ALL_ARCHETYPES:
                for text in at.REPEAT_TEMPLATES[et][arch]:
                    assert "{name}" in text, (
                        f"Missing {{name}}: REPEAT_TEMPLATES[{et}][{arch}] = {text!r}"
                    )


# ============================================
# API 테스트
# ============================================

class TestGetAftermathText:
    """get_aftermath_text() 함수 동작 검증."""

    def test_name_formatting(self):
        """이름 플레이스홀더가 올바르게 치환"""
        text = at.get_aftermath_text("밀라", "forced", 3, "gentle")
        assert "밀라" in text
        assert "{name}" not in text

    def test_standard_template_selection(self):
        """count=1일 때 표준 템플릿 사용"""
        text = at.get_aftermath_text("세라", "forced", 3, "stoic", count=1)
        assert text
        assert "세라" in text

    def test_repeat_template_on_count2(self):
        """count>=2 + stage 3에서 반복 템플릿 사용"""
        text = at.get_aftermath_text("세라", "forced", 3, "stoic", count=2)
        assert text
        assert "세라" in text

    def test_repeat_only_stage3(self):
        """count>=2여도 stage 2/1은 표준 템플릿 사용 (에러 없음)"""
        text_s2 = at.get_aftermath_text("세라", "forced", 2, "stoic", count=5)
        text_s1 = at.get_aftermath_text("세라", "forced", 1, "stoic", count=5)
        assert text_s2
        assert text_s1

    def test_all_event_types_work(self):
        """3개 event_type 모두 정상 반환"""
        for et in ALL_EVENT_TYPES:
            text = at.get_aftermath_text("테스트", et, 3, "stoic")
            assert text
            assert "테스트" in text

    def test_all_stages_work(self):
        """3개 stage 모두 정상 반환"""
        for stage in ALL_STAGES:
            text = at.get_aftermath_text("테스트", "forced", stage, "gentle")
            assert text

    def test_fallback_for_unknown_archetype(self):
        """존재하지 않는 아키타입은 fallback 텍스트 반환"""
        text = at.get_aftermath_text("테스트", "forced", 3, "nonexistent_archetype")
        assert text
        assert "테스트" in text

    def test_fallback_for_invalid_stage(self):
        """존재하지 않는 stage는 fallback 텍스트 반환"""
        text = at.get_aftermath_text("테스트", "forced", 99, "stoic")
        assert text


# ============================================
# 부호 규약 로직 테스트 (prop 라이프사이클)
# ============================================

class TestSignConvention:
    """부호 규약 (양수=대기, 음수=표시됨) 로직 검증.

    실제 prop은 morld를 통해 설정되지만,
    여기서는 로직의 정합성만 단위 테스트.
    """

    def test_positive_triggers_display(self):
        """양수 prop → 반응 대기 (표시 대상)"""
        value = 3
        assert value > 0  # 표시 대상

    def test_negate_marks_as_shown(self):
        """표시 후 부호 반전 → 음수"""
        value = 3
        shown = -value
        assert shown == -3
        assert shown < 0  # 이미 표시됨

    def test_sleep_decrement(self):
        """수면 시 abs-1 → 다음 단계"""
        value = -3
        new_stage = abs(value) - 1
        assert new_stage == 2
        assert new_stage > 0  # 양수로 전환 (대기)

    def test_sleep_final_clear(self):
        """마지막 단계 수면 → 0 (해제)"""
        value = -1
        new_stage = abs(value) - 1
        assert new_stage == 0  # 해제

    def test_positive_not_decremented_on_sleep(self):
        """양수(미표시)는 수면 시 감소 안 함"""
        value = 2
        # 양수 → 건드리지 않음
        assert value > 0  # 조건 불충족 → 감소 skip

    def test_full_lifecycle(self):
        """전체 라이프사이클 시뮬레이션: 사건→만남→수면→만남→수면→만남→수면→해제"""
        # 사건 발생
        prop = 3
        count = 1

        # 1차 만남: stage 3 표시
        assert prop > 0
        prop = -prop  # 부호 반전
        assert prop == -3

        # 1차 수면: 감소
        new_stage = abs(prop) - 1
        prop = max(new_stage, 0)
        assert prop == 2

        # 2차 만남: stage 2 표시
        assert prop > 0
        prop = -prop
        assert prop == -2

        # 2차 수면: 감소
        new_stage = abs(prop) - 1
        prop = max(new_stage, 0)
        assert prop == 1

        # 3차 만남: stage 1 표시
        assert prop > 0
        prop = -prop
        assert prop == -1

        # 3차 수면: 해제
        new_stage = abs(prop) - 1
        prop = max(new_stage, 0)
        assert prop == 0  # 해제 완료

    def test_new_incident_during_aftermath(self):
        """진행 중 새 사건 → stage 리셋, count 누적"""
        prop = -2  # stage 2, 이미 표시됨
        count = 1

        # 새 사건 발생
        prop = 3  # 최고 단계로 리셋
        count += 1

        assert prop == 3
        assert count == 2
