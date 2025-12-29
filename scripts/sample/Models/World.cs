namespace PathFinding.Models;

using System;
using System.Collections.Generic;
using System.Linq;

/// <summary>
/// World - 여러 Region과 Region 간 연결을 관리
/// </summary>
public class World
{
    private readonly Dictionary<int, Region> _regions = new();
    private readonly Dictionary<int, RegionEdge> _regionEdges = new();
    private readonly Dictionary<int, List<RegionEdge>> _regionEdgeIndex = new();
    private readonly HashSet<int> _changedRegions = new();
    private bool _isRegionEdgeChanged;
    private int _nextRegionEdgeId = 0;

    /// <summary>
    /// World 이름
    /// </summary>
    public string? Name { get; set; }

    /// <summary>
    /// 모든 Region
    /// </summary>
    public IReadOnlyCollection<Region> Regions => _regions.Values;

    /// <summary>
    /// 모든 Region 간 연결
    /// </summary>
    public IReadOnlyCollection<RegionEdge> RegionEdges => _regionEdges.Values;

    /// <summary>
    /// Region 수
    /// </summary>
    public int RegionCount => _regions.Count;

    /// <summary>
    /// Region 간 연결 수
    /// </summary>
    public int RegionEdgeCount => _regionEdges.Count;

    public World(string? name = null)
    {
        Name = name;
    }

    #region Change Tracking

    /// <summary>
    /// 변경된 Region이 있는지 여부
    /// </summary>
    public bool IsChanged() => _changedRegions.Count > 0 || _isRegionEdgeChanged;

    /// <summary>
    /// 특정 Region이 변경되었는지 여부
    /// </summary>
    public bool IsRegionChanged(int regionId) => _changedRegions.Contains(regionId);

    /// <summary>
    /// RegionEdge가 변경되었는지 여부
    /// </summary>
    public bool IsRegionEdgeChanged() => _isRegionEdgeChanged;

    /// <summary>
    /// 변경된 Region ID 목록
    /// </summary>
    public IReadOnlyCollection<int> GetChangedRegions() => _changedRegions;

    /// <summary>
    /// Region 변경 표시 (내부용)
    /// </summary>
    internal void MarkRegionAsChanged(int regionId)
    {
        _changedRegions.Add(regionId);
    }

    /// <summary>
    /// RegionEdge 변경 표시 (내부용)
    /// </summary>
    internal void MarkRegionEdgeAsChanged()
    {
        _isRegionEdgeChanged = true;
    }

    /// <summary>
    /// 모든 변경 플래그 초기화
    /// </summary>
    public void ClearAllChangedFlags()
    {
        _changedRegions.Clear();
        _isRegionEdgeChanged = false;

        foreach (var region in _regions.Values)
        {
            region.ClearChangedFlag();
        }
    }

    /// <summary>
    /// 특정 Region의 변경 플래그만 초기화
    /// </summary>
    public void ClearRegionChangedFlag(int regionId)
    {
        _changedRegions.Remove(regionId);
        if (_regions.TryGetValue(regionId, out var region))
            region.ClearChangedFlag();
    }

    #endregion

