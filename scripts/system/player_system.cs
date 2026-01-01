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
	/// - 자정 제한 자동 적용, 남은 시간은 다음 Step에서 계속
	///
	/// 시간 처리 흐름:
	/// 1. PlayerSystem이 NextStepDuration 설정 (다음 Step에서 사용될 값)
	/// 2. 다음 Step에서 MovementSystem이 해당 시간만큼 진행
	/// 3. PlayerSystem이 실제 소비된 시간을 _remainingDuration에서 차감
	/// </summary>
	public class PlayerSystem : ECS.System
	{
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

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			var planningSystem = _hub.FindSystem("planningSystem") as PlanningSystem;
			var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;

			if (planningSystem == null || worldSystem == null)
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
				planningSystem.SetNextStepDuration(0);
				_lastSetDuration = 0;
				return;
			}

			// 3. 다음 Step에서 진행할 시간 설정
			planningSystem.SetNextStepDuration(_remainingDuration);

			// 실제 적용될 시간 (자정 제한 적용됨) - 다음 Step에서 차감
			_lastSetDuration = planningSystem.NextStepDuration;

#if DEBUG_LOG
			GD.Print($"[PlayerSystem] 다음 Step 예약: {_lastSetDuration}분");
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

			// 2. 같은 위치에 있는 캐릭터들 (플레이어 제외)
			var characterIds = new List<int>();
			if (characterSystem != null)
			{
				foreach (var c in characterSystem.Characters.Values)
				{
					if (c.Id == PlayerId) continue;

					// 같은 위치에 있는 캐릭터 (이동 중이 아닌)
					if (c.CurrentLocation == player.CurrentLocation && c.CurrentEdge == null)
					{
						characterIds.Add(c.Id);
					}
				}
			}

			// 3. 이동 가능한 경로들 (조건 필터링 적용)
			var routes = BuildRoutes(player, terrain, region, location, itemSystem);

			return new LookResult
			{
				Location = locationInfo,
				CharacterIds = characterIds,
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
