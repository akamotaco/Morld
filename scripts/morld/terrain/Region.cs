namespace Morld;

using System;
using System.Collections.Generic;
using System.Linq;

/// <summary>
/// Region - Location들의 그래프를 포함하는 영역
/// </summary>
public class Region : IDescribable
{
    private readonly Dictionary<int, Location> _locations = new();
    private readonly Dictionary<int, List<Edge>> _adjacencyList = new();
    private readonly List<Edge> _allEdges = new();
    private bool _isChanged;

    /// <summary>
    /// Region 고유 식별자
    /// </summary>
    public int Id { get; }

    /// <summary>
    /// Region 이름
    /// </summary>
    public string Name { get; set; } = "unknown";

    /// <summary>
    /// 소속 Terrain (변경 추적용)
    /// </summary>
    internal Terrain? OwnerWorld { get; set; }

    /// <summary>
    /// 추가 데이터
    /// </summary>
    public object? Tag { get; set; }

    /// <summary>
    /// 장소 묘사 텍스트 (IDescribable)
    /// </summary>
    public Dictionary<string, string> DescribeText { get; set; } = new();

    /// <summary>
    /// 현재 날씨 (맑음, 흐림, 비, 눈)
    /// Region 내 모든 실외 Location에 적용됨
    /// </summary>
    public string CurrentWeather { get; set; } = "맑음";

    /// <summary>
    /// 사용 가능한 날씨 종류
    /// </summary>
    public static readonly string[] WeatherTypes = ["맑음", "흐림", "비", "눈"];

    /// <summary>
    /// Region 내 모든 Location
    /// </summary>
    public IReadOnlyCollection<Location> Locations => _locations.Values;

    /// <summary>
    /// Region 내 모든 Edge
    /// </summary>
    public IReadOnlyCollection<Edge> Edges => _allEdges;

    /// <summary>
    /// Location 수
    /// </summary>
    public int LocationCount => _locations.Count;

    /// <summary>
    /// Edge 수
    /// </summary>
    public int EdgeCount => _allEdges.Count;

    public Region(int id, string name = "unknown")
    {
        Id = id;
        Name = name;
    }

    #region Change Tracking

    /// <summary>
    /// Region이 변경되었는지 여부
    /// </summary>
    public bool IsChanged() => _isChanged;

    /// <summary>
    /// 변경됨으로 표시 (내부용)
    /// </summary>
    internal void MarkAsChanged()
    {
        _isChanged = true;
        OwnerWorld?.MarkRegionAsChanged(Id);
    }

    /// <summary>
    /// 변경 플래그 초기화
    /// </summary>
    public void ClearChangedFlag()
    {
        _isChanged = false;
    }

    #endregion

