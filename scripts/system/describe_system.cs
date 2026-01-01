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
							lines.Add($"  [url=look_character:{id}]{character.Name}[/url]");
						}
					}
					lines.Add("");
				}
			}

			// 5. 오브젝트
			if (lookResult.ObjectIds.Count > 0)
			{
				var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
				if (characterSystem != null)
				{
					lines.Add("[color=orange]오브젝트:[/color]");
					foreach (var id in lookResult.ObjectIds)
					{
						var obj = characterSystem.GetCharacter(id);
						if (obj != null)
						{
							lines.Add($"  [url=look_object:{id}]{obj.Name}[/url]");
						}
					}
					lines.Add("");
				}
			}

			// 6. 바닥 아이템
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

			// 7. 이동 가능 경로 (BBCode 링크)
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

			// 6. 행동 옵션
			lines.Add("");
			lines.Add("[color=yellow]행동:[/color]");
			lines.Add("  [url=inventory]소지품 확인[/url]");
			lines.Add("  [url=idle]멍때리기[/url]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 오브젝트 살펴보기 결과 텍스트 생성
		/// </summary>
		public string GetObjectLookText(ObjectLookResult objectLook)
		{
			var lines = new List<string>();

			lines.Add($"[b]{objectLook.Name}[/b]");
			lines.Add("");

			if (objectLook.Inventory.Count > 0)
			{
				var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
				if (itemSystem != null)
				{
					lines.Add("[color=lime]보관된 아이템:[/color]");
					foreach (var (itemId, count) in objectLook.Inventory)
					{
						var item = itemSystem.GetItem(itemId);
						if (item != null)
						{
							var countText = count > 1 ? $" x{count}" : "";
							lines.Add($"  [url=take:{objectLook.ObjectId}:{itemId}]{item.Name}{countText} 가져가기[/url]");
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

			// 플레이어 인벤토리에서 넣기 옵션 추가 (PlayerSystem에서 인벤토리 조회)
			var playerSystem = _hub.FindSystem("playerSystem") as PlayerSystem;
			var player = playerSystem?.GetPlayerCharacter();
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
							lines.Add($"  [url=put:{objectLook.ObjectId}:{kvp.Key}]{item.Name}{countText}[/url]");
						}
					}
					lines.Add("");
				}
			}

			// 오브젝트 행동 표시
			if (objectLook.Actions.Count > 0)
			{
				lines.Add("[color=yellow]행동:[/color]");
				foreach (var action in objectLook.Actions)
				{
					var actionName = GetActionDisplayName(action);
					lines.Add($"  [url=action:{objectLook.ObjectId}:{action}]{actionName}[/url]");
				}
				lines.Add("");
			}

			lines.Add("[url=back]뒤로[/url]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 캐릭터 살펴보기 결과 텍스트 생성
		/// </summary>
		public string GetCharacterLookText(CharacterLookResult characterLook)
		{
			var lines = new List<string>();

			lines.Add($"[b]{characterLook.Name}[/b]");
			lines.Add("");

			// 상호작용 옵션 표시
			if (characterLook.Interactions.Count > 0)
			{
				lines.Add("[color=yellow]상호작용:[/color]");
				foreach (var interaction in characterLook.Interactions)
				{
					var interactionName = GetInteractionDisplayName(interaction);
					lines.Add($"  [url=interact:{characterLook.CharacterId}:{interaction}]{interactionName}[/url]");
				}
				lines.Add("");
			}
			else
			{
				lines.Add("[color=gray]특별한 상호작용이 없다.[/color]");
				lines.Add("");
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
			var player = playerSystem?.GetPlayerCharacter();

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
		/// 바닥 아이템 상세 메뉴 텍스트 생성
		/// </summary>
		public string GetGroundItemMenuText(int itemId, int count)
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

			var countText = count > 1 ? $" x{count}" : "";
			lines.Add($"[b]{item.Name}{countText}[/b]");
			lines.Add("");

			lines.Add("[color=yellow]행동:[/color]");
			lines.Add($"  [url=pickup:{itemId}]줍기[/url]");
			lines.Add("");
			lines.Add("[url=back]뒤로[/url]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 인벤토리 아이템 상세 메뉴 텍스트 생성
		/// </summary>
		public string GetInventoryItemMenuText(int itemId, int count)
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

			var countText = count > 1 ? $" x{count}" : "";
			var valueText = item.Value > 0 ? $" ({item.Value * count}G)" : "";
			lines.Add($"[b]{item.Name}{countText}[/b]{valueText}");
			lines.Add("");

			lines.Add("[color=yellow]행동:[/color]");
			lines.Add($"  [url=item_use:{itemId}]사용[/url]");
			lines.Add($"  [url=item_combine:{itemId}]조합[/url]");
			lines.Add($"  [url=drop:{itemId}]버리기[/url]");
			lines.Add("");
			lines.Add("[url=back_inventory]뒤로[/url]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 행동 코드를 표시 이름으로 변환
		/// </summary>
		private static string GetActionDisplayName(string action)
		{
			return action switch
			{
				"use" => "사용하기",
				"open" => "열기",
				"close" => "닫기",
				"read" => "읽기",
				"examine" => "자세히 보기",
				_ => action
			};
		}

		/// <summary>
		/// 상호작용 코드를 표시 이름으로 변환
		/// </summary>
		private static string GetInteractionDisplayName(string interaction)
		{
			return interaction switch
			{
				"talk" => "대화하기",
				"trade" => "거래하기",
				"give" => "주기",
				"ask" => "물어보기",
				_ => interaction
			};
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