    /// <summary>
    /// Region 추가
    /// </summary>
    /// <param name="regionId">Region 고유 ID</param>
    /// <param name="name">Region 이름 (선택)</param>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public Region AddRegion(int regionId, string? name = null, bool throwOnDuplicate = false)
    {
        if (_regions.ContainsKey(regionId))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"Region with ID '{regionId}' already exists");
            return _regions[regionId];
        }

        var region = new Region(regionId, name);
        region.OwnerWorld = this;
        _regions[regionId] = region;
        _regionEdgeIndex[regionId] = new List<RegionEdge>();
        return region;
    }

    /// <summary>
    /// 기존 Region 객체 추가
    /// </summary>
    /// <param name="region">Region 객체</param>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public void AddRegion(Region region, bool throwOnDuplicate = false)
    {
        if (region == null) throw new ArgumentNullException(nameof(region));

        if (_regions.ContainsKey(region.Id))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"Region with ID '{region.Id}' already exists");
            return;
        }

        region.OwnerWorld = this;
        _regions[region.Id] = region;
        _regionEdgeIndex[region.Id] = new List<RegionEdge>();
    }

    /// <summary>
    /// Region 가져오기
    /// </summary>
    public Region? GetRegion(int regionId)
    {
        return _regions.TryGetValue(regionId, out var region) ? region : null;
    }

    /// <summary>
    /// Region 제거
    /// </summary>
    public bool RemoveRegion(int regionId)
    {
        if (!_regions.Remove(regionId))
            return false;

        // 해당 Region과 연결된 모든 RegionEdge도 제거
        if (_regionEdgeIndex.TryGetValue(regionId, out var edges))
        {
            var edgesToRemove = edges.ToList();
            foreach (var edge in edgesToRemove)
            {
                RemoveRegionEdge(edge.Id);
            }
        }

        _regionEdgeIndex.Remove(regionId);
        return true;
    }

    /// <summary>
    /// Location 가져오기 (전역)
    /// </summary>
    public Location? GetLocation(int regionId, int localId)
    {
        return GetRegion(regionId)?.GetLocation(localId);
    }

    /// <summary>
    /// Location 가져오기 (LocationRef로)
    /// </summary>
    public Location? GetLocation(LocationRef locationRef)
    {
        return GetLocation(locationRef.RegionId, locationRef.LocalId);
    }

    /// <summary>
    /// 이름으로 Location 검색
    /// </summary>
    /// <param name="name">검색할 이름</param>
    /// <param name="regionId">특정 Region에서만 검색 (null이면 전체 검색)</param>
    /// <param name="exactMatch">정확히 일치해야 하는지 (기본: false)</param>
    /// <returns>검색 결과 목록 (LocationRef와 Location 쌍)</returns>
    public List<LocationSearchResult> FindLocations(string name, int? regionId = null, bool exactMatch = false)
    {
        var results = new List<LocationSearchResult>();

        if (string.IsNullOrEmpty(name))
            return results;

        IEnumerable<Region> regionsToSearch;

        if (regionId.HasValue)
        {
            var region = GetRegion(regionId.Value);
            if (region == null)
                return results;
            regionsToSearch = new[] { region };
        }
        else
        {
            regionsToSearch = _regions.Values;
        }

        foreach (var region in regionsToSearch)
        {
            var locations = region.FindLocations(name, exactMatch);
            foreach (var loc in locations)
            {
                results.Add(new LocationSearchResult
                {
                    Location = loc,
                    LocationRef = new LocationRef(loc),
                    RegionId = region.Id,
                    LocalId = loc.LocalId
                });
            }
        }

        return results;
    }

    /// <summary>
    /// 첫 번째 일치하는 Location 검색
    /// </summary>
    /// <param name="name">검색할 이름</param>
    /// <param name="regionId">특정 Region에서만 검색 (null이면 전체 검색)</param>
    /// <param name="exactMatch">정확히 일치해야 하는지 (기본: false)</param>
    /// <returns>검색 결과 (없으면 null)</returns>
    public LocationSearchResult? FindLocation(string name, int? regionId = null, bool exactMatch = false)
    {
        var results = FindLocations(name, regionId, exactMatch);
        return results.FirstOrDefault();
    }

    /// <summary>
    /// Region 간 연결 추가
    /// </summary>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public RegionEdge AddRegionEdge(
        int edgeId,
        int regionIdA, int localIdA,
        int regionIdB, int localIdB,
        float travelTime,
        bool throwOnDuplicate = false)
    {
        if (_regionEdges.ContainsKey(edgeId))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"RegionEdge with ID '{edgeId}' already exists");
            return _regionEdges[edgeId];
        }

        ValidateRegionAndLocation(regionIdA, localIdA);
        ValidateRegionAndLocation(regionIdB, localIdB);

        var edge = new RegionEdge(edgeId, regionIdA, localIdA, regionIdB, localIdB);
        edge.OwnerWorld = this;
        edge.SetTravelTime(travelTime);

        _regionEdges[edgeId] = edge;
        _regionEdgeIndex[regionIdA].Add(edge);
        _regionEdgeIndex[regionIdB].Add(edge);

        if (edgeId >= _nextRegionEdgeId)
            _nextRegionEdgeId = edgeId + 1;

        MarkRegionEdgeAsChanged();
        return edge;
    }

    /// <summary>
    /// Region 간 연결 추가 (방향별 다른 이동 시간)
    /// </summary>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public RegionEdge AddRegionEdge(
        int edgeId,
        int regionIdA, int localIdA,
        int regionIdB, int localIdB,
        float? travelTimeAtoB, float? travelTimeBtoA,
        bool throwOnDuplicate = false)
    {
        if (_regionEdges.ContainsKey(edgeId))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"RegionEdge with ID '{edgeId}' already exists");
            return _regionEdges[edgeId];
        }

        ValidateRegionAndLocation(regionIdA, localIdA);
        ValidateRegionAndLocation(regionIdB, localIdB);

        var edge = new RegionEdge(edgeId, regionIdA, localIdA, regionIdB, localIdB);
        edge.OwnerWorld = this;
        edge.SetTravelTime(travelTimeAtoB, travelTimeBtoA);

        _regionEdges[edgeId] = edge;
        _regionEdgeIndex[regionIdA].Add(edge);
        _regionEdgeIndex[regionIdB].Add(edge);

        if (edgeId >= _nextRegionEdgeId)
            _nextRegionEdgeId = edgeId + 1;

        MarkRegionEdgeAsChanged();
        return edge;
    }

    /// <summary>
    /// Region 간 연결 추가 (ID 자동 생성)
    /// </summary>
    public RegionEdge AddRegionEdge(
        int regionIdA, int localIdA,
        int regionIdB, int localIdB,
        float travelTime)
    {
        return AddRegionEdge(_nextRegionEdgeId, regionIdA, localIdA, regionIdB, localIdB, travelTime);
    }

    /// <summary>
    /// 기존 RegionEdge 객체 추가
    /// </summary>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public void AddRegionEdge(RegionEdge edge, bool throwOnDuplicate = false)
    {
        if (edge == null) throw new ArgumentNullException(nameof(edge));

        if (_regionEdges.ContainsKey(edge.Id))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"RegionEdge with ID '{edge.Id}' already exists");
            return;
        }

        ValidateRegionAndLocation(edge.LocationA.RegionId, edge.LocationA.LocalId);
        ValidateRegionAndLocation(edge.LocationB.RegionId, edge.LocationB.LocalId);

        edge.OwnerWorld = this;
        _regionEdges[edge.Id] = edge;
        _regionEdgeIndex[edge.LocationA.RegionId].Add(edge);
        _regionEdgeIndex[edge.LocationB.RegionId].Add(edge);

        if (edge.Id >= _nextRegionEdgeId)
            _nextRegionEdgeId = edge.Id + 1;

        MarkRegionEdgeAsChanged();
    }

    /// <summary>
    /// RegionEdge 가져오기
    /// </summary>
    public RegionEdge? GetRegionEdge(int edgeId)
    {
        return _regionEdges.TryGetValue(edgeId, out var edge) ? edge : null;
    }

    /// <summary>
    /// RegionEdge 제거
    /// </summary>
    public bool RemoveRegionEdge(int edgeId)
    {
        if (!_regionEdges.TryGetValue(edgeId, out var edge))
            return false;

        _regionEdges.Remove(edgeId);
        if (_regionEdgeIndex.TryGetValue(edge.LocationA.RegionId, out var edgesA))
            edgesA.Remove(edge);
        if (_regionEdgeIndex.TryGetValue(edge.LocationB.RegionId, out var edgesB))
            edgesB.Remove(edge);

        return true;
    }

    /// <summary>
    /// 특정 Region에 연결된 모든 RegionEdge 가져오기
    /// </summary>
    public IReadOnlyList<RegionEdge> GetRegionEdges(int regionId)
    {
        if (_regionEdgeIndex.TryGetValue(regionId, out var edges))
            return edges;
        return Array.Empty<RegionEdge>();
    }

    /// <summary>
    /// 특정 Location에서 다른 Region으로 이동 가능한 연결들 가져오기
    /// </summary>
    public IEnumerable<(RegionEdge edge, LocationRef destination, float travelTime)> GetRegionExits(
        LocationRef from,
        TraversalContext? context = null)
    {
        var edges = GetRegionEdges(from.RegionId);

        foreach (var edge in edges)
        {
            var locInRegion = edge.GetLocationInRegion(from.RegionId);
            if (locInRegion == null || locInRegion.Value != from)
                continue;

            if (edge.CanTraverse(from, context))
            {
                var destination = edge.GetOtherLocation(from);
                var travelTime = edge.GetTravelTime(from)!.Value;
                yield return (edge, destination, travelTime);
            }
        }
    }

    /// <summary>
    /// Region과 Location 유효성 검사
    /// </summary>
    private void ValidateRegionAndLocation(int regionId, int localId)
    {
        if (!_regions.ContainsKey(regionId))
            throw new ArgumentException($"Region '{regionId}' not found");

        if (_regions[regionId].GetLocation(localId) == null)
            throw new ArgumentException($"Location {localId} not found in Region '{regionId}'");
    }

    /// <summary>
    /// 모든 RegionEdge 유효성 검사 및 무효한 것 제거
    /// </summary>
    public List<int> ValidateAndCleanRegionEdges()
    {
        var invalidEdges = new List<int>();

        foreach (var edge in _regionEdges.Values.ToList())
        {
            bool isValid = true;

            // Region 존재 확인
            if (!_regions.ContainsKey(edge.LocationA.RegionId) ||
                !_regions.ContainsKey(edge.LocationB.RegionId))
            {
                isValid = false;
            }
            else
            {
                // Location 존재 확인
                var locA = GetLocation(edge.LocationA);
                var locB = GetLocation(edge.LocationB);
                if (locA == null || locB == null)
                    isValid = false;
            }

            if (!isValid)
            {
                invalidEdges.Add(edge.Id);
                RemoveRegionEdge(edge.Id);
            }
        }

        return invalidEdges;
    }

    /// <summary>
    /// Region ID 존재 여부 확인
    /// </summary>
    public bool HasRegion(int regionId) => _regions.ContainsKey(regionId);

    /// <summary>
    /// RegionEdge ID 존재 여부 확인
    /// </summary>
    public bool HasRegionEdge(int edgeId) => _regionEdges.ContainsKey(edgeId);

    /// <summary>
    /// 다음 사용 가능한 Region ID
    /// </summary>
    public int GetNextRegionId() => _regions.Count > 0 ? _regions.Keys.Max() + 1 : 0;

    /// <summary>
    /// 다음 사용 가능한 RegionEdge ID
    /// </summary>
    public int GetNextRegionEdgeId() => _nextRegionEdgeId;

    /// <summary>
    /// 전체 ID 유효성 검사 (World → Region → Location)
    /// </summary>
    /// <param name="checkEmptySlots">빈 ID 슬롯도 경고로 표시할지</param>
    /// <returns>검사 결과</returns>
    public ValidationResult ValidateAllIds(bool checkEmptySlots = false)
    {
        var result = new ValidationResult();

        // 1. Region ID 중복 체크
        var regionValidation = ValidateRegionIds();
        result.Merge(regionValidation);

        // 2. 각 Region 내 Location ID 검사
        foreach (var region in _regions.Values)
        {
            var locationValidation = region.ValidateLocationIds();
            result.Merge(locationValidation);
        }

        // 3. RegionEdge ID 중복 체크
        var edgeValidation = ValidateRegionEdgeIds();
        result.Merge(edgeValidation);

        // 4. RegionEdge 참조 유효성 검사
        var refValidation = ValidateRegionEdgeReferences();
        result.Merge(refValidation);

        // 5. 빈 슬롯 확인 (옵션)
        if (checkEmptySlots)
        {
            var emptySlotValidation = CheckEmptyIdSlots();
            result.Merge(emptySlotValidation);
        }

        return result;
    }

    /// <summary>
    /// Region ID 중복 검사
    /// </summary>
    public ValidationResult ValidateRegionIds()
    {
        var result = new ValidationResult();

        // Dictionary 특성상 중복 불가하지만 명시적 확인
        var ids = _regions.Keys.ToList();
        var duplicates = ids.GroupBy(x => x)
            .Where(g => g.Count() > 1)
            .Select(g => g.Key)
            .ToList();

        foreach (var dup in duplicates)
        {
            result.AddError($"Duplicate Region ID: '{dup}'");
        }

        return result;
    }

    /// <summary>
    /// RegionEdge ID 중복 검사
    /// </summary>
    public ValidationResult ValidateRegionEdgeIds()
    {
        var result = new ValidationResult();

        var ids = _regionEdges.Keys.ToList();
        var duplicates = ids.GroupBy(x => x)
            .Where(g => g.Count() > 1)
            .Select(g => g.Key)
            .ToList();

        foreach (var dup in duplicates)
        {
            result.AddError($"Duplicate RegionEdge ID: '{dup}'");
        }

        return result;
    }

    /// <summary>
    /// RegionEdge가 참조하는 Region/Location 존재 여부 검사
    /// </summary>
    public ValidationResult ValidateRegionEdgeReferences()
    {
        var result = new ValidationResult();

        foreach (var edge in _regionEdges.Values)
        {
            // Region A 존재 확인
            if (!_regions.ContainsKey(edge.LocationA.RegionId))
            {
                result.AddError($"RegionEdge '{edge.Id}' references non-existent Region: '{edge.LocationA.RegionId}'");
            }
            else if (_regions[edge.LocationA.RegionId].GetLocation(edge.LocationA.LocalId) == null)
            {
                result.AddError($"RegionEdge '{edge.Id}' references non-existent Location: {edge.LocationA}");
            }

            // Region B 존재 확인
            if (!_regions.ContainsKey(edge.LocationB.RegionId))
            {
                result.AddError($"RegionEdge '{edge.Id}' references non-existent Region: '{edge.LocationB.RegionId}'");
            }
            else if (_regions[edge.LocationB.RegionId].GetLocation(edge.LocationB.LocalId) == null)
            {
                result.AddError($"RegionEdge '{edge.Id}' references non-existent Location: {edge.LocationB}");
            }
        }

        return result;
    }

    /// <summary>
    /// 빈 ID 슬롯 확인
    /// </summary>
    public ValidationResult CheckEmptyIdSlots()
    {
        var result = new ValidationResult();

        foreach (var region in _regions.Values)
        {
            var emptySlots = region.FindEmptyLocationIds();
            if (emptySlots.Count > 0)
            {
                result.AddWarning($"Region '{region.Id}' has empty Location ID slots: [{string.Join(", ", emptySlots)}]");
            }
        }

        return result;
    }

    /// <summary>
    /// 모든 Region의 빈 Location ID 슬롯 찾기
    /// </summary>
    public Dictionary<int, List<int>> FindAllEmptyLocationIds()
    {
        var result = new Dictionary<int, List<int>>();

        foreach (var region in _regions.Values)
        {
            var emptySlots = region.FindEmptyLocationIds();
            if (emptySlots.Count > 0)
            {
                result[region.Id] = emptySlots;
            }
        }

        return result;
    }

    public override string ToString()
    {
        return $"World[{Name ?? "Unnamed"}]: {RegionCount} regions, {RegionEdgeCount} connections";
    }
}
