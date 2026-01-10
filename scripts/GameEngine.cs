#define DEBUG_LOG

using Godot;
using System;
using System.Diagnostics;
using SE;

public partial class GameEngine : Node
{
	private SE.World _world;
	private RichTextLabel _textUi;
	private MetaActionHandler _actionHandler;

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

		// 4. 이벤트 콜백 및 핸들러 등록 (데이터 로드 전에 준비)
		RegisterEventHandlers();

		// 5. 데이터 로드 (Python + morld API 등록, 챕터 로드)
		LoadDataFromPython();

		// 6. 게임 시작
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
		(this._world.AddSystem(new ScriptSystem(), "scriptSystem") as ScriptSystem).SetScenarioPath(_scenarioPath);
		// Data Systems
		this._world.AddSystem(new WorldSystem("aka"), "worldSystem");
		this._world.AddSystem(new UnitSystem(), "unitSystem");
		this._world.AddSystem(new ItemSystem(), "itemSystem");
		this._world.AddSystem(new InventorySystem(), "inventorySystem");

		// Logic Systems (실행 순서: Think → JobBehavior → Event)
		this._world.AddSystem(new ActionSystem(), "actionSystem");

		// ThinkSystem (JobBehaviorSystem 전에 실행: JobList 채우기)
		this._world.AddSystem(new ThinkSystem(), "thinkSystem");

		// EventPredictionSystem (ThinkSystem 후, EventSystem 전: 이벤트 예측 및 시간 조정)
		this._world.AddSystem(new EventPredictionSystem(), "eventPredictionSystem");

		// EventSystem (EventPredictionSystem 후, JobBehaviorSystem 전: 이벤트 감지 및 처리)
		this._world.AddSystem(new EventSystem(), "eventSystem");

		this._world.AddSystem(new JobBehaviorSystem(), "jobBehaviorSystem");
		this._world.AddSystem(new PlayerSystem(), "playerSystem");
		this._world.AddSystem(new DescribeSystem(), "describeSystem");

