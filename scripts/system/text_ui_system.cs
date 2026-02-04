using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using ECS;
using Godot;
using Morld;

namespace SE
{
	/// <summary>
	/// UI 텍스트 시스템 (Focus 스택 기반)
	/// 스택에는 Focus 정보만 저장하고, 표시 시 항상 최신 데이터로 렌더링
	/// </summary>
	public class TextUISystem : ECS.System
	{
		private readonly RichTextLabel _textUiContent;
		private readonly RichTextLabel _textUiHeader;
		private readonly RichTextLabel _textUiFooter;
		private readonly FocusStack _stack = new();
		private readonly DescribeSystem _describeSystem;
		private ActionSystem _actionSystem;
		private ActionLogSystem _actionLogSystem;
		private string? _hoveredMeta = null;

		// Lazy update 플래그
		private bool _needsUpdateDisplay = false;

		// 캐시된 가로줄 (레터박스용)
		// TODO: 윈도우 크기 동적 변경 시 캐시 무효화 필요
		private string? _cachedHorizontalRule = null;

		// ============================================
		// 타이핑 효과 시스템
		// ============================================

		/// <summary>
		/// 타이핑 진행 중 여부
		/// </summary>
		private bool _isTyping = false;

		/// <summary>
		/// 현재 표시된 문자 수 (BBCode 제외)
		/// </summary>
		private int _visibleCharacters = 0;

		/// <summary>
		/// 전체 문자 수 (BBCode 제외)
		/// </summary>
		private int _totalCharacters = 0;

		/// <summary>
		/// 타이핑 대상 문자 수 (instant 구간 제외)
		/// </summary>
		private int _totalTypingCharacters = 0;

		/// <summary>
		/// 현재까지 타이핑된 문자 수 (instant 제외)
		/// </summary>
		private int _typedCharacters = 0;

		/// <summary>
		/// 즉시 출력 구간 정보 (시작 위치, 길이)
		/// [!]...[/!] 태그 제거 후의 visible char 기준
		/// </summary>
		private List<(int start, int length)> _instantSegments = new();

		/// <summary>
		/// 타이핑 경과 시간
		/// </summary>
		private float _typingElapsedTime = 0f;

		/// <summary>
		/// 타이핑 속도 (초당 문자 수)
		/// 0 = 즉시 출력 (타이핑 효과 비활성화)
		/// </summary>
		private float _typingSpeed = 50f;

		/// <summary>
		/// 현재 타이핑 중인 소스 텍스트 (hover 전 원본)
		/// hover로 인한 재렌더링 시 상태 유지 여부 판단에 사용
		/// </summary>
		private string _typingSourceText = "";

		/// <summary>
		/// 즉시 출력 태그 (페어 태그)
		/// [!]...[/!] 또는 [url=...]...[/url]
		/// </summary>
		private const string InstantTagOpen = "[!]";
		private const string InstantTagClose = "[/!]";

		/// <summary>
		/// UI 구분선 (즉시 출력 태그 포함)
		/// Python의 ui.divider()와 동일
		/// </summary>
		public const string Divider = "[!][color=gray]────────────────────[/color][/!]";

		/// <summary>
		/// 타이핑 진행 중인지 확인
		/// </summary>
		public bool IsTyping => _isTyping;

		/// <summary>
		/// 타이핑 속도 설정 (초당 문자 수, 0 = 즉시 출력)
		/// </summary>
		public float TypingSpeed
		{
			get => _typingSpeed;
			set => _typingSpeed = Math.Max(0, value);
		}

		public TextUISystem(
			RichTextLabel textUiContent,
			RichTextLabel textUiHeader,
			RichTextLabel textUiFooter,
			DescribeSystem describeSystem)
		{
			_textUiContent = textUiContent;
			_textUiHeader = textUiHeader;
			_textUiFooter = textUiFooter;
			_describeSystem = describeSystem;
		}

		/// <summary>
		/// 레터박스용 가로줄 생성 (RichTextLabel 너비에 맞춤)
		/// 라벨 너비가 유효할 때만 캐싱 (레이아웃 완료 전이면 기본값 반환)
		/// </summary>
		private string GetHorizontalRule()
		{
			if (_cachedHorizontalRule != null)
				return _cachedHorizontalRule;

			// Header 기준으로 너비 계산 (없으면 Content 사용)
			var label = _textUiHeader ?? _textUiContent;
			if (label == null)
				return Divider;

			try
			{
				// 라벨 너비 확인 (레이아웃 완료 전이면 0 또는 작은 값)
				float labelWidth = label.Size.X;
				if (labelWidth < 100)
					return Divider; // 레이아웃 미완료 - 캐싱하지 않고 기본값 반환

				// 폰트 정보로 문자 너비 계산
				// '─' (U+2500)는 일부 폰트에서 0 반환 → 'M' 기준으로 추정
				var font = label.GetThemeFont("normal_font");
				var fontSize = label.GetThemeFontSize("normal_font");
				float charWidthM = font.GetCharSize('M', fontSize).X;

				if (charWidthM <= 0)
					return Divider;

				// '─'는 대략 'M'의 50~60% 너비 추정
				float estimatedCharWidth = charWidthM * 0.55f;
				int charCount = Math.Max(1, (int)(labelWidth / estimatedCharWidth));

				// BBCode 색상 포함, 2줄 (레터박스 효과)
				var line = new string('─', charCount);
				_cachedHorizontalRule = $"[color=gray]{line}\n{line}[/color]";
			}
			catch (System.Exception)
			{
				// 폰트 정보 획득 실패 시 기본값 (캐싱하지 않음)
				return Divider;
			}

			return _cachedHorizontalRule;
		}

