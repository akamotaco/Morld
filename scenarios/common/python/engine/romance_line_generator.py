"""대사 생성기 — 3D 좌표 기반 (:start 1인칭)

좌표 공간:
  X축 (sentiment): 호감 - 반발*0.8          (-100 ~ +100)
  Y축 (desire):    (성욕*0.5 + 욕망*0.5) - 순수도*0.5  (-100 ~ +100)
  Z축 (climax):    gauge*0.6 + min(total,4)*10          (0 ~ 100)

네임드 NPC: ROMANCE_REACTIONS(조건기반) → Generator(좌표기반) fallback.
모브 NPC: REACTION_PROFILE만으로 전체 대사 자동.

override → 행위별 좌표 → 카테고리 좌표 (3단계).
"""
import random

from engine.romance_reaction_generator import resolve_tone, resolve_arousal_tier

from engine.tone_templates import (
    LINE_TEMPLATES, ACTION_LINE_TEMPLATES,
    calc_coordinates, select_by_coord,
)
from engine.tone_templates.coords import ACTION_TO_CATEGORY

# ─────────────────────────────────────────────
# 말투 상수 + 아키타입 기본 매핑
# ─────────────────────────────────────────────

ARCHETYPE_SPEECH = {
    "stoic": "rough",
    "gentle": "formal",
    "cheerful": "casual",
    "timid": "formal",
    "cold": "formal",
    "seductive": "casual",
    "fierce": "rough",
    "proud": "rough",
    "innocent": "casual",
    "devoted": "formal",
    "child": "formal",
}


# ─────────────────────────────────────────────
# CASUAL_LINE_TEMPLATES — 가벼운 애정 행위 대사
# action_type → archetype → speech → style → [texts]
# style: default(기본), flirty(호감≥80), addicted(욕망≥70)
# ─────────────────────────────────────────────

