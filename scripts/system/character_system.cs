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
		private readonly Dictionary<string, Character> _characters = new();

		public CharacterSystem()
		{
		}

		/// <summary>
		/// 모든 캐릭터 (읽기 전용)
		/// </summary>
		public IReadOnlyDictionary<string, Character> Characters => _characters;

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
		public bool RemoveCharacter(string id)
		{
			return _characters.Remove(id);
		}

		/// <summary>
		/// 캐릭터 찾기
		/// </summary>
		public Character? GetCharacter(string id)
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

				// 스케줄 설정
				foreach (var scheduleData in data.Schedule)
				{
					character.Schedule.AddEntry(
						scheduleData.Name,
						scheduleData.RegionId,
						scheduleData.LocationId,
						scheduleData.Start,
						scheduleData.End,
						scheduleData.Activity ?? ""
					);
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
				Schedule = character.Schedule.Entries.Select(entry => new ScheduleEntryJsonData
				{
					Name = entry.Name,
					RegionId = entry.Location.RegionId,
					LocationId = entry.Location.LocalId,
					Start = entry.TimeRange.StartMinute,
					End = entry.TimeRange.EndMinute,
					Activity = string.IsNullOrEmpty(entry.Activity) ? null : entry.Activity
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
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"  캐릭터 수: {_characters.Count}");
			foreach (var character in _characters.Values)
			{
				GD.Print($"  - {character}");
				GD.Print($"    스케줄: {character.Schedule.Entries.Count}개 항목");
				if (character.TraversalContext.Tags.Count > 0)
				{
					var tags = string.Join(", ", character.TraversalContext.Tags.Select(t => $"{t.Key}:{t.Value}"));
					GD.Print($"    태그: {tags}");
				}
			}
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}
	}
}