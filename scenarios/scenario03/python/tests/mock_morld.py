# mock_morld.py — 공유 mock 재노출 shim (S03)
# 실체: scenarios/common/python/testing/mock_morld.py (전 시나리오 단일본)
import os
import sys

_common = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "common", "python"))
if _common not in sys.path:
    sys.path.append(_common)

from testing.mock_morld import MockMorld as _SharedMockMorld  # noqa: E402


class MockMorld(_SharedMockMorld):
    """S03 테스트 호환 오버라이드.

    공유본과 다른 부분만 유지 — 실 C# API 계약 확인 후 공유본으로 수렴할 것 (TODO):
      - get_current_job: S03 테스트는 큐 선두(jobs[0])를 '현재 작업'으로 가정
        (공유본/S02는 마지막 삽입 job).
      - get_unit_props: 유닛 부재 시 {} 반환 (공유본은 None).
      - add_unit: unit_type 기본값 "object" (S03 world 코드가 생략 호출).
    """

    def get_current_job(self, unit_id):
        jobs = self._jobs.get(unit_id, [])
        return jobs[0] if jobs else None

    def get_unit_props(self, unit_id):
        u = self._units.get(unit_id)
        return dict(u["props"]) if u else {}

    def get_location_info(self, region_id, location_id):
        # S03 테스트는 부재 location에 None을 기대 (공유본은 기본값 dict)
        loc = self._locations.get((region_id, location_id))
        return dict(loc) if loc else None

    def add_unit(self, unit_id, name, region_id, location_id,
                 unit_type="object", actions=None, mood=None,
                 unique_id=None, action_props=None, owner=None, **kwargs):
        super().add_unit(unit_id, name, region_id, location_id, unit_type,
                         actions=actions, mood=mood, unique_id=unique_id,
                         action_props=action_props, owner=owner, **kwargs)
