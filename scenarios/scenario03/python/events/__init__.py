# events/__init__.py - 이벤트 핸들러 패키지 (시나리오03)
#
# 시나리오02의 이벤트 시스템을 공유하되,
# 시나리오03 전용 이벤트만 등록합니다.
#
# 시나리오02 events/__init__.py와 달리 간소화:
# - 프롤로그/튜토리얼/임무 이벤트만 관리
# - 공유 이벤트 시스템(registry, base)은 시나리오02에서 import

# 시나리오03 이벤트 모듈 (자동 등록)
from . import prologue
from . import tutorial
from . import first_mission
from . import ending
from . import progression
