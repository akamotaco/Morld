# engine/korean.py — 한국어 조사 처리
#
# 받침 판정 및 조사 자동 선택.
# Unicode 한글 음절 블록 기반 표준 알고리즘.
#
# 규칙:
#   - 한글 음절 범위: U+AC00 ~ U+D7A3
#   - 종성 인덱스 = (code - 0xAC00) % 28
#   - 0이면 받침 없음, 1~27이면 받침 있음 (값 8 = 'ㄹ')

_HANGUL_START = 0xAC00
_HANGUL_END = 0xD7A3
_JONGSEONG_RIEUL = 8  # ㄹ


def has_final_consonant(word: str) -> bool:
    """마지막 글자 받침 유무.

    한글: Unicode 공식 기반.
    영문/숫자/기타: 받침 있음으로 간주 (보수적 기본값).
    """
    if not word:
        return False
    last = word[-1]
    code = ord(last)
    if _HANGUL_START <= code <= _HANGUL_END:
        return (code - _HANGUL_START) % 28 != 0
    return True


def _jongseong_index(word: str) -> int:
    """마지막 글자 종성 인덱스. 한글이 아니면 -1."""
    if not word:
        return -1
    last = word[-1]
    code = ord(last)
    if _HANGUL_START <= code <= _HANGUL_END:
        return (code - _HANGUL_START) % 28
    return -1


def 이_가(word: str) -> str:
    return "이" if has_final_consonant(word) else "가"


def 은_는(word: str) -> str:
    return "은" if has_final_consonant(word) else "는"


def 을_를(word: str) -> str:
    return "을" if has_final_consonant(word) else "를"


def 와_과(word: str) -> str:
    return "과" if has_final_consonant(word) else "와"


def 으로_로(word: str) -> str:
    """ㄹ 받침 예외: 받침이 있지만 ㄹ이면 '로'."""
    idx = _jongseong_index(word)
    if idx == -1:
        return "으로"  # 영문/숫자 등: 보수적
    if idx == 0:
        return "로"
    if idx == _JONGSEONG_RIEUL:
        return "로"
    return "으로"


def with_particle(word: str, particle_pair: str) -> str:
    """단어 + 적절한 조사. particle_pair는 '이/가', '은/는', '을/를', '와/과', '으로/로'."""
    mapping = {
        "이/가": 이_가,
        "은/는": 은_는,
        "을/를": 을_를,
        "와/과": 와_과,
        "으로/로": 으로_로,
    }
    fn = mapping.get(particle_pair)
    if fn is None:
        return word
    return word + fn(word)


def reset():
    """모듈 상태 초기화 — pi-world reset 계약 (가변 전역 없음, 규약 준수용)"""
    pass
