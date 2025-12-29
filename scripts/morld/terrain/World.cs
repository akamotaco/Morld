namespace Morld;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using Godot;

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

    #region JSON Serialization

    /// <summary>
    /// JSON 파일에서 World 로드
    /// </summary>
    public static World LoadFromFile(string filePath)
    {
        using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Read);
        if (file == null)
        {
            throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
        }
        var json = file.GetAsText();
        return LoadFromJson(json);
    }

    /// <summary>
    /// JSON 문자열에서 World 로드
    /// </summary>
    public static World LoadFromJson(string json)
    {
        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            WriteIndented = true
        };

        var data = JsonSerializer.Deserialize<WorldJsonData>(json, options);
        if (data == null)
            throw new InvalidOperationException("Failed to parse World JSON data");

        return ImportFromData(data);
    }

    /// <summary>
    /// WorldJsonData에서 World 객체 생성
    /// </summary>
    private static World ImportFromData(WorldJsonData data)
    {
        var world = new World(data.Name);

        // Region 추가
        foreach (var regionData in data.Regions)
        {
            var region = new Region(regionData.Id, regionData.Name);

            // Location 추가
            foreach (var locData in regionData.Locations)
            {
                region.AddLocation(locData.Id, locData.Name);
            }

            // Edge 추가
            foreach (var edgeData in regionData.Edges)
            {
                var edge = region.AddEdge(
                    edgeData.A,
                    edgeData.B,
                    edgeData.TimeAtoB,
                    edgeData.TimeBtoA);

                if (edgeData.ConditionsAtoB != null)
                {
                    foreach (var (tag, value) in edgeData.ConditionsAtoB)
                        edge.AddConditionAtoB(tag, value);
                }
                if (edgeData.ConditionsBtoA != null)
                {
                    foreach (var (tag, value) in edgeData.ConditionsBtoA)
                        edge.AddConditionBtoA(tag, value);
                }

                edge.IsBlocked = edgeData.IsBlocked;
            }

            world.AddRegion(region);
        }

        // RegionEdge 추가
        foreach (var edgeData in data.RegionEdges)
        {
            var edge = world.AddRegionEdge(
                edgeData.Id,
                edgeData.RegionA, edgeData.LocalA,
                edgeData.RegionB, edgeData.LocalB,
                edgeData.TimeAtoB,
                edgeData.TimeBtoA);

            edge.Name = edgeData.Name;
            edge.IsBlocked = edgeData.IsBlocked;

            if (edgeData.ConditionsAtoB != null)
            {
                foreach (var (tag, value) in edgeData.ConditionsAtoB)
                    edge.AddConditionAtoB(tag, value);
            }
            if (edgeData.ConditionsBtoA != null)
            {
                foreach (var (tag, value) in edgeData.ConditionsBtoA)
                    edge.AddConditionBtoA(tag, value);
            }
        }

        return world;
    }

    /// <summary>
    /// JSON 파일에서 현재 World 업데이트
    /// </summary>
    public void UpdateFromFile(string filePath)
    {
        using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Read);
        if (file == null)
        {
            throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
        }
        var json = file.GetAsText();
        UpdateFromJson(json);
    }

    /// <summary>
    /// JSON 문자열에서 현재 World 업데이트
    /// </summary>
    public void UpdateFromJson(string json)
    {
        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            WriteIndented = true
        };

        var data = JsonSerializer.Deserialize<WorldJsonData>(json, options);
        if (data == null)
            throw new InvalidOperationException("Failed to parse World JSON data");

        UpdateFromData(data);
    }

    /// <summary>
    /// WorldJsonData로 현재 World 업데이트
    /// </summary>
    private void UpdateFromData(WorldJsonData data)
    {
        // 기존 데이터 모두 제거
        var regionIds = _regions.Keys.ToList();
        foreach (var regionId in regionIds)
        {
            RemoveRegion(regionId);
        }

        // 새 이름 설정
        Name = data.Name;

        // Region 추가
        foreach (var regionData in data.Regions)
        {
            var region = new Region(regionData.Id, regionData.Name);

            // Location 추가
            foreach (var locData in regionData.Locations)
            {
                region.AddLocation(locData.Id, locData.Name);
            }

            // Edge 추가
            foreach (var edgeData in regionData.Edges)
            {
                var edge = region.AddEdge(
                    edgeData.A,
                    edgeData.B,
                    edgeData.TimeAtoB,
                    edgeData.TimeBtoA);

                if (edgeData.ConditionsAtoB != null)
                {
                    foreach (var (tag, value) in edgeData.ConditionsAtoB)
                        edge.AddConditionAtoB(tag, value);
                }
                if (edgeData.ConditionsBtoA != null)
                {
                    foreach (var (tag, value) in edgeData.ConditionsBtoA)
                        edge.AddConditionBtoA(tag, value);
                }

                edge.IsBlocked = edgeData.IsBlocked;
            }

            AddRegion(region);
        }

        // RegionEdge 추가
        foreach (var edgeData in data.RegionEdges)
        {
            var edge = AddRegionEdge(
                edgeData.Id,
                edgeData.RegionA, edgeData.LocalA,
                edgeData.RegionB, edgeData.LocalB,
                edgeData.TimeAtoB,
                edgeData.TimeBtoA);

            edge.Name = edgeData.Name;
            edge.IsBlocked = edgeData.IsBlocked;

            if (edgeData.ConditionsAtoB != null)
            {
                foreach (var (tag, value) in edgeData.ConditionsAtoB)
                    edge.AddConditionAtoB(tag, value);
            }
            if (edgeData.ConditionsBtoA != null)
            {
                foreach (var (tag, value) in edgeData.ConditionsBtoA)
                    edge.AddConditionBtoA(tag, value);
            }
        }

        // 변경 플래그 초기화
        ClearAllChangedFlags();
    }

    /// <summary>
    /// World를 JSON 파일로 저장
    /// </summary>
    public void SaveToFile(string filePath)
    {
        var json = ToJson();

        using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Write);
        if (file == null)
        {
            throw new InvalidOperationException($"Failed to open file for writing: {filePath}");
        }
        file.StoreString(json);
    }

    /// <summary>
    /// World를 JSON 문자열로 변환
    /// </summary>
    public string ToJson()
    {
        var data = ExportToData();

        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            WriteIndented = true
        };

        return JsonSerializer.Serialize(data, options);
    }

    /// <summary>
    /// World를 WorldJsonData로 변환
    /// </summary>
    private WorldJsonData ExportToData()
    {
        var data = new WorldJsonData
        {
            Name = Name
        };

        // Region 내보내기
        foreach (var region in _regions.Values.OrderBy(r => r.Id))
        {
            var regionData = new RegionJsonData
            {
                Id = region.Id,
                Name = region.Name
            };

            // Location 내보내기
            foreach (var location in region.Locations.OrderBy(l => l.LocalId))
            {
                regionData.Locations.Add(new LocationJsonData
                {
                    Id = location.LocalId,
                    Name = location.Name
                });
            }

            // Edge 내보내기
            foreach (var edge in region.Edges)
            {
                var edgeData = new EdgeJsonData
                {
                    A = edge.LocationA.LocalId,
                    B = edge.LocationB.LocalId,
                    TimeAtoB = edge.TravelTimeAtoB,
                    TimeBtoA = edge.TravelTimeBtoA,
                    IsBlocked = edge.IsBlocked
                };

                if (edge.ConditionsAtoB.Count > 0)
                    edgeData.ConditionsAtoB = new Dictionary<string, int>(edge.ConditionsAtoB);
                if (edge.ConditionsBtoA.Count > 0)
                    edgeData.ConditionsBtoA = new Dictionary<string, int>(edge.ConditionsBtoA);

                regionData.Edges.Add(edgeData);
            }

            data.Regions.Add(regionData);
        }

        // RegionEdge 내보내기
        foreach (var edge in _regionEdges.Values.OrderBy(e => e.Id))
        {
            var edgeData = new RegionEdgeJsonData
            {
                Id = edge.Id,
                Name = edge.Name,
                RegionA = edge.LocationA.RegionId,
                LocalA = edge.LocationA.LocalId,
                RegionB = edge.LocationB.RegionId,
                LocalB = edge.LocationB.LocalId,
                TimeAtoB = edge.TravelTimeAtoB,
                TimeBtoA = edge.TravelTimeBtoA,
                IsBlocked = edge.IsBlocked
            };

            if (edge.ConditionsAtoB.Count > 0)
                edgeData.ConditionsAtoB = new Dictionary<string, int>(edge.ConditionsAtoB);
            if (edge.ConditionsBtoA.Count > 0)
                edgeData.ConditionsBtoA = new Dictionary<string, int>(edge.ConditionsBtoA);

            data.RegionEdges.Add(edgeData);
        }

        return data;
    }

    #endregion

    #region Debug Output

    /// <summary>
    /// World 전체 정보를 콘솔에 출력 (디버그용)
    /// </summary>
    public void DebugPrint(bool includeEdges = true, bool includeRegionEdges = true)
    {
        var output = GetDebugString(includeEdges, includeRegionEdges);
        GD.Print(output);
    }

    /// <summary>
    /// World 전체 정보를 문자열로 반환 (디버그용)
    /// </summary>
    public string GetDebugString(bool includeEdges = true, bool includeRegionEdges = true)
    {
        var lines = new List<string>();

        // 헤더
        lines.Add("╔════════════════════════════════════════════════════════════╗");
        lines.Add($"║  WORLD: {Name ?? "Unnamed",-50} ║");
        lines.Add("╠════════════════════════════════════════════════════════════╣");
        lines.Add($"║  Regions: {RegionCount,-6}  RegionEdges: {RegionEdgeCount,-27} ║");
        lines.Add("╚════════════════════════════════════════════════════════════╝");
        lines.Add("");

        // 각 Region 출력
        foreach (var region in _regions.Values.OrderBy(r => r.Id))
        {
            lines.Add($"┌─────────────────────────────────────────────────────────────┐");
            lines.Add($"│ Region [{region.Id}]: {region.Name ?? "Unnamed",-45} │");
            lines.Add($"├─────────────────────────────────────────────────────────────┤");
            lines.Add($"│ Locations: {region.LocationCount,-6}  Edges: {region.EdgeCount,-35} │");
            lines.Add($"└─────────────────────────────────────────────────────────────┘");
            lines.Add("");

            // Locations 테이블
            lines.Add("  Locations:");
            lines.Add("  ┌────────┬────────────────────────────────────────────────┐");
            lines.Add("  │   ID   │ Name                                           │");
            lines.Add("  ├────────┼────────────────────────────────────────────────┤");

            foreach (var location in region.Locations.OrderBy(l => l.LocalId))
            {
                var name = (location.Name ?? "").PadRight(46);
                if (name.Length > 46) name = name.Substring(0, 46);
                lines.Add($"  │ {location.LocalId,6} │ {name} │");
            }

            lines.Add("  └────────┴────────────────────────────────────────────────┘");
            lines.Add("");

            // Edges 테이블 (옵션)
            if (includeEdges && region.EdgeCount > 0)
            {
                lines.Add("  Edges:");
                lines.Add("  ┌────────┬────────┬──────────┬──────────┬─────────┐");
                lines.Add("  │  From  │   To   │  A → B   │  B → A   │ Blocked │");
                lines.Add("  ├────────┼────────┼──────────┼──────────┼─────────┤");

                foreach (var edge in region.Edges)
                {
                    var timeAtoB = edge.TravelTimeAtoB?.ToString("F1").PadLeft(8) ?? "     N/A";
                    var timeBtoA = edge.TravelTimeBtoA?.ToString("F1").PadLeft(8) ?? "     N/A";
                    var blocked = edge.IsBlocked ? "   Yes" : "    -";

                    lines.Add($"  │ {edge.LocationA.LocalId,6} │ {edge.LocationB.LocalId,6} │ {timeAtoB} │ {timeBtoA} │ {blocked,7} │");

                    // Conditions 표시
                    if (edge.ConditionsAtoB.Count > 0)
                    {
                        var conditions = string.Join(", ", edge.ConditionsAtoB.Select(kvp => $"{kvp.Key}={kvp.Value}"));
                        lines.Add($"  │        │        │ A→B Conditions: {conditions,-26} │");
                    }
                    if (edge.ConditionsBtoA.Count > 0)
                    {
                        var conditions = string.Join(", ", edge.ConditionsBtoA.Select(kvp => $"{kvp.Key}={kvp.Value}"));
                        lines.Add($"  │        │        │ B→A Conditions: {conditions,-26} │");
                    }
                }

                lines.Add("  └────────┴────────┴──────────┴──────────┴─────────┘");
                lines.Add("");
            }
        }

        // RegionEdges 테이블 (옵션)
        if (includeRegionEdges && RegionEdgeCount > 0)
        {
            lines.Add("┌─────────────────────────────────────────────────────────────┐");
            lines.Add($"│ Region Edges ({RegionEdgeCount})                                         │");
            lines.Add("├─────────────────────────────────────────────────────────────┤");
            lines.Add("│  ID  │ Name                 │ From        │ To          │TT │");
            lines.Add("├──────┼──────────────────────┼─────────────┼─────────────┼───┤");

            foreach (var edge in _regionEdges.Values.OrderBy(e => e.Id))
            {
                var name = (edge.Name ?? edge.Id.ToString()).PadRight(20);
                if (name.Length > 20) name = name.Substring(0, 20);

                var from = $"R{edge.LocationA.RegionId}:L{edge.LocationA.LocalId}".PadRight(11);
                var to = $"R{edge.LocationB.RegionId}:L{edge.LocationB.LocalId}".PadRight(11);
                var tt = edge.TravelTimeAtoB?.ToString("F0") ?? edge.TravelTimeBtoA?.ToString("F0") ?? "?";

                lines.Add($"│ {edge.Id,4} │ {name} │ {from} │ {to} │{tt,2} │");

                // 상세 정보
                if (edge.TravelTimeAtoB != edge.TravelTimeBtoA)
                {
                    var timeAtoB = edge.TravelTimeAtoB?.ToString("F1") ?? "N/A";
                    var timeBtoA = edge.TravelTimeBtoA?.ToString("F1") ?? "N/A";
                    lines.Add($"│      │                      │ A→B: {timeAtoB,-6} B→A: {timeBtoA,-6}           │");
                }

                if (edge.IsBlocked)
                {
                    lines.Add($"│      │                      │ [BLOCKED]                           │");
                }

                if (edge.ConditionsAtoB.Count > 0)
                {
                    var conditions = string.Join(", ", edge.ConditionsAtoB.Select(kvp => $"{kvp.Key}={kvp.Value}"));
                    lines.Add($"│      │ A→B Conditions: {conditions,-36} │");
                }
                if (edge.ConditionsBtoA.Count > 0)
                {
                    var conditions = string.Join(", ", edge.ConditionsBtoA.Select(kvp => $"{kvp.Key}={kvp.Value}"));
                    lines.Add($"│      │ B→A Conditions: {conditions,-36} │");
                }
            }

            lines.Add("└──────┴──────────────────────┴─────────────┴─────────────┴───┘");
        }

        return string.Join("\n", lines);
    }

    /// <summary>
    /// World 요약 정보를 콘솔에 출력 (간단 버전)
    /// </summary>
    public void DebugPrintSummary()
    {
        var output = GetDebugSummary();
        GD.Print(output);
    }

    /// <summary>
    /// World 요약 정보를 문자열로 반환 (간단 버전)
    /// </summary>
    public string GetDebugSummary()
    {
        var lines = new List<string>();

        lines.Add("═══════════════════════════════════════════════════════════");
        lines.Add($"  WORLD: {Name ?? "Unnamed"}");
        lines.Add("═══════════════════════════════════════════════════════════");
        lines.Add($"  Regions: {RegionCount}");
        lines.Add($"  RegionEdges: {RegionEdgeCount}");
        lines.Add("");

        foreach (var region in _regions.Values.OrderBy(r => r.Id))
        {
            lines.Add($"  [{region.Id}] {region.Name ?? "Unnamed"}: {region.LocationCount} locations, {region.EdgeCount} edges");
        }

        return string.Join("\n", lines);
    }

    #endregion
}
