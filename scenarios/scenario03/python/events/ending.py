# events/ending.py - 엔딩 이벤트 (Step 14)
#
# 데모 엔딩: 첫 임무 완료 후 비서 종합 보고 + 계속 안내

import morld
import ui


def handle_ending():
    """Step 14: 데모 엔딩

    트리거: 임무 완료 보고 (Step 13) 후 자동
    """
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "첫 임무가 성공적으로 완료되었습니다.\n"
        "+종합 보고를 드리겠습니다.",
    )

    # TODO: 실제 통계 수집 (건설 현황, 수집량, 부상자 등)
    yield ui.dialog(
        "[b]제3지저관리구역 — 종합 보고[/b]\n\n"
        "  거점: 플랫폼 (기본 시설 건설 완료)\n"
        "  에이전트: 4명 활동 중\n"
        "  탐사: 1회 완료\n"
        "  수집 자재: 확인 완료\n\n"
        "+이상으로 데모 시퀀스를 종료합니다.",
    )

    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "이 구역에는 아직 밝혀지지 않은 것들이 많습니다.\n"
        "+선로 너머에 무엇이 있는지...\n"
        "+곧 알게 되실 겁니다.",
    )

    yield ui.dialog(
        "[i]CRT 화면이 한 번 깜빡인다.\n"
        "녹색 커서가 조용히 점멸하고 있다.[/i]\n\n"
        "[b]— 데모 종료 —[/b]",
    )

    # 데모 완료 플래그
    from events.progression import complete_step
    # Step 14는 마지막이므로 complete_step은 False 반환 (더 이상 진행 없음)
    print("[ending] Demo sequence complete.")
