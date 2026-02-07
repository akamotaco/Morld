"""NPC 활동 핸들러 패키지

활동 이름 → 핸들러 함수 매핑을 제공합니다.
각 핸들러는 handle_X(agent, entry) 시그니처를 따릅니다.

새 NPC에 활동 추가 시, 스케줄에 activity 이름만 지정하면
ACTIVITY_HANDLERS를 통해 자동으로 핸들러가 호출됩니다.
"""
from .lights import handle_lights_off
from .chop import handle_chop
from .fish import handle_fish
from .gather import handle_gather_store
from .cook import handle_cook
from .clean import handle_clean
from .scavenge import handle_scavenge

ACTIVITY_HANDLERS = {
    "소등": handle_lights_off,
    "벌목": handle_chop,
    "낚시": handle_fish,
    "채집": handle_gather_store,
    "요리": handle_cook,
    "청소": handle_clean,
    "물자수집": handle_scavenge,
}
