#define DEBUG_LOG

using Godot;
using Morld;
using System;
using System.Collections.Generic;

namespace SE
{
	/// <summary>
	/// Edge 위에서의 충돌 감지 시스템
	/// 같은 Edge에서 반대 방향 또는 같은 방향으로 이동하는 유닛 간 충돌 감지
	/// </summary>
	public class EdgeCollisionDetector
	{
		/// <summary>
		/// Edge를 고유하게 식별하는 키 (양방향 동일)
		/// </summary>
		public readonly struct EdgeKey : IEquatable<EdgeKey>
		{
			public readonly LocationRef A;
			public readonly LocationRef B;

			public EdgeKey(LocationRef from, LocationRef to)
			{
				// 정규화: 항상 작은 것이 A (양방향 동일 키 생성)
				// RegionId 먼저 비교, 같으면 LocalId 비교
				if (from.RegionId < to.RegionId ||
					(from.RegionId == to.RegionId && from.LocalId <= to.LocalId))
				{
					A = from;
					B = to;
				}
				else
				{
					A = to;
					B = from;
				}
			}

			public bool Equals(EdgeKey other) =>
				A.Equals(other.A) && B.Equals(other.B);

			public override bool Equals(object? obj) =>
				obj is EdgeKey other && Equals(other);

			public override int GetHashCode() =>
				HashCode.Combine(A, B);

			public override string ToString() =>
				$"Edge({A} <-> {B})";
		}

		/// <summary>
		/// Edge 위 유닛 정보
		/// </summary>
		public struct EdgeTraveler
		{
			/// <summary>유닛 ID</summary>
			public int UnitId;
			/// <summary>출발지 (이동 방향: From → To)</summary>
			public LocationRef From;
			/// <summary>도착지</summary>
			public LocationRef To;
			/// <summary>현재 위치 (0.0 = From, 1.0 = To)</summary>
			public float Position;
			/// <summary>분당 정규화 속도 (0.0~1.0 범위 내 이동량/분)</summary>
			public float Velocity;
			/// <summary>남은 시간 (분)</summary>
			public int RemainingTime;
		}

		/// <summary>
		/// 충돌 결과
		/// </summary>
		public struct CollisionResult
		{
			/// <summary>유닛 A ID</summary>
			public int UnitA;
			/// <summary>유닛 B ID</summary>
			public int UnitB;
			/// <summary>충돌 타입</summary>
			public CollisionType Type;
			/// <summary>충돌까지 남은 시간 (분)</summary>
			public int TimeToCollision;
			/// <summary>충돌 위치 (0.0 = EdgeKey.A, 1.0 = EdgeKey.B)</summary>
			public float CollisionPosition;
			/// <summary>Edge 정규화 키</summary>
			public EdgeKey Edge;
		}

		/// <summary>
		/// 충돌 타입
		/// </summary>
		public enum CollisionType
		{
			/// <summary>반대 방향에서 만남</summary>
			Encounter,
			/// <summary>같은 방향에서 추월</summary>
			Overtake
		}

		// Edge별 유닛 인덱스
		private readonly Dictionary<EdgeKey, List<EdgeTraveler>> _edgeIndex = new();

		/// <summary>
		/// 인덱스 초기화
		/// </summary>
		public void Clear()
		{
			_edgeIndex.Clear();
		}

		/// <summary>
		/// 이동 중인 유닛 추가 (Pi-World: CurrentMovement 기반)
		/// Note: Pi-World에서는 Edge가 아닌 Location 내 이동이므로
		/// 이 시스템은 추후 LocationCollisionDetector로 재구현 필요
		/// </summary>
		public void AddTraveler(Unit unit)
		{
			// Pi-World: CurrentMovement 사용
			if (unit.CurrentMovement == null) return;

			var movement = unit.CurrentMovement;

			// Pi-World에서는 같은 Location 내에서 이동하므로
			// Edge 충돌 감지 개념이 맞지 않음 - 임시로 비활성화
			// TODO: LocationCollisionDetector로 재구현
			return;
		}

		/// <summary>
		/// 현재 인덱스된 모든 Edge에서 충돌 예측
		/// </summary>
		/// <param name="maxDuration">최대 예측 시간 (분)</param>
		/// <returns>예측된 충돌 목록</returns>
		public List<CollisionResult> PredictCollisions(int maxDuration)
		{
			var results = new List<CollisionResult>();

			foreach (var (edgeKey, travelers) in _edgeIndex)
			{
				if (travelers.Count < 2) continue;

				// 같은 Edge의 모든 유닛 쌍 비교
				for (int i = 0; i < travelers.Count; i++)
				{
					for (int j = i + 1; j < travelers.Count; j++)
					{
						var collision = CheckCollision(travelers[i], travelers[j], edgeKey, maxDuration);
						if (collision.HasValue)
						{
							results.Add(collision.Value);
						}
					}
				}
			}

			return results;
		}

		/// <summary>
		/// 두 유닛 간 충돌 체크
		/// </summary>
		private CollisionResult? CheckCollision(EdgeTraveler a, EdgeTraveler b, EdgeKey edgeKey, int maxDuration)
		{
			// 같은 방향인지 확인 (From이 같으면 같은 방향)
			bool sameDirection = a.From.Equals(b.From);

			if (sameDirection)
			{
				return CheckOvertake(a, b, edgeKey, maxDuration);
			}
			else
			{
				return CheckEncounter(a, b, edgeKey, maxDuration);
			}
		}