		/// <summary>
		/// ActionSystem 참조 설정 (시스템 등록 후 호출)
		/// </summary>
		public void SetActionSystem(ActionSystem actionSystem)
		{
			_actionSystem = actionSystem;
		}

		/// <summary>
		/// ActionLogSystem 참조 설정 (시스템 등록 후 호출)
		/// </summary>
		public void SetActionLogSystem(ActionLogSystem actionLogSystem)
		{
			_actionLogSystem = actionLogSystem;
			_actionLogSystem.OnLogAdded = RequestUpdateDisplay;
		}

		/// <summary>
		/// 현재 hover 중인 메타 설정 (null = hover 없음)
		/// </summary>
		public void SetHoveredMeta(string? meta)
		{
			if (_hoveredMeta == meta) return;
			_hoveredMeta = meta;
			RequestUpdateDisplay();
		}

		/// <summary>
		/// UI 업데이트 요청 (lazy update)
		/// 실제 렌더링은 FlushDisplay()에서 수행
		/// </summary>
		public void RequestUpdateDisplay()
		{
			_needsUpdateDisplay = true;
		}

		/// <summary>
		/// 스택이 비어있는지 확인
		/// </summary>
		public bool IsStackEmpty() => _stack.Count == 0;

		/// <summary>
		/// 현재 Focus에서 자동 시간 흐름이 허용되는지 확인
		/// - Situation, Unit: 항상 허용 (기본 게임 화면)
		/// - Dialog: TimeFlows 속성에 따름 (기본 false)
		/// - 기타 (Inventory, Item, Result): 허용하지 않음
		///
		/// [미구현] 시간이 흐르는 Focus에서 이벤트 발생 시:
		/// - 새 이벤트가 스택에 push되면 해당 Focus의 TimeFlows를 다시 체크
		/// - 이벤트에서 아이템 상태 변경 시 기존 Focus가 영향받을 수 있음
		/// </summary>
		public bool CanAutoTimeFlow()
		{
			if (_stack.Current == null)
				return true; // 스택 비어있으면 허용 (Situation과 동일)

			return _stack.Current.Type switch
			{
				FocusType.Situation => true,
				FocusType.Unit => true,
				FocusType.Dialog => _stack.Current.TimeFlows,
				_ => false // Inventory, Item, Result
			};
		}

