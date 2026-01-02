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
		public Unit? GetUnit(int id)
		{
			return _units.TryGetValue(id, out var unit) ? unit : null;
		}

		/// <summary>
		/// 모든 유닛 제거
		/// </summary>
		public void ClearUnits()
		{
			_units.Clear();
		}

		/// <summary>
		/// JSON 파일에서 유닛 데이터 로드
		/// </summary>
		public UnitSystem UpdateFromFile(string filePath)
		{
			using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Read);
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

				// 태그 설정
				if (data.Tags != null)
				{
					unit.TraversalContext.SetTags(data.Tags);
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

				// 스케줄 스택 설정 (배열 순서대로 push - 첫 요소가 스택 바닥)
				foreach (var layerData in data.ScheduleStack)
				{
					DailySchedule? schedule = null;

					// 시간 기반 스케줄이 있으면 생성
					if (layerData.Schedule != null && layerData.Schedule.Length > 0)
					{
						schedule = new DailySchedule();
						foreach (var entry in layerData.Schedule)
						{
							schedule.AddEntry(
								entry.Name,
								entry.RegionId,
								entry.LocationId,
								entry.Start,
								entry.End,
								entry.Activity ?? ""
							);
						}
					}

					unit.PushSchedule(new ScheduleLayer
					{
						Name = layerData.Name,
						Schedule = schedule,
						EndConditionType = layerData.EndConditionType,
						EndConditionParam = layerData.EndConditionParam
					});
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

			using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Write);
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
				Tags = unit.TraversalContext.Tags.Count > 0
					? new Dictionary<string, int>(unit.TraversalContext.Tags)
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
				ScheduleStack = unit.ScheduleStack.Reverse().Select(layer => new ScheduleLayerJsonData
				{
					Name = layer.Name,
					Schedule = layer.Schedule?.Entries.Select(entry => new ScheduleEntryJsonData
					{
						Name = entry.Name,
						RegionId = entry.Location.RegionId,
						LocationId = entry.Location.LocalId,
						Start = entry.TimeRange.StartMinute,
						End = entry.TimeRange.EndMinute,
						Activity = string.IsNullOrEmpty(entry.Activity) ? null : entry.Activity
					}).ToArray(),
					EndConditionType = layer.EndConditionType,
					EndConditionParam = layer.EndConditionParam
				}).ToArray(),
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
			return type?.ToLower() switch
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
			using var file = FileAccess.Open(jsonFilePath, FileAccess.ModeFlags.Read);
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
				GD.Print($"    스케줄 스택: {unit.ScheduleStack.Count}개 레이어");
				if (unit.CurrentScheduleLayer != null)
				{
					var layer = unit.CurrentScheduleLayer;
					var scheduleInfo = layer.Schedule != null ? $"{layer.Schedule.Entries.Count}개 엔트리" : "없음";
					GD.Print($"    현재 레이어: {layer.Name} (스케줄: {scheduleInfo})");
				}
				if (unit.TraversalContext.Tags.Count > 0)
				{
					var tags = string.Join(", ", unit.TraversalContext.Tags.Select(t => $"{t.Key}:{t.Value}"));
					GD.Print($"    태그: {tags}");
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
