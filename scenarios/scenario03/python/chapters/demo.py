# chapters/demo.py - 데모 챕터
#
# 시나리오03 데모: 지저 세계 오퍼레이터 첫 임무
# - Region 0: 플랫폼 (베이스캠프) — 승강장, 중앙 통로, 통신실
# - Region 1: 지저철 내부 — 객차 1량
# - 비서 NPC 배치 (통신실)
# - 시간 정지 + UI 잠금 → post_restore에서 프롤로그 이벤트 발동

import morld

TIME_SETTINGS = {
    "year": 1,
    "month": 1,
    "day": 1,
    "hour": 9,
    "minute": 0,
}


def initialize():
    """데모 챕터 초기화"""
    print("[demo] Initializing demo chapter...")

    # 0. 시간 정지 + UI Lock (프롤로그 진행 전 조작 제한)
    morld.set_time_frozen(True)

    import ui
    ui.set_ui_lock(True)

    # 1. 전체 월드 초기화 (Region + Gate)
    from world import initialize_world
    initialize_world()

    # 2. 시간 설정
    t = TIME_SETTINGS
    morld.set_time(t["year"], t["month"], t["day"], t["hour"], t.get("minute", 0))

    # 3. NPC 배치
    _instantiate_npcs()

    # 4. 오브젝트 배치
    _instantiate_objects()

    # 5. 건축 레시피 등록
    import build as build_module
    build_module.reset()
    build_module.register_demo_recipes()

    # 6. 분대/원정/맵/운영 루프 초기화
    import squad
    squad.reset()
    import expedition
    expedition.reset()
    import mapgen
    mapgen.reset()
    import cycle
    cycle.reset()
    import npc_dialogue
    npc_dialogue.clear_cache()

    print("[demo] Demo chapter initialized: 2 regions, 4 locations, 1 NPC")


def post_restore():
    """
    챕터 로드 후 호출 — 진행 시스템 초기화 + 프롤로그 이벤트 발동

    시간 정지 + UI 잠금 상태에서 프롤로그 시작.
    프롤로그 완료 후 set_time_frozen(False) + set_ui_lock(False)로 해제.
    """
    # 진행 시스템 초기화 + Step 1 진입
    from events.progression import reset, advance_to
    reset()
    advance_to(1)

    # 프롤로그 이벤트 트리거
    from events.prologue import trigger_prologue
    trigger_prologue()


def _instantiate_npcs():
    """플레이어/NPC 인스턴스화 + Agent 등록"""
    from assets.characters.operator import Operator
    from assets.characters.secretary import Secretary
    from think.agents.secretary_agent import SecretaryAgent
    from think import register_agent

    # 오퍼레이터(플레이어) — 통신실(R0, L2) 상주.
    # unique_id="player" 등록으로 C# PlayerId 자동 설정 → CRT 액션 노출 성립
    player = Operator()
    player_id = morld.create_id("unit")
    player.instantiate(player_id, 0, 2)

    # 비서 — 통신실(R0, L2) 배치
    secretary = Secretary()
    secretary_id = morld.create_id("unit")
    secretary.instantiate(secretary_id, 0, 2)  # Region 0, Location 2 (통신실)

    # Agent 등록
    agent = SecretaryAgent(secretary_id)
    register_agent(secretary_id, agent)

    print(f"[demo] Operator(player id={player_id}) + Secretary(id={secretary_id}) "
          "placed at comm_room")


def _instantiate_objects():
    """오브젝트 인스턴스화"""
    from assets.objects.train import SubwayTrain, CRTConsole

    # 지저철 — 승강장(R0, L0)에 배치
    train = SubwayTrain()
    train_id = morld.create_id("unit")
    train.instantiate(train_id, 0, 0, x=100)  # 승강장 중앙

    # CRT 콘솔 — 통신실(R0, L2)에 배치
    console = CRTConsole()
    console_id = morld.create_id("unit")
    console.instantiate(console_id, 0, 2, x=20)  # 통신실 내부

    print(f"[demo] Objects placed: SubwayTrain(id={train_id}), CRTConsole(id={console_id})")
