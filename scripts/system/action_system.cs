using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;
using System.Linq;

namespace SE
{
	/// <summary>
	/// 액션 시스템
	///
	/// - 액션 필터링 (can: prop 기반)
	/// - 액션 URL/라벨 생성
	/// - 차량 관련 액션 (C#에서 Terrain 데이터 접근 필요)
	/// </summary>
	public class ActionSystem : ECS.System
	{
		public ActionSystem()
		{
		}

		#region Action Filtering (can: prop based)

		/// <summary>
		/// 액션 파티션 결과 (가능/불가능 분리)
		/// </summary>
		public struct ActionPartition
		{
			public List<string> Enabled;   // 수행 가능한 액션
			public List<string> Disabled;  // 조건 불충족 액션 (회색 표시용)
		}

		/// <summary>
		/// 액션 문자열에서 액션 이름 추출 (can: prop 체크용)
		/// </summary>
		/// <remarks>
		/// 지원 형식:
		/// - "call:methodName:displayName" → "methodName"
		/// - "call:methodName" → "methodName"
		/// - "action@context" → "action"
		/// - "putinobject" → "putinobject"
		/// - "rest", "sleep" 등 → 그대로
		/// </remarks>
		public string ExtractActionName(string action)
		{
			// call:메서드명:표시명 또는 call:메서드명
			if (action.StartsWith("call:"))
			{
				var parts = action.Split(':');
				return parts.Length >= 2 ? parts[1] : action;
			}

			// action@context 형식 (take@container, equip@inventory 등)
			// @context는 아이템 위치에 따른 필터링용 (GetFilteredActions에서 처리)
			// 여기서는 can: 체크를 위해 액션 이름만 추출
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
		/// 장착 아이템의 EquipProps도 반영 (GetActualProps 사용)
		/// </summary>
		/// <param name="actor">행위자 Unit (플레이어 등)</param>
		/// <param name="action">액션 문자열</param>
		/// <returns>
		/// - 메서드명이 '*'로 끝나면 항상 true (can: 체크 스킵)
		/// - can:액션명 prop이 1 이상이면 true (정확한 매칭)
		/// - can:prefix* 형태의 prop이 있고 액션명이 prefix로 시작하면 true (wildcard 매칭)
		/// </returns>
		/// <remarks>
		/// Wildcard 매칭 규칙:
		/// - props 중 '*'로 끝나는 것이 있으면 glob 패턴 매칭
		/// - 예: can:debug_* prop이 있고 값 >= 1 이면 debug_로 시작하는 모든 액션 허용
		/// </remarks>
		public bool CanPerformAction(Unit actor, string action)
		{
			if (actor == null) return false;

			var actionName = ExtractActionName(action);

			// 메서드명이 '*'로 끝나면: can: 체크 없이 항상 통과
			// 예: call:view_errands*:의뢰 보기 → actionName = "view_errands*"
			if (actionName.EndsWith('*'))
			{
				return true;
			}

			// 장착 아이템의 EquipProps도 반영하기 위해 GetActualProps 사용
			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;

			IReadOnlyDictionary<int, int> inventory = null;
			IReadOnlyList<int> equippedItems = null;

			if (inventorySystem != null)
			{
				inventory = inventorySystem.GetUnitInventory(actor.Id);
				equippedItems = inventorySystem.GetUnitEquippedItems(actor.Id);
			}

			var actualProps = actor.GetActualProps(itemSystem, inventory, equippedItems);

			// 1. 정확한 매칭: can:액션명
			var canProp = $"can:{actionName}";
			if (actualProps.Props.HasAtLeast(canProp, 1))
			{
				return true;
			}

			// 2. Wildcard 매칭: props 중 "can:prefix*" 형태가 있으면 glob 매칭
			// 예: can:debug_* prop이 있고 actionName이 "debug_affection_up"이면 매칭
			foreach (var kvp in actualProps.Props)
			{
				var propName = kvp.Key.FullName;

				// can:으로 시작하고 *로 끝나는 prop 찾기
				if (propName.StartsWith("can:") && propName.EndsWith("*") && kvp.Value >= 1)
				{
					// "can:debug_*" → "debug_"
					var pattern = propName.Substring(4, propName.Length - 5); // "can:" 제거, "*" 제거
					if (actionName.StartsWith(pattern))
					{
						return true;
					}
				}
			}

			return false;
		}

		/// <summary>
		/// 액션 리스트를 Actor의 can: prop으로 가능/불가능으로 분리
		/// </summary>
		/// <param name="actions">원본 액션 리스트</param>
		/// <param name="actor">행위자 Unit</param>
		/// <returns>가능/불가능으로 분리된 액션 파티션</returns>
		/// <remarks>
		/// 마커 종류 (메서드명 끝에 붙임, 예: call:method*:표시명):
		/// - 마커 없음: 조건 맞으면 활성화, 안 맞으면 grey out
		/// - '#' (숨김): 조건 맞으면 표시, 안 맞으면 숨김
		/// - '*' (항상): can: 체크 없이 항상 활성화
		/// </remarks>
		public ActionPartition PartitionActionsByActor(List<string> actions, Unit actor)
		{
			var partition = new ActionPartition
			{
				Enabled = new List<string>(),
				Disabled = new List<string>()
			};

			if (actor == null || actions == null)
				return partition;

			foreach (var action in actions)
			{
				// '#'로 끝나는 액션: 조건 맞으면 표시, 안 맞으면 숨김
				// '#'가 없는 액션: 조건 맞으면 표시, 안 맞으면 grey out
				var isHiddenWhenDisabled = action.EndsWith("#");
				var actionToCheck = isHiddenWhenDisabled ? action.Substring(0, action.Length - 1) : action;

				// CanPerformAction에서 '*' 마커 체크 (ExtractActionName으로 메서드명 추출)
				if (CanPerformAction(actor, actionToCheck))
				{
					partition.Enabled.Add(actionToCheck);
				}
				else if (!isHiddenWhenDisabled)
				{
					partition.Disabled.Add(action);
				}
			}
			return partition;
		}

		/// <summary>
		/// 액션 리스트에서 현재 context에 해당하는 액션만 필터링
		/// </summary>
		public List<string> GetFilteredActions(List<string> actions, string context)
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
		/// 아이템의 ActionProps를 기반으로 액션 필터링
		/// ActionProps에 해당 액션이 있고 값이 0 이하면 필터링
		/// </summary>
		public List<string> FilterActionsByItemActionProps(List<string> actions, Item item)
		{
			var result = new List<string>();
			foreach (var action in actions)
			{
				// 액션 이름 추출 (call:method:label → method, equip → equip)
				var actionName = ExtractActionName(action);

				// ActionProps에 해당 액션이 있고 값이 0 이하면 필터링
				if (item.ActionProps.TryGetValue(actionName, out int value) && value <= 0)
				{
					continue; // 비활성화된 액션
				}

				result.Add(action);
			}
			return result;
		}

		#endregion

		#region Action URL/Label Generation

		/// <summary>
		/// 액션 이름을 URL과 표시 라벨로 변환
		/// </summary>
		public (string url, string label) GetActionUrlAndLabel(string action, int itemId, int? unitId, string context)
		{
			// call:메서드명:표시명 형식 처리
			// Focus.ItemId/TargetUnitId에서 instanceId를 가져오므로 URL에 ID 포함 불필요
			if (action.StartsWith("call:"))
			{
				var parts = action.Split(':');
				if (parts.Length >= 3)
				{
					// call:메서드명:표시명 → URL: call:메서드명:표시명, Label: 표시명
					return ($"call:{parts[1]}:{parts[2]}", parts[2]);
				}
				else if (parts.Length == 2)
				{
					// call:메서드명 (표시명 없음) → URL: call:메서드명:메서드명, Label: 메서드명
					return ($"call:{parts[1]}:{parts[1]}", parts[1]);
				}
			}

			// equip 액션: 장착 상태에 따라 equip 또는 unequip URL 반환
			// 라벨은 아이템 슬롯 타입에 따라 결정: 착용: → 입기/벗기, 장착: → 장착/장착 해제
			if (action == "equip")
			{
				var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
				var _inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;
				var _itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
				var player = playerSystem.FindPlayerUnit();
				if (player == null)
				{
					throw new InvalidOperationException("[ActionSystem] GetActionUrlAndLabel: Player not found for equip action");
				}
				bool isEquipped = _inventorySystem.IsEquippedOnUnit(player.Id, itemId);

				// 아이템의 슬롯 타입에 따라 라벨 결정
				string equipLabel = "장착";
				string unequipLabel = "장착 해제";
				var item = _itemSystem?.FindItem(itemId);
				if (item != null)
				{
					// 착용: 슬롯이 있으면 의류 → 입기/벗기
					var wearSlotKeys = item.GetAllEquipPropKeys("착용:");
					if (wearSlotKeys.Count > 0)
					{
						equipLabel = "입기";
						unequipLabel = "벗기";
					}
				}

				if (isEquipped)
					return ($"unequip:{itemId}", unequipLabel);
				else
					return ($"equip:{itemId}", equipLabel);
			}

			return action switch
			{
				// take는 container에서 가져가기 - call:take로 처리
				"take" when context == "container" => ($"call:take:{itemId}", "가져가기"),
				"use" => ($"item_use:{itemId}", "사용"),
				"throw" => ($"throw:{itemId}", "던지기"),
				_ => ($"action:{action}:{itemId}", action) // 알 수 없는 액션은 그대로
			};
		}

		/// <summary>
		/// 액션 라인 포맷팅 (활성화/비활성화에 따라 링크 또는 회색 텍스트)
		/// </summary>
		/// <param name="action">액션 문자열</param>
		/// <param name="unitId">대상 유닛 ID</param>
		/// <param name="enabled">활성화 여부</param>
		/// <returns>포맷된 BBCode 문자열</returns>
		public string FormatActionLine(string action, int unitId, bool enabled)
		{
			// putinobject 액션은 call:put으로 변환
			if (action == "putinobject")
			{
				return enabled
					? "  [url=call:put]넣기[/url]"
					: "  [color=gray]넣기[/color]";
			}

			// call:메서드명:표시명 형식
			if (action.StartsWith("call:"))
			{
				var parts = action.Split(':');
				if (parts.Length >= 3)
				{
					var methodName = parts[1];
					var displayName = parts[2];
					return enabled
						? $"  [url=call:{methodName}:{displayName}]{displayName}[/url]"
						: $"  [color=gray]{displayName}[/color]";
				}
				else if (parts.Length == 2)
				{
					var methodName = parts[1];
					return enabled
						? $"  [url=call:{methodName}:{methodName}]{methodName}[/url]"
						: $"  [color=gray]{methodName}[/color]";
				}
				else
				{
					GD.PrintErr($"[ActionSystem] Invalid call action format: '{action}'");
					return $"  [color=red][오류: {action}][/color]";
				}
			}

			// 다른 액션은 그대로 표시
			return enabled
				? $"  [url=action:{action}:{unitId}]{action}[/url]"
				: $"  [color=gray]{action}[/color]";
		}

		/// <summary>
		/// 특정 can: prop을 제공하는 장착 장비 반환
		/// </summary>
		/// <param name="actor">행위자 Unit</param>
		/// <param name="canProp">찾을 can: prop (예: "can:chop")</param>
		/// <returns>해당 prop을 제공하는 장착 아이템, 없으면 null</returns>
		public Item GetEquipmentSource(Unit actor, string canProp)
		{
			if (actor == null || string.IsNullOrEmpty(canProp))
				return null;

			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;

			if (itemSystem == null || inventorySystem == null)
				return null;

			var equippedItems = inventorySystem.GetUnitEquippedItems(actor.Id);
			if (equippedItems == null)
				return null;

			// 장착 아이템 중 해당 can: prop을 가진 아이템 찾기
			foreach (var itemId in equippedItems)
			{
				var item = itemSystem.FindItem(itemId);
				if (item == null) continue;

				// EquipProps에 해당 canProp이 있고 값이 1 이상인지 확인
				if (item.EquipProps.TryGetValue(canProp, out int value) && value >= 1)
				{
					return item;
				}
			}

			return null;
		}

		#endregion

		#region Action Text Generation

		/// <summary>
		/// 행동 옵션 텍스트만 생성 (구분선 포함)
		/// TextUISystem에서 Python 훅 폴백으로 사용
		/// </summary>
		public string GetActionText(LookResult lookResult)
		{
			var lines = new List<string>();

			// 구분선
			lines.Add(TextUISystem.Divider);

			// GetActionItems에서 행동 옵션 가져오기
			var actionItems = GetActionItems(lookResult);
			lines.AddRange(actionItems);

			return string.Join("\n", lines);
		}

		/// <summary>
		/// 행동 옵션 BBCode 리스트 생성 (Python에서 사용)
		/// 이동 경로, 앉은 상태 행동 포함
		/// 멍때리기 등의 일반 행동은 Python ui.py에서 처리
		/// </summary>
		public List<string> GetActionItems(LookResult lookResult)
		{
			var items = new List<string>();

			var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			var player = playerSystem.FindPlayerUnit();

			// 1. 이동 가능 경로
			if (lookResult.Routes.Count > 0)
			{
				items.Add("[color=cyan]이동 가능:[/color]");
				foreach (var route in lookResult.Routes)
				{
					// 숨김 처리 (조건 키에 # 마커가 있고 조건 미충족)
					if (route.IsHidden)
						continue;

					if (route.IsBlocked)
					{
						// grey out 처리 (조건 미충족)
						items.Add($"  [color=gray]- {route.LocationName}[/color]");
					}
					else
					{
						// 활성화 (이동 가능)
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
						// TODO: stand_up을 call:stand_up으로 전환 필요
						// items.Add($"  [url=stand_up]일어나기[/url]");

						// 운전석이면 운전 액션도 표시 (TODO: drive 메서드 구현 필요)
						if (seatObject != null && seatObject.TraversalContext.HasProp("driver_seat"))
						{
							items.Add($"  [url=call:drive]운전[/url]");
						}
					}
				}
			}

			return items;
		}

		#endregion

		#region Vehicle Actions

		/// <summary>
		/// 유닛이 운전 가능한 상태인지 확인
		/// 운전석에 앉아있고 차량이 있어야 함
		/// </summary>
		public bool CanDrive(Unit unit)
		{
			// seated_on prop으로 앉아있는 오브젝트 확인
			var seatedOnProps = unit.TraversalContext.Props.GetByType("seated_on").ToList();
			if (seatedOnProps.Count == 0) return false;

			var seatedOnValue = seatedOnProps.First().Value;
			if (seatedOnValue <= 0) return false;

			// 앉아있는 오브젝트가 driver_seat인지 확인
			if (_hub.GetSystem("unitSystem") is not UnitSystem unitSystem) return false;

			var seat = unitSystem.FindUnit(seatedOnValue);
			if (seat == null) return false;

			// driver_seat prop 확인
			return seat.TraversalContext.HasProp("driver_seat");
		}

		/// <summary>
		/// 운전 가능한 목적지 목록 가져오기
		/// 차량 Location에서 RegionEdge로 연결된 외부 Location들을 반환
		/// </summary>
		public List<(int regionId, int locationId, string name, int travelTime)> GetDrivableDestinations(Unit unit)
		{
			var destinations = new List<(int, int, string, int)>();

			if (_hub.GetSystem("worldSystem") is not WorldSystem worldSystem) return destinations;

			var terrain = worldSystem.GetTerrain();
			var currentLoc = unit.CurrentLocation;

			// 현재 위치에서 RegionEdge를 통해 연결된 외부 Location 찾기
			// 차량은 별도 Region에 있고, RegionEdge로 외부와 연결됨
			foreach (var (edge, destination, travelTime) in terrain.GetRegionExits(currentLoc, unit.TraversalContext))
			{
				// 목적지 정보 가져오기
				var destRegion = terrain.GetRegion(destination.RegionId);
				if (destRegion == null) continue;

				var destLocation = destRegion.GetLocation(destination.LocalId);
				if (destLocation == null) continue;

				// 실내는 차량 이동 불가
				if (destLocation.IsIndoor) continue;

				var name = destLocation.Name ?? $"Location {destination.LocalId}";
				destinations.Add((destination.RegionId, destination.LocalId, name, (int)travelTime));
			}

			return destinations;
		}

		/// <summary>
		/// 운전 액션 적용 (이동 시작)
		/// </summary>
		public ActionResult ApplyDriveAction(Unit unit, int destRegionId, int destLocationId)
		{
			// 운전 가능한지 확인
			if (!CanDrive(unit))
				return ActionResult.Fail("운전석에 앉아있지 않습니다.");

			// 목적지가 유효한지 확인
			var destinations = GetDrivableDestinations(unit);
			var dest = destinations.Find(d => d.regionId == destRegionId && d.locationId == destLocationId);
			if (dest == default)
				return ActionResult.Fail("해당 목적지로 운전할 수 없습니다.");

			// 운전 실행
			return ExecuteDrive(unit, destRegionId, destLocationId, dest.travelTime);
		}

		/// <summary>
		/// 실제 운전 실행 (RegionEdge의 LocationA 변경)
		/// 차량 이동 = RegionEdge의 외부 연결 지점 변경
		/// </summary>
		private ActionResult ExecuteDrive(Unit driver, int destRegionId, int destLocationId, int travelTime)
		{
			if (_hub.GetSystem("worldSystem") is not WorldSystem worldSystem)
				return ActionResult.Fail("WorldSystem을 찾을 수 없습니다.");

			// 목적지 이름 가져오기
			var terrain = worldSystem.GetTerrain();
			var destRegion = terrain.GetRegion(destRegionId);
			var destLocation = destRegion.GetLocation(destLocationId);
			var destName = destLocation.Name ?? $"Location {destLocationId}";

			// 현재 위치 (차량 Location)
			var currentLoc = driver.CurrentLocation;

			// 현재 연결된 RegionEdge 찾기
			var regionEdges = terrain.GetRegionEdgesFrom(currentLoc).ToList();
			if (regionEdges.Count == 0)
				return ActionResult.Fail("차량이 연결된 경로를 찾을 수 없습니다.");

			// 첫 번째 RegionEdge의 외부 Location을 목적지로 변경
			var edge = regionEdges.First();

			// RegionEdge의 외부 쪽(LocationA 또는 LocationB) 변경
			// 차량 Region 쪽이 아닌 외부 Region 쪽을 변경
			if (edge.LocationA.RegionId == currentLoc.RegionId)
			{
				// LocationA가 차량 쪽 → LocationB를 변경
				edge.LocationB = new LocationRef(destRegionId, destLocationId);
			}
			else
			{
				// LocationB가 차량 쪽 → LocationA를 변경
				edge.LocationA = new LocationRef(destRegionId, destLocationId);
			}

			// 탑승자들은 차량 Location에 계속 머무름 (위치 변경 없음)
			// RegionEdge만 변경되므로 탑승자 처리 불필요

			return ActionResult.Ok($"{destName}(으)로 이동했다.", timeConsumed: travelTime);
		}

		#endregion

		/// <summary>
		/// 디버그용 출력
		/// </summary>
		public void DebugPrint()
		{
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print("  ActionSystem 로드됨 (차량 전용)");
			GD.Print("  지원: CanDrive, GetDrivableDestinations, ApplyDriveAction");
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}
	}
}
