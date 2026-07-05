# assets/objects/construction.py - 건설현장 오브젝트
#
# 건설 중인 Location에 자동 배치되는 오브젝트.
# 진척도 추적 + 플레이어/NPC 건설 액션 제공.
# 시나리오02와 동일한 인터페이스 (build_progress + check_progress).

import morld
import ui
from assets.base import Object


class ConstructionSite(Object):
    """건설현장 - 건설 진행 추적용 오브젝트"""
    unique_id = "construction_site"
    name = "건설현장"
    category = "structure"
    actions = [
        "call:build_progress:건설",
        "call:check_progress:진척도 확인",
    ]
    props = {}

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
        if not player_id:  # player_id 계약: 부재 시 0 — 오퍼레이터 원격 지정만 가능
            yield ui.dialog(["직접 건설할 수 없다. 에이전트에게 맡기자."])
            return
        success, new_progress, msg = build.build_location_progress(
            player_id, self.instance_id, recipe.materials
        )
        yield ui.dialog([msg])

    def check_progress(self):
        """진척도 확인 핸들러 (call:check_progress)"""
        import build as build_module

        progress = build_module.get_construction_progress(self.instance_id)
        owner = morld.get_unit_prop(self.instance_id, "건설:소유자") or "불명"

        lines = [f"건설현장 - 소유자: {owner}"]
        if progress >= 100:
            lines.append("상태: 완성")
        else:
            lines.append(f"진척도: {progress}%")

            recipe_id = morld.get_unit_prop(self.instance_id, "건설:레시피") or ""
            recipe = build_module.get_recipe(recipe_id)
            if recipe:
                lines.append("")
                lines.append("필요 재료:")
                for item_uid, count in recipe.materials:
                    lines.append(f"  - {item_uid} x{count}")

        yield ui.dialog(lines)

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
