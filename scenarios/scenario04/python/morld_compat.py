# morld_compat.py - S04 morld API 호환 레이어
#
# S04 코드가 사용하는 API 중 C#에 없는 것을 Python에서 래핑.
# 이 모듈을 import하면 morld 모듈에 누락 함수가 추가됨.
#
# 추가되는 API:
# - morld.set_player(unit_id)
# - morld.add_character(unit_id, name, region_id, location_id, x=0)
# - morld.add_object(unit_id, name, region_id, location_id, x=0)
# - morld.get_location_unit_id(region_id, location_id)

import morld


def _install_compat():
    """누락 API를 morld 모듈에 설치"""

    # --- set_player ---
    if not hasattr(morld, 'set_player'):
        def set_player(unit_id):
            """플레이어 유닛 지정"""
            # PlayerSystem에서 사용하는 prop
            morld.set_unit_prop(unit_id, "player", 1)
            print(f"[morld_compat] set_player: {unit_id}")
        morld.set_player = set_player

    # --- add_character ---
    if not hasattr(morld, 'add_character'):
        def add_character(unit_id, name, region_id, location_id, x=0):
            """캐릭터 유닛 추가 (add_unit 래핑)"""
            morld.add_unit(unit_id, name, region_id, location_id, type="male")
            if x:
                morld.set_unit_position(unit_id, x)
        morld.add_character = add_character

    # --- add_object ---
    if not hasattr(morld, 'add_object'):
        def add_object(unit_id, name, region_id, location_id, x=0):
            """오브젝트 유닛 추가 (add_unit 래핑)"""
            morld.add_unit(unit_id, name, region_id, location_id, type="object")
            if x:
                morld.set_unit_position(unit_id, x)
        morld.add_object = add_object

    # --- get_location_unit_id ---
    if not hasattr(morld, 'get_location_unit_id'):
        def get_location_unit_id(region_id, location_id):
            """
            Location의 unit_id 조회.
            Location 정보에서 unit_id를 추출.
            없으면 None.
            """
            info = morld.get_location_info(region_id, location_id)
            if info and "unit_id" in info:
                return info["unit_id"]
            # fallback: location 자체가 unit_id를 가지지 않는 경우
            # prop을 설정할 수 없으므로 None
            return None
        morld.get_location_unit_id = get_location_unit_id

    # --- file I/O (향후, 스텁) ---
    if not hasattr(morld, 'save_file'):
        def save_file(path, content):
            print(f"[morld_compat] save_file stub: {path} ({len(content)} chars)")
        morld.save_file = save_file

    if not hasattr(morld, 'load_file'):
        def load_file(path):
            print(f"[morld_compat] load_file stub: {path}")
            return None
        morld.load_file = load_file

    if not hasattr(morld, 'file_exists'):
        def file_exists(path):
            return False
        morld.file_exists = file_exists


# 모듈 import 시 자동 설치
_install_compat()
