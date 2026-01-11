namespace Morld;

using System.Collections.Generic;

/// <summary>
/// Item (아이템)
/// </summary>
public class Item : IOwnable
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
	/// Python Asset의 unique_id (예: "apple", "bread")
	/// </summary>
	public string UniqueId { get; set; }

	/// <summary>
	/// 소유만으로 효과가 있는 Prop (예: 열쇠)
	/// </summary>
	public Dictionary<string, int> PassiveProps { get; set; } = new();

	/// <summary>
	/// 장착해야 효과가 있는 Prop (예: 망원경 +관찰)
	/// </summary>
	public Dictionary<string, int> EquipProps { get; set; } = new();

	/// <summary>
	/// 아이템 가치 (거래용)
	/// </summary>
	public int Value { get; set; } = 0;

	/// <summary>
	/// 가능한 액션 (예: "pickup", "drop", "use", "combine")
	/// </summary>
	public List<string> Actions { get; set; } = new();

	/// <summary>
	/// 액션별 활성화 상태 (action:액션명@컨텍스트 = 값)
	/// 값이 1 이상이면 활성화, 0 이하면 비활성화
	/// 예: {"take@container": 1, "equip@inventory": 1, "put": 1}
	/// </summary>
	public Dictionary<string, int> ActionProps { get; set; } = new();

	/// <summary>
	/// 소유자 unique_id (예: "sera", "mila") - null이면 공용 아이템
	/// </summary>
	public string Owner { get; set; }

	public Item(int id, string name)
	{
		_id = id;
		Name = name ?? throw new System.ArgumentNullException(nameof(name));
	}

	public override string ToString()
	{
		return $"Item[{Id}] {Name}";
	}

	/// <summary>
	/// EquipProps에서 특정 prefix로 시작하는 키 반환
	/// </summary>
	/// <param name="prefix">검색할 prefix (예: "장착:")</param>
	/// <returns>해당 키 (예: "장착:손") 또는 null</returns>
	public string GetEquipPropKey(string prefix)
	{
		if (EquipProps == null || EquipProps.Count == 0)
			return null;

		foreach (var key in EquipProps.Keys)
		{
			if (key.StartsWith(prefix))
				return key;
		}
		return null;
	}
}
