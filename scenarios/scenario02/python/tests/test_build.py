# test_build.py — 건축/파괴 시스템 테스트
#
# build.py의 핵심 로직 검증:
# - 레시피 등록/조회
# - 오브젝트 건축 (재료 확인 → 소비 → 생성)
# - 방 건설 (뼈대 + 진척도)
# - 방 확장 (length 증가)
# - 오브젝트 파괴 (소유권 + 인벤토리 drop)
# - 방 파괴 (조건 검증 + 제거)

import sys
import os
import types

# ========================================
# 1. Mock morld 주입
# ========================================

sys.path.insert(0, os.path.dirname(__file__))
import morld as mock

# ========================================
# 2. Stub 모듈 구성
# ========================================

# assets 패키지
assets_pkg = types.ModuleType("assets")
sys.modules["assets"] = assets_pkg

# assets.base — Object 기본 클래스
assets_base = types.ModuleType("assets.base")


class MockObject:
    """Object 기본 클래스 stub"""
    unique_id = "mock_object"
    name = "MockObject"
    category = "structure"
    actions = []
    position_x = 0
    position_y = 0
    props = None
    owner = None
    item_visible = True

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        self.instance_id = instance_id
        self.region_id = region_id
        self.location_id = location_id
        mock.add_unit(instance_id, self.name, region_id, location_id, "object")
        # register_instance 호출
        _object_instances[instance_id] = self


assets_base.Object = MockObject
assets_pkg.base = assets_base
sys.modules["assets.base"] = assets_base

# assets.registry — get_or_create_item_id
assets_registry = types.ModuleType("assets.registry")
_item_id_map = {}
_next_item_id = [100]


def _get_or_create_item_id(unique_id):
    if unique_id not in _item_id_map:
        _next_item_id[0] += 1
        _item_id_map[unique_id] = _next_item_id[0]
    return _item_id_map[unique_id]


assets_registry.get_or_create_item_id = _get_or_create_item_id
assets_pkg.registry = assets_registry
sys.modules["assets.registry"] = assets_registry

# assets.objects — 인스턴스 레지스트리
assets_objects = types.ModuleType("assets.objects")
_object_instances = {}
_location_objects = {}


def _register_instance(instance_id, instance):
    _object_instances[instance_id] = instance


def _register_location_object(region_id, location_id, instance_id):
    key = (region_id, location_id)
    if key not in _location_objects:
        _location_objects[key] = []
    _location_objects[key].append(instance_id)


assets_objects._instances = _object_instances
assets_objects._location_objects = _location_objects
assets_objects.register_instance = _register_instance
assets_objects.register_location_object = _register_location_object
assets_objects.get_instance = lambda uid: _object_instances.get(uid)
assets_pkg.objects = assets_objects
sys.modules["assets.objects"] = assets_objects

# assets.objects.construction — ConstructionSite


class MockConstructionSite(MockObject):
    unique_id = "construction_site"
    name = "건설현장"
    category = "structure"


assets_objects_construction = types.ModuleType("assets.objects.construction")
assets_objects_construction.ConstructionSite = MockConstructionSite
sys.modules["assets.objects.construction"] = assets_objects_construction

# ground — drop_item_at
ground_module = types.ModuleType("ground")
_dropped_items = []


def _drop_item_at(unit_id, item_id, count):
    _dropped_items.append((unit_id, item_id, count))


ground_module.drop_item_at = _drop_item_at
sys.modules["ground"] = ground_module

# ui — dialog (construction.py에서 사용)
ui_module = types.ModuleType("ui")
ui_module.dialog = lambda lines, **kwargs: None
sys.modules["ui"] = ui_module

# ========================================
# 3. import build (stub 주입 후)
# ========================================

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build

# ========================================
# 4. 테스트 헬퍼
# ========================================


class SimpleResultObject(MockObject):
    """build_object 테스트용 결과 오브젝트"""
    unique_id = "simple_table"
    name = "간이 테이블"


def _reset_all():
    """모든 상태 초기화"""
    mock.reset()
    build.reset()
    _object_instances.clear()
    _location_objects.clear()
    _dropped_items.clear()
    _item_id_map.clear()
    _next_item_id[0] = 100


class _T:
    def __init__(self):
        _reset_all()


def _setup_builder(unit_id=10, name="세라", region_id=0, location_id=5):
    """건축자 유닛 등록"""
    mock.register_unit(unit_id, name=name, location=(region_id, location_id))
    mock.add_region(region_id, "저택")
    mock.add_location(region_id, location_id, "거실", length=200)
    return unit_id


