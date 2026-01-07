#define DEBUG_LOG

using ECS;
using Godot;
using Morld;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace SE
{
	/// <summary>
	/// 인벤토리 변경 이벤트 타입
	/// </summary>
	public enum InventoryEventType
	{
		ItemAdded,      // 아이템 추가
		ItemRemoved,    // 아이템 제거
		ItemTransferred, // 아이템 이동
		ItemEquipped,   // 장착
		ItemUnequipped, // 장착 해제
		ItemLost        // 아이템 잃음 (사용/소모 등으로 인한 삭제)
	}

	/// <summary>
	/// 인벤토리 변경 이벤트 데이터
	/// </summary>
	public class InventoryEvent
	{
		public InventoryEventType Type { get; set; }
		public int ItemId { get; set; }
		public int Count { get; set; }
		public string? FromOwner { get; set; }
		public string? ToOwner { get; set; }
	}

	/// <summary>
	/// 인벤토리 시스템 (플러그인)
	/// - 유닛/위치/아이템의 보관 기능 제공
	/// - IDataProvider: 자체 데이터 저장/로드
	/// - IActionProvider: "소지품 확인" 행동 제공
	///
	/// 키 형식:
	/// - "unit:{id}" - 유닛 (캐릭터/오브젝트)
	/// - "location:{regionId}:{localId}" - 위치 (바닥)
	/// - "item:{id}" - 아이템 (가방 등)
	/// </summary>
	public class InventorySystem : ECS.System, IDataProvider, IActionProvider
	{
		// === IDataProvider ===
		public string DataId => "inventory";

		// === IActionProvider ===
		public string ProviderId => "inventory";

		/// <summary>
		/// 통합 인벤토리 (ownerKey → {itemId → count})
		/// ownerKey: "unit:0", "location:0:1", "item:5" 등
		/// </summary>
		private readonly Dictionary<string, Dictionary<int, int>> _inventories = new();

		/// <summary>
		/// 장착 아이템 (ownerKey → [itemId, ...])
		/// 주로 유닛에서 사용
		/// </summary>
		private readonly Dictionary<string, List<int>> _equippedItems = new();

		/// <summary>
		/// 인벤토리 가시성 (ownerKey → isVisible)
		/// true면 아이템이 외부에서 보임 (열린 상자, 바닥 등)
		/// </summary>
		private readonly Dictionary<string, bool> _visibility = new();

		/// <summary>
		/// 인벤토리 변경 이벤트 콜백
		/// </summary>
		public Action<InventoryEvent>? OnInventoryChanged { get; set; }

		public InventorySystem()
		{
		}

		// ===== 키 생성 헬퍼 =====

		/// <summary>
		/// 유닛 키 생성 (unitId를 문자열로 변환)
		/// </summary>
		public static string UnitKey(int unitId) => unitId.ToString();

		// ===== 범용 인벤토리 조회 API =====

		/// <summary>
		/// 인벤토리 가져오기 (읽기 전용)
		/// </summary>
		public IReadOnlyDictionary<int, int> GetInventory(string ownerKey)
		{
			return _inventories.TryGetValue(ownerKey, out var inv)
				? inv
				: new Dictionary<int, int>();
		}

		/// <summary>
		/// 인벤토리가 있는지 확인
		/// </summary>
		public bool HasInventory(string ownerKey)
		{
			return _inventories.ContainsKey(ownerKey);
		}

		/// <summary>
		/// 장착 아이템 목록 가져오기 (읽기 전용)
		/// </summary>
		public IReadOnlyList<int> GetEquippedItems(string ownerKey)
		{
			return _equippedItems.TryGetValue(ownerKey, out var items)
				? items
				: new List<int>();
		}

		// ===== 유닛 전용 편의 메서드 =====

		/// <summary>
		/// 유닛의 인벤토리 가져오기
		/// </summary>
		public IReadOnlyDictionary<int, int> GetUnitInventory(int unitId)
			=> GetInventory(UnitKey(unitId));

		/// <summary>
		/// 유닛이 인벤토리를 가지고 있는지 확인
		/// </summary>
		public bool HasUnitInventory(int unitId)
			=> HasInventory(UnitKey(unitId));

		/// <summary>
		/// 유닛의 장착 아이템 목록
		/// </summary>
		public IReadOnlyList<int> GetUnitEquippedItems(int unitId)
			=> GetEquippedItems(UnitKey(unitId));

		// ===== 범용 인벤토리 조작 API =====

		/// <summary>
		/// 인벤토리 생성 (이미 있으면 무시)
		/// </summary>
		public void CreateInventory(string ownerKey)
		{
			if (!_inventories.ContainsKey(ownerKey))
			{
				_inventories[ownerKey] = new Dictionary<int, int>();
			}
		}

		/// <summary>
		/// 인벤토리에 아이템 추가
		/// </summary>
		public bool AddItem(string ownerKey, int itemId, int count = 1)
		{
			if (count <= 0) return false;

			if (!_inventories.TryGetValue(ownerKey, out var inv))
			{
				inv = new Dictionary<int, int>();
				_inventories[ownerKey] = inv;
			}

			if (!inv.ContainsKey(itemId))
				inv[itemId] = 0;
			inv[itemId] += count;

			// 이벤트 발생
			OnInventoryChanged.Invoke(new InventoryEvent
			{
				Type = InventoryEventType.ItemAdded,
				ItemId = itemId,
				Count = count,
				ToOwner = ownerKey
			});

			return true;
		}

		/// <summary>
		/// 인벤토리에서 아이템 제거
		/// </summary>
		public bool RemoveItem(string ownerKey, int itemId, int count = 1)
		{
			if (count <= 0) return false;

			if (!_inventories.TryGetValue(ownerKey, out var inv))
				return false;

			if (!inv.TryGetValue(itemId, out int available) || available < count)
				return false;

			inv[itemId] -= count;
			if (inv[itemId] <= 0)
				inv.Remove(itemId);

			// 이벤트 발생
			OnInventoryChanged.Invoke(new InventoryEvent
			{
				Type = InventoryEventType.ItemRemoved,
				ItemId = itemId,
				Count = count,
				FromOwner = ownerKey
			});

			return true;
		}

		/// <summary>
		/// 아이템 잃음 처리 (사용/소모로 인한 삭제)
		/// RemoveItem과 동일하지만 ItemLost 이벤트 발생
		/// </summary>
		public bool LostItem(string ownerKey, int itemId, int count = 1)
		{
			if (count <= 0) return false;

			if (!_inventories.TryGetValue(ownerKey, out var inv))
				return false;

			if (!inv.TryGetValue(itemId, out int available) || available < count)
				return false;

			inv[itemId] -= count;
			if (inv[itemId] <= 0)
				inv.Remove(itemId);

			// ItemLost 이벤트 발생 (액션 로그에 사용)
			OnInventoryChanged.Invoke(new InventoryEvent
			{
				Type = InventoryEventType.ItemLost,
				ItemId = itemId,
				Count = count,
				FromOwner = ownerKey
			});

			return true;
		}

		/// <summary>
		/// 특정 아이템을 가지고 있는지 확인
		/// </summary>
		public bool HasItem(string ownerKey, int itemId, int count = 1)
		{
			if (!_inventories.TryGetValue(ownerKey, out var inv))
				return false;

			return inv.TryGetValue(itemId, out int available) && available >= count;
		}

		/// <summary>
		/// 인벤토리 간 아이템 이동 (내부용 - 이벤트 없이)
		/// </summary>
		private bool TransferItemInternal(string fromKey, string toKey, int itemId, int count = 1)
		{
			if (count <= 0) return false;

			if (!_inventories.TryGetValue(fromKey, out var fromInv))
				return false;

			if (!fromInv.TryGetValue(itemId, out int available) || available < count)
				return false;

			// 제거
			fromInv[itemId] -= count;
			if (fromInv[itemId] <= 0)
				fromInv.Remove(itemId);

			// 추가
			if (!_inventories.TryGetValue(toKey, out var toInv))
			{
				toInv = new Dictionary<int, int>();
				_inventories[toKey] = toInv;
			}
			if (!toInv.ContainsKey(itemId))
				toInv[itemId] = 0;
			toInv[itemId] += count;

			return true;
		}

		/// <summary>
		/// 인벤토리 간 아이템 이동
		/// </summary>
		public bool TransferItem(string fromKey, string toKey, int itemId, int count = 1)
		{
			if (!TransferItemInternal(fromKey, toKey, itemId, count))
				return false;

			// 이벤트 발생
			OnInventoryChanged.Invoke(new InventoryEvent
			{
				Type = InventoryEventType.ItemTransferred,
				ItemId = itemId,
				Count = count,
				FromOwner = fromKey,
				ToOwner = toKey
			});

			return true;
		}

		// ===== 유닛 전용 조작 편의 메서드 =====

		/// <summary>
		/// 유닛에게 인벤토리 생성
		/// </summary>
		public void CreateUnitInventory(int unitId)
			=> CreateInventory(UnitKey(unitId));

		/// <summary>
		/// 유닛 인벤토리에 아이템 추가
		/// </summary>
		public bool AddItemToUnit(int unitId, int itemId, int count = 1)
			=> AddItem(UnitKey(unitId), itemId, count);

		/// <summary>
		/// 유닛 인벤토리에서 아이템 제거
		/// </summary>
		public bool RemoveItemFromUnit(int unitId, int itemId, int count = 1)
			=> RemoveItem(UnitKey(unitId), itemId, count);

		/// <summary>
		/// 유닛 인벤토리에서 아이템 잃음 처리 (사용/소모)
		/// </summary>
		public bool LostItemFromUnit(int unitId, int itemId, int count = 1)
			=> LostItem(UnitKey(unitId), itemId, count);

		/// <summary>
		/// 유닛이 특정 아이템을 가지고 있는지 확인
		/// </summary>
		public bool UnitHasItem(int unitId, int itemId, int count = 1)
			=> HasItem(UnitKey(unitId), itemId, count);

		/// <summary>
		/// 유닛 간 아이템 이동
		/// </summary>
		public bool TransferBetweenUnits(int fromUnitId, int toUnitId, int itemId, int count = 1)
			=> TransferItem(UnitKey(fromUnitId), UnitKey(toUnitId), itemId, count);

		// ===== 가시성 API =====

		/// <summary>
		/// 인벤토리 가시성 설정
		/// </summary>
		public void SetVisible(string ownerKey, bool isVisible)
		{
			_visibility[ownerKey] = isVisible;
		}

		/// <summary>
		/// 인벤토리가 외부에서 보이는지 확인
		/// </summary>
		public bool IsVisible(string ownerKey)
		{
			return _visibility.TryGetValue(ownerKey, out var visible) && visible;
		}

		/// <summary>
		/// 유닛 인벤토리가 외부에서 보이는지 확인
		/// </summary>
		public bool IsUnitInventoryVisible(int unitId)
			=> IsVisible(UnitKey(unitId));

		/// <summary>
		/// 유닛 인벤토리 가시성 설정
		/// </summary>
		public void SetUnitInventoryVisible(int unitId, bool isVisible)
			=> SetVisible(UnitKey(unitId), isVisible);

		// ===== 장착 API =====

		/// <summary>
		/// 아이템 장착
		/// </summary>
		public bool EquipItem(string ownerKey, int itemId)
		{
			if (!HasItem(ownerKey, itemId))
				return false;

			if (!_equippedItems.TryGetValue(ownerKey, out var equipped))
			{
				equipped = new List<int>();
				_equippedItems[ownerKey] = equipped;
			}

			if (!equipped.Contains(itemId))
			{
				equipped.Add(itemId);

				// 이벤트 발생
				OnInventoryChanged.Invoke(new InventoryEvent
				{
					Type = InventoryEventType.ItemEquipped,
					ItemId = itemId,
					Count = 1,
					ToOwner = ownerKey
				});
			}

			return true;
		}

		/// <summary>
		/// 아이템 장착 해제
		/// </summary>
		public bool UnequipItem(string ownerKey, int itemId)
		{
			if (!_equippedItems.TryGetValue(ownerKey, out var equipped))
				return false;

			if (equipped.Remove(itemId))
			{
				// 이벤트 발생
				OnInventoryChanged.Invoke(new InventoryEvent
				{
					Type = InventoryEventType.ItemUnequipped,
					ItemId = itemId,
					Count = 1,
					FromOwner = ownerKey
				});
				return true;
			}

			return false;
		}

		/// <summary>
		/// 아이템이 장착되어 있는지 확인
		/// </summary>
		public bool IsEquipped(string ownerKey, int itemId)
		{
			if (!_equippedItems.TryGetValue(ownerKey, out var equipped))
				return false;

			return equipped.Contains(itemId);
		}

		// ===== 유닛 장착 편의 메서드 =====

		public bool EquipItemOnUnit(int unitId, int itemId)
			=> EquipItem(UnitKey(unitId), itemId);

		public bool UnequipItemFromUnit(int unitId, int itemId)
			=> UnequipItem(UnitKey(unitId), itemId);

		public bool IsEquippedOnUnit(int unitId, int itemId)
			=> IsEquipped(UnitKey(unitId), itemId);

		// ===== IActionProvider 구현 =====

		/// <summary>
		/// 유닛에게 제공할 액션 목록
		/// </summary>
		public List<ProvidedAction> GetActionsFor(Unit unit)
		{
			var actions = new List<ProvidedAction>();

			// 인벤토리가 있는 유닛에게만 "소지품 확인" 제공
			if (HasUnitInventory(unit.Id))
			{
				actions.Add(new ProvidedAction
				{
					Type = "simple",
					Name = "소지품 확인",
					Action = "inventory"
				});
			}

			return actions;
		}

		// ===== IDataProvider 구현 =====

		/// <summary>
		/// 데이터 저장
		/// </summary>
		public void SaveData(string basePath)
		{
			var data = new InventoryDataJson
			{
				Inventories = new Dictionary<string, Dictionary<int, int>>(),
				EquippedItems = new Dictionary<string, List<int>>(),
				Visibility = new Dictionary<string, bool>()
			};

			// 인벤토리 복사 (빈 것 제외)
			foreach (var (key, inv) in _inventories)
			{
				if (inv.Count > 0)
					data.Inventories[key] = new Dictionary<int, int>(inv);
			}

			// 장착 아이템 복사 (빈 것 제외)
			foreach (var (key, items) in _equippedItems)
			{
				if (items.Count > 0)
					data.EquippedItems[key] = new List<int>(items);
			}

			// 가시성 복사 (true인 것만)
			foreach (var (key, visible) in _visibility)
			{
				if (visible)
					data.Visibility[key] = true;
			}

			var options = new JsonSerializerOptions
			{
				WriteIndented = true,
				PropertyNamingPolicy = JsonNamingPolicy.CamelCase
			};

			var json = JsonSerializer.Serialize(data, options);
			var path = $"{basePath}{DataId}_data.json";

			using var file = Godot.FileAccess.Open(path, Godot.FileAccess.ModeFlags.Write);
			if (file != null)
			{
				file.StoreString(json);
#if DEBUG_LOG
				GD.Print($"[InventorySystem] 저장됨: {path}");
#endif
			}
			else
			{
				GD.PrintErr($"[InventorySystem] 저장 실패: {path}");
			}
		}

		/// <summary>
		/// 데이터 로드
		/// </summary>
		public bool LoadData(string basePath)
		{
			var path = $"{basePath}{DataId}_data.json";

			if (!Godot.FileAccess.FileExists(path))
			{
#if DEBUG_LOG
				GD.Print($"[InventorySystem] 파일 없음, 빈 상태로 시작: {path}");
#endif
				return false;
			}

			using var file = Godot.FileAccess.Open(path, Godot.FileAccess.ModeFlags.Read);
			if (file == null)
			{
				GD.PrintErr($"[InventorySystem] 파일 열기 실패: {path}");
				return false;
			}

			var json = file.GetAsText();
			var options = new JsonSerializerOptions
			{
				PropertyNamingPolicy = JsonNamingPolicy.CamelCase
			};

			try
			{
				var data = JsonSerializer.Deserialize<InventoryDataJson>(json, options);
				if (data == null)
					return false;

				ClearData();

				// 인벤토리 로드
				if (data.Inventories != null)
				{
					foreach (var (key, inv) in data.Inventories)
					{
						_inventories[key] = new Dictionary<int, int>(inv);
					}
				}

				// 장착 아이템 로드
				if (data.EquippedItems != null)
				{
					foreach (var (key, items) in data.EquippedItems)
					{
						_equippedItems[key] = new List<int>(items);
					}
				}

				// 가시성 로드
				if (data.Visibility != null)
				{
					foreach (var (key, visible) in data.Visibility)
					{
						_visibility[key] = visible;
					}
				}

#if DEBUG_LOG
				GD.Print($"[InventorySystem] 로드됨: 인벤토리 {_inventories.Count}개, 장착 {_equippedItems.Count}개, 가시성 {_visibility.Count}개");
#endif
				return true;
			}
			catch (Exception ex)
			{
				GD.PrintErr($"[InventorySystem] JSON 파싱 실패: {ex.Message}");
				return false;
			}
		}

		/// <summary>
		/// 데이터 초기화
		/// </summary>
		public void ClearData()
		{
			_inventories.Clear();
			_equippedItems.Clear();
			_visibility.Clear();
		}

		/// <summary>
		/// DescribeSystem에 ActionProvider 등록
		/// </summary>
		public void RegisterToDescribeSystem()
		{
			var describeSystem = _hub.GetSystem("describeSystem") as DescribeSystem;
			describeSystem.ActionRegistry.Register(this);

#if DEBUG_LOG
			GD.Print("[InventorySystem] 액션 프로바이더 등록됨");
#endif
		}

		/// <summary>
		/// 시스템 종료 시 프로바이더 등록 해제
		/// </summary>
		public override void Destroy()
		{
			var describeSystem = _hub.GetSystem("describeSystem") as DescribeSystem;
			describeSystem.ActionRegistry.Unregister(this);

#if DEBUG_LOG
			GD.Print("[InventorySystem] 액션 프로바이더 해제됨");
#endif

			base.Destroy();
		}

		protected override void Proc(int step, Span<Component[]> allComponents)
		{
			// 호출 기반이므로 Proc에서 할 일 없음
		}

		/// <summary>
		/// 디버그 출력
		/// </summary>
		public void DebugPrint()
		{
#if DEBUG_LOG
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
			GD.Print("[InventorySystem] 인벤토리 현황");
			GD.Print($"  총 인벤토리: {_inventories.Count}개");
			foreach (var (key, inv) in _inventories)
			{
				var items = string.Join(", ", inv.Select(kv => $"아이템{kv.Key}x{kv.Value}"));
				GD.Print($"    {key}: {items}");
			}
			if (_equippedItems.Count > 0)
			{
				GD.Print($"  장착 정보: {_equippedItems.Count}개");
				foreach (var (key, items) in _equippedItems)
				{
					var itemStr = string.Join(", ", items.Select(id => $"아이템{id}"));
					GD.Print($"    {key}: {itemStr}");
				}
			}
			GD.Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
#endif
		}
	}

	/// <summary>
	/// 인벤토리 데이터 JSON 포맷
	/// </summary>
	internal class InventoryDataJson
	{
		/// <summary>
		/// 통합 인벤토리 (ownerKey → {itemId → count})
		/// 키 형식: "unit:0", "location:0:1", "item:5"
		/// </summary>
		[JsonPropertyName("inventories")]
		public Dictionary<string, Dictionary<int, int>>? Inventories { get; set; }

		/// <summary>
		/// 장착 아이템 (ownerKey → [itemId, ...])
		/// </summary>
		[JsonPropertyName("equippedItems")]
		public Dictionary<string, List<int>>? EquippedItems { get; set; }

		/// <summary>
		/// 인벤토리 가시성 (ownerKey → isVisible)
		/// true면 아이템이 외부에서 보임
		/// </summary>
		[JsonPropertyName("visibility")]
		public Dictionary<string, bool>? Visibility { get; set; }
	}
}