		/// <summary>
		/// 대기 중인 UI 업데이트 수행 (lazy update 적용)
		/// </summary>
		public void FlushDisplay()
		{
			if (!_needsUpdateDisplay) return;
			_needsUpdateDisplay = false;

			Godot.GD.Print($"[TextUISystem] FlushDisplay: stack={_stack.Current?.Type}, hoveredMeta={_hoveredMeta ?? "null"}");

			if (_stack.Current == null)
			{
				Godot.GD.Print("[TextUISystem] FlushDisplay: stack is empty, clearing text");
				_textUiContent.Text = "";
				if (_textUiHeader != null) _textUiHeader.Text = "";
				if (_textUiFooter != null) _textUiFooter.Text = "";
				_isTyping = false;
				_typingSourceText = "";
				return;
			}

			// Focus 타입별 header/footer 결정
			var focusType = _stack.Current.Type;
			string headerText = "";
			string footerText = "";

			switch (focusType)
			{
				case FocusType.Situation:
				case FocusType.Unit:
					// 표시: Python에서 header/footer 가져오기
					headerText = GetHeaderFromPython() ?? "";
					footerText = GetFooterFromPython() ?? "";
					break;

				case FocusType.Dialog:
				case FocusType.Inventory:
				case FocusType.Item:
				case FocusType.Result:
					// 레터박스: 동적 너비 구분선
					var hr = GetHorizontalRule();
					headerText = hr;
					footerText = hr;
					break;
			}

			// Header/Footer 출력 ([!]...[/!] 태그 제거 - 타이핑 효과 미적용)
			if (_textUiHeader != null)
			{
				var (cleanHeader, _) = ParseInstantTags(headerText);
				_textUiHeader.Text = cleanHeader;
			}
			if (_textUiFooter != null)
			{
				var (cleanFooter, _) = ParseInstantTags(footerText);
				_textUiFooter.Text = cleanFooter;
			}

			// Content 렌더링
			var text = RenderFocusContent(_stack.Current);

			var renderedText = ToggleRenderer.Render(
				text,
				_stack.Current.ExpandedToggles,
				_hoveredMeta
			);

			// Dialog Focus인 경우 타이핑 효과 적용
			if (_stack.Current.Type == FocusType.Dialog)
			{
				// 같은 소스 텍스트면 스타일만 업데이트 (hover 등으로 인한 재렌더링)
				if (text == _typingSourceText)
				{
					// [!]...[/!] 태그 제거 (hover 스타일만 다를 뿐 내용은 동일)
					var (cleanText, _) = ParseInstantTags(renderedText);
					// 깜박임 방지: 현재 상태 유지하면서 Text만 교체
					int prevVisible = _textUiContent.VisibleCharacters;
					_textUiContent.VisibleCharacters = -1;  // 전체 표시로 잠깐 전환
					_textUiContent.Text = cleanText;
					_totalCharacters = _textUiContent.GetTotalCharacterCount();
					_textUiContent.VisibleCharacters = prevVisible;  // 원래 상태로 복원

					if (_isTyping)
					{
						// 타이핑 진행 중: 현재 진행률로 표시 문자 수 재계산
						_visibleCharacters = CalculateVisibleCharsAtProgress(_typedCharacters);
						_textUiContent.VisibleCharacters = _visibleCharacters;
						Godot.GD.Print($"[TextUISystem] FlushDisplay: hover update during typing at {_visibleCharacters}/{_totalCharacters}");
					}
					else
					{
						// 타이핑 완료: 전체 표시 유지
						_textUiContent.VisibleCharacters = -1;
						Godot.GD.Print($"[TextUISystem] FlushDisplay: hover update after typing complete");
					}
				}
				else
				{
					// 새 콘텐츠: 타이핑 시작
					_typingSourceText = text;
					StartTyping(renderedText);
					Godot.GD.Print($"[TextUISystem] FlushDisplay: started typing for Dialog, textLen={renderedText.Length}");
				}
			}
			else
			{
				// 다른 Focus는 즉시 표시
				// [!]...[/!] 태그는 제거해야 함 (타이핑 효과용 마커이므로)
				var (cleanText, _) = ParseInstantTags(renderedText);
				_textUiContent.Text = cleanText;
				_textUiContent.VisibleCharacters = -1;
				_isTyping = false;
				_typingSourceText = "";  // Dialog 벗어날 때 초기화
			}

			Godot.GD.Print($"[TextUISystem] FlushDisplay: rendered {_stack.Current.Type}, textLen={_textUiContent.Text.Length}");

			// Header/Footer Visible 제어 (Python ui.set_show_header/footer 반영)
			if (_textUiHeader != null)
				_textUiHeader.Visible = GetHeaderVisibleFromPython();
			if (_textUiFooter != null)
				_textUiFooter.Visible = GetFooterVisibleFromPython();

			// 읽음 처리는 FlushDisplay에서 하지 않음
			// OnPlayerAction()에서 플레이어 액션 시점에 처리
		}

		// ============================================
		// 타이핑 효과 메서드
		// ============================================

		/// <summary>
		/// 타이핑 효과 시작 (Dialog Focus 전용)
		/// [!]...[/!] 태그를 파싱하여 instant 구간을 추출하고, 태그 제거 후 표시
		/// </summary>
		/// <param name="text">전체 텍스트 (BBCode 포함, [!]...[/!] 태그 포함)</param>
		private void StartTyping(string text)
		{
			// [!]...[/!] 태그 파싱 및 제거
			var (cleanText, segments) = ParseInstantTags(text);
			_instantSegments = segments;

			// 깜박임 방지: Text 설정 전에 먼저 전체 표시 상태로 설정
			// 이후 필요한 경우 VisibleCharacters를 다시 조정
			_textUiContent.VisibleCharacters = -1;
			_textUiContent.Text = cleanText;

			// 타이핑 속도 0이면 즉시 출력
			if (_typingSpeed <= 0)
			{
				_isTyping = false;
				return;
			}

			_totalCharacters = _textUiContent.GetTotalCharacterCount();
			_totalTypingCharacters = CalculateTotalTypingCharacters(cleanText);

			// 타이핑 대상이 없으면 (모두 instant) 즉시 출력 유지
			if (_totalTypingCharacters == 0)
			{
				_isTyping = false;
				return;
			}

			_typedCharacters = 0;
			_typingElapsedTime = 0f;
			_isTyping = true;

			// 초기 표시 (타이핑 진행률 0에서의 표시 문자 수)
			_visibleCharacters = CalculateVisibleCharsAtProgress(0);
			_textUiContent.VisibleCharacters = _visibleCharacters;
		}

		/// <summary>
		/// 타이핑 업데이트 (매 프레임 호출)
		/// GameEngine._Process()에서 호출됨
		/// Frozen 상태와 무관하게 항상 동작
		/// </summary>
		/// <param name="delta">프레임 경과 시간 (초)</param>
		public void UpdateTyping(float delta)
		{
			if (!_isTyping) return;

			_typingElapsedTime += delta;
			_typedCharacters = Math.Min(
				(int)(_typingElapsedTime * _typingSpeed),
				_totalTypingCharacters
			);

			// 타이핑 진행률에 따른 표시 문자 수 계산
			_visibleCharacters = CalculateVisibleCharsAtProgress(_typedCharacters);
			_textUiContent.VisibleCharacters = _visibleCharacters;

			if (_typedCharacters >= _totalTypingCharacters)
			{
				FinishTyping();
			}
		}

