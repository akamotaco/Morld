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
			return SelectDescribeText(location.DescribeText, time, location.IsIndoor, region?.CurrentWeather);
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
			var activity = unit.CurrentSchedule?.Activity;
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
			var unitSystem = _hub.FindSystem("unitSystem") as UnitSystem;
			var playerSystem = _hub.FindSystem("playerSystem") as PlayerSystem;
			var scriptSystem = _hub.FindSystem("scriptSystem") as ScriptSystem;

			if (unitSystem == null || playerSystem == null || scriptSystem == null)
				return result;

			var playerId = playerSystem.PlayerId;
			var characterIds = new List<int>();

			foreach (var unitId in lookResult.UnitIds)
			{
				if (unitId == playerId) continue;
				var unit = unitSystem.GetUnit(unitId);
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
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;
			if (worldSystem == null) return null;

			var locRef = lookResult.Location.LocationRef;
			return worldSystem.GetTerrain()?.GetLocation(locRef.RegionId, locRef.LocalId);
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
						var inventorySystem = _hub.FindSystem("inventorySystem") as InventorySystem;
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

			// === 구분선 (행동 옵션 영역) ===
			lines.Add("[color=gray]────────────────────[/color]");

			// 5. 이동 가능 경로 (BBCode 링크)
			if (lookResult.Routes.Count > 0)
			{
				lines.Add("[color=cyan]이동 가능:[/color]");
				foreach (var route in lookResult.Routes)
				{
					if (route.IsBlocked)
					{
						// BlockedReason 표시 제거 - 회색 처리만으로 충분
						// lines.Add($"  [color=gray]- {route.LocationName} ({route.BlockedReason})[/color]");
						lines.Add($"  [color=gray]- {route.LocationName}[/color]");
					}
					else
					{
						var regionTag = route.IsRegionEdge ? $" [{route.RegionName}]" : "";
						var meta = $"move:{route.Destination.RegionId}:{route.Destination.LocalId}";
						lines.Add($"  [url={meta}]{route.LocationName}{regionTag} ({route.TravelTime}분)[/url]");
					}
				}
			}

			// 6. 행동 옵션 (ActionProviderRegistry 사용)
			var playerSystem = _hub.FindSystem("playerSystem") as PlayerSystem;
			var player = playerSystem?.GetPlayerUnit();

			if (player != null)
			{
				var providedActions = _actionRegistry.GetAllActionsFor(player);
				if (providedActions.Count > 0)
				{
					lines.Add("");
					lines.Add("[color=yellow]행동:[/color]");
					foreach (var action in providedActions)
					{
						lines.Add(action.ToBBCode());
					}
				}
			}

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 유닛 살펴보기 결과 텍스트 생성 (캐릭터/오브젝트 통합)
		/// </summary>
		public string GetUnitLookText(UnitLookResult unitLook, IReadOnlyList<ActionLogEntry>? actionLogs = null)
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

			// 액션 표시
			if (unitLook.Actions.Count > 0)
			{
				lines.Add("[color=yellow]행동:[/color]");
				foreach (var action in unitLook.Actions)
				{
					// putinobject 액션은 '넣기'로 표시
					if (action == "putinobject")
					{
						lines.Add($"  [url=put_select:{unitLook.UnitId}]넣기[/url]");
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
		/// 플레이어 인벤토리 텍스트 생성
		/// </summary>
		public string GetInventoryText()
		{
			var lines = new List<string>();

			lines.Add("[b]소지품[/b]");
			lines.Add("");

			var playerSystem = _hub.FindSystem("playerSystem") as PlayerSystem;
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.FindSystem("inventorySystem") as InventorySystem;
			var player = playerSystem?.GetPlayerUnit();

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
						// 아이템 메뉴로 연결
						lines.Add($"  [url=item_inv_menu:{itemId}]{item.Name}{countText}[/url]{valueText}");
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
		/// parentContainer: 인벤토리 컨텍스트에서 넣기/버리기 대상 (Unit 또는 Situation Focus)
		/// </summary>
		public string GetItemMenuText(string context, int itemId, int count, int? unitId = null, Focus? parentContainer = null)
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
			}

			// 인벤토리 컨텍스트에서 넣기 옵션 추가 (상위가 Unit인 경우만)
			if (context == "inventory" && parentContainer != null &&
				parentContainer.Type == FocusType.Unit && parentContainer.UnitId.HasValue)
			{
				var unitSystem = _hub.FindSystem("unitSystem") as UnitSystem;
				var targetUnit = unitSystem?.GetUnit(parentContainer.UnitId.Value);
				if (targetUnit != null)
				{
					var putLabel = $"넣기: {targetUnit.Name}";
					lines.Add($"  [url=put:{parentContainer.UnitId.Value}:{itemId}]{putLabel}[/url]");
				}
			}

			if (filteredActions.Count > 0 || (context == "inventory" && parentContainer != null))
			{
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
				// take는 container에서 가져가기
				"take" when context == "container" => ($"take:{unitId}:{itemId}", "가져가기"),
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

		/// <summary>
		/// Proc은 비어있음 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
