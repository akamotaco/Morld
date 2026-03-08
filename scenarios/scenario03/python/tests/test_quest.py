"""퀘스트/레시피 정의 테스트"""


class TestQuestDefinitions:
    def test_demo_quests_exist(self):
        from quest import DEMO_QUESTS
        assert "demo_explore_platform" in DEMO_QUESTS
        assert "demo_first_expedition" in DEMO_QUESTS

    def test_explore_quest_structure(self):
        from quest import DEMO_QUESTS
        q = DEMO_QUESTS["demo_explore_platform"]
        assert q["category"] == "main"
        assert len(q["conditions"]) == 3
        assert q["giver"] == "secretary"

    def test_expedition_quest_conditions(self):
        from quest import DEMO_QUESTS
        q = DEMO_QUESTS["demo_first_expedition"]
        # Should have collect conditions
        for cond in q["conditions"]:
            assert cond["type"] == "collect"
            assert "item" in cond
            assert "count" in cond


class TestBuildRecipes:
    def test_recipes_exist(self):
        from quest import BUILD_RECIPES
        assert "barracks" in BUILD_RECIPES
        assert "storage_room" in BUILD_RECIPES
        assert "med_bay" in BUILD_RECIPES
        assert "armory" in BUILD_RECIPES

    def test_recipe_has_materials(self):
        from quest import BUILD_RECIPES
        for recipe_id, recipe in BUILD_RECIPES.items():
            assert "materials" in recipe, f"{recipe_id} missing materials"
            assert len(recipe["materials"]) > 0, f"{recipe_id} has empty materials"
            assert "name" in recipe, f"{recipe_id} missing name"
