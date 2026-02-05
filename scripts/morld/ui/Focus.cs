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
	Dialog,      // 다이얼로그 (morld.dialog() API, BBCode URL 기반)
	Animation    // 애니메이션 시퀀스 (morld.animlog() API, 실시간 기반)
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

	/// <summary>
	/// 자동 시간 흐름 허용 여부 (Dialog 타입에서 사용)
	/// - true: 이 Focus가 활성화된 동안 자동 시간 흐름 계속 (지도 보기 등)
	/// - false: 이 Focus가 활성화된 동안 자동 시간 흐름 정지 (대화, 이벤트 등)
	/// 기본값: false (대부분의 다이얼로그는 시간 정지)
	///
	/// [미구현] 시간이 흐르는 동안 이벤트(on_meet 등)가 발생하면:
	/// - 새 이벤트 다이얼로그가 스택에 push됨
	/// - 현재 Focus는 중단되고 대기
	/// - 이벤트에서 현재 아이템을 뺏거나 상태를 변경하면 Focus도 영향받을 수 있음
	/// </summary>
	public bool TimeFlows { get; set; } = false;

	/// <summary>
	/// 애니메이션 요청 (Animation 타입에서 사용)
	/// </summary>
	public PyAnimlogRequest? AnimlogRequest { get; set; }

	// 팩토리 메서드들
	public static Focus Situation() => new() { Type = FocusType.Situation };
	public static Focus Unit(int unitId) => new() { Type = FocusType.Unit, TargetUnitId = unitId };
	public static Focus Inventory(int? targetUnitId = null) => new() { Type = FocusType.Inventory, TargetUnitId = targetUnitId };
	public static Focus Item(int itemId, string context, int? unitId = null)
		=> new() { Type = FocusType.Item, ItemId = itemId, Context = context, TargetUnitId = unitId };
	public static Focus Result(string message) => new() { Type = FocusType.Result, Message = message };
	public static Focus Dialog(string text, int timeConsumed = 0, bool timeFlows = false)
		=> new() { Type = FocusType.Dialog, DialogText = text, TimeConsumed = timeConsumed, TimeFlows = timeFlows };
	public static Focus Animation(PyAnimlogRequest request)
		=> new() { Type = FocusType.Animation, AnimlogRequest = request };
}
