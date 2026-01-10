using System;

namespace Morld
{
	/// <summary>
	/// 싱글톤 ID 생성기
	/// 모든 엔티티(Unit, Item, Location 등)에 대해 단일 시퀀스로 고유 ID 생성
	/// Overflow 시 빈 ID를 찾아 할당
	/// </summary>
	public static class IdGenerator
	{
		private static int _nextId = 1;
		private static bool _overflow = false;
		private const int MaxId = int.MaxValue - 1;

		// 시스템 참조 (overflow 시 ID 사용 여부 확인용)
		private static SE.UnitSystem _unitSystem;
		private static SE.ItemSystem _itemSystem;

		/// <summary>
		/// 시스템 참조 설정 (GameEngine에서 호출)
		/// </summary>
		public static void SetSystems(SE.UnitSystem unitSystem, SE.ItemSystem itemSystem)
		{
			_unitSystem = unitSystem;
			_itemSystem = itemSystem;
		}

		/// <summary>
		/// 다음 고유 ID 생성
		/// </summary>
		public static int NextId()
		{
			if (_overflow)
			{
				return FindAvailableId();
			}

			int id = _nextId++;

			// 최대치 도달 시 overflow 모드로 전환
			if (_nextId >= MaxId)
			{
				_overflow = true;
				_nextId = 1;
				Godot.GD.PrintErr("[IdGenerator] WARNING: ID overflow detected! Switching to search mode.");
			}

			return id;
		}

		/// <summary>
		/// 현재 다음 ID 값 조회 (생성하지 않음)
		/// </summary>
		public static int PeekNextId()
		{
			return _nextId;
		}

		/// <summary>
		/// Overflow 상태 확인
		/// </summary>
		public static bool IsOverflow()
		{
			return _overflow;
		}

		/// <summary>
		/// ID 카운터 리셋 (챕터 전환 시)
		/// </summary>
		public static void Reset(int startId = 1)
		{
			_nextId = startId;
			_overflow = false;
		}

		/// <summary>
		/// ID가 사용 중인지 확인
		/// </summary>
		private static bool IsIdInUse(int id)
		{
			if (_unitSystem != null && _unitSystem.Units.ContainsKey(id))
				return true;
			if (_itemSystem != null && _itemSystem.Items.ContainsKey(id))
				return true;
			return false;
		}

		/// <summary>
		/// 빈 ID 찾기 (overflow 모드)
		/// </summary>
		private static int FindAvailableId()
		{
			Godot.GD.Print("[IdGenerator] WARNING: Searching for available ID (overflow mode)");

			// 시스템 참조가 없으면 순차적으로 증가
			if (_unitSystem == null && _itemSystem == null)
			{
				Godot.GD.PrintErr("[IdGenerator] ERROR: No system references set! Using sequential ID.");
				return _nextId++;
			}

			// 1부터 MaxId까지 빈 ID 탐색
			int startSearch = _nextId;

			do
			{
				if (!IsIdInUse(_nextId))
				{
					int foundId = _nextId;
					_nextId++;
					if (_nextId >= MaxId) _nextId = 1;
					return foundId;
				}

				_nextId++;
				if (_nextId >= MaxId) _nextId = 1;

			} while (_nextId != startSearch);

			// 모든 ID가 사용 중
			Godot.GD.PrintErr("[IdGenerator] CRITICAL: No available ID found!");
			throw new InvalidOperationException("No available ID found - all IDs are in use");
		}
	}
}
