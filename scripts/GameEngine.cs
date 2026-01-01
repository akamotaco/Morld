#define DEBUG_LOG

using Godot;
using System;
using Mysix;
using System.Diagnostics;
using SE;

public partial class GameEngine : Node
{
	// Called when the node enters the scene tree for the first time.
	private SE.World _world;
	private PlayerSystem _playerSystem;
	private DescribeSystem _describeSystem;
	private RichTextLabel _textUi;

	public override void _Ready()
	{
		var text_ui_path = GetMeta("TextUI").As<string>(); //../Control/RichTextLabel
		this._textUi = GetNode<RichTextLabel>(text_ui_path);
		if (this._textUi == null) {
			GD.PrintErr($"TextUi 메타가 null이거나 유효하지 않습니다.({GetMeta("TextUI")})");
			throw new InvalidOperationException("TextUi 메타가 null이거나 유효하지 않습니다.");
		}

		// BBCode 활성화 및 meta_clicked 시그널 연결
		this._textUi.BbcodeEnabled = true;
		this._textUi.MetaClicked += OnMetaClicked;

		this._world = new SE.World(this);

		(this._world.AddSystem(new WorldSystem("aka"), "worldSystem") as WorldSystem).GetTerrain().UpdateFromFile("res://scripts/morld/json_data/location_data.json");
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTime().UpdateFromFile("res://scripts/morld/json_data/time_data.json");

		(this._world.AddSystem(new UnitSystem(), "unitSystem") as UnitSystem).UpdateFromFile("res://scripts/morld/json_data/unit_data.json");

		(this._world.AddSystem(new ItemSystem(), "itemSystem") as ItemSystem).UpdateFromFile("res://scripts/morld/json_data/item_data.json");

		this._world.AddSystem(new ActionSystem(), "actionSystem");

		// Logic Systems - 실행 순서: MovementSystem → BehaviorSystem → PlayerSystem → DescribeSystem
		this._world.AddSystem(new MovementSystem(), "movementSystem");
		this._world.AddSystem(new BehaviorSystem(), "behaviorSystem");
		_playerSystem = this._world.AddSystem(new PlayerSystem(), "playerSystem") as PlayerSystem;
		_describeSystem = this._world.AddSystem(new DescribeSystem(), "describeSystem") as DescribeSystem;

		// 초기 상황 설명 표시
		UpdateSituationText();

#if DEBUG_LOG
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTerrain().DebugPrint();
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTime().DebugPrint();
		(this._world.FindSystem("unitSystem") as UnitSystem).DebugPrint();

		Debug.Print($"System Count : {this._world.GetAllSystem().Count}");
		GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		GD.Print("[GameEngine] 입력 테스트 모드");
		GD.Print("  마우스 왼쪽 클릭: 4시간 (240분) 진행");
		GD.Print("  마우스 오른쪽 클릭: 15분 진행");
		GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
	}

	// public override void _Input(InputEvent @event)
	// {
	// 	if (@event is InputEventMouseButton mouseEvent && mouseEvent.Pressed)
	// 	{
	// 		if (mouseEvent.ButtonIndex == MouseButton.Left)
	// 		{
	// 			// 왼쪽 클릭: 4시간 진행
	// 			_playerSystem?.RequestTimeAdvance(240, "수면 (4시간)");
	// 		}
	// 		else if (mouseEvent.ButtonIndex == MouseButton.Right)
	// 		{
	// 			// 오른쪽 클릭: 15분 진행
	// 			_playerSystem?.RequestTimeAdvance(15, "휴식 (15분)");
	// 		}
	// 	}
	// }

	// Called every frame. 'delta' is the elapsed time since the previous frame.
	public override void _Process(double delta)
	{
		// 대기 중인 시간이 있을 때만 Step 실행
		if (_playerSystem == null || !_playerSystem.HasPendingTime)
			return;

		int delta_int = (int)(delta * 1000);
		this._world.Step(delta_int);

		// 시간 진행 완료 후 상황 설명 업데이트
		if (!_playerSystem.HasPendingTime)
		{
			UpdateSituationText();
		}
	}

	/// <summary>
	/// 현재 상황 설명을 TextUI에 표시
	/// </summary>
	private void UpdateSituationText()
	{
		if (_playerSystem == null || _describeSystem == null || _textUi == null)
			return;

		var worldSystem = _world.FindSystem("worldSystem") as WorldSystem;
		var lookResult = _playerSystem.Look();
		var time = worldSystem?.GetTime();

		var text = _describeSystem.GetSituationText(lookResult, time);
		_textUi.Text = text;
	}

