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
		/// Proc은 비어있음 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
