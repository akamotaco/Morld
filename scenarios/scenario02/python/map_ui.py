# map_ui.py - 지도 UI 모듈
#
# 지도 아이템 소지 시 활성화되는 지도 기능
# - tree 형태로 현재 region의 장소 표시
# - 장소 선택 시 장거리 이동 (path planning)
# - 다른 region으로 이동 가능한 장소 표시

import morld


def show_map():
    """
    지도 다이얼로그 표시

    Generator 방식으로 구현
    - proc 콜백으로 장소 선택 처리
    - 선택 시 이동 시간 표시 후 이동 또는 취소
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return

    current_loc = morld.get_unit_location(player_id)
    if current_loc is None:
        return

    current_region_id, current_local_id = current_loc

    state = {
        "region_id": current_region_id,
        "local_id": current_local_id,
        "selected": None,  # (region_id, local_id) 선택된 목적지
    }

    def handle_action(action):
        if action == "init":
            return None

        # 자동 시간 흐름에 의한 갱신 (tick)
        if action == "tick":
            return _render_map(state)  # 지도 다시 렌더링

        # 취소
        if action == "cancel":
            return True  # 다이얼로그 종료

        # 장소 선택: "region_id:local_id"
        if ":" in action:
            parts = action.split(":")
            if len(parts) == 2:
                try:
                    region_id = int(parts[0])
                    local_id = int(parts[1])

                    # 현재 위치면 무시
                    if region_id == state["region_id"] and local_id == state["local_id"]:
                        return None

                    state["selected"] = (region_id, local_id)
                    return True  # 다이얼로그 종료
                except ValueError:
                    pass

        return None

    text = _render_map(state)
    # time_flows=True: 지도를 보는 동안에도 자동 시간 흐름 허용
    # proc("tick")으로 지도 UI 자동 갱신
    yield morld.dialog(text, autofill="off", proc=handle_action, result=state, time_flows=True)

    # 선택된 목적지가 있으면 이동 확인
    if state["selected"]:
        dest_region, dest_local = state["selected"]
        travel_time = morld.get_travel_time(
            state["region_id"], state["local_id"],
            dest_region, dest_local,
            player_id
        )

        if travel_time > 0:
            # 이동 시간 표시 및 확인
            time_text = _format_time(travel_time)

            # 목적지 이름 조회
            region_info = morld.get_region_info(dest_region)
            dest_name = "알 수 없는 장소"
            if region_info:
                for loc in region_info["locations"]:
                    if loc["id"] == dest_local:
                        dest_name = loc["name"]
                        break

            confirm_state = {"confirmed": False}

            def confirm_handler(action):
                if action == "init":
                    return None
                if action == "yes":
                    confirm_state["confirmed"] = True
                    return True
                return True  # 아니오도 종료

            confirm_text = (
                f"[b]{dest_name}[/b](으)로 이동합니다.\n"
                f"이동 시간: {time_text}\n\n"
                "[url=@proc:yes]이동[/url]  [url=@proc:no]취소[/url]"
            )
            yield morld.dialog(confirm_text, autofill="off", proc=confirm_handler)

            if confirm_state["confirmed"]:
                # 이동 실행 - PlayerSystem.RequestCommand로 시간 진행 포함
                morld.request_player_command(f"이동:{dest_region}:{dest_local}")


def _render_map(state: dict) -> str:
    """
    지도 텍스트 렌더링

    현재 region의 장소를 tree 형태로 표시
    - 현재 위치 강조
    - 다른 region으로 가는 장소 표시
    - 각 장소에 있는 캐릭터 표시
    """
    region_id = state["region_id"]
    current_local = state["local_id"]
    player_id = morld.get_player_id()

    region_info = morld.get_region_info(region_id)
    if not region_info:
        return "[지도]\n\n지역 정보를 불러올 수 없습니다.\n\n[url=@proc:cancel]닫기[/url]"

    lines = []
    lines.append(f"[b]지도 - {region_info['name']}[/b]")
    lines.append("")

    # 각 장소에 있는 캐릭터 미리 조회 (플레이어 제외, 오브젝트 제외)
    # 이동 중인 캐릭터는 목적지에 "(→이름)" 형태로 표시
    location_characters = {}
    for loc in region_info["locations"]:
        loc_id = loc["id"]
        unit_ids = morld.get_units_at_location(region_id, loc_id)
        characters = []
        for unit_id in unit_ids:
            if unit_id == player_id:
                continue
            info = morld.get_unit_info(unit_id)
            if info and not info.get("is_object", False):
                characters.append(info.get("name", "???"))
        location_characters[loc_id] = characters

    # 이동 중인 캐릭터 조회 (Edge 위에 있는 유닛)
    # 목적지 Location에 "→이름" 형태로 추가
    all_units = morld.get_all_unit_ids()
    for unit_id in all_units:
        if unit_id == player_id:
            continue
        info = morld.get_unit_info(unit_id)
        if not info or info.get("is_object", False):
            continue
        # Edge 위에서 이동 중인 유닛만
        if not info.get("is_on_edge", False):
            continue
        # 같은 region의 목적지로 이동 중인지 확인
        dest_region = info.get("dest_region_id")
        dest_local = info.get("dest_location_id")
        if dest_region == region_id and dest_local is not None:
            name = info.get("name", "???")
            if dest_local not in location_characters:
                location_characters[dest_local] = []
            location_characters[dest_local].append(f"→{name}")

    # 위치 목록 (id 순 정렬)
    locations = sorted(region_info["locations"], key=lambda x: x["id"])

    # 인접 관계 빌드 (tree 구조용)
    adjacency = {}
    for loc in locations:
        loc_id = loc["id"]
        adjacency[loc_id] = set()
        for edge in loc["edges"]:
            to_local, _ = edge
            adjacency[loc_id].add(to_local)

    # BFS로 현재 위치부터 tree 구조 생성
    visited = set()
    tree_lines = []

    def build_tree(loc_id, depth=0):
        if loc_id in visited:
            return
        visited.add(loc_id)

        loc_info = None
        for loc in locations:
            if loc["id"] == loc_id:
                loc_info = loc
                break

        if not loc_info:
            return

        # 들여쓰기
        indent = "  " * depth

        # 이 장소에 있는 캐릭터
        chars = location_characters.get(loc_id, [])
        char_text = ""
        if chars:
            char_text = f" [color=lime][{', '.join(chars)}][/color]"

        # 현재 위치 표시
        if loc_id == current_local:
            marker = "[color=yellow]>[/color] "
            name_display = f"[color=yellow]{loc_info['name']}[/color]{char_text} [color=gray](현재 위치)[/color]"
            tree_lines.append(f"{indent}{marker}{name_display}")
        else:
            # 이동 가능 표시 (클릭 가능)
            marker = "- "
            travel_time = morld.get_travel_time(
                region_id, current_local,
                region_id, loc_id,
                morld.get_player_id()
            )
            if travel_time > 0:
                time_text = _format_time(travel_time)
                tree_lines.append(
                    f"{indent}{marker}[url=@proc:{region_id}:{loc_id}]{loc_info['name']}[/url]{char_text} "
                    f"[color=gray]({time_text})[/color]"
                )
            elif travel_time == 0:
                # 바로 옆 (이미 같은 위치 - shouldn't happen)
                tree_lines.append(f"{indent}{marker}{loc_info['name']}{char_text}")
            else:
                # 도달 불가
                tree_lines.append(f"{indent}{marker}[color=gray]{loc_info['name']} (도달 불가)[/color]{char_text}")

        # 다른 region으로 가는 연결 표시
        for region_edge in loc_info.get("region_edges", []):
            to_region, to_local, region_name = region_edge
            child_indent = "  " * (depth + 1)
            tree_lines.append(
                f"{child_indent}[color=cyan]-> {region_name}[/color]"
            )

        # 인접 장소 재귀 (이미 방문하지 않은 것만, 이동 시간 순 정렬)
        neighbors = list(adjacency.get(loc_id, []))
        # 각 인접 장소까지의 이동 시간 계산 후 정렬
        neighbor_times = []
        for neighbor_id in neighbors:
            travel_time = morld.get_travel_time(
                region_id, current_local,
                region_id, neighbor_id,
                morld.get_player_id()
            )
            neighbor_times.append((neighbor_id, travel_time if travel_time >= 0 else 999999))
        neighbor_times.sort(key=lambda x: x[1])

        for neighbor_id, _ in neighbor_times:
            build_tree(neighbor_id, depth + 1)

    # 현재 위치부터 시작
    build_tree(current_local)

    # 방문하지 않은 장소도 추가 (분리된 영역)
    for loc in locations:
        if loc["id"] not in visited:
            build_tree(loc["id"], 0)

    lines.extend(tree_lines)
    lines.append("")
    lines.append("[url=@proc:cancel]닫기[/url]")

    return "\n".join(lines)


def _format_time(minutes: int) -> str:
    """분 단위 시간을 읽기 좋은 형식으로 변환"""
    if minutes < 60:
        return f"{minutes}분"
    hours = minutes // 60
    mins = minutes % 60
    if mins > 0:
        return f"{hours}시간 {mins}분"
    return f"{hours}시간"
