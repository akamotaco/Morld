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
		/// Location 외관 묘사 반환
		/// </summary>
		public string GetLocationAppearance(Location? location, GameTime? time)
		{
			if (location == null) return "";
			return SelectAppearance(location.Appearance, time);
		}

		/// <summary>
		/// Region 외관 묘사 반환
		/// </summary>
		public string GetRegionAppearance(Region? region, GameTime? time)
		{
			if (region == null) return "";
			return SelectAppearance(region.Appearance, time);
		}

		/// <summary>
		/// Unit 외관 묘사 반환 (감정/표정 + Activity 기반)
		/// </summary>
		public string GetUnitAppearance(Unit? unit)
		{
			if (unit == null) return "";

			// Mood와 현재 Activity를 합쳐서 태그 생성
			var tags = new HashSet<string>(unit.Mood);
			var activity = unit.CurrentSchedule?.Activity;
			if (!string.IsNullOrEmpty(activity))
			{
				tags.Add(activity);
			}

			return SelectAppearanceByMood(unit.Appearance, tags);
		}

		/// <summary>
		/// Appearance Dictionary에서 Mood 기반 적절한 키 선택 (태그 순서 무관)
		/// </summary>
		private string SelectAppearanceByMood(Dictionary<string, string>? appearances, HashSet<string>? mood)
		{
			if (appearances == null || appearances.Count == 0)
				return "";

			if (mood == null || mood.Count == 0)
			{
				return appearances.TryGetValue("default", out var defaultAppearance) ? defaultAppearance : "";
			}

			string bestKey = "default";
			int bestMatchCount = 0;

			foreach (var (key, _) in appearances)
			{
				if (key == "default") continue;

				// 콤마로 구분된 태그를 HashSet으로 변환 (순서 무관)
				var keyTags = key.Split(',').Select(t => t.Trim()).ToHashSet();
				var matchCount = keyTags.Intersect(mood).Count();

				// 모든 키 태그가 현재 Mood에 포함되어야 함
				if (matchCount == keyTags.Count && matchCount > bestMatchCount)
				{
					bestMatchCount = matchCount;
					bestKey = key;
				}
			}

			return appearances.TryGetValue(bestKey, out var appearance) ? appearance : "";
		}

		/// <summary>
		/// Appearance Dictionary에서 적절한 키 선택 (태그 순서 무관)
		/// </summary>
		private string SelectAppearance(Dictionary<string, string>? appearances, GameTime? time)
		{
			if (appearances == null || appearances.Count == 0)
				return "";

			if (time == null)
			{
				return appearances.TryGetValue("default", out var defaultAppearance) ? defaultAppearance : "";
			}

			var currentTags = time.GetCurrentTags();

			string bestKey = "default";
			int bestMatchCount = 0;

			foreach (var (key, _) in appearances)
			{
				if (key == "default") continue;

				// 콤마로 구분된 태그를 HashSet으로 변환 (순서 무관)
				var keyTags = key.Split(',').Select(t => t.Trim()).ToHashSet();
				var matchCount = keyTags.Intersect(currentTags).Count();

				// 모든 키 태그가 현재 태그에 포함되어야 함
				if (matchCount == keyTags.Count && matchCount > bestMatchCount)
				{
					bestMatchCount = matchCount;
					bestKey = key;
				}
			}

			return appearances.TryGetValue(bestKey, out var appearance) ? appearance : "";
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

			// 3. 위치 외관 묘사
			if (!string.IsNullOrEmpty(loc.AppearanceText))
			{
				lines.Add(loc.AppearanceText);
				lines.Add("");
			}

			// 4. 주변 유닛 (캐릭터와 오브젝트 통합)
			if (lookResult.UnitIds.Count > 0)
			{
				var unitSystem = _hub.FindSystem("unitSystem") as UnitSystem;
				if (unitSystem != null)
				{
					// 캐릭터와 오브젝트 분리
					var characters = new List<Unit>();
					var objects = new List<Unit>();

					foreach (var id in lookResult.UnitIds)
					{
						var unit = unitSystem.GetUnit(id);
						if (unit != null)
						{
							if (unit.IsObject)
								objects.Add(unit);
							else
								characters.Add(unit);
						}
					}

					// 캐릭터 표시
					if (characters.Count > 0)
					{
						lines.Add("[color=yellow]주변 인물:[/color]");
						foreach (var character in characters)
						{
							lines.Add($"  [url=look_unit:{character.Id}]{character.Name}[/url]");
						}
						lines.Add("");
					}

					// 오브젝트 표시
					if (objects.Count > 0)
					{
						lines.Add("[color=orange]오브젝트:[/color]");
						foreach (var obj in objects)
						{
							lines.Add($"  [url=look_unit:{obj.Id}]{obj.Name}[/url]");
						}
						lines.Add("");
					}
				}
			}

			// 5. 바닥 아이템
			if (lookResult.GroundItems.Count > 0)
			{
				var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
				if (itemSystem != null)
				{
					lines.Add("[color=lime]바닥에 떨어진 아이템:[/color]");
					foreach (var (itemId, count) in lookResult.GroundItems)
					{
						var item = itemSystem.GetItem(itemId);
						if (item != null)
						{
							var countText = count > 1 ? $" x{count}" : "";
							lines.Add($"  [url=item_ground_menu:{itemId}:{count}]{item.Name}{countText}[/url]");
						}
					}
					lines.Add("");
				}
			}

			// 6. 이동 가능 경로 (BBCode 링크)
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

			// 7. 행동 옵션
			lines.Add("");
			lines.Add("[color=yellow]행동:[/color]");
			lines.Add("  [url=inventory]소지품 확인[/url]");
			lines.Add("  [url=toggle:idle]▶ 멍때리기[/url][hidden=idle]");
			lines.Add("    [url=idle:15]15분[/url]");
			lines.Add("    [url=idle:30]30분[/url]");
			lines.Add("    [url=idle:60]1시간[/url]");
			lines.Add("    [url=idle:240]4시간[/url]");
			lines.Add("  [/hidden=idle]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 유닛 살펴보기 결과 텍스트 생성 (캐릭터/오브젝트 통합)
		/// </summary>
		public string GetUnitLookText(UnitLookResult unitLook)
		{
			var lines = new List<string>();

			lines.Add($"[b]{unitLook.Name}[/b]");
			lines.Add("");

			// 외관 묘사
			if (!string.IsNullOrEmpty(unitLook.AppearanceText))
			{
				lines.Add(unitLook.AppearanceText);
				lines.Add("");
			}

			// 오브젝트일 경우 인벤토리 표시
			if (unitLook.IsObject)
			{
				if (unitLook.Inventory.Count > 0)
				{
					var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
					if (itemSystem != null)
					{
						lines.Add("[color=lime]보관된 아이템:[/color]");
						foreach (var (itemId, count) in unitLook.Inventory)
						{
							var item = itemSystem.GetItem(itemId);
							if (item != null)
							{
								var countText = count > 1 ? $" x{count}" : "";
								// 2차 메뉴로 연결
								lines.Add($"  [url=item_unit_menu:{unitLook.UnitId}:{itemId}:{count}]{item.Name}{countText}[/url]");
							}
						}
						lines.Add("");
					}
				}
				else
				{
					lines.Add("[color=gray]비어 있다.[/color]");
					lines.Add("");
				}

				// 플레이어 인벤토리에서 넣기 옵션 추가
				var playerSystem = _hub.FindSystem("playerSystem") as PlayerSystem;
				var player = playerSystem?.GetPlayerUnit();
				if (player != null && player.Inventory.Count > 0)
				{
					var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
					if (itemSystem != null)
					{
						lines.Add("[color=cyan]넣기:[/color]");
						foreach (var kvp in player.Inventory)
						{
							var item = itemSystem.GetItem(kvp.Key);
							if (item != null)
							{
								var countText = kvp.Value > 1 ? $" x{kvp.Value}" : "";
								lines.Add($"  [url=put:{unitLook.UnitId}:{kvp.Key}]{item.Name}{countText}[/url]");
							}
						}
						lines.Add("");
					}
				}
			}

			// 액션 표시
			if (unitLook.Actions.Count > 0)
			{
				lines.Add("[color=yellow]행동:[/color]");
				foreach (var action in unitLook.Actions)
				{
					// 액션 ID를 그대로 표시 (plan.md Q3 결정)
					lines.Add($"  [url=action:{action}:{unitLook.UnitId}]{action}[/url]");
				}
				lines.Add("");
			}
			else
			{
				if (!unitLook.IsObject)
				{
					lines.Add("[color=gray]특별한 상호작용이 없다.[/color]");
					lines.Add("");
				}
			}

			lines.Add("[url=back]뒤로[/url]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 플레이어 인벤토리 텍스트 생성
		/// </summary>
		public string GetInventoryText()
		{
			var lines = new List<string>();

			lines.Add("[b]소지품[/b]");
			lines.Add("");

			var playerSystem = _hub.FindSystem("playerSystem") as PlayerSystem;
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
			var player = playerSystem?.GetPlayerUnit();

			if (player == null || itemSystem == null)
			{
				lines.Add("[color=gray]인벤토리를 확인할 수 없습니다.[/color]");
				lines.Add("");
				lines.Add("[url=back]뒤로[/url]");
				return string.Join("\n", lines);
			}

			if (player.Inventory.Count == 0)
			{
				lines.Add("[color=gray]소지품이 없다.[/color]");
			}
			else
			{
				int totalValue = 0;
				foreach (var (itemId, count) in player.Inventory)
				{
					var item = itemSystem.GetItem(itemId);
					if (item != null)
					{
						var countText = count > 1 ? $" x{count}" : "";
						var valueText = item.Value > 0 ? $" ({item.Value * count}G)" : "";
						lines.Add($"  [url=item_inv_menu:{itemId}:{count}]{item.Name}{countText}[/url]{valueText}");
						totalValue += item.Value * count;
					}
				}
				lines.Add("");
				lines.Add($"[color=yellow]총 가치: {totalValue}G[/color]");
			}

			// 장착 아이템 표시
			if (player.EquippedItems.Count > 0)
			{
				lines.Add("");
				lines.Add("[color=cyan]장착 중:[/color]");
				foreach (var itemId in player.EquippedItems)
				{
					var item = itemSystem.GetItem(itemId);
					if (item != null)
					{
						lines.Add($"  {item.Name}");
					}
				}
			}

			lines.Add("");
			lines.Add("[url=back]뒤로[/url]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 아이템 상세 메뉴 텍스트 생성 (통합 함수)
		/// context: "ground" (바닥), "inventory" (플레이어 인벤토리), "container" (오브젝트/컨테이너)
		/// </summary>
		public string GetItemMenuText(string context, int itemId, int count, int? unitId = null)
		{
			var lines = new List<string>();
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
			var item = itemSystem?.GetItem(itemId);

			if (item == null)
			{
				lines.Add("[color=gray]아이템을 찾을 수 없습니다.[/color]");
				lines.Add("");
				lines.Add("[url=back]뒤로[/url]");
				return string.Join("\n", lines);
			}

			// 헤더 생성
			var countText = count > 1 ? $" x{count}" : "";
			var valueText = (context == "inventory" && item.Value > 0) ? $" ({item.Value * count}G)" : "";
			lines.Add($"[b]{item.Name}{countText}[/b]{valueText}");

			// container 컨텍스트일 경우 유닛 이름 표시
			if (context == "container" && unitId.HasValue)
			{
				var unitSystem = _hub.FindSystem("unitSystem") as UnitSystem;
				var unit = unitSystem?.GetUnit(unitId.Value);
				if (unit != null)
				{
					lines.Add($"[color=gray]{unit.Name}에서[/color]");
				}
			}
			lines.Add("");

			// 액션 필터링 및 표시
			var filteredActions = GetFilteredActions(item.Actions, context);
			if (filteredActions.Count > 0)
			{
				lines.Add("[color=yellow]행동:[/color]");
				foreach (var action in filteredActions)
				{
					var (url, label) = GetActionUrlAndLabel(action, itemId, unitId, context);
					lines.Add($"  [url={url}]{label}[/url]");
				}
				lines.Add("");
			}

			// 뒤로 버튼
			var backUrl = context switch
			{
				"inventory" => "back_inventory",
				"container" when unitId.HasValue => $"back_unit:{unitId.Value}",
				_ => "back"
			};
			lines.Add($"[url={backUrl}]뒤로[/url]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 액션 리스트에서 현재 context에 해당하는 액션만 필터링
		/// </summary>
		private List<string> GetFilteredActions(List<string> actions, string context)
		{
			var result = new List<string>();
			foreach (var action in actions)
			{
				var parts = action.Split('@');
				if (parts.Length == 2 && parts[1] == context)
				{
					result.Add(parts[0]); // 액션 이름만 추출
				}
			}
			return result;
		}

		/// <summary>
		/// 액션 이름을 URL과 표시 라벨로 변환
		/// </summary>
		private (string url, string label) GetActionUrlAndLabel(string action, int itemId, int? unitId, string context)
		{
			return action switch
			{
				// take는 context에 따라 다른 URL 생성
				"take" when context == "ground" => ($"take:ground:{itemId}", "줍기"),
				"take" when context == "container" => ($"take:{unitId}:{itemId}", "가져가기"),
				"use" => ($"item_use:{itemId}", "사용"),
				"drop" => ($"drop:{itemId}", "버리기"),
				"equip" => ($"equip:{itemId}", "장착"),
				"throw" => ($"throw:{itemId}", "던지기"),
				_ => ($"action:{action}:{itemId}", action) // 알 수 없는 액션은 그대로
			};
		}

		/// <summary>
		/// 바닥 아이템 상세 메뉴 텍스트 생성 (통합 함수 래퍼)
		/// </summary>
		public string GetGroundItemMenuText(int itemId, int count)
		{
			return GetItemMenuText("ground", itemId, count);
		}

		/// <summary>
		/// 인벤토리 아이템 상세 메뉴 텍스트 생성 (통합 함수 래퍼)
		/// </summary>
		public string GetInventoryItemMenuText(int itemId, int count)
		{
			return GetItemMenuText("inventory", itemId, count);
		}

		/// <summary>
		/// 오브젝트 인벤토리 아이템 상세 메뉴 텍스트 생성 (통합 함수 래퍼)
		/// </summary>
		public string GetUnitItemMenuText(int unitId, int itemId, int count)
		{
			return GetItemMenuText("container", itemId, count, unitId);
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
