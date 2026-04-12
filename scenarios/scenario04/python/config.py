# config.py — S04 시나리오 설정 상수

# 성인 모드 토글
# - True: 성인 컨텐츠 모듈 활성화 (매춘, 야간 습격, 애정 행위, 에로 함정, 조교 등)
# - False: 비성인 모드 (물리적 습격/일반 의뢰 등 대체 컨텐츠로 치환)
#
# 챕터 로드 시점에 확정되며 세션 중 변경 불가.
# 설계: docs/advanced-systems.md §0
ADULT_MODE_ENABLED: bool = True
