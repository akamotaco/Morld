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
	public override void _Ready()
	{
		this._world = new SE.World(this);

		(this._world.AddSystem(new WorldSystem("aka"), "worldSystem") as WorldSystem).GetTerrain().UpdateFromFile("res://scripts/morld/json_data/location_data.json");
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTime().UpdateFromFile("res://scripts/morld/json_data/time_data.json");

		(this._world.AddSystem(new CharacterSystem(), "characterSystem") as CharacterSystem).UpdateFromFile("res://scripts/morld/json_data/character_data.json");

		this._world.AddSystem(new PlanningSystem(), "planningSystem");
		this._world.AddSystem(new MovementSystem(), "movementSystem");

#if DEBUG_LOG
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTerrain().DebugPrint();
		(this._world.FindSystem("worldSystem") as WorldSystem).GetTime().DebugPrint();
		(this._world.FindSystem("characterSystem") as CharacterSystem).DebugPrint();

		Debug.Print($"System Count : {this._world.GetAllSystem().Count}");
#endif
	}

	// Called every frame. 'delta' is the elapsed time since the previous frame.
	public override void _Process(double delta)
	{
		int delta_int = (int)(delta * 1000);
		this._world.Step(delta_int);
	}
}