CASUAL_LINE_TEMPLATES = {
    # ─── CASUAL_KISS (가벼운 키스) ───
    "casual_kiss": {
        "stoic": {"rough": {
            "default":  ["...뭐해.", "...(눈을 돌린다) ...하지 마."],
            "flirty":   ["...뭐야, 갑자기...", "...(귀끝이 붉어진다) ...싫지 않아."],
            "addicted": ["...또 해.", "...입술... 더 줘.", "...빨리."],
        }},
        "gentle": {"formal": {
            "default":  ["...앗! ...갑자기...", "...(놀라며) ...저, 저한테요...?"],
            "flirty":   ["...에헤헤... 뽀뽀...", "...(수줍게 웃는다) ...또 해주세요..."],
            "addicted": ["...키스... 더 해주세요...", "...입술이... 보고 싶었어요...", "...놓지 마세요..."],
        }},
        "cheerful": {"casual": {
            "default":  ["앗! ...갑자기?!", "...(깜짝 놀라며) ...에, 에에?!"],
            "flirty":   ["에헤~ 뽀뽀다~!", "...(장난스럽게 웃으며) ...또 해줘~"],
            "addicted": ["...키스... 더 해줘...", "...입술... 떨어지기 싫어...", "...응... 더..."],
        }},
        "timid": {"formal": {
            "default":  ["...앗...", "...(놀라서 굳는다)", "......"],
            "flirty":   ["...(눈을 감는다)", "...또... 해주세요...", "...(살짝 미소 짓는다)"],
            "addicted": ["...키스... 해주세요...", "...입술... 더...", "...(떨리는 손으로 옷을 잡는다)"],
        }},
        "cold": {"formal": {
            "default":  ["......", "...(차갑게) ...뭐하시는 거예요.", "...허락한 적 없어요."],
            "flirty":   ["......", "...(이마를 기대며) ...싫지 않아요.", "...또 해줘도... 돼요."],
            "addicted": ["...키스... 해줘요.", "...입술... 더...", "...(옷깃을 쥐며) ...놓지 마요."],
        }},
        "seductive": {"casual": {
            "default":  ["여유롭네?", "...뭐, 나쁘지 않아."],
            "flirty":   ["잘하네...", "...더 깊이 해줘...", "...입술 맛있어..."],
            "addicted": ["...키스 줘...", "입술... 놓지 마...", "...더..."],
        }},
        "fierce": {"rough": {
            "default":  ["...뭐냐.", "...(째려본다) ...건드리지 마."],
            "flirty":   ["...훗, 나쁘지 않군.", "...(입술을 핥으며) ...또 해."],
            "addicted": ["...부족해. 더.", "...입술 줘.", "...빨리."],
        }},
        "proud": {"rough": {
            "default":  ["...감히.", "...(시선을 피한다) ...무례하군."],
            "flirty":   ["...특별히 허락한다.", "...(귀끝이 붉어지며) ...한 번 더..."],
            "addicted": ["...빨리 해.", "...(참지 못하고) ...입술... 더.", "...이번만이야."],
        }},
        "innocent": {"casual": {
            "default":  ["...뭐야 갑자기?", "...에? 뽀뽀?"],
            "flirty":   ["에헤, 뽀뽀다!", "...또 해줘!", "...좋아!"],
            "addicted": ["...또 해줘... 뽀뽀...", "...입술... 이상해...", "...더..."],
        }},
        "devoted": {"formal": {
            "default":  ["...앗... 감사해요...", "...(조용히 받아들인다)"],
            "flirty":   ["...기뻐요...", "...또 해주세요...", "...(행복한 표정)"],
            "addicted": ["...키스... 더... 부탁해요...", "...입술... 놓지 마세요...", "...행복해요..."],
        }},
    },

    # ─── CASUAL_BREAST (가슴 만지기) ───
    "casual_breast": {
        "stoic": {"rough": {
            "default":  ["...손 치워.", "...(노려본다) ...뭐하는 거야."],
            "flirty":   ["...거기는...", "...(고개를 돌리며) ...살짝만..."],
            "addicted": ["...만져...", "...더 세게...", "...거기... 좋아..."],
        }},
        "gentle": {"formal": {
            "default":  ["...히읏! ...저, 저기...", "...(당황하며 가슴을 감싼다)"],
            "flirty":   ["...앗... 거기는...", "...(얼굴을 가리며) ...부끄러워요..."],
            "addicted": ["...만져주세요... 가슴...", "...거기... 만지면... 이상해져요...", "...더..."],
        }},
        "cheerful": {"casual": {
            "default":  ["야야야! 가슴은~!", "...(팔로 가린다) ...부끄러워!"],
            "flirty":   ["앗, 거기~!", "...(웃으며) ...몰래 만지면 안 되지~"],
            "addicted": ["...만져줘... 가슴...", "...거기... 좋아... 더...", "...숨이..."],
        }},
        "timid": {"formal": {
            "default":  ["...앗!", "...(가슴을 감싸며) ...저기...", "......"],
            "flirty":   ["...거기는...", "...(눈을 감으며) ...괜찮아요...", "......"],
            "addicted": ["...만져주세요...", "...가슴... 이상해요...", "...(당신에게 기댄다)"],
        }},
        "cold": {"formal": {
            "default":  ["......", "...(차갑게 노려본다)", "...손 치워 주세요."],
            "flirty":   ["...거기는...", "...(귀끝이 붉어지며) ...조금만...", "......"],
            "addicted": ["...만져줘요...", "...가슴... 이상해져요...", "...(눈을 감으며 받아들인다)"],
        }},
        "seductive": {"casual": {
            "default":  ["대담하네?", "...(눈을 가늘게 뜨며) ...마음에 드는 건 알겠어."],
            "flirty":   ["좋아... 거기...", "더 만져줘...", "...손이 따뜻해..."],
            "addicted": ["...가슴... 더...", "...세게 만져줘...", "...놓지 마..."],
        }},
        "fierce": {"rough": {
            "default":  ["...(손목을 잡으며) ...건드리지 마.", "...뭐하는 거냐."],
            "flirty":   ["...흥, 마음대로 해.", "...(시선을 피하며) ...살짝만."],
            "addicted": ["...더 세게.", "...가슴... 만져.", "...부족해."],
        }},
        "proud": {"rough": {
            "default":  ["...감히 거길.", "...(차갑게) ...손 치워."],
            "flirty":   ["...특별히 허락한다.", "...(볼이 붉어지며) ...조금만..."],
            "addicted": ["...빨리 만져.", "...(참지 못하고) ...거기... 더.", "...이번만이야."],
        }},
        "innocent": {"casual": {
            "default":  ["앗! 거기는...!", "왜 가슴을 만져?!"],
            "flirty":   ["거기... 이상해...", "...또 만져줘...", "...뭔가 느껴져..."],
            "addicted": ["...가슴... 만져줘...", "...이상해... 더...", "...멈추지 마..."],
        }},
        "devoted": {"formal": {
            "default":  ["...앗... 괜찮아요...", "...(조용히 받아들인다)"],
            "flirty":   ["...만져주세요...", "...(수줍게) ...거기... 좋아요...", "......"],
            "addicted": ["...가슴... 더... 만져주세요...", "...이상해져요...", "...부탁해요..."],
        }},
    },

    # ─── CASUAL_BUTT (엉덩이 만지기) ───
    "casual_butt": {
        "stoic": {"rough": {
            "default":  ["...뒤에서 만지지 마.", "...(째려본다)"],
            "flirty":   ["...앗!", "...(움찔) ...뒤는... 부끄러워..."],
            "addicted": ["...거기도... 만져줘...", "...뒤쪽... 좋아..."],
        }},
        "gentle": {"formal": {
            "default":  ["...앗! ...엉, 엉덩이는...", "...(놀라서 뒤로 물러난다)"],
            "flirty":   ["...앗! ...뒤는...", "...(수줍게) ...부끄러워요..."],
            "addicted": ["...뒤도... 만져주세요...", "...거기... 좋아요..."],
        }},
        "cheerful": {"casual": {
            "default":  ["악! 엉덩이~!", "...(뒤로 물러나며) ...갑자기?!"],
            "flirty":   ["앗! ...뒤에서~!", "...(장난스럽게) ...몰래 만졌지~?"],
            "addicted": ["...뒤도... 만져줘...", "...거기... 좋아...", "...응..."],
        }},
        "timid": {"formal": {
            "default":  ["...!", "...(놀라서 뒤로 물러난다)", "......"],
            "flirty":   ["...앗...", "...(고개를 숙이며) ...부끄러워요...", "......"],
            "addicted": ["...뒤도... 만져주세요...", "...(떨리며) ...괜찮아요...", "......"],
        }},
        "cold": {"formal": {
            "default":  ["......", "...(날카로운 눈빛) ...뭐하시는 거예요.", "......"],
            "flirty":   ["...!", "...(미세하게 움찔) ...뒤는... 부끄럽군요.", "......"],
            "addicted": ["...뒤도... 만져줘요...", "...(떨리며) ...괜찮아요...", "...더..."],
        }},
        "seductive": {"casual": {
            "default":  ["뒤에서? 대담하네.", "...(흘긋 뒤를 보며) ...나쁘지 않아."],
            "flirty":   ["좋아... 거기도...", "...더 만져줘...", "...(허리를 비틀며)"],
            "addicted": ["...뒤도... 더...", "...거기... 좋아...", "...세게..."],
        }},
        "fierce": {"rough": {
            "default":  ["...(째려본다) ...뒤에서 건드리지 마.", "...뭐하냐."],
            "flirty":   ["...흥, 뒤를 좋아하는군.", "...(움찔하지만 참는다)"],
            "addicted": ["...뒤도 만져.", "...거기... 더.", "...세게."],
        }},
        "proud": {"rough": {
            "default":  ["...뒤에서 감히.", "...(차갑게) ...무례하군."],
            "flirty":   ["...(움찔) ...특별히 봐준다.", "...(볼이 붉어진다)"],
            "addicted": ["...뒤도... 만져.", "...(참지 못하고) ...더.", "......"],
        }},
        "innocent": {"casual": {
            "default":  ["앗! 엉덩이?!", "왜 거길 만져?!"],
            "flirty":   ["앗...! 뒤는... 부끄러워...", "...(얼굴이 빨개진다)"],
            "addicted": ["...뒤도... 만져줘...", "...거기... 이상해...", "...더..."],
        }},
        "devoted": {"formal": {
            "default":  ["...앗... 뒤는...", "...(조용히 참는다)"],
            "flirty":   ["...(고개를 숙이며) ...괜찮아요...", "...부끄럽지만..."],
            "addicted": ["...뒤도... 만져주세요...", "...거기... 좋아요...", "...부탁해요..."],
        }},
    },

    # ─── CASUAL_GENITAL (음부 만지기) ───
    "casual_genital": {
        "stoic": {"rough": {
            "default":  ["...미쳤어?!", "...(손을 잡아 밀친다) ...여기서?!"],
            "flirty":   ["...거기는...!", "...(얼굴이 빨개진다) ...바보..."],
            "addicted": ["...만져... 거기...", "...더... 해줘...", "...이상해져..."],
        }},
        "gentle": {"formal": {
            "default":  ["...히읏?! ...안 돼요...!", "...(다리를 모으며) ...여기서는..."],
            "flirty":   ["...거기는... 안 돼요...", "...(얼굴이 새빨개진다) ...밝은 데서..."],
            "addicted": ["...만져주세요... 거기...", "...이상해져요... 더...", "...참을 수 없어요..."],
        }},
        "cheerful": {"casual": {
            "default":  ["에에에?! 거, 거기는?!", "...(다리를 모으며) ...미쳤어?!"],
            "flirty":   ["...거기는...!", "...(얼굴이 빨개지며) ...야, 밝은 데서...!"],
            "addicted": ["...거기... 만져줘...", "...이상해져... 더...", "...참을 수 없어..."],
        }},
        "timid": {"formal": {
            "default":  ["...!", "...(놀라서 다리를 모은다)", "...(고개를 세차게 젓는다)"],
            "flirty":   ["...거기는...", "...(얼굴을 묻으며) ...안 돼요...", "...(하지만 거부하지 않는다)"],
            "addicted": ["...만져주세요... 거기...", "...이상해요... 더...", "...(다리에 힘이 풀린다)"],
        }},
        "cold": {"formal": {
            "default":  ["......!", "...(손목을 잡으며) ...멈추세요.", "...선을 넘지 마세요."],
            "flirty":   ["...거기는...!", "...(입술을 깨물며) ...여기서는...", "...(하지만 밀어내지 않는다)"],
            "addicted": ["...만져줘요... 거기...", "...참을 수 없어요...", "...(냉정함이 무너진다)"],
        }},
        "seductive": {"casual": {
            "default":  ["여기서? 대담하네.", "...(다리를 모으며) ...장소를 가리자."],
            "flirty":   ["좋아... 거기...", "...(눈을 가늘게 뜨며) ...더 해줘..."],
            "addicted": ["...거기... 더...", "...만져줘... 멈추지 마...", "...(숨이 거칠어진다)"],
        }},
        "fierce": {"rough": {
            "default":  ["...(손목을 비틀며) ...미쳤냐?!", "...여기서 감히."],
            "flirty":   ["...거기는...!", "...(얼굴이 붉어지며) ...마음대로 해."],
            "addicted": ["...거기... 만져.", "...더 세게.", "...멈추면 안 돼."],
        }},
        "proud": {"rough": {
            "default":  ["...감히 거길?!", "...(차갑게) ...선을 넘었군."],
            "flirty":   ["...(숨을 삼키며) ...특별히.", "...(시선을 피하며) ...거기는..."],
            "addicted": ["...빨리... 거기...", "...(참지 못하고) ...더.", "...이번만이야..."],
        }},
        "innocent": {"casual": {
            "default":  ["에?! 거, 거기는...?!", "...(놀라서 뒤로 물러난다) ...뭐하는 거야?!"],
            "flirty":   ["...거기... 이상해...", "...(얼굴이 빨개지며) ...뭔가 느껴져..."],
            "addicted": ["...거기... 만져줘...", "...이상해... 멈추지 마...", "...뭐야 이 느낌..."],
        }},
        "devoted": {"formal": {
            "default":  ["...앗...! ...거기는...", "...(조용히 다리를 모은다)"],
            "flirty":   ["...(얼굴을 묻으며) ...괜찮아요...", "...거기... 부끄럽지만..."],
            "addicted": ["...거기... 만져주세요...", "...이상해져요... 더...", "...부탁해요..."],
        }},
    },
}


