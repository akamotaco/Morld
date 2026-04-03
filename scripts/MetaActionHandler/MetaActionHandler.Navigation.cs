#define DEBUG_LOG

using Godot;
using Morld;

/// <summary>
/// MetaActionHandler - Navigation 핸들러
/// move, back, toggle, idle, inventory, look_unit 처리
/// </summary>
public partial class MetaActionHandler
{
	/// <summary>
	/// 이동 액션 처리: move:regionId:localId 또는 confirm_move:regionId:localId
	/// </summary>
	/// <param name="parts">move:regionId:localId 또는 confirm_move:regionId:localId</param>
	/// <param name="thresholdMillis">이 시간(밀리초) 이상이면 확인 다이얼로그, 0이면 즉시 이동</param>
	private void HandleMoveAction(string[] parts, int thresholdMillis)
	{
		if (parts.Length < 3)
		{
			GD.PrintErr("[MetaActionHandler] Invalid move format. Expected: move:regionId:localId");
			return;
		}

		if (!int.TryParse(parts[1], out int regionId) || !int.TryParse(parts[2], out int localId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid regionId or localId");
			return;
		}

		// threshold가 0이면 무한대로 처리 (다이얼로그 없이 즉시 이동)
		int effectiveThresholdMillis = thresholdMillis == 0 ? int.MaxValue : thresholdMillis;
		ExecuteMoveWithConfirm(regionId, localId, effectiveThresholdMillis);
	}

	/// <summary>
	/// 통합 이동 함수 - threshold 기반 확인 다이얼로그
	/// </summary>
	/// <param name="regionId">목적지 Region ID</param>
	/// <param name="localId">목적지 Location ID</param>
	/// <param name="thresholdMillis">이 시간(밀리초) 이상이면 확인 다이얼로그 표시</param>
	private void ExecuteMoveWithConfirm(int regionId, int localId, int thresholdMillis)
	{
		// TODO: 조건부 이동 체크 (locked 조건)
		// var (canMove, blockMessage) = CheckMoveConditions(regionId, localId);
		// if (!canMove)
		// {
		//     // 조건 미달 → 메시지 다이얼로그 + [확인] 버튼
		//     var dialogText = $"{blockMessage}\n\n[url=back]확인[/url]";
		//     _textUISystem?.PushDialog(dialogText, 0);
		//     return;
		// }

		// 이동 시간 계산 (경로 탐색 + 시간 계산)
		int travelTimeMillis = CalculateTravelTimeToDestination(regionId, localId);
		if (travelTimeMillis < 0)
		{
			_textUISystem?.ShowResult("이동할 수 없습니다.");
			return;
		}

		// 시간 정지 상태에서는 이동 시간이 소비되지 않으므로 확인 다이얼로그 생략
		var worldSystem = _world.GetSystem("worldSystem") as SE.WorldSystem;
		bool isTimeFrozen = worldSystem?.IsTimeFrozen() ?? false;

		// threshold 이상이면 확인 다이얼로그 (시간 정지 시 생략)
		if (!isTimeFrozen && travelTimeMillis >= thresholdMillis)
		{
			// 이동 확인 메시지 생성
			string message = FormatTravelTimeMessage(travelTimeMillis);

			// Yes 클릭 시 실행할 작업 저장
			_pendingAction = () => _playerSystem?.RequestCommand($"이동:{regionId}:{localId}");

			// Dialog 형식으로 YesNo 표시
			var dialogText = $"{message}\n\n[url=@ret:yes]예[/url]  [url=@ret:no]아니오[/url]";
			_textUISystem?.PushDialog(dialogText, 0);
			return;
		}

		// threshold 미만이면 즉시 이동
		_playerSystem?.RequestCommand($"이동:{regionId}:{localId}");
	}

	/// <summary>
	/// 이동 시간 포맷팅 (밀리초 → 시간/분 텍스트)
	/// </summary>
	private string FormatTravelTimeMessage(int travelTimeMillis)
	{
		int totalMinutes = travelTimeMillis / GameTime.MillisPerMinute;
		int hours = totalMinutes / 60;
		int minutes = totalMinutes % 60;

		string timeText;
		if (hours > 0)
			timeText = minutes > 0 ? $"{hours}시간 {minutes}분" : $"{hours}시간";
		else
			timeText = $"{minutes}분";

		return $"이동하는 데 {timeText}이 걸립니다. 이동하시겠습니까?";
	}

	/// <summary>
	/// 휴식 액션 처리: idle:millis
	/// </summary>
	private void HandleIdleAction(string[] parts)
	{
		if (parts.Length >= 2)
		{
			_playerSystem?.RequestCommand($"휴식:{parts[1]}");
		}
		else
		{
			GD.PrintErr("[MetaActionHandler] Invalid idle format. Expected: idle:millis");
		}
	}

	/// <summary>
	/// 기다리기 액션 처리: wait:millis
	/// </summary>
	private void HandleWaitAction(string[] parts)
	{
		if (parts.Length >= 2)
		{
			_playerSystem?.RequestCommand($"기다리기:{parts[1]}");
		}
		else
		{
			GD.PrintErr("[MetaActionHandler] Invalid wait format. Expected: wait:millis");
		}
	}

	/// <summary>
	/// 뒤로 가기 처리 (back, confirm, done)
	/// </summary>
	private void HandleBackAction()
	{
		_textUISystem?.Pop();
	}

	/// <summary>
	/// 토글 처리: toggle:toggleId
	/// </summary>
	private void HandleToggleAction(string[] parts)
	{
		if (parts.Length < 2)
		{
			GD.PrintErr("[MetaActionHandler] Invalid toggle format. Expected: toggle:toggleId");
			return;
		}

		_textUISystem?.ToggleExpand(parts[1]);
	}

	/// <summary>
	/// 인벤토리 확인 처리
	/// </summary>
	private void HandleInventoryAction()
	{
		_textUISystem?.ShowInventory();
	}

	/// <summary>
	/// 퀘스트 UI 표시 처리
	/// Python의 quest.show_quest_ui() Generator를 호출
	/// </summary>
	private void HandleQuestAction()
	{
		var scriptSystem = _world.GetSystem("scriptSystem") as SE.ScriptSystem;
		if (scriptSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] HandleQuestAction: ScriptSystem not found");
			return;
		}

		try
		{
			// Python quest 모듈의 show_quest_ui() 호출
			scriptSystem.Eval("import quest");
			var result = scriptSystem.Eval("quest.show_quest_ui()");

			if (result is SharpPy.PyGenerator generator)
			{
				var genResult = scriptSystem.ProcessGenerator(generator);
				if (genResult != null && genResult.Type == "generator_dialog" && genResult is SE.GeneratorScriptResult gr)
				{
					SetPendingGenerator(gr.Generator, gr.DialogRequest);

					// proc('init') 호출 - Dialog 초기화 시 텍스트 갱신
					var displayText = gr.DialogText;
					if (gr.DialogRequest?.ProcCallback != null)
					{
						var (initText, _) = scriptSystem.CallProcCallback(gr.DialogRequest.ProcCallback, "init");
						if (initText != null)
						{
							displayText = initText;
							gr.DialogRequest.UpdateCurrentPageText(initText);
						}
					}

					_textUISystem?.PushDialog(displayText, 0, gr.DialogRequest?.TimeFlows ?? false);
				}
			}
		}
		catch (System.Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] HandleQuestAction error: {ex.Message}");
		}
	}

	/// <summary>
	/// 설정 UI 표시 처리
	/// Python의 settings.show_settings_ui() Generator를 호출
	/// </summary>
	private void HandleSettingsAction()
	{
		var scriptSystem = _world.GetSystem("scriptSystem") as SE.ScriptSystem;
		if (scriptSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] HandleSettingsAction: ScriptSystem not found");
			return;
		}

		try
		{
			// Python settings 모듈의 show_settings_ui() 호출
			scriptSystem.Eval("import settings");
			var result = scriptSystem.Eval("settings.show_settings_ui()");

			if (result is SharpPy.PyGenerator generator)
			{
				var genResult = scriptSystem.ProcessGenerator(generator);
				if (genResult != null && genResult.Type == "generator_dialog" && genResult is SE.GeneratorScriptResult gr)
				{
					SetPendingGenerator(gr.Generator, gr.DialogRequest);

					// proc('init') 호출 - Dialog 초기화 시 텍스트 갱신
					var displayText = gr.DialogText;
					if (gr.DialogRequest?.ProcCallback != null)
					{
						var (initText, _) = scriptSystem.CallProcCallback(gr.DialogRequest.ProcCallback, "init");
						if (initText != null)
						{
							displayText = initText;
							gr.DialogRequest.UpdateCurrentPageText(initText);
						}
					}

					_textUISystem?.PushDialog(displayText, 0, gr.DialogRequest?.TimeFlows ?? false);
				}
			}
		}
		catch (System.Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] HandleSettingsAction error: {ex.Message}");
		}
	}

	/// <summary>
	/// 유닛 살펴보기 처리: look_unit:unitId
	///
	/// NPC 클릭 시 먼저 NPC 주도 이벤트(first meet, NPC 주도 스킨십 등)를 체크합니다.
	/// 이벤트가 있으면 Dialog로 실행하고, 없으면 일반 ShowUnitLook()을 호출합니다.
	///
	/// 이 로직은 이동 중인 NPC와의 만남 문제를 해결합니다.
	/// on_meet 이벤트는 두 유닛 모두 정지 상태여야 발동하지만,
	/// focus 시점에서 체크하면 이동 중인 NPC와도 이벤트가 발생합니다.
	/// </summary>
	private void HandleLookUnitAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int unitId))
		{
			GD.PrintErr("[MetaActionHandler] Invalid look_unit format. Expected: look_unit:unitId");
			return;
		}

		// NPC 주도 이벤트 체크 (first meet, NPC 주도 스킨십 등)
		var scriptSystem = _world.GetSystem("scriptSystem") as SE.ScriptSystem;
		if (scriptSystem != null)
		{
			try
			{
				// Python의 check_initiative_event() 호출
				scriptSystem.Eval("from assets import check_initiative_event");
				var result = scriptSystem.Eval($"check_initiative_event({unitId})");

				if (result is SharpPy.PyGenerator generator)
				{
					// NPC 주도 이벤트 발동
					var genResult = scriptSystem.ProcessGenerator(generator);
					if (genResult != null && genResult.Type == "generator_dialog"
						&& genResult is SE.GeneratorScriptResult gr)
					{
						// 플레이어 이동 취소 (시간 진행 중단 + Job 초기화)
						CancelPlayerMovement();

						// 스택을 Situation 상태로 정리 (다이얼로그 종료 후 현재 위치 표시를 위해)
						_textUISystem?.ShowSituation();

						SetPendingGenerator(gr.Generator, gr.DialogRequest);

						// proc('init') 호출
						var displayText = gr.DialogText;
						if (gr.DialogRequest?.ProcCallback != null)
						{
							var (initText, _) = scriptSystem.CallProcCallback(gr.DialogRequest.ProcCallback, "init");
							if (initText != null)
							{
								displayText = initText;
								gr.DialogRequest.UpdateCurrentPageText(initText);
							}
						}

						_textUISystem?.PushDialog(displayText, 0, gr.DialogRequest?.TimeFlows ?? false);
#if DEBUG_LOG
						GD.Print($"[MetaActionHandler] NPC initiative event triggered for unit {unitId}");
#endif
						return;  // 이벤트 실행됨, ShowUnitLook 스킵
					}
				}
			}
			catch (System.Exception ex)
			{
				GD.PrintErr($"[MetaActionHandler] check_initiative_event error: {ex.Message}");
			}
		}

		// Focus 시 on_meet 이벤트 체크 (충돌 반경 내, 아직 만난 적 없는 경우)
		var eventSystem = _world.GetSystem("eventSystem") as SE.EventSystem;
		if (eventSystem != null && eventSystem.TriggerOnMeetForFocus(unitId))
		{
			// on_meet 이벤트가 큐에 추가됨 → 이벤트 처리
			if (eventSystem.FlushEvents())
			{
#if DEBUG_LOG
				GD.Print($"[MetaActionHandler] Focus on_meet event triggered for unit {unitId}");
#endif
				return;  // on_meet 이벤트 실행됨, ShowUnitLook 스킵
			}
		}

		// NPC 주도 이벤트 없음, on_meet 없음 → 일반 focus UI 표시
		_textUISystem?.ShowUnitLook(unitId);
	}

	/// <summary>
	/// 목적지까지 이동 시간 계산
	/// Pi-World: X 좌표 기반 거리 계산
	/// Legacy: 경로 기반 시간 합산
	/// </summary>
	/// <returns>이동 시간(밀리초), 경로 없으면 -1</returns>
	private int CalculateTravelTimeToDestination(int regionId, int localId)
	{
		var destination = new LocationRef(regionId, localId);
		var player = _playerSystem?.FindPlayerUnit();
		if (player == null) return -1;

		var worldSystem = _world.GetSystem("worldSystem") as SE.WorldSystem;
		var itemSystem = _world.GetSystem("itemSystem") as SE.ItemSystem;
		var inventorySystem = _world.GetSystem("inventorySystem") as SE.InventorySystem;

		var terrain = worldSystem?.GetTerrain();
		if (terrain == null) return -1;

		// 이미 목적지에 있으면 0
		if (player.CurrentLocation == destination)
			return 0;

		// 아이템 효과가 반영된 Prop으로 경로 탐색
		var inventory = inventorySystem?.GetUnitInventory(player.Id);
		var equippedItems = inventorySystem?.GetUnitEquippedItems(player.Id);
		var actualProps = player.GetActualProps(itemSystem, inventory, equippedItems);
		var pathResult = terrain.FindPath(player.CurrentLocation, destination, actualProps);

		if (!pathResult.Found || pathResult.Path.Count < 2)
			return -1;

		int movementSpeedPercent = player.GetMovementSpeed(itemSystem, inventory, equippedItems);
		float speedModifier = movementSpeedPercent / 100f;

		return terrain.CalculatePathTravelTime(pathResult, player.PositionX, speedModifier, actualProps);
	}

	/// <summary>
	/// 지도 액션 처리: map:open 또는 map:move:regionId:localId
	/// Python의 map_ui.py 모듈 호출
	/// </summary>
	private void HandleMapAction(string[] parts)
	{
		if (parts.Length < 2)
		{
			GD.PrintErr("[MetaActionHandler] Invalid map format. Expected: map:open or map:move:regionId:localId");
			return;
		}

		var subAction = parts[1];

		var scriptSystem = _world.GetSystem("scriptSystem") as SE.ScriptSystem;
		if (scriptSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] HandleMapAction: ScriptSystem not found");
			return;
		}

		try
		{
			if (subAction == "open")
			{
				// 지도 UI 열기 - Python map_ui.show_map() 호출
				scriptSystem.Eval("import map_ui");
				var result = scriptSystem.Eval("map_ui.show_map()");

				if (result is SharpPy.PyGenerator generator)
				{
					var genResult = scriptSystem.ProcessGenerator(generator);
					if (genResult != null && genResult.Type == "generator_dialog" && genResult is SE.GeneratorScriptResult gr)
					{
						SetPendingGenerator(gr.Generator, gr.DialogRequest);

						// proc('init') 호출 - Dialog 초기화 시 텍스트 갱신
						var displayText = gr.DialogText;
						if (gr.DialogRequest?.ProcCallback != null)
						{
							var (initText, _) = scriptSystem.CallProcCallback(gr.DialogRequest.ProcCallback, "init");
							if (initText != null)
							{
								displayText = initText;
								gr.DialogRequest.UpdateCurrentPageText(initText);
							}
						}

						// time_flows=True인 다이얼로그(지도 등)에서 자동 시간 흐름 허용
						_textUISystem?.PushDialog(displayText, 0, gr.DialogRequest?.TimeFlows ?? false);
					}
				}
			}
			else if (subAction == "move" && parts.Length >= 4)
			{
				// 지도에서 이동 선택 - 장거리 이동 요청
				if (!int.TryParse(parts[2], out int regionId) || !int.TryParse(parts[3], out int localId))
				{
					GD.PrintErr("[MetaActionHandler] Invalid map move format");
					return;
				}

				// 장거리 이동 요청 (threshold 0으로 즉시 이동)
				_playerSystem?.RequestCommand($"이동:{regionId}:{localId}");
			}
			else if (subAction == "scroll" && parts.Length >= 3)
			{
				// map:scroll:left/right/up/down/center → Python ui.map_scroll(direction)
				var direction = parts[2];
				scriptSystem.CallModuleFunction("ui", "map_scroll", new SharpPy.PyStr(direction));
				// 탭 재렌더링 트리거
				_textUISystem?.RequestRefresh();
			}
			else if (subAction == "zoom" && parts.Length >= 3)
			{
				// map:zoom:in/out → Python ui.map_zoom(direction)
				var direction = parts[2];
				scriptSystem.CallModuleFunction("ui", "map_zoom", new SharpPy.PyStr(direction));
				_textUISystem?.RequestRefresh();
			}
		}
		catch (System.Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] HandleMapAction error: {ex.Message}");
		}
	}

	/// <summary>
	/// 자세 액션 처리: posture:toggle
	/// 통상 ↔ 은신 토글
	/// </summary>
	private void HandlePostureAction(string[] parts)
	{
		if (parts.Length < 2)
		{
			GD.PrintErr("[MetaActionHandler] Invalid posture format. Expected: posture:toggle");
			return;
		}

		var subAction = parts[1];
		if (subAction != "toggle")
		{
			GD.PrintErr($"[MetaActionHandler] Unknown posture action: {subAction}");
			return;
		}

		var scriptSystem = _world.GetSystem("scriptSystem") as SE.ScriptSystem;
		if (scriptSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] HandlePostureAction: ScriptSystem not found");
			return;
		}

		try
		{
			// Python ui 모듈의 toggle_posture() 호출
			var result = scriptSystem.CallFunctionEx("ui.toggle_posture", System.Array.Empty<string>());
#if DEBUG_LOG
			GD.Print($"[MetaActionHandler] toggle_posture result: {result?.Message}");
#endif

			// UI 갱신
			_textUISystem?.RequestUpdateDisplay();
		}
		catch (System.Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] HandlePostureAction error: {ex.Message}");
		}
	}

	/// <summary>
	/// 전투/평화 스탠스 토글: stance:toggle
	/// Python ui.toggle_stance() 호출
	/// </summary>
	private void HandleStanceAction(string[] parts)
	{
		if (parts.Length < 2 || parts[1] != "toggle")
		{
			GD.PrintErr("[MetaActionHandler] Invalid stance format. Expected: stance:toggle");
			return;
		}

		var scriptSystem = _world.GetSystem("scriptSystem") as SE.ScriptSystem;
		if (scriptSystem == null)
		{
			GD.PrintErr("[MetaActionHandler] HandleStanceAction: ScriptSystem not found");
			return;
		}

		try
		{
			scriptSystem.CallFunctionEx("ui.toggle_stance", System.Array.Empty<string>());
			_textUISystem?.RequestUpdateDisplay();
		}
		catch (System.Exception ex)
		{
			GD.PrintErr($"[MetaActionHandler] HandleStanceAction error: {ex.Message}");
		}
	}

	/// <summary>
	/// 위치 이동: move_x:targetX
	/// Location 내 X 좌표 변경 (거리 기반 시간 소비)
	/// </summary>
	private void HandleMoveXAction(string[] parts)
	{
		if (parts.Length < 2 || !float.TryParse(parts[1],
				System.Globalization.NumberStyles.Float,
				System.Globalization.CultureInfo.InvariantCulture,
				out float targetX))
		{
			GD.PrintErr("[MetaActionHandler] Invalid move_x format. Expected: move_x:targetX");
			return;
		}

		var player = _playerSystem?.FindPlayerUnit();
		if (player == null) return;

		// 앉은 상태에서는 이동 불가
		if (player.TraversalContext.Props.GetByType("seated_on").FirstOrDefault().Prop.IsValid)
			return;

		// Location 정보 가져오기
		var worldSystem = _world.GetSystem("worldSystem") as SE.WorldSystem;
		var terrain = worldSystem?.GetTerrain();
		if (terrain == null) return;
		var location = terrain.GetLocation(player.CurrentLocation);
		if (location == null) return;

		// X 좌표 정규화 (Ring: 0~360 wrap, Line: 0~Length clamp)
		targetX = location.NormalizeX(targetX);

		// 거리 계산
		float distance = location.CalculateDistance(player.PositionX, targetX);
		if (distance <= 0f)
		{
			_textUISystem?.RequestUpdateDisplay();
			return;
		}

		// 이동 속도 계수 계산 (장비/자세/혼잡 등 반영)
		var itemSystem = _world.GetSystem("itemSystem") as SE.ItemSystem;
		var inventorySystem = _world.GetSystem("inventorySystem") as SE.InventorySystem;
		var inventory = inventorySystem?.GetUnitInventory(player.Id);
		var equippedItems = inventorySystem?.GetUnitEquippedItems(player.Id);
		int movementSpeedPercent = player.GetMovementSpeed(itemSystem, inventory, equippedItems);
		float speedModifier = movementSpeedPercent / 100f;

		// 이동 시간 계산 (밀리초)
		int travelTimeMs = location.CalculateTravelTime(player.PositionX, targetX, speedModifier);

		// 플레이어 위치 설정
		player.PositionX = targetX;
		player.CurrentMovement = null;

		// 시간 정지 상태면 즉시 이동 (시간 소비 없음)
		bool isTimeFrozen = worldSystem?.IsTimeFrozen() ?? false;
		if (!isTimeFrozen && travelTimeMs > 0)
		{
			_playerSystem?.RequestTimeAdvance(travelTimeMs, "위치 이동");
		}

		_textUISystem?.RequestUpdateDisplay();
	}

	#region TODO: 조건부 이동 시스템

	// === 이동 조건 체계 설계 ===
	//
	// | 상태                    | UI 표시    | 클릭 시                        |
	// |------------------------|------------|-------------------------------|
	// | 연결 없음               | 표시 안됨   | -                             |
	// | 조건 미달 (hidden)      | 표시 안됨   | -                             |
	// | 조건 미달 (locked)      | 정상 표시   | 메시지 다이얼로그 + [확인]      |
	// | 조건 충족 (단거리)       | 정상 표시   | 즉시 이동                      |
	// | 조건 충족 (장거리)       | 정상 표시   | 확인 다이얼로그 + [예/아니오]   |
	//
	// === Gate 조건 타입 ===
	//
	// - hidden: 조건 미달 시 목록에서 숨김 (예: 관찰력 부족으로 숨겨진 문 못찾음)
	// - locked: 조건 미달 시 표시는 되나 이동 시 메시지 (예: 잠긴 문)
	//
	// === Python Gate 정의 예시 ===
	//
	// GATES = [
	//     (0, 1, 1),  # 기본 연결
	//     (1, 10, 1, {"hidden": {"관찰력": 5}}),  # 숨겨진 문
	//     (1, 11, 1, {"locked": {"has:열쇠": 1}, "message": "문이 잠겨 있다."}),  # 잠긴 문
	// ]
	//
	// === C# 구현 TODO ===
	//
	// private (bool canMove, string? blockMessage) CheckMoveConditions(int regionId, int localId)
	// {
	//     // 1. Gate에서 locked 조건 가져오기
	//     // 2. 플레이어 props와 비교
	//     // 3. 미달 시 (false, message) 반환
	//     // 4. 충족 시 (true, null) 반환
	// }

	#endregion

	/// <summary>
	/// 탭 전환 액션: tab:인덱스
	/// 클릭으로 탭을 직접 전환
	/// </summary>
	private void HandleTabAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int tabIndex))
		{
			GD.PrintErr("[MetaActionHandler] Invalid tab format. Expected: tab:index");
			return;
		}

		var current = _textUISystem?.CurrentFocus;
		if (current == null) return;

		current.ViewTab = tabIndex;
		_textUISystem?.RequestUpdateDisplay();
		_textUISystem?.FlushDisplay();
	}
}
