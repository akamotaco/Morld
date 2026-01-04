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
	private EventSystem _eventSystem;

	// 시나리오 경로 (res:// 기준)11111
	// private string _scenarioPath = "res://scenarios/scenario01/";
	private string _scenarioPath = "res://scenarios/scenario02/";
	private string DataPath => _scenarioPath + "data/";

	public override void _Ready()
	{
		// 1. UI 초기화
		InitializeUI();

		// 2. World 초기화
		this._world = new SE.World(this);

		// 3. 모든 시스템 등록
		RegisterAllSystems();

		// 4. 데이터 로드 (Python)
		LoadDataFromPython();

		// 5. 시스템 간 참조 설정 및 후처리
		SetupSystemReferences();

		// 6. 이벤트 콜백 및 핸들러 등록
		RegisterEventHandlers();

		// 7. 게임 시작
		StartGame();

#if DEBUG_LOG
		DebugPrintGameState();
#endif
	}

	/// <summary>
	/// UI 초기화
	/// </summary>
	private void InitializeUI()
	{
		var text_ui_path = GetMeta("TextUI").As<string>();
		this._textUi = GetNode<RichTextLabel>(text_ui_path);
		if (this._textUi == null)
		{
			GD.PrintErr($"TextUi 메타가 null이거나 유효하지 않습니다.({GetMeta("TextUI")})");
			throw new InvalidOperationException("TextUi 메타가 null이거나 유효하지 않습니다.");
		}

		this._textUi.BbcodeEnabled = true;
		this._textUi.MetaClicked += OnMetaClicked;
		this._textUi.MetaHoverStarted += OnMetaHoverStarted;
		this._textUi.MetaHoverEnded += OnMetaHoverEnded;
	}

	/// <summary>
	/// 모든 시스템 등록 (Data Systems + Logic Systems)
	/// </summary>
	private void RegisterAllSystems()
	{
		// Script System (시나리오 경로 설정 필요)
		_scriptSystem = this._world.AddSystem(new ScriptSystem(), "scriptSystem") as ScriptSystem;
		_scriptSystem?.SetScenarioPath(_scenarioPath);

		// Data Systems
		this._world.AddSystem(new WorldSystem("aka"), "worldSystem");
		this._world.AddSystem(new UnitSystem(), "unitSystem");
		this._world.AddSystem(new ItemSystem(), "itemSystem");
		_inventorySystem = this._world.AddSystem(new InventorySystem(), "inventorySystem") as InventorySystem;

		// Logic Systems (실행 순서: Movement → Event → Behavior)
		this._world.AddSystem(new ActionSystem(), "actionSystem");
		this._world.AddSystem(new MovementSystem(), "movementSystem");
		// EventSystem은 아래에서 별도 등록 (UI 시스템 이후)
		this._world.AddSystem(new BehaviorSystem(), "behaviorSystem");
		_playerSystem = this._world.AddSystem(new PlayerSystem(), "playerSystem") as PlayerSystem;
		_describeSystem = this._world.AddSystem(new DescribeSystem(), "describeSystem") as DescribeSystem;

		// UI System
		_textUISystem = new TextUISystem(_textUi, _describeSystem);
		this._world.AddSystem(_textUISystem, "textUISystem");

		// Event System
		_eventSystem = this._world.AddSystem(new EventSystem(), "eventSystem") as EventSystem;

		// 확장 시스템 (ActionProvider)
		var singSystem = this._world.AddSystem(new SingASongSystem(), "singASongSystem") as SingASongSystem;
		singSystem?.RegisterToDescribeSystem();
		_inventorySystem?.RegisterToDescribeSystem();

		// ScriptSystem에 morld 모듈 등록 (Python에서 import morld 가능하게)
		var unitSystem = this._world.FindSystem("unitSystem") as UnitSystem;
		_scriptSystem?.SetSystemReferences(_inventorySystem, _playerSystem, unitSystem, _textUISystem);
	}

	/// <summary>
	/// Python에서 데이터 로드 (morld API 사용)
	/// </summary>
	private void LoadDataFromPython()
	{
		GD.Print("[GameEngine] Data source: Python");
		GD.Print("[GameEngine] Loading data from Python via morld API...");

		var worldSystem = this._world.FindSystem("worldSystem") as WorldSystem;
		var unitSystem = this._world.FindSystem("unitSystem") as UnitSystem;
		var itemSystem = this._world.FindSystem("itemSystem") as ItemSystem;

		// Data System 참조 설정 (morld.add_unit 등 데이터 API 등록)
		_scriptSystem?.SetDataSystemReferences(worldSystem, unitSystem, itemSystem, _inventorySystem);

		// Python의 initialize_scenario() 호출 - morld API로 데이터 등록
		_scriptSystem?.CallInitializeScenario();

		// Python 패키지의 나머지 모듈 로드 (이벤트 핸들러 등)
		_scriptSystem?.LoadScenarioPackage();

		GD.Print("[GameEngine] Python data loaded.");
	}

	/// <summary>
	/// 시스템 간 참조 설정
	/// </summary>
	private void SetupSystemReferences()
	{
		var unitSystem = this._world.FindSystem("unitSystem") as UnitSystem;

		// ScriptSystem 테스트 함수 등록
		_scriptSystem?.TestHelloWorld();
		_scriptSystem?.RegisterTestFunctions();

		// TextUISystem 설정
		_textUISystem?.SetSystemReferences(_playerSystem, _inventorySystem, _scriptSystem);

		// EventSystem 설정
		_eventSystem?.SetSystemReferences(_scriptSystem, _textUISystem, unitSystem, _playerSystem);
		_eventSystem?.InitializeLocations();
	}

	/// <summary>
	/// 이벤트 핸들러 및 콜백 등록
	/// </summary>
	private void RegisterEventHandlers()
	{
		var itemSystem = this._world.FindSystem("itemSystem") as ItemSystem;

		// InventorySystem 이벤트 콜백 (행동 로그 자동 생성)
		_inventorySystem.OnInventoryChanged += (evt) =>
		{
			var itemName = itemSystem?.GetItem(evt.ItemId)?.Name ?? "아이템";
			var countText = evt.Count > 1 ? $" x{evt.Count}" : "";

			string? message = evt.Type switch
			{
				InventoryEventType.ItemAdded => $"{itemName}{countText}을(를) 획득했습니다",
				InventoryEventType.ItemRemoved => $"{itemName}{countText}을(를) 잃었습니다",
				InventoryEventType.ItemTransferred => $"{itemName}{countText}을(를) 옮겼습니다",
				InventoryEventType.ItemEquipped => $"{itemName}을(를) 장착했습니다",
				InventoryEventType.ItemUnequipped => $"{itemName}을(를) 장착 해제했습니다",
				InventoryEventType.ItemLost => $"{itemName}{countText}을(를) 사용했습니다",
				_ => null
			};

			if (message != null)
			{
				_textUISystem?.AddActionLog(message);
			}
		};

		// MetaActionHandler 초기화
		_actionHandler = new MetaActionHandler(_world, _playerSystem, _textUISystem);
		_actionHandler.OnUpdateSituation += UpdateSituationText;
	}

	/// <summary>
	/// 게임 시작
	/// </summary>
	private void StartGame()
	{
		// 게임 시작 이벤트 등록
		_eventSystem?.Enqueue(Morld.GameEvent.GameStart());

		// 게임 시작 이벤트 처리 후 초기 상황 표시
		var eventHandled = _eventSystem?.FlushEvents() ?? false;
		if (!eventHandled)
		{
			_textUISystem?.ShowSituation();
		}
	}

