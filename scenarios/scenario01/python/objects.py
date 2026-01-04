# objects.py - 시나리오01 플레이어 및 오브젝트 정의

import morld


def initialize_player():
    """플레이어 등록"""
    morld.add_unit(
        0,           # unit_id
        "플레이어",   # name
        0,           # region_id
        0,           # location_id (지하실에서 시작)
        "male",      # type
        [],          # actions
        {},          # appearance
        []           # mood
    )
    print("[objects] Registered player at 지하실")


def initialize_objects():
    """오브젝트 등록"""

    objects = [
        # === 지하실 (location 0) ===
        {
            "id": 100,
            "name": "낡은 상자",
            "region": 0,
            "location": 0,
            "actions": ["script:examine_object:조사"],
            "appearance": {
                "default": "구석에 먼지가 수북이 쌓인 낡은 나무 상자가 있다. 뚜껑이 살짝 들려 있어 안을 확인할 수 있을 것 같다."
            }
        },
        {
            "id": 101,
            "name": "배전함",
            "region": 0,
            "location": 0,
            "actions": ["script:toggle_switch:조작"],
            "appearance": {
                "default": "벽에 녹슨 금속 배전함이 설치되어 있다. 커다란 레버 스위치가 내려가 있다. '주의: 고압 전류'라고 적힌 경고문이 희미하게 보인다."
            }
        },

        # === 창고 (location 1) ===
        {
            "id": 102,
            "name": "선반",
            "region": 0,
            "location": 1,
            "actions": ["script:examine_object:조사"],
            "appearance": {
                "default": "벽에 붙은 나무 선반이다. 먼지와 거미줄 사이로 오래된 공구들과 깨진 유리병들이 흩어져 있다."
            }
        },
        {
            "id": 103,
            "name": "낡은 캐비닛",
            "region": 0,
            "location": 1,
            "actions": ["script:unlock_object:열기"],
            "appearance": {
                "default": "바닥에 세워진 낡은 철제 캐비닛이다. 녹슨 자물쇠가 달려 있다. 안에 뭔가 들어있는 것 같다.",
                "unlocked": "열린 캐비닛이다. 안에는 먼지만 남아있다."
            }
        },

        # === 거실 (location 2) ===
        {
            "id": 104,
            "name": "벽난로",
            "region": 0,
            "location": 2,
            "actions": ["script:examine_object:조사"],
            "appearance": {
                "default": "대리석 장식이 달린 오래된 벽난로다. 불을 피운 지 오래됐는지 재와 타다 남은 장작이 가득하다. 안쪽을 자세히 살펴보면 뭔가 있을지도..."
            }
        },
        {
            "id": 105,
            "name": "소파 쿠션",
            "region": 0,
            "location": 2,
            "actions": ["script:examine_object:조사"],
            "appearance": {
                "default": "한때 고급스러웠을 붉은 벨벳 소파다. 쿠션 사이가 벌어져 있어 무언가가 끼어있을 것 같다."
            }
        },

        # === 주방 (location 3) ===
        {
            "id": 106,
            "name": "냉장고",
            "region": 0,
            "location": 3,
            "actions": ["script:examine_object:조사"],
            "appearance": {
                "default": "1950년대 스타일의 오래된 냉장고다. 녹이 슬어 문이 삐걱거린다. 문에 무언가 붙어있다."
            }
        },
        {
            "id": 107,
            "name": "찬장",
            "region": 0,
            "location": 3,
            "actions": ["script:unlock_object:열기"],
            "appearance": {
                "default": "주방 구석에 놓인 큼지막한 찬장이다. 은색 자물쇠로 잠겨있다. 유리창 너머로 안에 뭔가 반짝이는 게 보인다.",
                "unlocked": "열린 찬장이다. 먼지 쌓인 접시들만 남아있다."
            }
        },

        # === 복도 1층 (location 4) ===
        {
            "id": 115,
            "name": "괘종시계",
            "region": 0,
            "location": 4,
            "actions": ["script:examine_clock:조사"],
            "appearance": {
                "default": "복도 끝에 서있는 커다란 괘종시계다. 시계는 멈춰있고, 시각은 18:42를 가리키고 있다. 문양이 새겨진 장식이 눈에 띈다."
            }
        },
        {
            "id": 116,
            "name": "우산꽂이",
            "region": 0,
            "location": 4,
            "actions": ["script:examine_umbrella:조사"],
            "appearance": {
                "default": "구리 재질의 우산꽂이다. 낡은 우산 몇 개와 지팡이가 꽂혀 있다. 바닥에 뭔가 떨어져 있는 것 같다."
            }
        },

        # === 계단 (location 5) ===
        {
            "id": 117,
            "name": "부서진 계단",
            "region": 0,
            "location": 5,
            "actions": ["script:examine_step:조사"],
            "appearance": {
                "default": "계단 중간에 부서진 단이 있다. 틈새로 무언가가 보이는 것 같기도 하다..."
            }
        },
        {
            "id": 118,
            "name": "창문",
            "region": 0,
            "location": 5,
            "actions": ["script:examine_window:조사"],
            "appearance": {
                "default": "계단 옆에 달린 창문이다. 두꺼운 커튼으로 가려져 있다. 밖으로 나갈 수 있을까?"
            }
        },

        # === 침실 (location 6) ===
        {
            "id": 108,
            "name": "침대 밑",
            "region": 0,
            "location": 6,
            "actions": ["script:examine_object:조사"],
            "appearance": {
                "default": "헤진 시트가 덮인 낡은 침대다. 침대 밑 어둠 속에 무언가가 있는 것 같다. 손을 넣어봐야 할 것 같다."
            }
        },
        {
            "id": 109,
            "name": "화장대 서랍",
            "region": 0,
            "location": 6,
            "actions": ["script:password_lock:열기"],
            "appearance": {
                "default": "화장대에 달린 작은 서랍이다. 4자리 숫자 잠금장치가 달려있다. 누군가 소중한 것을 숨겨둔 것 같다.",
                "unlocked": "열린 서랍이다. 화장품과 먼지만 남아있다."
            }
        },

        # === 서재 (location 7) ===
        {
            "id": 111,
            "name": "금고",
            "region": 0,
            "location": 7,
            "actions": ["script:password_lock:열기"],
            "appearance": {
                "default": "책상 옆에 놓인 묵직한 철제 금고다. 4자리 다이얼 자물쇠가 달려있다. 안에 중요한 것이 들어있을 것 같다.",
                "unlocked": "열린 금고다. 먼지와 오래된 서류 조각들만 남아있다."
            }
        },
        {
            "id": 112,
            "name": "책상 서랍",
            "region": 0,
            "location": 7,
            "actions": ["script:examine_object:조사"],
            "appearance": {
                "default": "낡은 오크나무 책상의 서랍이다. 손잡이가 녹슬었지만 열 수 있을 것 같다."
            }
        },

        # === 복도 2층 (location 8) ===
        {
            "id": 110,
            "name": "그림 액자",
            "region": 0,
            "location": 8,
            "actions": ["script:examine_object:조사"],
            "appearance": {
                "default": "벽에 비스듬히 걸린 오래된 풍경화다. 금박 액자 테두리가 벗겨져 있다. 그림 뒤에 뭔가 숨겨져 있을 것 같은 느낌이 든다."
            }
        },
        {
            "id": 114,
            "name": "서재 문",
            "region": 0,
            "location": 8,
            "actions": ["script:unlock_study_door:열기"],
            "appearance": {
                "default": "두꺼운 참나무 문이다. 전자식 4자리 비밀번호 잠금장치가 설치되어 있다.",
                "unlocked": "열린 서재 문이다. 안에서 오래된 책 냄새가 풍겨온다."
            }
        },

        # === 정문 홀 (location 9) ===
        {
            "id": 113,
            "name": "정문",
            "region": 0,
            "location": 9,
            "actions": ["script:escape:열기"],
            "appearance": {
                "default": "저택의 거대한 정문이다. 황금빛 자물쇠가 빛나고 있다. 이 문만 열면 자유다!"
            }
        },
    ]

    for obj in objects:
        morld.add_unit(
            obj["id"],
            obj["name"],
            obj["region"],
            obj["location"],
            "object",          # type
            obj["actions"],
            obj["appearance"],
            []                 # mood
        )

    print(f"[objects] Registered {len(objects)} objects")
