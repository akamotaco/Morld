# assets/objects/construction.py - 건설현장 오브젝트
#
# 건설 중인 Location에 자동 배치되는 오브젝트.
# 진척도 추적 + 플레이어/NPC 건설 액션 제공.

import morld
import ui
from assets.base import Object


class ConstructionSite(Object):
    """건설현장 - 건설 진행 추적용 오브젝트"""
    unique_id = "construction_site"
    name = "건설현장"
    actions = [
        "call:check_progress:진척도 확인",
    ]
    props = {}

    def check_progress(self):
        """진척도 확인 UI"""
        progress = morld.get_unit_prop(self.instance_id, "건설:진척도") or 0
        recipe_id = morld.get_unit_prop(self.instance_id, "건설:레시피") or ""
        owner = morld.get_unit_prop(self.instance_id, "건설:소유자") or "?"

        # 레시피 정보
        recipe_name = recipe_id
        materials_text = ""
        try:
            import build as build_module
            recipe = build_module.get_recipe(recipe_id)
            if recipe:
                recipe_name = recipe.name
                mat_lines = []
                for item_uid, count in recipe.materials.items():
                    mat_lines.append(f"  {item_uid}: {count}")
                materials_text = "\n".join(mat_lines)
        except ImportError:
            pass

        lines = [
            f"[b]{recipe_name} - 건설현장[/b]\n",
            f"  진척도: {progress}%",
            f"  지정자: {owner}",
        ]
        if materials_text:
            lines.append(f"\n  필요 자재 (1회분):\n{materials_text}")

        if progress >= 100:
            lines.append("\n[i]건설이 완료되었습니다.[/i]")

        yield ui.dialog("\n".join(lines))

    def get_focus_text(self):
        """포커스 묘사"""
        progress = morld.get_unit_prop(self.instance_id, "건설:진척도") or 0
        if progress >= 100:
            return "건설이 완료된 구역. 정리가 필요하다."
        if progress > 50:
            return f"건설 중인 구역. 절반 이상 진행되었다. ({progress}%)"
        if progress > 0:
            return f"건설이 시작된 구역. 아직 갈 길이 멀다. ({progress}%)"
        return "건설이 지정된 구역. 아직 착공하지 않았다."
