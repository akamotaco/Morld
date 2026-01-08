using System.Collections.Generic;

namespace Morld;

/// <summary>
/// 포커스 타입
/// </summary>
public enum FocusType
{
	Situation,   // 상황 화면 (location)
	Unit,        // 유닛/오브젝트 화면
	Inventory,   // 플레이어 인벤토리
	Item,        // 아이템 메뉴
	Result,      // 결과 메시지
	Dialog       // 다이얼로그 (morld.dialog() API, BBCode URL 기반)
}

/// <summary>
/// UI 포커스 정보 (스택의 각 요소)
/// </summary>
public class Focus
{
	/// <summary>
	/// 포커스 타입
	/// </summary>
	public FocusType Type { get; set; } = FocusType.Situation;

	/// <summary>
	/// 대상 유닛 ID
	/// - Unit 타입: 살펴보는 유닛
	/// - Item 타입: 아이템 이동 대상 (container에서 가져오기, inventory에서 넣기)
	/// - Inventory 타입: 넣기 대상 유닛 (설정 시 아이템 클릭하면 바로 넣기)
	/// </summary>
	public int? TargetUnitId { get; set; }

	/// <summary>
	/// 아이템 ID (Item 타입에서 사용)
	/// </summary>
	public int? ItemId { get; set; }

	/// <summary>
	/// 아이템 컨텍스트 (Item 타입에서 사용: "ground", "inventory", "container")
	/// </summary>
	public string? Context { get; set; }

	/// <summary>
	/// 결과 메시지 (Result 타입에서 사용)
	/// </summary>
	public string? Message { get; set; }

	/// <summary>
	/// 펼쳐진 토글 ID 목록
	/// </summary>
	public HashSet<string> ExpandedToggles { get; set; } = new();

	/// <summary>
	/// 다이얼로그 텍스트 (Dialog 타입에서 사용)
	/// BBCode URL 포함 (@ret:값, @proc:값 패턴)
	/// </summary>
	public string? DialogText { get; set; }

	/// <summary>
	/// 다이얼로그 완료 시 소요 시간 (Dialog 타입에서 사용)
	/// </summary>
	public int TimeConsumed { get; set; } = 0;

	// 팩토리 메서드들
	public static Focus Situation() => new() { Type = FocusType.Situation };
	public static Focus Unit(int unitId) => new() { Type = FocusType.Unit, TargetUnitId = unitId };
	public static Focus Inventory(int? targetUnitId = null) => new() { Type = FocusType.Inventory, TargetUnitId = targetUnitId };
	public static Focus Item(int itemId, string context, int? unitId = null)
		=> new() { Type = FocusType.Item, ItemId = itemId, Context = context, TargetUnitId = unitId };
	public static Focus Result(string message) => new() { Type = FocusType.Result, Message = message };
	public static Focus Dialog(string text, int timeConsumed = 0)
		=> new() { Type = FocusType.Dialog, DialogText = text, TimeConsumed = timeConsumed };
}
