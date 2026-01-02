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

		public InventorySystem()
		{
		}

		// ===== 키 생성 헬퍼 =====

		/// <summary>
		/// 유닛 키 생성
		/// </summary>
		public static string UnitKey(int unitId) => $"unit:{unitId}";

		/// <summary>
		/// 위치 키 생성
		/// </summary>
		public static string LocationKey(int regionId, int localId) => $"location:{regionId}:{localId}";

		/// <summary>
		/// 아이템 키 생성 (가방 등 컨테이너 아이템)
		/// </summary>
		public static string ItemKey(int itemId) => $"item:{itemId}";

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

		// ===== 위치 전용 편의 메서드 =====

		/// <summary>
		/// 위치의 바닥 아이템 가져오기
		/// </summary>
		public IReadOnlyDictionary<int, int> GetGroundItems(int regionId, int localId)
			=> GetInventory(LocationKey(regionId, localId));

		/// <summary>
		/// 위치에 바닥 아이템이 있는지 확인
		/// </summary>
		public bool HasGroundItems(int regionId, int localId)
		{
			var inv = GetInventory(LocationKey(regionId, localId));
			return inv.Count > 0;
		}

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
		/// 인벤토리 간 아이템 이동
		/// </summary>
		public bool TransferItem(string fromKey, string toKey, int itemId, int count = 1)
		{
			if (!RemoveItem(fromKey, itemId, count))
				return false;

			AddItem(toKey, itemId, count);
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
		/// 유닛이 특정 아이템을 가지고 있는지 확인
		/// </summary>
		public bool UnitHasItem(int unitId, int itemId, int count = 1)
			=> HasItem(UnitKey(unitId), itemId, count);

		/// <summary>
		/// 유닛 간 아이템 이동
		/// </summary>
		public bool TransferBetweenUnits(int fromUnitId, int toUnitId, int itemId, int count = 1)
			=> TransferItem(UnitKey(fromUnitId), UnitKey(toUnitId), itemId, count);

		// ===== 바닥 아이템 조작 편의 메서드 =====

		/// <summary>
		/// 바닥에 아이템 놓기
		/// </summary>
		public bool DropToGround(int regionId, int localId, int itemId, int count = 1)
			=> AddItem(LocationKey(regionId, localId), itemId, count);

		/// <summary>
		/// 바닥에서 아이템 제거
		/// </summary>
		public bool PickupFromGround(int regionId, int localId, int itemId, int count = 1)
			=> RemoveItem(LocationKey(regionId, localId), itemId, count);

		/// <summary>
		/// 유닛이 바닥에서 아이템 줍기
		/// </summary>
		public bool PickupItem(int unitId, int regionId, int localId, int itemId, int count = 1)
			=> TransferItem(LocationKey(regionId, localId), UnitKey(unitId), itemId, count);

		/// <summary>
		/// 유닛이 아이템을 바닥에 버리기
		/// </summary>
		public bool DropItem(int unitId, int regionId, int localId, int itemId, int count = 1)
			=> TransferItem(UnitKey(unitId), LocationKey(regionId, localId), itemId, count);

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
				equipped.Add(itemId);

			return true;
		}

		/// <summary>
		/// 아이템 장착 해제
		/// </summary>
		public bool UnequipItem(string ownerKey, int itemId)
		{
			if (!_equippedItems.TryGetValue(ownerKey, out var equipped))
				return false;

			return equipped.Remove(itemId);
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
				EquippedItems = new Dictionary<string, List<int>>()
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

			var options = new JsonSerializerOptions
			{
				WriteIndented = true,
				PropertyNamingPolicy = JsonNamingPolicy.CamelCase
			};

			var json = JsonSerializer.Serialize(data, options);
			var path = $"{basePath}{DataId}_data.json";

			using var file = FileAccess.Open(path, FileAccess.ModeFlags.Write);
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

			if (!FileAccess.FileExists(path))
			{
#if DEBUG_LOG
				GD.Print($"[InventorySystem] 파일 없음, 빈 상태로 시작: {path}");
#endif
				return false;
			}

			using var file = FileAccess.Open(path, FileAccess.ModeFlags.Read);
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

#if DEBUG_LOG
				GD.Print($"[InventorySystem] 로드됨: 인벤토리 {_inventories.Count}개, 장착 {_equippedItems.Count}개");
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
		}

		/// <summary>
		/// DescribeSystem에 ActionProvider 등록
		/// </summary>
		public void RegisterToDescribeSystem()
		{
			var describeSystem = _hub?.FindSystem("describeSystem") as DescribeSystem;
			describeSystem?.ActionRegistry.Register(this);

#if DEBUG_LOG
			GD.Print("[InventorySystem] 액션 프로바이더 등록됨");
#endif
		}

		/// <summary>
		/// 시스템 종료 시 프로바이더 등록 해제
		/// </summary>
		public override void Destroy()
		{
			var describeSystem = _hub?.FindSystem("describeSystem") as DescribeSystem;
			describeSystem?.ActionRegistry.Unregister(this);

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
	}
}
