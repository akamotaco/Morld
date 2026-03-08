"""Asset 클래스 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()


class TestLocations(_T):
    def test_station_instantiate(self):
        from assets.locations.platform_locations import Station
        morld.add_region(0, "test")
        loc = Station()
        loc.instantiate(0, 0)
        info = morld.get_location_info(0, 0)
        assert info is not None
        assert info["name"] == "승강장"
        assert info["length"] == 200
        assert info["is_indoor"] == True

    def test_corridor_instantiate(self):
        from assets.locations.platform_locations import PlatformCorridor
        morld.add_region(0, "test")
        loc = PlatformCorridor()
        loc.instantiate(1, 0)
        info = morld.get_location_info(0, 1)
        assert info is not None
        assert info["length"] == 100

    def test_comm_room_instantiate(self):
        from assets.locations.platform_locations import CommRoom
        morld.add_region(0, "test")
        loc = CommRoom()
        loc.instantiate(2, 0)
        info = morld.get_location_info(0, 2)
        assert info is not None
        assert info["length"] == 40

    def test_train_car_instantiate(self):
        from assets.locations.train_locations import TrainCar
        morld.add_region(1, "test")
        loc = TrainCar()
        loc.instantiate(0, 1)
        info = morld.get_location_info(1, 0)
        assert info is not None
        assert info["length"] == 150


class TestObjects(_T):
    def test_subway_train_instantiate(self):
        from assets.objects.train import SubwayTrain
        morld.add_region(0, "test")
        morld.add_location(0, 0, "test", length=200)
        train = SubwayTrain()
        train_id = morld.create_id("unit")
        train.instantiate(train_id, 0, 0, x=100)
        info = morld.get_unit_info(train_id)
        assert info is not None
        assert info["unique_id"] == "subway_train"
        # Vehicle props
        assert morld.get_unit_prop(train_id, "vehicle:type") == "train"
        assert morld.get_unit_prop(train_id, "vehicle:interior") == "R1:L0"
        assert morld.get_unit_prop(train_id, "vehicle:speed") == 5.0

    def test_crt_console_instantiate(self):
        from assets.objects.train import CRTConsole
        morld.add_region(0, "test")
        morld.add_location(0, 2, "test", length=40)
        console = CRTConsole()
        cid = morld.create_id("unit")
        console.instantiate(cid, 0, 2, x=20)
        info = morld.get_unit_info(cid)
        assert info is not None
        assert info["unique_id"] == "crt_console"


class TestCharacters(_T):
    def test_secretary_instantiate(self):
        from assets.characters.secretary import Secretary
        morld.add_region(0, "test")
        morld.add_location(0, 2, "comm", length=40)
        sec = Secretary()
        sec_id = morld.create_id("unit")
        sec.instantiate(sec_id, 0, 2)
        info = morld.get_unit_info(sec_id)
        assert info is not None
        assert info["unique_id"] == "secretary"

    def test_squad_member_configure(self):
        from assets.characters.squad_member import SquadMember
        morld.add_region(0, "test")
        morld.add_location(0, 0, "station", length=200)
        npc = SquadMember()
        npc.configure("echo_01", "Echo-01", "assault")
        assert npc.unique_id == "echo_01"
        assert npc.name == "Echo-01"
        npc_id = morld.create_id("unit")
        npc.instantiate(npc_id, 0, 0)
        info = morld.get_unit_info(npc_id)
        assert info is not None
        assert info["unique_id"] == "echo_01"
        assert morld.get_unit_prop(npc_id, "역할") == "돌격"
        assert morld.get_unit_prop(npc_id, "vita") == 6

    def test_squad_member_roles(self):
        from assets.characters.squad_member import SquadMember, ROLE_PROPS
        morld.add_region(0, "test")
        morld.add_location(0, 0, "station", length=200)
        for role in ["assault", "support", "sniper", "medic"]:
            npc = SquadMember()
            npc.configure(f"test_{role}", f"Test-{role}", role)
            npc_id = morld.create_id("unit")
            npc.instantiate(npc_id, 0, 0)
            # Verify role props are set
            for key, val in ROLE_PROPS[role].items():
                assert morld.get_unit_prop(npc_id, key) == val, f"{role}.{key} expected {val}"


class TestItems(_T):
    def test_material_items(self):
        from assets.items.materials import MetalPipe, ConcreteBlock, Plank, Wire
        for cls in [MetalPipe, ConcreteBlock, Plank, Wire]:
            item = cls()
            item_id = morld.create_id("item")
            item.instantiate(item_id)
            info = morld.get_item_info(item_id)
            assert info is not None, f"{cls.__name__} not registered"
            assert info["name"] is not None
