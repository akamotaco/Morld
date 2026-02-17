namespace Morld;

using System;

/// <summary>
/// Prop (타입:이름 형식 또는 단순 이름)
/// - 복합: "타입:이름" (예: "생존:체력", "외모:흑발")
/// - 단순: "이름" (예: "성별", "근력") → Type=""
/// </summary>
public readonly struct Prop : IEquatable<Prop>
{
	/// <summary>
	/// 타입 (예: "스탯", "상태", "감정")
	/// </summary>
	public string Type { get; }

	/// <summary>
	/// 이름 (예: "힘", "피로", "기쁨")
	/// </summary>
	public string Name { get; }

	/// <summary>
	/// 전체 이름 (복합: "타입:이름", 단순: "이름")
	/// </summary>
	public string FullName => string.IsNullOrEmpty(Type) ? Name : $"{Type}:{Name}";

	/// <summary>
	/// 유효한 Prop인지 (이름이 있으면 유효, Type은 비어도 됨)
	/// </summary>
	public bool IsValid => !string.IsNullOrEmpty(Name);

	/// <summary>
	/// Prop 생성
	/// </summary>
	public Prop(string type, string name)
	{
		Type = type ?? string.Empty;
		Name = name ?? string.Empty;
	}

	/// <summary>
	/// 문자열에서 파싱: "타입:이름" → 복합 Prop, "이름" → 단순 Prop (Type="")
	/// </summary>
	public static Prop Parse(string fullName)
	{
		if (string.IsNullOrEmpty(fullName))
			return default;

		var colonIndex = fullName.IndexOf(':');
		if (colonIndex <= 0 || colonIndex >= fullName.Length - 1)
		{
			// 콜론 없음 또는 불완전 → 단순 Prop (Type="")
			var trimmed = fullName.Trim();
			if (string.IsNullOrEmpty(trimmed))
				return default;
			return new Prop(string.Empty, trimmed);
		}

		var type = fullName.Substring(0, colonIndex).Trim();
		var name = fullName.Substring(colonIndex + 1).Trim();

		if (string.IsNullOrEmpty(type) || string.IsNullOrEmpty(name))
			return default;

		return new Prop(type, name);
	}

	/// <summary>
	/// "타입:이름" 형식 문자열에서 파싱 시도
	/// </summary>
	public static bool TryParse(string fullName, out Prop prop)
	{
		prop = Parse(fullName);
		return prop.IsValid;
	}

	/// <summary>
	/// 유효성 검사 후 파싱 (실패 시 예외)
	/// </summary>
	public static Prop ParseOrThrow(string fullName)
	{
		var prop = Parse(fullName);
		if (!prop.IsValid)
			throw new ArgumentException($"Invalid prop format: '{fullName}'. Expected 'Type:Name' or 'Name' format.", nameof(fullName));
		return prop;
	}

	/// <summary>
	/// 단순 Prop인지 (Type이 비어있는지)
	/// </summary>
	public bool IsSimple => string.IsNullOrEmpty(Type);

	public override string ToString() => IsValid ? FullName : "(invalid)";

	public override int GetHashCode() => HashCode.Combine(Type, Name);

	public override bool Equals(object? obj) => obj is Prop other && Equals(other);

	public bool Equals(Prop other) =>
		string.Equals(Type, other.Type, StringComparison.Ordinal) &&
		string.Equals(Name, other.Name, StringComparison.Ordinal);

	public static bool operator ==(Prop left, Prop right) => left.Equals(right);
	public static bool operator !=(Prop left, Prop right) => !left.Equals(right);

	/// <summary>
	/// 문자열에서 암시적 변환 (편의용)
	/// </summary>
	public static implicit operator Prop(string fullName) => Parse(fullName);

	/// <summary>
	/// 문자열로 암시적 변환
	/// </summary>
	public static implicit operator string(Prop prop) => prop.FullName;
}
