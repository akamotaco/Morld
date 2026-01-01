using ECS;
using Morld;
using System;
using System.Collections.Generic;
using System.Linq;

namespace SE
{
	/// <summary>
	/// 묘사 텍스트 생성을 담당하는 Logic System
	/// </summary>
	public class DescribeSystem : ECS.System
	{
		public DescribeSystem()
		{
		}

		/// <summary>
		/// Location 묘사 반환
		/// </summary>
		public string GetLocationDescription(Location? location, GameTime? time)
		{
			if (location == null) return "";
			return SelectDescription(location.Description, time);
		}

		/// <summary>
		/// Region 묘사 반환
		/// </summary>
		public string GetRegionDescription(Region? region, GameTime? time)
		{
			if (region == null) return "";
			return SelectDescription(region.Description, time);
		}

		/// <summary>
		/// Character 묘사 반환 (향후 확장)
		/// </summary>
		public string GetCharacterDescription(Character? character, GameTime? time)
		{
			// 기본: 이름 + 활동
			// 향후: LLM으로 풍성한 묘사 생성
			return character?.Name ?? "";
		}

		/// <summary>
		/// Description Dictionary에서 적절한 키 선택
		/// </summary>
		private string SelectDescription(Dictionary<string, string>? descriptions, GameTime? time)
		{
			if (descriptions == null || descriptions.Count == 0)
				return "";

			if (time == null)
			{
				return descriptions.TryGetValue("default", out var defaultDesc) ? defaultDesc : "";
			}

			var currentTags = time.GetCurrentTags();

			string bestKey = "default";
			int bestMatchCount = 0;

			foreach (var (key, _) in descriptions)
			{
				if (key == "default") continue;

				var keyTags = key.Split(',').Select(t => t.Trim()).ToHashSet();
				var matchCount = keyTags.Intersect(currentTags).Count();

				// 모든 키 태그가 현재 태그에 포함되어야 함
				if (matchCount == keyTags.Count && matchCount > bestMatchCount)
				{
					bestMatchCount = matchCount;
					bestKey = key;
				}
			}

			return descriptions.TryGetValue(bestKey, out var desc) ? desc : "";
		}

		/// <summary>
		/// LookResult를 기반으로 전체 상황 설명 텍스트 생성
		/// </summary>
		public string GetSituationText(LookResult lookResult, GameTime? time)
		{
			var lines = new List<string>();

			// 1. 위치 정보
			var loc = lookResult.Location;
			if (!string.IsNullOrEmpty(loc.RegionName))
			{
				lines.Add($"[b]{loc.RegionName} - {loc.LocationName}[/b]");
			}
			else if (!string.IsNullOrEmpty(loc.LocationName))
			{
				lines.Add($"[b]{loc.LocationName}[/b]");
			}

			// 2. 시간 정보
			if (time != null)
			{
				lines.Add($"{time}");
			}

			lines.Add("");

			// 3. 위치 묘사
			if (!string.IsNullOrEmpty(loc.DescriptionText))
			{
				lines.Add(loc.DescriptionText);
				lines.Add("");
			}

			// 4. 주변 캐릭터
			if (lookResult.CharacterIds.Count > 0)
			{
				var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
				if (characterSystem != null)
				{
					lines.Add("[color=yellow]주변 인물:[/color]");
					foreach (var id in lookResult.CharacterIds)
					{
						var character = characterSystem.GetCharacter(id);
						if (character != null)
						{
							lines.Add($"  - {character.Name}");
						}
					}
					lines.Add("");
				}
			}

			// 5. 이동 가능 경로 (BBCode 링크)
			if (lookResult.Routes.Count > 0)
			{
				lines.Add("[color=cyan]이동 가능:[/color]");
				foreach (var route in lookResult.Routes)
				{
					if (route.IsBlocked)
					{
						lines.Add($"  [color=gray]- {route.LocationName} ({route.BlockedReason})[/color]");
					}
					else
					{
						var regionTag = route.IsRegionEdge ? $" [{route.RegionName}]" : "";
						var meta = $"move:{route.Destination.RegionId}:{route.Destination.LocalId}";
						lines.Add($"  [url={meta}]{route.LocationName}{regionTag} ({route.TravelTime}분)[/url]");
					}
				}
			}

			// 6. 멍때리기 옵션
			lines.Add("");
			lines.Add("[color=yellow]행동:[/color]");
			lines.Add("  [url=idle]멍때리기[/url]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// Proc은 비어있음 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
