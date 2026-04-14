# facility.py — S04 마을 시설 존재 체크
#
# Phase 1: 스텁 — 항상 True (chapter_0이 시설을 고정 배치).
# Phase 2(마을 성장): 건설된 시설 목록을 동적으로 관리.
#   - 시작 시: 구호소/정화소/대장간 등 없음
#   - 플레이어가 자원으로 건설 시 등록
#   - 시설 부재 상황에서 관련 로직(구출/치료/정화 등) 자동 비활성화

import morld


# ========================================
# 시설 종류 상수
# ========================================

INFIRMARY = "infirmary"     # 구호소
PURIFIER = "purifier"       # 정화소
SMITHY = "smithy"           # 대장간
SHOP = "shop"               # 잡화점
INN = "inn"                 # 여관
TAVERN = "tavern"           # 술집


# ========================================
# API (Phase 1 스텁 — 항상 True / 기본 장비)
# ========================================

# Phase 1: 테스트/초기 챕터에서 모든 시설 기본 제공
_present = {INFIRMARY, PURIFIER, SMITHY, SHOP, INN, TAVERN}


def reset():
    """챕터 전환 시 리셋. Phase 2에서 시설 건설 상태 로드로 교체 예정."""
    global _present
    _present = {INFIRMARY, PURIFIER, SMITHY, SHOP, INN, TAVERN}


def has(facility: str) -> bool:
    """시설 존재 여부."""
    return facility in _present


def has_infirmary() -> bool:
    """구호소(치료 시설) 존재 여부 — 실신 구출/치료 로직의 게이트."""
    return has(INFIRMARY)


def register(facility: str):
    """시설 등록 (건설 완료 시)."""
    _present.add(facility)


def unregister(facility: str):
    """시설 제거 (파괴/폐쇄 시)."""
    _present.discard(facility)


def get_all() -> set:
    """현재 존재하는 시설 집합 (읽기 전용 복사본)."""
    return set(_present)
