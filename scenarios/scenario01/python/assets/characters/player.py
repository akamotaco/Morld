# assets/characters/player.py - 플레이어 캐릭터 Asset
# 방 탈출 시나리오: 정체불명의 주인공

from assets.base import Character


class Player(Character):
    """플레이어 캐릭터"""
    unique_id = "player"
    name = "플레이어"
    type = "male"
    props = {
        # 아이템 조작
        "can:take": 1,

        # 오브젝트 조사/조작 (call: 액션용)
        "can:examine": 1,   # 조사
        "can:toggle": 1,    # 스위치 조작
        "can:unlock": 1,    # 열쇠로 잠금 해제
        "can:open": 1,      # 비밀번호로 열기

        # 탈출 (call: 액션 - entrance.py)
        "can:escape": 1,

        # 아이템 사용 (call: 액션용)
        "can:read": 1,      # 문서/쪽지 읽기
        "can:combine": 1,   # 아이템 조합

        # 비밀번호 입력 시스템 (다이얼로그 내부에서 사용)
        "can:input_digit": 1,
        "can:input_study_digit": 1,
        "can:cancel_password": 1,
        "can:verify_password": 1,
        "can:verify_study_password": 1,

        # 엔딩 관련
        "can:show_ending": 1,
        "can:show_ending_credits": 1,
    }
    actions = []
    mood = []