		/// <summary>
		/// 타이핑 완료 (스킵 또는 자연 완료)
		/// </summary>
		public void FinishTyping()
		{
			_isTyping = false;
			_textUiContent.VisibleCharacters = -1; // 전체 표시
		}

		/// <summary>
		/// [!]...[/!] 및 [url=...]...[/url] 태그 파싱
		/// - [!]...[/!]: 태그 제거, 내용만 출력, instant 구간 등록
		/// - [url=...]...[/url]: BBCode 유지, instant 구간 등록
		/// </summary>
		/// <returns>(태그 제거된 텍스트, instant 구간 리스트)</returns>
		private (string cleanText, List<(int start, int length)> segments) ParseInstantTags(string text)
		{
			var segments = new List<(int start, int length)>();
			if (string.IsNullOrEmpty(text))
				return (text, segments);

			var result = new System.Text.StringBuilder();
			int visibleCharPos = 0;  // 태그 제거 후 visible char 위치
			int i = 0;

			while (i < text.Length)
			{
				// [!] 태그 시작 찾기
				if (i + InstantTagOpen.Length <= text.Length &&
					text.Substring(i, InstantTagOpen.Length) == InstantTagOpen)
				{
					// [/!] 매칭 태그 찾기 (중첩 고려, depth counting)
					int closeIndex = FindMatchingCloseTag(text, i + InstantTagOpen.Length);
					if (closeIndex >= 0)
					{
						// instant 구간 내용 추출
						string content = text.Substring(i + InstantTagOpen.Length, closeIndex - i - InstantTagOpen.Length);

						// nested [!]...[/!] 제거 (중첩 태그 처리)
						content = content.Replace(InstantTagOpen, "").Replace(InstantTagClose, "");

						int contentVisibleChars = CountVisibleChars(content);

						// instant 구간 정보 저장
						segments.Add((visibleCharPos, contentVisibleChars));

						// 내용만 결과에 추가 (태그 제외)
						result.Append(content);
						visibleCharPos += contentVisibleChars;

						i = closeIndex + InstantTagClose.Length;
						continue;
					}
				}

				// [url=...] 태그 시작 찾기 (BBCode 유지, instant 구간 등록)
				if (i + 5 <= text.Length && text.Substring(i, 5) == "[url=")
				{
					// [/url] 태그 끝 찾기
					int closeIndex = text.IndexOf("[/url]", i);
					if (closeIndex >= 0)
					{
						// URL 전체 (태그 포함) 추출
						string urlFull = text.Substring(i, closeIndex - i + 6); // 6 = "[/url]".Length
						int urlVisibleChars = CountVisibleChars(urlFull);

						// instant 구간 정보 저장 (URL은 BBCode 유지하면서 즉시 출력)
						segments.Add((visibleCharPos, urlVisibleChars));

						// URL 전체를 결과에 추가 (BBCode 포함)
						result.Append(urlFull);
						visibleCharPos += urlVisibleChars;

						i = closeIndex + 6;
						continue;
					}
				}

				// BBCode 태그 처리 (visible char 카운트에서 제외)
				if (text[i] == '[')
				{
					int closeIndex = text.IndexOf(']', i);
					if (closeIndex >= 0)
					{
						result.Append(text.Substring(i, closeIndex - i + 1));
						i = closeIndex + 1;
						continue;
					}
				}

				// 일반 문자
				result.Append(text[i]);
				visibleCharPos++;
				i++;
			}

			return (result.ToString(), segments);
		}

		/// <summary>
		/// 타이핑 대상 문자 수 계산 (instant 구간 및 공백 제외)
		///
		/// 공백(스페이스, 줄바꿈, 탭)은 타이핑 대상에서 제외됩니다.
		/// 이유: [!]A[/!]\n[!]B[/!] 같은 패턴에서 줄바꿈이 타이핑 대상이 되면
		/// 전체가 instant인데도 깜박임이 발생하기 때문입니다.
		/// </summary>
		private int CalculateTotalTypingCharacters(string cleanText)
		{
			if (string.IsNullOrEmpty(cleanText)) return 0;

			// 전체 visible 문자 중 instant 구간과 공백을 제외한 타이핑 대상 계산
			int typingChars = 0;
			int visiblePos = 0;
			bool inTag = false;

			foreach (char c in cleanText)
			{
				if (c == '[') { inTag = true; continue; }
				if (c == ']') { inTag = false; continue; }
				if (inTag) continue;

				// visible 문자
				bool isInstant = IsInInstantSegment(visiblePos);
				bool isWhitespace = char.IsWhiteSpace(c);

				// instant도 아니고 공백도 아닌 문자만 타이핑 대상
				if (!isInstant && !isWhitespace)
				{
					typingChars++;
				}

				visiblePos++;
			}

			return typingChars;
		}

