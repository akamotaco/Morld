namespace Morld;

using System.Collections.Generic;

/// <summary>
/// Item (아이템)
/// </summary>
public class Item
{
	private readonly int _id;

	/// <summary>
	/// Item 고유 ID
	/// </summary>
	public int Id => _id;

	/// <summary>
	/// Item 이름
	/// </summary>
	public string Name { get; set; }

	/// <summary>
	/// 소유만으로 효과가 있는 태그 (예: 열쇠)
	/// </summary>
	public Dictionary<string, int> PassiveTags { get; set; } = new();

	/// <summary>
	/// 장착해야 효과가 있는 태그 (예: 망원경 +관찰)
	/// </summary>
	public Dictionary<string, int> EquipTags { get; set; } = new();

	/// <summary>
	/// 아이템 가치 (거래용)
	/// </summary>
	public int Value { get; set; } = 0;

	public Item(int id, string name)
	{
		_id = id;
		Name = name ?? throw new System.ArgumentNullException(nameof(name));
	}

	public override string ToString()
	{
		return $"Item[{Id}] {Name}";
	}
}
