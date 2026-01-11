namespace Morld;

using System.Collections.Generic;
using System.Linq;

/// <summary>
/// 게임 이벤트 타입
/// </summary>
public enum EventType
{
	GameStart,       // 게임 시작
	OnReach,         // 위치 도착 (unit_id, region_id, location_id)
	OnMeet,          // 유닛들이 같은 위치에 있음 (unit_id1, unit_id2, ...)
	OnTimeElapsed,   // 시간 경과 (minutes)
	OnEquipChange,   // 장비 변경 (unit_id, item_id, is_equip)
}

/// <summary>
/// 게임 이벤트 데이터
/// Python으로 전달되는 이벤트 정보
/// </summary>
public class GameEvent
{
	/// <summary>
	/// 이벤트 타입
	/// </summary>
	public EventType Type { get; set; }

	/// <summary>
	/// 이벤트 인자 (타입별로 다름)
	/// </summary>
	public List<object> Args { get; set; } = new();

	/// <summary>
	/// Python 전달용 튜플 형식으로 변환
	/// 예: ("on_reach", 0, 0, 6)
	/// </summary>
	public List<object> ToPythonTuple()
	{
		var result = new List<object> { GetTypeName() };
		result.AddRange(Args);
		return result;
	}

	/// <summary>
	/// 이벤트 타입명 (Python 호환)
	/// </summary>
	private string GetTypeName() => Type switch
	{
		EventType.GameStart => "game_start",
		EventType.OnReach => "on_reach",
		EventType.OnMeet => "on_meet",
		EventType.OnTimeElapsed => "on_time_elapsed",
		EventType.OnEquipChange => "on_equip_change",
		_ => "unknown"
	};

	// === 팩토리 메서드 ===

	/// <summary>
	/// 게임 시작 이벤트
	/// </summary>
	public static GameEvent GameStart()
		=> new() { Type = EventType.GameStart };

	/// <summary>
	/// 위치 도착 이벤트
	/// </summary>
	public static GameEvent OnReach(int unitId, int regionId, int locationId)
		=> new() { Type = EventType.OnReach, Args = new List<object> { unitId, regionId, locationId } };

	/// <summary>
	/// 유닛 만남 이벤트
	/// </summary>
	public static GameEvent OnMeet(params int[] unitIds)
		=> new() { Type = EventType.OnMeet, Args = unitIds.Cast<object>().ToList() };

	/// <summary>
	/// 시간 경과 이벤트
	/// </summary>
	/// <param name="minutes">경과 시간 (분)</param>
	public static GameEvent OnTimeElapsed(int minutes)
		=> new() { Type = EventType.OnTimeElapsed, Args = new List<object> { minutes } };

	/// <summary>
	/// 장비 변경 이벤트
	/// </summary>
	/// <param name="unitId">유닛 ID</param>
	/// <param name="itemId">아이템 ID</param>
	/// <param name="isEquip">true: 장착, false: 해제</param>
	public static GameEvent OnEquipChange(int unitId, int itemId, bool isEquip)
		=> new() { Type = EventType.OnEquipChange, Args = new List<object> { unitId, itemId, isEquip } };

	public override string ToString()
		=> $"GameEvent({GetTypeName()}, [{string.Join(", ", Args)}])";
}
