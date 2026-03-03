# assets/characters/player.py - 플레이어 캐릭터 Asset
#
# 사용법:
#   from assets.characters.player import Player, NAME_OPTIONS
#   player = Player()
#   player_id = morld.create_id("unit")
#   player.instantiate(player_id, REGION_ID, location_id)

from assets.base import Character


# 캐릭터 생성 옵션
NAME_OPTIONS = ["카이", "레온", "아론", "유진"]

AGE_OPTIONS = [
    {"value": 17, "label": "17세 - 아직 어린 소년"},
    {"value": 22, "label": "22세 - 청년"},
    {"value": 30, "label": "30세 - 성숙한 장년"},
]

BODY_OPTIONS = [
    {"value": "왜소", "label": "왜소함 - 작고 가벼운 몸"},
    {"value": "보통", "label": "보통 - 평범한 체격"},
    {"value": "장신", "label": "장신 - 키가 크고 늘씬함"},
    {"value": "거구", "label": "거구 - 크고 건장한 몸"},
]

GENDER_OPTIONS = [
    {"value": "male", "label": "남성"},
    {"value": "female", "label": "여성"},
    {"value": "futanari", "label": "후타나리"},
]

PENIS_SIZE_OPTIONS = [
    {"value": 1, "label": "작음 - 평균 이하"},
    {"value": 2, "label": "보통 - 평범한 크기"},
    {"value": 3, "label": "큼 - 평균 이상"},
]

EQUIPMENT_OPTIONS = [
    {
        "id": "hunter",
        "label": "낡은 칼과 가죽 주머니",
        "desc": "전직 사냥꾼의 기억?",
        "items": [("old_knife", 1), ("leather_pouch", 1)]
    },
    {
        "id": "scholar",
        "label": "필기구와 책 한 권",
        "desc": "학자나 서기였을까?",
        "items": [("writing_tool", 1), ("old_book", 1)]
    },
    {
        "id": "craftsman",
        "label": "휴대용 제작 도구",
        "desc": "장인이나 기술자?",
        "items": [("small_toolbox", 1)]
    },
    {
        "id": "nothing",
        "label": "아무것도 없음",
        "desc": "완전히 빈손으로 시작",
        "items": []
    },
]


