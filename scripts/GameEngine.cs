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

	public override void _Ready()
	{
		this._world = new SE.World(this);

		(this._world.AddSystem(new WorldSystem("aka"), "worldSystem") as WorldSystem).GetTerrain().UpdateFromFile("res://scripts/morld/json_data/location_data.json");
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTime().UpdateFromFile("res://scripts/morld/json_data/time_data.json");

		(this._world.AddSystem(new CharacterSystem(), "characterSystem") as CharacterSystem).UpdateFromFile("res://scripts/morld/json_data/character_data.json");

		// Logic Systems - 실행 순서: MovementSystem → PlanningSystem → PlayerSystem
		this._world.AddSystem(new MovementSystem(), "movementSystem");
		this._world.AddSystem(new PlanningSystem(), "planningSystem");
		_playerSystem = this._world.AddSystem(new PlayerSystem(), "playerSystem") as PlayerSystem;

#if DEBUG_LOG
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTerrain().DebugPrint();
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTime().DebugPrint();
		(this._world.FindSystem("characterSystem") as CharacterSystem).DebugPrint();

		Debug.Print($"System Count : {this._world.GetAllSystem().Count}");
		GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		GD.Print("[GameEngine] 입력 테스트 모드");
		GD.Print("  마우스 왼쪽 클릭: 4시간 (240분) 진행");
		GD.Print("  마우스 오른쪽 클릭: 15분 진행");
		GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
	}

	public override void _Input(InputEvent @event)
	{
		if (@event is InputEventMouseButton mouseEvent && mouseEvent.Pressed)
		{
			if (mouseEvent.ButtonIndex == MouseButton.Left)
			{
				// 왼쪽 클릭: 4시간 진행
				_playerSystem?.RequestTimeAdvance(240, "수면 (4시간)");
			}
			else if (mouseEvent.ButtonIndex == MouseButton.Right)
			{
				// 오른쪽 클릭: 15분 진행
				_playerSystem?.RequestTimeAdvance(15, "휴식 (15분)");
			}
		}
	}

	// Called every frame. 'delta' is the elapsed time since the previous frame.
	public override void _Process(double delta)
	{
		// 대기 중인 시간이 있을 때만 Step 실행
		if (_playerSystem == null || !_playerSystem.HasPendingTime)
			return;

		int delta_int = (int)(delta * 1000);
		this._world.Step(delta_int);
	}
}
