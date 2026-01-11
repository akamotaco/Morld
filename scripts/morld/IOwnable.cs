namespace Morld;

/// <summary>
/// 소유자를 가질 수 있는 객체를 위한 인터페이스 (Unit, Item, Location)
/// </summary>
public interface IOwnable
{
	/// <summary>
	/// 소유자의 unique_id (예: "sera", "mila")
	/// </summary>
	string? Owner { get; set; }

	/// <summary>
	/// 객체 이름
	/// </summary>
	string Name { get; }
}
