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
	Monologue    // 모놀로그 (독백/나레이션)
}

/// <summary>
/// 모놀로그 버튼 타입 (Win32 MessageBox 스타일)
/// </summary>
public enum MonologueButtonType
{
	Ok,          // [확인] - 기본값, 마지막 페이지에서 DoneCallback 호출
	None,        // 버튼 없음 (선택지가 페이지에 포함된 경우)
	YesNo        // [승낙] [거절] - DoneCallback/CancelCallback 호출
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
	/// 유닛 ID (Unit, Item 타입에서 사용)
	/// </summary>
	public int? UnitId { get; set; }

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
	/// 모놀로그 페이지 목록 (Monologue 타입에서 사용)
	/// </summary>
	public List<string>? MonologuePages { get; set; }

	/// <summary>
	/// 모놀로그 완료 시 소요 시간 (Monologue 타입에서 사용)
	/// </summary>
	public int MonologueTimeConsumed { get; set; } = 0;

	/// <summary>
	/// 현재 페이지 인덱스 (Monologue 타입에서 사용)
	/// </summary>
	public int CurrentPage { get; set; } = 0;

	/// <summary>
	/// 모놀로그 버튼 타입 (Monologue 타입에서 사용)
	/// </summary>
	public MonologueButtonType MonologueButtonType { get; set; } = MonologueButtonType.Ok;

	/// <summary>
	/// 완료 콜백 (Ok/YesNo 타입에서 사용, 형식: "함수명:인자1:인자2")
	/// Ok: [확인] 클릭 시, YesNo: [승낙] 클릭 시 호출
	/// </summary>
	public string? DoneCallback { get; set; }

	/// <summary>
	/// 취소 콜백 (YesNo 타입에서 사용, 형식: "함수명:인자1:인자2")
	/// [거절] 클릭 시 호출 (없으면 단순 Pop)
	/// </summary>
	public string? CancelCallback { get; set; }

	/// <summary>
	/// 펼쳐진 토글 ID 목록
	/// </summary>
	public HashSet<string> ExpandedToggles { get; set; } = new();

	// 팩토리 메서드들
	public static Focus Situation() => new() { Type = FocusType.Situation };
	public static Focus Unit(int unitId) => new() { Type = FocusType.Unit, UnitId = unitId };
	public static Focus Inventory() => new() { Type = FocusType.Inventory };
	public static Focus Item(int itemId, string context, int? unitId = null)
		=> new() { Type = FocusType.Item, ItemId = itemId, Context = context, UnitId = unitId };
	public static Focus Result(string message) => new() { Type = FocusType.Result, Message = message };
	public static Focus Monologue(List<string> pages, int timeConsumed, MonologueButtonType buttonType = MonologueButtonType.Ok, string? doneCallback = null, string? cancelCallback = null)
		=> new() { Type = FocusType.Monologue, MonologuePages = pages, MonologueTimeConsumed = timeConsumed, CurrentPage = 0, MonologueButtonType = buttonType, DoneCallback = doneCallback, CancelCallback = cancelCallback };
}
