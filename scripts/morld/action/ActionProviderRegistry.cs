using System.Collections.Generic;
using Godot;

namespace Morld;

/// <summary>
/// 액션 프로바이더 레지스트리
/// 여러 시스템에서 제공하는 액션을 통합 관리
/// </summary>
public class ActionProviderRegistry
{
	private readonly List<IActionProvider> _providers = new();

	/// <summary>
	/// 액션 프로바이더 등록
	/// </summary>
	public void Register(IActionProvider provider)
	{
		if (_providers.Exists(p => p.ProviderId == provider.ProviderId))
		{
			GD.PrintErr($"[ActionProviderRegistry] Provider already registered: {provider.ProviderId}");
			return;
		}

		_providers.Add(provider);
#if DEBUG_LOG
		GD.Print($"[ActionProviderRegistry] Registered: {provider.ProviderId}");
#endif
	}

	/// <summary>
	/// 액션 프로바이더 등록 해제
	/// </summary>
	public void Unregister(string providerId)
	{
		var removed = _providers.RemoveAll(p => p.ProviderId == providerId);
#if DEBUG_LOG
		if (removed > 0)
			GD.Print($"[ActionProviderRegistry] Unregistered: {providerId}");
#endif
	}

	/// <summary>
	/// 액션 프로바이더 등록 해제 (인스턴스)
	/// </summary>
	public void Unregister(IActionProvider provider)
	{
		Unregister(provider.ProviderId);
	}

	/// <summary>
	/// 해당 유닛에게 제공 가능한 모든 액션 수집
	/// </summary>
	public List<ProvidedAction> GetAllActionsFor(Unit unit)
	{
		var allActions = new List<ProvidedAction>();

		foreach (var provider in _providers)
		{
			var actions = provider.GetActionsFor(unit);
			if (actions != null && actions.Count > 0)
			{
				allActions.AddRange(actions);
			}
		}

		return allActions;
	}

	/// <summary>
	/// 등록된 프로바이더 수
	/// </summary>
	public int Count => _providers.Count;

	/// <summary>
	/// 프로바이더 존재 여부 확인
	/// </summary>
	public bool HasProvider(string providerId)
	{
		return _providers.Exists(p => p.ProviderId == providerId);
	}
}
