# assets/locations/toilet.py - 화장실

import morld
import ui
from assets.base import Location, Object
from assets.objects.grounds import GroundTile
from assets.objects.furniture import WallLamp


class Toilet(Object):
    """
    변기 - 배변 행위 가능
    """
    unique_id = "toilet"
    name = "변기"
    actions = ["call:use:사용하기", "call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    props = {"action:toilet": 1}
    focus_text = {"default": "낡지만 깨끗하게 관리된 변기."}

    def look(self):
        """변기 살펴보기"""
        yield ui.dialog("깨끗하게 관리된 변기다. 사용하는 데 문제없어 보인다.")
        morld.advance_time_des(1 * 60_000)

    def use(self):
        """변기 사용 (배변)"""
        player_id = morld.get_player_id()

        # 배변욕 확인 (life.md 욕구 시스템 미구현 시 기본 동작)
        need = morld.get_unit_prop(player_id, "욕구:배변") or 0

        if need < 20:
            yield ui.dialog("지금은 볼일이 없다.")
            return

        yield ui.dialog([
            "...",
            "볼일을 마쳤다."
        ])

        # 배변욕 해소
        try:
            import needs
            needs.set_excretion(player_id, 0)
        except ImportError:
            morld.set_unit_prop(player_id, "욕구:배변", 0)
        morld.advance_time_des(5 * 60_000)


class PortableToilet(Object):
    """
    간이 화장실 - 은신처 등에 설치된 임시 변기
    """
    unique_id = "portable_toilet"
    name = "간이 화장실"
    actions = ["call:use:사용하기", "call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    props = {"action:toilet": 1}
    focus_text = {"default": "양동이와 판자로 만든 간이 화장실. 없는 것보다는 낫다."}

    def look(self):
        """간이 화장실 살펴보기"""
        yield ui.dialog("양동이 위에 판자를 얹어 만든 간이 화장실. 비위가 약하면 힘들겠지만, 용도는 충분히 해낸다.")
        morld.advance_time_des(1 * 60_000)

    def use(self):
        """간이 화장실 사용 (배변)"""
        player_id = morld.get_player_id()

        need = morld.get_unit_prop(player_id, "욕구:배변") or 0

        if need < 20:
            yield ui.dialog("지금은 볼일이 없다.")
            return

        yield ui.dialog([
            "...",
            "볼일을 마쳤다. 환경은 열악하지만 해결은 됐다."
        ])

        try:
            import needs
            needs.set_excretion(player_id, 0)
        except ImportError:
            morld.set_unit_prop(player_id, "욕구:배변", 0)
        morld.advance_time_des(5 * 60_000)


class ToiletRoom(Location):
    """화장실 Location - 인스턴스 생성 시 unique_id와 describe_text 지정"""
    name = "화장실"
    is_indoor = True
    stay_duration = 0
    length = 150  # Pi-World: 화장실 (개인 공간)

    # life.md 연동용 (미래 구현)
    activities = ["배변"]
    activity_capacity = {"배변": 1}  # 1명씩만

    def __init__(self, unique_id: str, description: str):
        super().__init__()
        self.unique_id = unique_id
        self.describe_text = {"default": description}

    def instantiate(self, location_id: int, region_id: int):
        """화장실 생성"""
        super().instantiate(location_id, region_id)
        self.add_ground(GroundTile())
        self.add_object(Toilet(), x=15)  # 중앙
        self.add_object(WallLamp(), x=90)