	/// <summary>
	/// BBCode 링크 클릭 핸들러
	/// meta 포맷: move:regionId:localId, idle, idle:minutes, back
	/// </summary>
	private void OnMetaClicked(Variant meta)
	{
		var metaString = meta.AsString();
		if (string.IsNullOrEmpty(metaString))
			return;

		var parts = metaString.Split(':');
		var action = parts[0];

#if DEBUG_LOG
		GD.Print($"[GameEngine] Meta clicked: {metaString}");
#endif

		switch (action)
		{
			case "move":
				HandleMoveAction(parts);
				break;
			case "idle":
				HandleIdleAction(parts);
				break;
			case "back":
				HandleBackAction();
				break;
			case "inventory":
				HandleInventoryAction();
				break;
			case "pickup":
				HandlePickupAction(parts);
				break;
			case "drop":
				HandleDropAction(parts);
				break;
			case "look_unit":
				HandleLookUnitAction(parts);
				break;
			case "take":
				HandleTakeAction(parts);
				break;
			case "put":
				HandlePutAction(parts);
				break;
			case "action":
				HandleUnitAction(parts);
				break;
			case "item_ground_menu":
				HandleItemGroundMenuAction(parts);
				break;
			case "item_inv_menu":
				HandleItemInvMenuAction(parts);
				break;
			case "back_inventory":
				HandleInventoryAction();
				break;
			case "item_use":
				HandleItemUseAction(parts);
				break;
			case "item_combine":
				HandleItemCombineAction(parts);
				break;
			default:
				GD.PrintErr($"[GameEngine] Unknown action: {action}");
				break;
		}
	}

	/// <summary>
	/// 이동 액션 처리: move:regionId:localId
	/// </summary>
	private void HandleMoveAction(string[] parts)
	{
		if (parts.Length < 3)
		{
			GD.PrintErr("[GameEngine] Invalid move format. Expected: move:regionId:localId");
			return;
		}

		// meta를 PlayerSystem 명령으로 변환: move:0:1 → 이동:0:1
		_playerSystem?.RequestCommand($"이동:{parts[1]}:{parts[2]}");
	}

	/// <summary>
	/// 휴식 액션 처리: idle 또는 idle:minutes
	/// </summary>
	private void HandleIdleAction(string[] parts)
	{
		if (parts.Length == 1)
		{
			// idle - 시간 선택 UI로 전환
			ShowIdleTimeSelection();
		}
		else if (parts.Length >= 2)
		{
			// idle:minutes - 실제 휴식 실행
			_playerSystem?.RequestCommand($"휴식:{parts[1]}");
		}
		else
		{
			GD.PrintErr("[GameEngine] Invalid idle format");
		}
	}

	/// <summary>
	/// 멍때리기 시간 선택 UI 표시 (2단계)
	/// </summary>
	private void ShowIdleTimeSelection()
	{
		if (_textUi == null) return;

		// 기존 idle 링크를 시간 선택지로 교체
		var currentText = _textUi.Text;
		var idlePattern = "[url=idle]멍때리기[/url]";
		var idleOptions = @"[url=idle:15]멍때리기 (15분)[/url]
  [url=idle:30]멍때리기 (30분)[/url]
  [url=idle:60]멍때리기 (1시간)[/url]
  [url=idle:240]멍때리기 (4시간)[/url]
  [url=back]뒤로[/url]";

		if (currentText.Contains(idlePattern))
		{
			_textUi.Text = currentText.Replace(idlePattern, idleOptions);
		}
	}

	/// <summary>
	/// 뒤로 가기 처리 - 원래 UI로 복원
	/// </summary>
	private void HandleBackAction()
	{
		// 상황 설명 다시 표시 (원래 상태로 복원)
		UpdateSituationText();
	}

	/// <summary>
	/// 인벤토리 확인 처리
	/// </summary>
	private void HandleInventoryAction()
	{
		if (_describeSystem != null && _textUi != null)
		{
			var text = _describeSystem.GetInventoryText();
			_textUi.Text = text;
		}
	}

