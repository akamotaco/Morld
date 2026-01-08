using System.Collections.Generic;
using System.Text;
using SharpPy;

namespace Morld;

/// <summary>
/// Dialog autofill 타입
/// </summary>
public enum DialogAutofill
{
    /// <summary>다음 버튼만 (기본값)</summary>
    Next,
    /// <summary>이전/다음 왕복 가능</summary>
    Book,
    /// <summary>텍스트 누적 + 다음</summary>
    Scroll,
    /// <summary>자동 버튼 없음 (커스텀)</summary>
    Off
}

/// <summary>
/// sharpPy에서 사용하는 PyObject 래퍼
/// Python에서 yield morld.dialog(...) 호출 시 반환되는 객체
///
/// 사용법:
///   # 단일 텍스트
///   result = yield morld.dialog("텍스트 내용")
///
///   # 여러 페이지 (순차 표시)
///   yield morld.dialog(["페이지1", "페이지2", "페이지3"])
///
///   # autofill 타입 지정
///   yield morld.dialog(["페이지1", "페이지2"], autofill="book")
///
///   # proc 콜백 + result 반환
///   result = yield morld.dialog("텍스트", autofill="off", proc=my_proc, result=state)
///
/// URL 패턴:
///   @next - 다음 페이지로 이동 (autofill 전용)
///   @prev - 이전 페이지로 이동 (book 전용)
///   @finish - 다이얼로그 종료, result 파라미터 값 반환
///   @proc:값 - proc 콜백 호출, 텍스트 업데이트
///   @proc_finish:값 - proc 콜백 호출 후 종료
///   @ret:값 - 다이얼로그 종료, 해당 값 반환 (레거시 호환)
/// </summary>
public class PyDialogRequest : PyObject
{
    /// <summary>
    /// 다이얼로그 페이지들 (원본 텍스트, autofill 버튼 제외)
    /// </summary>
    public List<string> Pages { get; }

    /// <summary>
    /// 현재 페이지 인덱스 (멀티페이지 처리용)
    /// </summary>
    public int CurrentPageIndex { get; set; } = 0;

    /// <summary>
    /// @ret:값 클릭 시 반환할 값 (레거시 호환)
    /// </summary>
    public string ReturnValue { get; }

    /// <summary>
    /// @proc:값 클릭 시 호출될 Python 콜백 함수
    /// </summary>
    public PyObject ProcCallback { get; }

    /// <summary>
    /// autofill 타입 (next, book, scroll, off)
    /// </summary>
    public DialogAutofill Autofill { get; }

    /// <summary>
    /// @finish 시 반환할 Python 객체 (result 파라미터)
    /// </summary>
    public PyObject ResultObject { get; }

    /// <summary>
    /// 현재 페이지의 원본 텍스트 (autofill 버튼 제외)
    /// </summary>
    public string RawText => Pages.Count > 0 && CurrentPageIndex < Pages.Count
        ? Pages[CurrentPageIndex]
        : "";

    /// <summary>
    /// 현재 표시할 텍스트 (autofill 버튼 포함)
    /// </summary>
    public string Text => GetDisplayText();

    /// <summary>
    /// 다음 페이지가 있는지 확인
    /// </summary>
    public bool HasNextPage => CurrentPageIndex < Pages.Count - 1;

    /// <summary>
    /// 이전 페이지가 있는지 확인
    /// </summary>
    public bool HasPrevPage => CurrentPageIndex > 0;

    /// <summary>
    /// 단일 텍스트 생성자
    /// </summary>
    public PyDialogRequest(
        string text,
        string returnValue = null,
        PyObject procCallback = null,
        DialogAutofill autofill = DialogAutofill.Next,
        PyObject resultObject = null)
    {
        Pages = new List<string> { text ?? "" };
        ReturnValue = returnValue;
        ProcCallback = procCallback;
        Autofill = autofill;
        ResultObject = resultObject;
    }

    /// <summary>
    /// 멀티페이지 생성자
    /// </summary>
    public PyDialogRequest(
        List<string> pages,
        string returnValue = null,
        PyObject procCallback = null,
        DialogAutofill autofill = DialogAutofill.Next,
        PyObject resultObject = null)
    {
        Pages = pages ?? new List<string>();
        if (Pages.Count == 0) Pages.Add("");
        ReturnValue = returnValue;
        ProcCallback = procCallback;
        Autofill = autofill;
        ResultObject = resultObject;
    }

    /// <summary>
    /// autofill 타입에 따라 버튼이 포함된 표시 텍스트 생성
    /// </summary>
    public string GetDisplayText()
    {
        if (Autofill == DialogAutofill.Off)
        {
            return RawText;
        }

        var sb = new StringBuilder();

        // scroll 타입: 현재 페이지까지 텍스트 누적
        if (Autofill == DialogAutofill.Scroll)
        {
            for (int i = 0; i <= CurrentPageIndex; i++)
            {
                if (i > 0) sb.Append("\n\n");
                sb.Append(Pages[i]);
            }
        }
        else
        {
            sb.Append(RawText);
        }

        // 버튼 추가
        sb.Append("\n\n");

        bool isLastPage = !HasNextPage;
        bool isFirstPage = !HasPrevPage;

        switch (Autofill)
        {
            case DialogAutofill.Next:
            case DialogAutofill.Scroll:
                if (isLastPage)
                    sb.Append("[url=@finish]종료[/url]");
                else
                    sb.Append("[url=@next]다음[/url]");
                break;

            case DialogAutofill.Book:
                if (isFirstPage)
                {
                    if (isLastPage)
                        sb.Append("[url=@finish]종료[/url]");
                    else
                        sb.Append("[url=@next]다음[/url]");
                }
                else
                {
                    sb.Append("[url=@prev]이전[/url]  ");
                    if (isLastPage)
                        sb.Append("[url=@finish]종료[/url]");
                    else
                        sb.Append("[url=@next]다음[/url]");
                }
                break;
        }

        return sb.ToString();
    }

    /// <summary>
    /// 다음 페이지로 이동
    /// </summary>
    /// <returns>다음 페이지가 있으면 true</returns>
    public bool MoveToNextPage()
    {
        if (HasNextPage)
        {
            CurrentPageIndex++;
            return true;
        }
        return false;
    }

    /// <summary>
    /// 이전 페이지로 이동
    /// </summary>
    /// <returns>이전 페이지가 있으면 true</returns>
    public bool MoveToPrevPage()
    {
        if (HasPrevPage)
        {
            CurrentPageIndex--;
            return true;
        }
        return false;
    }

    /// <summary>
    /// 현재 페이지 텍스트 업데이트 (proc 콜백 결과 반영용)
    /// </summary>
    public void UpdateCurrentPageText(string newText)
    {
        if (Pages.Count > 0 && CurrentPageIndex < Pages.Count)
        {
            Pages[CurrentPageIndex] = newText ?? "";
        }
    }

    public override string GetTypeName() => "DialogRequest";

    public override PyString ToStr()
    {
        var preview = RawText.Length > 50 ? RawText.Substring(0, 50) + "..." : RawText;
        var pageInfo = Pages.Count > 1 ? $" ({CurrentPageIndex + 1}/{Pages.Count})" : "";
        return new PyString($"<DialogRequest{pageInfo} autofill={Autofill} text='{preview}'>");
    }

    public override PyString ToRepr()
    {
        return new PyString($"DialogRequest(pages={Pages.Count}, autofill={Autofill}, returnValue='{ReturnValue ?? "None"}')");
    }
}
