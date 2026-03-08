"""건축 시스템 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()
        from assets.objects import _instances, _location_objects
        _instances.clear()
        _location_objects.clear()


class TestBuildRecipes(_T):
    def setUp(self):
        import build as build_module
        build_module.reset()

    def test_register_recipe(self):
        import build as build_module
        recipe = build_module.BuildRecipe(
            unique_id="test_room",
            name="테스트 방",
            materials=[("plank", 3)],
            base_length=40,
        )
        build_module.register_recipe(recipe)
        assert build_module.get_recipe("test_room") is not None
        assert build_module.get_recipe("test_room").name == "테스트 방"

    def test_get_all_recipes(self):
        import build as build_module
        r1 = build_module.BuildRecipe("a", "A", materials=[("plank", 1)])
        r2 = build_module.BuildRecipe("b", "B", materials=[("pipe", 2)])
        build_module.register_recipe(r1)
        build_module.register_recipe(r2)
        all_recipes = build_module.get_all_recipes()
        assert len(all_recipes) == 2
        assert "a" in all_recipes
        assert "b" in all_recipes

    def test_reset_clears_recipes(self):
        import build as build_module
        build_module.register_recipe(
            build_module.BuildRecipe("x", "X")
        )
        build_module.reset()
        assert build_module.get_recipe("x") is None

    def test_register_demo_recipes(self):
        import build as build_module
        build_module.register_demo_recipes()
        assert build_module.get_recipe("barracks") is not None
        assert build_module.get_recipe("storage_room") is not None
        assert build_module.get_recipe("barracks").name == "임시 막사"


class TestBuildLocationFrame(_T):
    def setUp(self):
        import build as build_module
        build_module.reset()
        build_module.register_demo_recipes()
        # Set up Region 0 with Location 0,1,2 (platform)
        morld.add_region(0, "platform")
        morld.add_location(0, 0, "station", length=200)
        morld.add_location(0, 1, "corridor", length=100)
        morld.add_location(0, 2, "comm_room", length=40)

    def test_frame_creates_location(self):
        import build as build_module
        success, r, l, site_id, msg = build_module.build_location_frame(
            builder_id=None,
            source_region=0,
            source_location=1,
            gate_x=80,
            recipe_id="barracks",
        )
        assert success is True
        assert r == 0
        # New location should be ID 3 (after 0,1,2)
        assert l == 3
        # Location should exist
        info = morld.get_location_info(0, 3)
        assert info is not None
        assert info["length"] == 60  # barracks result_length

    def test_frame_creates_construction_site(self):
        import build as build_module
        success, r, l, site_id, msg = build_module.build_location_frame(
            builder_id=None,
            source_region=0,
            source_location=1,
            gate_x=80,
            recipe_id="barracks",
        )
        assert site_id is not None
        info = morld.get_unit_info(site_id)
        assert info is not None
        assert info["unique_id"] == "construction_site"

    def test_frame_sets_props(self):
        import build as build_module
        success, r, l, site_id, msg = build_module.build_location_frame(
            builder_id=None,
            source_region=0,
            source_location=1,
            gate_x=80,
            recipe_id="barracks",
        )
        assert morld.get_unit_prop(site_id, "건설:진척도") == 0
        assert morld.get_unit_prop(site_id, "건설:레시피") == "barracks"
        assert morld.get_unit_prop(site_id, "건설:소유자") == "operator"

    def test_frame_creates_gates(self):
        import build as build_module
        success, r, l, site_id, msg = build_module.build_location_frame(
            builder_id=None,
            source_region=0,
            source_location=1,
            gate_x=80,
            recipe_id="barracks",
        )
        # Check forward gate: corridor(L1) -> new room(L3)
        found_forward = False
        found_return = False
        for key, gate in morld._gates.items():
            if key[0] == 0 and key[1] == 1 and gate["conn_location"] == 3:
                found_forward = True
                assert gate["x"] == 80
            if key[0] == 0 and key[1] == 3 and gate["conn_location"] == 1:
                found_return = True
        assert found_forward, "Forward gate not found"
        assert found_return, "Return gate not found"

    def test_designate_build(self):
        """designate_build = build_location_frame with builder_id=None"""
        import build as build_module
        success, r, l, site_id, msg = build_module.designate_build(
            "storage_room", 0, 1, 80
        )
        assert success is True
        assert morld.get_unit_prop(site_id, "건설:소유자") == "operator"


class TestBuildProgress(_T):
    def setUp(self):
        import build as build_module
        build_module.reset()
        build_module.register_demo_recipes()
        morld.add_region(0, "platform")
        morld.add_location(0, 0, "station", length=200)
        morld.add_location(0, 1, "corridor", length=100)
        # Create a construction site
        success, r, l, site_id, msg = build_module.build_location_frame(
            None, 0, 1, 80, "barracks"
        )
        self.site_id = site_id

    def test_progress_increments(self):
        import build as build_module
        success, progress, msg = build_module.build_location_progress(
            builder_id=None, site_id=self.site_id
        )
        assert success is True
        assert progress == 10  # progress_per_build = 10

    def test_progress_accumulates(self):
        import build as build_module
        for _ in range(5):
            build_module.build_location_progress(None, self.site_id)
        progress = morld.get_unit_prop(self.site_id, "건설:진척도")
        assert progress == 50

    def test_progress_completes_at_100(self):
        import build as build_module
        for _ in range(10):
            build_module.build_location_progress(None, self.site_id)
        assert build_module.is_construction_complete(self.site_id)
        progress = morld.get_unit_prop(self.site_id, "건설:진척도")
        assert progress == 100

    def test_progress_rejects_after_complete(self):
        import build as build_module
        for _ in range(10):
            build_module.build_location_progress(None, self.site_id)
        success, progress, msg = build_module.build_location_progress(
            None, self.site_id
        )
        assert success is False
        assert progress == 100

    def test_is_construction_complete_false(self):
        import build as build_module
        assert build_module.is_construction_complete(self.site_id) is False


class TestConstructionSite(_T):
    def test_instantiate(self):
        from assets.objects.construction import ConstructionSite
        morld.add_region(0, "test")
        morld.add_location(0, 0, "room", length=50)
        site = ConstructionSite()
        site_id = morld.create_id("unit")
        site.instantiate(site_id, 0, 0, x=0)
        info = morld.get_unit_info(site_id)
        assert info is not None
        assert info["unique_id"] == "construction_site"

    def test_focus_text_variants(self):
        from assets.objects.construction import ConstructionSite
        morld.add_region(0, "test")
        morld.add_location(0, 0, "room", length=50)
        site = ConstructionSite()
        site_id = morld.create_id("unit")
        site.instantiate(site_id, 0, 0)

        # No progress prop -> "착공하지 않았다"
        text = site.get_focus_text()
        assert "착공" in text

        # 30% progress
        morld.set_unit_prop(site_id, "건설:진척도", 30)
        text = site.get_focus_text()
        assert "30%" in text

        # 70% progress
        morld.set_unit_prop(site_id, "건설:진척도", 70)
        text = site.get_focus_text()
        assert "절반 이상" in text

        # 100% complete
        morld.set_unit_prop(site_id, "건설:진척도", 100)
        text = site.get_focus_text()
        assert "완료" in text


class TestBuildActivity(_T):
    def setUp(self):
        import build as build_module
        build_module.reset()
        build_module.register_demo_recipes()
        morld.add_region(0, "platform")
        morld.add_location(0, 0, "station", length=200)
        morld.add_location(0, 1, "corridor", length=100)

    def test_find_construction_site(self):
        import build as build_module
        from think.activities.build_activity import _find_construction_site
        from think import BaseAgent

        # Create agent at R0, L1
        agent_id = morld.create_id("unit")
        morld.add_unit(agent_id, "Echo-01", 0, 1, "male")
        agent = BaseAgent(agent_id)

        # No sites yet
        assert _find_construction_site(agent) is None

        # Create a site
        build_module.build_location_frame(None, 0, 1, 80, "barracks")

        # Now should find it
        result = _find_construction_site(agent)
        assert result is not None
        assert result["target"]["region_id"] == 0

    def test_handle_build_idle_no_site(self):
        from think.activities.build_activity import handle_build
        from think import BaseAgent

        agent_id = morld.create_id("unit")
        morld.add_unit(agent_id, "Echo-01", 0, 1, "male")
        agent = BaseAgent(agent_id)
        agent._activity_phase = "idle"
        agent._activity_state = {}

        entry = {"name": "건축", "start": 0, "end": 600_000}
        handle_build(agent, entry)

        # Should insert idle job (no site found)
        assert agent._action_taken is True
        assert agent._activity_phase == "idle"

    def test_handle_build_finds_and_goes(self):
        import build as build_module
        from think.activities.build_activity import handle_build
        from think import BaseAgent

        # Create site
        build_module.build_location_frame(None, 0, 1, 80, "barracks")

        agent_id = morld.create_id("unit")
        morld.add_unit(agent_id, "Echo-01", 0, 1, "male")
        agent = BaseAgent(agent_id)
        agent._activity_phase = "idle"
        agent._activity_state = {}

        entry = {"name": "건축", "start": 0, "end": 600_000}
        handle_build(agent, entry)

        # Should transition to going_to_site
        assert agent._activity_phase == "going_to_site"
        assert "site_id" in agent._activity_state

    def test_handle_build_building_phase(self):
        import build as build_module
        from think.activities.build_activity import handle_build
        from think import BaseAgent

        # Create site
        success, r, l, site_id, msg = build_module.build_location_frame(
            None, 0, 1, 80, "barracks"
        )

        agent_id = morld.create_id("unit")
        morld.add_unit(agent_id, "Echo-01", 0, l, "male")  # Place at site location
        agent = BaseAgent(agent_id)
        agent._activity_phase = "building"
        agent._activity_state = {"site_id": site_id}

        entry = {"name": "건축", "start": 0, "end": 600_000}
        handle_build(agent, entry)

        # Should have built (progress increased)
        progress = morld.get_unit_prop(site_id, "건설:진척도")
        assert progress == 10
        assert agent._action_taken is True
