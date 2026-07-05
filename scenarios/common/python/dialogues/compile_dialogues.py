# compile_dialogues.py — 대화 yaml → SharpPy용 컴파일본(dialogues_compiled 패키지) 생성
"""
사용법 (CPython + pyyaml 필요 — miniforge python 사용):
    python compile_dialogues.py            # 검증 + 컴파일본 생성
    python compile_dialogues.py --check    # 검증 + 기존 컴파일본과 드리프트 비교 (CI용)
    python compile_dialogues.py --strict   # 경고도 에러로 취급

동작:
    dialogues/characters/*.yaml + dialogues/archetype_dialogues/*/*.yaml 을 전수 파싱·검증 후
    ../dialogues_compiled/ 패키지로 출력 (아키타입별 분할 모듈 + lazy 접근자).
    출력은 결정적(같은 소스 → 같은 바이트) — git diff 리뷰 가능.

에러 정책:
    - 검증 에러 1건이라도 있으면 아무것도 쓰지 않고 exit 1 (부분 산출물 금지).
    - 에러 메시지는 항상 `파일: 위치: 내용` 형식 — 어느 yaml의 어느 intent/template이
      문제인지 특정 가능.
    - 경고는 출력만 (--strict 면 에러 승격).

문서: docs/dialogue-data-pipeline.md
"""
import hashlib
import io
import sys
from pathlib import Path
from pprint import pformat

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml 필요 — CPython(miniforge)에서 실행하세요. "
          "(SharpPy 런타임은 이 도구의 산출물을 사용)")
    sys.exit(1)

DIALOGUES_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = DIALOGUES_ROOT.parent / "dialogues_compiled"

# 패턴의 {slot}이 slots 풀에 없어도 경고하지 않는 컨텍스트 제공 슬롯
CONTEXT_SLOTS = {"name", "floor", "victim", "target", "item"}

# dialogue_overrides에서 허용하는 컨텍스트명
KNOWN_CONTEXTS = {"daily", "party", "dungeon", "combat", "romance",
                  "romance_reactions", "action_lines", "action_reactions"}

import re
SLOT_RE = re.compile(r"\{(\w+)\}")

errors = []    # (rel, where, msg)
warnings = []  # (rel, where, msg)


def err(rel, where, msg):
    errors.append(f"{rel}: {where}: {msg}")


def warn(rel, where, msg):
    warnings.append(f"{rel}: {where}: {msg}")


def _check_bias(rel, where, bias, key):
    if bias is None:
        return
    if not isinstance(bias, dict):
        err(rel, where, f"{key}는 dict여야 함 (현재 {type(bias).__name__})")
        return
    for axis, val in bias.items():
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            err(rel, where, f"{key}.{axis} 값이 숫자가 아님: {val!r}")


def _check_templates(rel, intent_name, templates, slots, op="templates"):
    """template 리스트 검증. 반환: pattern들이 참조한 slot 이름 집합."""
    referenced = set()
    if templates is None:
        return referenced
    if not isinstance(templates, list):
        err(rel, f"intents.{intent_name}", f"{op}는 list여야 함")
        return referenced
    seen_ids = set()
    for i, t in enumerate(templates):
        where = f"intents.{intent_name}.{op}[{i}]"
        if not isinstance(t, dict):
            err(rel, where, f"template은 dict여야 함 (현재 {type(t).__name__})")
            continue
        pattern = t.get("pattern")
        if not isinstance(pattern, str) or not pattern.strip():
            err(rel, where, f"pattern 누락 또는 빈 문자열 (id={t.get('id')!r})")
        else:
            referenced |= set(SLOT_RE.findall(pattern))
        tid = t.get("id")
        if tid is None:
            warn(rel, where, "id 없음 — replace/disable_templates 대상 지정 불가")
        elif tid in seen_ids:
            err(rel, where, f"중복 template id: {tid!r}")
        else:
            seen_ids.add(tid)
        _check_bias(rel, where, t.get("state_bias"), "state_bias")
        _check_bias(rel, where, t.get("inner_bias"), "inner_bias")
    return referenced


def _check_slots(rel, intent_name, slots, op="slots"):
    if slots is None:
        return
    if not isinstance(slots, dict):
        err(rel, f"intents.{intent_name}", f"{op}는 dict여야 함")
        return
    for slot_name, pool in slots.items():
        where = f"intents.{intent_name}.{op}.{slot_name}"
        if not isinstance(pool, list):
            err(rel, where, "slot 풀은 list여야 함")
            continue
        for item in pool:
            if isinstance(item, dict):
                if "token" not in item:
                    err(rel, where, f"dict slot 항목에 token 없음: {item!r}")
                _check_bias(rel, where, item.get("feature"), "feature")
            elif not isinstance(item, (str, int, float)):
                err(rel, where, f"slot 항목 타입 불가: {item!r}")


