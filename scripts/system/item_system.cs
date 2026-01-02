using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace SE
{
	public class ItemSystem : ECS.System
	{
		private readonly Dictionary<int, Item> _items = new();

		public ItemSystem()
		{
		}

		/// <summary>
		/// 모든 아이템 (읽기 전용)
		/// </summary>
		public IReadOnlyDictionary<int, Item> Items => _items;

		/// <summary>
		/// 아이템 추가
		/// </summary>
		public void AddItem(Item item)
		{
			if (item == null)
				throw new ArgumentNullException(nameof(item));

			_items[item.Id] = item;
		}

		/// <summary>
		/// 아이템 제거
		/// </summary>
		public bool RemoveItem(int id)
		{
			return _items.Remove(id);
		}

		/// <summary>
		/// 아이템 찾기
		/// </summary>
		public Item? GetItem(int id)
		{
			return _items.TryGetValue(id, out var item) ? item : null;
		}

		/// <summary>
		/// 모든 아이템 제거
		/// </summary>
		public void ClearItems()
		{
			_items.Clear();
		}

		/// <summary>
		/// JSON 파일에서 아이템 데이터 로드
		/// </summary>
		public ItemSystem UpdateFromFile(string filePath)
		{
			using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
			if (file == null)
			{
				throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
			}
			var json = file.GetAsText();
			UpdateFromJson(json);
			return this;
		}

		/// <summary>
		/// JSON 문자열에서 아이템 데이터 로드
		/// </summary>
		public void UpdateFromJson(string json)
		{
			var options = new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true,
				WriteIndented = true
			};

			var dataList = JsonSerializer.Deserialize<ItemJsonData[]>(json, options);
			if (dataList == null)
				throw new InvalidOperationException("Failed to parse Item JSON data");

			UpdateFromData(dataList);
		}

		/// <summary>
		/// ItemJsonData 배열로 아이템 데이터 로드
		/// </summary>
		private void UpdateFromData(ItemJsonData[] dataList)
		{
			// 기존 아이템 모두 제거
			ClearItems();

			// 새 아이템 생성 및 추가
			foreach (var data in dataList)
			{
				var item = new Item(data.Id, data.Name);

				// PassiveTags 설정
				if (data.PassiveTags != null)
				{
					foreach (var (tag, value) in data.PassiveTags)
					{
						item.PassiveTags[tag] = value;
					}
				}

				// EquipTags 설정
				if (data.EquipTags != null)
				{
					foreach (var (tag, value) in data.EquipTags)
					{
						item.EquipTags[tag] = value;
					}
				}

				// Value 설정
				item.Value = data.Value;

				// Actions 설정
				if (data.Actions != null)
				{
					item.Actions.AddRange(data.Actions);
				}

				AddItem(item);
			}
		}

		/// <summary>
		/// 현재 아이템 데이터를 JSON 파일로 저장
		/// </summary>
		public void SaveToFile(string filePath)
		{
			var json = ToJson();

			using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Write);
			if (file == null)
			{
				throw new InvalidOperationException($"Failed to open file for writing: {filePath}");
			}
			file.StoreString(json);
		}

		/// <summary>
		/// 현재 아이템 데이터를 JSON 문자열로 변환
		/// </summary>
		public string ToJson()
		{
			var data = ExportToData();

			var options = new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true,
				WriteIndented = true
			};

			return JsonSerializer.Serialize(data, options);
		}

		/// <summary>
		/// ItemJsonData 배열로 변환
		/// </summary>
		private ItemJsonData[] ExportToData()
		{
			return _items.Values.Select(item => new ItemJsonData
			{
				Id = item.Id,
				Name = item.Name,
				PassiveTags = item.PassiveTags.Count > 0
					? new Dictionary<string, int>(item.PassiveTags)
					: null,
				EquipTags = item.EquipTags.Count > 0
					? new Dictionary<string, int>(item.EquipTags)
					: null,
				Value = item.Value,
				Actions = item.Actions.Count > 0
					? new List<string>(item.Actions)
					: null
			}).ToArray();
		}

		/// <summary>
		/// 디버그용 아이템 정보 출력
		/// </summary>
		public void DebugPrint()
		{
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"  아이템 수: {_items.Count}");
			foreach (var item in _items.Values)
			{
				GD.Print($"  - {item}");
				if (item.PassiveTags.Count > 0)
				{
					var tags = string.Join(", ", item.PassiveTags.Select(t => $"{t.Key}:{t.Value}"));
					GD.Print($"    PassiveTags: {tags}");
				}
				if (item.EquipTags.Count > 0)
				{
					var tags = string.Join(", ", item.EquipTags.Select(t => $"{t.Key}:{t.Value}"));
					GD.Print($"    EquipTags: {tags}");
				}
			}
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}
	}
}
