# events/first_mission.py - 첫 임무 이벤트 (Step 7~13)
#
# MissionBriefingEvent: 비서의 임무 브리핑 (건설 완료 후)
# MissionCompleteEvent: 귀환 후 임무 완료 보고

import morld
import ui


def handle_mission_briefing():
    """Step 7: 첫 임무 브리핑

    트리거: 기본 플랫폼 건설 완료 (임시 막사 + 보관소)
    """
    state = {"result": None}

    def handle_choice(action):
        if action == "init":
            return None
        state["result"] = action
        return True

    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "기본 시설이 갖춰졌습니다. 첫 임무를 시작하겠습니다.\n"
        "인근 구역에서 보수 자재를 수집해야 합니다.\n"
        "분대를 편성하여 탐사를 진행하세요.\n\n"
        "[url=@proc:detail]자세히 알려줘[/url]\n"
        "[url=@proc:accept]알겠다[/url]",
        autofill="off",
        proc=handle_choice,
        result=state,
    )

    if state["result"] == "detail":
        yield ui.dialog(
            "[b]비서[/b]\n\n"
            "금속 파이프 5개, 콘크리트 블록 3개가 필요합니다.\n"
            "탐사 지역에서 수집하여 귀환하세요.",
        )
    else:
        yield ui.dialog(
            "[b]비서[/b]\n\n"
            "행운을 빕니다.",
        )

    # TODO: 퀘스트 부여
    # quest_manager.give_quest("demo_first_expedition")
    # quest_manager.accept_quest("demo_first_expedition")
    print("[first_mission] Mission briefing complete. Quest pending.")


def handle_mission_complete():
    """Step 13: 임무 완료 보고

    트리거: 플랫폼 도착 후 비서 대화
    """
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "탐사 임무가 완료되었습니다.\n"
        "+수집된 자재를 확인하겠습니다.",
    )

    # TODO: 수집량 표시 (분대원 인벤토리 합산)
    # collected = _count_squad_inventory()
    # for item_name, count in collected.items():
    #     yield ui.dialog(f"+  {item_name}: {count}개")

    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "수고하셨습니다.\n"
        "+수집된 자재는 보관소로 이동됩니다.",
    )

    # TODO: 퀘스트 보상 처리
    # quest_manager.claim_reward("demo_first_expedition")
    print("[first_mission] Mission complete. Reward pending.")


def start_expedition(squad_id):
    """Step 9: 탐사 출발 시퀀스

    1. 탐사 지역 동적 생성
    2. 분대원 지저철 탑승
    3. 지저철 이동
    4. 도착 → Gate 재연결

    Args:
        squad_id: 분대 ID (party.py)
    """
    # TODO: mapgen 연동 — 탐사 지역 동적 생성
    # expedition_region = 100
    # from mapgen import generate_expedition
    # rooms, connections = generate_expedition(
    #     region_id=expedition_region,
    #     difficulty="easy",
    #     room_count=(5, 8),
    #     seed=None,
    # )

    # TODO: 분대원 탑승 → 이동 → 도착
    # members = party.get_squad_members(squad_id)
    # for member_id in members:
    #     party.set_order(squad_id, member_id, Order(order_type="move", ...))
    # morld.advance_time_des(10 * 60_000)  # 10분

    # train_id = get_instance_id("subway_train")
    # vehicle.vehicle_move_to(train_id, dest_region=100, ...)

    print(f"[first_mission] Expedition start for squad {squad_id} (not yet implemented)")


def retreat_expedition(squad_id, expedition_region):
    """Step 11~12: 탐사 귀환 시퀀스

    Args:
        squad_id: 분대 ID
        expedition_region: 탐사 지역 Region ID
    """
    # TODO: 분대원 귀환 → 지저철 탑승 → 플랫폼 복귀
    # TODO: 동적 Region 정리 (mapgen.cleanup_expedition)
    print(f"[first_mission] Retreat from region {expedition_region} (not yet implemented)")
