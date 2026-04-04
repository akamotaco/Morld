# sound.py - S04 소리 시스템 (스텁)
#
# C#에서 GetSoundHeardTexts를 호출하므로 모듈 존재 필요.
# S02의 sound.py 재활용 예정, 현재 최소 인터페이스.


def reset():
    pass


def get_heard_texts(unit_id):
    """해당 유닛이 들은 소리 텍스트 목록"""
    return []


def emit_sound(source_id, sound_type, location=None):
    """소리 발생 (향후 구현)"""
    pass