		// UI System
		this._world.AddSystem(new TextUISystem(_textUi, this._world.GetSystem("describeSystem") as DescribeSystem), "textUISystem");

	}

	/// <summary>
	/// Python에서 데이터 로드 (morld API 사용)
	/// </summary>
	private void LoadDataFromPython()
	{
		GD.Print("[GameEngine] Data source: Python");
		GD.Print("[GameEngine] Loading data from Python via morld API...");

		var _scriptSystem = this._world.GetSystem("scriptSystem") as ScriptSystem;

		// morld API 등록
		_scriptSystem.RegisterDataManipulationAPI();
		_scriptSystem.RegisterNpcJobAPI();

		// Python의 initialize_scenario() 호출 - morld API로 데이터 등록
		// 챕터 로드 시 reinitialize_locations()도 호출됨
		_scriptSystem.CallInitializeScenario();

		// Python 패키지의 나머지 모듈 로드 (이벤트 핸들러 등)
		_scriptSystem.LoadScenarioPackage();

		GD.Print("[GameEngine] Python data loaded.");
	}

	/// <summary>
	/// 이벤트 핸들러 및 콜백 등록
	/// </summary>
	private void RegisterEventHandlers()
	{
		var _inventorySystem = this._world.GetSystem("inventorySystem") as InventorySystem;
		var _textUISystem = this._world.GetSystem("textUISystem") as TextUISystem;
		var _playerSystem = this._world.GetSystem("playerSystem") as PlayerSystem;
		var itemSystem = this._world.GetSystem("itemSystem") as ItemSystem;
		var _eventSystem = this._world.GetSystem("eventSystem") as EventSystem;

		// InventorySystem 이벤트 콜백 (행동 로그 자동 생성)
		// 오브젝트(IsObject=true)의 인벤토리 변경은 로그에서 제외
		var unitSystem = this._world.GetSystem("unitSystem") as UnitSystem;
		_inventorySystem.OnInventoryChanged += (evt) =>
		{
			// 캐릭터(IsObject=false)의 인벤토리 변경만 로그 출력
			// ItemAdded: ToOwner가 캐릭터인지 확인
			// ItemRemoved: FromOwner가 캐릭터인지 확인
			string? ownerKey = evt.Type switch
			{
				InventoryEventType.ItemAdded => evt.ToOwner,
				InventoryEventType.ItemRemoved => evt.FromOwner,
				_ => evt.ToOwner ?? evt.FromOwner
			};

			if (string.IsNullOrEmpty(ownerKey) || !int.TryParse(ownerKey, out int unitId))
				return;

			var unit = unitSystem?.FindUnit(unitId);
			if (unit == null || unit.IsObject)
				return; // 캐릭터가 아니면 로그 생략

			var itemName = itemSystem?.FindItem(evt.ItemId)?.Name ?? "아이템";
			var countText = evt.Count > 1 ? $" x{evt.Count}" : "";

			string? message = evt.Type switch
			{
				InventoryEventType.ItemAdded => $"{itemName}{countText}을(를) 획득했습니다",
				InventoryEventType.ItemRemoved => $"{itemName}{countText}을(를) 잃었습니다",
				InventoryEventType.ItemEquipped => $"{itemName}을(를) 장착했습니다",
				InventoryEventType.ItemUnequipped => $"{itemName}을(를) 장착 해제했습니다",
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

		// EventSystem에 MetaActionHandler 참조 설정 (Generator 처리용)
		_eventSystem?.SetMetaActionHandler(_actionHandler);
	}

	/// <summary>
	/// 게임 시작
	/// </summary>
	private void StartGame()
	{
		var _eventSystem = this._world.GetSystem("eventSystem") as EventSystem;
		var _textUISystem = this._world.GetSystem("textUISystem") as TextUISystem;

		// 게임 시작 이벤트 등록
		_eventSystem.Enqueue(Morld.GameEvent.GameStart());

		// 게임 시작 이벤트 처리 후 초기 상황 표시
		var eventHandled = _eventSystem.FlushEvents();
		if (!eventHandled)
		{
			_textUISystem.ShowSituation();
		}
	}

#if DEBUG_LOG
	/// <summary>
	/// 디버그 정보 출력
	/// </summary>
	private void DebugPrintGameState()
	{
		(this._world.GetSystem("worldSystem") as WorldSystem).GetTerrain().DebugPrint();
		(this._world.GetSystem("worldSystem") as WorldSystem).GetTime().DebugPrint();
		(this._world.GetSystem("unitSystem") as UnitSystem).DebugPrint();
		var _inventorySystem = this._world.GetSystem("inventorySystem") as InventorySystem;

		_inventorySystem.DebugPrint();

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
		var _playerSystem = this._world.GetSystem("playerSystem") as PlayerSystem;
		var _eventSystem = this._world.GetSystem("eventSystem") as EventSystem;
		var _textUISystem = this._world.GetSystem("textUISystem") as TextUISystem;

		// 대기 중인 시간이 있을 때만 Step 실행
		if (_playerSystem != null && _playerSystem.HasPendingTime)
		{
			int delta_int = (int)(delta * 1000);
			this._world.Step(delta_int);

			// 시간 진행 완료 후 이벤트 감지 및 상황 업데이트
			if (!_playerSystem.HasPendingTime)
			{
				// 1. 만남 감지 → 이벤트 처리 (ApplyNpcJobs로 이동 상태 변경)
				//    DetectMeetings가 먼저여야 ApplyNpcJobs가 DetectLocationChanges 전에 실행됨
				_eventSystem.DetectMeetings();
				var eventHandled = _eventSystem.FlushEvents();

				// 2. 위치 변경 감지 (ApplyNpcJobs 후이므로 오버라이드된 상태 반영)
				_eventSystem?.DetectLocationChanges();

				// 3. 위치 변경으로 인한 추가 이벤트 처리
				var newEventHandled = _eventSystem.FlushEvents();

				// 4. ExcessTime 계산 (이벤트 처리에서 누적된 다이얼로그 시간 기준)
				_eventSystem.FinalizeDialogTime();

				// 5. 모놀로그가 없으면 상황 업데이트
				if (!eventHandled && !newEventHandled)
				{
					UpdateSituationText();
				}
			}
		}

		// 프레임 끝에서 한 번만 UI 렌더링 (lazy update 플러시)
		_textUISystem.FlushDisplay();
	}

	/// <summary>
	/// 현재 상황 설명을 TextUI에 표시
	/// </summary>
	private void UpdateSituationText()
	{
		var _textUISystem = this._world.GetSystem("textUISystem") as TextUISystem;
		_textUISystem.ShowSituation();
	}

	/// <summary>
	/// BBCode 링크 클릭 핸들러
	/// </summary>
	private void OnMetaClicked(Variant meta)
	{
		_actionHandler.HandleAction(meta.AsString());
	}

	/// <summary>
	/// BBCode 링크 hover 시작 핸들러
	/// </summary>
	private void OnMetaHoverStarted(Variant meta)
	{
		var _textUISystem = this._world.GetSystem("textUISystem") as TextUISystem;
		_textUISystem.SetHoveredMeta(meta.AsString());
	}

	/// <summary>
	/// BBCode 링크 hover 종료 핸들러
	/// </summary>
	private void OnMetaHoverEnded(Variant meta)
	{
		var _textUISystem = this._world.GetSystem("textUISystem") as TextUISystem;
		_textUISystem.SetHoveredMeta(null);
	}
}
