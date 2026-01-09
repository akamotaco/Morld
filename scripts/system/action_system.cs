using ECS;
using Godot;
using Morld;
using System.Collections.Generic;
using System.Linq;

namespace SE
{
	/// <summary>
	/// 차량 액션 시스템
	///
	/// 일반 액션(rest, sleep, talk 등)은 Python Asset의 call: 패턴으로 처리됨
	/// 이 시스템은 차량 관련 액션만 처리 (C#에서 Terrain 데이터 접근 필요)
	/// </summary>
	public class ActionSystem : ECS.System
	{
		public ActionSystem()
		{
		}

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
			GD.Print("  ActionSystem 로드됨 (차량 전용)");
			GD.Print("  지원: CanDrive, GetDrivableDestinations, ApplyDriveAction");
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}
	}
}