#if DEBUG_LOG
	/// <summary>
	/// 디버그 정보 출력
	/// </summary>
	private void DebugPrintGameState()
	{
		(this._world.FindSystem("worldSystem") as WorldSystem)?.GetTerrain().DebugPrint();
		(this._world.FindSystem("worldSystem") as WorldSystem)?.GetTime().DebugPrint();
		(this._world.FindSystem("unitSystem") as UnitSystem)?.DebugPrint();
		_inventorySystem?.DebugPrint();

		Debug.Print($"System Count : {this._world.GetAllSystem().Count}");
		GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		GD.Print("[GameEngine] 입력 테스트 모드");
		GD.Print("  마우스 왼쪽 클릭: 4시간 (240분) 진행");
		GD.Print("  마우스 오른쪽 클릭: 15분 진행");
		GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
	}
#endif

	public override void _Process(double delta)
	{
		// 대기 중인 시간이 있을 때만 Step 실행
		if (_playerSystem != null && _playerSystem.HasPendingTime)
		{
			int delta_int = (int)(delta * 1000);
			this._world.Step(delta_int);

			// 시간 진행 완료 후 이벤트 감지 및 상황 업데이트
			if (!_playerSystem.HasPendingTime)
			{
				// 위치 변경 및 만남 이벤트 감지
				_eventSystem?.DetectLocationChanges();
				_eventSystem?.DetectMeetings();

				// 이벤트 처리 (모놀로그 표시 시 상황 업데이트 스킵)
				var eventHandled = _eventSystem?.FlushEvents() ?? false;
				if (!eventHandled)
				{
					UpdateSituationText();
				}
			}
		}

		// 프레임 끝에서 한 번만 UI 렌더링 (lazy update 플러시)
		_textUISystem?.FlushDisplay();
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