		/// <summary>
		/// 타이핑 진행률에 따른 표시 문자 수 계산
		/// - instant 구간: 해당 구간 시작점에 도달하면 전체를 한 번에 표시
		/// - 공백 문자: 즉시 표시 (타이핑 진행에 포함하지 않음)
		/// - 일반 문자: 1글자씩 증가
		/// - 정책: 항상 최소 1문자는 표시 (빈 화면 방지)
		///
		/// 공백을 즉시 표시하는 이유:
		/// [!]A[/!]\n[!]B[/!] 같은 패턴에서 줄바꿈(\n)이 타이핑 대상이 되면
		/// 전체가 instant인데도 깜박임이 발생합니다.
		/// 공백은 시각적으로 보이지 않으므로 즉시 표시해도 사용자 경험에 영향이 없습니다.
		/// </summary>
		/// <param name="typedChars">타이핑된 문자 수 (instant 및 공백 제외)</param>
		private int CalculateVisibleCharsAtProgress(int typedChars)
		{
			string cleanText = _textUiContent.Text;
			if (string.IsNullOrEmpty(cleanText)) return 0;

			// visible char 위치 → 실제 문자 매핑 생성
			var visibleCharMap = BuildVisibleCharMap(cleanText);
			int totalVisible = visibleCharMap.Count;
			if (totalVisible == 0) return 0;

			int visibleChars = 0;      // 실제 표시할 문자 수
			int typingProgress = 0;    // 타이핑 진행 카운터 (instant 및 공백 제외)

			for (int charPos = 0; charPos < totalVisible; charPos++)
			{
				char currentChar = visibleCharMap[charPos];
				bool isWhitespace = char.IsWhiteSpace(currentChar);

				if (IsInInstantSegment(charPos))
				{
					// instant 구간: 구간 시작점에 도달했으면 표시
					var segment = GetInstantSegmentAt(charPos);
					if (segment.HasValue && charPos == segment.Value.start)
					{
						// 구간 시작점: 이전까지 도달했으면 전체 구간 표시
						if (typingProgress <= typedChars)
						{
							visibleChars += segment.Value.length;
						}
					}
					// 구간 중간/끝은 이미 시작점에서 처리됨
				}
				else if (isWhitespace)
				{
					// 공백 문자: 즉시 표시 (타이핑 진행에 포함하지 않음)
					// 이전까지의 타이핑 진행에 도달했으면 표시
					if (typingProgress <= typedChars)
					{
						visibleChars++;
					}
				}
				else
				{
					// 일반 문자: 1글자씩 진행
					// 첫 글자는 항상 표시 (visibleChars == 0일 때 무조건 포함)
					if (typingProgress < typedChars || visibleChars == 0)
					{
						visibleChars++;
						typingProgress++;
					}
					else
					{
						// 타이핑 완료 지점
						return visibleChars;
					}
				}
			}

			return visibleChars;
		}

		/// <summary>
		/// BBCode를 제외한 visible 문자 리스트 생성
		/// </summary>
		private List<char> BuildVisibleCharMap(string text)
		{
			var result = new List<char>();
			bool inTag = false;

			foreach (char c in text)
			{
				if (c == '[') { inTag = true; continue; }
				if (c == ']') { inTag = false; continue; }
				if (inTag) continue;

				result.Add(c);
			}

			return result;
		}

		/// <summary>
		/// 해당 위치가 instant 구간 내인지 확인
		/// </summary>
		private bool IsInInstantSegment(int pos)
		{
			foreach (var (start, length) in _instantSegments)
			{
				if (pos >= start && pos < start + length)
					return true;
			}
			return false;
		}

		/// <summary>
		/// 해당 위치를 포함하는 instant 구간 반환
		/// </summary>
		private (int start, int length)? GetInstantSegmentAt(int pos)
		{
			foreach (var segment in _instantSegments)
			{
				if (pos >= segment.start && pos < segment.start + segment.length)
					return segment;
			}
			return null;
		}

		/// <summary>
		/// 중첩 [!]...[/!]를 고려하여 매칭되는 [/!] 태그 위치 찾기
		/// </summary>
		/// <param name="text">전체 텍스트</param>
		/// <param name="startIndex">검색 시작 위치 (여는 [!] 다음 위치)</param>
		/// <returns>매칭되는 [/!] 시작 위치, 없으면 -1</returns>
		private static int FindMatchingCloseTag(string text, int startIndex)
		{
			int depth = 1;
			int i = startIndex;

			while (i < text.Length && depth > 0)
			{
				// [!] 찾기
				if (i + InstantTagOpen.Length <= text.Length &&
					text.Substring(i, InstantTagOpen.Length) == InstantTagOpen)
				{
					depth++;
					i += InstantTagOpen.Length;
					continue;
				}

				// [/!] 찾기
				if (i + InstantTagClose.Length <= text.Length &&
					text.Substring(i, InstantTagClose.Length) == InstantTagClose)
				{
					depth--;
					if (depth == 0)
					{
						return i;  // 매칭되는 닫는 태그 위치
					}
					i += InstantTagClose.Length;
					continue;
				}

				i++;
			}

			return -1;  // 매칭되는 태그 없음
		}

