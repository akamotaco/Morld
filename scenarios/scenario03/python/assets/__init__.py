# assets/__init__.py - Asset 시스템 (시나리오03)
from .base import Asset, Unit, Character, Object, Item, Location
from .registry import get_instance_id, get_unique_id, require_instance_id, clear
