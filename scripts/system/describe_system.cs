using ECS;
using Morld;
using System.Collections.Generic;
using System.Linq;

namespace SE
{
	/// <summary>
	/// 묘사 텍스트 생성을 담당하는 Logic System
	/// </summary>
	public class DescribeSystem : ECS.System
	{
		/// <summary>
		/// Edge 위 캐릭터 감지 거리 threshold (분 단위, -1이면 무한)
		/// </summary>
		public int AwarenessDistanceThreshold { get; set; } = 30;

		/// <summary>
		/// 인접 Location 군중 감지 거리 threshold (분 단위, -1이면 무한)
		/// </summary>
		public int CrowdDistanceThreshold { get; set; } = 30;

		/// <summary>
		/// 군중으로 판단할 최소 인원 수
		/// </summary>
		public int CrowdCountThreshold { get; set; } = 3;

		public DescribeSystem()
		{
		}

		/// <summary>
		/// 플레이어 주변 인식 정보를 ActionLog에 추가
		/// - Edge 위에서 다가오는 캐릭터 감지
		/// - 인접 Location의 군중(3명 이상) 감지
		/// pending 상태에서 한 번 호출
		/// Note: 멀어지는 캐릭터는 NotifyNpcDeparture에서 처리
		/// </summary>
		public void GenerateNearbyAwarenessLogs()
		{
			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
			var actionLogSystem = _hub.GetSystem("actionLogSystem") as ActionLogSystem;

			var player = playerSystem?.FindPlayerUnit();
			if (player == null) return;

			var playerLocation = player.CurrentLocation;
			var terrain = worldSystem?.GetTerrain();
			if (terrain == null) return;

			var region = terrain.GetRegion(playerLocation.RegionId);
			var currentLoc = region?.GetLocation(playerLocation.LocalId);
			if (currentLoc == null) return;

			// 1. Edge 위에서 다가오는 캐릭터 감지
			foreach (var unit in unitSystem.Units.Values)
			{
				// 플레이어, 오브젝트 제외
				if (unit.Id == player.Id) continue;
				if (unit.IsObject) continue;

				var edgeProgress = unit.CurrentEdge;
				if (edgeProgress == null) continue;

				// 다가오는 캐릭터: 목적지가 플레이어 위치
				if (edgeProgress.To == playerLocation)
				{
					// threshold 체크 (-1이면 무한)
					if (AwarenessDistanceThreshold >= 0 && edgeProgress.RemainingTime > AwarenessDistanceThreshold)
						continue;

					var fromLoc = terrain.GetLocation(edgeProgress.From);
					var fromName = GetLocationDisplayName(terrain, fromLoc);
					actionLogSystem?.AddLog($"{unit.Name}(이)가 {fromName} 쪽에서 다가온다.");
				}
			}

			// 2. 인접 Location의 군중 감지
			var edges = region.GetEdges(currentLoc);
			foreach (var edge in edges)
			{
				var neighborLoc = edge.GetOtherLocation(currentLoc);
				var travelTime = edge.GetTravelTime(currentLoc);

				// threshold 체크 (-1이면 무한)
				if (CrowdDistanceThreshold >= 0 && travelTime > CrowdDistanceThreshold)
					continue;

				// 해당 Location에 있는 캐릭터 수 계산 (오브젝트 제외)
				var neighborRef = new LocationRef(neighborLoc.RegionId, neighborLoc.LocalId);
				int characterCount = 0;
				foreach (var unit in unitSystem.Units.Values)
				{
					if (unit.IsObject) continue;
					if (unit.Id == player.Id) continue;
					if (unit.CurrentLocation == neighborRef && unit.CurrentEdge == null)
					{
						characterCount++;
					}
				}

				if (characterCount >= CrowdCountThreshold)
				{
					var locName = GetLocationDisplayName(terrain, neighborLoc);
					actionLogSystem?.AddLog($"{locName}에서 왁자지껄한 소리가 들린다.");
				}
				else if (characterCount == 2)
				{
					var locName = GetLocationDisplayName(terrain, neighborLoc);
					actionLogSystem?.AddLog($"{locName}에서 도란도란 이야기 소리가 들린다.");
				}
			}
		}