# ─────────────────────────────────────────────
# SELF_COMFORT_TEMPLATES — 자위 발각 반응
# archetype → {text: [(conditions, texts)], effects: {호감: -N}}
# {name} → NPC 이름으로 format
# ─────────────────────────────────────────────

SELF_COMFORT_TEMPLATES = {
    "stoic": {
        "text": [
            ({"호감": 70}, ["[{name}]", "...!", "...(얼굴을 돌린다)",
                           "...뭘 봤는지 모른 척 해.", "...안 그러면 죽여버린다."]),
            ({}, ["[{name}]", "...!", "{name}(이)가 황급히 몸을 돌린다.",
                  "...나가.", "...지금 당장."]),
        ],
        "effects": {"호감": -5},
    },
    "gentle": {
        "text": [
            ({"호감": 70}, ["[{name}]", "...!", "...어, 어떡해...",
                           "...(눈물이 글썽인다)", "...이건... 그게 아니라..."]),
            ({}, ["[{name}]", "...!", "{name}(이)가 비명을 지르며 이불을 끌어당긴다.",
                  "...나가 주세요...!"]),
        ],
        "effects": {"호감": -3},
    },
    "cheerful": {
        "text": [
            ({"호감": 70}, ["[{name}]", "꺄악!!", "...이, 이건...!!",
                           "...(얼굴이 새빨개진다)", "...봤어...?!"]),
            ({}, ["[{name}]", "꺄악!!", "{name}(이)가 베개를 집어던진다.",
                  "나가!! 나가라고!!"]),
        ],
        "effects": {"호감": -5},
    },
    "timid": {
        "text": [
            ({"호감": 70}, ["[{name}]", "...!", "...(몸이 굳는다)",
                           "...", "...(눈물이 흐른다)"]),
            ({}, ["[{name}]", "...!", "{name}(이)가 움직임을 멈추고 부들부들 떤다.",
                  "...(아무 말도 못 한다)"]),
        ],
        "effects": {"호감": -3},
    },
    "cold": {
        "text": [
            ({"호감": 70}, ["[{name}]", "......!", "...(옷을 고쳐입는다)",
                           "...노크 정도는 해주세요."]),
            ({}, ["[{name}]", "......!", "{name}(이)가 차가운 시선을 보낸다.",
                  "...나가요. 지금."]),
        ],
        "effects": {"호감": -5},
    },
    "seductive": {
        "text": [
            ({"호감": 70}, ["[{name}]", "......", "...(느긋하게 몸을 돌리며)",
                           "...보고 싶었으면 말하지 그랬어.", "...이리 와."]),
            ({}, ["[{name}]", "...!", "...(천천히 몸을 가리며)",
                  "...훗, 구경은 재미있었어?", "...다음엔 노크해."]),
        ],
        "effects": {"호감": -5},
    },
    "fierce": {
        "text": [
            ({"호감": 70}, ["[{name}]", "...!!", "...(얼굴이 붉어지며)",
                           "...죽고 싶어?!", "...(하지만 시선을 피한다)"]),
            ({}, ["[{name}]", "...!!", "{name}(이)가 가장 가까운 물건을 집어던진다.",
                  "꺼져!! 지금 당장!!"]),
        ],
        "effects": {"호감": -5},
    },
    "proud": {
        "text": [
            ({"호감": 70}, ["[{name}]", "......!", "...(침착하게 옷을 고쳐입는다)",
                           "...뭘 봤는지는 모른 척 하는 게 좋을 거야.",
                           "...(하지만 귀끝이 붉다)"]),
            ({}, ["[{name}]", "......!", "{name}(이)가 차갑게 노려본다.",
                  "...감히. 나가.", "...두 번 말하게 하지 마."]),
        ],
        "effects": {"호감": -5},
    },
    "innocent": {
        "text": [
            ({"호감": 70}, ["[{name}]", "앗...!", "...(당황하며 이불을 끌어당긴다)",
                           "...이, 이건 그게 아니야...!", "...몸이 이상해서..."]),
            ({}, ["[{name}]", "앗!", "{name}(이)가 당황하며 몸을 웅크린다.",
                  "...보지 마...!", "...(울 것 같은 표정)"]),
        ],
        "effects": {"호감": -3},
    },
    "devoted": {
        "text": [
            ({"호감": 70}, ["[{name}]", "...!", "...(얼굴을 가리며)",
                           "...죄, 죄송해요...", "...당신 생각을... 하고 있었어요..."]),
            ({}, ["[{name}]", "...!", "{name}(이)가 황급히 몸을 가린다.",
                  "...죄송해요...!", "...(고개를 숙인다)"]),
        ],
        "effects": {"호감": -3},
    },
}


