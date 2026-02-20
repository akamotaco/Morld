# assets/items/tools.py - 도구 아이템
#
# OOP call: 패턴 적용
# - actions: ["call:메서드명:표시명@context"] 형식
# - 각 클래스가 인스턴스 메서드로 동작 구현
# - 동일한 액션명(read, use)도 클래스별로 다른 동작 구현
#
# 사용법:
#   from assets.items.tools import Torch, Rope
#   torch = Torch()
#   torch.instantiate(item_id)

import morld
import ui
from assets.base import Item
from assets.registry import register_item


# ========================================
# 기타 도구
# ========================================

class Torch(Item):
    unique_id = "torch"
    name = "횃불"
    category = "tool"
    passive_props = {}
    equip_props = {"밝기": 3, "장착:손": 1}
    value = 5
    actions = ["take@container", "call:use:사용하기@inventory", "equip@inventory"]

    def use(self):
        """횃불 사용 - 불 켜기"""
        yield ui.dialog([
            "횃불에 불을 붙였다.",
            "주변이 환하게 밝아졌다."
        ])
        morld.advance_time_des(1 * 60_000)


class Rope(Item):
    unique_id = "rope"
    name = "밧줄"
    passive_props = {}
    equip_props = {}
    value = 8
    actions = ["take@container", "call:use:살펴보기@inventory"]

    def use(self):
        """밧줄 살펴보기"""
        yield ui.dialog([
            "튼튼한 밧줄이다.",
            "오르거나 묶는 데 쓸 수 있겠다."
        ])


# ========================================
# 소유자가 있는 개인 물품
# ========================================

class KitchenKnife(Item):
    """밀라의 부엌칼"""
    unique_id = "kitchen_knife"
    name = "부엌칼"
    category = "tool"
    owner = "mila"
    passive_props = {}
    equip_props = {"공격력": 2, "장착:손": 1}
    value = 15
    actions = ["take@container", "call:use:살펴보기@inventory", "equip@inventory"]

    def use(self):
        """부엌칼 살펴보기"""
        yield ui.dialog([
            "날이 잘 서있는 부엌칼이다.",
            "밀라가 소중히 관리하는 것 같다."
        ])


class AlarmClock(Item):
    """리나의 자명종"""
    unique_id = "alarm_clock"
    name = "자명종"
    owner = "lina"
    passive_props = {}
    equip_props = {}
    value = 20
    actions = ["take@container", "call:use:살펴보기@inventory"]

    def use(self):
        """자명종 살펴보기"""
        yield ui.dialog([
            "째깍째깍 소리를 내는 자명종이다.",
            "리나가 아끼는 물건 같다."
        ])


class FishingRod(Item):
    """
    세라의 낚시대

    장착 시 can:fish 부여 → 물가에서 "낚시" 액션 활성화
    """
    unique_id = "fishing_rod"
    name = "낚시대"
    category = "tool"
    owner = "sera"
    passive_props = {}
    equip_props = {"can:fish": 1, "장착:손": 1}
    value = 25
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """낚시대 살펴보기"""
        yield ui.dialog([
            "세라의 낚시대다.",
            "장착하면 물가에서 낚시를 할 수 있다."
        ])


class Axe(Item):
    """
    세라의 도끼

    장착 시 can:chop 부여 → 나무에서 "벌목" 액션 활성화
    equip_props의 "날붙이": 1 → chop() 메서드에서 "뚝딱뚝딱" 출력
    """
    unique_id = "axe"
    name = "도끼"
    category = "tool"
    owner = "sera"
    passive_props = {}
    equip_props = {"can:chop": 1, "공격력": 3, "장착:손": 1, "날붙이": 1}
    value = 35
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """도끼 살펴보기"""
        yield ui.dialog([
            "세라의 도끼다.",
            "장착하면 나무를 벨 수 있다."
        ])


