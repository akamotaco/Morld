using ECS;
using Godot;
using System.Collections.Generic;
using System.Linq;

namespace SE
{
	/// <summary>
	/// 행동 로그 항목
	/// </summary>
	public class ActionLogEntry
	{
		public string Message { get; set; } = "";
		public bool IsRead { get; set; } = false;
		public bool WasDisplayed { get; set; } = false;

		public ActionLogEntry(string message)
		{
			Message = message;
		}
	}

	/// <summary>
	/// 행동 로그 시스템 (싱글톤처럼 사용)
	/// 게임 내 행동 로그를 관리하고 UI에 표시할 로그를 제공
	/// </summary>
	public class ActionLogSystem : ECS.System
	{
		private readonly List<ActionLogEntry> _actionLogs = new();
		private const int MaxLogLength = 50;

		/// <summary>
		/// UI 업데이트 요청 콜백 (TextUISystem에서 설정)
		/// </summary>
		public System.Action? OnLogAdded { get; set; }

		public ActionLogSystem()
		{
		}

		/// <summary>
		/// 행동 로그 추가
		/// </summary>
		public void AddLog(string message)
		{
			_actionLogs.Add(new ActionLogEntry(message));

			// MaxLogLength 초과 시 오래된 로그 삭제
			while (_actionLogs.Count > MaxLogLength)
			{
				_actionLogs.RemoveAt(0);
			}

			// UI 업데이트 요청
			OnLogAdded?.Invoke();
		}

		/// <summary>
		/// 출력용 로그 엔트리 반환 (읽지 않은 것만)
		/// </summary>
		public IReadOnlyList<ActionLogEntry> GetPrintableLogs()
		{
			var logs = _actionLogs
				.Where(e => !e.IsRead)
				.ToList();

			// 렌더링에 사용된 로그를 표시됨으로 마킹
			foreach (var log in logs)
				log.WasDisplayed = true;

			return logs;
		}

		/// <summary>
		/// 모든 로그를 읽음 처리
		/// </summary>
		public void MarkAllLogsAsRead()
		{
			foreach (var log in _actionLogs)
			{
				log.IsRead = true;
			}
		}

		/// <summary>
		/// 출력된 로그를 읽음 처리 (읽지 않은 것만)
		/// </summary>
		public void MarkPrintedLogsAsRead()
		{
			foreach (var log in _actionLogs.Where(e => !e.IsRead && e.WasDisplayed))
			{
				log.IsRead = true;
			}
		}

		/// <summary>
		/// 읽지 않은 로그 개수
		/// </summary>
		public int UnreadLogCount => _actionLogs.Count(e => !e.IsRead);

		/// <summary>
		/// 디버그용: 전체 로그 상태 출력
		/// </summary>
		public void DebugPrintLogs()
		{
#if DEBUG_LOG
			GD.Print($"[ActionLogs] Total: {_actionLogs.Count}, Unread: {UnreadLogCount}");
			foreach (var log in _actionLogs)
			{
				var readMark = log.IsRead ? "[R]" : "[U]";
				GD.Print($"  {readMark} {log.Message}");
			}
#endif
		}

		/// <summary>
		/// Proc은 비어있음 (호출 기반 시스템)
		/// </summary>
		protected override void Proc(int step, System.Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}
	}
}
