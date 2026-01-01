namespace Morld;

using SE;

/// <summary>
/// 스케줄 스택의 한 레이어
/// - 일상 스케줄 (시간 기반)
/// - 이동 명령 (목표 위치)
/// - 따라가기 (목표 캐릭터)
/// </summary>
public class ScheduleLayer
{
	/// <summary>
	/// 레이어 이름 (예: "일상", "이동", "여행")
	/// </summary>
	public string Name { get; set; } = string.Empty;

	/// <summary>
	/// 시간 기반 스케줄 (null이면 단일 목표 모드)
	/// </summary>
	public DailySchedule? Schedule { get; set; }

	/// <summary>
	/// 종료 조건 타입 (문자열 기반 - JSON 저장 가능)
	/// "이동", "따라가기", "순찰" 등
	/// null이면 종료 조건 없음 (영구 스케줄)
	/// </summary>
	public string? EndConditionType { get; set; }

	/// <summary>
	/// 종료 조건 파라미터
	/// "이동": "regionId:localId" (예: "0:1")
	/// "따라가기": "characterId" (예: "3")
	/// "순찰": "0:1,0:2,0:3" (순환 경로)
	/// </summary>
	public string? EndConditionParam { get; set; }

	/// <summary>
	/// 종료 조건 충족 여부 확인
	/// </summary>
	public bool IsComplete(Character character, CharacterSystem? characterSystem)
	{
		if (string.IsNullOrEmpty(EndConditionType))
			return false; // 종료 조건 없음 = 영구 스케줄

		switch (EndConditionType)
		{
			case "이동":
				// param = "regionId:localId"
				var loc = ParseLocationRef(EndConditionParam);
				return loc.HasValue && character.CurrentLocation == loc.Value;

			case "따라가기":
				// param = "characterId"
				if (int.TryParse(EndConditionParam, out int targetId) && characterSystem != null)
				{
					var target = characterSystem.GetCharacter(targetId);
					return target != null && character.CurrentLocation == target.CurrentLocation;
				}
				return false;

			case "순찰":
				// 순찰은 영구적이므로 항상 false
				return false;

			default:
				return false;
		}
	}

	/// <summary>
	/// 위치 문자열 파싱 ("regionId:localId" → LocationRef)
	/// </summary>
	public static LocationRef? ParseLocationRef(string? param)
	{
		if (string.IsNullOrEmpty(param)) return null;

		var parts = param.Split(':');
		if (parts.Length >= 2 &&
			int.TryParse(parts[0], out int regionId) &&
			int.TryParse(parts[1], out int localId))
		{
			return new LocationRef(regionId, localId);
		}

		return null;
	}

	public override string ToString()
	{
		if (Schedule != null)
			return $"ScheduleLayer[{Name}] (시간 기반, {Schedule.Entries.Count}개 엔트리)";
		else if (!string.IsNullOrEmpty(EndConditionType))
			return $"ScheduleLayer[{Name}] ({EndConditionType}: {EndConditionParam})";
		else
			return $"ScheduleLayer[{Name}] (영구)";
	}
}
