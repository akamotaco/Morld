# events/prologue.py - 프롤로그 이벤트 (Step 1~3)
#
# Step 1: 계약 — 검은 화면, 계약서 텍스트, 서명/거부 선택
# Step 2: 지저철 탑승 — 비서 소개, 이동 시간 경과
# Step 3: 플랫폼 도착 — CRT 뷰 활성화, 탐색 퀘스트 부여

import morld
import ui


def trigger_prologue():
    """프롤로그 이벤트 트리거 (post_restore에서 호출)

    Returns:
        Generator — C# 이벤트 시스템이 실행
    """
    # TODO: C# 이벤트 시스템 연동
    # 현재는 이벤트 함수만 정의. 실제 트리거는 C# GameStartEvent 등으로 연결 필요.
    print("[prologue] Prologue event triggered (awaiting C# integration)")


def handle_contract():
    """Step 1: 계약 이벤트

    검은 화면 → 계약서 텍스트 표시 → 서명/거부 선택
    """
    # TODO: AnimLog 클래스 — 시나리오02 ui 모듈에서 import
    # anim = AnimLog()
    # anim.text("", speed=0)  # 검은 화면
    # anim.text("계약서", speed=30)
    # anim.wait(1.0)
    # anim.text("본 계약에 서명함으로써...", speed=50)
    # anim.text("귀하는 제3지저관리구역 오퍼레이터로 임명되며...", speed=50)
    # anim.text("계약 기간 중 발생하는 모든 손실에 대해...", speed=50)
    # anim.text("상부는 책임을 지지 않습니다.", speed=50)
    # anim.wait(2.0)
    # yield anim.play(mode="lock")

    # 서명 선택
    state = {"result": None}

    def handle_choice(action):
        if action == "init":
            return None
        state["result"] = action
        return True

    yield ui.dialog(
        "[b]계약서[/b]\n\n"
        "본 계약에 서명함으로써...\n"
        "귀하는 제3지저관리구역 오퍼레이터로 임명되며...\n"
        "계약 기간 중 발생하는 모든 손실에 대해\n"
        "상부는 책임을 지지 않습니다.\n\n"
        "서명란 위에 펜이 놓여 있다.\n\n"
        "[url=@proc:sign]서명한다[/url]\n"
        "[url=@proc:refuse]거부한다[/url]",
        autofill="off",
        proc=handle_choice,
        result=state,
    )

    if state["result"] == "refuse":
        # 게임 종료 연출
        yield ui.dialog(
            "...\n\n"
            "계약이 거부되었습니다.",
        )
        # TODO: morld.quit_game() 호출
        return

    # 서명 완료 → Step 2로 진행
    yield from _start_train_sequence()


def _start_train_sequence():
    """Step 2: 지저철 탑승 → 비서 대화"""
    # 비서 소개 시퀀스
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "지저철이 출발합니다.\n"
        "+선로의 진동이 객차를 흔든다.",
    )
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "저는 상부에서 파견된 연락관입니다.\n"
        "+귀하의 임무를 보좌하겠습니다.",
    )
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "귀하는 제3지저관리구역의 오퍼레이터로 임명되셨습니다.\n"
        "+오퍼레이터는 원격으로 에이전트를 지휘합니다.",
    )
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "에이전트는... 설명이 필요할까요?\n"
        "+간단히 말씀드리자면, 귀하의 손과 발입니다.",
    )

    # 이동 시간 경과
    morld.advance_time_des(120 * 60_000)  # 2시간

    # Step 3으로
    yield from _arrive_at_platform()


def _arrive_at_platform():
    """Step 3: 플랫폼 도착"""
    yield ui.dialog(
        "지저철이 감속한다.\n\n"
        "승강장에 정차.",
    )

    # 시간 정지 해제 + UI Lock 해제
    morld.set_time_frozen(False)

    import ui as ui_module
    ui_module.set_ui_lock(False)

    # TODO: CRT 모드 전환 (시나리오03 전용 UI)
    # ui_module.set_view_mode("crt")

    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "여기가 제3구역 플랫폼입니다.\n"
        "+보시다시피... 황폐합니다.",
    )
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "통신실의 CRT 콘솔이 귀하의 눈과 귀가 됩니다.\n"
        "+모든 관찰과 지시는 이 콘솔을 통해 이루어집니다.",
    )

    # TODO: 플랫폼 탐색 퀘스트 부여
    # quest_manager.give_quest("demo_explore_platform")
    print("[prologue] Platform arrival complete. Explore quest pending.")
