using System.Collections.Generic;

namespace Morld;

/// <summary>
/// 핵심 기본 액션 프로바이더
/// 멍때리기 등 시스템에 의존하지 않는 기본 행동 제공
/// (인벤토리는 InventorySystem이 제공)
/// </summary>
public class CoreActionProvider : IActionProvider
{
	public string ProviderId => "core";

	public List<ProvidedAction> GetActionsFor(Unit unit)
	{
		var actions = new List<ProvidedAction>();

		// 멍때리기 (시간 선택 토글)
		actions.Add(new ProvidedAction
		{
			Type = "toggle",
			Name = "멍때리기",
			ToggleId = "idle",
			Options = new List<ActionOption>
			{
				new() { Label = "15분", Action = "idle:15" },
				new() { Label = "30분", Action = "idle:30" },
				new() { Label = "1시간", Action = "idle:60" },
				new() { Label = "4시간", Action = "idle:240" }
			}
		});

		return actions;
	}
}
