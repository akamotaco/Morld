# assets/__init__.py - S04 Asset 패키지
#
# base 클래스와 registry 함수 노출

from .base import Asset, Character, Object, Item
from .registry import (
    register_item,
    register_object,
    register_character,
    instantiate_character,
    instantiate_object,
    get_instance_id,
    get_unique_id,
    get_or_create_item_id,
    clear,
)