		/// <summary>
		/// BBCode를 제외한 실제 표시 문자 수 계산
		/// </summary>
		private static int CountVisibleChars(string text)
		{
			int count = 0;
			bool inTag = false;
			foreach (char c in text)
			{
				if (c == '[') inTag = true;
				else if (c == ']') inTag = false;
				else if (!inTag) count++;
			}
			return count;
		}

		/// <summary>
		/// 화면 콘텐츠가 변경될 때 호출 (플레이어 액션 시)
		/// 새로운 화면으로 전환되기 전에 현재 상태를 정리하는 역할
		///
		/// 포함 기능:
		/// - 현재 표시된 로그 읽음 처리 (markLogsAsRead=true일 때만)
		/// - (향후) 기타 정리 작업 추가 가능
		/// </summary>
		/// <param name="markLogsAsRead">true면 로그 읽음 처리, false면 건너뜀 (토글 등 UI 상태만 변경 시)</param>
		public void OnContentChange(bool markLogsAsRead = true)
		{
			// 스택이 비어있으면 무시
			if (_stack.Current == null)
				return;

			// 1. 로그 읽음 처리 (Situation, Unit 화면에서만, markLogsAsRead=true일 때)
			if (markLogsAsRead &&
				(_stack.Current.Type == FocusType.Situation || _stack.Current.Type == FocusType.Unit))
			{
				MarkPrintedLogsAsRead();
			}

			// 2. (향후 추가 기능을 여기에)
		}

		/// <summary>
		/// 현재 Focus를 기반으로 텍스트 생성 및 표시 (즉시 실행)
		/// </summary>
		public void UpdateDisplay()
		{
			RequestUpdateDisplay();
			FlushDisplay();
		}

		/// <summary>
		/// 출력된 로그를 읽음 처리
		/// </summary>
		private void MarkPrintedLogsAsRead()
		{
			_actionLogSystem?.MarkPrintedLogsAsRead();
		}

		/// <summary>
		/// Focus 정보를 기반으로 텍스트 생성
		/// </summary>
		private string RenderFocusContent(Focus focus)
		{
			return focus.Type switch
			{
				FocusType.Situation => RenderSituation(),
				FocusType.Unit => RenderUnit(focus.TargetUnitId ?? 0),
				FocusType.Inventory => RenderInventory(),
				FocusType.Item => RenderItem(focus.ItemId ?? 0, focus.Context ?? "inventory", focus.TargetUnitId),
				FocusType.Result => RenderResult(focus.Message ?? ""),
				FocusType.Dialog => RenderDialog(focus),
				_ => ""
			};
		}

		/// <summary>
		/// 다이얼로그 렌더링 (morld.dialog() API)
		/// BBCode URL을 그대로 표시 (@ret:값, @proc:값 패턴은 MetaActionHandler에서 처리)
		/// </summary>
		private string RenderDialog(Focus focus)
		{
			// 구분선은 FlushDisplay()에서 header/footer로 출력 (레터박스 스타일)
			// content는 순수 대화 텍스트만
			return focus.DialogText ?? "";
		}

		private string RenderSituation()
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

			var lookResult = _playerSystem.Look();
			var time = (_hub.GetSystem("worldSystem") as WorldSystem).GetTime();

			var lines = new List<string>();

			// Header/Footer는 FlushDisplay()에서 처리

			// Body: 묘사 텍스트
			var describeText = _describeSystem.GetSituationText(lookResult, time);
			Godot.GD.Print($"[RenderSituation] describeText.Length={describeText?.Length ?? 0}");
			lines.Add(describeText);

			// 행동 텍스트 (Python 훅 또는 C# 폴백)
			var actionText = GetActionTextFromPython();
			Godot.GD.Print($"[RenderSituation] actionText from Python: {actionText?.Length ?? 0} chars");
			if (string.IsNullOrEmpty(actionText))
			{
				// Python 훅 실패 시 C# 폴백
				actionText = _actionSystem.GetActionText(lookResult);
				Godot.GD.Print($"[RenderSituation] actionText from C# fallback: {actionText?.Length ?? 0} chars");
			}
			lines.Add(actionText);

			var result = string.Join("\n", lines);
			Godot.GD.Print($"[RenderSituation] total={result.Length} chars");
			return result;
		}

		/// <summary>
		/// Python ui.get_action_text() 훅 호출
		/// </summary>
		private string? GetActionTextFromPython()
		{
			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			try
			{
				// ui 모듈의 get_action_text() 호출
				var result = _scriptSystem.CallModuleFunction("ui", "get_action_text");
				if (result != null && result is not SharpPy.PyNone)
				{
					var text = result.AsString();
					if (!string.IsNullOrEmpty(text))
					{
						// 구분선 추가
						return Divider + "\n" + text;
					}
				}
			}
			catch (System.Exception ex)
			{
				Godot.GD.PrintErr($"[TextUISystem] Python get_action_text() error: {ex.Message}");
			}

			return null;
		}

