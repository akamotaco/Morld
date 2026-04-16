# test_linear_dungeon.py — e2e 구조 테스트
#
# 실행: python test_linear_dungeon.py
# (mock 없이 linear_dungeon 순수 함수만 테스트 — 이벤트/UI 외부 의존 없음)

import io
import os
import random
import sys
import traceback


# Windows cp949 콘솔에서도 한글/em-dash 출력 가능하도록 UTF-8 재포장
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# ============================================
# Path 설정 + 최소 mock (linear_dungeon 로드용)
# ============================================

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_python_dir = os.path.abspath(os.path.join(_tests_dir, ".."))
_common_dir = os.path.abspath(os.path.join(_tests_dir, "..", "..", "..", "common", "python"))

if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)
if _common_dir not in sys.path:
    sys.path.append(_common_dir)


class _StubMorld:
    """linear_dungeon.generate_nodes / advance 테스트에 필요한 최소 API."""
    def get_game_time(self): return 0
    def get_player_id(self): return 1
    def get_unit_location(self, uid): return None
    def set_unit_location(self, *a, **kw): pass
    def get_unit_prop(self, *a, **kw): return None
    def set_unit_prop(self, *a, **kw): pass
    def modify_prop(self, *a, **kw): pass
    def advance_time_des(self, *a, **kw): pass
    def get_unit_name(self, uid): return f"U{uid}"


sys.modules.setdefault("morld", _StubMorld())

import linear_dungeon as ld


# ============================================
# 테스트 유틸
# ============================================

def _bfs_reachable(nodes, start_id, target_type):
    """start에서 paths를 따라 target_type 노드에 도달 가능한지."""
    visited = {start_id}
    stack = [start_id]
    while stack:
        nid = stack.pop()
        if nodes[nid]["type"] == target_type:
            return True
        for p in nodes[nid]["paths"]:
            if p not in visited:
                visited.add(p)
                stack.append(p)
    return False


# ============================================
# Tests
# ============================================

class TestGenerateNodes:

    def test_endpoints_present(self):
        """첫 노드 START, 마지막 노드 EXIT."""
        for seed in range(10):
            random.seed(seed)
            nodes = ld.generate_nodes(depth=6, max_width=3)
            assert nodes[0]["type"] == ld.NODE_START, f"seed={seed}"
            assert any(n["type"] == ld.NODE_EXIT for n in nodes), f"seed={seed}"

    def test_exit_reachable_from_start(self):
        """START에서 EXIT까지 forward 경로 존재."""
        for seed in range(20):
            random.seed(seed)
            nodes = ld.generate_nodes(depth=6, max_width=3)
            assert _bfs_reachable(nodes, 0, ld.NODE_EXIT), f"seed={seed}"

    def test_depth_minimum(self):
        """depth=1/2도 크래시 없이 생성 (내부에서 3으로 클램프)."""
        for d in (1, 2, 3):
            random.seed(0)
            nodes = ld.generate_nodes(depth=d, max_width=2)
            assert len(nodes) >= 3
            assert nodes[0]["type"] == ld.NODE_START

    def test_no_orphan_content_nodes(self):
        """컨텐츠 노드가 incoming path를 최소 1개 가짐 (reachable)."""
        for seed in range(20):
            random.seed(seed)
            nodes = ld.generate_nodes(depth=6, max_width=3)
            incoming = {n["id"]: 0 for n in nodes}
            for n in nodes:
                for p in n["paths"]:
                    incoming[p] += 1
            # START 제외 모든 노드는 incoming ≥ 1
            for n in nodes:
                if n["type"] == ld.NODE_START:
                    continue
                assert incoming[n["id"]] >= 1, f"seed={seed} orphan id={n['id']}"

    def test_paths_point_to_valid_ids(self):
        """paths가 모두 유효한 노드 id를 가리킴."""
        for seed in range(20):
            random.seed(seed)
            nodes = ld.generate_nodes(depth=6, max_width=3)
            valid_ids = {n["id"] for n in nodes}
            for n in nodes:
                for p in n["paths"]:
                    assert p in valid_ids, f"seed={seed} bad path {p} in {n['id']}"

    def test_exit_has_no_paths(self):
        """EXIT 노드는 paths 비어있음."""
        for seed in range(10):
            random.seed(seed)
            nodes = ld.generate_nodes(depth=6, max_width=3)
            for n in nodes:
                if n["type"] == ld.NODE_EXIT:
                    assert n["paths"] == [], f"seed={seed} EXIT has paths"

    def test_labels_match_paths(self):
        """labels 길이가 paths와 같고, 각 방 타입을 반영."""
        for seed in range(10):
            random.seed(seed)
            nodes = ld.generate_nodes(depth=6, max_width=3)
            for n in nodes:
                assert len(n["labels"]) == len(n["paths"]), f"seed={seed} {n['id']}"
                for i, p in enumerate(n["paths"]):
                    target_type = nodes[p]["type"]
                    label = n["labels"][i]
                    # 라벨은 각 방 타입 이름 포함 (종료/계속 같은 일반어 금지)
                    assert any(
                        room_name in label
                        for room_name in (
                            "전투방", "휴식방", "출구", "시작방",
                            "엘리트 전투방", "캠프", "보물방", "이벤트방", "빈방", "???",
                        )
                    ), f"seed={seed} bad label '{label}'"
                    # "계속", "종료" 금지
                    assert "계속" not in label and "종료" not in label


