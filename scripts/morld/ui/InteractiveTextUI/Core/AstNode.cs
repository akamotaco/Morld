using System.Collections.Generic;

namespace Morld.TextUI;

/// <summary>
/// AST 노드 타입
/// </summary>
public enum NodeType
{
	/// <summary>일반 텍스트 (BBCode 포함 가능)</summary>
	Text,
	/// <summary>클릭 가능한 링크 [url=meta]label[/url]</summary>
	Link,
	/// <summary>스타일 적용 [b], [i], [s], [color=X] 등</summary>
	Style,
	/// <summary>체크박스 위젯</summary>
	Todo,
	/// <summary>on/off 토글 버튼</summary>
	Button,
	/// <summary>펼침/접힘 섹션</summary>
	Toggle,
	/// <summary>라디오 버튼 (그룹 내 단일 선택)</summary>
	Radio,
	/// <summary>선택지 (비가역적 단일 선택)</summary>
	Choice,
	/// <summary>선택지 항목 (Choice의 자식)</summary>
	Option,
}

/// <summary>
/// 위젯 트리 노드.
/// 파서가 마크업을 파싱하여 이 트리를 생성하고,
/// 렌더러가 이 트리를 읽어 플랫폼별 출력을 만든다.
/// </summary>
public class AstNode
{
	/// <summary>노드 종류</summary>
	public NodeType Type;

	/// <summary>위젯 식별자 (todo/button/toggle/choice의 key, radio의 group)</summary>
	public string Key = "";

	/// <summary>값 (radio/option의 value)</summary>
	public string Value = "";

	/// <summary>표시 텍스트 (라벨)</summary>
	public string Label = "";

	/// <summary>Button 켜짐 텍스트</summary>
	public string OnText = "";

	/// <summary>Button 꺼짐 텍스트</summary>
	public string OffText = "";

	/// <summary>초기 상태 (checked/selected/open)</summary>
	public bool DefaultState;

	/// <summary>비활성화 여부</summary>
	public bool Disabled;

	/// <summary>Choice 모드: "hide", "fade", "keep"</summary>
	public string Mode = "hide";

	/// <summary>Text 노드의 원본 문자열</summary>
	public string RawText = "";

	/// <summary>Link 노드의 메타 문자열 (url=이후 값)</summary>
	public string Meta = "";

	/// <summary>
	/// Style 노드의 스타일 정보.
	/// "b", "i", "s", "color=#hex" 등.
	/// </summary>
	public string StyleTag = "";

	/// <summary>자식 노드 (Toggle의 content, Choice의 option, Style의 내부 노드)</summary>
	public List<AstNode> Children = new();
}
