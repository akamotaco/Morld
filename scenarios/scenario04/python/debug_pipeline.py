# debug_pipeline.py — 파이프라인 디버그 실행
#
# 플레이어(리더) → NPC 모집 → 일자 던전 → 마을 복귀 전체 플로우를
# Python 레벨에서 자동 실행.
#
# 게임 UI/액션 바인딩 전 단계에서 시스템 연동을 검증하기 위함.
# 호출: `debug_pipeline.run()` (챕터 로드 후)

import morld
import linear_dungeon as ld
import recruit
import player_mode as pm
from engine import party_group as _pg


def run(*, dungeon_length: int = 5, max_recruits: int = 2, verbose: bool = True) -> dict:
    """파이프라인 자동 실행.

    Args:
        dungeon_length: 일자 던전 노드 수 (exit 포함)
        max_recruits: 모집할 최대 NPC 수
        verbose: print 로그 여부

    Returns:
        {"recruits": [uid], "dungeon_log": [str], "outcome": "returned"|"cleared"|"aborted"}
    """
    log = []

    def _p(msg):
        log.append(msg)
        if verbose:
            print(msg)

    player_id = morld.get_player_id()
    if not player_id:
        _p("[debug_pipeline] no player — abort")
        return {"recruits": [], "dungeon_log": log, "outcome": "aborted"}

    # 플레이어 파티 상태 확인
    if not pm.is_leader():
        _p("[debug_pipeline] player is not leader — abort")
        return {"recruits": [], "dungeon_log": log, "outcome": "aborted"}

    # 1. NPC 모집 — 여관 체류 NPC 중에서 시도
    recruited = _try_recruit(max_recruits, _p)
    _p(f"[debug_pipeline] Recruited {len(recruited)} NPCs: {recruited}")

    # 2. 일자 던전 진입
    ld.enter(depth=dungeon_length)

    # 3. 노드 자동 진행
    outcome = _auto_progress(_p)

    # 4. 결과
    return {
        "recruits": recruited,
        "dungeon_log": log + ld.get_log(),
        "outcome": outcome,
    }


def _try_recruit(max_count: int, log_fn) -> list:
    """npc_generator 체류 NPC 중 파티 후보로 등록된 NPC 모집 시도."""
    recruited = []
    try:
        import npc_generator
        candidates = npc_generator.get_party_candidates()
    except ImportError:
        log_fn("[debug_pipeline] npc_generator not available — skip recruit")
        return []

    for cand in candidates:
        if len(recruited) >= max_count:
            break
        uid = cand.get("unit_id") if isinstance(cand, dict) else cand
        if uid is None:
            continue
        result = recruit.recruit(uid)
        if result["success"]:
            recruited.append(uid)
            log_fn(f"[debug_pipeline]   recruited {uid} ({cand.get('name', '?')})")
        else:
            log_fn(f"[debug_pipeline]   recruit failed {uid}: {result['result']}")
    return recruited


def _auto_progress(log_fn) -> str:
    """던전 노드를 자동 진행 (분기는 첫 옵션 선택, 전투 패배 시 abort)."""
    max_iters = 50
    for _ in range(max_iters):
        if not ld.is_active():
            return "returned"

        node = ld.get_current_node()
        if node is None:
            return "aborted"

        t = node["type"]

        # EXIT: 마을 귀환
        if t == ld.NODE_EXIT:
            ld.exit_to_village(reason="cleared_end")
            return "cleared"

        # START: 이벤트 없음, 다음 노드로 진행
        if t == ld.NODE_START:
            if not node["paths"]:
                log_fn("[debug_pipeline] START dead-end — abort")
                return "aborted"
            ld.advance(node["paths"][0])
            continue

        # BATTLE/REST: 노드 처리 → 결과 확인 → advance
        result = ld.process_current_node()
        node_result = result.get("result")

        if t == ld.NODE_BATTLE:
            if node_result != "victory":
                log_fn(f"[debug_pipeline] battle not won (result={node_result}) — abort")
                return "aborted"

        # 다음 노드로 진행 (paths[0])
        if not node["paths"]:
            log_fn("[debug_pipeline] dead-end node — abort")
            return "aborted"
        adv = ld.advance(node["paths"][0])
        if not adv["ok"]:
            log_fn(f"[debug_pipeline] advance failed: {adv['reason']} — abort")
            return "aborted"

    log_fn("[debug_pipeline] max iterations reached — abort")
    return "aborted"
