using ECS;

namespace SE
{
	/// <summary>
	/// 게임 월드의 지형(Terrain)과 시간(GameTime) 데이터를 관리하는 시스템
	/// Data System: Proc() 없음, JSON Import/Export만 제공
	/// </summary>
	public class WorldSystem : ECS.System
	{
		/// <summary>
		/// graph terrain 데이터 저장하는 곳
		/// json 파일로 import/export 하는 기능을 제공하며, 다음의 것을 제공함
		/// [morld]
		/// - terrain
		/// - region (+ region edge)
		/// - location (+ edge)
		/// </summary>
		private Morld.Terrain _terrain;
		private Morld.GameTime _currentTime;

		/// <summary>
		/// 시간 정지 플래그
		/// True일 때: 시간 흐름 없음, NPC 이동 없음, 이벤트 없음
		/// 플레이어는 자유롭게 이동 가능 (시간 소모 없이)
		/// </summary>
		private bool _timeFrozen = false;

		public WorldSystem(string TerrainName)
		{
			_terrain = new Morld.Terrain(TerrainName);
			_currentTime = new Morld.GameTime();
		}

		public Morld.Terrain GetTerrain()
		{
			return this._terrain;
		}

		public Morld.GameTime GetTime()
		{
			return this._currentTime;
		}

		/// <summary>
		/// Terrain 초기화 (챕터 전환 시 사용)
		/// 모든 Region, Location, Edge 제거
		/// </summary>
		public void ClearTerrain()
		{
			_terrain = new Morld.Terrain(_terrain.Name);
			Godot.GD.Print("[WorldSystem] Terrain cleared.");
		}

		/// <summary>
		/// 시간 초기화
		/// </summary>
		public void ResetTime()
		{
			_currentTime = new Morld.GameTime();
		}

		/// <summary>
		/// 시간 정지 상태 설정
		/// </summary>
		/// <param name="frozen">True: 시간 정지, False: 정상 진행</param>
		public void SetTimeFrozen(bool frozen)
		{
			_timeFrozen = frozen;
			Godot.GD.Print($"[WorldSystem] Time frozen: {frozen}");
		}

		/// <summary>
		/// 시간 정지 상태 조회
		/// </summary>
		public bool IsTimeFrozen()
		{
			return _timeFrozen;
		}
	}
}
