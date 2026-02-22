namespace Morld;

/// <summary>
/// Unit 타입 (캐릭터, 오브젝트, 생물)
/// </summary>
public enum UnitType
{
	/// <summary>
	/// 캐릭터 (이동/스케줄/이벤트 가능, 인간급 AI)
	/// </summary>
	Character,

	/// <summary>
	/// 오브젝트 (이동/스케줄 없음)
	/// </summary>
	Object,

	/// <summary>
	/// 생물 (이동/스케줄/이벤트 가능, 단순화된 AI)
	/// </summary>
	Creature
}
