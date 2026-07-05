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

from testing.mock_morld import MockMorld  # noqa: E402,F401