def _check_intents(rel, intents, is_override=False):
    if intents is None:
        return
    if not isinstance(intents, dict):
        err(rel, "intents", "intents는 dict여야 함")
        return
    for intent_name, intent in intents.items():
        if not isinstance(intent, dict):
            err(rel, f"intents.{intent_name}", "intent는 dict여야 함")
            continue
        slots = intent.get("slots") or intent.get("add_slots") or {}
        referenced = set()
        for op in ("templates", "add_templates", "replace_templates"):
            referenced |= _check_templates(rel, intent_name, intent.get(op), slots, op)
        _check_slots(rel, intent_name, intent.get("slots"), "slots")
        _check_slots(rel, intent_name, intent.get("add_slots"), "add_slots")
        dis = intent.get("disable_templates")
        if dis is not None and not isinstance(dis, list):
            err(rel, f"intents.{intent_name}", "disable_templates는 list여야 함")
        # 패턴이 참조한 slot 가용성 (override의 경우 base 풀과 합쳐지므로 경고만)
        slot_names = set((intent.get("slots") or {}).keys()) \
            | set((intent.get("add_slots") or {}).keys())
        missing = referenced - slot_names - CONTEXT_SLOTS
        if missing and not is_override:
            warn(rel, f"intents.{intent_name}",
                 f"패턴이 참조하지만 풀/컨텍스트에 없는 slot: {sorted(missing)} "
                 f"(런타임에 빈 문자열로 치환됨)")


def load_and_validate():
    """전체 yaml 로드 + 검증. 반환: {rel: data} (에러 있으면 그래도 수집 계속)."""
    all_data = {}

    arch_dir = DIALOGUES_ROOT / "archetype_dialogues"
    archetypes = sorted(p.name for p in arch_dir.iterdir() if p.is_dir())

    for arch in archetypes:
        for path in sorted((arch_dir / arch).glob("*.yaml")):
            rel = f"archetype_dialogues/{arch}/{path.name}"
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception as e:
                err(rel, "(파일)", f"yaml 파싱 실패: {e}")
                continue
            if not isinstance(data, dict):
                err(rel, "(파일)", "최상위가 dict가 아님")
                continue
            _check_intents(rel, data.get("intents"))
            all_data[rel] = data

    char_dir = DIALOGUES_ROOT / "characters"
    for path in sorted(char_dir.glob("*.yaml")):
        rel = f"characters/{path.name}"
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            err(rel, "(파일)", f"yaml 파싱 실패: {e}")
            continue
        if not isinstance(data, dict):
            err(rel, "(파일)", "최상위가 dict가 아님")
            continue

        cname = data.get("character")
        if cname and cname != path.stem:
            warn(rel, "character", f"파일명({path.stem})과 character({cname}) 불일치")

        arch = data.get("archetype")
        if not arch:
            err(rel, "archetype", "archetype 누락")
        elif arch not in archetypes:
            err(rel, "archetype",
                f"아키타입 '{arch}'의 archetype_dialogues/{arch}/ 폴더가 없음 "
                f"(가용: {archetypes})")

        _check_bias(rel, "outer_profile", data.get("outer_profile"), "outer_profile")
        _check_bias(rel, "inner_profile", data.get("inner_profile"), "inner_profile")

        overrides = data.get("dialogue_overrides") or {}
        if not isinstance(overrides, dict):
            err(rel, "dialogue_overrides", "dict여야 함")
            overrides = {}
        for ctx_name, ctx_data in overrides.items():
            if ctx_name not in KNOWN_CONTEXTS:
                warn(rel, f"dialogue_overrides.{ctx_name}",
                     f"알 수 없는 컨텍스트 (가용: {sorted(KNOWN_CONTEXTS)}) — 병합되지 않음")
            if isinstance(ctx_data, dict):
                _check_intents(rel, ctx_data.get("intents"), is_override=True)
            else:
                err(rel, f"dialogue_overrides.{ctx_name}", "dict여야 함")

        all_data[rel] = data

    _check_coverage(all_data, archetypes)
    return all_data, archetypes


def _check_coverage(all_data, archetypes):
    """아키타입 간 커버리지 갭 경고 — 게임에서 해당 아키타입 NPC만 침묵('...')하는
    증상의 원인을 빌드 타임에 노출한다. (아키타입 전용 intent가 의도라면 무시 가능)"""
    contexts = sorted({rel.split("/")[2].removesuffix(".yaml")
                       for rel in all_data if rel.startswith("archetype_dialogues/")})
    for ctx in contexts:
        having = {}
        for arch in archetypes:
            rel = f"archetype_dialogues/{arch}/{ctx}.yaml"
            if rel in all_data:
                having[arch] = set((all_data[rel].get("intents") or {}).keys())
        if len(having) <= 1:
            continue
        union = set().union(*having.values())
        for arch in archetypes:
            rel = f"archetype_dialogues/{arch}/{ctx}.yaml"
            if arch not in having:
                warn(rel, "(파일)",
                     f"{ctx} 컨텍스트 파일 없음 — 다른 {len(having)}개 아키타입은 보유. "
                     f"해당 아키타입 NPC는 {ctx} 발화가 전부 폴백('...')이 됨")
            else:
                missing = union - having[arch]
                if missing:
                    warn(rel, "intents",
                         f"다른 아키타입에 있는 intent 누락: {sorted(missing)}")


