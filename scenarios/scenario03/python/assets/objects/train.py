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
        "call:order_depart:탐사 출발",
        "call:order_advance:진군 명령",
        "call:order_retreat:퇴각 명령",
        "call:view_report:운용 보고서",
    ]
    props = {}

    def view_status(self):
        """현재 플랫폼 상황 확인"""
        import cycle

        lines = ["[b]제3지저관리구역 — 상황 보고[/b]\n"]
        if cycle.is_active():
            phase_label = {
                "ready": "출발 대기",
                "expedition": "탐사 진행 중",
                "debrief": "보고 대기",
            }.get(cycle.get_phase(), cycle.get_phase())
            lines.append(f"  운행 주기: {cycle.get_cycle_number()}")
            lines.append(f"  단계: {phase_label}")
            lines.append(f"  차기 탐사 난이도: {cycle.current_difficulty()}")
            stock = cycle.get_stockpile()
            if stock:
                stock_text = ", ".join(f"{u} x{c}" for u, c in stock.items())
                lines.append(f"  자재 재고: {stock_text}")
        else:
            lines.append("  거점: 플랫폼")
            lines.append("  지저철: 대기 중")
            lines.append("  에이전트: 배정 대기")
        lines.append("\n[i]CRT 화면이 지직거린다.[/i]")
        yield ui.dialog("\n".join(lines))

    def order_depart(self):
        """탐사 출발 (운영 모드) — 현 주기 난이도로 원정 준비/개시"""
        import cycle
        import squad as squad_module
        import expedition as exp_module
        import npc_dialogue

        if not cycle.is_active():
            yield ui.dialog("아직 정규 운영이 개시되지 않았습니다.\n"
                            "튜토리얼 임무를 먼저 완료하세요.")
            return
        if cycle.get_phase() != "ready":
            yield ui.dialog("지금은 출발할 수 없습니다.\n"
                            "(탐사 진행 중이거나 보고 대기 상태)")
            return

        squads = squad_module.get_all_squads()
        if not squads:
            yield ui.dialog("편성된 분대가 없습니다.\n분대 관리에서 편성하세요.")
            return
        sq = squads[0]

        difficulty = cycle.current_difficulty()
        state = exp_module.prepare_expedition(sq.squad_id, difficulty)
        if not state:
            yield ui.dialog("원정 준비에 실패했습니다.\n분대 상태를 확인하세요.")
            return
        success, msg = exp_module.start_expedition(state.expedition_id)
        if not success:
            exp_module.complete_expedition(state.expedition_id)
            yield ui.dialog(f"출발 실패: {msg}")
            return

        cycle.mark_expedition_started()

        text = (
            "[b]비서[/b]\n\n"
            f"운행 주기 {cycle.get_cycle_number()} — 탐사를 개시합니다.\n"
            f"+탐사 구역: {len(state.rooms)}개 구역 탐지됨 (난이도: {difficulty})\n"
            "+진군 명령으로 분대를 지휘하세요."
        )
        # 출발 한마디 (주변 대사)
        unit_ids = squad_module.get_all_unit_ids(sq.squad_id)
        if unit_ids:
            speaker = unit_ids[cycle.get_cycle_number() % len(unit_ids)]
            line = npc_dialogue.member_dungeon_line(speaker, "floor_descent")
            if line:
                text += "\n\n" + line
        yield ui.dialog(text)

    def view_report(self):
        """최근 사후 운용 보고서 열람"""
        import cycle
        yield ui.dialog(cycle.build_report_text())

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
            mat_text = ", ".join(f"{uid} x{cnt}" for uid, cnt in recipe.materials)
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
        """분대 편성/해산/공세 레벨 설정"""
        import squad as squad_module
        from think import get_all_agents

        squads = squad_module.get_all_squads()

        if squads:
            yield from self._manage_existing_squad(squads[0])
        else:
            yield from self._create_new_squad()

    def _create_new_squad(self):
        """새 분대 편성"""
        import squad as squad_module
        from think import get_all_agents

        # 사용 가능한 에이전트 목록
        agents = get_all_agents()
        available = []
        for uid, agent in agents.items():
            if squad_module.is_in_squad(uid):
                continue
            info = morld.get_unit_info(uid)
            if info and info.get("unique_id", "").startswith("echo_"):
                available.append((uid, info.get("name", f"Unit-{uid}")))

        if len(available) < 2:
            yield ui.dialog(
                "[b]분대 편성[/b]\n\n"
                "편성 가능한 에이전트가 부족합니다.\n"
                "(최소 리더 1 + 멤버 1 필요)",
            )
            return

        # 자동 편성 (데모: 전원 편입)
        sid = squad_module.create_squad()
        squad_module.assign_leader(sid, available[0][0])
        for uid, name in available[1:]:
            squad_module.add_member(sid, uid)

        # 대열 배치
        all_ids = squad_module.get_all_unit_ids(sid)
        for i, uid in enumerate(all_ids):
            rank = min(i + 1, 3)
            squad_module.set_member_rank(sid, uid, rank)

        names = [name for _, name in available]
        yield ui.dialog(
            "[b]분대 편성 완료[/b]\n\n"
            f"  분대장: {available[0][1]}\n"
            f"  대원: {', '.join(names[1:])}\n"
            f"  공세 레벨: 유지 (hold)\n\n"
            "+탐사 준비가 완료되었습니다.",
        )

        # 분대 편성 완료 → Step 9 → Step 10 자동 진행
        from events.progression import complete_step
        complete_step(9)

    def _manage_existing_squad(self, sq):
        """기존 분대 관리 (공세 레벨 변경/해산)"""
        import squad as squad_module
        import expedition as exp_module

        state = {"result": None}

        def handle_choice(action):
            if action == "init":
                return None
            state["result"] = action
            return True

        # 분대 상태 표시
        all_ids = sq.all_unit_ids()
        member_lines = []
        for uid in all_ids:
            info = morld.get_unit_info(uid)
            name = info.get("name", f"Unit-{uid}") if info else f"Unit-{uid}"
            rank = squad_module.get_member_rank(sq.squad_id, uid)
            rank_label = {1: "전위", 2: "중위", 3: "후위"}.get(rank, "?")
            is_leader = uid == sq.leader_id
            role = " (분대장)" if is_leader else ""
            member_lines.append(f"  [{rank_label}] {name}{role}")

        aggression_label = {
            "retreat": "전면 후퇴",
            "defensive": "방어 우선",
            "hold": "현 위치 유지",
            "combat_normal": "교전 허가",
            "combat_aggressive": "적극 공격",
        }.get(sq.aggression, sq.aggression)

        lines = [
            "[b]분대 관리[/b]\n",
            *member_lines,
            f"\n  공세 레벨: {aggression_label}\n",
        ]

        # 원정 중이면 추가 정보
        exp_state = exp_module.get_expedition_by_squad(sq.squad_id)
        if exp_state and exp_state.status == "active":
            lines.append(
                f"  탐사 중: {len(exp_state.explored_rooms)}/{len(exp_state.rooms)} 구역 탐색\n"
            )

        lines.append("[url=@proc:aggression]공세 레벨 변경[/url]")
        lines.append("[url=@proc:disband]해산[/url]")
        lines.append("[url=@proc:close]닫기[/url]")

        yield ui.dialog(
            "\n".join(lines),
            autofill="off",
            proc=handle_choice,
            result=state,
        )

        if state["result"] == "aggression":
            yield from self._change_aggression(sq)
        elif state["result"] == "disband":
            squad_module.disband_squad(sq.squad_id)
            yield ui.dialog("분대가 해산되었습니다.")

    def _change_aggression(self, sq):
        """공세 레벨 변경"""
        import squad as squad_module

        state = {"result": None}

        def handle_choice(action):
            if action == "init":
                return None
            state["result"] = action
            return True

        yield ui.dialog(
            "[b]공세 레벨 설정[/b]\n\n"
            "[url=@proc:retreat]전면 후퇴[/url]\n"
            "[url=@proc:defensive]방어 우선[/url]\n"
            "[url=@proc:hold]현 위치 유지[/url]\n"
            "[url=@proc:combat_normal]교전 허가[/url]\n"
            "[url=@proc:combat_aggressive]적극 공격[/url]",
            autofill="off",
            proc=handle_choice,
            result=state,
        )

        if state["result"] and state["result"] in squad_module.AGGRESSION_LEVELS:
            squad_module.set_aggression(sq.squad_id, state["result"])
            label = {
                "retreat": "전면 후퇴",
                "defensive": "방어 우선",
                "hold": "현 위치 유지",
                "combat_normal": "교전 허가",
                "combat_aggressive": "적극 공격",
            }.get(state["result"], state["result"])
            yield ui.dialog(f"공세 레벨이 [{label}]로 변경되었습니다.")

    def order_advance(self):
        """진군 명령 — 다음 미탐색 방으로 이동"""
        import squad as squad_module
        import expedition as exp_module
        from events.first_mission import handle_room_entered

        squads = squad_module.get_all_squads()
        if not squads:
            yield ui.dialog("편성된 분대가 없습니다.")
            return

        sq = squads[0]
        exp_state = exp_module.get_expedition_by_squad(sq.squad_id)
        if not exp_state or exp_state.status != "active":
            yield ui.dialog("진행 중인 탐사가 없습니다.")
            return

        # 이동 가능한 방 목록
        explorable = exp_module.get_explorable_rooms(exp_state.expedition_id)
        if not explorable:
            yield ui.dialog("더 이상 이동할 수 있는 구역이 없습니다.\n퇴각을 고려하세요.")
            return

        # 미탐색 방 우선, 없으면 아무 방
        unexplored = [r for r in explorable if not r["explored"]]
        target = unexplored[0] if unexplored else explorable[0]

        success, room, msg = exp_module.move_to_room(
            exp_state.expedition_id, target["id"])
        if not success:
            yield ui.dialog(f"이동 실패: {msg}")
            return

        # 방 이벤트 (전투/전리품) 처리
        gen = handle_room_entered(exp_state.expedition_id, target["id"])
        if gen:
            yield from gen

        # 목표 지점 도달 체크
        if room and room.get("type") == "objective":
            yield ui.dialog(
                "[b]비서[/b]\n\n"
                "목표 지점에 도달했습니다.\n"
                "+필요한 자재를 수집한 뒤 퇴각하세요.",
            )

    def order_retreat(self):
        """퇴각 명령 — 운영 모드에서는 주기 마감(보고서) + 보급까지 진행"""
        import cycle
        import squad as squad_module
        import expedition as exp_module
        from events.first_mission import retreat_expedition
        from events.progression import complete_step, is_step

        squads = squad_module.get_all_squads()
        exp_state = None
        if squads:
            exp_state = exp_module.get_expedition_by_squad(squads[0].squad_id)
        if not exp_state:
            # 전멸 등으로 분대 없이 남은 원정 회수
            actives = exp_module.get_active_expeditions()
            exp_state = actives[0] if actives else None
        if not exp_state or exp_state.status != "active":
            yield ui.dialog("진행 중인 탐사가 없습니다.")
            return

        gen = retreat_expedition(exp_state.squad_id)
        if gen:
            yield from gen

        # 완료 처리
        summary = exp_module.complete_expedition(exp_state.expedition_id)

        if cycle.is_active():
            # 주기 마감: 사후 운용 보고서 → 보급 → 다음 주기
            report = cycle.complete_cycle(summary)
            yield ui.dialog(cycle.build_report_text(report))
            supply = cycle.run_supply_phase()
            if supply:
                yield from self._supply_dialog(supply)
        else:
            # 튜토리얼(데모) 흐름: Step 12 → 13 → 14 진행
            if is_step(11) or is_step(12):
                complete_step(12)
                complete_step(13)

    def _supply_dialog(self, supply):
        """보급 열차 도착 안내 (정기 배급 + 결번 대체 개체)"""
        import cycle
        import npc_dialogue

        lines = [f"[b]보급 — 운행 주기 {supply['cycle']}[/b]\n"]
        greet = npc_dialogue.secretary_line("greet")
        if greet:
            lines.append(f"비서: 「{greet}」\n")

        mat_text = ", ".join(f"{u} x{c}" for u, c in supply["materials"].items())
        lines.append(f"  정기 배급: {mat_text}")

        for rep in supply["replacements"]:
            role_label = cycle.ROLE_LABELS.get(rep["role_key"], rep["role_key"])
            lines.append(
                f"\n[i]\"잠시 후 1번선 하행선으로, 보급 개체 {rep['name']}"
                f"이(가) 도착합니다.\"[/i]")
            lines.append(f"  {rep['name']} ({role_label}) — H.I {rep['humanity']}%")
            hello = npc_dialogue.member_daily_line(rep["unit_id"], "greet")
            if hello:
                lines.append(f"  {hello}")

        lines.append("\n+출발 준비가 완료되면 [탐사 출발]을 지시하세요.")
        yield ui.dialog("\n".join(lines))

    def get_focus_text(self):
        """포커스 묘사"""
        return "구형 CRT 모니터. 녹색 문자가 깜빡이고 있다. 이것이 오퍼레이터의 눈이다."
