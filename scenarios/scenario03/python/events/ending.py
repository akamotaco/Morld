# events/ending.py - 튜토리얼 종료 → 정규 운영 개시 (Step 14)
#
# MVP: 데모 14단계는 튜토리얼로 재해석. 첫 임무 완료 후 반복 운영 루프(cycle.py)에
# 진입한다. 이후 게임은 보급 → 편성 → 탐사 → 귀환 → 보고서 주기를 반복.

import morld
import ui


def handle_ending():
    """Step 14: 튜토리얼 종료 + 정규 운영 개시

    트리거: 임무 완료 보고 (Step 13) 후 자동
    """
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "첫 임무가 성공적으로 완료되었습니다.\n"
        "+종합 보고를 드리겠습니다.",
    )

    # 통계 수집
    import squad as squad_module
    agent_count = sum(len(s.members) + (1 if s.leader_id else 0)
                      for s in squad_module.get_all_squads())

    yield ui.dialog(
        "[b]제3지저관리구역 — 종합 보고[/b]\n\n"
        "  거점: 플랫폼 (기본 시설 건설 완료)\n"
        f"  에이전트: {max(agent_count, 4)}명 활동 중\n"
        "  탐사: 1회 완료\n"
        "  수집 자재: 확인 완료\n\n"
        "+시운전 평가: 적합. 정규 운영을 개시합니다.",
    )

    # 정규 운영 개시 — 반복 탐사 루프 진입
    import cycle
    cycle.start_operations()

    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "지금부터는 정규 운행 주기입니다.\n"
        "+매 주기: 보급 → 분대 편성 → 탐사 → 귀환 → 보고.\n"
        "+CRT 콘솔의 [탐사 출발]로 다음 탐사를 지시하세요.",
    )

    yield ui.dialog(
        "[i]CRT 화면이 한 번 깜빡인다.\n"
        "녹색 커서가 조용히 점멸하고 있다.[/i]\n\n"
        "[i]\"안전한 운행은 정확한 관리에서 시작됩니다.\"[/i]",
    )

    print("[ending] Tutorial complete - operations started.")