		/// <summary>
		/// Location 표시 이름 생성 (Region 이름 포함)
		/// </summary>
		private string GetLocationDisplayName(Terrain terrain, Location location)
		{
			if (location == null) return "어딘가";

			var region = terrain.GetRegion(location.RegionId);
			if (region != null && region.Name != "unknown")
			{
				return $"{region.Name} {location.Name}";
			}
			return location.Name ?? "어딘가";
		}

		/// <summary>
		/// 행동 로그 텍스트 생성 (ActionLogSystem에서 가져옴)
		/// </summary>
		private List<string> GetActionLogText()
		{
			var lines = new List<string>();
			var actionLogSystem = _hub.GetSystem("actionLogSystem") as ActionLogSystem;
			var actionLogs = actionLogSystem.GetPrintableLogs();

			if (actionLogs != null && actionLogs.Count > 0)
			{
				foreach (var log in actionLogs)
				{
					lines.Add($"[color=yellow]*{log.Message}[/color]");
				}
			}

			return lines;
		}

		/// <summary>
		/// 캐릭터 describe text 가져오기 (ScriptSystem을 통해 Python 호출)
		/// </summary>
		private List<string> GetCharacterDescribeTexts(LookResult lookResult)
		{
			var result = new List<string>();

			// 플레이어 제외한 캐릭터 ID 목록
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var scriptSystem = _hub.GetSystem("scriptSystem") as ScriptSystem;

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

			// ScriptSystem을 통해 Python에서 describe text 가져오기
			return scriptSystem.GetCharacterDescribeTexts(characterIds);
		}

		/// <summary>
		/// 주변 유닛(캐릭터/오브젝트) 목록 텍스트 생성
		/// </summary>
		private List<string> GetNearbyUnitsText(LookResult lookResult)
		{
			var lines = new List<string>();

			if (lookResult.UnitIds.Count == 0)
				return lines;

			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;

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
					// 현재 Job의 Name을 activity로 표시
					// 목표 지역에 도착했으면 "XX 중", 이동 중이면 "XX-이동 중"
					var currentJob = character.JobList?.Current;
					var activity = currentJob?.Name;
					string activityText = "";
					if (!string.IsNullOrEmpty(activity))
					{
						var currentLoc = character.CurrentLocation;
						var jobLoc = currentJob.GetLocationRef();
						bool isAtDestination = currentLoc.RegionId == jobLoc.RegionId && currentLoc.LocalId == jobLoc.LocalId;
						activityText = isAtDestination
							? $" [color=gray]({activity} 중)[/color]"
							: $" [color=gray]({activity}-이동 중)[/color]";
					}
					lines.Add($"  [url=look_unit:{character.Id}]{character.Name}[/url]{activityText}");
				}
				lines.Add("");
			}

			// 오브젝트 표시 (바닥 오브젝트도 포함 - 클릭해서 Container Focus로 조작)
			if (objects.Count > 0)
			{
				lines.Add("[color=orange]오브젝트:[/color]");
				foreach (var obj in objects)
				{
					// ItemVisible이 true면 아이템 개수 표시
					var itemCountText = "";
					if (obj.ItemVisible && inventorySystem != null)
					{
						var inventory = inventorySystem.GetUnitInventory(obj.Id);
						if (inventory != null)
						{
							int totalCount = 0;
							foreach (var kvp in inventory)
								totalCount += kvp.Value;
							if (totalCount > 0)
								itemCountText = $" [color=gray](아이템 {totalCount}개)[/color]";
						}
					}
					lines.Add($"  [url=look_unit:{obj.Id}]{obj.Name}[/url]{itemCountText}");
				}
				lines.Add("");
			}

