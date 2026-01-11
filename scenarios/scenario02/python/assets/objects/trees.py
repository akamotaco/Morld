# assets/objects/trees.py - 나무 오브젝트
#
# 나무 베이스 클래스 및 서브클래스
# - Tree: 통나무/나뭇가지 획득 가능한 나무 베이스
# - PineTree: 소나무
# - OakTree: 참나무
#
# props 기반 자원 관리:
# - "자원:통나무": 현재 통나무 개수
# - "자원:나뭇가지": 현재 나뭇가지 개수
#
# 확률 기반 획득 (낚시 패턴 참고)

import random
import morld
from assets.base import Object
from assets.registry import get_item_class


class Tree(Object):
    """
    나무 베이스 클래스 - 통나무/나뭇가지 획득

    props 기반 자원 관리:
    - 컨테이너(인벤토리) 대신 props로 개수 관리
    - OnTimeElapsed 이벤트로 자동 보충 (resource_agent)

    Attributes:
        max_logs: 최대 통나무 개수
        max_branches: 최대 나뭇가지 개수
        log_chance: 통나무 획득 확률 (0.0 ~ 1.0)
        branch_chance: 나뭇가지 획득 확률 (0.0 ~ 1.0)
        initial_logs: 초기 통나무 개수
        initial_branches: 초기 나뭇가지 개수
    """
    unique_id = "tree"
    name = "나무"

    # props 기반 자원 설정
    max_logs = 3
    max_branches = 5

    # 초기 자원 개수
    initial_logs = 2
    initial_branches = 3

    # 확률 설정
    log_chance = 0.6      # 60%
    branch_chance = 0.8   # 80%

    # 시간 소요
    chop_time = 15        # 벌목 15분
    gather_time = 5       # 가지 줍기 5분

    actions = [
        "call:look:살펴보기",
        "call:chop:벌목",           # can:chop 필요 (도끼 장착)
        "call:gather:가지 줍기",    # 도구 불필요
        "call:debug_props:속성 보기"
    ]

    focus_text = {
        "default": "커다란 나무다. 도끼가 있으면 벨 수 있을 것 같다."
    }

    def instantiate(self, instance_id: int, region_id: int = None, location_id: int = None):
        """나무 인스턴스화 - 초기 자원 설정 및 resource_agent 등록"""
        super().instantiate(instance_id, region_id, location_id)

        # 초기 자원 설정
        self.set_log_count(self.initial_logs)
        self.set_branch_count(self.initial_branches)

        # resource_agent에 등록 (자동 보충용)
        from think.resource_agent import register_tree_object
        register_tree_object(instance_id, self.unique_id)

    def get_log_count(self) -> int:
        """현재 통나무 개수 (props에서 조회)"""
        if not self._instantiated:
            return 0
        props = morld.get_unit_props(self.instance_id)
        return props.get("자원:통나무", 0)

    def get_branch_count(self) -> int:
        """현재 나뭇가지 개수 (props에서 조회)"""
        if not self._instantiated:
            return 0
        props = morld.get_unit_props(self.instance_id)
        return props.get("자원:나뭇가지", 0)

    def set_log_count(self, count: int):
        """통나무 개수 설정"""
        morld.set_unit_prop(self.instance_id, "자원:통나무", max(0, min(count, self.max_logs)))

    def set_branch_count(self, count: int):
        """나뭇가지 개수 설정"""
        morld.set_unit_prop(self.instance_id, "자원:나뭇가지", max(0, min(count, self.max_branches)))

    def can_chop(self) -> bool:
        """벌목 가능 여부 (통나무 남아있는지)"""
        return self.get_log_count() > 0

    def can_gather(self) -> bool:
        """가지 줍기 가능 여부 (나뭇가지 남아있는지)"""
        return self.get_branch_count() > 0

    def get_focus_text(self):
        """현재 상태에 따른 묘사"""
        logs = self.get_log_count()
        branches = self.get_branch_count()

        if logs > 0 and branches > 0:
            return f"{self.name}. 통나무를 {logs}개 얻을 수 있고, 나뭇가지도 {branches}개 정도 보인다."
        elif logs > 0:
            return f"{self.name}. 통나무를 {logs}개 정도 얻을 수 있을 것 같다."
        elif branches > 0:
            return f"{self.name}. 나뭇가지가 {branches}개 정도 떨어져 있다."
        else:
            return f"{self.name}. 지금은 얻을 수 있는 게 없어 보인다."

    def look(self):
        """나무 살펴보기"""
        logs = self.get_log_count()
        branches = self.get_branch_count()

        lines = [f"{self.name}를 살펴본다."]

        if logs > 0:
            lines.append(f"벌목하면 통나무를 얻을 수 있을 것 같다. (약 {logs}개)")
        else:
            lines.append("지금은 벌목해도 통나무를 얻기 어려워 보인다.")

        if branches > 0:
            lines.append(f"주변에 나뭇가지가 떨어져 있다. ({branches}개)")
        else:
            lines.append("주변에 나뭇가지가 보이지 않는다.")

        yield morld.dialog(lines)
        morld.advance_time(1)

    def chop(self):
        """
        벌목 - can:chop 필요 (도끼 장착)

        확률 기반 통나무 획득 (낚시 패턴 참고)
        """
        # 통나무 남아있는지 확인
        if not self.can_chop():
            yield morld.dialog([
                f"{self.name}를 벌목하려 했지만...",
                "지금은 얻을 수 있는 통나무가 없다."
            ])
            return

        yield morld.dialog(f"{self.name}를 벌목한다...")
        morld.advance_time(self.chop_time)

        # 확률 체크
        if random.random() < self.log_chance:
            player_id = morld.get_player_id()

            # 통나무 아이템 ID 조회 또는 생성
            log_id = morld.get_item_id_by_unique("log")
            if log_id is None:
                log_class = get_item_class("log")
                if log_class:
                    log_item = log_class()
                    log_id = morld.create_id("item")
                    log_item.instantiate(log_id)
                else:
                    yield morld.dialog("통나무를 얻었지만, 놓쳐버렸다.")
                    return

            # 통나무 지급 및 자원 감소
            morld.give_item(player_id, log_id, 1)
            self.set_log_count(self.get_log_count() - 1)

            yield morld.dialog([
                "통나무를 얻었다!",
                "무거운 통나무다."
            ])
        else:
            yield morld.dialog([
                "열심히 벌목했지만...",
                "쓸만한 통나무를 얻지 못했다."
            ])

    def gather(self):
        """
        나뭇가지 줍기 - 도구 불필요

        확률 기반 나뭇가지 획득
        """
        # 나뭇가지 남아있는지 확인
        if not self.can_gather():
            yield morld.dialog([
                f"{self.name} 주변을 둘러보았지만...",
                "주울 만한 나뭇가지가 없다."
            ])
            return

        yield morld.dialog(f"{self.name} 주변에서 나뭇가지를 줍는다...")
        morld.advance_time(self.gather_time)

        # 확률 체크
        if random.random() < self.branch_chance:
            player_id = morld.get_player_id()

            # 나뭇가지 아이템 ID 조회 또는 생성
            branch_id = morld.get_item_id_by_unique("branch")
            if branch_id is None:
                branch_class = get_item_class("branch")
                if branch_class:
                    branch_item = branch_class()
                    branch_id = morld.create_id("item")
                    branch_item.instantiate(branch_id)
                else:
                    yield morld.dialog("나뭇가지를 주웠지만, 놓쳐버렸다.")
                    return

            # 나뭇가지 지급 및 자원 감소
            morld.give_item(player_id, branch_id, 1)
            self.set_branch_count(self.get_branch_count() - 1)

            yield morld.dialog([
                "나뭇가지를 주웠다!",
                "불쏘시개로 쓸 수 있겠다."
            ])
        else:
            yield morld.dialog([
                "둘러보았지만...",
                "쓸만한 나뭇가지를 찾지 못했다."
            ])


class PineTree(Tree):
    """소나무 - 통나무/나뭇가지 많음"""
    unique_id = "pine_tree"
    name = "소나무"

    max_logs = 4
    max_branches = 6
    initial_logs = 3
    initial_branches = 4

    focus_text = {
        "default": "키가 큰 소나무다. 곧게 뻗은 줄기가 인상적이다."
    }


class OakTree(Tree):
    """참나무 - 통나무 많음, 나뭇가지 적음"""
    unique_id = "oak_tree"
    name = "참나무"

    max_logs = 5
    max_branches = 4
    initial_logs = 4
    initial_branches = 2

    focus_text = {
        "default": "굵고 튼튼한 참나무다. 좋은 목재를 얻을 수 있을 것 같다."
    }