class Player(Character):
    unique_id = "player"
    name = "???"
    type = "character"
    props = {
        # "성별"은 player_creation에서 설정, persistence가 챕터 전환 시 복원
        # 기본 스탯
        "근력": 5,
        "지능": 5,
        "손재주": 5,
        "체력": 5,
        "신체:보통": 1,
        "나이": 22,
        "신뢰도": 0,

        # 생존 스탯
        "생존:체력": 100,
        "생존:최대체력": 100,
        "생존:포만감": 100,
        "생존:최대포만감": 100,

        # 전투 스탯
        "전투:공격력": 3,
        "전투:방어력": 1,
        "전투:명중": 80,
        "전투:회피": 5,
        "전투:치명타": 5,
        "전투:사거리": 50,
        "전투:공격속도": 1.0,

        # 기본 행동 능력 (can:메서드명)
        # NPC 상호작용
        "can:talk": 1,
        "can:wake_up": 1,  # 수면 중인 NPC 깨우기

        # 이동/자세
        "can:sit": 1,
        "can:lie_down": 1,
        "can:stand_up": 1,
        "can:rest": 1,
        "can:sleep": 1,

        # 아이템 조작
        "can:take": 1,
        "can:use": 1,
        "can:equip": 1,
        "can:unequip": 1,
        "can:putinobject": 1,
        "can:put": 1,

        # 오브젝트 상호작용 - OOP 메서드명
        "can:toggle_switch": 1,  # 등/벽난로 켜기/끄기
        "can:look": 1,
        "can:draw": 1,
        "can:drive": 1,

        # 아이템 사용
        "can:read_book": 1,
        "can:eat": 1,
        "can:harvest": 1,

        # 자원 채집
        "can:gather": 1,    # 나뭇가지 줍기 등 (도구 불필요)
        "can:disassemble": 1,  # 분해 (붙잡힌 덫 등)

        # 조리
        "can:cook": 1,
        "can:brew": 1,

        # 제작
        "can:craft": 1,

        # 거래 (페이 상점)
        "can:buy_items": 1,
        "can:sell_items": 1,
        "can:buyback_items": 1,

        # 연애
        "can:give_gift": 1,
        "can:romance": 0,       # 연애 모드 ON 시 settings에서 1로 변경
        "can:force_romance": 0, # 연애 모드 ON 시 settings에서 1로 변경
        "can:masturbate": 0,    # 연애 모드 ON 시 settings에서 1로 변경
        "can:date": 1,
        "can:end_date": 0,    # 데이트 시작 시 1로 변경
        "can:hold_hands": 0,  # 동적 관리 (date.py에서 조건에 따라 설정)
        "can:date_hug": 0,    # 동적 관리 (date.py에서 조건에 따라 설정)
        "can:date_kiss": 0,   # 동적 관리 (date.py에서 조건에 따라 설정)

        # 전투
        "can:attack": 0,     # 적대모드 ON 시 활성화
        "can:steal": 0,      # 적대모드 ON 시 활성화

        # 이동
        "이동:달리기": 0,    # 0=보통, 1=달리기

        # 퀘스트
        "can:errand": 0,  # 동적 관리 (심부름 가능한 퀘스트가 있을 때만 1)

        # 세력 — 방문자: 숲속 저택/도시와 우호, 생물과 적대
        # (세라 개인은 sera.props의 관계:방문자:세력도 = 0 override로 중립)
        "세력": "방문자",

    }
    actions = ["call:rest:휴식", "call:sleep:노숙", "call:masturbate:자위#",
               "call:self_expose:옷 들추기#",
               "call:remove_parasite:기생체 제거#"]
    mood = []

    def rest(self):
        """휴식 (멍때리기) - 30분 경과"""
        import morld
        morld.add_action_log(f"{self.name}이(가) 잠시 쉬었다.")
        morld.advance_time_des(30 * 60_000)  # DES: NPC 자율 행동

    def sleep(self):
        """야외 취침 (노숙) - 4시간 경과"""
        import morld
        morld.add_action_log(f"{self.name}이(가) 바닥에서 잠을 청했다.")
        morld.advance_time_des(240 * 60_000)  # DES: NPC 자율 행동
        # 몽정 연출
        if morld.get_unit_prop(self.instance_id, "기억:몽정"):
            morld.clear_prop(self.instance_id, "기억:몽정")
            morld.add_action_log("...꿈속에서 사정한 것 같다. 하의가 젖어 있다.")

    def masturbate(self):
        """자위 행위 — 주변에 아무도 없을 때만"""
        import morld
        try:
            import semen as semen_mod
        except ImportError:
            return

        # 1. 혼자인지 확인
        loc = morld.get_unit_location(self.instance_id)
        if loc:
            units = morld.get_characters_at_location(loc[0], loc[1])
            others = [u for u in units if u != self.instance_id]
            if others:
                morld.add_action_log("주변에 다른 사람이 있어 할 수 없다.")
                return

        # 2. 발기 가능 확인
        if not semen_mod.can_erect(self.instance_id):
            morld.add_action_log("정액이 부족해 의욕이 나지 않는다.")
            return

        # 3. 자위 상태 설정 (NPC 발각용)
        morld.set_unit_prop(self.instance_id, "상태:자위중", 1)

        # 4. 15분 경과 (NPC 이동/이벤트 처리)
        morld.advance_time_des(15 * 60_000)

        # 5. 상태 해제
        morld.clear_prop(self.instance_id, "상태:자위중")

        # 6. 효과 적용
        can_ejac = semen_mod.can_ejaculate(self.instance_id)
        arousal = morld.get_unit_prop(self.instance_id, "상태:성욕") or 0

        if can_ejac:
            semen_mod.consume_semen(self.instance_id, semen_mod.MASTURBATION_COST)
            morld.set_unit_prop(self.instance_id, "상태:성욕", max(0, arousal - 50))
            morld.add_action_log("사정으로 크게 해소되었다.")
        else:
            morld.set_unit_prop(self.instance_id, "상태:성욕", max(0, arousal - 15))
            morld.add_action_log("사정까지 이르지 못했지만 약간 해소되었다.")

    def self_expose(self):
        """플레이어 자기 노출 — 상체/하체 선택"""
        import morld
        import settings
        if not settings.is_harassment_enabled():
            morld.add_action_log("성추행 모드가 꺼져 있다.")
            return
        import ui
        lines = ["[b]어느 쪽을 노출할까?[/b]\n"]
        lines.append("[url=@ret:upper]상체 들추기[/url]")
        lines.append("[url=@ret:lower]하체 들추기[/url]")
        # 이미 노출 중이면 복구 옵션
        upper = morld.get_unit_prop(self.instance_id, "임시노출:상체") or 0
        lower = morld.get_unit_prop(self.instance_id, "임시노출:하체") or 0
        if upper or lower:
            lines.append("[url=@ret:fix]옷매무새 정리[/url]")
        lines.append("\n[url=@ret:cancel]취소[/url]")
        choice = yield ui.dialog("[!]" + "\n".join(lines) + "[/!]")
        if not choice or choice == "cancel":
            return
        if choice == "fix":
            morld.clear_prop(self.instance_id, "임시노출:상체")
            morld.clear_prop(self.instance_id, "임시노출:하체")
            morld.clear_prop(self.instance_id, "상태:자발적노출")
            morld.add_action_log("옷매무새를 정리했다.")
            morld.advance_time_des(1 * 60_000)
            return
        part = "상체" if choice == "upper" else "하체"
        morld.set_unit_prop(self.instance_id, f"임시노출:{part}", 2)
        morld.set_unit_prop(self.instance_id, "상태:자발적노출", 1)
        morld.add_action_log(f"{part} 옷을 들추었다.")
        morld.advance_time_des(1 * 60_000)

    def remove_parasite(self):
        """기생체 자력 제거 시도"""
        import morld
        import ui
        import parasite

        attached = parasite.get_attached_parasites(self.instance_id)
        if not attached:
            morld.add_action_log("부착된 기생체가 없다.")
            return
        # 선택 UI
        lines = ["[b]제거할 기생체 선택[/b]\n"]
        for slot, item_id, name in attached:
            part = slot.split(":")[1]
            lines.append(f"[url=@ret:{slot}]{name} ({part})[/url]")
        lines.append("\n[url=@ret:cancel]취소[/url]")
        choice = yield ui.dialog("\n".join(lines))
        if choice == "cancel" or not choice:
            return
        result = parasite.attempt_self_removal(self.instance_id, choice)
        morld.add_action_log(result["message"])
        morld.advance_time_des(5 * 60_000)  # 5분

