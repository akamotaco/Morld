# mock_morld.py — 공유 mock 재노출 shim
# 실체: scenarios/common/python/testing/mock_morld.py (전 시나리오 단일본)
# 이 파일은 기존 `from mock_morld import MockMorld` import 경로 호환용.
import os
import sys

_common = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "common", "python"))
if _common not in sys.path:
    sys.path.append(_common)

from testing.mock_morld import MockMorld as _SharedMockMorld  # noqa: E402


class MockMorld(_SharedMockMorld):
    """S02 테스트 호환 오버라이드.

    S02 레거시 테스트는 '유닛 1 = 주인공(플레이어)'를 광범위하게 가정한다
    (register_unit(1, name="주인공") 30+ 지점). S02는 항상 플레이어가 존재하는
    시나리오이므로 기본 player_id=1을 유지한다.
    공유본은 실 C# 계약(미등록 시 0, add_unit(unique_id="player") 시 설정)을 따른다.
    """

    def reset(self):
        super().reset()
        self._player_id = 1
