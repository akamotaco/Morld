# assets/items/keys.py - 열쇠류 (녹슨 열쇠, 은열쇠)

from assets.base import Item


class RustyKey(Item):
    """녹슨 열쇠"""
    unique_id = "rusty_key"
    name = "녹슨 열쇠"
    passive_props = {"녹슨열쇠": 1}
    equip_props = {}
    value = 0
    actions = ["take@container"]


class SilverKey(Item):
    """은열쇠"""
    unique_id = "silver_key"
    name = "은열쇠"
    passive_props = {"은열쇠": 1}
    equip_props = {}
    value = 0
    actions = ["take@container"]
