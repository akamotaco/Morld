namespace Morld;

using System.Collections.Generic;

/// <summary>
/// 장소 묘사 가능한 객체를 위한 인터페이스 (Region, Location)
/// </summary>
public interface IDescribable
{
	Dictionary<string, string> DescribeText { get; set; }
}