def _make_recipe(**kwargs):
    """테스트용 레시피 생성"""
    defaults = {
        "unique_id": "test_recipe",
        "name": "테스트 레시피",
        "recipe_type": "object",
        "tool_category": "hammer",
        "materials": [("wood", 3), ("nail", 2)],
        "result_class": SimpleResultObject,
        "base_length": 1,
        "progress_per_build": 25,
        "indoor": True,
    }
    defaults.update(kwargs)
    return build.BuildRecipe(**defaults)


def _give_materials(unit_id, materials):
    """건축자에게 재료 지급"""
    for item_uid, count in materials:
        item_id = _get_or_create_item_id(item_uid)
        mock.give_item(unit_id, item_id, count)


# ========================================
# 5. 테스트 케이스
# ========================================


class TestRecipe(_T):
    """레시피 등록/조회 테스트"""

    def test_register_and_get(self):
        recipe = _make_recipe()
        build.register_recipe(recipe)

        result = build.get_recipe("test_recipe")
        assert result is not None
        assert result.name == "테스트 레시피"
        assert result.type == "object"

    def test_get_nonexistent(self):
        assert build.get_recipe("nonexistent") is None

    def test_get_recipes_for_tool(self):
        r1 = _make_recipe(unique_id="r1", tool_category="hammer")
        r2 = _make_recipe(unique_id="r2", tool_category="saw")
        r3 = _make_recipe(unique_id="r3", tool_category="hammer")
        build.register_recipe(r1)
        build.register_recipe(r2)
        build.register_recipe(r3)

        hammer_recipes = build.get_recipes_for_tool("hammer")
        assert len(hammer_recipes) == 2
        saw_recipes = build.get_recipes_for_tool("saw")
        assert len(saw_recipes) == 1


class TestBuildObject(_T):
    """오브젝트 건축 테스트"""

    def test_success(self):
        uid = _setup_builder()
        recipe = _make_recipe(materials=[("wood", 2)])
        build.register_recipe(recipe)
        _give_materials(uid, [("wood", 5)])

        success, obj_id, msg = build.build_object(uid, "test_recipe", 0, 5, 100)

        assert success is True
        assert obj_id is not None
        assert msg == "건축 완료"
        # 재료 소비 확인 (5 - 2 = 3)
        wood_id = _get_or_create_item_id("wood")
        assert mock.has_item(uid, wood_id, 3)
        assert not mock.has_item(uid, wood_id, 4)

    def test_insufficient_materials(self):
        uid = _setup_builder()
        recipe = _make_recipe(materials=[("wood", 10)])
        build.register_recipe(recipe)
        _give_materials(uid, [("wood", 3)])

        success, obj_id, msg = build.build_object(uid, "test_recipe", 0, 5, 100)

        assert success is False
        assert obj_id is None
        assert "재료 부족" in msg

    def test_owner_set(self):
        uid = _setup_builder(name="세라")
        recipe = _make_recipe(materials=[])
        build.register_recipe(recipe)

        success, obj_id, _ = build.build_object(uid, "test_recipe", 0, 5, 100)

        assert success is True
        owner = mock.get_unit_prop(obj_id, "건축:소유자")
        assert owner == "세라"


