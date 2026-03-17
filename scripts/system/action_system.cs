using ECS;
using Godot;
using Morld;
using Morld.TextUI;
using System;
using System.Collections.Generic;
using static Morld.TextUI.UIStyle;
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
		/// <summary>
		/// 적대 행동 메서드명 (빨간색 표시)
		/// </summary>
		private static readonly HashSet<string> _hostileMethodNames = new()
		{
			"attack", "aimed_attack_head", "aimed_attack_arms", "aimed_attack_legs",
			"steal", "finish_off", "combat_harass", "harass"
		};

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
					: $"  {StyleMuted("넣기")}";
			}

			// call:메서드명:표시명 형식
			if (action.StartsWith("call:"))
			{
				var parts = action.Split(':');
				if (parts.Length >= 3)
				{
					var methodName = parts[1];
					var displayName = parts[2];
					if (enabled)
					{
						var label = _hostileMethodNames.Contains(methodName)
							? StyleDanger(displayName)
							: displayName;
						return $"  [url=call:{methodName}:{displayName}]{label}[/url]";
					}
					return $"  {StyleMuted(displayName)}";
				}
				else if (parts.Length == 2)
				{
					var methodName = parts[1];
					return enabled
						? $"  [url=call:{methodName}:{methodName}]{methodName}[/url]"
						: $"  {StyleMuted(methodName)}";
				}
				else
				{
					GD.PrintErr($"[ActionSystem] Invalid call action format: '{action}'");
					return $"  {StyleDanger($"[오류: {action}]")}";
				}
			}

			// 다른 액션은 그대로 표시
			return enabled
				? $"  [url=action:{action}:{unitId}]{action}[/url]"
				: $"  {StyleMuted(action)}";
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

			// 1. 이동 경로는 Python ui.py에서 morld.get_movement_info()로 렌더링

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
						items.Add(StyleSuccess($"[앉음: {seatName}]"));
						items.Add($"  [url=call:stand_up:{objectId}]일어나기[/url]");

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
		/// 차량 위치에서 직접 연결된 실외 Location 목록 반환
		///
		/// 같은 Region 내 LocationGate + 다른 Region의 RegionGate 모두 탐색.
		/// 실내(IsIndoor) Location은 제외.
		/// </summary>
		/// <param name="vehicleId">차량 Object의 Unit ID</param>
		/// <returns>목적지 리스트: (regionId, locationId, name, distance)</returns>
		public List<(int regionId, int locationId, string name, float distance)> GetVehicleDestinations(int vehicleId)
		{
			var destinations = new List<(int, int, string, float)>();

			if (_hub.GetSystem("unitSystem") is not UnitSystem unitSystem) return destinations;
			if (_hub.GetSystem("worldSystem") is not WorldSystem worldSystem) return destinations;

			var vehicle = unitSystem.FindUnit(vehicleId);
			if (vehicle == null) return destinations;

			var terrain = worldSystem.GetTerrain();
			var currentLoc = vehicle.CurrentLocation;
			var region = terrain.GetRegion(currentLoc.RegionId);
			if (region == null) return destinations;

			// 1. 같은 Region 내 LocationGate 이웃 (실외만)
			var location = region.GetLocation(currentLoc.LocalId);
			if (location != null)
			{
				foreach (var (neighbor, distance) in region.GetTraversableNeighbors(location))
				{
					if (neighbor.IsIndoor) continue;
					var name = neighbor.Name ?? $"Location {neighbor.LocalId}";
					destinations.Add((currentLoc.RegionId, neighbor.LocalId, name, distance));
				}
			}

			// 2. 다른 Region의 RegionGate 이웃 (실외만)
			foreach (var (rGate, destination, distance) in terrain.GetRegionExits(currentLoc))
			{
				var destRegion = terrain.GetRegion(destination.RegionId);
				if (destRegion == null) continue;

				var destLocation = destRegion.GetLocation(destination.LocalId);
				if (destLocation == null) continue;

				if (destLocation.IsIndoor) continue;

				var name = destLocation.Name ?? $"Location {destination.LocalId}";
				destinations.Add((destination.RegionId, destination.LocalId, name, distance));
			}

			return destinations;
		}

		/// <summary>
		/// 차량 + 탑승자 일괄 위치 이동 (seated 상태 유지)
		///
		/// set_unit_location과 달리 stand_up 하지 않음.
		/// 탑승자의 seated_on/seated_by prop을 유지한 채 이동.
		/// </summary>
		/// <param name="vehicleId">차량 Object ID</param>
		/// <param name="destRegionId">목적지 Region</param>
		/// <param name="destLocationId">목적지 Location</param>
		/// <returns>이동된 유닛 수 (차량 포함)</returns>
		public int VehicleRelocate(int vehicleId, int destRegionId, int destLocationId)
		{
			if (_hub.GetSystem("unitSystem") is not UnitSystem unitSystem) return 0;

			var vehicle = unitSystem.FindUnit(vehicleId);
			if (vehicle == null) return 0;

			var destRef = new LocationRef(destRegionId, destLocationId);
			int movedCount = 0;

			// 1. 탑승자 이동 (seated 유지 — stand_up 없음)
			var seatedByProps = vehicle.TraversalContext.Props.GetByType("seated_by").ToList();
			foreach (var (prop, value) in seatedByProps)
			{
				if (value <= 0) continue;

				var passenger = unitSystem.FindUnit(value);
				if (passenger == null) continue;

				passenger.SetLocation2D(destRef, 0, 0);
				movedCount++;
			}

			// 2. 차량 자체 이동
			vehicle.SetLocation2D(destRef, 0, 0);
			movedCount++;

			GD.Print($"[ActionSystem] VehicleRelocate: vehicle={vehicleId} -> {destRegionId}:{destLocationId} ({movedCount} units moved)");
			return movedCount;
		}

		/// <summary>
		/// 대형 차량 내부 Location의 RegionGate 연결점을 새 외부 Location으로 변경
		///
		/// 차량 이동 시 내부 Location의 Gate가 가리키는 외부 위치를 갱신.
		/// 내부 Location 측(interiorRef)은 고정, 반대편(외부)만 변경.
		/// </summary>
		/// <param name="interiorRegionId">내부 Location의 Region ID</param>
		/// <param name="interiorLocalId">내부 Location의 Local ID</param>
		/// <param name="newExtRegionId">새 외부 Region ID</param>
		/// <param name="newExtLocalId">새 외부 Location ID</param>
		/// <returns>성공 여부</returns>
		public bool ReconnectInteriorGate(int interiorRegionId, int interiorLocalId,
			int newExtRegionId, int newExtLocalId)
		{
			if (_hub.GetSystem("worldSystem") is not WorldSystem worldSystem) return false;

			var terrain = worldSystem.GetTerrain();
			var interiorRef = new LocationRef(interiorRegionId, interiorLocalId);

			// 내부 Location에서 나가는 RegionGate 찾기
			foreach (var rGate in terrain.GetRegionGatesFrom(interiorRef))
			{
				// 외부 쪽(반대편) 연결점 변경
				var newExtRef = new LocationRef(newExtRegionId, newExtLocalId);
				if (rGate.LocationA == interiorRef)
				{
					rGate.LocationB = newExtRef;
				}
				else
				{
					rGate.LocationA = newExtRef;
				}

				GD.Print($"[ActionSystem] ReconnectInteriorGate: {interiorRegionId}:{interiorLocalId} -> ext {newExtRegionId}:{newExtLocalId}");
				return true;
			}

			GD.PrintErr($"[ActionSystem] ReconnectInteriorGate: no gate from {interiorRegionId}:{interiorLocalId}");
			return false;
		}

		#endregion

		/// <summary>
		/// 디버그용 출력
		/// </summary>
		public void DebugPrint()
		{
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print("  ActionSystem 로드됨");
			GD.Print("  지원: GetVehicleDestinations, VehicleRelocate, ReconnectInteriorGate");
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}
	}
}