class TestRandomWalkCompletion:

    def test_random_walk_reaches_exit(self):
        """START부터 랜덤 path 선택만으로 EXIT 도달."""
        for seed in range(30):
            random.seed(seed)
            nodes = ld.generate_nodes(depth=6, max_width=3)

            current = 0  # START
            steps = 0
            path_trace = [0]
            while nodes[current]["type"] != ld.NODE_EXIT and steps < 100:
                paths = nodes[current]["paths"]
                assert paths, f"seed={seed} dead-end at {current}"
                current = random.choice(paths)
                path_trace.append(current)
                steps += 1
            assert nodes[current]["type"] == ld.NODE_EXIT, (
                f"seed={seed} did not reach EXIT. trace={path_trace}"
            )


class TestAdvance:

    def test_advance_allowed_targets_only(self):
        """advance는 현재 노드의 paths에 있는 id만 허용."""
        random.seed(0)
        ld.enter(depth=5, max_width=2)
        node = ld.get_current_node()
        valid = node["paths"][0]

        # 유효한 타겟
        r = ld.advance(valid)
        assert r["ok"], "valid advance failed"

        # 무효한 타겟 (현 노드 paths에 없는 id)
        bad_id = 999
        r = ld.advance(bad_id)
        assert not r["ok"], "invalid advance unexpectedly succeeded"
        ld.reset()

    def test_full_play_through(self):
        """enter → 랜덤 walk로 advance만 호출하며 EXIT까지 도달."""
        random.seed(1)
        ld.enter(depth=6, max_width=3)
        steps = 0
        while ld.is_active() and steps < 100:
            node = ld.get_current_node()
            if node["type"] == ld.NODE_EXIT:
                # 테스트는 여기서 끝 (exit_to_village는 morld 의존 많아 생략)
                break
            # BATTLE/ELITE/UNKNOWN은 advance 차단 가능 — cleared=True 강제
            if node["type"] in (ld.NODE_BATTLE, ld.NODE_ELITE):
                node["cleared"] = True
            elif node["type"] == ld.NODE_UNKNOWN:
                # UNKNOWN은 실전에선 reveal로 바뀌지만 테스트는 그대로 통과시킴
                node["cleared"] = True
            paths = node["paths"]
            assert paths, f"dead-end at {node['id']}"
            target = random.choice(paths)
            r = ld.advance(target)
            assert r["ok"], f"advance({target}) failed at {node['id']}: {r.get('reason')}"
            steps += 1
        assert ld.get_current_node()["type"] == ld.NODE_EXIT
        ld.reset()


# ============================================
# 테스트 러너
# ============================================

def _run():
    test_classes = [TestGenerateNodes, TestRandomWalkCompletion, TestAdvance]
    passed = failed = errors = 0
    for cls in test_classes:
        instance = cls()
        for name in sorted(dir(instance)):
            if not name.startswith("test_"):
                continue
            method = getattr(instance, name)
            full = f"{cls.__name__}.{name}"
            try:
                method()
                print(f"  PASS  {full}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {full}: {e}")
                failed += 1
            except Exception as e:
                print(f"  ERROR {full}: {e}")
                traceback.print_exc()
                errors += 1

    total = passed + failed + errors
    print("=" * 50)
    print(f"TOTAL: {passed}/{total} passed ({failed} failed, {errors} errors)")
    return 0 if failed == 0 and errors == 0 else 1


if __name__ == "__main__":
    sys.exit(_run())
