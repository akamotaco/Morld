using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace SE
{
	public class UnitSystem : ECS.System
	{
		private readonly Dictionary<int, Unit> _units = new();

		public UnitSystem()
		{
		}

		/// <summary>
		/// 모든 유닛 (읽기 전용)
		/// </summary>
		public IReadOnlyDictionary<int, Unit> Units => _units;

		/// <summary>
		/// 유닛 추가
		/// </summary>
		public void AddUnit(Unit unit)
		{
			if (unit == null)
				throw new ArgumentNullException(nameof(unit));

			_units[unit.Id] = unit;
		}

		/// <summary>
		/// 유닛 제거
		/// </summary>
		public bool RemoveUnit(int id)
		{
			return _units.Remove(id);
		}

		/// <summary>
		/// 유닛 찾기
		/// </summary>
		public Unit? FindUnit(int id)
		{
			return _units.TryGetValue(id, out var unit) ? unit : null;
		}

		/// <summary>
		/// UniqueId로 유닛 찾기
		/// </summary>
		public Unit? FindByUniqueId(string uniqueId)
		{
			if (string.IsNullOrEmpty(uniqueId))
				return null;

			foreach (var unit in _units.Values)
			{
				if (unit.UniqueId == uniqueId)
					return unit;
			}
			return null;
		}

		/// <summary>
		/// 모든 유닛 제거
		/// </summary>
		public void ClearUnits()
		{
			_units.Clear();
		}

		/// <summary>
		/// 모든 유닛 제거 (챕터 전환용 alias)
		/// </summary>
		public void Clear()
		{
			ClearUnits();
			GD.Print("[UnitSystem] All units cleared.");
		}

		/// <summary>
		/// JSON 파일에서 유닛 데이터 로드
		/// </summary>
		public UnitSystem UpdateFromFile(string filePath)
		{
			using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
			if (file == null)
			{
				throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
			}
			var json = file.GetAsText();
			UpdateFromJson(json);
			return this;
		}

		/// <summary>
		/// JSON 문자열에서 유닛 데이터 로드
		/// </summary>
		public void UpdateFromJson(string json)
		{
			var options = new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true,
				WriteIndented = true
			};

			var dataList = JsonSerializer.Deserialize<UnitJsonData[]>(json, options);
			if (dataList == null)
				throw new InvalidOperationException("Failed to parse Unit JSON data");

			UpdateFromData(dataList);
		}

		/// <summary>
		/// UnitJsonData 배열로 유닛 데이터 로드
		/// </summary>
		private void UpdateFromData(UnitJsonData[] dataList)
		{
			// 기존 유닛 모두 제거
			ClearUnits();

			// 새 유닛 생성 및 추가
			foreach (var data in dataList)
			{
				var unit = new Unit(data.Id, data.Name, data.RegionId, data.LocationId);

				// Props 설정
				if (data.Tags != null)
				{
					unit.TraversalContext.SetProps(data.Tags);
				}

				// 타입 설정
				unit.Type = ParseUnitType(data.Type);

				// 액션 설정
				if (data.Actions != null)
				{
					unit.Actions.AddRange(data.Actions);
				}

				// ActionProps 설정
				if (data.ActionProps != null)
				{
					foreach (var (action, value) in data.ActionProps)
					{
						unit.ActionProps[action] = value;
					}
				}

				// Appearance 설정
				if (data.Appearance != null)
				{
					foreach (var (key, value) in data.Appearance)
					{
						unit.Appearance[key] = value;
					}
				}

				// Mood 설정
				if (data.Mood != null)
				{
					foreach (var mood in data.Mood)
					{
						unit.Mood.Add(mood);
					}
				}

				AddUnit(unit);
			}
		}

		/// <summary>
		/// 현재 유닛 데이터를 JSON 파일로 저장
		/// </summary>
		public void SaveToFile(string filePath)
		{
			var json = ToJson();

			using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Write);
			if (file == null)
			{
				throw new InvalidOperationException($"Failed to open file for writing: {filePath}");
			}
			file.StoreString(json);
		}

		/// <summary>
		/// 현재 유닛 데이터를 JSON 문자열로 변환
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
		/// UnitJsonData 배열로 변환
		/// 주의: Inventory와 EquippedItems는 InventorySystem에서 저장됨
		/// </summary>
		private UnitJsonData[] ExportToData()
		{
			return _units.Values.Select(unit => new UnitJsonData
			{
				Id = unit.Id,
				Name = unit.Name,
				RegionId = unit.CurrentLocation.RegionId,
				LocationId = unit.CurrentLocation.LocalId,
				Tags = unit.TraversalContext.Props.Count > 0
					? unit.TraversalContext.Props.ToDictionary()
					: null,
				Type = unit.Type.ToString().ToLower(),
				Actions = unit.Actions.Count > 0
					? new List<string>(unit.Actions)
					: null,
				ActionProps = unit.ActionProps.Count > 0
					? new Dictionary<string, int>(unit.ActionProps)
					: null,
				Appearance = unit.Appearance.Count > 0
					? new Dictionary<string, string>(unit.Appearance)
					: null,
				Mood = unit.Mood.Count > 0
					? new List<string>(unit.Mood)
					: null
			}).ToArray();
		}

		/// <summary>
		/// 문자열을 UnitType으로 변환
		/// </summary>
		private static UnitType ParseUnitType(string type)
		{
			return type.ToLower() switch
			{
				"male" => UnitType.Male,
				"female" => UnitType.Female,
				"object" => UnitType.Object,
				_ => UnitType.Male // 기본값
			};
		}

		/// <summary>
		/// JSON에서 읽은 인벤토리 데이터를 InventorySystem으로 마이그레이션
		/// (초기 로드 시 한번만 호출)
		/// </summary>
		public void MigrateInventoryData(string jsonFilePath, InventorySystem inventorySystem)
		{
			using var file = Godot.FileAccess.Open(jsonFilePath, Godot.FileAccess.ModeFlags.Read);
			if (file == null) return;

			var json = file.GetAsText();
			var options = new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true
			};

			var dataList = JsonSerializer.Deserialize<UnitJsonData[]>(json, options);
			if (dataList == null) return;

			foreach (var data in dataList)
			{
				// 인벤토리 마이그레이션
				if (data.Inventory != null)
				{
					foreach (var (itemId, count) in data.Inventory)
					{
						inventorySystem.AddItemToUnit(data.Id, itemId, count);
					}
				}

				// 장착 아이템 마이그레이션
				if (data.EquippedItems != null)
				{
					foreach (var itemId in data.EquippedItems)
					{
						inventorySystem.EquipItemOnUnit(data.Id, itemId);
					}
				}
			}

