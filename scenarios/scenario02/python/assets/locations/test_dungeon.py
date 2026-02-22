# assets/locations/test_dungeon.py — 잊혀진 유적 지역
#
# Location ID (Region 5 내부 ID)
# - 0: 유적 입구 (ruin_entrance)
# - 1: 1층 회랑 (ruin_corridor)
# - 2: 2층 거미굴 (ruin_nest)
# - 3: 3층 기생실 (ruin_parasite_room)
# - 4: 유적 심층 (ruin_boss)

from assets.base import Location


class RuinEntrance(Location):
    """유적 입구 — 깊은 숲에서 연결"""
    unique_id = "ruin_entrance"
    name = "유적 입구"
    is_indoor = False
    ground_type = "GroundDirt"
    stay_duration = 3
    geometry = 1
    length = 400

    describe_text = {
        "default": "고대 석문이 열려 있다. 안에서 으스스한 기운이 느껴진다.",
        "밤": "달빛 아래 유적 입구가 불길하게 빛나고 있다.",
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 기생체 제거제 바닥 배치
        import morld
        import ground as ground_mod
        from assets.items.parasites import ParasiteRemover
        remover = ParasiteRemover()
        remover_id = morld.create_id("item")
        remover.instantiate(remover_id)
        ground_id = ground_mod.ensure_ground_at(region_id, location_id, 0)
        morld.give_item(ground_id, remover_id, 2)


class RuinCorridor(Location):
    """1층 회랑 — 부서진 석상과 벽화"""
    unique_id = "ruin_corridor"
    name = "1층 회랑"
    is_indoor = True
    ground_type = "GroundConcrete"
    stay_duration = 0
    geometry = 1
    length = 500

    describe_text = {
        "default": "부서진 석상과 벽화가 늘어선 넓은 복도. 발밑에 돌 부스러기가 흩어져 있다.",
    }


class RuinNest(Location):
    """2층 거미굴 — 거미줄이 뒤덮인 방"""
    unique_id = "ruin_nest"
    name = "2층 거미굴"
    is_indoor = True
    ground_type = "GroundDirt"
    stay_duration = 0
    geometry = 1
    length = 400

    describe_text = {
        "default": "거미줄이 빽빽하게 뒤덮인 넓은 방. 어디선가 다리가 움직이는 소리가 들린다.",
    }


class RuinParasiteRoom(Location):
    """3층 기생실 — 기묘한 생물체 서식"""
    unique_id = "ruin_parasite_room"
    name = "3층 기생실"
    is_indoor = True
    ground_type = "GroundDirt"
    stay_duration = 0
    geometry = 1
    length = 300

    describe_text = {
        "default": "벽면에 기묘한 생물체가 꿈틀거리고 있다. 습하고 끈적한 공기가 가득하다.",
    }


class RuinBossRoom(Location):
    """유적 심층 — 고대 의식장"""
    unique_id = "ruin_boss"
    name = "유적 심층"
    is_indoor = True
    ground_type = "GroundConcrete"
    stay_duration = 0
    geometry = 1
    length = 200

    describe_text = {
        "default": "고대 의식이 행해진 듯한 넓은 방. 제단에 기묘한 문양이 새겨져 있다.",
    }
