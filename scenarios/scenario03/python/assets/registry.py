"""Asset 레지스트리 (시나리오03 최소 구현)"""

# unique_id -> instance_id mapping
_instance_map = {}
# instance_id -> unique_id mapping
_reverse_map = {}


def register_instance(unique_id, instance_id):
    _instance_map[unique_id] = instance_id
    _reverse_map[instance_id] = unique_id


def get_instance_id(unique_id):
    return _instance_map.get(unique_id)


def get_unique_id(instance_id):
    return _reverse_map.get(instance_id)


def require_instance_id(unique_id):
    result = _instance_map.get(unique_id)
    if result is None:
        raise KeyError(f"Instance not found: {unique_id}")
    return result


def get_or_create_item_id(unique_id):
    return _instance_map.get(unique_id)


def clear():
    _instance_map.clear()
    _reverse_map.clear()
