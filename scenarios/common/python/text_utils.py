# text_utils.py - 공통 텍스트 유틸리티
#
# 모노스페이스 폰트 기반 문자 폭 계산.
# D2Coding: 한글=2칸, 영문=1칸.


def char_width(ch):
    """모노스페이스 폰트에서 문자 표시 폭 (한글=2, 그 외=1)"""
    cp = ord(ch)
    if (0xAC00 <= cp <= 0xD7AF or   # 한글 음절
        0x3000 <= cp <= 0x303F or   # CJK 기호
        0x3040 <= cp <= 0x309F or   # 히라가나
        0x30A0 <= cp <= 0x30FF or   # 카타카나
        0x4E00 <= cp <= 0x9FFF or   # CJK 통합 한자
        0xFF00 <= cp <= 0xFFEF):    # 전각
        return 2
    return 1


def str_width(s):
    """문자열 표시 폭 (한글=2칸, 영문=1칸)"""
    return sum(char_width(ch) for ch in s)


def truncate_to_width(s, max_width):
    """표시 폭 기준으로 문자열 잘라내기"""
    w = 0
    for i, ch in enumerate(s):
        cw = char_width(ch)
        if w + cw > max_width:
            return s[:i]
        w += cw
    return s
