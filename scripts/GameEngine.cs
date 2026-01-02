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
	private TextUISystem _textUISystem;
	private RichTextLabel _textUi;
	private MetaActionHandler _actionHandler;

	public override void _Ready()
	{
		var text_ui_path = GetMeta("TextUI").As<string>();
		this._textUi = GetNode<RichTextLabel>(text_ui_path);
		if (this._textUi == null)
		{
			GD.PrintErr($"TextUi 메타가 null이거나 유효하지 않습니다.({GetMeta("TextUI")})");
			throw new InvalidOperationException("TextUi 메타가 null이거나 유효하지 않습니다.");
		}

		// BBCode 활성화 및 meta_clicked 시그널 연결
		this._textUi.BbcodeEnabled = true;
		this._textUi.MetaClicked += OnMetaClicked;

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

		this._world.AddSystem(new ActionSystem(), "actionSystem");

		// Logic Systems
		this._world.AddSystem(new MovementSystem(), "movementSystem");
		this._world.AddSystem(new BehaviorSystem(), "behaviorSystem");
		_playerSystem = this._world.AddSystem(new PlayerSystem(), "playerSystem") as PlayerSystem;
		_describeSystem = this._world.AddSystem(new DescribeSystem(), "describeSystem") as DescribeSystem;

		// TextUISystem 초기화
		_textUISystem = new TextUISystem(_textUi, _describeSystem);
		this._world.AddSystem(_textUISystem, "textUISystem");

		// text_ui_data.json 로드 (게임 시작 시 빈 스택)
		_textUISystem.LoadFromFile("res://scripts/morld/json_data/text_ui_data.json");

		// 스택이 비어있으면 초기 상황 표시
		if (_textUISystem.IsEmpty)
		{
			var worldSystem = _world.FindSystem("worldSystem") as WorldSystem;
			var lookResult = _playerSystem.Look();
			var time = worldSystem?.GetTime();
			_textUISystem.ShowSituation(lookResult, time);
		}

		// MetaActionHandler 초기화
		_actionHandler = new MetaActionHandler(_world, _playerSystem, _textUISystem);
		_actionHandler.OnUpdateSituation += UpdateSituationText;

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

		var worldSystem = _world.FindSystem("worldSystem") as WorldSystem;
		var lookResult = _playerSystem.Look();
		var time = worldSystem?.GetTime();

		_textUISystem.ShowSituation(lookResult, time);
	}

	/// <summary>
	/// BBCode 링크 클릭 핸들러
	/// </summary>
	private void OnMetaClicked(Variant meta)
	{
		_actionHandler?.HandleAction(meta.AsString());
	}
}
