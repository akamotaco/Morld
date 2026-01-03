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

				// Lifetime 만료 체크 → pop (종료 조건보다 우선)
				if (currentLayer.RemainingLifetime == 0 && currentLayer.RemainingLifetime != -1)
				{
					// RemainingLifetime이 양수였다가 0이 된 경우에만 (초기값 0은 무제한)
					// 이 로직을 정확히 하려면 "활성화 여부" 플래그가 필요하지만,
					// 여기서는 EndConditionType이 "대기"인 경우만 Lifetime pop 대상으로 함
					if (currentLayer.EndConditionType == "대기")
					{
						var poppedLayer = unit.PopSchedule();
#if DEBUG_LOG
						GD.Print($"[BehaviorSystem] {unit.Name}: 스케줄 레이어 수명 만료 - {poppedLayer?.Name}");
						if (unit.CurrentScheduleLayer != null)
						{
							GD.Print($"  → 다음 레이어: {unit.CurrentScheduleLayer.Name}");
						}
#endif
						continue;
					}
				}

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
