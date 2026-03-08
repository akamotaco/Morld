# think/activities/__init__.py - 활동 핸들러 레지스트리 (시나리오03)

from .build_activity import handle_build

ACTIVITY_HANDLERS = {
    "건축": handle_build,
}
