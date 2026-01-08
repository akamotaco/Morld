using System;
using System.Collections.Generic;
using Godot;

namespace Morld;

/// <summary>
/// 포커스 스택
/// </summary>
public class FocusStack
{
	private readonly Stack<Focus> _layers = new();
	private int _maxDepth = 10;

	/// <summary>
	/// 최대 스택 깊이 (기본값 10, 1 이상)
	/// </summary>
	public int MaxDepth
	{
		get => _maxDepth;
		set => _maxDepth = value > 0 ? value : 10;
	}

	/// <summary>
	/// 현재 활성 포커스 (스택 최상위)
	/// </summary>
	public Focus? Current => _layers.Count > 0 ? _layers.Peek() : null;

	/// <summary>
	/// 스택 크기
	/// </summary>
	public int Count => _layers.Count;

	/// <summary>
	/// 새 포커스 추가
	/// </summary>
	/// <exception cref="InvalidOperationException">MaxDepth 초과 시</exception>
	public void Push(Focus focus)
	{
		if (_layers.Count >= _maxDepth)
		{
			throw new InvalidOperationException($"FocusStack exceeded maximum depth ({_maxDepth})");
		}
		var before = _layers.Count;
		_layers.Push(focus);
		GD.Print($"[FocusStack] {before} -> {_layers.Count} (push {focus.Type})");
	}

	/// <summary>
	/// 최상위 포커스 제거
	/// </summary>
	public void Pop()
	{
		if (_layers.Count == 0)
		{
			return;
		}
		if (_layers.Count == 1)
		{
			GD.PrintErr("[FocusStack] Warning: Pop called on stack with only 1 layer. This indicates a content or logic bug.");
		}
		var before = _layers.Count;
		var popped = _layers.Pop();
		GD.Print($"[FocusStack] {before} -> {_layers.Count} (pop {popped.Type})");
	}

	/// <summary>
	/// 스택 전체 비우기
	/// </summary>
	public void Clear()
	{
		_layers.Clear();
	}

	/// <summary>
	/// JSON 직렬화용 리스트 반환 (스택 순서: 바닥→최상위)
	/// </summary>
	public List<Focus> ToList()
	{
		var list = new List<Focus>(_layers);
		list.Reverse();
		return list;
	}

	/// <summary>
	/// JSON 역직렬화용 리스트에서 복원 (리스트 순서: 바닥→최상위)
	/// </summary>
	public void FromList(List<Focus> layers)
	{
		_layers.Clear();
		foreach (var layer in layers)
		{
			_layers.Push(layer);
		}
	}

	/// <summary>
	/// 스택에서 가장 가까운 Unit Focus의 TargetUnitId를 찾아 반환 (현재 포커스 제외)
	/// 넣기/가져오기 대상 유닛 ID를 찾는 데 사용
	/// </summary>
	/// <returns>찾은 TargetUnitId, 없으면 null</returns>
	public int? FindTargetUnitId()
	{
		var list = ToList(); // 바닥→최상위 순서
		// 최상위(마지막)는 현재 포커스이므로 제외하고 역순 탐색
		for (int i = list.Count - 2; i >= 0; i--)
		{
			if (list[i].Type == FocusType.Unit && list[i].TargetUnitId.HasValue)
			{
				return list[i].TargetUnitId;
			}
		}
		return null;
	}
}
