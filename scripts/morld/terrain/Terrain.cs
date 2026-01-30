namespace Morld;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using Godot;
using SE;

/// <summary>
/// Terrain - 여러 Region과 Region 간 연결을 관리
/// </summary>
public class Terrain
{
    private readonly Dictionary<int, Region> _regions = new();
    private readonly Dictionary<int, RegionGate> _regionGates = new();
    /// <summary>
    /// Region ID별 연결된 RegionGate 목록 (O(1) 조회를 위한 인덱스)
    /// Key: Region ID, Value: 해당 Region에 연결된 모든 RegionGate
    /// </summary>
    private readonly Dictionary<int, List<RegionGate>> _regionGateIndex = new();
    private readonly HashSet<int> _changedRegions = new();
    private bool _isRegionGateChanged;
    /// <summary>
    /// RegionGate ID 자동 생성을 위한 카운터 (중복 방지)
    /// </summary>
    private int _nextRegionGateId = 0;

    /// <summary>
    /// Terrain 이름
    /// </summary>
    public string Name { get; set; } = "unknown";

    /// <summary>
    /// 모든 Region
    /// </summary>
    public IReadOnlyCollection<Region> Regions => _regions.Values;

    /// <summary>
    /// 모든 Region 간 연결
    /// </summary>
    public IReadOnlyCollection<RegionGate> RegionGates => _regionGates.Values;

    /// <summary>
    /// Region 수
    /// </summary>
    public int RegionCount => _regions.Count;

    /// <summary>
    /// Region 간 연결 수
    /// </summary>
    public int RegionGateCount => _regionGates.Count;

    public Terrain(string name = "unknown")
    {
        Name = name;
    }

    #region Change Tracking

    /// <summary>
    /// 변경된 Region이 있는지 여부
    /// </summary>
    public bool IsChanged() => _changedRegions.Count > 0 || _isRegionGateChanged;

    /// <summary>
    /// 특정 Region이 변경되었는지 여부
    /// </summary>
    public bool IsRegionChanged(int regionId) => _changedRegions.Contains(regionId);

    /// <summary>
    /// RegionGate가 변경되었는지 여부
    /// </summary>
    public bool IsRegionGateChanged() => _isRegionGateChanged;

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
    /// RegionGate 변경 표시 (내부용)
    /// </summary>
    internal void MarkRegionGateAsChanged()
    {
        _isRegionGateChanged = true;
    }

    /// <summary>
    /// 모든 변경 플래그 초기화
    /// </summary>
    public void ClearAllChangedFlags()
    {
        _changedRegions.Clear();
        _isRegionGateChanged = false;

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
    /// Terrain 전체 초기화 (모든 Region, RegionGate 제거)
    /// </summary>
    public void Clear()
    {
        _regions.Clear();
        _regionGates.Clear();
        _regionGateIndex.Clear();
        _changedRegions.Clear();
        _isRegionGateChanged = false;
        _nextRegionGateId = 0;
    }

    /// <summary>
    /// Region 추가
    /// </summary>
    /// <param name="regionId">Region 고유 ID</param>
    /// <param name="name">Region 이름</param>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public Region AddRegion(int regionId, string name = "unknown", bool throwOnDuplicate = false)
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
        _regionGateIndex[regionId] = new List<RegionGate>();
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
        _regionGateIndex[region.Id] = new List<RegionGate>();
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

        // 해당 Region과 연결된 모든 RegionGate도 제거
        if (_regionGateIndex.TryGetValue(regionId, out var gates))
        {
            var gatesToRemove = gates.ToList();
            foreach (var rGate in gatesToRemove)
            {
                RemoveRegionGate(rGate.Id);
            }
        }

        _regionGateIndex.Remove(regionId);
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

    #region Pi-World Gate 조회

    /// <summary>
    /// Gate 가져오기 (전역) (Pi-World)
    /// </summary>
    public Gate? GetGate(int regionId, int localId, int gateId)
    {
        return GetRegion(regionId)?.GetGate(localId, gateId);
    }

    /// <summary>
    /// Gate 가져오기 (LocationRef로) (Pi-World)
    /// </summary>
    public Gate? GetGate(LocationRef location, int gateId)
    {
        return GetGate(location.RegionId, location.LocalId, gateId);
    }

    /// <summary>
    /// Gate 가져오기 (GateRef로) (Pi-World)
    /// </summary>
    public Gate? GetGate(GateRef gateRef)
    {
        return GetGate(gateRef.Location.RegionId, gateRef.Location.LocalId, gateRef.GateId);
    }

    /// <summary>
    /// Location의 모든 Gate 가져오기 (Pi-World)
    /// </summary>
    public IReadOnlyCollection<Gate> GetGates(LocationRef location)
    {
        return GetRegion(location.RegionId)?.GetGates(location.LocalId) ?? Array.Empty<Gate>();
    }


    #endregion

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
    public RegionGate AddRegionGate(
        int gateId,
        int regionIdA, int localIdA,
        int regionIdB, int localIdB,
        int travelTime,
        bool throwOnDuplicate = false)
    {
        if (_regionGates.ContainsKey(gateId))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"RegionGate with ID '{gateId}' already exists");
            return _regionGates[gateId];
        }

