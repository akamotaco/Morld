using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace SE
{
	public class UnitSystem : ECS.System
	{
		private readonly Dictionary<int, Unit> _units = new();

		public UnitSystem()
		{
		}

		/// <summary>
		/// 모든 유닛 (읽기 전용)
		/// </summary>
		public IReadOnlyDictionary<int, Unit> Units => _units;

		/// <summary>
		/// 유닛 추가
		/// </summary>
		public void AddUnit(Unit unit)
		{
			if (unit == null)
				throw new ArgumentNullException(nameof(unit));

			_units[unit.Id] = unit;
		}

		/// <summary>
		/// 유닛 제거
		/// </summary>
		public bool RemoveUnit(int id)
		{
			return _units.Remove(id);
		}

		/// <summary>
		/// 유닛 찾기
		/// </summary>
		public Unit? FindUnit(int id)
		{
			return _units.TryGetValue(id, out var unit) ? unit : null;
		}

		/// <summary>
		/// UniqueId로 유닛 찾기
		/// </summary>
		public Unit? FindByUniqueId(string uniqueId)
		{
			if (string.IsNullOrEmpty(uniqueId))
				return null;

			foreach (var unit in _units.Values)
			{
				if (unit.UniqueId == uniqueId)
					return unit;
			}
			return null;
		}

		/// <summary>
		/// 모든 유닛 제거
		/// </summary>
		public void ClearUnits()
		{
			_units.Clear();
		}

		/// <summary>
		/// 모든 유닛 제거 (챕터 전환용 alias)
		/// </summary>
		public void Clear()
		{
			ClearUnits();
			GD.Print("[UnitSystem] All units cleared.");
		}

		/// <summary>
		/// JSON 파일에서 유닛 데이터 로드
		/// </summary>
		public UnitSystem UpdateFromFile(string filePath)
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
		/// JSON 문자열에서 유닛 데이터 로드
		/// </summary>
		public void UpdateFromJson(string json)
		{
			var options = new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true,
				WriteIndented = true
			};

			var dataList = JsonSerializer.Deserialize<UnitJsonData[]>(json, options);
			if (dataList == null)
				throw new InvalidOperationException("Failed to parse Unit JSON data");

			UpdateFromData(dataList);
		}

		/// <summary>
		/// UnitJsonData 배열로 유닛 데이터 로드
		/// </summary>
		private void UpdateFromData(UnitJsonData[] dataList)
		{
			// 기존 유닛 모두 제거
			ClearUnits();

			// 새 유닛 생성 및 추가
			foreach (var data in dataList)
			{
				var unit = new Unit(data.Id, data.Name, data.RegionId, data.LocationId);

				// Props 설정
				if (data.Tags != null)
				{
					unit.TraversalContext.SetProps(data.Tags);
				}

				// 타입 설정
				unit.Type = ParseUnitType(data.Type);

				// 액션 설정
				if (data.Actions != null)
				{
					unit.Actions.AddRange(data.Actions);
				}

				// Appearance 설정
				if (data.Appearance != null)
				{
					foreach (var (key, value) in data.Appearance)
					{
						unit.Appearance[key] = value;
					}
				}

				// Mood 설정
				if (data.Mood != null)
				{
					foreach (var mood in data.Mood)
					{
						unit.Mood.Add(mood);
					}
				}

				// CurrentEdge 설정 (이동 중 상태 복원)
				if (data.CurrentEdge != null)
				{
					unit.CurrentEdge = new EdgeProgress
					{
						From = new LocationRef(data.CurrentEdge.FromRegionId, data.CurrentEdge.FromLocalId),
						To = new LocationRef(data.CurrentEdge.ToRegionId, data.CurrentEdge.ToLocalId),
						TotalTime = data.CurrentEdge.TotalTime,
						ElapsedTime = data.CurrentEdge.ElapsedTime
					};
				}

				AddUnit(unit);
			}
		}

		/// <summary>
		/// 현재 유닛 데이터를 JSON 파일로 저장
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
		/// 현재 유닛 데이터를 JSON 문자열로 변환
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
		/// UnitJsonData 배열로 변환
		/// 주의: Inventory와 EquippedItems는 InventorySystem에서 저장됨
		/// </summary>
		private UnitJsonData[] ExportToData()
		{
			return _units.Values.Select(unit => new UnitJsonData
			{
				Id = unit.Id,
				Name = unit.Name,
				RegionId = unit.CurrentLocation.RegionId,
				LocationId = unit.CurrentLocation.LocalId,
				Tags = unit.TraversalContext.Props.Count > 0
					? unit.TraversalContext.Props.ToDictionary()
					: null,
				Type = unit.Type.ToString().ToLower(),
				Actions = unit.Actions.Count > 0
					? new List<string>(unit.Actions)
					: null,
				Appearance = unit.Appearance.Count > 0
					? new Dictionary<string, string>(unit.Appearance)
					: null,
				Mood = unit.Mood.Count > 0
					? new List<string>(unit.Mood)
					: null,
				CurrentEdge = unit.CurrentEdge != null
					? new EdgeProgressJsonData
					{
						FromRegionId = unit.CurrentEdge.From.RegionId,
						FromLocalId = unit.CurrentEdge.From.LocalId,
						ToRegionId = unit.CurrentEdge.To.RegionId,
						ToLocalId = unit.CurrentEdge.To.LocalId,
						TotalTime = unit.CurrentEdge.TotalTime,
						ElapsedTime = unit.CurrentEdge.ElapsedTime
					}
					: null
			}).ToArray();
		}

		/// <summary>
		/// 문자열을 UnitType으로 변환
		/// </summary>
		private static UnitType ParseUnitType(string type)
		{
			return type.ToLower() switch
			{
				"male" => UnitType.Male,
				"female" => UnitType.Female,
				"object" => UnitType.Object,
				_ => UnitType.Male // 기본값
			};
		}

		/// <summary>
		/// JSON에서 읽은 인벤토리 데이터를 InventorySystem으로 마이그레이션
		/// (초기 로드 시 한번만 호출)
		/// </summary>
		public void MigrateInventoryData(string jsonFilePath, InventorySystem inventorySystem)
		{
			using var file = Godot.FileAccess.Open(jsonFilePath, Godot.FileAccess.ModeFlags.Read);
			if (file == null) return;

			var json = file.GetAsText();
			var options = new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true
			};

			var dataList = JsonSerializer.Deserialize<UnitJsonData[]>(json, options);
			if (dataList == null) return;

			foreach (var data in dataList)
			{
				// 인벤토리 마이그레이션
				if (data.Inventory != null)
				{
					foreach (var (itemId, count) in data.Inventory)
					{
						inventorySystem.AddItemToUnit(data.Id, itemId, count);
					}
				}

				// 장착 아이템 마이그레이션
				if (data.EquippedItems != null)
				{
					foreach (var itemId in data.EquippedItems)
					{
						inventorySystem.EquipItemOnUnit(data.Id, itemId);
					}
				}
			}

#if DEBUG_LOG
			GD.Print($"[UnitSystem] 인벤토리 데이터 마이그레이션 완료");
#endif
		}

		/// <summary>
		/// 디버그용 유닛 정보 출력
		/// </summary>
		public void DebugPrint()
		{
			var characters = _units.Values.Where(u => !u.IsObject).ToList();
			var objects = _units.Values.Where(u => u.IsObject).ToList();

			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"  캐릭터 수: {characters.Count}, 오브젝트 수: {objects.Count}");
			foreach (var unit in characters)
			{
				GD.Print($"  - {unit}");
				GD.Print($"    JobList: {unit.JobList.Count}개 Job");
				if (unit.CurrentJob != null)
				{
					GD.Print($"    현재 Job: {unit.CurrentJob.Name} ({unit.CurrentJob.Action}, {unit.CurrentJob.Duration}분)");
				}
				if (unit.TraversalContext.Props.Count > 0)
				{
					var props = string.Join(", ", unit.TraversalContext.Props.ToDictionary().Select(t => $"{t.Key}={t.Value}"));
					GD.Print($"    Props: {props}");
				}
				if (unit.Actions.Count > 0)
				{
					GD.Print($"    액션: {string.Join(", ", unit.Actions)}");
				}
			}
			foreach (var obj in objects)
			{
				GD.Print($"  - [Object] {obj.Name} @ {obj.CurrentLocation}");
				if (obj.Actions.Count > 0)
				{
					GD.Print($"    액션: {string.Join(", ", obj.Actions)}");
				}
			}
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}
	}
}
