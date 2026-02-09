namespace Morld;

using System;
using System.Collections.Generic;

/// <summary>
/// Location의 기하학적 형태
/// </summary>
public enum LocationGeometry
{
    /// <summary>
    /// 선형 공간: X = 거리 (0 ~ Length)
    /// </summary>
    Line,

    /// <summary>
    /// 원형 공간: X = 각도 (0 ~ 360, 회전 가능)
    /// </summary>
    Ring
}

/// <summary>
/// Region에 속한 위치 (기존 Node 개념)
/// Pi-World: 점(0D) → 선형/원형 1D 공간으로 확장
/// </summary>
public class Location : IEquatable<Location>, IDescribable, IOwnable
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
    /// 경유 시 지체 시간 (밀리초)
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
    /// 소유자 unique_id (예: "sera", "mila") - null이면 공용 장소
    /// </summary>
    public string Owner { get; set; }

    /// <summary>
    /// 바닥 오브젝트의 Unit ID (null이면 바닥 없음)
    /// 아이템을 버리거나 떨어뜨릴 때 사용
    /// </summary>
    public int? GroundUnitId { get; set; }

    #region Pi-World 2D 속성

    /// <summary>
    /// Location의 기하학적 형태
    /// Line: X = 거리 (0 ~ Length), Ring: X = 각도 (0 ~ 360)
    /// </summary>
    public LocationGeometry Geometry { get; set; } = LocationGeometry.Line;

    /// <summary>
    /// Location의 길이 (Line 형태에서 X의 최대값)
    /// Ring 형태에서는 무시됨 (항상 360)
    /// </summary>
    public float Length { get; set; } = 0f;

    /// <summary>
    /// 기본 이동 속도 (단위/밀리초) - 전역 상수
    /// 1/1000 = 0.001 (1단위/초 = 60단위/분)
    /// </summary>
    public const float BaseSpeed = 1f / GameTime.MillisPerSecond;

    /// <summary>
    /// Y축 최소값 (확장용, 현재 미사용)
    /// </summary>
    public float HeightMin { get; set; } = 0f;

    /// <summary>
    /// Y축 최대값 (확장용, 현재 미사용)
    /// </summary>
    public float HeightMax { get; set; } = 10f;

    /// <summary>
    /// X축의 유효 최대값
    /// Line: Length, Ring: 360
    /// </summary>
    public float MaxX => Geometry == LocationGeometry.Ring ? 360f : Length;

    /// <summary>
    /// 두 X 좌표 사이의 거리 계산
    /// Ring 형태에서는 최단 경로 (시계/반시계 중 짧은 방향)
    /// </summary>
    public float CalculateDistance(float x1, float x2)
    {
        float dx = MathF.Abs(x2 - x1);

        if (Geometry == LocationGeometry.Ring)
        {
            // Ring: 최단 경로 선택 (직접 또는 반대 방향)
            return MathF.Min(dx, 360f - dx);
        }

        // Line: 직선 거리
        return dx;
    }

    /// <summary>
    /// 거리 기반 이동 시간 계산 (밀리초)
    /// </summary>
    /// <param name="fromX">출발 X 좌표</param>
    /// <param name="toX">도착 X 좌표</param>
    /// <param name="speedModifier">이동 속도 배율 (1.0 = 기본)</param>
    /// <returns>이동 시간 (밀리초, 올림)</returns>
    public int CalculateTravelTime(float fromX, float toX, float speedModifier = 1.0f)
    {
        float distance = CalculateDistance(fromX, toX);
        float speed = BaseSpeed * speedModifier;

        if (speed <= 0f) return int.MaxValue;

        return (int)MathF.Ceiling(distance / speed);
    }

    /// <summary>
    /// X 좌표 정규화 (범위 내로 제한)
    /// Ring: 0~360 범위로 래핑
    /// Line: 0~Length 범위로 클램핑
    /// </summary>
    public float NormalizeX(float x)
    {
        if (Geometry == LocationGeometry.Ring)
        {
            // Ring: 모듈로 연산으로 0~360 범위
            x %= 360f;
            if (x < 0) x += 360f;
            return x;
        }

        // Line: 범위 제한
        return MathF.Max(0f, MathF.Min(x, Length));
    }

    /// <summary>
    /// 거리를 이동 시간(밀리초)으로 변환
    /// </summary>
    /// <param name="distance">거리 (location units)</param>
    /// <param name="speedModifier">이동 속도 배율 (1.0 = 기본)</param>
    /// <returns>이동 시간 (밀리초, 올림). 거리 0 이하면 0</returns>
    public static int DistanceToTime(float distance, float speedModifier = 1.0f)
    {
        if (distance <= 0f) return 0;
        float speed = BaseSpeed * speedModifier;
        if (speed <= 0f) return int.MaxValue;
        return (int)MathF.Ceiling(distance / speed);
    }

    #endregion

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
