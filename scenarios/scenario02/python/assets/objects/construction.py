# assets/objects/construction.py — 건설현장 오브젝트
#
# 방 건설 시 자동 배치되는 오브젝트.
# 재료 투입 → 진척도 상승 → 완성 시 방 사용 가능.

import morld
from assets.base import Object
import ui


class ConstructionSite(Object):
    """건설현장 — 방 건설 진척도 관리"""

    unique_id = "construction_site"
    name = "건설현장"
    category = "structure"
    actions = [
        "call:build_progress:건설",
        "call:check_progress:진척도 확인",
    ]

    def get_focus_text(self):
        progress = morld.get_unit_prop(self.instance_id, "건설:진척도") or 0
        owner = morld.get_unit_prop(self.instance_id, "건설:소유자") or "불명"
        if progress >= 100:
            status = "완성"
        else:
            status = f"건설 중 ({progress}%)"
        return f"[건설현장] {status}\n소유자: {owner}"

    def build_progress(self):
        """건설 액션 핸들러 (call:build_progress)"""
        import build

        progress = build.get_construction_progress(self.instance_id)
        if progress >= 100:
            yield ui.dialog(["이미 완성된 건물이다."])
            return

        recipe_id = morld.get_unit_prop(self.instance_id, "건설:레시피") or ""
        recipe = build.get_recipe(recipe_id)

        if recipe is None:
            yield ui.dialog(["건설 정보를 확인할 수 없다."])
            return

        # 필요 재료 표시
        lines = [f"건설 진척도: {progress}%", ""]
        lines.append("필요 재료:")
        for item_uid, count in recipe.materials:
            lines.append(f"  - {item_uid} x{count}")
        lines.append("")
        lines.append("[url=@ret:confirm]재료를 투입한다[/url]")
        lines.append("[url=@ret:cancel]그만둔다[/url]")

        choice = yield ui.dialog(lines, autofill="off")
        if choice != "confirm":
            return

        player_id = morld.get_player_id()
        success, new_progress, msg = build.build_location_progress(
            player_id, self.instance_id, recipe.materials
        )
        yield ui.dialog([msg])

    def check_progress(self):
        """진척도 확인 핸들러 (call:check_progress)"""
        import build

        progress = build.get_construction_progress(self.instance_id)
        owner = morld.get_unit_prop(self.instance_id, "건설:소유자") or "불명"

        lines = [f"건설현장 — 소유자: {owner}"]
        if progress >= 100:
            lines.append("상태: 완성")
        else:
            lines.append(f"진척도: {progress}%")

            recipe_id = morld.get_unit_prop(self.instance_id, "건설:레시피") or ""
            recipe = build.get_recipe(recipe_id)
            if recipe:
                lines.append("")
                lines.append("필요 재료:")
                for item_uid, count in recipe.materials:
                    lines.append(f"  - {item_uid} x{count}")

        yield ui.dialog(lines)
