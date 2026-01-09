#define DEBUG_LOG

using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace SE
{
	/// <summary>
	/// 플레이어 입력 기반 시간 진행 시스템
	/// - 입력이 없으면 시간 정지 (duration = 0)
	/// - RequestTimeAdvance()로 시간 진행 요청
	/// - 플레이어 명령 = 스케줄 스택에 push
	/// </summary>
	public class PlayerSystem : ECS.System
	{
		/// <summary>
		/// 다음 Step에서 진행할 시간 (분)
		/// </summary>
		public int NextStepDuration { get; private set; } = 0;

		/// <summary>
		/// 아직 처리해야 할 남은 시간 (분)
		/// </summary>
		private int _remainingDuration = 0;

		/// <summary>
		/// 이전 Step에서 설정한 시간 (이번 Step에서 실제 소비된 시간)
		/// </summary>
		private int _lastSetDuration = 0;

		/// <summary>
		/// 현재 활성화된 액션 이름 (디버그용)
		/// </summary>
		private string _currentAction = "";

		/// <summary>
		/// 플레이어 유닛 ID
		/// </summary>
		public int PlayerId { get; set; } = 0;

		public PlayerSystem()
		{
		}

		/// <summary>
		/// 초과 시간 추가 (다이얼로그에서 NextStepDuration 초과 시)
		/// 플레이어가 이미 소비한 시간이므로 입력 없이 자동 처리됨
		/// </summary>
		public void AddExcessTime(int minutes)
		{
			_remainingDuration += minutes;
#if DEBUG_LOG
			GD.Print($"[PlayerSystem] ExcessTime 추가: +{minutes}분 (총 대기: {_remainingDuration}분)");
#endif
		}

		/// <summary>
		/// 플레이어 유닛 접근 헬퍼
		/// </summary>
		public Unit? GetPlayerUnit()
		{
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			return unitSystem.FindUnit(PlayerId);
		}

		/// <summary>
		/// 시간 진행 요청 (외부에서 호출)
		/// </summary>
		/// <param name="minutes">진행할 시간 (분)</param>
		/// <param name="actionName">액션 이름 (디버그용)</param>
		public void RequestTimeAdvance(int minutes, string actionName = "")
		{
			_remainingDuration += minutes;
			_currentAction = actionName;

#if DEBUG_LOG
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"[PlayerSystem] 시간 진행 요청!");
			GD.Print($"  액션: {actionName}");
			GD.Print($"  요청 시간: {minutes}분");
			GD.Print($"  총 대기 시간: {_remainingDuration}분");
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
		}

		/// <summary>
		/// 현재 대기 중인 시간이 있는지
		/// </summary>
		public bool HasPendingTime => _remainingDuration > 0;

		/// <summary>
		/// 다음 Step 시간 조정 (EventPredictionSystem에서 호출)
		/// </summary>
		/// <param name="adjustedMinutes">조정할 시간 (분)</param>
		public void AdjustNextStepDuration(int adjustedMinutes)
		{
			if (adjustedMinutes <= 0 || adjustedMinutes >= NextStepDuration)
				return;

#if DEBUG_LOG
			GD.Print($"[PlayerSystem] NextStepDuration 조정: {NextStepDuration} → {adjustedMinutes}분");
#endif

			NextStepDuration = adjustedMinutes;
			_lastSetDuration = adjustedMinutes;
		}

		#region 플레이어 액션 요청

		/// <summary>
		/// 통합 명령 처리
		/// 포맷: "이동:regionId:localId" 또는 "휴식:minutes"
		/// </summary>
		public void RequestCommand(string cmd)
		{
			if (string.IsNullOrEmpty(cmd))
				return;

			var parts = cmd.Split(':');
			var action = parts[0];

			switch (action)
			{
				case "이동":
					if (parts.Length >= 3 &&
						int.TryParse(parts[1], out int regionId) &&
						int.TryParse(parts[2], out int localId))
					{
						ExecuteMove(new LocationRef(regionId, localId));
					}
					break;
				case "휴식":
					if (parts.Length >= 2 && int.TryParse(parts[1], out int minutes))
					{
						ExecuteIdle(minutes);
					}
					break;
				default:
#if DEBUG_LOG
					GD.Print($"[PlayerSystem] 알 수 없는 명령: {action}");
#endif
					break;
			}
		}

		/// <summary>
		/// 이동 시간 계산 (확인 다이얼로그용)
		/// </summary>
		/// <returns>이동 시간 (분), 경로가 없으면 -1</returns>
		public int CalculateTravelTime(int regionId, int localId)
		{
			var destination = new LocationRef(regionId, localId);
			var player = GetPlayerUnit();
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;

			if (player == null || worldSystem == null)
				return -1;

			var terrain = worldSystem.GetTerrain();

			// 이미 목적지에 있으면 0
			if (player.CurrentLocation == destination)
				return 0;

			// 아이템 효과가 반영된 Prop으로 경로 탐색
			var inventory = inventorySystem.GetUnitInventory(player.Id);
			var equippedItems = inventorySystem.GetUnitEquippedItems(player.Id);
			var actualProps = player.GetActualProps(itemSystem, inventory, equippedItems);
			var pathResult = terrain.FindPath(player.CurrentLocation, destination, actualProps);

			if (!pathResult.Found || pathResult.Path.Count < 2)
				return -1;

			return CalculateTotalTravelTime(pathResult, terrain);
		}

		/// <summary>
		/// 이동 실행 (JobList에 이동 Job 삽입)
		/// </summary>
		private void ExecuteMove(LocationRef destination)
		{
			var player = GetPlayerUnit();
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;

			if (player == null || worldSystem == null)
				return;

			var terrain = worldSystem.GetTerrain();

			// 이미 목적지에 있으면 무시
			if (player.CurrentLocation == destination)
				return;

			// 아이템 효과가 반영된 Prop으로 경로 탐색
			var inventory = inventorySystem.GetUnitInventory(player.Id);
			var equippedItems = inventorySystem.GetUnitEquippedItems(player.Id);
			var actualProps = player.GetActualProps(itemSystem, inventory, equippedItems);
			var pathResult = terrain.FindPath(player.CurrentLocation, destination, actualProps);

			if (!pathResult.Found || pathResult.Path.Count < 2)
			{
#if DEBUG_LOG
				GD.Print($"[PlayerSystem] 경로를 찾을 수 없음: {player.CurrentLocation} → {destination}");
#endif
				return;
			}

			// 총 이동 시간 계산
			var totalTime = CalculateTotalTravelTime(pathResult, terrain);

			// JobList에 이동 Job 삽입 (플레이어는 스케줄 없음 → 단순 Insert)
			var destLocation = terrain.GetLocation(destination);
			var moveJob = new Job
			{
				Name = $"{destLocation.Name ?? destination.ToString()}(으)로 이동",
				Action = "move",
				RegionId = destination.RegionId,
				LocationId = destination.LocalId,
				Duration = totalTime,
				TargetId = null
			};
			player.InsertJobWithClear(moveJob);

			// 시간 진행 요청
			RequestTimeAdvance(totalTime, moveJob.Name);

#if DEBUG_LOG
			GD.Print($"[PlayerSystem] 이동 요청: {player.CurrentLocation} → {destination} ({totalTime}분)");
#endif
		}

		/// <summary>
		/// 휴식 실행 (스택 변화 없이 시간만 진행)
		/// </summary>
		private void ExecuteIdle(int minutes)
		{
			// 시간 진행 요청 (스택 변화 없음)
			RequestTimeAdvance(minutes, $"휴식 ({minutes}분)");

#if DEBUG_LOG
			GD.Print($"[PlayerSystem] 휴식 요청: {minutes}분");
#endif
		}

		/// <summary>
		/// 경로의 총 이동 시간 계산
		/// </summary>
		private int CalculateTotalTravelTime(PathResult pathResult, Terrain terrain)
		{
			if (!pathResult.Found || pathResult.Path.Count < 2)
				return 0;

			int totalTime = 0;
			for (int i = 0; i < pathResult.Path.Count - 1; i++)
			{
				var from = new LocationRef(pathResult.Path[i]);
				var to = new LocationRef(pathResult.Path[i + 1]);
				totalTime += GetTravelTime(from, to, terrain);
			}
			return totalTime;
		}

		/// <summary>
		/// 두 Location 간 이동 시간 계산
		/// </summary>
		private int GetTravelTime(LocationRef from, LocationRef to, Terrain terrain)
		{
			// 같은 Region 내 이동
			if (from.RegionId == to.RegionId)
			{
				var region = terrain.GetRegion(from.RegionId);
				var edge = region.GetEdgeBetween(from.LocalId, to.LocalId);

				if (edge != null)
				{
					var travelTime = edge.LocationA.LocalId == from.LocalId
						? edge.TravelTimeAtoB
						: edge.TravelTimeBtoA;
					return travelTime >= 0 ? travelTime : 1;
				}
			}
			else
			{
				// Region 간 이동
				foreach (var regionEdge in terrain.RegionEdges)
				{
					var locA = regionEdge.LocationA;
					var locB = regionEdge.LocationB;

					if (locA.RegionId == from.RegionId && locA.LocalId == from.LocalId &&
						locB.RegionId == to.RegionId && locB.LocalId == to.LocalId)
					{
						return regionEdge.TravelTimeAtoB >= 0 ? regionEdge.TravelTimeAtoB : 1;
					}
					else if (locB.RegionId == from.RegionId && locB.LocalId == from.LocalId &&
							 locA.RegionId == to.RegionId && locA.LocalId == to.LocalId)
					{
						return regionEdge.TravelTimeBtoA >= 0 ? regionEdge.TravelTimeBtoA : 1;
					}
				}
			}

			return 1;
		}

		#endregion

		#region 유닛 조회

		/// <summary>
		/// 유닛 살펴보기 (캐릭터/오브젝트 통합)
		/// </summary>
		public UnitLookResult? LookUnit(int unitId)
		{
			var player = GetPlayerUnit();
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;

			if (player == null || unitSystem == null)
				return null;

			var unit = unitSystem.FindUnit(unitId);
			if (unit == null)
				return null;

			// 유닛이 같은 위치에 있는지 확인
			if (unit.CurrentLocation != player.CurrentLocation)
				return null;

			var describeSystem = _hub.GetSystem("describeSystem") as DescribeSystem;

			// InventorySystem에서 인벤토리 가져오기
			var inventory = unit.IsObject && inventorySystem != null
				? new Dictionary<int, int>(inventorySystem.GetUnitInventory(unit.Id))
				: new Dictionary<int, int>();

			return new UnitLookResult
			{
				UnitId = unit.Id,
				Name = unit.Name,
				IsObject = unit.IsObject,
				Inventory = inventory,
				Actions = new List<string>(unit.Actions),
				AppearanceText = describeSystem.GetUnitAppearance(unit) ?? ""
			};
		}

		#endregion

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;

			if (worldSystem == null)
				return;

			var time = worldSystem.GetTime();

			// 1. 이전 Step에서 설정한 시간을 차감 (이번 Step에서 실제 소비됨)
			if (_lastSetDuration > 0)
			{
				_remainingDuration -= _lastSetDuration;

#if DEBUG_LOG
				GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
				GD.Print($"[PlayerSystem] Step 완료");
				GD.Print($"  현재 시간: {time}");
				GD.Print($"  액션: {_currentAction}");
				GD.Print($"  소비된 시간: {_lastSetDuration}분");
				GD.Print($"  남은 시간: {_remainingDuration}분");
				if (_remainingDuration > 0)
				{
					GD.Print($"  ⚠ 다음 Step에서 계속 진행 예정");
				}
				else
				{
					GD.Print($"  ✓ 완료!");
					_currentAction = "";
				}
				GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
			}

			// 2. EventSystem에서 ExcessTime 가져와서 적용
			{
				var _eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;
				var excessTime = _eventSystem.ConsumeExcessTime();
				if (excessTime > 0)
				{
					AddExcessTime(excessTime);
				}
			}

			// 3. 대기 중인 시간이 없으면 시간 정지
			if (_remainingDuration <= 0)
			{
				NextStepDuration = 0;
				_lastSetDuration = 0;
				return;
			}

			// 4. 자정까지 남은 시간 계산 (1440분 = 24시간)
			var minutesToMidnight = 1440 - time.MinuteOfDay;
			if (minutesToMidnight <= 0) minutesToMidnight = 1440;

			// 5. 다음 Step에서 진행할 시간 설정 (자정 제한)
			NextStepDuration = Math.Min(_remainingDuration, minutesToMidnight);
			_lastSetDuration = NextStepDuration;

#if DEBUG_LOG
			GD.Print($"[PlayerSystem] 다음 Step 예약: {NextStepDuration}분");
#endif
		}

		#region Look 기능

		/// <summary>
		/// 현재 플레이어 위치의 정보 조회
		/// </summary>
		public LookResult Look()
		{
			var player = GetPlayerUnit();
			if (player == null)
				return new LookResult();

			// 이동 중인 경우도 처리 (런타임에서는 호출되지 않음)
			if (player.IsMoving && player.CurrentEdge != null)
			{
				return LookFromEdge(player);
			}

			return LookFromLocation(player);
		}

		/// <summary>
		/// Location에서 Look
		/// </summary>
		private LookResult LookFromLocation(Unit player)
		{
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			var describeSystem = _hub.GetSystem("describeSystem") as DescribeSystem;
			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;
			var terrain = worldSystem.GetTerrain();
			var gameTime = worldSystem.GetTime();

			// 1. 현재 위치 정보
			var location = terrain.GetLocation(player.CurrentLocation);
			var region = location != null ? terrain.GetRegion(location.RegionId) : null;

			// 챕터 전환 중 데이터가 없으면 빈 결과 반환
			if (location == null || region == null)
			{
				return new LookResult
				{
					Location = new LocationInfo
					{
						RegionName = "",
						LocationName = "로딩 중...",
						AppearanceText = "",
						LocationRef = player.CurrentLocation
					},
					UnitIds = new List<int>(),
					Routes = new List<RouteInfo>()
				};
			}

			var locationInfo = new LocationInfo
			{
				RegionName = region.Name ?? "",
				LocationName = describeSystem.GetLocationNameWithOwner(location) ?? "",
				AppearanceText = describeSystem.GetLocationDescribeText(location, gameTime, region) ?? "",
				LocationRef = player.CurrentLocation
			};

			// 2. 같은 위치에 있는 유닛들 (플레이어 제외)
			var unitIds = new List<int>();
			if (unitSystem != null)
			{
				foreach (var u in unitSystem.Units.Values)
				{
					if (u.Id == PlayerId) continue;

					// 같은 위치에 있는 유닛 (이동 중이 아닌)
					if (u.CurrentLocation == player.CurrentLocation && u.CurrentEdge == null)
					{
						unitIds.Add(u.Id);
					}
				}
			}

			// 3. 이동 가능한 경로들 (조건 필터링 적용)
			var routes = BuildRoutes(player, terrain, region, location, itemSystem, inventorySystem);

			return new LookResult
			{
				Location = locationInfo,
				UnitIds = unitIds,
				Routes = routes
			};
		}

		/// <summary>
		/// Edge에서 Look (이동 중)
		/// </summary>
		private LookResult LookFromEdge(Unit player)
		{
			var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			var terrain = worldSystem.GetTerrain();

			// Edge 정보
			var fromLocation = terrain.GetLocation(player.CurrentEdge!.From);
			var toLocation = terrain.GetLocation(player.CurrentEdge!.To);

			var locationInfo = new LocationInfo
			{
				RegionName = "",  // Edge에서는 Region 정보 생략
				LocationName = $"{fromLocation.Name} → {toLocation.Name}",
				AppearanceText = "이동 중입니다.",
				LocationRef = player.CurrentLocation
			};

			// 같은 Edge에 있는 유닛들
			var unitIds = new List<int>();
			if (unitSystem != null)
			{
				foreach (var u in unitSystem.Units.Values)
				{
					if (u.Id == PlayerId) continue;

					if (u.CurrentEdge != null)
					{
						// 같은 Edge = From-To 쌍이 같거나 반대
						bool sameEdge = (u.CurrentEdge.From == player.CurrentEdge!.From &&
										u.CurrentEdge.To == player.CurrentEdge!.To) ||
									   (u.CurrentEdge.From == player.CurrentEdge!.To &&
										u.CurrentEdge.To == player.CurrentEdge!.From);
						if (sameEdge)
						{
							unitIds.Add(u.Id);
						}
					}
				}
			}

			return new LookResult
			{
				Location = locationInfo,
				UnitIds = unitIds,
				Routes = new List<RouteInfo>()  // Edge에서는 경로 없음
			};
		}

		/// <summary>
		/// 경로 정보 생성 (조건 필터링 적용)
		/// </summary>
		private List<RouteInfo> BuildRoutes(Unit player, Terrain? terrain, Region? region, Location? location, ItemSystem? itemSystem, InventorySystem? inventorySystem)
		{
			var routes = new List<RouteInfo>();
			if (region == null || location == null || terrain == null) return routes;

			// InventorySystem에서 인벤토리 데이터 가져오기
			var inventory = inventorySystem.GetUnitInventory(player.Id);
			var equippedItems = inventorySystem.GetUnitEquippedItems(player.Id);
			var actualProps = player.GetActualProps(itemSystem, inventory, equippedItems);

			// Region 내부 Edge
			var edges = region.GetEdges(location);
			foreach (var edge in edges)
			{
				// Edge.IsBlocked 체크 - 완전 차단된 경로는 제외
				if (edge.IsBlocked) continue;

				var conditions = edge.GetConditions(location);
				bool canPass = true;
				string? blockedReason = null;

				foreach (var (propName, requiredValue) in conditions)
				{
					if (actualProps.GetProp(propName) < requiredValue)
					{
						canPass = false;
						blockedReason = $"{propName}이(가) 필요합니다";
						break;
					}
				}

				var neighbor = edge.GetOtherLocation(location);
				routes.Add(new RouteInfo
				{
					LocationName = neighbor.Name,
					RegionName = region.Name,
					Destination = new LocationRef(neighbor.RegionId, neighbor.LocalId),
					TravelTime = edge.GetTravelTime(location),
					IsRegionEdge = false,
					IsBlocked = !canPass,
					BlockedReason = blockedReason
				});
			}

			// Region 간 Edge (RegionEdge)
			foreach (var regionEdge in terrain.GetRegionEdgesFrom(player.CurrentLocation))
			{
				if (regionEdge.IsBlocked) continue;

				var conditions = regionEdge.GetConditions(player.CurrentLocation);
				bool canPass = true;
				string? blockedReason = null;

				foreach (var (propName, requiredValue) in conditions)
				{
					if (actualProps.GetProp(propName) < requiredValue)
					{
						canPass = false;
						blockedReason = $"{propName}이(가) 필요합니다";
						break;
					}
				}

				var destination = regionEdge.GetOtherLocation(player.CurrentLocation);
				var destLocation = terrain.GetLocation(destination);
				var destRegion = terrain.GetRegion(destination.RegionId);

				routes.Add(new RouteInfo
				{
					LocationName = destLocation.Name ?? "",
					RegionName = destRegion.Name ?? "",
					Destination = destination,
					TravelTime = regionEdge.GetTravelTime(player.CurrentLocation),
					IsRegionEdge = true,
					IsBlocked = !canPass,
					BlockedReason = blockedReason
				});
			}

			return routes;
		}

		#endregion

		#region 저장/로드

		/// <summary>
		/// JSON 파일에서 플레이어 데이터 로드
		/// </summary>
		public PlayerSystem UpdateFromFile(string filePath)
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
		/// JSON 문자열에서 플레이어 데이터 로드
		/// </summary>
		public void UpdateFromJson(string json)
		{
			var options = new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true,
				WriteIndented = true
			};

			var data = JsonSerializer.Deserialize<PlayerJsonData>(json, options);
			if (data == null)
				throw new InvalidOperationException("Failed to parse Player JSON data");

			PlayerId = data.PlayerId;
		}

		/// <summary>
		/// 현재 플레이어 데이터를 JSON 파일로 저장
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
		/// 현재 플레이어 데이터를 JSON 문자열로 변환
		/// </summary>
		public string ToJson()
		{
			var data = new PlayerJsonData
			{
				PlayerId = PlayerId
			};

			var options = new JsonSerializerOptions
			{
				PropertyNameCaseInsensitive = true,
				WriteIndented = true
			};

			return JsonSerializer.Serialize(data, options);
		}

		#endregion
	}
}
