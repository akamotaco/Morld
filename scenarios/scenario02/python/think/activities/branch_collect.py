"""난방 연료 수집 활동 핸들러

나뭇가지를 나무에서 주워 모아서 material 저장소에 보관하는 활동.
연료수집(fuel.py)이 열원에 직접 장전하는 것과 달리, 보관소에 비축하는 역할.
"""
from .resource_activity import handle_resource_activity


def _check_need(agent):
    return (agent._check_storage_need("material", "branch", 6)
            or agent._check_storage_need("material", "log", 3))


def _resolve_target(agent):
    from .helpers import resolve_branch_tree
    return resolve_branch_tree(agent, cross_region=False)


def _do_work(agent, target):
    from assets.objects import get_instance
    obj_id = target.get("object_id")
    if obj_id:
        obj = get_instance(obj_id)
        if obj and hasattr(obj, "npc_gather_branch"):
            for _ in range(3):
                if not obj.npc_gather_branch(agent.unit_id):
                    break


_BRANCH_CONFIG = {
    "activity_name": "난방 연료 수집",
    "check_need": _check_need,
    "resolve_target": _resolve_target,
    "do_work": _do_work,
    "action_key": "gather_branch",
    "work_label": "나뭇가지 줍기",
    "store_categories": ["material"],
    "store_resolve": ["material"],
    "store_label": "재료 저장",
}


def handle_branch_collect(agent, entry):
    """난방 연료 수집: 나무 탐색 → 나뭇가지 줍기 → 저장소에 보관"""
    handle_resource_activity(agent, entry, _BRANCH_CONFIG)
