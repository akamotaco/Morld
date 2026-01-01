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
		/// 플레이어 캐릭터 ID
		/// </summary>
		public int PlayerId { get; set; } = 0;

		public PlayerSystem()
		{
		}

		/// <summary>
		/// 플레이어 캐릭터 접근 헬퍼
		/// </summary>
		public Character? GetPlayerCharacter()
		{
			var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
			return characterSystem?.GetCharacter(PlayerId);
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
		/// 이동 실행 (스케줄 스택에 이동 레이어 push)
		/// </summary>
		private void ExecuteMove(LocationRef destination)
		{
			var player = GetPlayerCharacter();
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;

			if (player == null || worldSystem == null)
				return;

			var terrain = worldSystem.GetTerrain();

			// 이미 목적지에 있으면 무시
			if (player.CurrentLocation == destination)
				return;

			// 경로 탐색 (총 이동 시간 계산용)
			var pathResult = terrain.FindPath(player.CurrentLocation, destination, player, itemSystem);

			if (!pathResult.Found || pathResult.Path.Count < 2)
			{
#if DEBUG_LOG
				GD.Print($"[PlayerSystem] 경로를 찾을 수 없음: {player.CurrentLocation} → {destination}");
#endif
				return;
			}

			// 총 이동 시간 계산
			var totalTime = CalculateTotalTravelTime(pathResult, terrain);

			// 이동 스케줄 push
			player.PushSchedule(new ScheduleLayer
			{
				Name = "이동",
				Schedule = null,
				EndConditionType = "이동",
				EndConditionParam = $"{destination.RegionId}:{destination.LocalId}"
			});

			// 시간 진행 요청
			var destLocation = terrain.GetLocation(destination);
			RequestTimeAdvance(totalTime, $"{destLocation?.Name ?? destination.ToString()}(으)로 이동");

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
				var edge = region?.GetEdgeBetween(from.LocalId, to.LocalId);

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

		#region 아이템 조작 (시간 소모 없음)

		/// <summary>
		/// 바닥에서 아이템 줍기
		/// </summary>
		public bool PickupItem(int itemId, int count = 1)
		{
			var player = GetPlayerCharacter();
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;

			if (player == null || worldSystem == null)
				return false;

			var terrain = worldSystem.GetTerrain();
			var location = terrain.GetLocation(player.CurrentLocation);

			if (location == null)
				return false;

			// 바닥에 아이템이 있는지 확인
			if (!location.Inventory.TryGetValue(itemId, out int available) || available < count)
				return false;

			// 바닥에서 제거
			location.Inventory[itemId] -= count;
			if (location.Inventory[itemId] <= 0)
				location.Inventory.Remove(itemId);

			// 플레이어 인벤토리에 추가
			if (!player.Inventory.ContainsKey(itemId))
				player.Inventory[itemId] = 0;
			player.Inventory[itemId] += count;

#if DEBUG_LOG
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
			var itemName = itemSystem?.GetItem(itemId)?.Name ?? $"아이템{itemId}";
			GD.Print($"[PlayerSystem] 아이템 줍기: {itemName} x{count}");
#endif

			return true;
		}

		/// <summary>
		/// 아이템 바닥에 놓기
		/// </summary>
		public bool DropItem(int itemId, int count = 1)
		{
			var player = GetPlayerCharacter();
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;

			if (player == null || worldSystem == null)
				return false;

			// 플레이어가 아이템을 가지고 있는지 확인
			if (!player.Inventory.TryGetValue(itemId, out int available) || available < count)
				return false;

			var terrain = worldSystem.GetTerrain();
			var location = terrain.GetLocation(player.CurrentLocation);

			if (location == null)
				return false;

			// 플레이어 인벤토리에서 제거
			player.Inventory[itemId] -= count;
			if (player.Inventory[itemId] <= 0)
				player.Inventory.Remove(itemId);

			// 바닥에 추가
			if (!location.Inventory.ContainsKey(itemId))
				location.Inventory[itemId] = 0;
			location.Inventory[itemId] += count;

#if DEBUG_LOG
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
			var itemName = itemSystem?.GetItem(itemId)?.Name ?? $"아이템{itemId}";
			GD.Print($"[PlayerSystem] 아이템 놓기: {itemName} x{count}");
#endif

			return true;
		}

		/// <summary>
		/// 오브젝트에서 아이템 가져오기
		/// </summary>
		public bool TakeFromObject(int objectId, int itemId, int count = 1)
		{
			var player = GetPlayerCharacter();
			var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;

			if (player == null || characterSystem == null)
				return false;

			var obj = characterSystem.GetCharacter(objectId);
			if (obj == null || !obj.IsObject)
				return false;

			// 오브젝트가 같은 위치에 있는지 확인
			if (obj.CurrentLocation != player.CurrentLocation)
				return false;

			// 오브젝트에 아이템이 있는지 확인
			if (!obj.Inventory.TryGetValue(itemId, out int available) || available < count)
				return false;

			// 오브젝트에서 제거
			obj.Inventory[itemId] -= count;
			if (obj.Inventory[itemId] <= 0)
				obj.Inventory.Remove(itemId);

			// 플레이어에게 추가
			if (!player.Inventory.ContainsKey(itemId))
				player.Inventory[itemId] = 0;
			player.Inventory[itemId] += count;

#if DEBUG_LOG
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
			var itemName = itemSystem?.GetItem(itemId)?.Name ?? $"아이템{itemId}";
			GD.Print($"[PlayerSystem] {obj.Name}에서 가져오기: {itemName} x{count}");
#endif

			return true;
		}

		/// <summary>
		/// 오브젝트에 아이템 넣기
		/// </summary>
		public bool PutToObject(int objectId, int itemId, int count = 1)
		{
			var player = GetPlayerCharacter();
			var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;

			if (player == null || characterSystem == null)
				return false;

			var obj = characterSystem.GetCharacter(objectId);
			if (obj == null || !obj.IsObject)
				return false;

			// 오브젝트가 같은 위치에 있는지 확인
			if (obj.CurrentLocation != player.CurrentLocation)
				return false;

			// 플레이어가 아이템을 가지고 있는지 확인
			if (!player.Inventory.TryGetValue(itemId, out int available) || available < count)
				return false;

			// 플레이어에서 제거
			player.Inventory[itemId] -= count;
			if (player.Inventory[itemId] <= 0)
				player.Inventory.Remove(itemId);

			// 오브젝트에 추가
			if (!obj.Inventory.ContainsKey(itemId))
				obj.Inventory[itemId] = 0;
			obj.Inventory[itemId] += count;

#if DEBUG_LOG
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
			var itemName = itemSystem?.GetItem(itemId)?.Name ?? $"아이템{itemId}";
			GD.Print($"[PlayerSystem] {obj.Name}에 넣기: {itemName} x{count}");
#endif

			return true;
		}

		/// <summary>
		/// 오브젝트 살펴보기
		/// </summary>
		public ObjectLookResult? LookObject(int objectId)
		{
			var player = GetPlayerCharacter();
			var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;

			if (player == null || characterSystem == null)
				return null;

			var obj = characterSystem.GetCharacter(objectId);
			if (obj == null || !obj.IsObject)
				return null;

			// 오브젝트가 같은 위치에 있는지 확인
			if (obj.CurrentLocation != player.CurrentLocation)
				return null;

			return new ObjectLookResult
			{
				ObjectId = obj.Id,
				Name = obj.Name,
				Inventory = new Dictionary<int, int>(obj.Inventory)
			};
		}

		#endregion

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;

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

			// 2. 대기 중인 시간이 없으면 시간 정지
			if (_remainingDuration <= 0)
			{
				NextStepDuration = 0;
				_lastSetDuration = 0;
				return;
			}

			// 3. 자정까지 남은 시간 계산 (1440분 = 24시간)
			var minutesToMidnight = 1440 - time.MinuteOfDay;
			if (minutesToMidnight <= 0) minutesToMidnight = 1440;

			// 4. 다음 Step에서 진행할 시간 설정 (자정 제한)
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
			var player = GetPlayerCharacter();
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
		private LookResult LookFromLocation(Character player)
		{
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;
			var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
			var describeSystem = _hub.FindSystem("describeSystem") as DescribeSystem;
			var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
			var terrain = worldSystem?.GetTerrain();
			var gameTime = worldSystem?.GetTime();

			// 1. 현재 위치 정보
			var location = terrain?.GetLocation(player.CurrentLocation);
			var region = location != null ? terrain?.GetRegion(location.RegionId) : null;

			var locationInfo = new LocationInfo
			{
				RegionName = region?.Name ?? "",
				LocationName = location?.Name ?? "",
				DescriptionText = describeSystem?.GetLocationDescription(location, gameTime) ?? "",
				LocationRef = player.CurrentLocation
			};

			// 2. 같은 위치에 있는 캐릭터/오브젝트 (플레이어 제외)
			var characterIds = new List<int>();
			var objectIds = new List<int>();
			if (characterSystem != null)
			{
				foreach (var c in characterSystem.Characters.Values)
				{
					if (c.Id == PlayerId) continue;

					// 같은 위치에 있는 캐릭터/오브젝트 (이동 중이 아닌)
					if (c.CurrentLocation == player.CurrentLocation && c.CurrentEdge == null)
					{
						if (c.IsObject)
							objectIds.Add(c.Id);
						else
							characterIds.Add(c.Id);
					}
				}
			}

			// 3. 바닥에 떨어진 아이템
			var groundItems = new Dictionary<int, int>();
			if (location != null && location.Inventory.Count > 0)
			{
				foreach (var (itemId, count) in location.Inventory)
				{
					groundItems[itemId] = count;
				}
			}

			// 4. 이동 가능한 경로들 (조건 필터링 적용)
			var routes = BuildRoutes(player, terrain, region, location, itemSystem);

			return new LookResult
			{
				Location = locationInfo,
				CharacterIds = characterIds,
				ObjectIds = objectIds,
				GroundItems = groundItems,
				Routes = routes
			};
		}

		/// <summary>
		/// Edge에서 Look (이동 중)
		/// </summary>
		private LookResult LookFromEdge(Character player)
		{
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;
			var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
			var terrain = worldSystem?.GetTerrain();

			// Edge 정보
			var fromLocation = terrain?.GetLocation(player.CurrentEdge!.From);
			var toLocation = terrain?.GetLocation(player.CurrentEdge!.To);

			var locationInfo = new LocationInfo
			{
				RegionName = "",  // Edge에서는 Region 정보 생략
				LocationName = $"{fromLocation?.Name} → {toLocation?.Name}",
				DescriptionText = "이동 중입니다.",
				LocationRef = player.CurrentLocation
			};

			// 같은 Edge에 있는 캐릭터들
			var characterIds = new List<int>();
			if (characterSystem != null)
			{
				foreach (var c in characterSystem.Characters.Values)
				{
					if (c.Id == PlayerId) continue;

					if (c.CurrentEdge != null)
					{
						// 같은 Edge = From-To 쌍이 같거나 반대
						bool sameEdge = (c.CurrentEdge.From == player.CurrentEdge!.From &&
										c.CurrentEdge.To == player.CurrentEdge!.To) ||
									   (c.CurrentEdge.From == player.CurrentEdge!.To &&
										c.CurrentEdge.To == player.CurrentEdge!.From);
						if (sameEdge)
						{
							characterIds.Add(c.Id);
						}
					}
				}
			}

			return new LookResult
			{
				Location = locationInfo,
				CharacterIds = characterIds,
				Routes = new List<RouteInfo>()  // Edge에서는 경로 없음
			};
		}

		/// <summary>
		/// 경로 정보 생성 (조건 필터링 적용)
		/// </summary>
		private List<RouteInfo> BuildRoutes(Character player, Terrain? terrain, Region? region, Location? location, ItemSystem? itemSystem)
		{
			var routes = new List<RouteInfo>();
			if (region == null || location == null || terrain == null) return routes;

			var actualTags = player.GetActualTags(itemSystem);

			// Region 내부 Edge
			var edges = region.GetEdges(location);
			foreach (var edge in edges)
			{
				// Edge.IsBlocked 체크 - 완전 차단된 경로는 제외
				if (edge.IsBlocked) continue;

				var conditions = edge.GetConditions(location);
				bool canPass = true;
				string? blockedReason = null;

				foreach (var (tag, requiredValue) in conditions)
				{
					if (actualTags.GetTagValue(tag) < requiredValue)
					{
						canPass = false;
						blockedReason = $"{tag}이(가) 필요합니다";
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

				foreach (var (tag, requiredValue) in conditions)
				{
					if (actualTags.GetTagValue(tag) < requiredValue)
					{
						canPass = false;
						blockedReason = $"{tag}이(가) 필요합니다";
						break;
					}
				}

				var destination = regionEdge.GetOtherLocation(player.CurrentLocation);
				var destLocation = terrain.GetLocation(destination);
				var destRegion = terrain.GetRegion(destination.RegionId);

				routes.Add(new RouteInfo
				{
					LocationName = destLocation?.Name ?? "",
					RegionName = destRegion?.Name ?? "",
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
			using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Read);
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

			using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Write);
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