class Saw(Item):
    """
    톱

    소지만으로 can:chop 부여 → 나무에서 "벌목" 액션 활성화
    passive_props의 "톱날": 1 → chop() 메서드에서 "슥삭슥삭" 출력
    """
    unique_id = "saw"
    name = "톱"
    category = "tool"
    passive_props = {"can:chop": 1, "톱날": 1}
    equip_props = {}
    value = 30
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """톱 살펴보기"""
        yield ui.dialog([
            "나무를 자를 수 있는 톱이다.",
            "소지하고 있으면 나무를 벨 수 있다."
        ])


class HuntingBow(Item):
    """
    사냥용 활

    세라가 처음 소유하고 있지만, 크래프팅으로도 제작 가능
    재료: 나무판 2개 + 끈 1개
    """
    unique_id = "hunting_bow"
    name = "사냥용 활"
    category = "tool"
    owner = "sera"
    passive_props = {}
    equip_props = {"공격력": 5, "사거리": 3, "장착:손": 1}
    value = 50
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """활 살펴보기"""
        yield ui.dialog([
            "잘 만들어진 사냥용 활이다.",
            "화살과 함께 사용하면 사냥을 할 수 있다."
        ])


class HerbPouch(Item):
    """리나의 약초 주머니"""
    unique_id = "herb_pouch"
    name = "약초 주머니"
    owner = "lina"
    passive_props = {}
    equip_props = {}
    value = 10
    actions = ["take@container", "call:use:살펴보기@inventory"]

    def use(self):
        """약초 주머니 살펴보기"""
        yield ui.dialog([
            "리나의 약초 주머니다.",
            "안에는 말린 약초들이 가득하다.",
            "치료에 쓸 수 있는 것들이 많아 보인다."
        ])


class CookingPot(Item):
    """밀라의 냄비"""
    unique_id = "cooking_pot"
    name = "냄비"
    owner = "mila"
    passive_props = {}
    equip_props = {}
    value = 30
    actions = ["take@container"]


class Diary(Item):
    """유키의 일기장"""
    unique_id = "diary"
    name = "일기장"
    owner = "yuki"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container", "call:read:읽기@inventory"]

    def read(self):
        """유키의 일기장 읽기"""
        yield ui.dialog([
            "유키의 일기장을 펼쳐본다.",
            "\"오늘도 언니들과 함께 저택 청소를 했다.\"",
            "\"저녁에는 밀라 언니가 맛있는 저녁을 해줬다.\"",
            "\"...모두가 행복해 보여서 나도 기분이 좋다.\""
        ], autofill="book")
        morld.advance_time_des(5 * 60_000)


class ManagementLedger(Item):
    """엘라의 관리 장부"""
    unique_id = "management_ledger"
    name = "관리 장부"
    owner = "ella"
    passive_props = {}
    equip_props = {}
    value = 10
    actions = ["take@container", "call:read:읽기@inventory"]

    def read(self):
        """엘라의 관리 장부 읽기"""
        yield ui.dialog([
            "엘라의 관리 장부를 펼쳐본다.",
            "저택의 식량, 자금, 일정 등이 꼼꼼하게 기록되어 있다.",
            "엘라의 정리 능력에 감탄하지 않을 수 없다."
        ], autofill="book")
        morld.advance_time_des(5 * 60_000)


# ========================================
# 공용 아이템 (소유자 없음)
# ========================================