    /// <summary>
    /// Location 추가
    /// </summary>
    /// <param name="localId">Location 로컬 ID</param>
    /// <param name="name">Location 이름</param>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public Location AddLocation(int localId, string name = "unknown", bool throwOnDuplicate = false)
    {
        if (localId < 0)
            throw new ArgumentException("Local ID cannot be negative", nameof(localId));

        if (_locations.ContainsKey(localId))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"Location with ID {localId} already exists in Region '{Id}'");
            return _locations[localId];
        }

        var location = new Location(localId, Id, name);
        location.ParentRegion = this;
        _locations[localId] = location;
        _adjacencyList[localId] = new List<Edge>();
        return location;
    }

    /// <summary>
    /// 기존 Location 객체 추가
    /// </summary>
    /// <param name="location">Location 객체</param>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public void AddLocation(Location location, bool throwOnDuplicate = false)
    {
        if (location == null) throw new ArgumentNullException(nameof(location));
        if (location.RegionId != Id)
            throw new ArgumentException($"Location belongs to region '{location.RegionId}', not '{Id}'");

        if (_locations.ContainsKey(location.LocalId))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"Location with ID {location.LocalId} already exists in Region '{Id}'");
            return;
        }

        location.ParentRegion = this;
        _locations[location.LocalId] = location;
        _adjacencyList[location.LocalId] = new List<Edge>();
    }

    /// <summary>
    /// 양방향 엣지 추가 (동일한 이동 시간)
    /// </summary>
    public Edge AddEdge(int localIdA, int localIdB, int travelTime)
    {
        var locationA = GetOrCreateLocation(localIdA);
        var locationB = GetOrCreateLocation(localIdB);

        var edge = new Edge(locationA, locationB);
        edge.OwnerRegion = this;
        edge.SetTravelTime(travelTime);

        _adjacencyList[localIdA].Add(edge);
        _adjacencyList[localIdB].Add(edge);
        _allEdges.Add(edge);

        MarkAsChanged();
        return edge;
    }

    /// <summary>
    /// 양방향 엣지 추가 (방향별 다른 이동 시간)
    /// </summary>
    public Edge AddEdge(int localIdA, int localIdB, int travelTimeAtoB, int travelTimeBtoA)
    {
        var locationA = GetOrCreateLocation(localIdA);
        var locationB = GetOrCreateLocation(localIdB);

        var edge = new Edge(locationA, locationB);
        edge.OwnerRegion = this;
        edge.SetTravelTime(travelTimeAtoB, travelTimeBtoA);

        _adjacencyList[localIdA].Add(edge);
        _adjacencyList[localIdB].Add(edge);
        _allEdges.Add(edge);

        MarkAsChanged();
        return edge;
    }

    /// <summary>
    /// 엣지 제거
    /// </summary>
    public bool RemoveEdge(int localIdA, int localIdB)
    {
        var edge = GetEdgeBetween(localIdA, localIdB);
        if (edge == null)
            return false;

        _adjacencyList[localIdA].Remove(edge);
        _adjacencyList[localIdB].Remove(edge);
        _allEdges.Remove(edge);
        edge.OwnerRegion = null;

        MarkAsChanged();
        return true;
    }

    /// <summary>
    /// ID로 Location 가져오기
    /// </summary>
    public Location? GetLocation(int localId)
    {
        return _locations.TryGetValue(localId, out var location) ? location : null;
    }

    /// <summary>
    /// 이름으로 Location 검색
    /// </summary>
    /// <param name="name">검색할 이름 (부분 일치)</param>
    /// <param name="exactMatch">정확히 일치해야 하는지 (기본: false)</param>
    /// <returns>일치하는 Location 목록</returns>
    public List<Location> FindLocations(string name, bool exactMatch = false)
    {
        if (string.IsNullOrEmpty(name))
            return new List<Location>();

        if (exactMatch)
        {
            return _locations.Values
                .Where(loc => loc.Name != "unknown" && loc.Name.Equals(name, StringComparison.OrdinalIgnoreCase))
                .ToList();
        }
        else
        {
            return _locations.Values
                .Where(loc => loc.Name != "unknown" && loc.Name.Contains(name, StringComparison.OrdinalIgnoreCase))
                .ToList();
        }
    }

    /// <summary>
    /// Location이 없으면 생성
    /// </summary>
    private Location GetOrCreateLocation(int localId)
    {
        if (!_locations.ContainsKey(localId))
            return AddLocation(localId);
        return _locations[localId];
    }

    /// <summary>
    /// 특정 Location에 연결된 모든 엣지 가져오기
    /// </summary>
    public IReadOnlyList<Edge> GetEdges(Location location)
    {
        if (_adjacencyList.TryGetValue(location.LocalId, out var edges))
            return edges;
        return Array.Empty<Edge>();
    }

    /// <summary>
    /// 특정 Location에 연결된 모든 이웃 Location들 가져오기 (이동 가능 여부 무관)
    /// </summary>
    public IEnumerable<Location> GetNeighbors(Location location)
    {
        var edges = GetEdges(location);
        foreach (var edge in edges)
        {
            yield return edge.GetOtherLocation(location);
        }
    }

    /// <summary>
    /// 특정 Location에서 이동 가능한 이웃들 가져오기
    /// </summary>
    public IEnumerable<(Location neighbor, Edge edge, int travelTime)> GetTraversableNeighbors(
        Location location,
        TraversalContext? context = null)
    {
        var edges = GetEdges(location);

        foreach (var edge in edges)
        {
            if (edge.CanTraverse(location, context))
            {
                var neighbor = edge.GetOtherLocation(location);
                var travelTime = edge.GetTravelTime(location);
                yield return (neighbor, edge, travelTime);
            }
        }
    }

    /// <summary>
    /// 두 Location 사이의 엣지 찾기
    /// </summary>
    public Edge? GetEdgeBetween(int localIdA, int localIdB)
    {
        if (!_adjacencyList.TryGetValue(localIdA, out var edges))
            return null;

        return edges.FirstOrDefault(e =>
            (e.LocationA.LocalId == localIdA && e.LocationB.LocalId == localIdB) ||
            (e.LocationA.LocalId == localIdB && e.LocationB.LocalId == localIdA));
    }

    /// <summary>
    /// Region 초기화
    /// </summary>
    public void Clear()
    {
        _locations.Clear();
        _adjacencyList.Clear();
        _allEdges.Clear();
    }

    /// <summary>
    /// Location ID 존재 여부 확인
    /// </summary>
    public bool HasLocation(int localId) => _locations.ContainsKey(localId);

    /// <summary>
    /// Location ID 유효성 검사
    /// </summary>
    /// <returns>검사 결과</returns>
    public ValidationResult ValidateLocationIds()
    {
        var result = new ValidationResult();

        // 중복 체크 (Dictionary 특성상 중복 불가하지만, 명시적 확인)
        var ids = _locations.Keys.ToList();
        var duplicates = ids.GroupBy(x => x)
            .Where(g => g.Count() > 1)
            .Select(g => g.Key)
            .ToList();

        foreach (var dup in duplicates)
        {
            result.AddError($"Duplicate Location ID: {dup} in Region '{Id}'");
        }

        // 연속성 체크 (0부터 시작하는 연속된 ID인지)
        if (ids.Count > 0)
        {
            var minId = ids.Min();
            var maxId = ids.Max();

            if (minId != 0)
            {
                result.AddWarning($"Location IDs don't start from 0 (starts from {minId}) in Region '{Id}'");
            }

            var expectedCount = maxId - minId + 1;
            if (ids.Count != expectedCount)
            {
                var allExpected = Enumerable.Range(minId, expectedCount);
                var missing = allExpected.Except(ids).ToList();
                foreach (var m in missing)
                {
                    result.AddWarning($"Missing Location ID: {m} in Region '{Id}'");
                }
            }
        }

        return result;
    }

    /// <summary>
    /// 빈(사용되지 않은) Location ID 슬롯 찾기
    /// </summary>
    /// <param name="maxId">검사할 최대 ID (기본: 현재 최대 ID)</param>
    /// <returns>비어있는 ID 목록</returns>
    public List<int> FindEmptyLocationIds(int? maxId = null)
    {
        if (_locations.Count == 0)
            return new List<int>();

        var currentMax = maxId ?? _locations.Keys.Max();
        var allIds = Enumerable.Range(0, currentMax + 1);
        return allIds.Except(_locations.Keys).ToList();
    }

    /// <summary>
    /// 다음 사용 가능한 Location ID 반환
    /// </summary>
    public int GetNextAvailableLocationId()
    {
        if (_locations.Count == 0)
            return 0;

        return _locations.Keys.Max() + 1;
    }

    public override string ToString() => Name != "unknown" ? Name : $"Region[{Id}]";
}
