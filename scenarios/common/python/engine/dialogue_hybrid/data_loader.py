# data_loader.py — 대화 yaml 데이터 로드 (yaml 직독 ↔ 컴파일본 2단 폴백)
"""
로드 순서:
  1. pyyaml import 가능 (CPython 개발/테스트) → yaml 파일 직독. 항상 최신 소스 반영.
  2. pyyaml 없음 (SharpPy 프로덕션)      → `dialogues_compiled` 패키지(빌드 산출물) 사용.
     산출물 생성: `python scenarios/common/python/dialogues/compile_dialogues.py`
     문서: docs/dialogue-data-pipeline.md

에러 정책 (catch 가능성 우선):
  - 두 경로 모두 불가 → RuntimeError (조치 방법 포함 메시지). 조용한 빈 대사 금지.
  - yaml 파싱 실패     → "[dialogue_data] ERROR ..." 로그 + None 반환 (해당 파일만 격리,
                         호출측 _LINES 폴백 유지). 로그가 진단 단서.
  - 컴파일본에 없는 파일 요청 → "[dialogue_data] WARN ..." 로그 + None
                         (yaml 신규 추가 후 재컴파일 누락의 대표 증상).
  - 기본 루트가 아닌 커스텀 root + pyyaml 없음 → RuntimeError (컴파일본은 기본 루트만 커버).

테스트 훅:
  FORCE_COMPILED=True 로 두면 pyyaml이 있어도 컴파일본 경로를 사용 (동등성 테스트용).
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional

# 테스트/진단용 스위치 — True면 yaml이 있어도 컴파일본 사용
FORCE_COMPILED = False

_yaml_mod = None
_yaml_checked = False
_compiled_mod = None
_compiled_checked = False
_notice_printed = False


def default_root() -> Path:
    """dialogue_hybrid 패키지 기준 dialogues 루트 (= 컴파일본이 커버하는 루트)."""
    return Path(__file__).resolve().parent.parent.parent / "dialogues"


def _get_yaml():
    global _yaml_mod, _yaml_checked
    if not _yaml_checked:
        _yaml_checked = True
        try:
            import yaml as _y
            _yaml_mod = _y
        except ImportError:
            _yaml_mod = None
    return _yaml_mod


def _get_compiled():
    global _compiled_mod, _compiled_checked, _notice_printed
    if not _compiled_checked:
        _compiled_checked = True
        try:
            import dialogues_compiled as _dc
            _compiled_mod = _dc
            if not _notice_printed:
                _notice_printed = True
                print("[dialogue_data] compiled 데이터 사용 (files="
                      + str(getattr(_dc, "FILE_COUNT", "?"))
                      + ", source_hash=" + str(getattr(_dc, "SOURCE_HASH", "?"))[:12]
                      + ")")
        except ImportError:
            _compiled_mod = None
    return _compiled_mod


def load_yaml_file(root: Path, rel: str) -> Optional[Dict[str, Any]]:
    """dialogues 루트 기준 상대 경로(rel, posix 슬래시)의 파싱된 dict 반환.

    파일/데이터 없음 → None (호출측이 '해당 캐릭터/컨텍스트 없음'으로 처리).
    """
    use_yaml = (_get_yaml() is not None) and not FORCE_COMPILED
    if use_yaml:
        path = root / rel
        if not path.exists():
            return None
        try:
            return _yaml_mod.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as e:  # 파싱 실패는 해당 파일만 격리 + 진단 로그
            print(f"[dialogue_data] ERROR yaml 파싱 실패: {rel}: {e}")
            return None

    # ---- 컴파일본 경로 ----
    dc = _get_compiled()
    if dc is None:
        raise RuntimeError(
            "[dialogue_data] pyyaml 도 dialogues_compiled 도 없음 — 대화 데이터를 "
            "로드할 수 없습니다. CPython에서 "
            "`python scenarios/common/python/dialogues/compile_dialogues.py` 를 "
            "실행해 컴파일본을 생성하세요. (docs/dialogue-data-pipeline.md)")

    if Path(root).resolve() != default_root().resolve():
        raise RuntimeError(
            f"[dialogue_data] 컴파일본은 기본 dialogues 루트만 커버합니다 — "
            f"커스텀 root({root})는 pyyaml 환경에서만 사용 가능.")

    data = dc.get(rel)
    if data is None and not rel.startswith("characters/"):
        # 캐릭터 yaml 부재는 정상(아키타입만 사용). 그 외 부재는 재컴파일 누락 의심.
        print(f"[dialogue_data] WARN compiled 데이터에 없음: {rel} — "
              f"yaml 추가/이동 후 compile_dialogues.py 재실행 필요 여부 확인")
    return data


def reset_for_test() -> None:
    """테스트용: import 캐시 리셋 (FORCE_COMPILED 토글 후 호출)."""
    global _yaml_checked, _compiled_checked, _yaml_mod, _compiled_mod
    _yaml_checked = False
    _compiled_checked = False
    _yaml_mod = None
    _compiled_mod = None
