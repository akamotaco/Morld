# assets/objects/__init__.py - 오브젝트 Asset 모듈

from assets import registry

# 개별 오브젝트 모듈 (장소별 분류)
from . import basement       # 지하실: old_box, power_panel
from . import storage        # 창고: shelf, old_cabinet
from . import living_room    # 거실: fireplace, sofa_cushion
from . import kitchen        # 주방: refrigerator, cupboard
from . import bedroom        # 침실: bed_under, vanity_drawer
from . import study          # 서재: safe, desk_drawer
from . import corridor       # 복도: picture_frame, grandfather_clock, umbrella_stand, study_door
from . import stairs         # 계단: broken_step, stair_window
from . import entrance       # 정문 홀: front_door


def register_all():
    """모든 오브젝트 Asset 등록"""
    basement.register()
    storage.register()
    living_room.register()
    kitchen.register()
    bedroom.register()
    study.register()
    corridor.register()
    stairs.register()
    entrance.register()
    print("[assets.objects] All object assets registered")


# 스크립트 함수 export (script: 액션에서 호출됨)
# 지하실
examine_old_box = basement.examine_old_box
toggle_switch = basement.toggle_switch

# 창고
examine_shelf = storage.examine_shelf
unlock_cabinet = storage.unlock_cabinet

# 거실
examine_fireplace = living_room.examine_fireplace
examine_sofa = living_room.examine_sofa

# 주방
examine_refrigerator = kitchen.examine_refrigerator
unlock_cupboard = kitchen.unlock_cupboard

# 침실
examine_bed = bedroom.examine_bed
open_vanity_drawer = bedroom.open_vanity_drawer

# 서재
open_safe = study.open_safe
examine_desk = study.examine_desk

# 복도
examine_picture = corridor.examine_picture
examine_clock = corridor.examine_clock
examine_umbrella = corridor.examine_umbrella
unlock_study_door = corridor.unlock_study_door
input_study_digit = corridor.input_study_digit
verify_study_password = corridor.verify_study_password

# 계단
examine_step = stairs.examine_step
examine_window = stairs.examine_window

# 정문
escape = entrance.escape
show_ending = entrance.show_ending

# 비밀번호 시스템용 오브젝트 정보
PASSWORD_OBJECTS = {
    "vanity_drawer": bedroom,
    "safe": study,
}