		/// <summary>
		/// 반대 방향 충돌 체크 (Encounter)
		///
		/// A: position_a → 1.0 방향 (From → To)
		/// B: position_b → 0.0 방향 (To → From, 실제 위치 = 1 - position_b)
		/// </summary>
		private CollisionResult? CheckEncounter(EdgeTraveler a, EdgeTraveler b, EdgeKey edgeKey, int maxDuration)
		{
			// 위치를 EdgeKey 기준으로 정규화
			// EdgeKey.A가 더 작은 LocationRef이므로
			// a.From == EdgeKey.A이면 a의 position은 그대로
			// a.From == EdgeKey.B이면 a의 position은 1 - position
			float posA = NormalizePosition(a, edgeKey);
			float posB = NormalizePosition(b, edgeKey);

			// 속도도 방향 반영
			float velA = NormalizeVelocity(a, edgeKey);
			float velB = NormalizeVelocity(b, edgeKey);

			// 상대 속도 (서로 접근하면 양수)
			float relativeVelocity = velA - velB;  // A가 오른쪽으로, B가 왼쪽으로 이동

			// A가 B 왼쪽에 있고 서로 접근 중
			float distance = posB - posA;

			if (relativeVelocity > 0.0001f && distance > 0.0001f)
			{
				float timeToCollision = distance / relativeVelocity;
				int timeMinutes = (int)Math.Floor(timeToCollision);

				if (timeMinutes >= 0 && timeMinutes < maxDuration)
				{
					float collisionPos = posA + velA * timeToCollision;

#if DEBUG_LOG
					GD.Print($"[EdgeCollisionDetector] Encounter: Unit {a.UnitId} vs {b.UnitId} at pos={collisionPos:F2}, time={timeMinutes}min");
#endif

					return new CollisionResult
					{
						UnitA = a.UnitId,
						UnitB = b.UnitId,
						Type = CollisionType.Encounter,
						TimeToCollision = timeMinutes,
						CollisionPosition = collisionPos,
						Edge = edgeKey
					};
				}
			}

			return null;
		}

		/// <summary>
		/// 같은 방향 추월 체크 (Overtake)
		///
		/// 빠른 유닛이 느린 유닛을 따라잡는 경우
		/// </summary>
		private CollisionResult? CheckOvertake(EdgeTraveler a, EdgeTraveler b, EdgeKey edgeKey, int maxDuration)
		{
			// 위치와 속도를 EdgeKey 기준으로 정규화
			float posA = NormalizePosition(a, edgeKey);
			float posB = NormalizePosition(b, edgeKey);
			float velA = NormalizeVelocity(a, edgeKey);
			float velB = NormalizeVelocity(b, edgeKey);

			// 상대 속도 (A가 더 빠르면 양수)
			float relativeVelocity = velA - velB;

			// 거리 (A가 뒤에 있으면 양수)
			float distance = posB - posA;

			// A가 B 뒤에 있고 더 빠른 경우
			if (relativeVelocity > 0.0001f && distance > 0.0001f)
			{
				float timeToCollision = distance / relativeVelocity;
				int timeMinutes = (int)Math.Floor(timeToCollision);

				if (timeMinutes >= 0 && timeMinutes < maxDuration)
				{
					float collisionPos = posA + velA * timeToCollision;

#if DEBUG_LOG
					GD.Print($"[EdgeCollisionDetector] Overtake: Unit {a.UnitId} catches {b.UnitId} at pos={collisionPos:F2}, time={timeMinutes}min");
#endif

					return new CollisionResult
					{
						UnitA = a.UnitId,  // 추월하는 유닛
						UnitB = b.UnitId,  // 추월당하는 유닛
						Type = CollisionType.Overtake,
						TimeToCollision = timeMinutes,
						CollisionPosition = collisionPos,
						Edge = edgeKey
					};
				}
			}

			// B가 A 뒤에 있고 더 빠른 경우 (역방향 체크)
			relativeVelocity = velB - velA;
			distance = posA - posB;

			if (relativeVelocity > 0.0001f && distance > 0.0001f)
			{
				float timeToCollision = distance / relativeVelocity;
				int timeMinutes = (int)Math.Floor(timeToCollision);

				if (timeMinutes >= 0 && timeMinutes < maxDuration)
				{
					float collisionPos = posB + velB * timeToCollision;

#if DEBUG_LOG
					GD.Print($"[EdgeCollisionDetector] Overtake: Unit {b.UnitId} catches {a.UnitId} at pos={collisionPos:F2}, time={timeMinutes}min");
#endif

					return new CollisionResult
					{
						UnitA = b.UnitId,  // 추월하는 유닛
						UnitB = a.UnitId,  // 추월당하는 유닛
						Type = CollisionType.Overtake,
						TimeToCollision = timeMinutes,
						CollisionPosition = collisionPos,
						Edge = edgeKey
					};
				}
			}

			return null;
		}

		/// <summary>
		/// 위치를 EdgeKey 기준으로 정규화
		/// EdgeKey.A에서 출발하면 그대로, EdgeKey.B에서 출발하면 1 - position
		/// </summary>
		private float NormalizePosition(EdgeTraveler traveler, EdgeKey edgeKey)
		{
			if (traveler.From.Equals(edgeKey.A))
			{
				// A → B 방향: position 그대로
				return traveler.Position;
			}
			else
			{
				// B → A 방향: 1 - position
				return 1.0f - traveler.Position;
			}
		}

		/// <summary>
		/// 속도를 EdgeKey 기준으로 정규화
		/// EdgeKey.A에서 출발하면 양수 (오른쪽 이동), EdgeKey.B에서 출발하면 음수 (왼쪽 이동)
		/// </summary>
		private float NormalizeVelocity(EdgeTraveler traveler, EdgeKey edgeKey)
		{
			if (traveler.From.Equals(edgeKey.A))
			{
				// A → B 방향: 양수
				return traveler.Velocity;
			}
			else
			{
				// B → A 방향: 음수
				return -traveler.Velocity;
			}
		}
	}
}
