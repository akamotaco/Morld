using System.Collections.Generic;

namespace Morld;

/// <summary>
/// 액션 제공자 인터페이스
/// ECS System이 이 인터페이스를 구현하면 플레이어에게 추가 행동을 제공할 수 있음
/// </summary>
public interface IActionProvider
{
	/// <summary>
	/// 프로바이더 고유 ID (시스템 식별용)
	/// </summary>
	string ProviderId { get; }

	/// <summary>
	/// 해당 유닛에게 제공할 액션 목록 반환
	/// </summary>
	/// <param name="unit">대상 유닛</param>
	/// <returns>제공 가능한 액션 목록 (빈 목록 = 제공 안함)</returns>
	List<ProvidedAction> GetActionsFor(Unit unit);
}

/// <summary>
/// 프로바이더가 제공하는 액션 정보
/// </summary>
public class ProvidedAction
{
	/// <summary>
	/// 액션 타입 (simple, toggle)
	/// </summary>
	public string Type { get; set; } = "simple";

	/// <summary>
	/// 표시 이름
	/// </summary>
	public string Name { get; set; } = "";

	/// <summary>
	/// 클릭 시 실행할 액션 (URL meta)
	/// simple 타입일 때 사용
	/// </summary>
	public string Action { get; set; } = "";

	/// <summary>
	/// 토글 ID (toggle 타입일 때 사용)
	/// </summary>
	public string? ToggleId { get; set; }

	/// <summary>
	/// 하위 옵션 목록 (toggle 타입일 때 사용)
	/// </summary>
	public List<ActionOption>? Options { get; set; }

	/// <summary>
	/// 들여쓰기 레벨 (0 = 최상위)
	/// </summary>
	public int IndentLevel { get; set; } = 0;

	/// <summary>
	/// BBCode로 변환
	/// </summary>
	public string ToBBCode()
	{
		var indent = new string(' ', (IndentLevel + 1) * 2);

		if (Type == "toggle" && ToggleId != null && Options != null)
		{
			var lines = new List<string>
			{
				$"{indent}[url=toggle:{ToggleId}]▶ {Name}[/url][hidden={ToggleId}]"
			};

			foreach (var option in Options)
			{
				lines.Add($"{indent}  [url={option.Action}]{option.Label}[/url]");
			}

			lines.Add($"{indent}[/hidden={ToggleId}]");
			return string.Join("\n", lines);
		}

		// simple 타입
		return $"{indent}[url={Action}]{Name}[/url]";
	}
}

/// <summary>
/// 토글 메뉴의 하위 옵션
/// </summary>
public class ActionOption
{
	/// <summary>
	/// 표시 라벨
	/// </summary>
	public string Label { get; set; } = "";

	/// <summary>
	/// 클릭 시 실행할 액션 (URL meta)
	/// </summary>
	public string Action { get; set; } = "";
}
