# assets/objects/train.py - 지저철 및 콘솔 오브젝트
#
# SubwayTrain: OldBus 패턴 확장, interior Location을 별도 Region으로 관리
# CRTConsole: 통신실 메인 콘솔, 분대 관리/건축 지정 UI

import morld
import ui
from assets.base import Object


class SubwayTrain(Object):
    """지저철 — OldBus 패턴 확장

    시나리오02의 대형 차량(OldBus) 구조를 재활용.
    interior Location을 별도 Region으로 두고, Gate로 연결.
    이동 시 Gate 재연결으로 승/하차 위치 변경.
    """
    unique_id = "subway_train"
    name = "지저철"
    actions = [
        "call:inspect:점검",
    ]
    props = {
        "vehicle:type": "train",
        "vehicle:seats": 0,           # 직접 좌석 없음 (interior 사용)
        "vehicle:speed": 5.0,         # 선로 고속 이동
        "vehicle:fuel": 100,
        "vehicle:fuel_max": 100,
        "vehicle:fuel_rate": 0.1,     # 전력 기반, 낮은 소비
        "vehicle:hp": 500,
        "vehicle:hp_max": 500,
        "vehicle:status": "normal",
        "vehicle:interior": "R1:L0",  # Region 1, Location 0
        "vehicle:part:engine": 100,
        "vehicle:part:engine_max": 100,
        "vehicle:part:body": 100,
        "vehicle:part:body_max": 100,
    }

    def inspect(self):
        """차량 상태 점검"""
        status = morld.get_unit_prop(self.instance_id, "vehicle:status") or "normal"
        hp = morld.get_unit_prop(self.instance_id, "vehicle:hp") or 0
        hp_max = morld.get_unit_prop(self.instance_id, "vehicle:hp_max") or 0
        fuel = morld.get_unit_prop(self.instance_id, "vehicle:fuel") or 0
        fuel_max = morld.get_unit_prop(self.instance_id, "vehicle:fuel_max") or 0

        engine = morld.get_unit_prop(self.instance_id, "vehicle:part:engine") or 0
        body = morld.get_unit_prop(self.instance_id, "vehicle:part:body") or 0

        status_label = {
            "normal": "정상",
            "disabled": "고장",
            "wrecked": "완파",
        }.get(status, status)

        lines = [
            f"[b]{self.name} — 상태 점검[/b]\n",
            f"  상태: {status_label}",
            f"  내구도: {hp}/{hp_max}",
            f"  전력: {fuel:.0f}/{fuel_max:.0f}",
            f"  엔진: {engine}%",
            f"  차체: {body}%",
        ]
        yield ui.dialog("\n".join(lines))

    def get_focus_text(self):
        """포커스 묘사"""
        status = morld.get_unit_prop(self.instance_id, "vehicle:status") or "normal"
        if status == "wrecked":
            return "완파된 지저철. 더 이상 움직이지 않는다."
        if status == "disabled":
            return "고장난 지저철. 수리가 필요하다."
        return "낡았지만 아직 움직이는 지저철. 선로를 따라 지저 세계를 이동할 수 있다."


class CRTConsole(Object):
    """CRT 콘솔 — 통신실 메인 콘솔

    오퍼레이터(플레이어)의 주 인터페이스.
    분대 관리, 건축 지정, 상황 모니터링 등을 수행한다.
    """
    unique_id = "crt_console"
    name = "CRT 콘솔"
    actions = [
        "call:view_status:상황 확인",
        "call:designate_build:건축 지정",
        "call:manage_squad:분대 관리",
    ]
    props = {}

    def view_status(self):
        """현재 플랫폼 상황 확인"""
        # TODO: 실제 상황 데이터 수집 (NPC 수, 건축 진행률 등)
        lines = [
            "[b]제3지저관리구역 — 상황 보고[/b]\n",
            "  거점: 플랫폼",
            "  지저철: 대기 중",
            "  에이전트: 배정 대기",
            "\n[i]CRT 화면이 지직거린다.[/i]",
        ]
        yield ui.dialog("\n".join(lines))

    def designate_build(self):
        """건축 지정 (원격)

        레시피 선택 -> 건설 위치(중앙 통로 Gate) 지정 -> 건설현장 생성.
        실제 건설은 에이전트의 "건축" 활동이 수행.
        """
        import build as build_module

        recipes = build_module.get_all_recipes()
        if not recipes:
            yield ui.dialog("사용 가능한 건축 레시피가 없습니다.")
            return

        # 레시피 선택 UI
        state = {"result": None}

        def handle_choice(action):
            if action == "init":
                return None
            state["result"] = action
            return True

        lines = ["[b]건축 지정[/b]\n\n건설할 시설을 선택하세요.\n"]
        for recipe_id, recipe in recipes.items():
            mat_text = ", ".join(f"{k} x{v}" for k, v in recipe.materials.items())
            lines.append(f"[url=@proc:{recipe_id}]{recipe.name}[/url] ({mat_text})")
        lines.append("\n[url=@proc:cancel]취소[/url]")

        yield ui.dialog(
            "\n".join(lines),
            autofill="off",
            proc=handle_choice,
            result=state,
        )

        if state["result"] == "cancel" or state["result"] is None:
            return

        recipe_id = state["result"]
        recipe = build_module.get_recipe(recipe_id)
        if not recipe:
            yield ui.dialog("알 수 없는 레시피입니다.")
            return

        # 건설 위치: 중앙 통로(R0, L1)에 Gate 추가
        from world.platform import REGION_ID
        source_location = 1  # 중앙 통로
        gate_x = 80  # 통로 우측 부근

        success, r, l, site_id, msg = build_module.designate_build(
            recipe_id, REGION_ID, source_location, gate_x
        )

        if success:
            yield ui.dialog(
                f"[b]비서[/b]\n\n"
                f"{recipe.name} 건설이 지정되었습니다.\n"
                f"+에이전트가 건설을 시작할 것입니다."
            )
        else:
            yield ui.dialog(f"건설 지정 실패: {msg}")

    def manage_squad(self):
        """분대 관리"""
        # TODO: party.py API 연동 — 분대 편성/해산/명령
        yield ui.dialog("분대 관리 시스템은 아직 준비되지 않았습니다.\n(에이전트 도착 후 사용 가능)")

    def get_focus_text(self):
        """포커스 묘사"""
        return "구형 CRT 모니터. 녹색 문자가 깜빡이고 있다. 이것이 오퍼레이터의 눈이다."
