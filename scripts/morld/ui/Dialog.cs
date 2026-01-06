using SharpPy;

namespace Morld;

/// <summary>
/// sharpPy에서 사용하는 PyObject 래퍼
/// Python에서 yield morld.dialog(...) 호출 시 반환되는 객체
///
/// 사용법:
///   result = yield morld.dialog("텍스트 내용")
///   # result = URL에서 @ret:값 또는 @proc:값의 값 부분
///
/// URL 패턴:
///   @ret:값 - 다이얼로그 종료, yield에 값 반환
///   @proc:값 - generator에 값 전달, 다이얼로그 유지 (텍스트는 다음 yield에서 갱신)
/// </summary>
public class PyDialogRequest : PyObject
{
    /// <summary>
    /// 다이얼로그 본문 (BBCode URL 포함 가능)
    /// </summary>
    public string Text { get; }

    public PyDialogRequest(string text)
    {
        Text = text ?? "";
    }

    public override string GetTypeName() => "DialogRequest";

    public override PyString ToStr()
    {
        var preview = Text.Length > 50 ? Text.Substring(0, 50) + "..." : Text;
        return new PyString($"<DialogRequest text='{preview}'>");
    }

    public override PyString ToRepr()
    {
        return new PyString($"DialogRequest('{Text}')");
    }
}
