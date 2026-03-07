"""NPC 활동 핸들러 패키지

활동 이름 → 핸들러 함수 매핑을 제공합니다.
각 핸들러는 handle_X(agent, entry) 시그니처를 따릅니다.

새 NPC에 활동 추가 시, 스케줄에 activity 이름만 지정하면
ACTIVITY_HANDLERS를 통해 자동으로 핸들러가 호출됩니다.
"""
from .lights import handle_lights_off, handle_lights_on
from .chop import handle_chop, handle_chop_hobby
from .fish import handle_fish, handle_fish_hobby
from .gather import handle_gather_store, handle_gather_hobby
from .cook import handle_cook
from .clean import handle_clean
from .scavenge import handle_scavenge
from .garden_activity import handle_garden
from .fuel import handle_fuel
from .branch_collect import handle_branch_collect
from .craft import handle_craft
from .fuel_load import handle_fuel_load
from .build_activity import handle_build
from .inspect import handle_inspect

ACTIVITY_HANDLERS = {
    "소등": handle_lights_off,
    "점등": handle_lights_on,
    "벌목": handle_chop,
    "낚시": handle_fish,
    "채집": handle_gather_store,
    "요리": handle_cook,
    "청소": handle_clean,
    "물자수집": handle_scavenge,
    "정원": handle_garden,
    "연료수집": handle_fuel,
    "난방 연료 수집": handle_branch_collect,
    "제작": handle_craft,
    "연료장전": handle_fuel_load,
    "건축": handle_build,
    "점검": handle_inspect,
    "취미낚시": handle_fish_hobby,
    "취미벌목": handle_chop_hobby,
    "취미채집": handle_gather_hobby,
}
