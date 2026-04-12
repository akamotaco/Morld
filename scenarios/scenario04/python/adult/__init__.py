# adult/ — S04 성인 컨텐츠 패키지
#
# 원칙:
# - 비성인 핵심 모듈(party_group, encounter, trust, erosion, morale 등)은
#   이 패키지에 의존하지 않는다 — 단방향 의존.
# - 성인 컨텐츠 트리거 지점(think, encounter 등)에서 adult.is_enabled()를
#   체크한 뒤에만 하위 모듈을 import/호출.
# - 성인 전용 함수 본체는 최상단에서 require_enabled()를 호출해
#   모드 off 상태에서의 오용을 조기 검출.
#
# 설계: docs/advanced-systems.md §0

import config


def is_enabled() -> bool:
    """성인 모드 활성화 여부. 모든 성인 컨텐츠 호출 전 체크."""
    return config.ADULT_MODE_ENABLED


def require_enabled():
    """성인 모드가 꺼져 있으면 즉시 실패.

    성인 전용 함수의 최상단에서 호출. off 상태에서 이 함수에
    도달했다는 것은 호출 측이 is_enabled() 가드를 빠뜨렸다는 의미.
    """
    if not is_enabled():
        raise RuntimeError(
            "Adult content is disabled (config.ADULT_MODE_ENABLED=False). "
            "Check adult.is_enabled() before calling adult module functions."
        )
