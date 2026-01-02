#define DEBUG_LOG

using Godot;
using System;
using System.Diagnostics;
using SE;

public partial class GameEngine : Node
{
	private SE.World _world;
	private PlayerSystem _playerSystem;
	private DescribeSystem _describeSystem;
	private InventorySystem _inventorySystem;
	private TextUISystem _textUISystem;
	private RichTextLabel _textUi;
	private MetaActionHandler _actionHandler;
	private ScriptSystem _scriptSystem;

	public override void _Ready()
	{
		var text_ui_path = GetMeta("TextUI").As<string>();
		this._textUi = GetNode<RichTextLabel>(text_ui_path);
		if (this._textUi == null)
		{
			GD.PrintErr($"TextUi 메타가 null이거나 유효하지 않습니다.({GetMeta("TextUI")})");
			throw new InvalidOperationException("TextUi 메타가 null이거나 유효하지 않습니다.");
		}

		// BBCode 활성화 및 시그널 연결
		this._textUi.BbcodeEnabled = true;
		this._textUi.MetaClicked += OnMetaClicked;
		this._textUi.MetaHoverStarted += OnMetaHoverStarted;
		this._textUi.MetaHoverEnded += OnMetaHoverEnded;

		this._world = new SE.World(this);

		// Data Systems 초기화
		(this._world.AddSystem(new WorldSystem("aka"), "worldSystem") as WorldSystem)
			.GetTerrain().UpdateFromFile("res://scripts/morld/json_data/location_data.json");
		(this._world.FindSystem("worldSystem") as WorldSystem)
			.GetTime().UpdateFromFile("res://scripts/morld/json_data/time_data.json");

		(this._world.AddSystem(new UnitSystem(), "unitSystem") as UnitSystem)
			.UpdateFromFile("res://scripts/morld/json_data/unit_data.json");

		(this._world.AddSystem(new ItemSystem(), "itemSystem") as ItemSystem)
			.UpdateFromFile("res://scripts/morld/json_data/item_data.json");

		// InventorySystem 초기화 (IDataProvider + IActionProvider)
		_inventorySystem = this._world.AddSystem(new InventorySystem(), "inventorySystem") as InventorySystem;

		// InventorySystem 데이터 로드 시도 (없으면 unit_data.json에서 마이그레이션)
		var inventoryDataPath = "res://scripts/morld/json_data/";
		if (!_inventorySystem.LoadData(inventoryDataPath))
		{
			// inventory_data.json이 없으면 unit_data.json에서 마이그레이션
			var unitSystem = this._world.FindSystem("unitSystem") as UnitSystem;
			unitSystem?.MigrateInventoryData("res://scripts/morld/json_data/unit_data.json", _inventorySystem);
		}

		this._world.AddSystem(new ActionSystem(), "actionSystem");

		// Logic Systems
		this._world.AddSystem(new MovementSystem(), "movementSystem");
		this._world.AddSystem(new BehaviorSystem(), "behaviorSystem");
		_playerSystem = this._world.AddSystem(new PlayerSystem(), "playerSystem") as PlayerSystem;
		_describeSystem = this._world.AddSystem(new DescribeSystem(), "describeSystem") as DescribeSystem;

		// 액션 메시지 템플릿 로드
		_describeSystem?.LoadActionMessages("res://scripts/morld/json_data/action_messages.json");

		// InventorySystem을 ActionProvider로 등록
		_inventorySystem?.RegisterToDescribeSystem();

		// 확장 시스템 등록 예시: SingASongSystem
		// 이 시스템을 등록하면 '노래 부르기' 행동이 추가됨
		// 시스템을 제거하면 해당 행동도 사라짐
		var singSystem = this._world.AddSystem(new SingASongSystem(), "singASongSystem") as SingASongSystem;
		singSystem?.RegisterToDescribeSystem();

		// ScriptSystem 초기화 (TextUISystem보다 먼저)
		_scriptSystem = this._world.AddSystem(new ScriptSystem(), "scriptSystem") as ScriptSystem;
		var unitSys = this._world.FindSystem("unitSystem") as UnitSystem;
		_scriptSystem?.SetSystemReferences(_inventorySystem, _playerSystem, unitSys);
		_scriptSystem?.TestHelloWorld();
		_scriptSystem?.RegisterTestFunctions();
		_scriptSystem?.LoadMonologueScripts();

		// TextUISystem 초기화
		_textUISystem = new TextUISystem(_textUi, _describeSystem);
		this._world.AddSystem(_textUISystem, "textUISystem");

		// TextUISystem에 시스템 참조 설정 (ScriptSystem 포함)
		_textUISystem.SetSystemReferences(_playerSystem, _inventorySystem, _scriptSystem);

		// 초기 상황 표시
		_textUISystem.ShowSituation();

		// MetaActionHandler 초기화
		_actionHandler = new MetaActionHandler(_world, _playerSystem, _textUISystem);
		_actionHandler.OnUpdateSituation += UpdateSituationText;

		// 게임 시작 이벤트 트리거
		TriggerEvent("ready");

#if DEBUG_LOG
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTerrain().DebugPrint();
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTime().DebugPrint();
		(this._world.FindSystem("unitSystem") as UnitSystem).DebugPrint();
		_inventorySystem?.DebugPrint();

		Debug.Print($"System Count : {this._world.GetAllSystem().Count}");
		GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		GD.Print("[GameEngine] 입력 테스트 모드");
		GD.Print("  마우스 왼쪽 클릭: 4시간 (240분) 진행");
		GD.Print("  마우스 오른쪽 클릭: 15분 진행");
		GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
	}

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
		if (_playerSystem == null || _textUISystem == null)
			return;

		_textUISystem.ShowSituation();
	}

	/// <summary>
	/// 이벤트 트리거 및 결과 처리
	/// </summary>
	private void TriggerEvent(string eventName)
	{
		if (_scriptSystem == null) return;

		var result = _scriptSystem.TriggerEvent(eventName);
		if (result == null) return;

		// 이벤트 결과에 따른 처리
		switch (result.Type)
		{
			case "monologue":
				if (result is SE.MonologueEventResult monoResult)
				{
					_textUISystem?.ShowMonologue(monoResult.Pages, monoResult.TimeConsumed);
#if DEBUG_LOG
					GD.Print($"[GameEngine] 이벤트 '{eventName}' → 모놀로그 ({monoResult.Pages.Count} pages)");
#endif
				}
				break;

			default:
				GD.PrintErr($"[GameEngine] 알 수 없는 이벤트 결과 타입: {result.Type}");
				break;
		}
	}

	/// <summary>
	/// BBCode 링크 클릭 핸들러
	/// </summary>
	private void OnMetaClicked(Variant meta)
	{
		_actionHandler?.HandleAction(meta.AsString());
	}

	/// <summary>
	/// BBCode 링크 hover 시작 핸들러
	/// </summary>
	private void OnMetaHoverStarted(Variant meta)
	{
		_textUISystem?.SetHoveredMeta(meta.AsString());
	}

	/// <summary>
	/// BBCode 링크 hover 종료 핸들러
	/// </summary>
	private void OnMetaHoverEnded(Variant meta)
	{
		_textUISystem?.SetHoveredMeta(null);
	}
}
