namespace Morld;

using System;
using System.Collections.Generic;

/// <summary>
/// Region에 속한 위치 (기존 Node 개념)
/// </summary>
public class Location : IEquatable<Location>, IDescribable
{
    /// <summary>
    /// Region 내에서의 로컬 ID
    /// </summary>
    public int LocalId { get; }

    /// <summary>
    /// 소속 Region ID
    /// </summary>
    public int RegionId { get; }

    /// <summary>
    /// 위치 이름
    /// </summary>
    public string Name { get; set; } = "unknown";

    /// <summary>
    /// 추가 데이터
    /// </summary>
    public object? Tag { get; set; }

    /// <summary>
    /// 상황별 묘사 텍스트 (IDescribable)
    /// </summary>
    public Dictionary<string, string> Description { get; set; } = new();

    /// <summary>
    /// 전역 고유 식별자 (RegionId:LocalId)
    /// </summary>
    public string GlobalId => $"{RegionId}:{LocalId}";

    public Location(int localId, int regionId, string name = "unknown")
    {
        LocalId = localId;
        RegionId = regionId;
        Name = name;
    }

    public bool Equals(Location? other)
    {
        if (other is null) return false;
        return LocalId == other.LocalId && RegionId == other.RegionId;
    }

    public override bool Equals(object? obj) => Equals(obj as Location);
    
    public override int GetHashCode() => HashCode.Combine(RegionId, LocalId);
    
    public override string ToString() => Name != "unknown" ? Name : $"[{GlobalId}]";
}

/// <summary>
/// 전역 위치 참조 (Region 간 이동 시 사용)
/// </summary>
public readonly struct LocationRef : IEquatable<LocationRef>
{
    public int RegionId { get; }
    public int LocalId { get; }

    public LocationRef(int regionId, int localId)
    {
        RegionId = regionId;
        LocalId = localId;
    }

    public LocationRef(Location location)
    {
        RegionId = location.RegionId;
        LocalId = location.LocalId;
    }

    public string GlobalId => $"{RegionId}:{LocalId}";

    public bool Equals(LocationRef other) => 
        RegionId == other.RegionId && LocalId == other.LocalId;

    public override bool Equals(object? obj) => obj is LocationRef other && Equals(other);
    
    public override int GetHashCode() => HashCode.Combine(RegionId, LocalId);
    
    public override string ToString() => GlobalId;

    public static bool operator ==(LocationRef left, LocationRef right) => left.Equals(right);
    public static bool operator !=(LocationRef left, LocationRef right) => !left.Equals(right);
}

/// <summary>
/// Location 검색 결과
/// </summary>
public class LocationSearchResult
{
    /// <summary>
    /// 찾은 Location 객체
    /// </summary>
    public required Location Location { get; init; }

    /// <summary>
    /// Location 참조
    /// </summary>
    public required LocationRef LocationRef { get; init; }

    /// <summary>
    /// Region ID
    /// </summary>
    public required int RegionId { get; init; }

    /// <summary>
    /// Local ID
    /// </summary>
    public required int LocalId { get; init; }

    public override string ToString() => $"{(Location.Name != "unknown" ? Location.Name : "Unnamed")} ({RegionId}:{LocalId})";
}
