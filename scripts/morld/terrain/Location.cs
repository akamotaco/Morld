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
    /// 장소 묘사 텍스트 (IDescribable)
    /// </summary>
    public Dictionary<string, string> DescribeText { get; set; } = new();

    /// <summary>
    /// 경유 시 지체 시간 (분)
    /// 지역이 험하거나 넓어서 통과하는데 시간이 소요됨
    /// 0이면 즉시 통과, 기본값 0
    /// </summary>
    public int StayDuration { get; set; } = 0;

    /// <summary>
    /// 실내 여부 (true: 실내, false: 실외)
    /// 날씨 효과는 실외에서만 표시됨
    /// </summary>
    public bool IsIndoor { get; set; } = true;

    /// <summary>
    /// 부모 Region 참조 (Terrain에서 설정)
    /// </summary>
    public Region? ParentRegion { get; internal set; }

    /// <summary>
    /// 현재 날씨 (실외일 때만 유효, 부모 Region에서 가져옴)
    /// </summary>
    public string? CurrentWeather => IsIndoor ? null : ParentRegion?.CurrentWeather;

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
