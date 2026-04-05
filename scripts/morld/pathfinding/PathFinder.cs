using System;
using System.Collections.Generic;
using System.Linq;
using SE;

namespace Morld;

/// <summary>
/// 경로 탐색 결과
/// </summary>
public class PathResult
{
	/// <summary>
	/// 경로를 찾았는지 여부
	/// </summary>
	public bool Found { get; init; }

	/// <summary>
	/// 경로 (Location 리스트)
	/// </summary>
	public List<Location> Path { get; init; } = new();

	/// <summary>
	/// 경로 그래프 거리 (Gate.Distance 합, Dijkstra 비용)
	/// 실제 이동 시간은 Terrain.CalculatePathTravelTime()으로 계산
	/// </summary>
	public float GraphDistance { get; init; }

	/// <summary>
	/// 탐색 중 방문한 노드 수
	/// </summary>
	public int VisitedNodes { get; init; }

	/// <summary>
	/// 경유한 Region ID 목록
	/// </summary>
	public List<int> RegionsTraversed { get; init; } = new();

	/// <summary>
	/// 사용한 RegionGate ID 목록
	/// </summary>
	public List<int> RegionGatesUsed { get; init; } = new();

	/// <summary>
	/// 빈 결과 (경로 없음)
	/// </summary>
	public static PathResult Empty => new() { Found = false };
}

/// <summary>
/// Region 내/간 경로 탐색기
/// </summary>
public class PathFinder
{
	private readonly Terrain _terrain;

	public PathFinder(Terrain terrain)
	{
		_terrain = terrain ?? throw new ArgumentNullException(nameof(terrain));
	}

	/// <summary>
	/// 경로 탐색 (같은 Region 또는 다른 Region)
	/// Unit + ItemSystem + InventorySystem 기반으로 GetActualProps()를 통해 조건 체크
	/// </summary>
	public PathResult FindPath(LocationRef start, LocationRef goal, Unit? unit = null, ItemSystem? itemSystem = null, InventorySystem? inventorySystem = null)
	{
		var startLocation = _terrain.GetLocation(start);
		var goalLocation = _terrain.GetLocation(goal);

		if (startLocation == null)
			throw new ArgumentException($"Start location {start} not found");
		if (goalLocation == null)
			throw new ArgumentException($"Goal location {goal} not found");

		// Unit이 있으면 아이템 효과가 반영된 ActualProps 사용
		TraversalContext? context = null;
		if (unit != null)
		{
			var inventory = inventorySystem?.GetUnitInventory(unit.Id);
			var equippedItems = inventorySystem?.GetUnitEquippedItems(unit.Id);
			context = unit.GetActualProps(itemSystem, inventory, equippedItems);
		}

		// 같은 Region 내 탐색
		if (start.RegionId == goal.RegionId)
		{
			return FindPathInRegion(startLocation, goalLocation, context);
		}

		// 다른 Region 간 탐색
		return FindPathAcrossRegions(startLocation, goalLocation, context);
	}

	/// <summary>
	/// 경로 탐색 (TraversalContext 직접 전달 - 하위 호환용)
	/// </summary>
	public PathResult FindPath(LocationRef start, LocationRef goal, TraversalContext? context)
	{
		var startLocation = _terrain.GetLocation(start);
		var goalLocation = _terrain.GetLocation(goal);

		if (startLocation == null)
			throw new ArgumentException($"Start location {start} not found");
		if (goalLocation == null)
			throw new ArgumentException($"Goal location {goal} not found");

		// 같은 Region 내 탐색
		if (start.RegionId == goal.RegionId)
		{
			return FindPathInRegion(startLocation, goalLocation, context);
		}

		// 다른 Region 간 탐색
		return FindPathAcrossRegions(startLocation, goalLocation, context);
	}

	/// <summary>
	/// 경로 탐색 (직접 Location 지정, Unit + ItemSystem + InventorySystem)
	/// </summary>
	public PathResult FindPath(
		int startRegionId, int startLocalId,
		int goalRegionId, int goalLocalId,
		Unit? unit = null, ItemSystem? itemSystem = null, InventorySystem? inventorySystem = null)
	{
		return FindPath(
			new LocationRef(startRegionId, startLocalId),
			new LocationRef(goalRegionId, goalLocalId),
			unit, itemSystem, inventorySystem);
	}

	/// <summary>
	/// 경로 탐색 (직접 Location 지정, TraversalContext - 하위 호환용)
	/// </summary>
	public PathResult FindPath(
		int startRegionId, int startLocalId,
		int goalRegionId, int goalLocalId,
		TraversalContext? context)
	{
		return FindPath(
			new LocationRef(startRegionId, startLocalId),
			new LocationRef(goalRegionId, goalLocalId),
			context);
	}

