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
				"give" => ExecuteGive(user, item, targets.FirstOrDefault()),

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

		#region Vehicle Actions

		/// <summary>
		/// 유닛이 운전 가능한 상태인지 확인
		/// 운전석에 앉아있고 차량이 있어야 함
		/// </summary>
		public bool CanDrive(Unit unit)
		{
			// seated_on prop으로 앉아있는 오브젝트 확인
			var seatedOnProps = unit.TraversalContext.Props.GetByType("seated_on").ToList();
			if (seatedOnProps.Count == 0) return false;

			var seatedOnValue = seatedOnProps.First().Value;
			if (seatedOnValue <= 0) return false;

			// 앉아있는 오브젝트가 driver_seat인지 확인
			if (_hub.GetSystem("unitSystem") is not UnitSystem unitSystem) return false;

			var seat = unitSystem.FindUnit(seatedOnValue);
			if (seat == null) return false;

			// driver_seat prop 확인
			return seat.TraversalContext.HasProp("driver_seat");
		}

		/// <summary>
		/// 운전 가능한 목적지 목록 가져오기
		/// 차량 Location에서 RegionEdge로 연결된 외부 Location들을 반환
		/// </summary>
		public List<(int regionId, int locationId, string name, int travelTime)> GetDrivableDestinations(Unit unit)
		{
			var destinations = new List<(int, int, string, int)>();

			if (_hub.GetSystem("worldSystem") is not WorldSystem worldSystem) return destinations;

			var terrain = worldSystem.GetTerrain();
			var currentLoc = unit.CurrentLocation;

			// 현재 위치에서 RegionEdge를 통해 연결된 외부 Location 찾기
			// 차량은 별도 Region에 있고, RegionEdge로 외부와 연결됨
			foreach (var (edge, destination, travelTime) in terrain.GetRegionExits(currentLoc, unit.TraversalContext))
			{
				// 목적지 정보 가져오기
				var destRegion = terrain.GetRegion(destination.RegionId);
				if (destRegion == null) continue;

				var destLocation = destRegion.GetLocation(destination.LocalId);
				if (destLocation == null) continue;

				// 실내는 차량 이동 불가
				if (destLocation.IsIndoor) continue;

				var name = destLocation.Name ?? $"Location {destination.LocalId}";
				destinations.Add((destination.RegionId, destination.LocalId, name, (int)travelTime));
			}

			return destinations;
		}

		/// <summary>
		/// 운전 액션 적용 (이동 시작)
		/// </summary>
		public ActionResult ApplyDriveAction(Unit unit, int destRegionId, int destLocationId)
		{
			// 운전 가능한지 확인
			if (!CanDrive(unit))
				return ActionResult.Fail("운전석에 앉아있지 않습니다.");

			// 목적지가 유효한지 확인
			var destinations = GetDrivableDestinations(unit);
			var dest = destinations.Find(d => d.regionId == destRegionId && d.locationId == destLocationId);
			if (dest == default)
				return ActionResult.Fail("해당 목적지로 운전할 수 없습니다.");

			// 운전 실행
			return ExecuteDrive(unit, destRegionId, destLocationId, dest.travelTime);
		}

		/// <summary>
		/// 실제 운전 실행 (RegionEdge의 LocationA 변경)
		/// 차량 이동 = RegionEdge의 외부 연결 지점 변경
		/// </summary>
		private ActionResult ExecuteDrive(Unit driver, int destRegionId, int destLocationId, int travelTime)
		{
			if (_hub.GetSystem("worldSystem") is not WorldSystem worldSystem)
				return ActionResult.Fail("WorldSystem을 찾을 수 없습니다.");

			// 목적지 이름 가져오기
			var terrain = worldSystem.GetTerrain();
			var destRegion = terrain.GetRegion(destRegionId);
			var destLocation = destRegion.GetLocation(destLocationId);
			var destName = destLocation.Name ?? $"Location {destLocationId}";

			// 현재 위치 (차량 Location)
			var currentLoc = driver.CurrentLocation;

			// 현재 연결된 RegionEdge 찾기
			var regionEdges = terrain.GetRegionEdgesFrom(currentLoc).ToList();
			if (regionEdges.Count == 0)
				return ActionResult.Fail("차량이 연결된 경로를 찾을 수 없습니다.");

			// 첫 번째 RegionEdge의 외부 Location을 목적지로 변경
			var edge = regionEdges.First();

			// RegionEdge의 외부 쪽(LocationA 또는 LocationB) 변경
			// 차량 Region 쪽이 아닌 외부 Region 쪽을 변경
			if (edge.LocationA.RegionId == currentLoc.RegionId)
			{
				// LocationA가 차량 쪽 → LocationB를 변경
				edge.LocationB = new LocationRef(destRegionId, destLocationId);
			}
			else
			{
				// LocationB가 차량 쪽 → LocationA를 변경
				edge.LocationA = new LocationRef(destRegionId, destLocationId);
			}

			// 탑승자들은 차량 Location에 계속 머무름 (위치 변경 없음)
			// RegionEdge만 변경되므로 탑승자 처리 불필요

			return ActionResult.Ok($"{destName}(으)로 이동했다.", timeConsumed: travelTime);
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