			return lines;
		}

		/// <summary>
		/// 모든 묘사 텍스트 통합 (위치, 캐릭터)
		/// </summary>
		private List<string> GetAllDescribeText(LookResult lookResult, GameTime time)
		{
			var lines = new List<string>();

			// 1. 위치 묘사
			var locationDescribeText = GetLocationDescribeText(lookResult, time);
			if (!string.IsNullOrEmpty(locationDescribeText))
			{
				lines.Add(locationDescribeText);
			}

			// 2. 캐릭터 묘사
			var characterTexts = GetCharacterDescribeTexts(lookResult);
			lines.AddRange(characterTexts);

			// 묘사 텍스트가 있으면 다음 섹션과 구분하기 위해 빈 줄 추가
			if (lines.Count > 0)
			{
				lines.Add("");
			}

			return lines;
		}

		/// <summary>
		/// Location 묘사 텍스트 반환 (LookResult에서 Location/Region 조회, 태그 기반 선택)
		/// </summary>
		private string GetLocationDescribeText(LookResult lookResult, GameTime time)
		{
			if (_hub.GetSystem("worldSystem") is not WorldSystem worldSystem)
				return "";

			var terrain = worldSystem.GetTerrain();
			var locRef = lookResult.Location.LocationRef;
			var location = terrain.GetLocation(locRef);
			var region = terrain.GetRegion(locRef.RegionId);

			if (location == null || region == null) return "";

			var describeText = location.DescribeText;
			if (describeText == null || describeText.Count == 0)
				return "";

			if (time == null)
			{
				return describeText.TryGetValue("default", out var defaultText) ? defaultText : "";
			}

			var currentTags = time.GetCurrentTags();

			// 실내/날씨 태그 추가
			if (location.IsIndoor)
			{
				currentTags.Add("실내");
			}
			else if (!string.IsNullOrEmpty(region.CurrentWeather))
			{
				currentTags.Add($"날씨:{region.CurrentWeather}");
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
		/// 위치/시간/날씨 정보는 TextUISystem에서 Python get_header()를 통해 별도로 렌더링
		/// </summary>
		public string GetSituationText(LookResult lookResult, GameTime time)
		{
			var lines = new List<string>();

			// 1. 묘사 텍스트 (위치, 캐릭터)
			lines.AddRange(GetAllDescribeText(lookResult, time));

			// 2. 행동 로그
			var actionLogs = GetActionLogText();
			if (actionLogs.Count > 0)
			{
				lines.AddRange(actionLogs);
				lines.Add("");
			}

			// 3. 주변 유닛 목록 (캐릭터, 오브젝트)
			lines.AddRange(GetNearbyUnitsText(lookResult));

			return string.Join("\n", lines);
		}



		/// <summary>
		/// 유닛 살펴보기 결과 텍스트 생성 (캐릭터/오브젝트 통합)
		/// </summary>
		public string GetUnitLookText(UnitLookResult unitLook)
		{
			var lines = new List<string>();

			// 플레이어 정보 가져오기 (액션 필터링용)
			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var actionSystem = _hub.GetSystem("actionSystem") as ActionSystem;
			var player = playerSystem?.FindPlayerUnit();

			lines.Add($"[b]{unitLook.Name}[/b]");
			lines.Add("");

			// 행동 로그 (ActionLogSystem에서 직접 가져옴)
			var actionLogSystem = _hub.GetSystem("actionLogSystem") as ActionLogSystem;
			var actionLogs = actionLogSystem?.GetPrintableLogs();
			if (actionLogs != null && actionLogs.Count > 0)
			{
				foreach (var log in actionLogs)
				{
					lines.Add($"[color=yellow]*{log.Message}[/color]");
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
							var item = itemSystem.FindItem(itemId);
							if (item != null)
							{
								var countText = count > 1 ? $" x{count}" : "";
								var itemName = GetNameWithOwner(item);
								// 아이템 메뉴로 연결
								lines.Add($"  [url=item_unit_menu:{unitLook.UnitId}:{itemId}]{itemName}{countText}[/url]");
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

			// 상태 차단 메시지 표시 (수면 중 등)
			if (!string.IsNullOrEmpty(unitLook.BlockedMessage))
			{
				lines.Add($"[color=gray]{unitLook.BlockedMessage}[/color]");
				lines.Add("");
			}

			// 액션 표시 (플레이어의 can: prop으로 파티션)
			var partition = actionSystem.PartitionActionsByActor(unitLook.Actions, player);
			if (partition.Enabled.Count > 0 || partition.Disabled.Count > 0)
			{
				lines.Add("[color=yellow]행동:[/color]");

				// 활성화된 액션 (링크로 표시)
				foreach (var action in partition.Enabled)
				{
					lines.Add(actionSystem.FormatActionLine(action, unitLook.UnitId, enabled: true));
				}

				// 비활성화된 액션 (회색으로 표시)
				foreach (var action in partition.Disabled)
				{
					lines.Add(actionSystem.FormatActionLine(action, unitLook.UnitId, enabled: false));
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

			// 뒤로 버튼 (인벤토리 메뉴는 footer에서 표시)
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
		/// IOwnable 객체 이름에 소유자 표시 추가 (Unit, Item, Location 공통)
		/// </summary>
		public string GetNameWithOwner(Morld.IOwnable ownable)
		{
			if (ownable == null) return "";

			var ownerName = GetOwnerName(ownable.Owner);
			if (!string.IsNullOrEmpty(ownerName))
				return $"{ownable.Name} [color=gray]({ownerName} 소유)[/color]";

			return ownable.Name;
		}

		/// <summary>
		/// 아이템 카테고리 분류
		/// </summary>
		private enum ItemCategory
		{
			Equipment,  // 장비 (장착 가능 - 손에 드는 것)
			Clothing,   // 옷 (착용 가능 - 입는 것)
			Tool,       // 도구 (passive 능력 또는 사용/조합 가능)
			Food,       // 음식 (먹거나 마실 수 있음)
			Material    // 재료&잡동사니
		}

		/// <summary>
		/// 아이템의 카테고리 판별
		/// </summary>
		private ItemCategory GetItemCategory(Item item)
		{
			// 1. 옷: 착용 슬롯이 있는 아이템
			if (item.EquipProps != null && item.EquipProps.Count > 0)
			{
				if (item.GetEquipPropKey("착용:") != null)
				{
					return ItemCategory.Clothing;
				}
			}

			// 2. 장비: 장착 슬롯이 있는 아이템 (손에 드는 것)
			if (item.EquipProps != null && item.EquipProps.Count > 0)
			{
				if (item.GetEquipPropKey("장착:") != null)
				{
					return ItemCategory.Equipment;
				}
			}

			// 2. 음식: eat 또는 drink 액션이 있는 아이템
			if (item.Actions != null)
			{
				foreach (var action in item.Actions)
				{
					if (action.Contains("call:eat:") || action.Contains(":먹기") || action.Contains(":마시기"))
					{
						return ItemCategory.Food;
					}
				}
			}

			// 3. 도구: passive_props가 있거나 call: 액션(사용/조합)이 있는 아이템
			if (item.PassiveProps != null && item.PassiveProps.Count > 0)
			{
				return ItemCategory.Tool;
			}
			if (item.Actions != null)
			{
				foreach (var action in item.Actions)
				{
					if (action.Contains("call:") && !action.Contains("call:look:") && !action.Contains("call:debug"))
					{
						return ItemCategory.Tool;
					}
				}
			}

			// 4. 나머지는 재료&잡동사니
			return ItemCategory.Material;
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
			var player = playerSystem.FindPlayerUnit();

			if (player == null)
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
				// 카테고리별로 아이템 분류
				var equipmentItems = new List<(int itemId, int count, Item item)>();
				var clothingItems = new List<(int itemId, int count, Item item)>();
				var toolItems = new List<(int itemId, int count, Item item)>();
				var foodItems = new List<(int itemId, int count, Item item)>();
				var materialItems = new List<(int itemId, int count, Item item)>();

				foreach (var (itemId, count) in inventory)
				{
					var item = itemSystem.FindItem(itemId);
					if (item == null) continue;

					var category = GetItemCategory(item);
					switch (category)
					{
						case ItemCategory.Equipment:
							equipmentItems.Add((itemId, count, item));
							break;
						case ItemCategory.Clothing:
							clothingItems.Add((itemId, count, item));
							break;
						case ItemCategory.Tool:
							toolItems.Add((itemId, count, item));
							break;
						case ItemCategory.Food:
							foodItems.Add((itemId, count, item));
							break;
						case ItemCategory.Material:
							materialItems.Add((itemId, count, item));
							break;
					}
				}

				// 각 카테고리 렌더링
				RenderInventoryCategory(lines, "장비", equipmentItems);
				RenderInventoryCategory(lines, "옷", clothingItems);
				RenderInventoryCategory(lines, "도구", toolItems);
				RenderInventoryCategory(lines, "음식", foodItems);
				RenderInventoryCategory(lines, "재료&잡동사니", materialItems);
			}

			// 장착 아이템 표시
			if (equippedItems.Count > 0)
			{
				lines.Add("");
				lines.Add("[color=cyan]장착 중:[/color]");
				foreach (var itemId in equippedItems)
				{
					var item = itemSystem.FindItem(itemId);
					if (item != null)
					{
						var itemName = GetNameWithOwner(item);
						lines.Add($"  {itemName}");
					}
				}
			}

			lines.Add("");
			lines.Add("[url=back]뒤로[/url]");

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 인벤토리 카테고리 렌더링 헬퍼
		/// </summary>
		private void RenderInventoryCategory(List<string> lines, string categoryName, List<(int itemId, int count, Item item)> items)
		{
			if (items.Count == 0) return;

			lines.Add($"[color=yellow]{categoryName}[/color]");
			foreach (var (itemId, count, item) in items)
			{
				var countText = count > 1 ? $" x{count}" : "";
				var valueText = item.Value > 0 ? $" ({item.Value}G)" : "";
				var itemName = GetNameWithOwner(item);
				lines.Add($"  [url=item_inv_menu:{itemId}]{itemName}{countText}[/url]{valueText}");
			}
			lines.Add("");
		}

		/// <summary>
		/// 장착 아이템 목록 텍스트 생성
		/// </summary>
		public string GetEquipmentText()
		{
			var lines = new List<string>();

			lines.Add("[b]장비[/b]");
			lines.Add("");

			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;
			var player = playerSystem.FindPlayerUnit();

			if (player == null)
			{
				lines.Add("[color=gray]장비 정보를 확인할 수 없습니다.[/color]");
				lines.Add("");
				lines.Add("[url=back]뒤로[/url]");
				return string.Join("\n", lines);
			}

			var equippedItems = inventorySystem.GetUnitEquippedItems(player.Id);

			if (equippedItems.Count == 0)
			{
				lines.Add("[color=gray]장착 중인 장비가 없다.[/color]");
			}
			else
			{
				foreach (var itemId in equippedItems)
				{
					var item = itemSystem.FindItem(itemId);
					if (item != null)
					{
						var itemName = GetNameWithOwner(item);
						// 아이템 메뉴로 연결 (장착 해제 가능)
						lines.Add($"  [url=item_inv_menu:{itemId}]{itemName}[/url]");
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
			var actionSystem = _hub.GetSystem("actionSystem") as ActionSystem;

			// 플레이어 정보 가져오기 (액션 필터링용)
			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var player = playerSystem.FindPlayerUnit();
			var item = itemSystem.FindItem(itemId);

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
			var itemName = GetNameWithOwner(item);
			lines.Add($"[b]{itemName}{countText}[/b]{valueText}");

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
			// 2. 아이템의 ActionProps로 필터링 (값이 0 이하면 비활성화)
			// 3. 플레이어의 can: prop으로 파티션 (가능/불가능 분리)
			var contextFiltered = actionSystem.GetFilteredActions(item.Actions, context);
			var actionPropsFiltered = actionSystem.FilterActionsByItemActionProps(contextFiltered, item);
			var partition = actionSystem.PartitionActionsByActor(actionPropsFiltered, player);
			if (partition.Enabled.Count > 0 || partition.Disabled.Count > 0)
			{
				lines.Add("[color=yellow]행동:[/color]");
				// 활성화된 액션 (링크)
				foreach (var action in partition.Enabled)
				{
					var (url, label) = actionSystem.GetActionUrlAndLabel(action, itemId, targetUnitId, context);
					lines.Add($"  [url={url}]{label}[/url]");
				}
				// 비활성화된 액션 (회색)
				foreach (var action in partition.Disabled)
				{
					var (_, label) = actionSystem.GetActionUrlAndLabel(action, itemId, targetUnitId, context);
					lines.Add($"  [color=gray]{label}[/color]");
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

			// 바닥에 버리기 (항상 표시, 클릭 시 조건 체크하여 다이얼로그로 이유 표시)
			// - 바닥 없음, 저주 아이템, 장착 중 등의 경우 다이얼로그로 안내
			if (context == "inventory")
			{
				lines.Add($"  [url=drop_floor:{itemId}]바닥에 버리기[/url]");
			}

			// 디버그: 아이템 props 보기 (can:debug_item_props가 있으면 표시)
			if (actionSystem.CanPerformAction(player, "debug_item_props"))
			{
				lines.Add($"  [url=call:debug_item_props]속성 보기[/url]");
			}

			if (partition.Enabled.Count > 0 || partition.Disabled.Count > 0 || (context == "inventory" && targetUnitId.HasValue))
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
		/// Proc은 비어있음 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}

	}
}
