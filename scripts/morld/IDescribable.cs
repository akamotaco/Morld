namespace Morld;

using System.Collections.Generic;

/// <summary>
/// 외관 묘사 가능한 객체를 위한 인터페이스
/// </summary>
public interface IDescribable
{
	Dictionary<string, string> Appearance { get; set; }
}
