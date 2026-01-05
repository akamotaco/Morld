# assets/items/tools.py - 도구 아이템
#
# 사용법:
#   from assets.items.tools import Torch, Rope
#   torch = Torch()
#   torch.instantiate(item_id)

from assets.base import Item


# ========================================
# 기타 도구
# ========================================

class Torch(Item):
    unique_id = "torch"
    name = "횃불"
    passive_props = {}
    equip_props = {"밝기": 3}
    value = 5
    actions = ["take@container", "use@inventory", "equip@inventory"]


class Rope(Item):
    unique_id = "rope"
    name = "밧줄"
    passive_props = {}
    equip_props = {}
    value = 8
    actions = ["take@container", "use@inventory"]
