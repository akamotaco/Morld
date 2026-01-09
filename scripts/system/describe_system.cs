using ECS;
using Morld;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace SE
{
	/// <summary>
	/// 묘사 텍스트 생성을 담당하는 Logic System
	/// </summary>
	public class DescribeSystem : ECS.System
	{
		private readonly ActionProviderRegistry _actionRegistry = new();
		private Dictionary<string, string> _actionMessages = new();

		public DescribeSystem()
		{
			// 핵심 기본 액션 프로바이더 등록
			_actionRegistry.Register(new CoreActionProvider());
		}

		/// <summary>
		/// 액션 메시지 템플릿 파일 로드
		/// </summary>
		public void LoadActionMessages(string filePath)
		{
			// Godot FileAccess를 사용해서 res:// 경로 지원
			// Python 모드에서는 이 파일이 없을 수 있으므로 조용히 스킵
			if (!Godot.FileAccess.FileExists(filePath))
			{
				return;
			}

			using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
			if (file == null)
			{
				Godot.GD.PrintErr($"[DescribeSystem] Failed to open action messages file: {filePath}");
				return;
			}
			var json = file.GetAsText();
			_actionMessages = JsonSerializer.Deserialize<Dictionary<string, string>>(json) ?? new();
			Godot.GD.Print($"[DescribeSystem] Loaded {_actionMessages.Count} action messages");
		}

		/// <summary>
		/// 액션 결과 메시지 생성
		/// </summary>
		public string FormatActionMessage(string actionKey, Dictionary<string, string> parameters)
		{
			if (!_actionMessages.TryGetValue(actionKey, out var template))
			{
				return $"{actionKey} 완료";
			}

			var result = template;
			foreach (var (key, value) in parameters)
			{
				result = result.Replace($"{{{key}}}", value);
			}
			return result;
		}

		/// <summary>
		/// 아이템 관련 액션 메시지 생성 (편의 메서드)
		/// </summary>
		public string FormatItemActionMessage(string actionKey, string itemName, string? unitName = null)
		{
			var parameters = new Dictionary<string, string> { { "itemName", itemName } };
			if (unitName != null)
			{
				parameters["unitName"] = unitName;
			}
			return FormatActionMessage(actionKey, parameters);
		}

		/// <summary>
		/// 액션 프로바이더 레지스트리 접근
		/// 외부 시스템에서 프로바이더를 등록/해제할 수 있음
		/// </summary>
		public ActionProviderRegistry ActionRegistry => _actionRegistry;

		/// <summary>
		/// Location 묘사 텍스트 반환 (실내/날씨 태그 포함)
		/// </summary>
		public string GetLocationDescribeText(Location? location, GameTime? time, Region? region = null)
		{
			if (location == null) return "";
			return SelectDescribeText(location.DescribeText, time, location.IsIndoor, region.CurrentWeather);
		}

		/// <summary>
		/// Region 묘사 텍스트 반환
		/// </summary>
		public string GetRegionDescribeText(Region? region, GameTime? time)
		{
			if (region == null) return "";
			// isIndoor=false, weather=null → 실내/날씨 태그 없이 시간 태그만 사용
			return SelectDescribeText(region.DescribeText, time, false, null);
		}

		/// <summary>
		/// Unit 외관 묘사 반환 (감정/표정 + Activity 기반)
		/// </summary>
		public string GetUnitAppearance(Unit? unit)
		{
			if (unit == null) return "";

			// Mood와 현재 Activity를 합쳐서 태그 생성
			var tags = new HashSet<string>(unit.Mood);
			// JobList 기반: CurrentJob.Name이 activity 역할 ("사냥", "식사" 등)
			var activity = unit.CurrentJob?.Name;
			if (!string.IsNullOrEmpty(activity))
			{
				tags.Add(activity);
			}

			return SelectAppearanceByMood(unit.Appearance, tags);
		}

		/// <summary>
		/// 캐릭터 presence text 가져오기 (ScriptSystem을 통해 Python 호출)
		/// </summary>
		private List<string> GetCharacterPresenceTexts(LookResult lookResult, LocationInfo loc)
		{
			var result = new List<string>();

			// 플레이어 제외한 캐릭터 ID 목록
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var scriptSystem = _hub.GetSystem("scriptSystem") as ScriptSystem;

			if (unitSystem == null || playerSystem == null || scriptSystem == null)
				return result;

			var playerId = playerSystem.PlayerId;
			var characterIds = new List<int>();

			foreach (var unitId in lookResult.UnitIds)
			{
				if (unitId == playerId) continue;
				var unit = unitSystem.FindUnit(unitId);
				if (unit != null && !unit.IsObject)
				{
					characterIds.Add(unitId);
				}
			}

			if (characterIds.Count == 0)
				return result;

			// ScriptSystem을 통해 Python에서 presence text 가져오기
			return scriptSystem.GetCharacterPresenceTexts(characterIds, loc.LocationRef.RegionId, loc.LocationRef.LocalId);
		}

		/// <summary>
		/// LookResult에서 현재 Location 객체 가져오기
		/// </summary>
		private Location? GetLocationFromLookResult(LookResult lookResult)
		{
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
			if (worldSystem == null) return null;

			var locRef = lookResult.Location.LocationRef;
			return worldSystem.GetTerrain().GetLocation(locRef.RegionId, locRef.LocalId);
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
		/// DescribeText Dictionary에서 적절한 키 선택 (태그 순서 무관)
		/// isIndoor=true → "실내" 태그 추가
		/// isIndoor=false + weather → "날씨:{weather}" 태그 추가
		/// isIndoor=false + weather=null → 실내/날씨 태그 없음 (Region용)
		/// </summary>
		private string SelectDescribeText(Dictionary<string, string>? describeText, GameTime? time, bool isIndoor = true, string? weather = null)
		{
			if (describeText == null || describeText.Count == 0)
				return "";

			if (time == null)
			{
				return describeText.TryGetValue("default", out var defaultText) ? defaultText : "";
			}

			var currentTags = time.GetCurrentTags();

			// 실내/날씨 태그 추가
			if (isIndoor)
			{
				currentTags.Add("실내");
			}
			else if (!string.IsNullOrEmpty(weather))
			{
				currentTags.Add($"날씨:{weather}");
			}

			string bestKey = "default";
			int bestMatchCount = 0;

			foreach (var (key, _) in describeText)
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

			return describeText.TryGetValue(bestKey, out var text) ? text : "";
		}

		/// <summary>
		/// LookResult를 기반으로 전체 상황 설명 텍스트 생성
		/// </summary>
		public string GetSituationText(LookResult lookResult, GameTime? time, IReadOnlyList<ActionLogEntry>? actionLogs = null)
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

			// 2. 시간 + 날씨 정보
			if (time != null)
			{
				var location = GetLocationFromLookResult(lookResult);
				var weatherText = "";
				// Location.CurrentWeather는 실외일 때만 부모 Region의 날씨 반환
				if (location != null && !string.IsNullOrEmpty(location.CurrentWeather))
				{
					weatherText = $" / {location.CurrentWeather}";
				}
				lines.Add($"{time}{weatherText}");
			}

			// === 구분선 ===
			lines.Add("[color=gray]────────────────────[/color]");

			// 3. 위치 외관 묘사
			if (!string.IsNullOrEmpty(loc.AppearanceText))
			{
				lines.Add(loc.AppearanceText);
			}

			// 3.1. 캐릭터 presence text (위치 외관 묘사 바로 다음)
			var presenceTexts = GetCharacterPresenceTexts(lookResult, loc);
			foreach (var presenceText in presenceTexts)
			{
				lines.Add(presenceText);
			}

			if (!string.IsNullOrEmpty(loc.AppearanceText) || presenceTexts.Count > 0)
			{
				lines.Add("");
			}

			// 3.5. 행동 로그 (appearance 다음, 유닛/액션 전)
			if (actionLogs != null && actionLogs.Count > 0)
			{
				foreach (var log in actionLogs)
				{
					var readMark = log.IsRead ? " [읽음]" : "";
					lines.Add($"[color=yellow]*{log.Message}{readMark}[/color]");
				}
				lines.Add("");
			}

			// 4. 주변 유닛 (캐릭터와 오브젝트 통합)
			if (lookResult.UnitIds.Count > 0)
			{
				var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
				if (unitSystem != null)
				{
					// 캐릭터와 오브젝트 분리
					var characters = new List<Unit>();
					var objects = new List<Unit>();

					foreach (var id in lookResult.UnitIds)
					{
						var unit = unitSystem.FindUnit(id);
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
						var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;
						lines.Add("[color=orange]오브젝트:[/color]");
						foreach (var obj in objects)
						{
							// IsVisible이고 인벤토리가 비어있지 않으면 "(아이템이 보임)" 표시
							var visibleSuffix = "";
							if (inventorySystem != null &&
								inventorySystem.IsUnitInventoryVisible(obj.Id) &&
								inventorySystem.GetUnitInventory(obj.Id).Count > 0)
							{
								visibleSuffix = " [color=lime](아이템이 보임)[/color]";
							}
							lines.Add($"  [url=look_unit:{obj.Id}]{obj.Name}[/url]{visibleSuffix}");
						}
						lines.Add("");
					}
				}
			}

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 묘사 텍스트만 생성 (행동 옵션 제외)
		/// TextUISystem에서 Python 훅과 함께 사용
		/// </summary>
		public string GetDescribeText(LookResult lookResult, GameTime? time, IReadOnlyList<ActionLogEntry>? actionLogs = null)
		{
			return GetSituationText(lookResult, time, actionLogs);
		}

		/// <summary>
		/// 행동 옵션 텍스트만 생성 (구분선 포함)
		/// TextUISystem에서 Python 훅 폴백으로 사용
		/// </summary>
		public string GetActionText(LookResult lookResult)
		{
			var lines = new List<string>();

			// 구분선
			lines.Add("[color=gray]────────────────────[/color]");

			// GetActionItems에서 행동 옵션 가져오기
			var actionItems = GetActionItems(lookResult);
			lines.AddRange(actionItems);

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 행동 옵션 BBCode 리스트 생성 (Python에서 사용)
		/// 이동 경로, 앉은 상태 행동, ActionProviderRegistry 행동 포함
		/// </summary>
		public List<string> GetActionItems(LookResult lookResult)
		{
			var items = new List<string>();

			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var player = playerSystem.GetPlayerUnit();
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;

			// 1. 이동 가능 경로
			if (lookResult.Routes.Count > 0)
			{
				items.Add("[color=cyan]이동 가능:[/color]");
				foreach (var route in lookResult.Routes)
				{
					if (route.IsBlocked)
					{
						items.Add($"  [color=gray]- {route.LocationName}[/color]");
					}
					else
					{
						var regionTag = route.IsRegionEdge ? $" [{route.RegionName}]" : "";
						var meta = $"move:{route.Destination.RegionId}:{route.Destination.LocalId}";
						items.Add($"  [url={meta}]{route.LocationName}{regionTag} ({route.TravelTime}분)[/url]");
					}
				}
			}

			// 2. 앉은 상태 행동
			if (player != null)
			{
				var seatedOnProp = player.TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
				if (seatedOnProp.Prop.IsValid)
				{
					var propName = seatedOnProp.Prop.Name;
					var colonIdx = propName.IndexOf(':');
					if (colonIdx >= 0 && int.TryParse(propName.Substring(colonIdx + 1), out int objectId))
					{
						var seatObject = unitSystem.FindUnit(objectId);
						var seatName = seatObject.Name ?? "오브젝트";

						items.Add("");
						items.Add($"[color=lime][앉음: {seatName}][/color]");
						items.Add($"  [url=stand_up]일어나기[/url]");

						// 운전석이면 운전 액션도 표시
						if (seatObject != null && seatObject.TraversalContext.HasProp("driver_seat"))
						{
							items.Add($"  [url=script:drive_menu]운전[/url]");
						}
					}
				}

				// 3. ActionProviderRegistry 행동
				var providedActions = _actionRegistry.GetAllActionsFor(player);
				if (providedActions.Count > 0)
				{
					items.Add("");
					items.Add("[color=yellow]행동:[/color]");
					foreach (var action in providedActions)
					{
						items.Add(action.ToBBCode());
					}
				}
			}

			return items;
		}

		/// <summary>
		/// 유닛 살펴보기 결과 텍스트 생성 (캐릭터/오브젝트 통합)
		/// </summary>
		public string GetUnitLookText(UnitLookResult unitLook, IReadOnlyList<ActionLogEntry>? actionLogs = null)
		{
			var lines = new List<string>();

			// 플레이어 정보 가져오기 (액션 필터링용)
			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var player = playerSystem?.GetPlayerUnit();

			lines.Add($"[b]{unitLook.Name}[/b]");
			lines.Add("");

			// 외관 묘사
			if (!string.IsNullOrEmpty(unitLook.AppearanceText))
			{
				lines.Add(unitLook.AppearanceText);
				lines.Add("");
			}

			// 행동 로그 (appearance 다음, 인벤토리/액션 전)
			if (actionLogs != null && actionLogs.Count > 0)
			{
				foreach (var log in actionLogs)
				{
					var readMark = log.IsRead ? " [읽음]" : "";
					lines.Add($"[color=yellow]*{log.Message}{readMark}[/color]");
				}
				lines.Add("");
			}

			// 오브젝트일 경우 인벤토리 표시
			if (unitLook.IsObject)
			{
				if (unitLook.Inventory.Count > 0)
				{
					var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
					if (itemSystem != null)
					{
						lines.Add("[color=lime]보관된 아이템:[/color]");
						foreach (var (itemId, count) in unitLook.Inventory)
						{
							var item = itemSystem.GetItem(itemId);
							if (item != null)
							{
								var countText = count > 1 ? $" x{count}" : "";
								// 아이템 메뉴로 연결
								lines.Add($"  [url=item_unit_menu:{unitLook.UnitId}:{itemId}]{item.Name}{countText}[/url]");
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

			}

			// 액션 표시 (플레이어의 can: prop으로 필터링)
			var filteredUnitActions = FilterActionsByActor(unitLook.Actions, player);
			if (filteredUnitActions.Count > 0)
			{
				lines.Add("[color=yellow]행동:[/color]");
				foreach (var action in filteredUnitActions)
				{
					// putinobject 액션은 script:put_to_object로 변환 (가져가기는 기존 Item 메뉴 방식 유지)
					if (action == "putinobject")
					{
						lines.Add($"  [url=script:put_to_object]넣기[/url]");
					}
					// script:함수명:표시명 형식 - Python 스크립트 직접 호출
					else if (action.StartsWith("script:"))
					{
						var parts = action.Split(':');
						if (parts.Length >= 3)
						{
							var funcName = parts[1];
							var displayName = parts[2];
							lines.Add($"  [url=script:{funcName}]{displayName}[/url]");
						}
						else if (parts.Length == 2)
						{
							// script:함수명 (표시명 없음 → 함수명 그대로 표시)
							var funcName = parts[1];
							lines.Add($"  [url=script:{funcName}]{funcName}[/url]");
						}
						else
						{
							// 형식 오류 - 디버그 정보와 함께 표시
							Godot.GD.PrintErr($"[DescribeSystem] Invalid script action format: '{action}' (expected 'script:funcName:displayName')");
							lines.Add($"  [color=red][오류: {action}][/color]");
						}
					}
					else
					{
						// 다른 액션은 그대로 표시
						lines.Add($"  [url=action:{action}:{unitLook.UnitId}]{action}[/url]");
					}
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
		/// 아이템 소유자 이름 가져오기 (unique_id → 이름)
		/// </summary>
		private string GetOwnerName(string ownerUniqueId)
		{
			if (string.IsNullOrEmpty(ownerUniqueId))
				return null;

			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			var owner = unitSystem?.FindByUniqueId(ownerUniqueId);
			return owner?.Name;
		}

		/// <summary>
		/// 아이템 이름에 소유자 표시 추가
		/// </summary>
		private string GetItemNameWithOwner(Morld.Item item)
		{
			if (item == null) return "";

			var ownerName = GetOwnerName(item.Owner);
			if (!string.IsNullOrEmpty(ownerName))
				return $"{item.Name} [color=gray]({ownerName} 소유)[/color]";

			return item.Name;
		}

		/// <summary>
		/// Location 이름에 소유자 표시 추가
		/// </summary>
		public string GetLocationNameWithOwner(Morld.Location location)
		{
			if (location == null) return "";

			var ownerName = GetOwnerName(location.Owner);
			if (!string.IsNullOrEmpty(ownerName))
				return $"{location.Name} [color=gray]({ownerName} 소유)[/color]";

			return location.Name;
		}

		/// <summary>
		/// 플레이어 인벤토리 텍스트 생성
		/// </summary>
		public string GetInventoryText()
		{
			var lines = new List<string>();

			lines.Add("[b]소지품[/b]");
			lines.Add("");

			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;
			var player = playerSystem.GetPlayerUnit();

			if (player == null || itemSystem == null || inventorySystem == null)
			{
				lines.Add("[color=gray]인벤토리를 확인할 수 없습니다.[/color]");
				lines.Add("");
				lines.Add("[url=back]뒤로[/url]");
				return string.Join("\n", lines);
			}

			var inventory = inventorySystem.GetUnitInventory(player.Id);
			var equippedItems = inventorySystem.GetUnitEquippedItems(player.Id);

			if (inventory.Count == 0)
			{
				lines.Add("[color=gray]소지품이 없다.[/color]");
			}
			else
			{
				int totalValue = 0;
				foreach (var (itemId, count) in inventory)
				{
					var item = itemSystem.GetItem(itemId);
					if (item != null)
					{
						var countText = count > 1 ? $" x{count}" : "";
						var valueText = item.Value > 0 ? $" ({item.Value * count}G)" : "";
						var ownerText = !string.IsNullOrEmpty(item.Owner) ? $" [color=gray]({GetOwnerName(item.Owner)} 소유)[/color]" : "";
						// 아이템 메뉴로 연결
						lines.Add($"  [url=item_inv_menu:{itemId}]{item.Name}{countText}[/url]{valueText}{ownerText}");
						totalValue += item.Value * count;
					}
				}
				lines.Add("");
				lines.Add($"[color=yellow]총 가치: {totalValue}G[/color]");
			}

			// 장착 아이템 표시
			if (equippedItems.Count > 0)
			{
				lines.Add("");
				lines.Add("[color=cyan]장착 중:[/color]");
				foreach (var itemId in equippedItems)
				{
					var item = itemSystem.GetItem(itemId);
					if (item != null)
					{
						var ownerText = !string.IsNullOrEmpty(item.Owner) ? $" [color=gray]({GetOwnerName(item.Owner)} 소유)[/color]" : "";
						lines.Add($"  {item.Name}{ownerText}");
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
		/// targetUnitId:
		///   - container: 아이템이 있는 컨테이너 유닛 ID
		///   - inventory: 넣기 대상 유닛 ID (있으면 넣기 옵션 표시)
		/// </summary>
		public string GetItemMenuText(string context, int itemId, int count, int? targetUnitId = null)
		{
			var lines = new List<string>();
			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;

			// 플레이어 정보 가져오기 (액션 필터링용)
			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var player = playerSystem?.GetPlayerUnit();
			var item = itemSystem.GetItem(itemId);

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
			if (context == "container" && targetUnitId.HasValue)
			{
				var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
				var unit = unitSystem.FindUnit(targetUnitId.Value);
				if (unit != null)
				{
					lines.Add($"[color=gray]{unit.Name}에서[/color]");
				}
			}
			lines.Add("");

			// 액션 필터링 및 표시
			// 1. context로 필터링 (take@container 등)
			// 2. 플레이어의 can: prop으로 필터링
			var contextFiltered = GetFilteredActions(item.Actions, context);
			var filteredActions = FilterActionsByActor(contextFiltered, player);
			if (filteredActions.Count > 0)
			{
				lines.Add("[color=yellow]행동:[/color]");
				foreach (var action in filteredActions)
				{
					var (url, label) = GetActionUrlAndLabel(action, itemId, targetUnitId, context);
					lines.Add($"  [url={url}]{label}[/url]");
				}
			}

			// 인벤토리 컨텍스트에서 넣기 옵션 추가 (targetUnitId가 있는 경우)
			if (context == "inventory" && targetUnitId.HasValue)
			{
				var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
				var targetUnit = unitSystem.FindUnit(targetUnitId.Value);
				if (targetUnit != null)
				{
					var putLabel = $"넣기: {targetUnit.Name}";
					lines.Add($"  [url=put:{targetUnitId.Value}:{itemId}]{putLabel}[/url]");
				}
			}

			if (filteredActions.Count > 0 || (context == "inventory" && targetUnitId.HasValue))
			{
				lines.Add("");
			}

			// 뒤로 버튼
			var backUrl = context switch
			{
				"inventory" => "back_inventory",
				"container" when targetUnitId.HasValue => $"back_unit:{targetUnitId.Value}",
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
			// script:함수명:표시명 형식 처리
			if (action.StartsWith("script:"))
			{
				var parts = action.Split(':');
				if (parts.Length >= 3)
				{
					// script:함수명:표시명 → URL: script:함수명:itemId, Label: 표시명
					return ($"script:{parts[1]}:{itemId}", parts[2]);
				}
				else if (parts.Length == 2)
				{
					// script:함수명 (표시명 없음) → URL: script:함수명:itemId, Label: 함수명
					return ($"script:{parts[1]}:{itemId}", parts[1]);
				}
			}

			return action switch
			{
				// take는 container에서 가져가기 - script:take_item으로 처리
				"take" when context == "container" => ($"script:take_item:{itemId}", "가져가기"),
				"use" => ($"item_use:{itemId}", "사용"),
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

		// ========================================
		// 액션 필터링 (can: prop 기반)
		// ========================================

		/// <summary>
		/// 액션 문자열에서 액션 이름 추출 (can: prop 체크용)
		/// </summary>
		/// <remarks>
		/// 지원 형식:
		/// - "script:funcName:displayName" → "funcName"
		/// - "script:funcName" → "funcName"
		/// - "sit@seatName:displayName" → "sit"
		/// - "action@context" → "action"
		/// - "putinobject" → "putinobject"
		/// - "rest", "sleep" 등 → 그대로
		/// </remarks>
		private string ExtractActionName(string action)
		{
			// script:함수명:표시명 또는 script:함수명
			if (action.StartsWith("script:"))
			{
				var parts = action.Split(':');
				return parts.Length >= 2 ? parts[1] : action;
			}

			// sit@좌석명:표시명 형식
			if (action.StartsWith("sit@"))
			{
				return "sit";
			}

			// action@context 형식 (take@container, use@inventory 등)
			var atIndex = action.IndexOf('@');
			if (atIndex > 0)
			{
				return action.Substring(0, atIndex);
			}

			// 기본 액션 (rest, sleep, putinobject 등)
			return action;
		}

		/// <summary>
		/// Actor가 특정 액션을 수행할 수 있는지 확인 (can: prop 체크)
		/// </summary>
		/// <param name="actor">행위자 Unit (플레이어 등)</param>
		/// <param name="action">액션 문자열</param>
		/// <returns>can:액션명 prop이 1 이상이면 true</returns>
		private bool CanPerformAction(Unit actor, string action)
		{
			if (actor == null) return false;

			var actionName = ExtractActionName(action);
			var canProp = $"can:{actionName}";

			// can:액션명 prop이 존재하고 값이 1 이상이면 수행 가능
			return actor.TraversalContext.Props.HasAtLeast(canProp, 1);
		}

		/// <summary>
		/// 액션 리스트를 Actor의 can: prop으로 필터링
		/// </summary>
		/// <param name="actions">원본 액션 리스트</param>
		/// <param name="actor">행위자 Unit</param>
		/// <returns>수행 가능한 액션만 포함된 리스트</returns>
		private List<string> FilterActionsByActor(List<string> actions, Unit actor)
		{
			if (actor == null) return new List<string>();

			var result = new List<string>();
			foreach (var action in actions)
			{
				if (CanPerformAction(actor, action))
				{
					result.Add(action);
				}
			}
			return result;
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