	/// <summary>
	/// 아이템 줍기 처리: pickup:itemId
	/// </summary>
	private void HandlePickupAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[GameEngine] Invalid pickup format. Expected: pickup:itemId");
			return;
		}

		_playerSystem?.PickupItem(itemId);
		UpdateSituationText();
	}

	/// <summary>
	/// 아이템 놓기 처리: drop:itemId
	/// </summary>
	private void HandleDropAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[GameEngine] Invalid drop format. Expected: drop:itemId");
			return;
		}

		_playerSystem?.DropItem(itemId);
		UpdateSituationText();
	}

	/// <summary>
	/// 유닛 살펴보기 처리: look_unit:unitId
	/// </summary>
	private void HandleLookUnitAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int unitId))
		{
			GD.PrintErr("[GameEngine] Invalid look_unit format. Expected: look_unit:unitId");
			return;
		}

		var unitLook = _playerSystem?.LookUnit(unitId);
		if (unitLook != null && _describeSystem != null && _textUi != null)
		{
			var text = _describeSystem.GetUnitLookText(unitLook);
			_textUi.Text = text;
		}
	}

	/// <summary>
	/// 유닛에서 아이템 가져오기 처리: take:unitId:itemId
	/// </summary>
	private void HandleTakeAction(string[] parts)
	{
		if (parts.Length < 3 || !int.TryParse(parts[1], out int unitId) || !int.TryParse(parts[2], out int itemId))
		{
			GD.PrintErr("[GameEngine] Invalid take format. Expected: take:unitId:itemId");
			return;
		}

		_playerSystem?.TakeFromUnit(unitId, itemId);

		// 유닛 살펴보기 화면 새로고침
		var unitLook = _playerSystem?.LookUnit(unitId);
		if (unitLook != null && _describeSystem != null && _textUi != null)
		{
			var text = _describeSystem.GetUnitLookText(unitLook);
			_textUi.Text = text;
		}
	}

	/// <summary>
	/// 유닛에 아이템 넣기 처리: put:unitId:itemId
	/// </summary>
	private void HandlePutAction(string[] parts)
	{
		if (parts.Length < 3 || !int.TryParse(parts[1], out int unitId) || !int.TryParse(parts[2], out int itemId))
		{
			GD.PrintErr("[GameEngine] Invalid put format. Expected: put:unitId:itemId");
			return;
		}

		_playerSystem?.PutToUnit(unitId, itemId);

		// 유닛 살펴보기 화면 새로고침
		var unitLook = _playerSystem?.LookUnit(unitId);
		if (unitLook != null && _describeSystem != null && _textUi != null)
		{
			var text = _describeSystem.GetUnitLookText(unitLook);
			_textUi.Text = text;
		}
	}

	/// <summary>
	/// 유닛 행동 처리: action:actionType:unitId
	/// </summary>
	private void HandleUnitAction(string[] parts)
	{
		if (parts.Length < 3)
		{
			GD.PrintErr("[GameEngine] Invalid action format. Expected: action:actionType:unitId");
			return;
		}

		var actionType = parts[1];

		if (!int.TryParse(parts[2], out int unitId))
		{
			GD.PrintErr("[GameEngine] Invalid unitId in action");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[GameEngine] 유닛 행동: unitId={unitId}, type={actionType}");
#endif

		// ActionSystem을 통해 행동 실행
		var actionSystem = _world.FindSystem("actionSystem") as ActionSystem;
		var unitSystem = _world.FindSystem("unitSystem") as UnitSystem;

		if (actionSystem != null && unitSystem != null && _playerSystem != null)
		{
			var player = _playerSystem.GetPlayerUnit();
			var target = unitSystem.GetUnit(unitId);

			if (player != null && target != null)
			{
				var result = actionSystem.ApplyAction(player, actionType, new System.Collections.Generic.List<Morld.Unit> { target });

				if (_textUi != null)
				{
					_textUi.Text = $"[b]{result.Message}[/b]\n\n[url=back]뒤로[/url]";
				}

				// 시간이 소모되었으면 상황 업데이트
				if (result.TimeConsumed > 0)
				{
					_playerSystem.RequestTimeAdvance(result.TimeConsumed, actionType);
				}
			}
		}
	}

	/// <summary>
	/// 바닥 아이템 메뉴 표시: item_ground_menu:itemId:count
	/// </summary>
	private void HandleItemGroundMenuAction(string[] parts)
	{
		if (parts.Length < 3 || !int.TryParse(parts[1], out int itemId) || !int.TryParse(parts[2], out int count))
		{
			GD.PrintErr("[GameEngine] Invalid item_ground_menu format. Expected: item_ground_menu:itemId:count");
			return;
		}

		if (_describeSystem != null && _textUi != null)
		{
			var text = _describeSystem.GetGroundItemMenuText(itemId, count);
			_textUi.Text = text;
		}
	}

	/// <summary>
	/// 인벤토리 아이템 메뉴 표시: item_inv_menu:itemId:count
	/// </summary>
	private void HandleItemInvMenuAction(string[] parts)
	{
		if (parts.Length < 3 || !int.TryParse(parts[1], out int itemId) || !int.TryParse(parts[2], out int count))
		{
			GD.PrintErr("[GameEngine] Invalid item_inv_menu format. Expected: item_inv_menu:itemId:count");
			return;
		}

		if (_describeSystem != null && _textUi != null)
		{
			var text = _describeSystem.GetInventoryItemMenuText(itemId, count);
			_textUi.Text = text;
		}
	}

	/// <summary>
	/// 아이템 사용: item_use:itemId
	/// </summary>
	private void HandleItemUseAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[GameEngine] Invalid item_use format. Expected: item_use:itemId");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[GameEngine] 아이템 사용: itemId={itemId}");
#endif

		// TODO: 실제 사용 처리
		if (_textUi != null)
		{
			_textUi.Text = "[b]사용 기능은 아직 구현되지 않았습니다.[/b]\n\n[url=back_inventory]뒤로[/url]";
		}
	}

	/// <summary>
	/// 아이템 조합: item_combine:itemId
	/// </summary>
	private void HandleItemCombineAction(string[] parts)
	{
		if (parts.Length < 2 || !int.TryParse(parts[1], out int itemId))
		{
			GD.PrintErr("[GameEngine] Invalid item_combine format. Expected: item_combine:itemId");
			return;
		}

#if DEBUG_LOG
		GD.Print($"[GameEngine] 아이템 조합: itemId={itemId}");
#endif

		// TODO: 실제 조합 처리
		if (_textUi != null)
		{
			_textUi.Text = "[b]조합 기능은 아직 구현되지 않았습니다.[/b]\n\n[url=back_inventory]뒤로[/url]";
		}
	}
}
