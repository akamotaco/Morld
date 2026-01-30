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
		/// 다음 Step에서 진행할 시간 (밀리초)
		/// </summary>
		public int NextStepDuration { get; private set; } = 0;

		/// <summary>
		/// 아직 처리해야 할 남은 시간 (밀리초)
		/// </summary>
		private int _remainingDuration = 0;

		/// <summary>
		/// 이전 Step에서 설정한 시간 (이번 Step에서 실제 소비된 시간)
		/// </summary>
		private int _lastSetDuration = 0;

		/// <summary>
		/// 즉시 행동 대기 플래그 (Duration=0 Job 처리용)
		/// RequestTimeAdvance(0) 호출 시 설정, Step 처리 후 해제
		/// frozen 상태 또는 Gate 인접 이동 시 Duration=0이 발생
		/// </summary>
		private bool _hasInstantAction = false;

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
		public void AddExcessTime(int millis)
		{
			_remainingDuration += millis;
#if DEBUG_LOG
			int displayMin = millis / GameTime.MillisPerMinute;
			int totalMin = _remainingDuration / GameTime.MillisPerMinute;
			GD.Print($"[PlayerSystem] ExcessTime 추가: +{displayMin}분 (총 대기: {totalMin}분)");
#endif
		}

		/// <summary>
		/// 대기 중인 시간 모두 제거 (시간 정지 상태에서 즉시 이동 후 호출)
		/// </summary>
		public void ClearPendingTime()
		{
			_remainingDuration = 0;
			_hasInstantAction = false;
			NextStepDuration = 0;
			_lastSetDuration = 0;
#if DEBUG_LOG
			GD.Print("[PlayerSystem] 대기 시간 초기화 (시간 정지 모드)");
#endif
		}

		/// <summary>
		/// 플레이어 유닛 접근 헬퍼
		/// </summary>
		public Unit? FindPlayerUnit()
		{
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			return unitSystem.FindUnit(PlayerId);
		}

		/// <summary>
		/// 시간 진행 요청 (외부에서 호출)
		/// </summary>
		/// <param name="millis">진행할 시간 (밀리초)</param>
		/// <param name="actionName">액션 이름 (디버그용)</param>
		public void RequestTimeAdvance(int millis, string actionName = "")
		{
			_remainingDuration += millis;
			if (millis == 0) _hasInstantAction = true;
			_currentAction = actionName;

			// NextStepDuration 사전 설정:
			// PlayerSystem.Proc()은 JobBehaviorSystem 이후에 실행되므로,
			// 새 요청의 첫 Step에서 JobBehavior가 NextStepDuration=0을 읽어 스킵하는 문제를 방지.
			// 여기서 미리 설정하면 첫 Step부터 바로 이동 처리 가능.
			if (millis > 0 && NextStepDuration <= 0)
			{
				var worldSystem = _hub.GetSystem("worldSystem") as WorldSystem;
				var time = worldSystem?.GetTime();
				if (time != null)
				{
					var millisToMidnight = GameTime.MillisPerDay - time.MillisOfDay;
					if (millisToMidnight <= 0) millisToMidnight = GameTime.MillisPerDay;
					NextStepDuration = Math.Min(_remainingDuration, millisToMidnight);
					_lastSetDuration = NextStepDuration;
				}
			}

#if DEBUG_LOG
			int reqMin = millis / GameTime.MillisPerMinute;
			int totalMin = _remainingDuration / GameTime.MillisPerMinute;
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print($"[PlayerSystem] 시간 진행 요청!");
			GD.Print($"  액션: {actionName}");
			GD.Print($"  요청 시간: {reqMin}분 ({millis}ms)");
			GD.Print($"  총 대기 시간: {totalMin}분 ({_remainingDuration}ms)");
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
		}

		/// <summary>
		/// 현재 대기 중인 시간이 있는지
		/// </summary>
		public bool HasPendingTime => _remainingDuration > 0;

		/// <summary>
		/// Duration=0 즉시 행동이 대기 중인지
		/// (frozen 이동 또는 Gate 인접 이동 시 Step 트리거용)
		/// </summary>
		public bool HasPendingInstantAction => _hasInstantAction;

		/// <summary>
		/// 다음 Step 시간 조정 (EventPredictionSystem에서 호출)
		/// </summary>
		/// <param name="adjustedMillis">조정할 시간 (밀리초)</param>
		public void AdjustNextStepDuration(int adjustedMillis)
		{
			if (adjustedMillis <= 0 || adjustedMillis >= NextStepDuration)
				return;

#if DEBUG_LOG
			int fromMin = NextStepDuration / GameTime.MillisPerMinute;
			int toMin = adjustedMillis / GameTime.MillisPerMinute;
			GD.Print($"[PlayerSystem] NextStepDuration 조정: {fromMin}분 → {toMin}분 ({adjustedMillis}ms)");
#endif

			NextStepDuration = adjustedMillis;
			_lastSetDuration = adjustedMillis;
		}

		#region 플레이어 액션 요청

		/// <summary>
		/// 통합 명령 처리
		/// 포맷: "이동:regionId:localId" 또는 "휴식:millis"
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
						ExecuteMoveAndAdvanceTime(new LocationRef(regionId, localId));
					}
					break;
				case "휴식":
					if (parts.Length >= 2 && int.TryParse(parts[1], out int millis))
					{
						ExecuteIdle(millis);
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
		/// 플레이어 이동 스케줄링 및 시간 진행 요청
		/// - JobList에 이동 Job 삽입
		/// - RequestTimeAdvance 호출
		/// PlayerSystem 전용: 시간 제어 + Job 스케줄링 책임
		/// </summary>
		private void ExecuteMoveAndAdvanceTime(LocationRef destination)
		{
			var player = FindPlayerUnit();
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
			// frozen 상태: 시간 소모 0 (즉시 이동)
			// 일반 상태: Pi-World X 좌표 기반 거리 계산
			int totalTime = worldSystem.IsTimeFrozen()
				? 0
				: CalculatePathTravelTime2D(terrain, pathResult, player);

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
			int totalMin = totalTime / GameTime.MillisPerMinute;
			GD.Print($"[PlayerSystem] 이동 요청: {player.CurrentLocation} → {destination} ({totalMin}분, {totalTime}ms)");
#endif
		}

		/// <summary>
		/// 휴식 실행 (스택 변화 없이 시간만 진행)
		/// </summary>
		private void ExecuteIdle(int millis)
		{
			int displayMin = millis / GameTime.MillisPerMinute;
			// 시간 진행 요청 (스택 변화 없음)
			RequestTimeAdvance(millis, $"휴식 ({displayMin}분)");

#if DEBUG_LOG
			GD.Print($"[PlayerSystem] 휴식 요청: {displayMin}분 ({millis}ms)");
#endif
		}

		/// <summary>
		/// Pi-World 2D 경로 이동 시간 계산
		/// 각 Location 내 Gate까지 X 좌표 거리 기반 시간 합산
		/// </summary>
		/// <returns>총 이동 시간 (밀리초)</returns>
		private int CalculatePathTravelTime2D(Morld.Terrain terrain, Morld.PathResult pathResult, Unit player)
		{
			if (!pathResult.Found || pathResult.Path.Count < 2)
				return 0;

			var itemSystem = _hub.GetSystem("itemSystem") as ItemSystem;
			var inventorySystem = _hub.GetSystem("inventorySystem") as InventorySystem;
			var inventory = inventorySystem?.GetUnitInventory(player.Id);
			var equippedItems = inventorySystem?.GetUnitEquippedItems(player.Id);
			var actualProps = player.GetActualProps(itemSystem, inventory, equippedItems);

			int movementSpeedPercent = player.GetMovementSpeed(itemSystem, inventory, equippedItems);
			float speedModifier = movementSpeedPercent / 100f;

			int totalTimeMillis = 0;
			float currentX = player.PositionX;

			for (int i = 0; i < pathResult.Path.Count - 1; i++)
			{
				var fromLocRef = new LocationRef(pathResult.Path[i]);
				var toLocRef = new LocationRef(pathResult.Path[i + 1]);

				var location = terrain.GetLocation(fromLocRef);
				if (location == null) continue;

				// Gate 찾기
				var region = terrain.GetRegion(fromLocRef.RegionId);
				if (region == null) continue;

				var gates = region.GetGates(fromLocRef.LocalId);
				Morld.Gate? targetGate = null;

				foreach (var gate in gates)
				{
					if (gate.ConnectedLocation == toLocRef && gate.CanTraverseForward(actualProps))
					{
						targetGate = gate;
						break;
					}
				}

				if (targetGate == null)
				{
					totalTimeMillis += GameTime.MillisPerMinute;
					currentX = 0f;
					continue;
				}

				// Gate까지 이동 시간 + Gate 통과 시간 (밀리초)
				int segmentTimeMillis = location.CalculateTravelTime(currentX, targetGate.X, speedModifier);
				totalTimeMillis += segmentTimeMillis + targetGate.TravelTime;

				// Gate 통과 후 위치 업데이트
				currentX = targetGate.ArrivalX;
			}

			return totalTimeMillis;
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
				int consumedMin = _lastSetDuration / GameTime.MillisPerMinute;
				int remainMin = _remainingDuration / GameTime.MillisPerMinute;
				GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
				GD.Print($"[PlayerSystem] Step 완료");
				GD.Print($"  현재 시간: {time}");
				GD.Print($"  액션: {_currentAction}");
				GD.Print($"  소비된 시간: {consumedMin}분 ({_lastSetDuration}ms)");
				GD.Print($"  남은 시간: {remainMin}분 ({_remainingDuration}ms)");
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
				_hasInstantAction = false;
				NextStepDuration = 0;
				_lastSetDuration = 0;
				return;
			}

			// 4. 자정까지 남은 시간 계산 (밀리초)
			var millisToMidnight = GameTime.MillisPerDay - time.MillisOfDay;
			if (millisToMidnight <= 0) millisToMidnight = GameTime.MillisPerDay;

			// 5. 다음 Step에서 진행할 시간 설정 (자정 제한)
			NextStepDuration = Math.Min(_remainingDuration, millisToMidnight);
			_lastSetDuration = NextStepDuration;

#if DEBUG_LOG
			int nextMin = NextStepDuration / GameTime.MillisPerMinute;
			int remMin = _remainingDuration / GameTime.MillisPerMinute;
			GD.Print($"[PlayerSystem] 다음 Step 예약: {nextMin}분 ({NextStepDuration}ms) (남은시간: {remMin}분)");
#endif
		}

		#region Look 기능 (UnitSystem으로 위임)

		/// <summary>
		/// 현재 플레이어 위치의 정보 조회
		/// UnitSystem.LookFromUnit으로 위임
		/// </summary>
		public LookResult Look()
		{
			var player = FindPlayerUnit();
			if (player == null)
			{
				GD.Print("[PlayerSystem.Look] player is null");
				return new LookResult();
			}

			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;
			return unitSystem.LookFromUnit(player, PlayerId);
		}

		/// <summary>
		/// 유닛 살펴보기 (캐릭터/오브젝트 통합)
		/// UnitSystem.LookUnit으로 위임
		/// </summary>
		public UnitLookResult? LookUnit(int unitId)
		{
			var player = FindPlayerUnit();
			var unitSystem = _hub.GetSystem("unitSystem") as UnitSystem;

			if (player == null || unitSystem == null)
				return null;

			return unitSystem.LookUnit(unitId, player);
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
