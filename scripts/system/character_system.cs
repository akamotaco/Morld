using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace SE
{
	public class CharacterSystem : ECS.System
	{
		private readonly Dictionary<int, Character> _characters = new();

		public CharacterSystem()
		{
		}

		/// <summary>
		/// 모든 캐릭터 (읽기 전용)
		/// </summary>
		public IReadOnlyDictionary<int, Character> Characters => _characters;

		/// <summary>
		/// 캐릭터 추가
		/// </summary>
		public void AddCharacter(Character character)
		{
			if (character == null)
				throw new ArgumentNullException(nameof(character));

			_characters[character.Id] = character;
		}

		/// <summary>
		/// 캐릭터 제거
		/// </summary>
		public bool RemoveCharacter(int id)
		{
			return _characters.Remove(id);
		}

		/// <summary>
		/// 캐릭터 찾기
		/// </summary>
		public Character? GetCharacter(int id)
		{
			return _characters.TryGetValue(id, out var character) ? character : null;
		}

		/// <summary>
		/// 모든 캐릭터 제거
		/// </summary>
		public void ClearCharacters()
		{
			_characters.Clear();
		}

		/// <summary>
		/// JSON 파일에서 캐릭터 데이터 로드
		/// </summary>
		public CharacterSystem UpdateFromFile(string filePath)
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
		/// JSON 문자열에서 캐릭터 데이터 로드
		/// </summary>
		public void UpdateFromJson(string json)
		{
			var options = new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true,
				WriteIndented = true
			};

			var dataList = JsonSerializer.Deserialize<CharacterJsonData[]>(json, options);
			if (dataList == null)
				throw new InvalidOperationException("Failed to parse Character JSON data");

			UpdateFromData(dataList);
		}

		/// <summary>
		/// CharacterJsonData 배열로 캐릭터 데이터 로드
		/// </summary>
		private void UpdateFromData(CharacterJsonData[] dataList)
		{
			// 기존 캐릭터 모두 제거
			ClearCharacters();

			// 새 캐릭터 생성 및 추가
			foreach (var data in dataList)
			{
				var character = new Character(data.Id, data.Name, data.RegionId, data.LocationId);

				// 태그 설정
				if (data.Tags != null)
				{
					character.TraversalContext.SetTags(data.Tags);
				}

				// 인벤토리 설정
				if (data.Inventory != null)
				{
					foreach (var (itemId, count) in data.Inventory)
					{
						character.Inventory[itemId] = count;
					}
				}

				// 장착 아이템 설정
				if (data.EquippedItems != null)
				{
					character.EquippedItems.AddRange(data.EquippedItems);
				}

				// 오브젝트 여부 설정
				character.IsObject = data.IsObject;

				// 상호작용/행동 설정
				if (data.Interactions != null)
				{
					character.Interactions.AddRange(data.Interactions);
				}
				if (data.Actions != null)
				{
					character.Actions.AddRange(data.Actions);
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

					character.PushSchedule(new ScheduleLayer
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
					character.CurrentEdge = new EdgeProgress
					{
						From = new LocationRef(data.CurrentEdge.FromRegionId, data.CurrentEdge.FromLocalId),
						To = new LocationRef(data.CurrentEdge.ToRegionId, data.CurrentEdge.ToLocalId),
						TotalTime = data.CurrentEdge.TotalTime,
						ElapsedTime = data.CurrentEdge.ElapsedTime
					};
				}

				AddCharacter(character);
			}
		}

		/// <summary>
		/// 현재 캐릭터 데이터를 JSON 파일로 저장
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
		/// 현재 캐릭터 데이터를 JSON 문자열로 변환
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
		/// CharacterJsonData 배열로 변환
		/// </summary>
		private CharacterJsonData[] ExportToData()
		{
			return _characters.Values.Select(character => new CharacterJsonData
			{
				Id = character.Id,
				Name = character.Name,
				RegionId = character.CurrentLocation.RegionId,
				LocationId = character.CurrentLocation.LocalId,
				Tags = character.TraversalContext.Tags.Count > 0
					? new Dictionary<string, int>(character.TraversalContext.Tags)
					: null,
				Inventory = character.Inventory.Count > 0
					? new Dictionary<int, int>(character.Inventory)
					: null,
				EquippedItems = character.EquippedItems.Count > 0
					? new List<int>(character.EquippedItems)
					: null,
				IsObject = character.IsObject,
				Interactions = character.Interactions.Count > 0
					? new List<string>(character.Interactions)
					: null,
				Actions = character.Actions.Count > 0
					? new List<string>(character.Actions)
					: null,
				ScheduleStack = character.ScheduleStack.Reverse().Select(layer => new ScheduleLayerJsonData
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
				CurrentEdge = character.CurrentEdge != null
					? new EdgeProgressJsonData
					{
						FromRegionId = character.CurrentEdge.From.RegionId,
						FromLocalId = character.CurrentEdge.From.LocalId,
						ToRegionId = character.CurrentEdge.To.RegionId,
						ToLocalId = character.CurrentEdge.To.LocalId,
						TotalTime = character.CurrentEdge.TotalTime,
						ElapsedTime = character.CurrentEdge.ElapsedTime
					}
					: null
			}).ToArray();
		}

		/// <summary>
		/// 디버그용 캐릭터 정보 출력
		/// </summary>
		public void DebugPrint()
		{
			var characters = _characters.Values.Where(c => !c.IsObject).ToList();
			var objects = _characters.Values.Where(c => c.IsObject).ToList();

			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"  캐릭터 수: {characters.Count}, 오브젝트 수: {objects.Count}");
			foreach (var character in characters)
			{
				GD.Print($"  - {character}");
				GD.Print($"    스케줄 스택: {character.ScheduleStack.Count}개 레이어");
				if (character.CurrentScheduleLayer != null)
				{
					var layer = character.CurrentScheduleLayer;
					var scheduleInfo = layer.Schedule != null ? $"{layer.Schedule.Entries.Count}개 엔트리" : "없음";
					GD.Print($"    현재 레이어: {layer.Name} (스케줄: {scheduleInfo})");
				}
				if (character.TraversalContext.Tags.Count > 0)
				{
					var tags = string.Join(", ", character.TraversalContext.Tags.Select(t => $"{t.Key}:{t.Value}"));
					GD.Print($"    태그: {tags}");
				}
			}
			foreach (var obj in objects)
			{
				GD.Print($"  - [Object] {obj.Name} @ {obj.CurrentLocation}");
				if (obj.Inventory.Count > 0)
				{
					var items = string.Join(", ", obj.Inventory.Select(i => $"아이템{i.Key}x{i.Value}"));
					GD.Print($"    인벤토리: {items}");
				}
			}
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}
	}
}