class TestBuildLocationFrame(_T):
    """방 건설 (뼈대) 테스트"""

    def test_creates_location_and_gates(self):
        uid = _setup_builder()
        recipe = _make_recipe(
            unique_id="room_recipe",
            recipe_type="location",
            base_length=5,
            indoor=True,
        )
        build.register_recipe(recipe)

        success, region_id, new_loc_id, site_id, msg = build.build_location_frame(
            uid, 0, 5, 100, recipe_id="room_recipe", room_name="세라의 방"
        )

        assert success is True
        assert region_id == 0
        assert site_id is not None
        assert msg == "뼈대 건설 완료"

        # 새 location 생성 확인
        loc_key = (0, new_loc_id)
        assert loc_key in mock._locations
        assert mock._locations[loc_key]["name"] == "세라의 방"
        assert mock._locations[loc_key]["length"] == 5

        # 양방향 gate 확인
        src_gates = mock.get_location_gates(0, 5)
        new_gates = mock.get_location_gates(0, new_loc_id)
        assert len(src_gates) >= 1
        assert len(new_gates) >= 1

        # source → new gate
        src_gate = [g for g in src_gates
                    if g["connected_location"] == new_loc_id]
        assert len(src_gate) == 1
        assert src_gate[0]["x"] == 100

        # new → source gate
        new_gate = [g for g in new_gates
                    if g["connected_location"] == 5]
        assert len(new_gate) == 1

    def test_construction_site_placed(self):
        uid = _setup_builder()
        recipe = _make_recipe(unique_id="room_recipe", recipe_type="location")
        build.register_recipe(recipe)

        success, _, new_loc_id, _site_id, _ = build.build_location_frame(
            uid, 0, 5, 100, recipe_id="room_recipe"
        )

        assert success is True
        # 건설현장 유닛이 새 location에 배치됨
        units = mock.get_units_at_location(0, new_loc_id, "object")
        assert len(units) >= 1

        # 건설 props 확인
        site_id = units[0]
        assert mock.get_unit_prop(site_id, "건설:진척도") == 0
        assert mock.get_unit_prop(site_id, "건설:소유자") == "세라"
        assert mock.get_unit_prop(site_id, "건설:레시피") == "room_recipe"

    def test_next_location_id(self):
        """기존 location이 있을 때 빈 ID 자동 선택"""
        uid = _setup_builder()
        # location 0, 1이 이미 존재
        mock.add_location(0, 0, "입구")
        mock.add_location(0, 1, "복도")

        recipe = _make_recipe(unique_id="r", recipe_type="location")
        build.register_recipe(recipe)

        success, _, new_id, _site_id, _ = build.build_location_frame(uid, 0, 5, 50, recipe_id="r")
        assert success is True
        # 0, 1, 5 이미 사용 중 → 2가 선택됨
        assert new_id == 2


class TestBuildLocationProgress(_T):
    """방 건설 (진척도) 테스트"""

    def _setup_site(self, progress=0, progress_per_build=25):
        """건설현장 세팅"""
        uid = _setup_builder()
        recipe = _make_recipe(
            unique_id="room_r",
            recipe_type="location",
            materials=[("stone", 5)],
            progress_per_build=progress_per_build,
        )
        build.register_recipe(recipe)

        # 건설현장 직접 생성
        site_id = 500
        mock.register_unit(site_id, name="건설현장",
                           location=(0, 5), gender="object")
        mock.set_unit_prop(site_id, "건설:진척도", progress)
        mock.set_unit_prop(site_id, "건설:레시피", "room_r")

        return uid, site_id

    def test_progress_increases(self):
        uid, site_id = self._setup_site(progress=0)
        _give_materials(uid, [("stone", 5)])

        success, new_progress, msg = build.build_location_progress(
            uid, site_id, [("stone", 5)]
        )

        assert success is True
        assert new_progress == 25
        assert "25%" in msg

    def test_completion(self):
        uid, site_id = self._setup_site(progress=80, progress_per_build=25)
        _give_materials(uid, [("stone", 5)])

        success, new_progress, msg = build.build_location_progress(
            uid, site_id, [("stone", 5)]
        )

        assert success is True
        assert new_progress == 100
        assert "완료" in msg

    def test_already_complete(self):
        uid, site_id = self._setup_site(progress=100)
        _give_materials(uid, [("stone", 5)])

        success, _, msg = build.build_location_progress(
            uid, site_id, [("stone", 5)]
        )

        assert success is False
        assert "완성" in msg

    def test_insufficient_materials(self):
        uid, site_id = self._setup_site(progress=0)
        # 재료 지급하지 않음

        success, _, msg = build.build_location_progress(
            uid, site_id, [("stone", 5)]
        )

        assert success is False
        assert "재료 부족" in msg
        # 진척도 변동 없음
        assert mock.get_unit_prop(site_id, "건설:진척도") == 0


class TestExpandLocation(_T):
    """방 확장 테스트"""

    def test_success(self):
        uid = _setup_builder()
        mock.set_location_length(0, 5, 100)
        _give_materials(uid, [("wood", 10)])

        success, new_length, msg = build.expand_location(
            uid, 0, 5, 50, [("wood", 10)]
        )

        assert success is True
        assert new_length == 150
        assert "150" in msg

    def test_insufficient_materials(self):
        uid = _setup_builder()
        mock.set_location_length(0, 5, 100)

        success, _, msg = build.expand_location(
            uid, 0, 5, 50, [("wood", 10)]
        )

        assert success is False
        assert "재료 부족" in msg


