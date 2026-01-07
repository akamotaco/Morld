#define DEBUG_LOG

using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;

namespace SE
{
	/// <summary>
	/// 노래 부르기 시스템 (예시)
	/// IActionProvider를 구현하여 캐릭터에게 '노래 부르기' 행동 제공
	/// 이 시스템이 등록되면 행동 가능, 삭제되면 행동 불가
	/// </summary>
	public class SingASongSystem : ECS.System, IActionProvider
	{
		public string ProviderId => "singasong";

		public SingASongSystem()
		{
		}

		/// <summary>
		/// 유닛에게 제공할 액션 목록 반환
		/// </summary>
		public List<ProvidedAction> GetActionsFor(Unit unit)
		{
			var actions = new List<ProvidedAction>();

			// 예: 특정 조건 체크 (예: 유닛이 '노래' 태그를 가지고 있거나)
			// 여기서는 간단히 모든 캐릭터에게 제공
			if (!unit.IsObject)
			{
				actions.Add(new ProvidedAction
				{
					Type = "toggle",
					Name = "노래 부르기",
					ToggleId = "sing",
					Options = new List<ActionOption>
					{
						new() { Label = "혼자 흥얼거리기", Action = "sing:hum" },
						new() { Label = "크게 노래하기", Action = "sing:loud" },
						new() { Label = "세레나데", Action = "sing:serenade" }
					}
				});
			}

			return actions;
		}

		/// <summary>
		/// 시스템 시작 시 DescribeSystem에 프로바이더 등록
		/// </summary>
		public void RegisterToDescribeSystem()
		{
			var describeSystem = _hub.GetSystem("describeSystem") as DescribeSystem;
			describeSystem.ActionRegistry.Register(this);

#if DEBUG_LOG
			GD.Print("[SingASongSystem] 노래 부르기 시스템 활성화됨");
#endif
		}

		/// <summary>
		/// 시스템 종료 시 프로바이더 등록 해제
		/// </summary>
		public override void Destroy()
		{
			var describeSystem = _hub.GetSystem("describeSystem") as DescribeSystem;
			describeSystem.ActionRegistry.Unregister(this);

#if DEBUG_LOG
			GD.Print("[SingASongSystem] 노래 부르기 시스템 비활성화됨");
#endif

			base.Destroy();
		}

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
