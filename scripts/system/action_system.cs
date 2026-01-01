using ECS;
using Godot;
using Morld;
using System.Collections.Generic;
using System.Linq;

namespace SE
{
	/// <summary>
	/// 통합 액션 실행 시스템
	/// </summary>
	public class ActionSystem : ECS.System
	{
		public ActionSystem()
		{
		}

		/// <summary>
		/// 유닛 대상 액션 실행
		/// </summary>
		/// <param name="user">액션 수행자</param>
		/// <param name="action">액션 ID</param>
		/// <param name="targets">대상 유닛들</param>
		public ActionResult ApplyAction(Unit user, string action, List<Unit> targets)
		{
			return action switch
			{
				// Self 액션 (targets 무시)
				"rest" => ExecuteRest(user),
				"sleep" => ExecuteSleep(user),
				"wait" => ExecuteWait(user),

				// 단일 대상 액션
				"talk" => ExecuteTalk(user, targets.FirstOrDefault()),
				"trade" => ExecuteTrade(user, targets.FirstOrDefault()),
				"open" => ExecuteOpen(user, targets.FirstOrDefault()),
				"examine" => ExecuteExamine(user, targets.FirstOrDefault()),

				// 복수 대상 액션
				// "share_meal" => ExecuteShareMeal(user, targets),

				_ => ActionResult.Fail($"Unknown action: {action}")
			};
		}

		/// <summary>
		/// 아이템 대상 액션 실행
		/// </summary>
		/// <param name="user">액션 수행자</param>
		/// <param name="action">액션 ID</param>
		/// <param name="item">대상 아이템</param>
		/// <param name="targets">추가 대상 유닛들</param>
		public ActionResult ApplyItemAction(Unit user, string action, Item item, List<Unit>? targets = null)
		{
			return action switch
			{
				"pickup" => ExecutePickup(user, item),
				"drop" => ExecuteDrop(user, item),
				"use" => ExecuteUse(user, item),
				"combine" => ExecuteCombine(user, item),
				"give" => ExecuteGive(user, item, targets?.FirstOrDefault()),

				_ => ActionResult.Fail($"Unknown item action: {action}")
			};
		}

		#region Self Actions

		private ActionResult ExecuteRest(Unit user)
		{
			// TODO: 피로도 시스템 구현 시 효과 적용
			return ActionResult.Ok($"{user.Name}이(가) 휴식을 취한다.", timeConsumed: 60);
		}

		private ActionResult ExecuteSleep(Unit user)
		{
			// TODO: 피로도/체력 시스템 구현 시 효과 적용
			return ActionResult.Ok($"{user.Name}이(가) 잠을 잔다.", timeConsumed: 480);
		}

		private ActionResult ExecuteWait(Unit user)
		{
			return ActionResult.Ok($"{user.Name}이(가) 대기한다.", timeConsumed: 15);
		}

		#endregion

		#region Unit Target Actions

		private ActionResult ExecuteTalk(Unit user, Unit? target)
		{
			if (target == null)
				return ActionResult.Fail("대화 대상이 없습니다.");

			// TODO: 대화 시스템 구현
			return ActionResult.Fail($"대화 시스템은 아직 구현되지 않았습니다. ({target.Name})");
		}

		private ActionResult ExecuteTrade(Unit user, Unit? target)
		{
			if (target == null)
				return ActionResult.Fail("거래 대상이 없습니다.");

			// TODO: 거래 시스템 구현
			return ActionResult.Fail($"거래 시스템은 아직 구현되지 않았습니다. ({target.Name})");
		}

		private ActionResult ExecuteOpen(Unit user, Unit? target)
		{
			if (target == null)
				return ActionResult.Fail("열 대상이 없습니다.");

			if (!target.IsObject)
				return ActionResult.Fail($"{target.Name}은(는) 열 수 없습니다.");

			// TODO: 열기 시스템 구현 (잠금 체크 등)
			return ActionResult.Ok($"{target.Name}을(를) 열었다.");
		}

		private ActionResult ExecuteExamine(Unit user, Unit? target)
		{
			if (target == null)
				return ActionResult.Fail("살펴볼 대상이 없습니다.");

			// TODO: 자세히 보기 시스템 구현
			return ActionResult.Ok($"{target.Name}을(를) 자세히 살펴보았다.");
		}

		#endregion

		#region Item Actions

		private ActionResult ExecutePickup(Unit user, Item item)
		{
			// 실제 pickup 로직은 PlayerSystem에서 처리
			// 여기서는 결과만 반환
			return ActionResult.Ok($"{item.Name}을(를) 주웠다.");
		}

		private ActionResult ExecuteDrop(Unit user, Item item)
		{
			// 실제 drop 로직은 PlayerSystem에서 처리
			return ActionResult.Ok($"{item.Name}을(를) 버렸다.");
		}

		private ActionResult ExecuteUse(Unit user, Item item)
		{
			// TODO: 아이템 사용 효과 구현
			return ActionResult.Fail($"사용 기능은 아직 구현되지 않았습니다. ({item.Name})");
		}

		private ActionResult ExecuteCombine(Unit user, Item item)
		{
			// TODO: 조합 시스템 구현
			return ActionResult.Fail($"조합 기능은 아직 구현되지 않았습니다. ({item.Name})");
		}

		private ActionResult ExecuteGive(Unit user, Item item, Unit? target)
		{
			if (target == null)
				return ActionResult.Fail("줄 대상이 없습니다.");

			// TODO: 아이템 주기 구현
			return ActionResult.Fail($"아이템 주기 기능은 아직 구현되지 않았습니다.");
		}

		#endregion

		/// <summary>
		/// 디버그용 출력
		/// </summary>
		public void DebugPrint()
		{
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print("  ActionSystem 로드됨");
			GD.Print("  지원 액션: rest, sleep, wait, talk, trade, open, examine");
			GD.Print("  지원 아이템 액션: pickup, drop, use, combine, give");
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}
	}
}