	/// <summary>
	/// 같은 Region 내 경로 탐색 (Dijkstra)
	/// </summary>
	private PathResult FindPathInRegion(Location start, Location goal, TraversalContext? context)
	{
		var region = _terrain.GetRegion(start.RegionId)!;

		if (start.Equals(goal))
		{
			return new PathResult
			{
				Found = true,
				Path = new List<Location> { start },
				GraphDistance = 0,
				VisitedNodes = 1,
				RegionsTraversed = new List<int> { start.RegionId }
			};
		}

		var openSet = new PriorityQueue<Location, float>();
		var cameFrom = new Dictionary<string, Location>();
		var distMap = new Dictionary<string, float>();
		var closedSet = new HashSet<string>();
		int visitedCount = 0;

		distMap[start.GlobalId] = 0;
		openSet.Enqueue(start, 0);

		while (openSet.Count > 0)
		{
			var current = openSet.Dequeue();
			visitedCount++;

			if (closedSet.Contains(current.GlobalId))
				continue;

			if (current.Equals(goal))
			{
				return new PathResult
				{
					Found = true,
					Path = ReconstructPath(cameFrom, current),
					GraphDistance = distMap[current.GlobalId],
					VisitedNodes = visitedCount,
					RegionsTraversed = new List<int> { start.RegionId }
				};
			}

			closedSet.Add(current.GlobalId);

			foreach ((Location neighbor, float gateDistance) in region.GetTraversableNeighbors(current, context))
			{
				if (closedSet.Contains(neighbor.GlobalId))
					continue;

				float tentativeDist = distMap[current.GlobalId] + gateDistance;

				if (!distMap.ContainsKey(neighbor.GlobalId) || tentativeDist < distMap[neighbor.GlobalId])
				{
					cameFrom[neighbor.GlobalId] = current;
					distMap[neighbor.GlobalId] = tentativeDist;
					openSet.Enqueue(neighbor, tentativeDist);
				}
			}
		}

		return new PathResult { Found = false, VisitedNodes = visitedCount };
	}

	/// <summary>
	/// 다른 Region 간 경로 탐색 (Dijkstra with Region transitions)
	/// </summary>
	private PathResult FindPathAcrossRegions(Location start, Location goal, TraversalContext? context)
	{
		// 전역 탐색: Location + RegionGate를 모두 탐색
		var openSet = new PriorityQueue<SearchNode, float>();
		var cameFrom = new Dictionary<string, (SearchNode node, int? regionGateId)>();
		var distMap = new Dictionary<string, float>();
		var closedSet = new HashSet<string>();
		int visitedCount = 0;

		var startNode = new SearchNode(start);
		distMap[startNode.Id] = 0;
		openSet.Enqueue(startNode, 0);

		while (openSet.Count > 0)
		{
			var current = openSet.Dequeue();
			visitedCount++;

			if (closedSet.Contains(current.Id))
				continue;

			// 목표 도달
			if (current.Location.Equals(goal))
			{
				return ReconstructCrossRegionPath(cameFrom, current, distMap[current.Id], visitedCount);
			}

			closedSet.Add(current.Id);

			var currentRegion = _terrain.GetRegion(current.Location.RegionId)!;

			// 1. 같은 Region 내 이동
			foreach ((Location neighbor, float gateDistance) in currentRegion.GetTraversableNeighbors(current.Location, context))
			{
				var neighborNode = new SearchNode(neighbor);
				if (closedSet.Contains(neighborNode.Id))
					continue;

				float tentativeDist = distMap[current.Id] + gateDistance;

				if (!distMap.ContainsKey(neighborNode.Id) || tentativeDist < distMap[neighborNode.Id])
				{
					cameFrom[neighborNode.Id] = (current, null);
					distMap[neighborNode.Id] = tentativeDist;
					openSet.Enqueue(neighborNode, tentativeDist);
				}
			}

			// 2. 다른 Region으로 이동 (Gate의 cross-region 연결)
			var gates = currentRegion.GetGates(current.Location.LocalId);
			foreach (var gate in gates)
			{
				if (gate.IsBlocked) continue;
				if (gate.ConnectedLocation.RegionId == current.Location.RegionId) continue; // same-region은 #1에서 처리

				if (context != null && !gate.CanTraverseForward(context)) continue;

				var destLocation = _terrain.GetLocation(gate.ConnectedLocation);
				if (destLocation == null) continue;

				var destNode = new SearchNode(destLocation);
				if (closedSet.Contains(destNode.Id)) continue;

				float tentativeDist = distMap[current.Id] + gate.Distance;

				if (!distMap.ContainsKey(destNode.Id) || tentativeDist < distMap[destNode.Id])
				{
					cameFrom[destNode.Id] = (current, null);
					distMap[destNode.Id] = tentativeDist;
					openSet.Enqueue(destNode, tentativeDist);
				}
			}
		}

		return new PathResult { Found = false, VisitedNodes = visitedCount };
	}

	/// <summary>
	/// Region 내 경로 재구성
	/// </summary>
	private List<Location> ReconstructPath(Dictionary<string, Location> cameFrom, Location current)
	{
		var path = new List<Location> { current };

		while (cameFrom.ContainsKey(current.GlobalId))
		{
			current = cameFrom[current.GlobalId];
			path.Add(current);
		}

		path.Reverse();
		return path;
	}

	/// <summary>
	/// Region 간 경로 재구성
	/// </summary>
	private PathResult ReconstructCrossRegionPath(
		Dictionary<string, (SearchNode node, int? regionGateId)> cameFrom,
		SearchNode current,
		float totalTime,
		int visitedCount)
	{
		var path = new List<Location> { current.Location };
		var regions = new HashSet<int> { current.Location.RegionId };
		var regionGates = new List<int>();

		while (cameFrom.ContainsKey(current.Id))
		{
			var (prevNode, regionGateId) = cameFrom[current.Id];
			
			if (regionGateId.HasValue)
				regionGates.Add(regionGateId.Value);

			current = prevNode;
			path.Add(current.Location);
			regions.Add(current.Location.RegionId);
		}

		path.Reverse();
		regionGates.Reverse();

		return new PathResult
		{
			Found = true,
			Path = path,
			GraphDistance = totalTime,
			VisitedNodes = visitedCount,
			RegionsTraversed = regions.ToList(),
			RegionGatesUsed = regionGates
		};
	}

	/// <summary>
	/// 탐색용 내부 노드
	/// </summary>
	private class SearchNode
	{
		public Location Location { get; }
		public string Id => Location.GlobalId;

		public SearchNode(Location location)
		{
			Location = location;
		}
	}
}
