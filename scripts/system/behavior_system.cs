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
			var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
			if (characterSystem == null) return;

			foreach (var character in characterSystem.Characters.Values)
			{
				var currentLayer = character.CurrentScheduleLayer;
				if (currentLayer == null) continue;

				// 종료 조건 체크 → pop
				if (currentLayer.IsComplete(character, characterSystem))
				{
					var poppedLayer = character.PopSchedule();
#if DEBUG_LOG
					GD.Print($"[BehaviorSystem] {character.Name}: 스케줄 레이어 완료 - {poppedLayer?.Name}");
					if (character.CurrentScheduleLayer != null)
					{
						GD.Print($"  → 다음 레이어: {character.CurrentScheduleLayer.Name}");
					}
#endif
				}
			}
		}
	}
}