		/// <summary>
		/// Python ui.get_header() 훅 호출
		/// Focus 화면 상단에 시간/날씨 정보 표시
		/// </summary>
		private string? GetHeaderFromPython()
		{
			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			try
			{
				var result = _scriptSystem.CallModuleFunction("ui", "get_header");
				if (result != null && result is not SharpPy.PyNone)
				{
					var text = result.AsString();
					if (!string.IsNullOrEmpty(text))
					{
						return text;
					}
				}
			}
			catch (System.Exception ex)
			{
				Godot.GD.PrintErr($"[TextUISystem] Python get_header() error: {ex.Message}");
			}

			return null;
		}

		/// <summary>
		/// Python ui.get_footer() 훅 호출
		/// Focus 화면 하단에 상태바 정보 표시
		/// </summary>
		private string? GetFooterFromPython()
		{
			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			try
			{
				var result = _scriptSystem.CallModuleFunction("ui", "get_footer");
				if (result != null && result is not SharpPy.PyNone)
				{
					var text = result.AsString();
					if (!string.IsNullOrEmpty(text))
					{
						return text;
					}
				}
			}
			catch (System.Exception ex)
			{
				Godot.GD.PrintErr($"[TextUISystem] Python get_footer() error: {ex.Message}");
			}

			return null;
		}

		/// <summary>
		/// Python ui.is_header_visible() 호출
		/// Header UI 표시 여부 확인
		/// </summary>
		private bool GetHeaderVisibleFromPython()
		{
			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			try
			{
				var result = _scriptSystem.CallModuleFunction("ui", "is_header_visible");
				if (result is SharpPy.PyBool pyBool)
				{
					return pyBool.Value;
				}
			}
			catch (System.Exception ex)
			{
				Godot.GD.PrintErr($"[TextUISystem] Python is_header_visible() error: {ex.Message}");
			}

			return true; // 기본값: 표시
		}

		/// <summary>
		/// Python ui.is_footer_visible() 호출
		/// Footer UI 표시 여부 확인
		/// </summary>
		private bool GetFooterVisibleFromPython()
		{
			var _scriptSystem = this._hub.GetSystem("scriptSystem") as ScriptSystem;

			try
			{
				var result = _scriptSystem.CallModuleFunction("ui", "is_footer_visible");
				if (result is SharpPy.PyBool pyBool)
				{
					return pyBool.Value;
				}
			}
			catch (System.Exception ex)
			{
				Godot.GD.PrintErr($"[TextUISystem] Python is_footer_visible() error: {ex.Message}");
			}

			return true; // 기본값: 표시
		}

		private string RenderUnit(int unitId)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

			var unitLook = _playerSystem.LookUnit(unitId);
			if (unitLook == null) return "[color=gray]유닛을 찾을 수 없습니다.[/color]\n\n[url=back]뒤로[/url]";

