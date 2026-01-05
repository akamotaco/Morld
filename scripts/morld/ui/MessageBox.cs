using SharpPy;

namespace Morld;

/// <summary>
/// MessageBox 버튼 타입 (Win32 스타일)
/// </summary>
public enum MessageBoxType
{
	Ok,        // MB_OK - [확인]
	YesNo,     // MB_YESNO - [예] [아니오]
	OkCancel   // MB_OKCANCEL - [확인] [취소]
}

/// <summary>
/// MessageBox 결과 (Win32 스타일)
/// </summary>
public enum MessageBoxResult
{
	Ok,      // IDOK
	Yes,     // IDYES
	No,      // IDNO
	Cancel   // IDCANCEL
}

/// <summary>
/// Python에서 yield로 반환되는 MessageBox 요청
/// C#에서 이 객체를 감지하면 다이얼로그를 표시하고 결과를 generator.Send()로 전달
/// </summary>
public class MessageBoxRequest
{
	/// <summary>
	/// 다이얼로그 제목 (caption)
	/// </summary>
	public string Caption { get; }

	/// <summary>
	/// 다이얼로그 본문 (text)
	/// </summary>
	public string Text { get; }

	/// <summary>
	/// 버튼 구성
	/// </summary>
	public MessageBoxType Type { get; }

	public MessageBoxRequest(string caption, string text, MessageBoxType type)
	{
		Caption = caption ?? "";
		Text = text ?? "";
		Type = type;
	}

	/// <summary>
	/// MessageBoxType을 MonologueButtonType으로 변환
	/// </summary>
	public MonologueButtonType ToMonologueButtonType()
	{
		return Type switch
		{
			MessageBoxType.Ok => MonologueButtonType.Ok,
			MessageBoxType.YesNo => MonologueButtonType.YesNo,
			MessageBoxType.OkCancel => MonologueButtonType.YesNo,  // OkCancel도 YesNo UI 사용
			_ => MonologueButtonType.Ok
		};
	}
}

/// <summary>
/// sharpPy에서 사용하는 PyObject 래퍼
/// Python에서 yield morld.messagebox(...) 호출 시 반환되는 객체
/// </summary>
public class PyMessageBoxRequest : PyObject
{
	/// <summary>
	/// 내부 C# MessageBoxRequest
	/// </summary>
	public MessageBoxRequest Request { get; }

	public PyMessageBoxRequest(string caption, string text, MessageBoxType type)
	{
		Request = new MessageBoxRequest(caption, text, type);
	}

	public override string GetTypeName() => "MessageBoxRequest";

	public override PyString ToStr()
	{
		return new PyString($"<MessageBoxRequest caption='{Request.Caption}' type={Request.Type}>");
	}

	public override PyString ToRepr()
	{
		return new PyString($"MessageBoxRequest('{Request.Caption}', '{Request.Text}', '{Request.Type}')");
	}
}
