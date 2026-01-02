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
	/// UI 텍스트 시스템 (RichTextLabel.Text 수정의 단일 지점)
	/// ECS System으로 등록되어 GameEngine에서 관리
	/// </summary>
	public class TextUISystem : ECS.System
	{
		private readonly RichTextLabel _textUi;
		private readonly ScreenStack _stack = new();
		private readonly DescribeSystem _describeSystem;
		private string? _hoveredMeta = null;

		public TextUISystem(RichTextLabel textUi, DescribeSystem describeSystem)
		{
			_textUi = textUi;
			_describeSystem = describeSystem;
		}

		/// <summary>
		/// 현재 hover 중인 메타 설정 (null = hover 없음)
		/// </summary>
		public void SetHoveredMeta(string? meta)
		{
			if (_hoveredMeta == meta) return;
			_hoveredMeta = meta;
			UpdateDisplay();
		}

		/// <summary>
		/// 현재 화면을 렌더링하여 RichTextLabel에 반영
		/// </summary>
		public void UpdateDisplay()
		{
			if (_stack.Current == null)
			{
				_textUi.Text = "";
				return;
			}
			_textUi.Text = ToggleRenderer.Render(
				_stack.Current.Text,
				_stack.Current.ExpandedToggles,
				_hoveredMeta
			);
		}

		// === 화면 전환 API ===

		/// <summary>
		/// 상황 화면 표시 (스택 초기화 후 Push)
		/// </summary>
		public void ShowSituation(LookResult lookResult, GameTime? time)
		{
			var text = _describeSystem.GetSituationText(lookResult, time);
			Clear();
			Push(text);
		}

		/// <summary>
		/// 유닛 상세 화면 표시 (Push)
		/// </summary>
		public void ShowUnitLook(UnitLookResult unitLook)
		{
			var text = _describeSystem.GetUnitLookText(unitLook);
			Push(text);
		}

		/// <summary>
		/// 인벤토리 화면 표시 (Push)
		/// </summary>
		public void ShowInventory()
		{
			var text = _describeSystem.GetInventoryText();
			Push(text);
		}

		/// <summary>
		/// 아이템 메뉴 표시 (Push)
		/// </summary>
		public void ShowItemMenu(int itemId, int count, string context)
		{
			var text = _describeSystem.GetItemMenuText(context, itemId, count);
			Push(text);
		}

		/// <summary>
		/// 결과 메시지 표시 (Push - 뒤로 가면 이전 화면 복귀)
		/// </summary>
		public void ShowResult(string message)
		{
			var text = $"[b]{message}[/b]\n\n[url=back]뒤로[/url]";
			Push(text);
		}

		// === 스택 조작 API ===

		/// <summary>
		/// 텍스트로 새 레이어 Push
		/// </summary>
		public void Push(string text)
		{
			_stack.Push(new ScreenLayer { Text = text });
			UpdateDisplay();
		}

		/// <summary>
		/// 최상위 레이어 Pop
		/// </summary>
		public void Pop()
		{
			_stack.Pop();
			UpdateDisplay();
		}

		/// <summary>
		/// 스택 전체 비우기
		/// </summary>
		public void Clear()
		{
			_stack.Clear();
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

			UpdateDisplay();
		}

		/// <summary>
		/// 스택이 비어있는지 확인
		/// </summary>
		public bool IsEmpty => _stack.Count == 0;

		// === JSON 저장/복원 ===

		/// <summary>
		/// 현재 상태를 JSON 데이터로 내보내기
		/// </summary>
		public UIStateJsonData ExportState()
		{
			var data = new UIStateJsonData();
			foreach (var layer in _stack.ToList())
			{
				data.ScreenStack.Add(ScreenLayerJsonData.FromScreenLayer(layer));
			}
			return data;
		}

		/// <summary>
		/// JSON 데이터에서 상태 복원
		/// </summary>
		public void ImportState(UIStateJsonData data)
		{
			var layers = new List<ScreenLayer>();
			foreach (var layerData in data.ScreenStack)
			{
				layers.Add(layerData.ToScreenLayer());
			}
			_stack.FromList(layers);
			UpdateDisplay();
		}

		/// <summary>
		/// 파일에서 상태 로드
		/// </summary>
		public void LoadFromFile(string filePath)
		{
			try
			{
				if (!File.Exists(filePath))
				{
					GD.PrintErr($"[TextUISystem] File not found: {filePath}");
					return;
				}

				var json = File.ReadAllText(filePath);
				var data = JsonSerializer.Deserialize<UIStateJsonData>(json);
				if (data != null)
				{
					ImportState(data);
				}
			}
			catch (Exception ex)
			{
				GD.PrintErr($"[TextUISystem] Failed to load from file: {ex.Message}");
			}
		}

		/// <summary>
		/// 파일에 상태 저장
		/// </summary>
		public void SaveToFile(string filePath)
		{
			try
			{
				var data = ExportState();
				var options = new JsonSerializerOptions { WriteIndented = true };
				var json = JsonSerializer.Serialize(data, options);
				File.WriteAllText(filePath, json);
			}
			catch (Exception ex)
			{
				GD.PrintErr($"[TextUISystem] Failed to save to file: {ex.Message}");
			}
		}

		/// <summary>
		/// Proc은 빈 구현 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