class TestDestroyObject(_T):
    """오브젝트 파괴 테스트"""

    def _setup_object(self, owner_name="세라"):
        """파괴 대상 오브젝트 세팅"""
        uid = _setup_builder(name="세라")
        obj_id = 200
        mock.register_unit(obj_id, name="간이 테이블",
                           location=(0, 5), gender="object")
        mock.set_unit_prop(obj_id, "건축:소유자", owner_name)

        # 레지스트리 등록
        _object_instances[obj_id] = MockObject()
        _location_objects[(0, 5)] = [obj_id]

        return uid, obj_id

    def test_success(self):
        uid, obj_id = self._setup_object(owner_name="세라")

        success, msg = build.destroy_object(uid, obj_id)

        assert success is True
        assert mock.get_unit_info(obj_id) is None  # 제거됨

    def test_non_owner_fails(self):
        uid, obj_id = self._setup_object(owner_name="밀라")

        success, msg = build.destroy_object(uid, obj_id)

        assert success is False
        assert "소유자" in msg

    def test_inventory_dropped(self):
        uid, obj_id = self._setup_object(owner_name="세라")
        # 오브젝트 인벤토리에 아이템 추가
        mock.give_item(obj_id, 50, 3)
        mock.give_item(obj_id, 51, 1)

        success, _ = build.destroy_object(uid, obj_id)

        assert success is True
        # ground에 drop 호출 확인
        assert len(_dropped_items) == 2

    def test_registry_cleanup(self):
        uid, obj_id = self._setup_object(owner_name="세라")

        success, _ = build.destroy_object(uid, obj_id)

        assert success is True
        assert obj_id not in _object_instances
        assert obj_id not in _location_objects.get((0, 5), [])


class TestDestroyLocation(_T):
    """방 파괴 테스트"""

    def _setup_room(self):
        """파괴 대상 방 세팅 (gate 1개, 유닛 없음)"""
        uid = _setup_builder(name="세라")
        # 새 방 (location_id=10)
        mock.add_location(0, 10, "세라의 방", owner="세라", length=50)
        # gate: 방 → 거실
        mock.add_gate(0, 10, 0, 0, 0, 5, 100)
        # 역방향 gate: 거실 → 방
        mock.add_gate(0, 5, 1, 100, 0, 10, 0)
        return uid

    def test_success(self):
        uid = self._setup_room()

        success, msg = build.destroy_location(uid, 0, 10)

        assert success is True
        assert (0, 10) not in mock._locations
        # 역방향 gate도 정리됨
        src_gates = mock.get_location_gates(0, 5)
        pointing_to_10 = [g for g in src_gates
                          if g["connected_location"] == 10]
        assert len(pointing_to_10) == 0

    def test_non_owner_fails(self):
        uid = self._setup_room()
        # 다른 캐릭터로 시도
        other_id = 20
        mock.register_unit(other_id, name="밀라", location=(0, 5))

        success, msg = build.destroy_location(other_id, 0, 10)

        assert success is False
        assert "소유자" in msg

    def test_units_inside_fails(self):
        uid = self._setup_room()
        # 방 안에 유닛 배치
        mock.register_unit(30, name="리나", location=(0, 10))

        success, msg = build.destroy_location(uid, 0, 10)

        assert success is False
        assert "유닛" in msg

    def test_multiple_gates_fails(self):
        uid = self._setup_room()
        # gate 추가 (2개)
        mock.add_gate(0, 10, 1, 25, 0, 6, 0)

        success, msg = build.destroy_location(uid, 0, 10)

        assert success is False
        assert "gate" in msg

    def test_inside_fails(self):
        """방 안에서 파괴 시도 → 실패"""
        uid = self._setup_room()
        # 파괴자를 방 안으로 이동
        mock.set_unit_location(uid, 0, 10)

        success, msg = build.destroy_location(uid, 0, 10)

        assert success is False
        assert "밖" in msg or "안" in msg


class TestHelpers(_T):
    """헬퍼 함수 테스트"""

    def test_get_construction_progress(self):
        site_id = 500
        mock.register_unit(site_id, name="건설현장", gender="object")
        mock.set_unit_prop(site_id, "건설:진척도", 75)

        assert build.get_construction_progress(site_id) == 75

    def test_is_construction_complete(self):
        site_id = 500
        mock.register_unit(site_id, name="건설현장", gender="object")

        mock.set_unit_prop(site_id, "건설:진척도", 99)
        assert build.is_construction_complete(site_id) is False

        mock.set_unit_prop(site_id, "건설:진척도", 100)
        assert build.is_construction_complete(site_id) is True


class TestReset(_T):
    """챕터 전환 리셋 테스트"""

    def test_clears_recipes(self):
        recipe = _make_recipe()
        build.register_recipe(recipe)
        assert build.get_recipe("test_recipe") is not None

        build.reset()

        assert build.get_recipe("test_recipe") is None