        ValidateRegionAndLocation(regionIdA, localIdA);
        ValidateRegionAndLocation(regionIdB, localIdB);

        var rGate = new RegionGate(gateId, regionIdA, localIdA, regionIdB, localIdB);
        rGate.OwnerWorld = this;
        rGate.SetTravelTime(travelTime);

        _regionGates[gateId] = rGate;
        _regionGateIndex[regionIdA].Add(rGate);
        _regionGateIndex[regionIdB].Add(rGate);

        if (gateId >= _nextRegionGateId)
            _nextRegionGateId = gateId + 1;

        MarkRegionGateAsChanged();
        return rGate;
    }

    /// <summary>
    /// Region 간 연결 추가 (방향별 다른 이동 시간)
    /// </summary>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public RegionGate AddRegionGate(
        int gateId,
        int regionIdA, int localIdA,
        int regionIdB, int localIdB,
        int travelTimeAtoB, int travelTimeBtoA,
        bool throwOnDuplicate = false)
    {
        if (_regionGates.ContainsKey(gateId))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"RegionGate with ID '{gateId}' already exists");
            return _regionGates[gateId];
        }

        ValidateRegionAndLocation(regionIdA, localIdA);
        ValidateRegionAndLocation(regionIdB, localIdB);

        var rGate = new RegionGate(gateId, regionIdA, localIdA, regionIdB, localIdB);
        rGate.OwnerWorld = this;
        rGate.SetTravelTime(travelTimeAtoB, travelTimeBtoA);

        _regionGates[gateId] = rGate;
        _regionGateIndex[regionIdA].Add(rGate);
        _regionGateIndex[regionIdB].Add(rGate);

        if (gateId >= _nextRegionGateId)
            _nextRegionGateId = gateId + 1;

        MarkRegionGateAsChanged();
        return rGate;
    }

    /// <summary>
    /// Region 간 연결 추가 (ID 자동 생성)
    /// </summary>
    public RegionGate AddRegionGate(
        int regionIdA, int localIdA,
        int regionIdB, int localIdB,
        int travelTime)
    {
        return AddRegionGate(_nextRegionGateId, regionIdA, localIdA, regionIdB, localIdB, travelTime);
    }

    /// <summary>
    /// 기존 RegionGate 객체 추가
    /// </summary>
    /// <param name="throwOnDuplicate">중복 시 예외 발생 여부 (기본: false)</param>
    public void AddRegionGate(RegionGate rGate, bool throwOnDuplicate = false)
    {
        if (rGate == null) throw new ArgumentNullException(nameof(rGate));

        if (_regionGates.ContainsKey(rGate.Id))
        {
            if (throwOnDuplicate)
                throw new InvalidOperationException($"RegionGate with ID '{rGate.Id}' already exists");
            return;
        }

        ValidateRegionAndLocation(rGate.LocationA.RegionId, rGate.LocationA.LocalId);
        ValidateRegionAndLocation(rGate.LocationB.RegionId, rGate.LocationB.LocalId);

        rGate.OwnerWorld = this;
        _regionGates[rGate.Id] = rGate;
        _regionGateIndex[rGate.LocationA.RegionId].Add(rGate);
        _regionGateIndex[rGate.LocationB.RegionId].Add(rGate);

        if (rGate.Id >= _nextRegionGateId)
            _nextRegionGateId = rGate.Id + 1;

        MarkRegionGateAsChanged();
    }

    /// <summary>
    /// RegionGate 가져오기
    /// </summary>
    public RegionGate? GetRegionGate(int gateId)
    {
        return _regionGates.TryGetValue(gateId, out var rGate) ? rGate : null;
    }

    /// <summary>
    /// RegionGate 제거
    /// </summary>
    public bool RemoveRegionGate(int gateId)
    {
        if (!_regionGates.TryGetValue(gateId, out var rGate))
            return false;

        _regionGates.Remove(gateId);
        if (_regionGateIndex.TryGetValue(rGate.LocationA.RegionId, out var gatesA))
            gatesA.Remove(rGate);
        if (_regionGateIndex.TryGetValue(rGate.LocationB.RegionId, out var gatesB))
            gatesB.Remove(rGate);

        return true;
    }

    /// <summary>
    /// 특정 Region에 연결된 모든 RegionGate 가져오기
    /// </summary>
    public IReadOnlyList<RegionGate> GetRegionGates(int regionId)
    {
        if (_regionGateIndex.TryGetValue(regionId, out var gates))
            return gates;
        return Array.Empty<RegionGate>();
    }

    /// <summary>
    /// 특정 Location에서 연결된 RegionGate 목록 가져오기
    /// </summary>
    public IEnumerable<RegionGate> GetRegionGatesFrom(LocationRef from)
    {
        var gates = GetRegionGates(from.RegionId);

        foreach (var rGate in gates)
        {
            var locInRegion = rGate.GetLocationInRegion(from.RegionId);
            if (locInRegion == null || locInRegion.Value != from)
                continue;

            yield return rGate;
        }
    }

    /// <summary>
    /// 특정 Location에서 다른 Region으로 이동 가능한 연결들 가져오기
    /// </summary>
    public IEnumerable<(RegionGate rGate, LocationRef destination, float travelTime)> GetRegionExits(
        LocationRef from,
        TraversalContext? context = null)
    {
        var gates = GetRegionGates(from.RegionId);

        foreach (var rGate in gates)
        {
            var locInRegion = rGate.GetLocationInRegion(from.RegionId);
            if (locInRegion == null || locInRegion.Value != from)
                continue;

            if (rGate.CanTraverse(from, context))
            {
                var destination = rGate.GetOtherLocation(from);
                var travelTime = rGate.GetTravelTime(from);
                yield return (rGate, destination, travelTime);
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
    /// 모든 RegionGate 유효성 검사 및 무효한 것 제거
    /// </summary>
    public List<int> ValidateAndCleanRegionGates()
    {
        var invalidGates = new List<int>();

        foreach (var rGate in _regionGates.Values.ToList())
        {
            bool isValid = true;

            // Region 존재 확인
            if (!_regions.ContainsKey(rGate.LocationA.RegionId) ||
                !_regions.ContainsKey(rGate.LocationB.RegionId))
            {
                isValid = false;
            }
            else
            {
                // Location 존재 확인
                var locA = GetLocation(rGate.LocationA);
                var locB = GetLocation(rGate.LocationB);
                if (locA == null || locB == null)
                    isValid = false;
            }

            if (!isValid)
            {
                invalidGates.Add(rGate.Id);
                RemoveRegionGate(rGate.Id);
            }
        }

        return invalidGates;
    }

    /// <summary>
    /// 경로 탐색 (PathFinder 래퍼) - TraversalContext 직접 전달
    /// </summary>
    public PathResult FindPath(LocationRef from, LocationRef to, TraversalContext? context)
    {
        var pathFinder = new PathFinder(this);
        return pathFinder.FindPath(from, to, context);
    }

    /// <summary>
    /// 경로 탐색 (PathFinder 래퍼) - Unit 기반 (하위 호환용)
    /// </summary>
    public PathResult FindPath(LocationRef from, LocationRef to, Unit? unit = null, ItemSystem? itemSystem = null, InventorySystem? inventorySystem = null)
    {
        var pathFinder = new PathFinder(this);
        return pathFinder.FindPath(from, to, unit, itemSystem, inventorySystem);
    }

    /// <summary>
    /// 경로의 총 이동 시간 계산 (Pi-World: Gate/RegionGate X 좌표 기반)
    /// Gate 통과 조건, Gate.TravelTime, RegionGate 이동 시간을 모두 고려
    /// </summary>
    /// <param name="pathResult">FindPath 결과</param>
    /// <param name="startX">출발 X 좌표 (기본 0)</param>
    /// <param name="speedModifier">이동 속도 배율 (기본 1.0)</param>
    /// <param name="context">Gate 통과 조건 체크용 (null이면 조건 무시)</param>
    /// <returns>총 이동 시간 (밀리초), 경로가 없으면 0</returns>
    public int CalculatePathTravelTime(PathResult pathResult, float startX = 0f, float speedModifier = 1.0f, TraversalContext? context = null)
    {
        if (!pathResult.Found || pathResult.Path.Count < 2)
            return 0;

        int totalTime = 0;
        float currentX = startX;

        for (int i = 0; i < pathResult.Path.Count - 1; i++)
        {
            var fromLocRef = new LocationRef(pathResult.Path[i]);
            var toLocRef = new LocationRef(pathResult.Path[i + 1]);

            var location = GetLocation(fromLocRef);
            if (location == null) continue;

            var region = GetRegion(fromLocRef.RegionId);
            if (region == null) continue;

            // 목적지로 연결된 Gate 찾기
            var gates = region.GetGates(fromLocRef.LocalId);
            Gate? targetGate = null;
            foreach (var gate in gates)
            {
                if (gate.ConnectedLocation == toLocRef &&
                    (context == null || gate.CanTraverseForward(context)))
                {
                    targetGate = gate;
                    break;
                }
            }

            if (targetGate == null)
            {
                // Gate가 없으면 RegionGate (다른 Region 연결) 확인
                bool foundRegionGate = false;
                foreach (var rGate in GetRegionGatesFrom(fromLocRef))
                {
                    var dest = rGate.GetOtherLocation(fromLocRef);
                    if (dest == toLocRef && (context == null || rGate.CanTraverse(fromLocRef, context)))
                    {
                        totalTime += rGate.GetTravelTime(fromLocRef);
                        foundRegionGate = true;
                        break;
                    }
                }

                if (!foundRegionGate)
                {
                    throw new System.InvalidOperationException(
                        $"[Terrain.CalculatePathTravelTime] No Gate or RegionGate found from {fromLocRef} to {toLocRef}");
                }

                currentX = 0f;
                continue;
            }

            // Gate까지 이동 시간 + Gate 통과 시간 (밀리초)
            int travelTime = location.CalculateTravelTime(currentX, targetGate.X, speedModifier);
            totalTime += travelTime + targetGate.TravelTime;

            // Gate 통과 후 위치 업데이트
            currentX = targetGate.ArrivalX;
        }

        return totalTime;
    }

    /// <summary>
    /// Region ID 존재 여부 확인
    /// </summary>
    public bool HasRegion(int regionId) => _regions.ContainsKey(regionId);

    /// <summary>
    /// RegionGate ID 존재 여부 확인
    /// </summary>
    public bool HasRegionGate(int gateId) => _regionGates.ContainsKey(gateId);

    /// <summary>
    /// 다음 사용 가능한 Region ID
    /// </summary>
    public int GetNextRegionId() => _regions.Count > 0 ? _regions.Keys.Max() + 1 : 0;

    /// <summary>
    /// 다음 사용 가능한 RegionGate ID
    /// </summary>
    public int GetNextRegionGateId() => _nextRegionGateId;

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

        // 3. RegionGate ID 중복 체크
        var gateValidation = ValidateRegionGateIds();
        result.Merge(gateValidation);

        // 4. RegionGate 참조 유효성 검사
        var refValidation = ValidateRegionGateReferences();
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
    /// RegionGate ID 중복 검사
    /// </summary>
    public ValidationResult ValidateRegionGateIds()
    {
        var result = new ValidationResult();

        var ids = _regionGates.Keys.ToList();
        var duplicates = ids.GroupBy(x => x)
            .Where(g => g.Count() > 1)
            .Select(g => g.Key)
            .ToList();

        foreach (var dup in duplicates)
        {
            result.AddError($"Duplicate RegionGate ID: '{dup}'");
        }

        return result;
    }

    /// <summary>
    /// RegionGate가 참조하는 Region/Location 존재 여부 검사
    /// </summary>
    public ValidationResult ValidateRegionGateReferences()
    {
        var result = new ValidationResult();

        foreach (var rGate in _regionGates.Values)
        {
            // Region A 존재 확인
            if (!_regions.ContainsKey(rGate.LocationA.RegionId))
            {
                result.AddError($"RegionGate '{rGate.Id}' references non-existent Region: '{rGate.LocationA.RegionId}'");
            }
            else if (_regions[rGate.LocationA.RegionId].GetLocation(rGate.LocationA.LocalId) == null)
            {
                result.AddError($"RegionGate '{rGate.Id}' references non-existent Location: {rGate.LocationA}");
            }

            // Region B 존재 확인
            if (!_regions.ContainsKey(rGate.LocationB.RegionId))
            {
                result.AddError($"RegionGate '{rGate.Id}' references non-existent Region: '{rGate.LocationB.RegionId}'");
            }
            else if (_regions[rGate.LocationB.RegionId].GetLocation(rGate.LocationB.LocalId) == null)
            {
                result.AddError($"RegionGate '{rGate.Id}' references non-existent Location: {rGate.LocationB}");
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
        return $"Terrain[{Name ?? "Unnamed"}]: {RegionCount} regions, {RegionGateCount} connections";
    }

    #region JSON Serialization

    /// <summary>
    /// JSON 파일에서 Terrain 로드
    /// </summary>
    public static Terrain LoadFromFile(string filePath)
    {
        using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
        if (file == null)
        {
            throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
        }
        var json = file.GetAsText();
        return LoadFromJson(json);
    }

    /// <summary>
    /// JSON 문자열에서 Terrain 로드
    /// </summary>
    public static Terrain LoadFromJson(string json)
    {
        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            WriteIndented = true
        };

        var data = JsonSerializer.Deserialize<TerrainJsonData>(json, options);
        if (data == null)
            throw new InvalidOperationException("Failed to parse Terrain JSON data");

        return ImportFromData(data);
    }

    /// <summary>
    /// TerrainJsonData에서 Terrain 객체 생성
    /// </summary>
    private static Terrain ImportFromData(TerrainJsonData data)
    {
        var terrain = new Terrain(data.Name);

        // Region 추가
        foreach (var regionData in data.Regions)
        {
            var region = new Region(regionData.Id, regionData.Name);

            // Location 추가
            foreach (var locData in regionData.Locations)
            {
                region.AddLocation(locData.Id, locData.Name);
            }


            terrain.AddRegion(region);
        }

        // RegionGate 추가
        foreach (var gateData in data.RegionGates)
        {
            var rGate = terrain.AddRegionGate(
                gateData.Id,
                gateData.RegionA, gateData.LocalA,
                gateData.RegionB, gateData.LocalB,
                gateData.TimeAtoB,
                gateData.TimeBtoA);

            rGate.Name = gateData.Name;
            rGate.IsBlocked = gateData.IsBlocked;

            if (gateData.ConditionsAtoB != null)
            {
                foreach (var (tag, value) in gateData.ConditionsAtoB)
                    rGate.AddConditionAtoB(tag, value);
            }
            if (gateData.ConditionsBtoA != null)
            {
                foreach (var (tag, value) in gateData.ConditionsBtoA)
                    rGate.AddConditionBtoA(tag, value);
            }
        }

        return terrain;
    }

    /// <summary>
    /// JSON 파일에서 현재 Terrain 업데이트
    /// </summary>
    public void UpdateFromFile(string filePath)
    {
        using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
        if (file == null)
        {
            throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
        }
        var json = file.GetAsText();
        UpdateFromJson(json);
    }

    /// <summary>
    /// JSON 문자열에서 현재 Terrain 업데이트
    /// </summary>
    public void UpdateFromJson(string json)
    {
        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            WriteIndented = true
        };

        var data = JsonSerializer.Deserialize<TerrainJsonData>(json, options);
        if (data == null)
            throw new InvalidOperationException("Failed to parse Terrain JSON data");

        UpdateFromData(data);
    }

    /// <summary>
    /// TerrainJsonData로 현재 Terrain 업데이트
    /// </summary>
    private void UpdateFromData(TerrainJsonData data)
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

            // Region DescribeText 복사
            if (regionData.DescribeText != null)
            {
                foreach (var (key, value) in regionData.DescribeText)
                {
                    region.DescribeText[key] = value;
                }
            }

            // Region 날씨 복사
            region.CurrentWeather = regionData.Weather;

            // Location 추가
            foreach (var locData in regionData.Locations)
            {
                var location = region.AddLocation(locData.Id, locData.Name);

                // Location DescribeText 복사
                if (locData.DescribeText != null)
                {
                    foreach (var (key, value) in locData.DescribeText)
                    {
                        location.DescribeText[key] = value;
                    }
                }

                // StayDuration 복사
                location.StayDuration = locData.StayDuration;

                // Indoor 복사
                location.IsIndoor = locData.Indoor;

                // 주의: Location의 바닥 아이템은 InventorySystem에서 관리됨
            }


            AddRegion(region);
        }

        // RegionGate 추가
        foreach (var gateData in data.RegionGates)
        {
            var rGate = AddRegionGate(
                gateData.Id,
                gateData.RegionA, gateData.LocalA,
                gateData.RegionB, gateData.LocalB,
                gateData.TimeAtoB,
                gateData.TimeBtoA);

            rGate.Name = gateData.Name;
            rGate.IsBlocked = gateData.IsBlocked;

            if (gateData.ConditionsAtoB != null)
            {
                foreach (var (tag, value) in gateData.ConditionsAtoB)
                    rGate.AddConditionAtoB(tag, value);
            }
            if (gateData.ConditionsBtoA != null)
            {
                foreach (var (tag, value) in gateData.ConditionsBtoA)
                    rGate.AddConditionBtoA(tag, value);
            }
        }

        // 변경 플래그 초기화
        ClearAllChangedFlags();
    }

    /// <summary>
    /// Terrain을 JSON 파일로 저장
    /// </summary>
    public void SaveToFile(string filePath)
    {
        var json = ToJson();

        using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Write);
        if (file == null)
        {
            throw new InvalidOperationException($"Failed to open file for writing: {filePath}");
        }
        file.StoreString(json);
    }

    /// <summary>
    /// Terrain을 JSON 문자열로 변환
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
    /// Terrain을 TerrainJsonData로 변환
    /// </summary>
    private TerrainJsonData ExportToData()
    {
        var data = new TerrainJsonData
        {
            Name = Name
        };

        // Region 내보내기
        foreach (var region in _regions.Values.OrderBy(r => r.Id))
        {
            var regionData = new RegionJsonData
            {
                Id = region.Id,
                Name = region.Name,
                Weather = region.CurrentWeather
            };

            // Region DescribeText 내보내기
            if (region.DescribeText.Count > 0)
                regionData.DescribeText = new Dictionary<string, string>(region.DescribeText);

            // Location 내보내기
            foreach (var location in region.Locations.OrderBy(l => l.LocalId))
            {
                var locationData = new LocationJsonData
                {
                    Id = location.LocalId,
                    Name = location.Name,
                    StayDuration = location.StayDuration,
                    Indoor = location.IsIndoor
                };

                // DescribeText 내보내기
                if (location.DescribeText.Count > 0)
                    locationData.DescribeText = new Dictionary<string, string>(location.DescribeText);

                // 주의: Location의 바닥 아이템은 InventorySystem에서 관리됨

                regionData.Locations.Add(locationData);
            }

            // Note: Gate export would go here if needed for JSON serialization

            data.Regions.Add(regionData);
        }

        // RegionGate 내보내기
        foreach (var rGate in _regionGates.Values.OrderBy(e => e.Id))
        {
            var gateData = new RegionGateJsonData
            {
                Id = rGate.Id,
                Name = rGate.Name,
                RegionA = rGate.LocationA.RegionId,
                LocalA = rGate.LocationA.LocalId,
                RegionB = rGate.LocationB.RegionId,
                LocalB = rGate.LocationB.LocalId,
                TimeAtoB = rGate.TravelTimeAtoB,
                TimeBtoA = rGate.TravelTimeBtoA,
                IsBlocked = rGate.IsBlocked
            };

            if (rGate.ConditionsAtoB.Count > 0)
                gateData.ConditionsAtoB = new Dictionary<string, int>(rGate.ConditionsAtoB);
            if (rGate.ConditionsBtoA.Count > 0)
                gateData.ConditionsBtoA = new Dictionary<string, int>(rGate.ConditionsBtoA);

            data.RegionGates.Add(gateData);
        }

        return data;
    }

    #endregion

    #region Condition Checking

    /// <summary>
    /// 조건 딕셔너리를 검사하여 통과 여부, 차단 사유, 숨김 여부를 반환
    /// 조건 키가 '#'로 끝나면 조건 미충족 시 숨김 처리
    /// </summary>
    /// <param name="conditions">조건 딕셔너리 (키: prop 이름, 값: 필요 수치)</param>
    /// <param name="actualProps">실제 유닛 Props</param>
    /// <returns>(통과 여부, 차단 사유, 숨김 여부)</returns>
    public (bool canPass, string? blockedReason, bool isHidden) CheckConditionsWithHiddenMarker(
        Dictionary<string, int> conditions, TraversalContext actualProps)
    {
        bool canPass = true;
        string? blockedReason = null;
        bool isHidden = false;

        foreach (var (propName, requiredValue) in conditions)
        {
            // '#'로 끝나는 조건: 미충족 시 숨김
            var isHiddenCondition = propName.EndsWith("#");
            var actualPropName = isHiddenCondition ? propName.Substring(0, propName.Length - 1) : propName;

            if (actualProps.GetProp(actualPropName) < requiredValue)
            {
                canPass = false;
                if (isHiddenCondition)
                {
                    isHidden = true;
                }
                else
                {
                    blockedReason = $"{actualPropName}이(가) 필요합니다";
                }
                break;
            }
        }

        return (canPass, blockedReason, isHidden);
    }

    #endregion

    #region Route Building

    /// <summary>
    /// 원시 경로 정보 (표시 이름 없음)
    /// </summary>
    public struct RawRouteInfo
    {
        public LocationRef Destination;
        public int TravelTime;
        public bool IsRegionGate;
        public bool IsBlocked;
        public string? BlockedReason;
        public bool IsHidden;
    }

    /// <summary>
    /// 특정 위치에서 이동 가능한 경로 목록 생성 (조건 필터링 적용)
    /// </summary>
    /// <param name="from">출발 위치</param>
    /// <param name="actualProps">유닛의 실제 Props (장비 효과 포함)</param>
    /// <param name="unitX">유닛의 현재 X 좌표 (이동 시간 계산용)</param>
    /// <param name="speedModifier">이동 속도 배율 (1.0 = 기본)</param>
    /// <returns>이동 가능한 경로 목록 (표시 이름 제외)</returns>
    public List<RawRouteInfo> BuildRawRoutes(LocationRef from, TraversalContext actualProps, float unitX = 0f, float speedModifier = 1.0f)
    {
        var routes = new List<RawRouteInfo>();

        var region = GetRegion(from.RegionId);
        var location = GetLocation(from);
        if (region == null || location == null) return routes;

        // Gate 기반 경로 (Pi-World)
        var gates = region.GetGates(from.LocalId);
        foreach (var gate in gates)
        {
            if (gate.IsBlocked) continue;

            var conditions = gate.ConditionsForward;
            var (canPass, blockedReason, isHidden) = CheckConditionsWithHiddenMarker(conditions, actualProps);

            var isRegionGate = gate.ConnectedLocation.RegionId != from.RegionId;
            // Gate까지 이동 시간 + Gate 통과 시간 (밀리초)
            int travelTimeMillis = location.CalculateTravelTime(unitX, gate.X, speedModifier) + gate.TravelTime;
            routes.Add(new RawRouteInfo
            {
                Destination = gate.ConnectedLocation,
                TravelTime = travelTimeMillis,
                IsRegionGate = isRegionGate,
                IsBlocked = !canPass,
                BlockedReason = blockedReason,
                IsHidden = isHidden
            });
        }

        // RegionGate (Legacy support)
        foreach (var regionGate in GetRegionGatesFrom(from))
        {
            if (regionGate.IsBlocked) continue;

            var conditions = regionGate.GetConditions(from);
            var (canPass, blockedReason, isHidden) = CheckConditionsWithHiddenMarker(conditions, actualProps);

            var destination = regionGate.GetOtherLocation(from);
            routes.Add(new RawRouteInfo
            {
                Destination = destination,
                TravelTime = regionGate.GetTravelTime(from),
                IsRegionGate = true,
                IsBlocked = !canPass,
                BlockedReason = blockedReason,
                IsHidden = isHidden
            });
        }

        return routes;
    }

    #endregion

    #region Debug Output

    /// <summary>
    /// Terrain 전체 정보를 콘솔에 출력 (디버그용)
    /// </summary>
    public void DebugPrint(bool includeGates = true, bool includeRegionGates = true)
    {
        var output = GetDebugString(includeGates, includeRegionGates);
        GD.Print(output);
    }

    /// <summary>
    /// Terrain 전체 정보를 문자열로 반환 (디버그용)
    /// </summary>
    public string GetDebugString(bool includeGates = true, bool includeRegionGates = true)
    {
        var lines = new List<string>();

        // 헤더
        lines.Add("╔════════════════════════════════════════════════════════════╗");
        lines.Add($"║  TERRAIN: {Name ?? "Unnamed",-48} ║");
        lines.Add("╠════════════════════════════════════════════════════════════╣");
        lines.Add($"║  Regions: {RegionCount,-6}  RegionGates: {RegionGateCount,-27} ║");
        lines.Add("╚════════════════════════════════════════════════════════════╝");
        lines.Add("");

        // 각 Region 출력
        foreach (var region in _regions.Values.OrderBy(r => r.Id))
        {
            lines.Add($"┌─────────────────────────────────────────────────────────────┐");
            lines.Add($"│ Region [{region.Id}]: {region.Name ?? "Unnamed",-45} │");
            lines.Add($"├─────────────────────────────────────────────────────────────┤");
            lines.Add($"│ Locations: {region.LocationCount,-6}  Gates: {region.GateCount,-35} │");
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

            // Gates 테이블 (옵션)
            if (includeGates && region.GateCount > 0)
            {
                lines.Add("  Gates:");
                lines.Add("  ┌────────┬────────┬──────────────────────────┬─────────┐");
                lines.Add("  │  Loc   │ GateID │ Connected To             │ Blocked │");
                lines.Add("  ├────────┼────────┼──────────────────────────┼─────────┤");

                foreach (var gate in region.Gates)
                {
                    var blocked = gate.IsBlocked ? "   Yes" : "    -";
                    var connected = $"R{gate.ConnectedLocation.RegionId}:L{gate.ConnectedLocation.LocalId}(X={gate.ArrivalX:F0})";

                    lines.Add($"  │ {gate.OwnerLocation.LocalId,6} │ {gate.Id,6} │ {connected,-24} │ {blocked,7} │");

                    // Conditions 표시
                    if (gate.ConditionsForward.Count > 0)
                    {
                        var conditions = string.Join(", ", gate.ConditionsForward.Select(kvp => $"{kvp.Key}={kvp.Value}"));
                        lines.Add($"  │        │        │ Fwd: {conditions,-40} │");
                    }
                }

                lines.Add("  └────────┴────────┴──────────────────────────┴─────────┘");
                lines.Add("");
            }
        }

        // RegionGates 테이블 (옵션)
        if (includeRegionGates && RegionGateCount > 0)
        {
            lines.Add("┌─────────────────────────────────────────────────────────────┐");
            lines.Add($"│ Region Gates ({RegionGateCount})                                         │");
            lines.Add("├─────────────────────────────────────────────────────────────┤");
            lines.Add("│  ID  │ Name                 │ From        │ To          │TT │");
            lines.Add("├──────┼──────────────────────┼─────────────┼─────────────┼───┤");

            foreach (var rGate in _regionGates.Values.OrderBy(e => e.Id))
            {
                var name = (rGate.Name ?? rGate.Id.ToString()).PadRight(20);
                if (name.Length > 20) name = name.Substring(0, 20);

                var from = $"R{rGate.LocationA.RegionId}:L{rGate.LocationA.LocalId}".PadRight(11);
                var to = $"R{rGate.LocationB.RegionId}:L{rGate.LocationB.LocalId}".PadRight(11);
                var tt = rGate.TravelTimeAtoB >= 0 ? rGate.TravelTimeAtoB.ToString() : (rGate.TravelTimeBtoA >= 0 ? rGate.TravelTimeBtoA.ToString() : "?");

                lines.Add($"│ {rGate.Id,4} │ {name} │ {from} │ {to} │{tt,2} │");

                // 상세 정보
                if (rGate.TravelTimeAtoB != rGate.TravelTimeBtoA)
                {
                    var timeAtoB = rGate.TravelTimeAtoB >= 0 ? rGate.TravelTimeAtoB.ToString() : "N/A";
                    var timeBtoA = rGate.TravelTimeBtoA >= 0 ? rGate.TravelTimeBtoA.ToString() : "N/A";
                    lines.Add($"│      │                      │ A→B: {timeAtoB,-6} B→A: {timeBtoA,-6}           │");
                }

                if (rGate.IsBlocked)
                {
                    lines.Add($"│      │                      │ [BLOCKED]                           │");
                }

                if (rGate.ConditionsAtoB.Count > 0)
                {
                    var conditions = string.Join(", ", rGate.ConditionsAtoB.Select(kvp => $"{kvp.Key}={kvp.Value}"));
                    lines.Add($"│      │ A→B Conditions: {conditions,-36} │");
                }
                if (rGate.ConditionsBtoA.Count > 0)
                {
                    var conditions = string.Join(", ", rGate.ConditionsBtoA.Select(kvp => $"{kvp.Key}={kvp.Value}"));
                    lines.Add($"│      │ B→A Conditions: {conditions,-36} │");
                }
            }

            lines.Add("└──────┴──────────────────────┴─────────────┴─────────────┴───┘");
        }

        return string.Join("\n", lines);
    }

    /// <summary>
    /// Terrain 요약 정보를 콘솔에 출력 (간단 버전)
    /// </summary>
    public void DebugPrintSummary()
    {
        var output = GetDebugSummary();
        GD.Print(output);
    }

    /// <summary>
    /// Terrain 요약 정보를 문자열로 반환 (간단 버전)
    /// </summary>
    public string GetDebugSummary()
    {
        var lines = new List<string>();

        lines.Add("═══════════════════════════════════════════════════════════");
        lines.Add($"  TERRAIN: {Name ?? "Unnamed"}");
        lines.Add("═══════════════════════════════════════════════════════════");
        lines.Add($"  Regions: {RegionCount}");
        lines.Add($"  RegionGates: {RegionGateCount}");
        lines.Add("");

        foreach (var region in _regions.Values.OrderBy(r => r.Id))
        {
            lines.Add($"  [{region.Id}] {region.Name ?? "Unnamed"}: {region.LocationCount} locations, {region.GateCount} gates");
        }

        return string.Join("\n", lines);
    }

    #endregion
}
