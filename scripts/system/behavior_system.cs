using ECS;
using Godot;
using Morld;
using System;

namespace SE
{
	/// <summary>
	/// BehaviorSystem - 스케줄 종료 조건 체크 및 스택 관리
	/// </summary>
	public class BehaviorSystem : ECS.System
	{
		public BehaviorSystem()
		{
		}

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			var unitSystem = _hub.FindSystem("unitSystem") as UnitSystem;
			if (unitSystem == null) return;

			foreach (var unit in unitSystem.Units.Values)
			{
				// 오브젝트는 스케줄 없음
				if (unit.IsObject) continue;

				var currentLayer = unit.CurrentScheduleLayer;
				if (currentLayer == null) continue;

				// 종료 조건 체크 → pop
				if (currentLayer.IsComplete(unit, unitSystem))
				{
					var poppedLayer = unit.PopSchedule();
#if DEBUG_LOG
					GD.Print($"[BehaviorSystem] {unit.Name}: 스케줄 레이어 완료 - {poppedLayer?.Name}");
					if (unit.CurrentScheduleLayer != null)
					{
						GD.Print($"  → 다음 레이어: {unit.CurrentScheduleLayer.Name}");
					}
#endif
				}
			}
		}
	}
}
