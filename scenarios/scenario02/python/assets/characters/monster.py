# assets/characters/monster.py — 몬스터 캐릭터 Asset
#
# Monster(Character) 기본 클래스 + 구체 서브클래스
# - DROP_TABLE: 스폰 시 인벤토리에 아이템 생성 (사망 후 루팅)
# - HARVEST_TABLE: 시체에서 도구로 수확하는 소재 (props 기반)
# - BATTLE_BEHAVIOR: think Tier 2 전투 AI 파라미터

import morld
from assets.base import Character
from assets.registry import register_item


class Monster(Character):
    """몬스터 기본 클래스 — Character 서브클래스"""
    type = "character"
    owner = None

    props = {
        "전투:적대유형": "monster",
        "생존:체력": 30,
        "생존:최대체력": 30,
        "전투:공격력": 5,
        "전투:방어력": 2,
        "전투:명중": 70,
        "전투:회피": 10,
        "전투:치명타": 3,
        "전투:사거리": 60,
        "전투:공격속도": 1.0,
        "전투:감지거리": 100,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 60,
        "retreat_threshold": 0.2,
    }

    # 포커스 시 공격만 가능 (대화/스킨십 불가)
    actions = ["call:attack:공격#"]

    # 인벤토리 드롭 테이블
    # 형식: [{"item": "unique_id", "chance": 0.0~1.0, "count": int or (min,max)}]
    DROP_TABLE = []

    # 소재 수확 테이블 (시체에서 도구로 수확)
    # 형식: {"소재:키": {"item": "unique_id", "name": "표시명",
    #                    "tool_prop": "날붙이", "time_ms": 10000}}
    HARVEST_TABLE = {}

    # 24시간 순찰 스케줄
    SCHEDULE = [
        {"name": "순찰", "start": 0, "end": 86_400_000, "activity": "순찰"},
    ]

    def _populate_inventory(self):
        """스폰 시 드롭 테이블 기반 인벤토리 생성"""
        import random
        from assets.registry import get_or_create_item_id

        for entry in self.DROP_TABLE:
            if random.random() > entry["chance"]:
                continue
            count = entry["count"]
            if isinstance(count, tuple):
                count = random.randint(count[0], count[1])
            item_id = get_or_create_item_id(entry["item"])
            morld.give_item(self.instance_id, item_id, count)


class Wolf(Monster):
    """늑대 — 숲 지역 서식, 공격적"""
    unique_id = "wolf"
    name = "늑대"

    props = {
        **Monster.props,
        "생존:체력": 40,
        "생존:최대체력": 40,
        "전투:공격력": 8,
        "전투:방어력": 3,
        "전투:명중": 75,
        "전투:회피": 15,
        "전투:사거리": 70,
        "전투:감지거리": 120,
        # 수확 가능 소재 (props에 수량 등록)
        "소재:가죽": 2,
        "소재:이빨": 1,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 70,
        "retreat_threshold": 0.2,
    }

    DROP_TABLE = [
        {"item": "meat", "chance": 0.8, "count": (1, 2)},
    ]

    HARVEST_TABLE = {
        "소재:가죽": {
            "item": "wolf_pelt",
            "name": "늑대 가죽",
            "tool_prop": "날붙이",
            "time_ms": 10_000,
        },
        "소재:이빨": {
            "item": "wolf_fang",
            "name": "늑대 이빨",
            "tool_prop": "날붙이",
            "time_ms": 5_000,
        },
    }


class Bat(Monster):
    """박쥐 — 폐광산 1층, 빠르고 회피 높지만 약함"""
    unique_id = "bat"
    name = "박쥐"

    props = {
        **Monster.props,
        "생존:체력": 15,
        "생존:최대체력": 15,
        "전투:공격력": 3,
        "전투:방어력": 1,
        "전투:명중": 65,
        "전투:회피": 25,
        "전투:치명타": 5,
        "전투:사거리": 50,
        "전투:감지거리": 80,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",
        "target_priority": "nearest",
        "preferred_range": 50,
        "retreat_threshold": 0.3,
    }

    DROP_TABLE = [
        {"item": "meat", "chance": 0.5, "count": 1},
    ]


class Spider(Monster):
    """거미 — 폐광산 2층/깊은 갱도, 공격적"""
    unique_id = "spider"
    name = "거미"

    props = {
        **Monster.props,
        "생존:체력": 50,
        "생존:최대체력": 50,
        "전투:공격력": 6,
        "전투:방어력": 4,
        "전투:명중": 75,
        "전투:회피": 10,
        "전투:치명타": 8,
        "전투:사거리": 70,
        "전투:감지거리": 100,
        # 수확 가능 소재
        "소재:독낭": 1,
        "소재:거미줄": 2,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 70,
        "retreat_threshold": 0.15,
    }

    HARVEST_TABLE = {
        "소재:독낭": {
            "item": "spider_venom",
            "name": "거미독",
            "tool_prop": "날붙이",
            "time_ms": 8_000,
        },
        "소재:거미줄": {
            "item": "spider_silk",
            "name": "거미줄",
            "tool_prop": None,
            "time_ms": 3_000,
        },
    }


class TrainingDummy(Character):
    """훈련용 허수아비 — 반격 없음, HP 999"""
    unique_id = "training_dummy"
    name = "허수아비"
    type = "character"
    owner = None

    props = {
        "생존:체력": 999,
        "생존:최대체력": 999,
        "전투:방어력": 0,
        "전투:회피": 0,
    }

    actions = ["call:attack:공격#"]
    # BATTLE_BEHAVIOR 없음 → think에서 전투 안 함
