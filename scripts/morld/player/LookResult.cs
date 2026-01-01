namespace Morld;

using System.Collections.Generic;

/// <summary>
/// 현재 플레이어 위치의 정보 조회 결과
/// </summary>
public class LookResult
{
	/// <summary>
	/// 현재 위치 정보
	/// </summary>
	public LocationInfo Location { get; set; } = new();

	/// <summary>
	/// 같은 위치/엣지의 캐릭터 ID들
	/// </summary>
	public List<int> CharacterIds { get; set; } = new();

	/// <summary>
	/// 이동 가능한 경로들
	/// </summary>
	public List<RouteInfo> Routes { get; set; } = new();

	/// <summary>
	/// 같은 위치의 오브젝트 ID들
	/// </summary>
	public List<int> ObjectIds { get; set; } = new();

	/// <summary>
	/// 바닥에 떨어진 아이템 (아이템ID -> 개수)
	/// </summary>
	public Dictionary<int, int> GroundItems { get; set; } = new();
}

/// <summary>
/// 현재 위치 정보
/// </summary>
public class LocationInfo
{
	/// <summary>
	/// 지역 이름
	/// </summary>
	public string RegionName { get; set; } = "";

	/// <summary>
	/// 장소 이름
	/// </summary>
	public string LocationName { get; set; } = "";

	/// <summary>
	/// DescribeSystem에서 선택된 묘사 텍스트
	/// </summary>
	public string DescriptionText { get; set; } = "";

	/// <summary>
	/// 위치 참조
	/// </summary>
	public LocationRef LocationRef { get; set; }
}

/// <summary>
/// 이동 가능한 경로 정보
/// </summary>
public class RouteInfo
{
	/// <summary>
	/// 목적지 장소 이름
	/// </summary>
	public string LocationName { get; set; } = "";

	/// <summary>
	/// 목적지 지역 이름 (다른 Region일 경우 표시)
	/// </summary>
	public string RegionName { get; set; } = "";

	/// <summary>
	/// 목적지 위치 참조
	/// </summary>
	public LocationRef Destination { get; set; }

	/// <summary>
	/// 이동 소요 시간 (분)
	/// </summary>
	public int TravelTime { get; set; }

	/// <summary>
	/// Region 간 이동인지
	/// </summary>
	public bool IsRegionEdge { get; set; }

	/// <summary>
	/// Edge.IsBlocked 또는 조건 미충족
	/// </summary>
	public bool IsBlocked { get; set; }

	/// <summary>
	/// 불가 사유 (아이템 미보유 시)
	/// </summary>
	public string? BlockedReason { get; set; }
}

/// <summary>
/// 오브젝트 살펴보기 결과
/// </summary>
public class ObjectLookResult
{
	/// <summary>
	/// 오브젝트 ID
	/// </summary>
	public int ObjectId { get; set; }

	/// <summary>
	/// 오브젝트 이름
	/// </summary>
	public string Name { get; set; } = "";

	/// <summary>
	/// 오브젝트 인벤토리 (아이템ID -> 개수)
	/// </summary>
	public Dictionary<int, int> Inventory { get; set; } = new();
}
