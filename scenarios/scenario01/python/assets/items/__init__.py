# assets/items/__init__.py - 아이템 Asset 모듈

from assets.base import Item

# 아이템 클래스 import
from .keys import RustyKey, SilverKey
from .golden_key import GoldenKeyHead, GoldenKeyBody, GoldenKey
from .notes import Note1, Note2, Note3
from .documents import Diary, OldLetter, StudyMemo

# 모든 아이템 클래스 export
__all__ = [
    'RustyKey', 'SilverKey',
    'GoldenKeyHead', 'GoldenKeyBody', 'GoldenKey',
    'Note1', 'Note2', 'Note3',
    'Diary', 'OldLetter', 'StudyMemo',
]
