namespace Morld;

using System.Text.Json.Serialization;

/// <summary>
/// player_data.json 직렬화용 클래스
/// </summary>
internal class PlayerJsonData
{
	[JsonPropertyName("playerId")]
	public int PlayerId { get; set; } = 0;
}
