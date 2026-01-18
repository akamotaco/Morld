# assets/items/currency.py - 통화 아이템
#
# 코인 등 스택 가능한 통화 아이템
#
# 사용법:
#   from assets.items.currency import Coin
#   coin_id = get_or_create_item_id("coin")
#   morld.give_item(player_id, coin_id, 10)  # 10코인 지급

from assets.base import Item
from assets.registry import register_item


@register_item
class Coin(Item):
    """
    코인 - 게임 내 기본 통화

    심부름 보상 등으로 획득하며, 상점에서 물건 구매에 사용.
    버리기/넣기 불가능.
    """
    unique_id = "coin"
    name = "코인"
    category = "currency"
    value = 1  # 자체 가치
    actions = []  # 사용 불가 (버리기, 넣기, 장착 등 모두 불가)
    action_props = {
        "drop_floor": 0,  # 버리기 불가
        "put": 0,         # 컨테이너에 넣기 불가
    }
    focus_text = {"default": "금색 동전. 심부름이나 거래에 사용된다."}