#if DEBUG_LOG
			GD.Print($"[UnitSystem] 인벤토리 데이터 마이그레이션 완료");
#endif
		}

		/// <summary>
		/// 디버그용 유닛 정보 출력
		/// </summary>
		public void DebugPrint()
		{
			var characters = _units.Values.Where(u => !u.IsObject).ToList();
			var objects = _units.Values.Where(u => u.IsObject).ToList();

			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"  캐릭터 수: {characters.Count}, 오브젝트 수: {objects.Count}");
			foreach (var unit in characters)
			{
				GD.Print($"  - {unit}");
				GD.Print($"    JobList: {unit.JobList.Count}개 Job");
				if (unit.CurrentJob != null)
				{
					GD.Print($"    현재 Job: {unit.CurrentJob.Name} ({unit.CurrentJob.Action}, {unit.CurrentJob.Duration}분)");
				}
				if (unit.TraversalContext.Props.Count > 0)
				{
					var props = string.Join(", ", unit.TraversalContext.Props.ToDictionary().Select(t => $"{t.Key}={t.Value}"));
					GD.Print($"    Props: {props}");
				}
				if (unit.Actions.Count > 0)
				{
					GD.Print($"    액션: {string.Join(", ", unit.Actions)}");
				}
			}
			foreach (var obj in objects)
			{
				GD.Print($"  - [Object] {obj.Name} @ {obj.CurrentLocation}");
				if (obj.Actions.Count > 0)
				{
					GD.Print($"    액션: {string.Join(", ", obj.Actions)}");
				}
			}
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
		}

		#region Look 기능

		/// <summary>
		/// 유닛 시점에서 현재 위치 정보 조회
		/// </summary>
		/// <param name="unit">조회 주체 유닛</param>
		/// <param name="viewerUnitId">조회하는 유닛의 ID (주변 유닛 목록에서 제외용)</param>
		public LookResult LookFromUnit(Unit unit, int viewerUnitId)
		{
			if (unit == null)
			{
				GD.Print("[UnitSystem.LookFromUnit] unit is null");
				return new LookResult();
			}

			// Pi-World: 이동 중이어도 같은 Location에 있음
			return LookFromLocation(unit, viewerUnitId);
		}

		/// <summary>
		/// Location에서 Look
		/// </summary>
		private LookResult LookFromLocation(Unit unit, int viewerUnitId)
		{
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
			var describeSystem = _hub.GetSystem("describeSystem") as DescribeSystem;
			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;
			var terrain = worldSystem.GetTerrain();
			var gameTime = worldSystem.GetTime();

			// 1. 현재 위치 정보
			var location = terrain.GetLocation(unit.CurrentLocation);
			var region = location != null ? terrain.GetRegion(location.RegionId) : null;

			// 챕터 전환 중 데이터가 없으면 빈 결과 반환
			if (location == null || region == null)
			{
				Godot.GD.Print($"[UnitSystem.LookFromLocation] returning 'loading' result - location={location != null}, region={region != null}, unitLoc={unit.CurrentLocation}");
				return new LookResult
				{
					Location = new LocationInfo
					{
						RegionName = "",
						LocationName = "로딩 중...",
						LocationRef = unit.CurrentLocation
					},
					UnitIds = new List<int>(),
					Routes = new List<RouteInfo>()
				};
			}

			var locationInfo = new LocationInfo
			{
				RegionName = region.Name ?? "",
				LocationName = describeSystem.GetNameWithOwner(location) ?? "",
				LocationRef = unit.CurrentLocation
			};

			// 2. 같은 위치에 있는 유닛들 (viewer 제외)
			// Pi-World: CurrentMovement가 있어도 같은 Location이면 표시
			var unitIds = new List<int>();
			foreach (var u in _units.Values)
			{
				if (u.Id == viewerUnitId) continue;

				// 같은 위치에 있는 유닛
				if (u.CurrentLocation == unit.CurrentLocation)
				{
					unitIds.Add(u.Id);
				}
			}

			// 3. 이동 가능한 경로들 (조건 필터링 적용)
			var routes = BuildRoutes(unit, terrain, itemSystem, inventorySystem);

			return new LookResult
			{
				Location = locationInfo,
				UnitIds = unitIds,
				Routes = routes
			};
		}

		/// <summary>
		/// 경로 정보 생성 (조건 필터링 적용)
		/// Terrain.BuildRawRoutes로 원시 데이터를 얻고, 표시 이름을 추가
		/// </summary>
		private List<RouteInfo> BuildRoutes(Unit unit, Terrain? terrain, ItemSystem? itemSystem, InventorySystem? inventorySystem)
		{
			var routes = new List<RouteInfo>();
			if (terrain == null) return routes;

			// InventorySystem에서 인벤토리 데이터 가져오기
			var inventory = inventorySystem?.GetUnitInventory(unit.Id);
			var equippedItems = inventorySystem?.GetUnitEquippedItems(unit.Id);
			var actualProps = unit.GetActualProps(itemSystem, inventory, equippedItems);

			var describeSystem = this._hub.GetSystem("describeSystem") as DescribeSystem;

			// Terrain에서 원시 경로 데이터 가져오기
			var rawRoutes = terrain.BuildRawRoutes(unit.CurrentLocation, actualProps);

			// 표시 이름 추가하여 RouteInfo로 변환
			foreach (var raw in rawRoutes)
			{
				var destLocation = terrain.GetLocation(raw.Destination);
				var destRegion = terrain.GetRegion(raw.Destination.RegionId);

				routes.Add(new RouteInfo
				{
					LocationName = describeSystem?.GetNameWithOwner(destLocation) ?? destLocation?.Name ?? "",
					RegionName = destRegion?.Name ?? "",
					Destination = raw.Destination,
					TravelTime = raw.TravelTime,
					IsRegionGate = raw.IsRegionGate,
					IsBlocked = raw.IsBlocked,
					BlockedReason = raw.BlockedReason,
					IsHidden = raw.IsHidden
				});
			}

			return routes;
		}

		/// <summary>
		/// 유닛 살펴보기 (캐릭터/오브젝트 통합)
		/// </summary>
		/// <param name="targetUnitId">살펴볼 대상 유닛 ID</param>
		/// <param name="viewerUnit">조회하는 유닛</param>
		public UnitLookResult? LookUnit(int targetUnitId, Unit viewerUnit)
		{
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;
			var scriptSystem = _hub.GetSystem("scriptSystem") as ScriptSystem;

			if (viewerUnit == null)
				return null;

			var unit = FindUnit(targetUnitId);
			if (unit == null)
				return null;

			// 유닛이 같은 위치에 있는지 확인
			if (unit.CurrentLocation != viewerUnit.CurrentLocation)
				return null;

			// InventorySystem에서 인벤토리 가져오기
			var inventory = unit.IsObject && inventorySystem != null
				? new Dictionary<int, int>(inventorySystem.GetUnitInventory(unit.Id))
				: new Dictionary<int, int>();

			// 캐릭터의 경우 상태 기반 액션 필터링 적용
			List<string> actions;
			string blockedMessage = null;

			if (!unit.IsObject && scriptSystem != null)
			{
				// Python에서 필터링된 액션 목록 조회
				var filteredActions = scriptSystem.GetFilteredActions(targetUnitId);
				if (filteredActions != null)
				{
					actions = filteredActions;
					blockedMessage = scriptSystem.GetActionBlockedMessage(targetUnitId);
				}
				else
				{
					actions = new List<string>(unit.Actions);
				}
			}
			else
			{
				actions = new List<string>(unit.Actions);
			}

			return new UnitLookResult
			{
				UnitId = unit.Id,
				Name = unit.Name,
				IsObject = unit.IsObject,
				Inventory = inventory,
				Actions = actions,
				BlockedMessage = blockedMessage
			};
		}

		#endregion
	}
}
