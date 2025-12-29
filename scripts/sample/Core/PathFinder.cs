namespace PathFinding.Core;
using System;
using System.Collections.Generic;
using System.Linq;
using PathFinding.Models;

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
    /// 총 이동 시간
    /// </summary>
    public float TotalTravelTime { get; init; }

    /// <summary>
    /// 탐색 중 방문한 노드 수
    /// </summary>
    public int VisitedNodes { get; init; }

    /// <summary>
    /// 경유한 Region ID 목록
    /// </summary>
    public List<int> RegionsTraversed { get; init; } = new();

    /// <summary>
    /// 사용한 RegionEdge ID 목록
    /// </summary>
    public List<int> RegionEdgesUsed { get; init; } = new();

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
    private readonly World _world;

    public PathFinder(World world)
    {
        _world = world ?? throw new ArgumentNullException(nameof(world));
    }

    /// <summary>
    /// 경로 탐색 (같은 Region 또는 다른 Region)
    /// </summary>
    public PathResult FindPath(LocationRef start, LocationRef goal, TraversalContext? context = null)
    {
        var startLocation = _world.GetLocation(start);
        var goalLocation = _world.GetLocation(goal);

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
    /// 경로 탐색 (직접 Location 지정)
    /// </summary>
    public PathResult FindPath(
        int startRegionId, int startLocalId,
        int goalRegionId, int goalLocalId,
        TraversalContext? context = null)
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
        var region = _world.GetRegion(start.RegionId)!;

        if (start.Equals(goal))
        {
            return new PathResult
            {
                Found = true,
                Path = new List<Location> { start },
                TotalTravelTime = 0,
                VisitedNodes = 1,
                RegionsTraversed = new List<int> { start.RegionId }
            };
        }

        var openSet = new PriorityQueue<Location, float>();
        var cameFrom = new Dictionary<string, Location>();
        var travelTime = new Dictionary<string, float>();
        var closedSet = new HashSet<string>();
        int visitedCount = 0;

        travelTime[start.GlobalId] = 0;
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
                    TotalTravelTime = travelTime[current.GlobalId],
                    VisitedNodes = visitedCount,
                    RegionsTraversed = new List<int> { start.RegionId }
                };
            }

            closedSet.Add(current.GlobalId);

            foreach ((Location neighbor, Edge edge, float edgeTravelTime) in region.GetTraversableNeighbors(current, context))
            {
                if (closedSet.Contains(neighbor.GlobalId))
                    continue;

                float tentativeTime = travelTime[current.GlobalId] + edgeTravelTime;

                if (!travelTime.ContainsKey(neighbor.GlobalId) || tentativeTime < travelTime[neighbor.GlobalId])
                {
                    cameFrom[neighbor.GlobalId] = current;
                    travelTime[neighbor.GlobalId] = tentativeTime;
                    openSet.Enqueue(neighbor, tentativeTime);
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
        // 전역 탐색: Location + RegionEdge를 모두 탐색
        var openSet = new PriorityQueue<SearchNode, float>();
        var cameFrom = new Dictionary<string, (SearchNode node, int? regionEdgeId)>();
        var travelTime = new Dictionary<string, float>();
        var closedSet = new HashSet<string>();
        int visitedCount = 0;

        var startNode = new SearchNode(start);
        travelTime[startNode.Id] = 0;
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
                return ReconstructCrossRegionPath(cameFrom, current, travelTime[current.Id], visitedCount);
            }

            closedSet.Add(current.Id);

            var currentRegion = _world.GetRegion(current.Location.RegionId)!;

            // 1. 같은 Region 내 이동
            foreach ((Location neighbor, Edge edge, float edgeTravelTime) in currentRegion.GetTraversableNeighbors(current.Location, context))
            {
                var neighborNode = new SearchNode(neighbor);
                if (closedSet.Contains(neighborNode.Id))
                    continue;

                float tentativeTime = travelTime[current.Id] + edgeTravelTime;

                if (!travelTime.ContainsKey(neighborNode.Id) || tentativeTime < travelTime[neighborNode.Id])
                {
                    cameFrom[neighborNode.Id] = (current, null);
                    travelTime[neighborNode.Id] = tentativeTime;
                    openSet.Enqueue(neighborNode, tentativeTime);
                }
            }

            // 2. 다른 Region으로 이동 (RegionEdge)
            var currentRef = new LocationRef(current.Location);
            foreach ((RegionEdge regionEdge, LocationRef destRef, float edgeTravelTime) in _world.GetRegionExits(currentRef, context))
            {
                var destLocation = _world.GetLocation(destRef);
                if (destLocation == null)
                    continue;

                var destNode = new SearchNode(destLocation);
                if (closedSet.Contains(destNode.Id))
                    continue;

                float tentativeTime = travelTime[current.Id] + edgeTravelTime;

                if (!travelTime.ContainsKey(destNode.Id) || tentativeTime < travelTime[destNode.Id])
                {
                    cameFrom[destNode.Id] = (current, regionEdge.Id);
                    travelTime[destNode.Id] = tentativeTime;
                    openSet.Enqueue(destNode, tentativeTime);
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
        Dictionary<string, (SearchNode node, int? regionEdgeId)> cameFrom,
        SearchNode current,
        float totalTime,
        int visitedCount)
    {
        var path = new List<Location> { current.Location };
        var regions = new HashSet<int> { current.Location.RegionId };
        var regionEdges = new List<int>();

        while (cameFrom.ContainsKey(current.Id))
        {
            var (prevNode, regionEdgeId) = cameFrom[current.Id];
            
            if (regionEdgeId.HasValue)
                regionEdges.Add(regionEdgeId.Value);

            current = prevNode;
            path.Add(current.Location);
            regions.Add(current.Location.RegionId);
        }

        path.Reverse();
        regionEdges.Reverse();

        return new PathResult
        {
            Found = true,
            Path = path,
            TotalTravelTime = totalTime,
            VisitedNodes = visitedCount,
            RegionsTraversed = regions.ToList(),
            RegionEdgesUsed = regionEdges
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