# ─────────────────────────────────────────────
# LineGenerator 클래스
# ─────────────────────────────────────────────

class LineGenerator:
    """3D 좌표 기반 대사 생성기.

    override → 행위별 좌표 → 카테고리 좌표 (3단계).
    네임드 NPC: char_lines로 일부 좌표 대체 + 아키타입 텍스트 fallback.
    모브 NPC: REACTION_PROFILE만으로 전체 대사 자동 생성.
    """

    def __init__(self, profile):
        self.profile = profile
        self.name = profile["name"]
        self.archetype = profile.get("archetype", "stoic")
        self.speech_level = profile.get(
            "speech_level",
            ARCHETYPE_SPEECH.get(self.archetype, "casual"))
        self._overrides = profile.get("line_overrides", {})
        self._char_lines = profile.get("char_lines", {})

    def generate(self, action_id, state):
        """1인칭 대사 생성 — override → 행위별 좌표 → 카테고리 좌표.

        Returns:
            대사 텍스트 또는 None
        """
        sx, sy, sz = calc_coordinates(state)
        tone = resolve_tone(state)
        speech = self.speech_level

        # 1) 캐릭터 override
        override_texts = self._overrides.get(f"{action_id}:start")
        if override_texts:
            return self._pick_from_nested(override_texts, speech, tone)

        # 2) 행위별 아키타입 템플릿 (좌표 기반 + 캐릭터 오버레이)
        key = f"{action_id}:start"
        pool = ACTION_LINE_TEMPLATES.get(key, {}).get(self.archetype, {})
        pool = self._merge_char_pool(pool, action_id)
        text = select_by_coord(pool, sx, sy, sz)
        if text:
            return text

        # 3) 카테고리 fallback (좌표 기반 + 캐릭터 오버레이)
        category = ACTION_TO_CATEGORY.get(action_id)
        if category:
            pool = LINE_TEMPLATES.get(f"{category}:start", {}).get(
                self.archetype, {})
            pool = self._merge_char_pool(pool, category)
            text = select_by_coord(pool, sx, sy, sz)
            if text:
                return text

        return None

    def _merge_char_pool(self, base_pool, key):
        """캐릭터 오버레이 머지 — 같은 좌표는 대체, 나머지는 유지."""
        char_pool = self._char_lines.get(key, {})
        if not char_pool:
            return base_pool
        merged = dict(base_pool)
        merged.update(char_pool)
        return merged

    def _pick_speech_tone(self, speech_dict, speech, tone):
        """speech_dict[speech][tone] → random.choice, tone fallback 포함."""
        if not speech_dict:
            return None

        tone_dict = speech_dict.get(speech, {})
        if not tone_dict:
            return None

        if isinstance(tone_dict, list):
            return random.choice(tone_dict) if tone_dict else None

        texts = tone_dict.get(tone)
        if texts:
            return random.choice(texts)

        fallback_order = {
            "romance": ["lust", "platonic"],
            "lust": ["romance"],
            "platonic": ["romance"],
            "rejection": ["platonic"],
        }
        for fb in fallback_order.get(tone, []):
            texts = tone_dict.get(fb)
            if texts:
                return random.choice(texts)

        return None

    def _pick_from_nested(self, data, speech, tone):
        """override 데이터 해석 — 리스트 or dict."""
        if isinstance(data, list):
            return random.choice(data) if data else None
        if isinstance(data, dict):
            return self._pick_speech_tone(data, speech, tone)
        return None

    # ─── 가벼운 애정 행위 (casual_affection) ───

    def generate_casual(self, action_type, style):
        """가벼운 애정 행위 대사 생성.

        Args:
            action_type: "casual_kiss" / "casual_breast" / "casual_butt" / "casual_genital"
            style: "default" / "flirty" / "addicted"
        Returns:
            대사 텍스트 또는 None
        """
        templates = CASUAL_LINE_TEMPLATES.get(action_type, {})
        arch_templates = templates.get(self.archetype, {})
        speech_templates = arch_templates.get(self.speech_level, {})
        texts = speech_templates.get(style, speech_templates.get("default", []))
        return random.choice(texts) if texts else None

    # ─── 자위 발각 반응 (self_comfort_discovery) ───

    def get_discovery_config(self):
        """자위 발각 반응 config 반환 — _run_discovery_reaction() 호환 형식.

        Returns:
            {"text": [(conditions, texts)], "effects": {...}} 또는 None
        """
        template = SELF_COMFORT_TEMPLATES.get(self.archetype)
        if not template:
            return None

        config = {"effects": dict(template["effects"])}
        text_rules = []
        for conditions, texts in template["text"]:
            formatted = [t.format(name=self.name) for t in texts]
            text_rules.append((conditions, formatted))
        config["text"] = text_rules
        return config