class Lantern(Item):
    """랜턴 - 장착 시 밝기 제공"""
    unique_id = "lantern"
    name = "랜턴"
    category = "tool"
    passive_props = {}
    equip_props = {"밝기": 2, "장착:손": 1}    
    value = 10
    actions = ["take@container", "equip@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """랜턴 살펴보기"""
        yield ui.dialog([
            "손잡이가 달린 유리 랜턴이다.",
            "장착하면 어두운 곳을 밝힐 수 있다."
        ])


class WaterBottle(Item):
    """물병"""
    unique_id = "water_bottle"
    name = "물병"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container", "call:use:물 마시기@inventory"]

    def use(self):
        """물병 사용 - 물 마시기"""
        yield ui.dialog([
            "물병의 물을 마셨다.",
            "시원하고 상쾌하다."
        ])
        morld.advance_time_des(1 * 60_000)


# ========================================
# 사냥 도구
# ========================================

@register_item
class RabbitTrap(Item):
    """
    소형 동물 덫 - 토끼 굴에 설치

    제작 방법:
    - 나뭇가지 3개 (rabbit_trap_branch 레시피)
    - 나무판 1개 (rabbit_trap_plank 레시피)
    """
    unique_id = "rabbit_trap"
    name = "소형 동물 덫"
    passive_props = {}
    equip_props = {}
    action_props = {"put": 1}  # 토끼 굴에 넣기 가능
    value = 10
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """소형 동물 덫 살펴보기"""
        yield ui.dialog([
            "간단히 만든 소형 동물 덫이다.",
            "토끼 굴 근처에 설치하면 토끼를 잡을 수 있다."
        ])


@register_item
class TrappedRabbit(Item):
    """
    토끼가 붙잡힌 덫

    분해하면 토끼 사체를 얻고, 덫은 부서짐
    """
    unique_id = "trapped_rabbit"
    name = "토끼가 붙잡힌 덫"
    passive_props = {}
    equip_props = {}
    value = 25
    actions = ["take@container", "call:disassemble:분해@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """붙잡힌 덫 살펴보기"""
        yield ui.dialog([
            "덫에 토끼가 걸려 있다!",
            "분해하면 토끼 사체를 얻을 수 있다."
        ])

    def disassemble(self):
        """
        덫 분해 - 토끼 사체 획득, 덫은 부서짐
        """
        from assets.registry import get_or_create_item_id

        player_id = morld.get_player_id()

        yield ui.dialog("덫을 분해해서 토끼를 꺼낸다...")
        morld.advance_time_des(5 * 60_000)

        # 토끼 사체 지급
        rabbit_carcass_id = get_or_create_item_id("rabbit_carcass")
        if rabbit_carcass_id:
            import inventory as inv_module
            inv_module.safe_give_item(player_id, rabbit_carcass_id, 1)

        # 붙잡힌 덫 제거 (부서짐)
        morld.lost_item(player_id, self.instance_id, 1)

        yield ui.dialog([
            "토끼 사체를 얻었다!",
            "덫은 부서져서 사용할 수 없게 되었다."
        ])


@register_item
class RabbitCarcass(Item):
    """
    토끼 사체

    박피(skin) 시 토끼 생고기 + 토끼 가죽 획득
    날붙이(can:skin) 소지 필요 - 도구 선택 UI 표시
    박피 소요 시간은 사용하는 도구(skin_time)에 따라 결정
    """
    unique_id = "rabbit_carcass"
    name = "토끼 사체"
    passive_props = {}
    equip_props = {}
    value = 20
    actions = ["take@container", "call:skin:박피@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """토끼 사체 살펴보기"""
        yield ui.dialog([
            "갓 잡은 토끼다.",
            "날붙이로 손질하면 고기와 가죽을 얻을 수 있다."
        ])

    def skin(self):
        """
        박피 - 도구 선택 후 실행

        can:skin을 가진 아이템을 검색하여 선택지 제공
        각 도구별 소요 시간 표시 (skin_time 속성)
        """
        from assets.registry import get_item_class

        player_id = morld.get_player_id()

        # can:skin 능력을 가진 아이템 검색
        skin_tools = morld.find_items_with_passive(player_id, "can:skin")

        if not skin_tools:
            yield ui.dialog("박피에 필요한 도구가 없다.")
            return

        # 각 도구에 skin_time 추가
        for tool in skin_tools:
            item_class = get_item_class(tool["unique_id"])
            tool["skin_time"] = getattr(item_class, "skin_time", 15) if item_class else 15

        if len(skin_tools) == 1:
            # 도구가 하나면 바로 사용
            tool = skin_tools[0]
            yield from self._do_skin(tool)
        else:
            # 여러 개면 선택 다이얼로그
            state = {"selected_tool": None}

            def on_select(action):
                if action == "init":
                    return None
                # action = tool의 item_id
                for t in skin_tools:
                    if str(t["id"]) == action:
                        state["selected_tool"] = t
                        return True
                return None

            # 선택지 텍스트 생성 (도구별 소요 시간 표시)
            lines = ["어떤 도구로 박피할까?", ""]
            for tool in skin_tools:
                lines.append(f"  [url=@proc:{tool['id']}]{tool['name']}[/url] [color=gray]({tool['skin_time']}분)[/color]")

            yield ui.dialog("\n".join(lines), autofill="off", proc=on_select, result=state)

            if state["selected_tool"]:
                yield from self._do_skin(state["selected_tool"])

    def _do_skin(self, tool):
        """
        실제 박피 실행

        Args:
            tool: {"id": int, "name": str, "skin_time": int, ...} 도구 정보
        """
        from assets.registry import get_or_create_item_id

        player_id = morld.get_player_id()
        skin_time = tool.get("skin_time", 15)

        yield ui.dialog(f"{tool['name']}(으)로 토끼를 손질한다...")
        morld.advance_time_des(skin_time * 60_000)

        # 토끼 생고기 지급
        raw_meat_id = get_or_create_item_id("raw_rabbit_meat")
        if raw_meat_id:
            import inventory as inv_module
            inv_module.safe_give_item(player_id, raw_meat_id, 1)

        # 토끼 가죽 지급
        hide_id = get_or_create_item_id("rabbit_hide")
        if hide_id:
            import inventory as inv_module
            inv_module.safe_give_item(player_id, hide_id, 1)

        # 토끼 사체 제거
        morld.lost_item(player_id, self.instance_id, 1)

        yield ui.dialog([
            "토끼 생고기를 얻었다!",
            "토끼 가죽을 얻었다!"
        ])


@register_item
class RawRabbitMeat(Item):
    """
    토끼 생고기

    조리하면 토끼 구이가 됨
    """
    unique_id = "raw_rabbit_meat"
    name = "토끼 생고기"
    category = "food_ingredient"
    passive_props = {}
    equip_props = {}
    value = 15
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """토끼 생고기 살펴보기"""
        yield ui.dialog([
            "신선한 토끼 고기다.",
            "익혀서 먹으면 맛있을 것 같다."
        ])


@register_item
class RabbitHide(Item):
    """
    토끼 가죽

    가공하면 가죽 조각이 됨 (나중에 구현)
    """
    unique_id = "rabbit_hide"
    name = "토끼 가죽"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 10
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """토끼 가죽 살펴보기"""
        yield ui.dialog([
            "부드러운 토끼 가죽이다.",
            "가공하면 여러 가지에 쓸 수 있을 것 같다."
        ])


# ========================================
# 청소 도구
# ========================================

class Broom(Item):
    """
    빗자루 - 청소 도구

    NPC가 can:clean 으로 탐색하여 청소 활동에 사용.
    플레이어는 인벤토리에서 "청소하기" 액션으로 현재 위치 오염도 감소.
    청소력 prop으로 1회 청소 시 감소량 결정.
    """
    unique_id = "broom"
    name = "빗자루"
    category = "tool"
    owner = None
    passive_props = {"can:clean": 1, "청소력": 5}
    equip_props = {"장착:손": 1}
    value = 10
    actions = ["take@container", "equip@inventory",
               "call:clean:청소하기@inventory", "call:look:살펴보기@inventory"]

    def look(self):
        """빗자루 살펴보기"""
        yield ui.dialog([
            "낡았지만 튼튼한 빗자루다.",
            "이것으로 방을 청소할 수 있다."
        ])

    def clean(self):
        """플레이어 청소: 현재 위치 오염도 감소"""
        import pollution

        player_id = morld.get_player_id()
        loc = morld.get_unit_location(player_id)
        if not loc:
            return

        current = pollution.get_location_pollution(loc[0], loc[1])
        if current <= 0:
            yield ui.dialog("이 장소는 충분히 깨끗하다.")
            return

        clean_power = morld.get_unit_prop(self.instance_id, "청소력") or 5
        yield ui.dialog("열심히 빗자루질을 한다...")
        morld.advance_time_des(30 * 60_000)  # 30분

        pollution.clean_location(loc[0], loc[1], clean_power)
        after = pollution.get_location_pollution(loc[0], loc[1])
        if after <= 0:
            yield ui.dialog("깨끗해졌다!")
        else:
            yield ui.dialog("조금 깨끗해진 것 같다.")