			// Header/Footer는 FlushDisplay()에서 처리
			// Body: 유닛 정보
			return _describeSystem.GetUnitLookText(unitLook);
		}

		private string RenderInventory()
		{
			// 레터박스 스타일: header/footer에 구분선이 표시되므로 body만 반환
			return _describeSystem.GetInventoryText();
		}

		private string RenderItem(int itemId, string context, int? targetUnitId)
		{
			var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
			var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;

			// 아이템 개수 조회
			int count = 0;
			if (_inventorySystem != null)
			{
				if (context == "inventory" && _playerSystem != null)
				{
					var player = _playerSystem.FindPlayerUnit();
					if (player != null)
					{
						var inv = _inventorySystem.GetUnitInventory(player.Id);
						inv.TryGetValue(itemId, out count);
					}
				}
				else if (context == "container" && targetUnitId.HasValue)
				{
					var inv = _inventorySystem.GetUnitInventory(targetUnitId.Value);
					inv.TryGetValue(itemId, out count);
				}
			}

			// 레터박스 스타일: header/footer에 구분선이 표시되므로 body만 반환
			return _describeSystem.GetItemMenuText(context, itemId, count, targetUnitId);
		}

		private string RenderResult(string message)
		{
			return $"[b]{message}[/b]\n\n[url=back]뒤로[/url]";
		}

		// === 화면 전환 API (Focus Push) ===

		/// <summary>
		/// 상황 화면 표시 (스택 초기화 후 Push)
		/// 로그는 유지됨 (MaxLogLength 초과 시에만 자동 삭제)
		/// </summary>
		public void ShowSituation()
		{
			Clear();
			_stack.Push(Focus.Situation());
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 현재 Focus 화면 갱신 (스택 유지)
		/// ShowSituation()과 달리 Clear()를 호출하지 않아 스택이 유지됨
		/// 시간 흐름 시 호출하여 Dialog/Item Focus를 방해하지 않음
		/// </summary>
		public void RefreshSituationDisplay()
		{
			// 스택 초기화 없이 현재 Focus 화면만 갱신
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 유닛 상세 화면 표시 (Push)
		/// </summary>
		public void ShowUnitLook(int unitId)
		{
			_stack.Push(Focus.Unit(unitId));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 인벤토리 화면 표시 (Push)
		/// </summary>
		public void ShowInventory()
		{
			_stack.Push(Focus.Inventory());
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 아이템 메뉴 표시 (Push)
		/// </summary>
		public void ShowItemMenu(int itemId, string context, int? unitId = null)
		{
			_stack.Push(Focus.Item(itemId, context, unitId));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 결과 메시지 표시 (Push)
		/// </summary>
		public void ShowResult(string message)
		{
			_stack.Push(Focus.Result(message));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 다이얼로그 Push (첫 yield morld.dialog() 호출 시)
		/// Note: 로그 읽음 처리는 액션 버튼 클릭 시점(HandleAction)에서만 수행
		/// 이벤트 연쇄 처리 시 중간 다이얼로그에서 로그가 유실되지 않도록 함
		/// </summary>
		/// <param name="text">다이얼로그 텍스트</param>
		/// <param name="timeConsumed">다이얼로그 완료 시 소요 시간</param>
		/// <param name="timeFlows">자동 시간 흐름 허용 여부 (기본값: false, 대부분의 다이얼로그는 시간 정지)</param>
		public void PushDialog(string text, int timeConsumed = 0, bool timeFlows = false)
		{
			// 새 다이얼로그는 타이핑 소스 리셋 (새 페이지는 새로 타이핑 시작)
			_typingSourceText = "";

			_stack.Push(Focus.Dialog(text, timeConsumed, timeFlows));
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 다이얼로그 텍스트 갱신 (@proc: 후 다음 yield 호출 시)
		/// lazy update로 변경 - FlushDisplay()에서 일괄 렌더링
		/// </summary>
		public void UpdateDialogText(string text)
		{
			if (_stack.Current.Type != FocusType.Dialog)
			{
				Godot.GD.PrintErr("[TextUISystem] UpdateDialogText called but no dialog is open - this is a bug!");
				return;
			}

			_stack.Current.DialogText = text;
			RequestUpdateDisplay();
		}

		// === 스택 조작 API ===

		/// <summary>
		/// 최상위 레이어 Pop (자동으로 상위 화면 갱신)
		/// </summary>
		public void Pop()
		{
			_stack.Pop();
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 현재 포커스가 유효하지 않으면 Pop (아이템 0개 등)
		/// </summary>
		public void PopIfInvalid()
		{
			if (_stack.Current == null) return;

			if (_stack.Current.Type == FocusType.Item)
			{
				var itemId = _stack.Current.ItemId ?? 0;
				var context = _stack.Current.Context ?? "inventory";
				var unitId = _stack.Current.TargetUnitId;

				var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
				var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;

				// context에 따라 소유자 결정
				int ownerId;
				if (context == "inventory")
				{
					var player = _playerSystem?.FindPlayerUnit();
					if (player == null) return;
					ownerId = player.Id;
				}
				else if (context == "container" && unitId.HasValue)
				{
					ownerId = unitId.Value;
				}
				else
				{
					return;
				}

				// 아이템이 없으면 Pop
				if (!_inventorySystem.UnitHasItem(ownerId, itemId))
				{
					Pop();
					return;
				}
			}

			RequestUpdateDisplay();
		}

		/// <summary>
		/// 스택 전체 비우기
		/// </summary>
		public void Clear()
		{
			_stack.Clear();
		}

		/// <summary>
		/// Situation Focus까지 스택 Pop (스킨십 비정상 종료 등에 사용)
		/// Situation 레이어를 만나면 멈추고, Situation이 없으면 스택 전체 비우고 Situation Push
		/// </summary>
		public void PopToSituation()
		{
			while (_stack.Count > 0)
			{
				if (_stack.Current?.Type == FocusType.Situation)
				{
					RequestUpdateDisplay();
					return;
				}
				_stack.Pop();
			}

			// 스택이 비었으면 Situation으로 초기화
			_stack.Push(Focus.Situation());
			RequestUpdateDisplay();
		}

		/// <summary>
		/// 토글 펼침/접힘 전환
		/// </summary>
		public void ToggleExpand(string toggleId)
		{
			if (_stack.Current == null) return;

			var toggles = _stack.Current.ExpandedToggles;
			if (toggles.Contains(toggleId))
				toggles.Remove(toggleId);
			else
				toggles.Add(toggleId);

			RequestUpdateDisplay();
		}

		/// <summary>
		/// 스택이 비어있는지 확인
		/// </summary>
		public bool IsEmpty => _stack.Count == 0;

		/// <summary>
		/// 현재 Focus 정보 반환
		/// </summary>
		public Focus? CurrentFocus => _stack.Current;

		/// <summary>
		/// Proc은 빈 구현 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