def source_hash(all_data):
    h = hashlib.sha1()
    for rel in sorted(all_data):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update((DIALOGUES_ROOT / rel).read_bytes())
    return h.hexdigest()


HEADER = ("# -*- coding: utf-8 -*-\n"
          "# AUTO-GENERATED by scenarios/common/python/dialogues/compile_dialogues.py\n"
          "# 수동 편집 금지 — yaml 수정 후 컴파일러를 재실행하세요.\n"
          "# 문서: docs/dialogue-data-pipeline.md\n")


def render_outputs(all_data, archetypes):
    """{filename: content} 생성 (결정적)."""
    outputs = {}

    def data_module(rel_items):
        body = "DATA = {\n"
        for rel in sorted(rel_items):
            body += f"    {rel!r}:\n"
            body += "        " + pformat(all_data[rel], width=96, sort_dicts=False) \
                .replace("\n", "\n        ") + ",\n"
        body += "}\n"
        return HEADER + "\n" + body

    char_rels = [r for r in all_data if r.startswith("characters/")]
    outputs["characters.py"] = data_module(char_rels)

    for arch in archetypes:
        prefix = f"archetype_dialogues/{arch}/"
        rels = [r for r in all_data if r.startswith(prefix)]
        outputs[f"arch_{arch}.py"] = data_module(rels)

    # __init__.py — lazy 접근자 (SharpPy 호환: 정적 if-chain + 절대 import)
    lines = [HEADER]
    lines.append(f'SOURCE_HASH = "{source_hash(all_data)}"')
    lines.append(f"FILE_COUNT = {len(all_data)}")
    lines.append("")
    lines.append("")
    lines.append("def get(rel):")
    lines.append('    """dialogues 루트 기준 상대경로(posix)로 파싱된 dict 반환. 없으면 None."""')
    lines.append('    if rel.startswith("characters/"):')
    lines.append("        import dialogues_compiled.characters as m")
    lines.append("        return m.DATA.get(rel)")
    for arch in archetypes:
        lines.append(f'    if rel.startswith("archetype_dialogues/{arch}/"):')
        lines.append(f"        import dialogues_compiled.arch_{arch} as m")
        lines.append("        return m.DATA.get(rel)")
    lines.append("    return None")
    lines.append("")
    outputs["__init__.py"] = "\n".join(lines)

    return outputs


def main():
    check_mode = "--check" in sys.argv
    strict = "--strict" in sys.argv

    all_data, archetypes = load_and_validate()

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    fatal = list(errors) + (list(warnings) if strict else [])
    if fatal:
        print(f"\n검증 실패: 에러 {len(errors)}건"
              + (f", 경고(strict) {len(warnings)}건" if strict else "")
              + " — 아무것도 쓰지 않음")
        return 1

    outputs = render_outputs(all_data, archetypes)

    if check_mode:
        drift = []
        for fname, content in outputs.items():
            path = OUTPUT_ROOT / fname
            if not path.exists():
                drift.append(f"{fname} (없음)")
            elif path.read_text(encoding="utf-8") != content:
                drift.append(f"{fname} (내용 다름)")
        stale = [p.name for p in OUTPUT_ROOT.glob("*.py")
                 if p.name not in outputs] if OUTPUT_ROOT.exists() else []
        for s in stale:
            drift.append(f"{s} (소스에 없는 잔여 파일)")
        if drift:
            print("DRIFT: 컴파일본이 yaml 소스와 불일치 — compile_dialogues.py 재실행 필요:")
            for d in drift:
                print(f"  - {d}")
            return 1
        print(f"OK: 컴파일본 최신 (files={len(all_data)}, 경고 {len(warnings)}건)")
        return 0

    OUTPUT_ROOT.mkdir(exist_ok=True)
    for fname, content in outputs.items():
        (OUTPUT_ROOT / fname).write_text(content, encoding="utf-8", newline="\n")
    for p in OUTPUT_ROOT.glob("*.py"):
        if p.name not in outputs:
            p.unlink()
            print(f"제거: 잔여 {p.name}")
    print(f"OK: {len(all_data)}개 yaml → {len(outputs)}개 모듈 "
          f"(경고 {len(warnings)}건) → {OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    # 콘솔 한글 출력용 — 도구로 import될 때는 호출측 stdout을 건드리지 않음
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.exit(main())
