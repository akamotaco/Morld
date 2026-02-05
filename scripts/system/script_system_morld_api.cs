using SharpPy;
using Morld;

namespace SE
{
    /// <summary>
    /// ScriptSystem partial - morld 모듈 기본 API 등록
    ///
    /// 포함 API:
    /// - 플레이어 API: get_player_id
    /// - 인벤토리 API: give_item, remove_item, lost_item, get_inventory, has_item, get_unit_inventory, get_item_info
    /// - 유닛 API: get_unit_info
    /// - Prop API: set_prop, get_prop, clear_prop
    /// - 시나리오 API: get_scenario_path, get_scenario_data_path, get_scenario_python_path
    /// - 액션 로그 API: add_action_log, mark_all_logs_read
    /// - Action Text API: get_actions_list
    /// - Job API: insert_job_override, insert_job_merge, get_current_job, clear_jobs
    /// - 스크립트 함수 등록 API: register_script
    /// - Dialog API: dialog
    /// </summary>
    public partial class ScriptSystem
    {
        /// <summary>
        /// morld Python 모듈 등록 - 게임 데이터 조작 API
        /// </summary>
        private void RegisterMorldModule()
        {
            Godot.GD.Print("[ScriptSystem] Registering morld module...");

            try
            {
                // morld 모듈 생성
                var morldModule = new PyModule("morld", "<morld module>");

                // API 등록을 카테고리별 메서드로 분리
                RegisterPlayerAPI(morldModule);
                RegisterInventoryAPI(morldModule);
                RegisterUnitInfoAPI(morldModule);
                RegisterPropAPI(morldModule);
                RegisterScenarioAPI(morldModule);
                RegisterActionLogAPI(morldModule);
                RegisterJobAPI(morldModule);
                RegisterScriptAPI(morldModule);
                RegisterDialogAPI(morldModule);
                RegisterAnimlogAPI(morldModule);

                // sys.modules에 등록
                PyImportSystem.SetModule("morld", morldModule);

                Godot.GD.Print("[ScriptSystem] morld module registered successfully.");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] RegisterMorldModule error: {ex.Message}");
            }
        }

        /// <summary>
        /// 플레이어 API 등록
        /// </summary>
        private void RegisterPlayerAPI(PyModule morldModule)
        {
            morldModule.ModuleDict["get_player_id"] = new PyBuiltinFunction("get_player_id", args =>
            {
                var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
                if (_playerSystem == null)
                {
                    Godot.GD.PrintErr("[ScriptSystem] get_player_id: PlayerSystem is null");
                    return PyNone.Instance;
                }
                return new PyInt(_playerSystem.PlayerId);
            });

            // create_id() - 고유 인스턴스 ID 생성
            morldModule.ModuleDict["create_id"] = new PyBuiltinFunction("create_id", args =>
            {
                return new PyInt(IdGenerator.NextId());
            });

            // reset_id_generator() - ID 생성기 리셋
            morldModule.ModuleDict["reset_id_generator"] = new PyBuiltinFunction("reset_id_generator", args =>
            {
                int startId = args.Length >= 1 && args[0] is not PyNone ? args[0].ToInt() : 1;
                IdGenerator.Reset(startId);
                Godot.GD.Print($"[morld] reset_id_generator: reset to {startId}");
                return PyBool.True;
            });

            // queue_event(event_type, player_id, unit_ids) - 이벤트 핸들러 큐에 추가
            // 로맨스 중단 등 특수 상황에서 on_meet 이벤트를 수동으로 큐잉할 때 사용
            morldModule.ModuleDict["queue_event"] = new PyBuiltinFunction("queue_event", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("queue_event(event_type, player_id, unit_ids) requires 3 arguments");

                string eventType = args[0] is PyString pyStr ? pyStr.Value : args[0].ToString();
                int playerId = args[1].ToInt();

                // unit_ids는 리스트
                var unitIdsList = new System.Collections.Generic.List<int>();
                if (args[2] is PyList pyList)
                {
                    foreach (var item in pyList.Items)
                    {
                        unitIdsList.Add(item.ToInt());
                    }
                }
                var unitIds = unitIdsList.ToArray();

                var _eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;
                if (_eventSystem == null)
                {
                    Godot.GD.PrintErr("[morld] queue_event: EventSystem is null");
                    return PyBool.False;
                }

                _eventSystem.QueueEventHandlers(eventType, playerId, unitIds);
#if DEBUG_LOG
                Godot.GD.Print($"[morld] queue_event: type={eventType}, player={playerId}, units=[{string.Join(",", unitIds)}]");
#endif
                return PyBool.True;
            });
        }

        /// <summary>
        /// 인벤토리 API 등록
        /// </summary>
        private void RegisterInventoryAPI(PyModule morldModule)
        {
            morldModule.ModuleDict["give_item"] = new PyBuiltinFunction("give_item", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("give_item(unit_id, item_id, count=1) requires at least 2 arguments");

                int unitId = args[0].ToInt();
                int itemId = args[1].ToInt();
                int count = args.Length >= 3 ? args[2].ToInt() : 1;

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                _inventorySystem.AddItemToUnit(unitId, itemId, count);
                Godot.GD.Print($"[morld] give_item: unit={unitId}, item={itemId}, count={count}");
                return PyBool.True;
            });

            morldModule.ModuleDict["remove_item"] = new PyBuiltinFunction("remove_item", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("remove_item(unit_id, item_id, count=1) requires at least 2 arguments");

                int unitId = args[0].ToInt();
                int itemId = args[1].ToInt();
                int count = args.Length >= 3 ? args[2].ToInt() : 1;

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                bool success = _inventorySystem.RemoveItemFromUnit(unitId, itemId, count);
                Godot.GD.Print($"[morld] remove_item: unit={unitId}, item={itemId}, count={count}, success={success}");
                return PyBool.FromBool(success);
            });

            morldModule.ModuleDict["lost_item"] = new PyBuiltinFunction("lost_item", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("lost_item(unit_id, item_id, count=1) requires at least 2 arguments");

                int unitId = args[0].ToInt();
                int itemId = args[1].ToInt();
                int count = args.Length >= 3 ? args[2].ToInt() : 1;

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                bool success = _inventorySystem.RemoveItemFromUnit(unitId, itemId, count);
                Godot.GD.Print($"[morld] lost_item: unit={unitId}, item={itemId}, count={count}, success={success}");
                return PyBool.FromBool(success);
            });

            morldModule.ModuleDict["get_inventory"] = new PyBuiltinFunction("get_inventory", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_inventory(unit_id) requires 1 argument");

                int unitId = args[0].ToInt();

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                var inventory = _inventorySystem.GetUnitInventory(unitId);
                var pyDict = new PyDict();
                foreach (var kvp in inventory)
                {
                    pyDict.SetItem(new PyInt(kvp.Key), new PyInt(kvp.Value));
                }
                return pyDict;
            });

            morldModule.ModuleDict["has_item"] = new PyBuiltinFunction("has_item", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("has_item(unit_id, item_id, count=1) requires at least 2 arguments");

                int unitId = args[0].ToInt();
                int itemId = args[1].ToInt();
                int count = args.Length >= 3 ? args[2].ToInt() : 1;

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                return PyBool.FromBool(_inventorySystem.UnitHasItem(unitId, itemId, count));
            });

            morldModule.ModuleDict["get_unit_inventory"] = new PyBuiltinFunction("get_unit_inventory", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_unit_inventory(unit_id) requires 1 argument");

                int unitId = args[0].ToInt();

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                var inventory = _inventorySystem.GetUnitInventory(unitId);

                // PyDict로 변환 {item_id: count, ...}
                var result = new PyDict();
                foreach (var (itemId, count) in inventory)
                {
                    result.SetItem(new PyInt(itemId), new PyInt(count));
                }
                return result;
            });

            // get_item_info: 아이템 정보 조회
            morldModule.ModuleDict["get_item_info"] = new PyBuiltinFunction("get_item_info", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_item_info(item_id) requires 1 argument");

                int itemId = args[0].ToInt();

                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
                var item = _itemSystem?.FindItem(itemId);

                if (item == null)
                    return PyNone.Instance;

                var result = new PyDict();
                result.SetItem(new PyString("id"), new PyInt(item.Id));
                result.SetItem(new PyString("unique_id"), new PyString(item.UniqueId ?? ""));
                result.SetItem(new PyString("name"), new PyString(item.Name ?? ""));
                result.SetItem(new PyString("value"), new PyInt(item.Value));

                // passive_props
                var passiveProps = new PyDict();
                foreach (var kv in item.PassiveProps)
                    passiveProps.SetItem(new PyString(kv.Key), new PyInt(kv.Value));
                result.SetItem(new PyString("passive_props"), passiveProps);

                // equip_props
                var equipProps = new PyDict();
                foreach (var kv in item.EquipProps)
                    equipProps.SetItem(new PyString(kv.Key), new PyInt(kv.Value));
                result.SetItem(new PyString("equip_props"), equipProps);

                // action_props
                var actionProps = new PyDict();
                foreach (var kv in item.ActionProps)
                    actionProps.SetItem(new PyString(kv.Key), new PyInt(kv.Value));
                result.SetItem(new PyString("action_props"), actionProps);

                return result;
            });

            // find_items_with_passive: 특정 passive_prop을 가진 아이템 검색
            // 반환: [{id, unique_id, name, passive_props, equip_props}, ...]
            morldModule.ModuleDict["find_items_with_passive"] = new PyBuiltinFunction("find_items_with_passive", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("find_items_with_passive(unit_id, prop_name) requires 2 arguments");

                int unitId = args[0].ToInt();
                string propName = args[1].AsString();

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;

                var inventory = _inventorySystem.GetUnitInventory(unitId);
                var result = new PyList();

                foreach (var (itemId, count) in inventory)
                {
                    var item = _itemSystem?.FindItem(itemId);
                    if (item == null) continue;

                    // passive_props에서 해당 prop이 있는지 확인
                    if (item.PassiveProps.TryGetValue(propName, out int propValue) && propValue > 0)
                    {
                        var itemInfo = new PyDict();
                        itemInfo.SetItem(new PyString("id"), new PyInt(item.Id));
                        itemInfo.SetItem(new PyString("unique_id"), new PyString(item.UniqueId ?? ""));
                        itemInfo.SetItem(new PyString("name"), new PyString(item.Name ?? ""));
                        itemInfo.SetItem(new PyString("count"), new PyInt(count));

                        // passive_props
                        var passiveProps = new PyDict();
                        foreach (var kv in item.PassiveProps)
                            passiveProps.SetItem(new PyString(kv.Key), new PyInt(kv.Value));
                        itemInfo.SetItem(new PyString("passive_props"), passiveProps);

                        // equip_props
                        var equipProps = new PyDict();
                        foreach (var kv in item.EquipProps)
                            equipProps.SetItem(new PyString(kv.Key), new PyInt(kv.Value));
                        itemInfo.SetItem(new PyString("equip_props"), equipProps);

                        result.Append(itemInfo);
                    }
                }

                return result;
            });

            // get_item_id_by_unique: unique_id로 아이템 ID 조회
            morldModule.ModuleDict["get_item_id_by_unique"] = new PyBuiltinFunction("get_item_id_by_unique", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_item_id_by_unique(unique_id) requires 1 argument");

                string uniqueId = args[0].AsString();

                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
                var item = _itemSystem?.FindByUniqueId(uniqueId);

                if (item == null)
                    return PyNone.Instance;

                return new PyInt(item.Id);
            });

            // === 장착 관련 API ===

            // equip_item_internal(unit_id, item_id) - C# InventorySystem.EquipItem 호출
            morldModule.ModuleDict["equip_item_internal"] = new PyBuiltinFunction("equip_item_internal", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("equip_item_internal(unit_id, item_id) requires 2 arguments");

                int unitId = args[0].ToInt();
                int itemId = args[1].ToInt();

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                bool success = _inventorySystem.EquipItemOnUnit(unitId, itemId);
                Godot.GD.Print($"[morld] equip_item_internal: unit={unitId}, item={itemId}, success={success}");
                return PyBool.FromBool(success);
            });

            // unequip_item_internal(unit_id, item_id) - C# InventorySystem.UnequipItem 호출
            morldModule.ModuleDict["unequip_item_internal"] = new PyBuiltinFunction("unequip_item_internal", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("unequip_item_internal(unit_id, item_id) requires 2 arguments");

                int unitId = args[0].ToInt();
                int itemId = args[1].ToInt();

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                bool success = _inventorySystem.UnequipItemFromUnit(unitId, itemId);
                Godot.GD.Print($"[morld] unequip_item_internal: unit={unitId}, item={itemId}, success={success}");
                return PyBool.FromBool(success);
            });

            // is_equipped(unit_id, item_id) - 장착 여부 확인
            morldModule.ModuleDict["is_equipped"] = new PyBuiltinFunction("is_equipped", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("is_equipped(unit_id, item_id) requires 2 arguments");

                int unitId = args[0].ToInt();
                int itemId = args[1].ToInt();

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                bool equipped = _inventorySystem.IsEquippedOnUnit(unitId, itemId);
                return PyBool.FromBool(equipped);
            });

            // get_equipped_items(unit_id) - 장착 아이템 ID 리스트 반환
            morldModule.ModuleDict["get_equipped_items"] = new PyBuiltinFunction("get_equipped_items", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_equipped_items(unit_id) requires 1 argument");

                int unitId = args[0].ToInt();

                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                var equipped = _inventorySystem.GetUnitEquippedItems(unitId);

                var result = new PyList();
                foreach (var itemId in equipped)
                {
                    result.Append(new PyInt(itemId));
                }
                return result;
            });

            // get_actual_props(unit_id) - 장착 아이템의 EquipProps 포함한 전체 Props 반환
            morldModule.ModuleDict["get_actual_props"] = new PyBuiltinFunction("get_actual_props", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_actual_props(unit_id) requires 1 argument");

                int unitId = args[0].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;

                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return new PyDict();

                var inventory = _inventorySystem.GetUnitInventory(unitId);
                var equippedItems = _inventorySystem.GetUnitEquippedItems(unitId);
                var actualProps = unit.GetActualProps(_itemSystem, inventory, equippedItems);

                var result = new PyDict();
                foreach (var (key, value) in actualProps.Props)
                {
                    result.SetItem(new PyString(key), new PyInt(value));
                }
                return result;
            });
        }

        /// <summary>
        /// 유닛 정보 API 등록
        /// </summary>
        private void RegisterUnitInfoAPI(PyModule morldModule)
        {
            // get_location_info(region_id, location_id) - Location 정보 반환
            morldModule.ModuleDict["get_location_info"] = new PyBuiltinFunction("get_location_info", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("get_location_info(region_id, location_id) requires 2 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem?.GetTerrain();
                if (terrain == null)
                    return PyNone.Instance;

                var location = terrain.GetLocation(regionId, locationId);
                if (location == null)
                    return PyNone.Instance;

                var result = new PyDict();
                result.SetItem(new PyString("name"), new PyString(location.Name ?? ""));
                result.SetItem(new PyString("region_id"), new PyInt(location.RegionId));
                result.SetItem(new PyString("location_id"), new PyInt(location.LocalId));
                result.SetItem(new PyString("is_indoor"), PyBool.FromBool(location.IsIndoor));
                result.SetItem(new PyString("stay_duration"), new PyInt(location.StayDuration));

                // 날씨 정보 (실외일 때만 유효)
                var weather = location.CurrentWeather;
                if (weather != null)
                    result.SetItem(new PyString("weather"), new PyString(weather));
                else
                    result.SetItem(new PyString("weather"), PyNone.Instance);

                // 소유자 정보
                if (location.Owner != null)
                    result.SetItem(new PyString("owner"), new PyString(location.Owner));
                else
                    result.SetItem(new PyString("owner"), PyNone.Instance);

                // 바닥 오브젝트 ID
                if (location.GroundUnitId.HasValue)
                    result.SetItem(new PyString("ground_unit_id"), new PyInt(location.GroundUnitId.Value));
                else
                    result.SetItem(new PyString("ground_unit_id"), PyNone.Instance);

                return result;
            });

            morldModule.ModuleDict["get_unit_info"] = new PyBuiltinFunction("get_unit_info", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_unit_info(unit_id) requires 1 argument");

                // None 체크
                if (args[0] is PyNone)
                    return PyNone.Instance;

                int unitId = args[0].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return PyNone.Instance;

                // 유닛 정보를 PyDict로 반환
                var result = new PyDict();
                result.SetItem(new PyString("id"), new PyInt(unit.Id));
                result.SetItem(new PyString("name"), new PyString(unit.Name ?? ""));
                result.SetItem(new PyString("is_object"), PyBool.FromBool(unit.IsObject));

                // 현재 위치
                result.SetItem(new PyString("region_id"), new PyInt(unit.CurrentLocation.RegionId));
                result.SetItem(new PyString("location_id"), new PyInt(unit.CurrentLocation.LocalId));

                // 현재 Job 정보 (JobList 기반)
                var currentJob = unit.CurrentJob;
                if (currentJob != null)
                {
                    result.SetItem(new PyString("activity"), new PyString(currentJob.Name ?? ""));
                    result.SetItem(new PyString("schedule_name"), new PyString(currentJob.Name ?? ""));
                }
                else
                {
                    result.SetItem(new PyString("activity"), PyNone.Instance);
                    result.SetItem(new PyString("schedule_name"), PyNone.Instance);
                }

                // 이동 중인지 여부 (Pi-World: CurrentMovement가 있으면 이동 중)
                result.SetItem(new PyString("is_moving"), PyBool.FromBool(unit.IsMoving));

                // 목적지로 이동 중인지 여부 (논리적 상태)
                result.SetItem(new PyString("is_traveling"), PyBool.FromBool(unit.IsTraveling));

                // 이동 중인 경우 최종 목적지 정보 (CurrentJob에서 추출)
                if (currentJob != null && currentJob.Action == "move")
                {
                    result.SetItem(new PyString("dest_region_id"), new PyInt(currentJob.RegionId));
                    result.SetItem(new PyString("dest_location_id"), new PyInt(currentJob.LocationId));
                }
                else
                {
                    result.SetItem(new PyString("dest_region_id"), PyNone.Instance);
                    result.SetItem(new PyString("dest_location_id"), PyNone.Instance);
                }

                // Pi-World: 2D 위치 정보
                result.SetItem(new PyString("x"), new PyFloat(unit.PositionX));
                result.SetItem(new PyString("y"), new PyFloat(unit.PositionY));

                // Pi-World: Location 내 이동 중 여부
                bool isMoving2D = unit.CurrentMovement != null;
                result.SetItem(new PyString("is_moving_2d"), PyBool.FromBool(isMoving2D));

                if (unit.CurrentMovement != null)
                {
                    result.SetItem(new PyString("target_gate_id"),
                        unit.CurrentMovement.TargetGateId.HasValue
                            ? new PyInt(unit.CurrentMovement.TargetGateId.Value)
                            : PyNone.Instance);
                    result.SetItem(new PyString("movement_progress"), new PyFloat(unit.CurrentMovement.Progress));
                }
                else
                {
                    result.SetItem(new PyString("target_gate_id"), PyNone.Instance);
                    result.SetItem(new PyString("movement_progress"), PyNone.Instance);
                }

                return result;
            });

            // get_units_at_location(region_id, location_id) - Location에 있는 유닛 ID 목록 반환
            // 캐릭터만 반환 (IsObject=false), 이동 중인 유닛 제외
            morldModule.ModuleDict["get_units_at_location"] = new PyBuiltinFunction("get_units_at_location", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("get_units_at_location(region_id, location_id) requires 2 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var result = new PyList();
                foreach (var unit in _unitSystem.Units.Values)
                {
                    // 오브젝트는 제외 (캐릭터만)
                    if (unit.IsObject)
                        continue;

                    // 이동 중인 유닛 제외 (Location에 도착한 유닛만)
                    if (unit.IsMoving)
                        continue;

                    // 현재 위치가 일치하는지 확인
                    if (unit.CurrentLocation.RegionId == regionId &&
                        unit.CurrentLocation.LocalId == locationId)
                    {
                        result.Append(new PyInt(unit.Id));
                    }
                }
                return result;
            });

            // get_objects_at_location(region_id, location_id) - Location에 있는 오브젝트 ID 목록 반환
            // 오브젝트만 반환 (IsObject=true)
            morldModule.ModuleDict["get_objects_at_location"] = new PyBuiltinFunction("get_objects_at_location", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("get_objects_at_location(region_id, location_id) requires 2 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var result = new PyList();
                foreach (var unit in _unitSystem.Units.Values)
                {
                    // 오브젝트만 (캐릭터 제외)
                    if (!unit.IsObject)
                        continue;

                    // 현재 위치가 일치하는지 확인
                    if (unit.CurrentLocation.RegionId == regionId &&
                        unit.CurrentLocation.LocalId == locationId)
                    {
                        result.Append(new PyInt(unit.Id));
                    }
                }
                return result;
            });

            // get_all_unit_ids() - 모든 유닛 ID 목록 반환 (캐릭터만, 오브젝트 제외)
            morldModule.ModuleDict["get_all_unit_ids"] = new PyBuiltinFunction("get_all_unit_ids", args =>
            {
                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var result = new PyList();
                foreach (var unit in _unitSystem.Units.Values)
                {
                    // 오브젝트는 제외 (캐릭터만)
                    if (unit.IsObject)
                        continue;

                    result.Append(new PyInt(unit.Id));
                }
                return result;
            });

            // resolve_sleep_target(unit_id, pref_region, pref_location, owner_unique_id)
            // 수면 장소 탐색 API - 우선순위에 따라 침대/노숙 장소 결정
            // 반환: {"bed_object_id": int|None, "region_id": int, "location_id": int, "x": float, "rough": bool}
            morldModule.ModuleDict["resolve_sleep_target"] = new PyBuiltinFunction("resolve_sleep_target", args =>
            {
                if (args.Length < 4)
                    throw PyTypeError.Create("resolve_sleep_target(unit_id, pref_region, pref_location, owner_unique_id) requires 4 arguments");

                int unitId = args[0].ToInt();
                int prefRegion = args[1].ToInt();
                int prefLocation = args[2].ToInt();
                string ownerUniqueId = args[3].ToString();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem?.GetTerrain();

                var npc = _unitSystem.FindUnit(unitId);
                if (npc == null)
                    return PyNone.Instance;

                // can:sleep 체크 - NPC가 수면 능력이 있는지 확인
                bool npcCanSleep = false;
                foreach (var (prop, value) in npc.TraversalContext.Props.GetByType("can"))
                {
                    if (prop.Name == "sleep" && value > 0)
                    {
                        npcCanSleep = true;
                        break;
                    }
                }
                if (!npcCanSleep)
                    return PyNone.Instance;

                // 우선순위 1: pref_location에서 bed_owner가 일치하는 침대 + 빈 슬롯
                // 우선순위 2: pref_location에서 아무 빈 침대
                Unit bestOwnerBed = null;
                string bestOwnerSlot = null;
                Unit bestAnyBed = null;
                string bestAnySlot = null;

                foreach (var unit in _unitSystem.Units.Values)
                {
                    if (!unit.IsObject) continue;
                    if (unit.CurrentLocation.RegionId != prefRegion ||
                        unit.CurrentLocation.LocalId != prefLocation) continue;

                    // 수면 가능 오브젝트 식별: action:sleep prop
                    bool canSleep = false;
                    foreach (var (prop, value) in unit.TraversalContext.Props.GetByType("action"))
                    {
                        if (prop.Name == "sleep" && value > 0)
                        {
                            canSleep = true;
                            break;
                        }
                    }
                    if (!canSleep) continue;

                    // 빈 슬롯 찾기
                    string emptySlot = null;
                    foreach (var (prop, value) in unit.TraversalContext.Props.GetByType("seated_by"))
                    {
                        if (value == -1)
                        {
                            emptySlot = prop.Name;
                            break;
                        }
                    }
                    if (emptySlot == null) continue;

                    // bed_owner 체크
                    if (!string.IsNullOrEmpty(ownerUniqueId))
                    {
                        bool isOwnerBed = false;
                        foreach (var (prop, value) in unit.TraversalContext.Props.GetByType("bed_owner"))
                        {
                            if (prop.Name == ownerUniqueId && value > 0)
                            {
                                isOwnerBed = true;
                                break;
                            }
                        }

                        if (isOwnerBed && bestOwnerBed == null)
                        {
                            bestOwnerBed = unit;
                            bestOwnerSlot = emptySlot;
                        }
                    }

                    // 아무 빈 침대 (우선순위 2 후보)
                    if (bestAnyBed == null)
                    {
                        bestAnyBed = unit;
                        bestAnySlot = emptySlot;
                    }
                }

                // 결과 결정
                Unit selectedBed = bestOwnerBed ?? bestAnyBed;

                if (selectedBed != null)
                {
                    // 침대 발견
                    var result = new PyDict();
                    result.SetItem(new PyString("bed_object_id"), new PyInt(selectedBed.Id));
                    result.SetItem(new PyString("region_id"), new PyInt(prefRegion));
                    result.SetItem(new PyString("location_id"), new PyInt(prefLocation));
                    result.SetItem(new PyString("x"), new PyFloat(selectedBed.PositionX));
                    result.SetItem(new PyString("rough"), PyBool.FromBool(false));
                    return result;
                }

                // 우선순위 3: pref_location이 실내면 노숙
                var location = terrain?.GetLocation(prefRegion, prefLocation);
                if (location != null && location.IsIndoor)
                {
                    var result = new PyDict();
                    result.SetItem(new PyString("bed_object_id"), PyNone.Instance);
                    result.SetItem(new PyString("region_id"), new PyInt(prefRegion));
                    result.SetItem(new PyString("location_id"), new PyInt(prefLocation));
                    result.SetItem(new PyString("x"), new PyFloat(0));
                    result.SetItem(new PyString("rough"), PyBool.FromBool(true));
                    return result;
                }

                // 우선순위 4: 현재 위치에서 노숙
                var result4 = new PyDict();
                result4.SetItem(new PyString("bed_object_id"), PyNone.Instance);
                result4.SetItem(new PyString("region_id"), new PyInt(npc.CurrentLocation.RegionId));
                result4.SetItem(new PyString("location_id"), new PyInt(npc.CurrentLocation.LocalId));
                result4.SetItem(new PyString("x"), new PyFloat(npc.PositionX));
                result4.SetItem(new PyString("rough"), PyBool.FromBool(true));
                return result4;
            });
        }

        /// <summary>
        /// Prop API 등록
        ///
        /// 확장된 시그니처:
        /// - set_prop(unit_id, prop_name, value=1) - 유닛 지정
        /// - set_prop(prop_name, value=1) - 플레이어 (하위 호환)
        /// </summary>
        private void RegisterPropAPI(PyModule morldModule)
        {
            // set_prop: Prop 설정 ("타입:이름" 형식)
            // set_prop(unit_id, prop_name, value=1) 또는 set_prop(prop_name, value=1)
            morldModule.ModuleDict["set_prop"] = new PyBuiltinFunction("set_prop", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("set_prop(unit_id, prop_name, value=1) or set_prop(prop_name, value=1)");

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

                int unitId;
                string propName;
                int value;

                // 첫 번째 인자가 문자열이면 레거시 모드 (플레이어 대상)
                if (args[0] is PyString)
                {
                    unitId = _playerSystem.PlayerId;
                    propName = args[0].AsString();
                    value = args.Length >= 2 ? args[1].ToInt() : 1;
                }
                else
                {
                    // 새 모드: unit_id 지정
                    unitId = args[0].ToInt();
                    propName = args[1].AsString();
                    value = args.Length >= 3 ? args[2].ToInt() : 1;
                }

                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return PyBool.False;

                unit.TraversalContext.SetProp(propName, value);
                Godot.GD.Print($"[morld] set_prop: unit={unitId}, {propName} = {value}");
                return new PyInt(value);
            });

            // get_prop: Prop 값 조회 ("타입:이름" 형식)
            // get_prop(unit_id, prop_name) 또는 get_prop(prop_name)
            morldModule.ModuleDict["get_prop"] = new PyBuiltinFunction("get_prop", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_prop(unit_id, prop_name) or get_prop(prop_name)");

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

                int unitId;
                string propName;

                // 첫 번째 인자가 문자열이면 레거시 모드 (플레이어 대상)
                if (args[0] is PyString)
                {
                    unitId = _playerSystem.PlayerId;
                    propName = args[0].AsString();
                }
                else
                {
                    unitId = args[0].ToInt();
                    propName = args[1].AsString();
                }

                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return new PyInt(0);

                int value = unit.TraversalContext.GetProp(propName);
                return new PyInt(value);
            });

            // clear_prop: Prop 제거 ("타입:이름" 형식)
            // clear_prop(unit_id, prop_name) 또는 clear_prop(prop_name)
            morldModule.ModuleDict["clear_prop"] = new PyBuiltinFunction("clear_prop", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("clear_prop(unit_id, prop_name) or clear_prop(prop_name)");

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

                int unitId;
                string propName;

                // 첫 번째 인자가 문자열이면 레거시 모드 (플레이어 대상)
                if (args[0] is PyString)
                {
                    unitId = _playerSystem.PlayerId;
                    propName = args[0].AsString();
                }
                else
                {
                    unitId = args[0].ToInt();
                    propName = args[1].AsString();
                }

                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return PyBool.False;

                unit.TraversalContext.SetProp(propName, 0);
                Godot.GD.Print($"[morld] clear_prop: unit={unitId}, {propName}");
                return PyBool.True;
            });

            // get_unit_props: 유닛의 모든 Props 반환
            morldModule.ModuleDict["get_unit_props"] = new PyBuiltinFunction("get_unit_props", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_unit_props(unit_id) requires 1 argument");

                int unitId = args[0].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return new PyDict();

                var result = new PyDict();
                foreach (var (key, value) in unit.TraversalContext.Props)
                {
                    result.SetItem(new PyString(key), new PyInt(value));
                }
                return result;
            });

            // modify_prop: Prop 값 상대적 변경 (delta 더하기)
            // modify_prop(unit_id, prop_name, delta)
            morldModule.ModuleDict["modify_prop"] = new PyBuiltinFunction("modify_prop", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("modify_prop(unit_id, prop_name, delta) requires 3 arguments");

                int unitId = args[0].ToInt();
                string propName = args[1].AsString();
                int delta = args[2].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return PyBool.False;

                // 현재 값 조회 (없으면 0)
                int currentValue = unit.TraversalContext.GetProp(propName);
                int newValue = currentValue + delta;

                unit.TraversalContext.SetProp(propName, newValue);
                Godot.GD.Print($"[morld] modify_prop: unit={unitId}, {propName} = {currentValue} + {delta} = {newValue}");
                return new PyInt(newValue);
            });
        }

        /// <summary>
        /// 시나리오 API 등록
        /// </summary>
        private void RegisterScenarioAPI(PyModule morldModule)
        {
            morldModule.ModuleDict["get_scenario_path"] = new PyBuiltinFunction("get_scenario_path", args =>
            {
                // 시나리오 기본 경로 반환 (res://scenarios/scenario01/)
                return new PyString(_scenarioPath);
            });

            morldModule.ModuleDict["get_scenario_data_path"] = new PyBuiltinFunction("get_scenario_data_path", args =>
            {
                // 시나리오 데이터 폴더 경로 반환 (res://scenarios/scenario01/data/)
                return new PyString(_scenarioPath + "data/");
            });

            morldModule.ModuleDict["get_scenario_python_path"] = new PyBuiltinFunction("get_scenario_python_path", args =>
            {
                // 시나리오 Python 폴더 경로 반환 (res://scenarios/scenario01/python/)
                return new PyString(ScenarioPythonPath);
            });
        }

        /// <summary>
        /// 액션 로그 API 등록
        /// </summary>
        private void RegisterActionLogAPI(PyModule morldModule)
        {
            morldModule.ModuleDict["add_action_log"] = new PyBuiltinFunction("add_action_log", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("add_action_log(message) requires 1 argument");

                string message = args[0].AsString();

                var _actionLogSystem = this._hub.GetSystem("actionLogSystem") as ActionLogSystem;

                _actionLogSystem?.AddLog(message);
                Godot.GD.Print($"[morld] add_action_log: {message}");
                return PyBool.True;
            });

            morldModule.ModuleDict["mark_all_logs_read"] = new PyBuiltinFunction("mark_all_logs_read", args =>
            {
                var _actionLogSystem = this._hub.GetSystem("actionLogSystem") as ActionLogSystem;
                _actionLogSystem?.MarkAllLogsAsRead();
                return PyBool.True;
            });

            // get_actions_list() - 현재 상황의 행동 옵션 BBCode 리스트 반환
            morldModule.ModuleDict["get_actions_list"] = new PyBuiltinFunction("get_actions_list", args =>
            {
                var actionSystem = this._hub.GetSystem("actionSystem") as ActionSystem;
                var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

                // PlayerSystem에서 현재 LookResult 가져오기
                var lookResult = _playerSystem.Look();
                if (lookResult == null)
                    return new PyList();

                // ActionSystem에서 행동 아이템 리스트 가져오기
                var actionItems = actionSystem.GetActionItems(lookResult);

                // PyList로 변환
                var pyList = new PyList();
                foreach (var item in actionItems)
                {
                    pyList.Append(new PyString(item));
                }
                return pyList;
            });

            // get_movement_info() - 이동 UI용 구조화된 경로 데이터 반환
            morldModule.ModuleDict["get_movement_info"] = new PyBuiltinFunction("get_movement_info", args =>
            {
                var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
                var worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var terrain = worldSystem?.GetTerrain();

                var player = _playerSystem?.FindPlayerUnit();
                if (player == null || terrain == null)
                    return PyNone.Instance;

                var lookResult = _playerSystem.Look();
                if (lookResult == null)
                    return PyNone.Instance;

                // 현재 Location 정보
                var location = terrain.GetLocation(player.CurrentLocation);
                if (location == null)
                    return PyNone.Instance;

                var result = new PyDict();
                result.SetItem(new PyString("geometry"), new PyString(location.Geometry.ToString().ToLower()));
                result.SetItem(new PyString("length"), new PyFloat(location.Length));
                result.SetItem(new PyString("player_x"), new PyFloat(player.PositionX));

                // 앉기/눕기 상태
                var seatedOnProp = player.TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
                bool isSeated = seatedOnProp.Prop.IsValid;
                result.SetItem(new PyString("seated"), isSeated ? PyBool.True : PyBool.False);

                // 경로 목록
                var routesList = new PyList();
                foreach (var route in lookResult.Routes)
                {
                    var routeDict = new PyDict();
                    routeDict.SetItem(new PyString("name"), new PyString(route.LocationName));
                    routeDict.SetItem(new PyString("region_name"), new PyString(route.RegionName));
                    routeDict.SetItem(new PyString("region_id"), new PyInt(route.Destination.RegionId));
                    routeDict.SetItem(new PyString("local_id"), new PyInt(route.Destination.LocalId));
                    routeDict.SetItem(new PyString("travel_time"), new PyInt(route.TravelTime));
                    routeDict.SetItem(new PyString("gate_x"), new PyFloat(route.GateX));
                    routeDict.SetItem(new PyString("is_region_gate"), route.IsRegionGate ? PyBool.True : PyBool.False);
                    routeDict.SetItem(new PyString("is_blocked"), route.IsBlocked ? PyBool.True : PyBool.False);
                    routeDict.SetItem(new PyString("is_hidden"), route.IsHidden ? PyBool.True : PyBool.False);
                    routesList.Append(routeDict);
                }
                result.SetItem(new PyString("routes"), routesList);

                return result;
            });
        }

        /// <summary>
        /// Job API 등록
        /// </summary>
        private void RegisterJobAPI(PyModule morldModule)
        {
            // insert_job_override(unit_id, name, action, duration, region_id=0, location_id=0, target_id=None)
            morldModule.ModuleDict["insert_job_override"] = new PyBuiltinFunction("insert_job_override", args =>
            {
                if (args.Length < 4)
                    throw PyTypeError.Create("insert_job_override(unit_id, name, action, duration, region_id=0, location_id=0, target_id=None) requires at least 4 arguments");

                int unitId = args[0].ToInt();
                string name = args[1].AsString();
                string action = args[2].AsString();
                int duration = args[3].ToInt();
                int regionId = args.Length >= 5 ? args[4].ToInt() : 0;
                int locationId = args.Length >= 6 ? args[5].ToInt() : 0;
                int? targetId = args.Length >= 7 && args[6] is not PyNone ? args[6].ToInt() : null;

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return PyBool.False;

                var job = new Morld.Job
                {
                    Name = name,
                    Action = action,
                    Duration = duration,
                    RegionId = regionId,
                    LocationId = locationId,
                    TargetId = targetId,
                    StartOffset = 0
                };

                unit.InsertJobOverride(job);
                Godot.GD.Print($"[morld] insert_job_override: unit={unitId}, {job}");
                return PyBool.True;
            });

            // insert_job_merge(unit_id, name, action, duration, start_offset=0, region_id=0, location_id=0, target_id=None)
            morldModule.ModuleDict["insert_job_merge"] = new PyBuiltinFunction("insert_job_merge", args =>
            {
                if (args.Length < 4)
                    throw PyTypeError.Create("insert_job_merge(unit_id, name, action, duration, start_offset=0, region_id=0, location_id=0, target_id=None) requires at least 4 arguments");

                int unitId = args[0].ToInt();
                string name = args[1].AsString();
                string action = args[2].AsString();
                int duration = args[3].ToInt();
                int startOffset = args.Length >= 5 ? args[4].ToInt() : 0;
                int regionId = args.Length >= 6 ? args[5].ToInt() : 0;
                int locationId = args.Length >= 7 ? args[6].ToInt() : 0;
                int? targetId = args.Length >= 8 && args[7] is not PyNone ? args[7].ToInt() : null;

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return PyBool.False;

                var job = new Morld.Job
                {
                    Name = name,
                    Action = action,
                    Duration = duration,
                    RegionId = regionId,
                    LocationId = locationId,
                    TargetId = targetId,
                    StartOffset = startOffset
                };

                unit.InsertJobMerge(job);
                Godot.GD.Print($"[morld] insert_job_merge: unit={unitId}, offset={startOffset}, {job}");
                return PyBool.True;
            });

            // get_current_job(unit_id) - 현재 Job 정보 반환
            morldModule.ModuleDict["get_current_job"] = new PyBuiltinFunction("get_current_job", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_current_job(unit_id) requires 1 argument");

                int unitId = args[0].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return PyNone.Instance;

                var job = unit.CurrentJob;
                if (job == null)
                    return PyNone.Instance;

                var result = new PyDict();
                result.SetItem(new PyString("name"), new PyString(job.Name ?? ""));
                result.SetItem(new PyString("action"), new PyString(job.Action ?? "stay"));
                result.SetItem(new PyString("duration"), new PyInt(job.Duration));
                result.SetItem(new PyString("region_id"), new PyInt(job.RegionId));
                result.SetItem(new PyString("location_id"), new PyInt(job.LocationId));
                if (job.TargetId.HasValue)
                    result.SetItem(new PyString("target_id"), new PyInt(job.TargetId.Value));
                else
                    result.SetItem(new PyString("target_id"), PyNone.Instance);

                return result;
            });

            // clear_jobs(unit_id) - JobList 초기화
            morldModule.ModuleDict["clear_jobs"] = new PyBuiltinFunction("clear_jobs", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("clear_jobs(unit_id) requires 1 argument");

                int unitId = args[0].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var unit = _unitSystem.FindUnit(unitId);
                if (unit == null)
                    return PyBool.False;

                unit.JobList.Clear();
                Godot.GD.Print($"[morld] clear_jobs: unit={unitId}");
                return PyBool.True;
            });
        }

        /// <summary>
        /// 스크립트 함수 등록 API
        /// </summary>
        private void RegisterScriptAPI(PyModule morldModule)
        {
            // morld.register_script(func) - Python 함수를 전역 스코프에 등록
            // done_callback 등에서 함수 이름만으로 호출 가능하게 함
            // CPython 3.12: 전역 스코프 = sys.modules['__main__'].__dict__
            morldModule.ModuleDict["register_script"] = new PyBuiltinFunction("register_script", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("register_script(func) requires 1 argument");

                var func = args[0];
                if (func is not PyFunction pyFunc)
                    throw PyTypeError.Create("register_script() argument must be a function");

                var funcName = pyFunc.Name;

                // CPython 3.12: Python/ceval.c - globals() == sys.modules['__main__'].__dict__
                if (PyImportSystem.TryGetModule("__main__", out var mainModule))
                {
                    mainModule.ModuleDict[funcName] = func;
                    Godot.GD.Print($"[morld] register_script: {funcName}");
                }
                return func;  // 데코레이터로 사용할 수 있도록 함수 반환
            });
        }

        /// <summary>
        /// Dialog API 등록
        /// </summary>
        private void RegisterDialogAPI(PyModule morldModule)
        {
            // morld.dialog(text_or_pages, autofill="next", proc=None, result=None, time_flows=False)
            // Python에서 yield로 사용:
            //   yield morld.dialog("텍스트")  # 단일 페이지, 기본 autofill
            //   yield morld.dialog(["페이지1", "페이지2"])  # 멀티 페이지
            //   yield morld.dialog(["페이지1", "페이지2"], autofill="book")  # 이전/다음 왕복
            //   result = yield morld.dialog("텍스트", autofill="off", proc=my_proc, result=state)
            //   yield morld.dialog("지도 내용", time_flows=True)  # 시간이 계속 흐르는 다이얼로그
            //
            // autofill 타입:
            //   "next" (기본값) - [다음] 버튼만, 마지막 페이지는 [종료]
            //   "book" - [이전][다음] 왕복 가능
            //   "off" - 자동 버튼 없음 (커스텀 UI)
            //
            // time_flows 파라미터:
            //   False (기본값) - 다이얼로그 표시 중 자동 시간 흐름 정지 (대화, 이벤트 등)
            //   True - 다이얼로그 표시 중에도 자동 시간 흐름 계속 (지도 보기 등)
            //
            // URL 패턴:
            //   @next - 다음 페이지로 이동 (autofill 전용)
            //   @prev - 이전 페이지로 이동 (book 전용)
            //   @finish - 다이얼로그 종료, result 파라미터 값 반환
            //   @proc:값 - proc 콜백 호출, 텍스트 업데이트
            //   @proc_finish:값 - proc 콜백 호출 후 종료
            //   @ret:값 - 다이얼로그 종료, 해당 값 반환 (레거시 호환)
            morldModule.ModuleDict["dialog"] = new PyBuiltinFunction("dialog", (args, kwargs) =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("dialog(text_or_pages, autofill='next', proc=None, result=None, time_flows=False) requires at least 1 argument");

                var firstArg = args[0];

                // kwargs에서 파라미터 추출
                DialogAutofill autofill = DialogAutofill.Next;
                PyObject procCallback = null;
                PyObject resultObject = null;
                bool timeFlows = false;

                if (kwargs != null)
                {
                    // autofill 파라미터
                    var autofillKey = new PyString("autofill");
                    var autofillValue = kwargs.Get(autofillKey);
                    if (autofillValue != null && !(autofillValue is PyNone))
                    {
                        string autofillStr = autofillValue.AsString().ToLower();
                        autofill = autofillStr switch
                        {
                            "next" => DialogAutofill.Next,
                            "book" => DialogAutofill.Book,
                            "off" => DialogAutofill.Off,
                            _ => DialogAutofill.Next
                        };
                    }

                    // proc 파라미터
                    var procKey = new PyString("proc");
                    var procValue = kwargs.Get(procKey);
                    if (procValue != null && !(procValue is PyNone))
                    {
                        procCallback = procValue;
                    }

                    // result 파라미터
                    var resultKey = new PyString("result");
                    var resultValue = kwargs.Get(resultKey);
                    if (resultValue != null && !(resultValue is PyNone))
                    {
                        resultObject = resultValue;
                    }

                    // time_flows 파라미터 - 자동 시간 흐름 허용 여부
                    var timeFlowsKey = new PyString("time_flows");
                    var timeFlowsValue = kwargs.Get(timeFlowsKey);
                    if (timeFlowsValue != null && !(timeFlowsValue is PyNone))
                    {
                        timeFlows = timeFlowsValue.IsTrue();
                    }
                }

                // 리스트인 경우 멀티페이지
                if (firstArg is PyList pageList)
                {
                    var pages = new System.Collections.Generic.List<string>();
                    foreach (var item in pageList.Items)
                    {
                        pages.Add(item.AsString());
                    }
                    return new PyDialogRequest(pages, null, procCallback, autofill, resultObject, timeFlows);
                }

                // 단일 텍스트
                string text = firstArg.AsString();
                return new PyDialogRequest(text, null, procCallback, autofill, resultObject, timeFlows);
            });

            // morld.pop_to_situation() - Situation Focus까지 스택 Pop (스킨십 비정상 종료 등)
            // 사용: morld.pop_to_situation()
            // 반환: True (항상 성공)
            morldModule.ModuleDict["pop_to_situation"] = new PyBuiltinFunction("pop_to_situation", args =>
            {
                var _textUiSystem = this._hub.GetSystem("textUISystem") as TextUISystem;
                if (_textUiSystem != null)
                {
                    _textUiSystem.PopToSituation();
                    Godot.GD.Print("[morld] pop_to_situation: popped to situation focus");
                }
                return PyBool.True;
            });
        }

        /// <summary>
        /// Animlog API 등록
        /// </summary>
        private void RegisterAnimlogAPI(PyModule morldModule)
        {
            // morld.animlog(steps, scale=1.0, mode="normal")
            // Python에서 yield로 사용:
            //   anim = ui.Animlog()
            //   anim.text("텍스트")
            //   yield anim.play(mode="lock")
            //
            // mode 타입:
            //   "normal" (기본값) - header/footer 보이고 입력 가능
            //   "lock" - header/footer 가림 (레터박스), 집중 연출용
            //   "block" - header/footer 보이지만 입력 불가, 전투용
            morldModule.ModuleDict["animlog"] = new PyBuiltinFunction("animlog", (args, kwargs) =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("animlog(steps, scale=1.0, mode='normal') requires at least 1 argument");

                var stepsList = args[0] as PyList;
                if (stepsList == null)
                    throw PyTypeError.Create("animlog: first argument must be a list of steps");

                // kwargs에서 파라미터 추출
                float scale = 1.0f;
                AnimlogMode mode = AnimlogMode.Normal;

                if (kwargs != null)
                {
                    // scale 파라미터
                    var scaleKey = new PyString("scale");
                    var scaleValue = kwargs.Get(scaleKey);
                    if (scaleValue != null && !(scaleValue is PyNone))
                    {
                        scale = PyObjectToFloat(scaleValue, 1.0f);
                    }

                    // mode 파라미터
                    var modeKey = new PyString("mode");
                    var modeValue = kwargs.Get(modeKey);
                    if (modeValue != null && !(modeValue is PyNone))
                    {
                        string modeStr = modeValue.AsString().ToLower();
                        mode = modeStr switch
                        {
                            "normal" => AnimlogMode.Normal,
                            "lock" => AnimlogMode.Lock,
                            "block" => AnimlogMode.Block,
                            _ => AnimlogMode.Normal
                        };
                    }
                }

                // 스텝 파싱
                var steps = ParseAnimlogSteps(stepsList);
                return new PyAnimlogRequest(steps, scale, mode);
            });
        }

        /// <summary>
        /// Python 스텝 리스트를 AnimlogStep 리스트로 변환
        /// </summary>
        private System.Collections.Generic.List<AnimlogStep> ParseAnimlogSteps(PyList stepsList)
        {
            var steps = new System.Collections.Generic.List<AnimlogStep>();

            foreach (var item in stepsList.Items)
            {
                if (item is not PyDict dict) continue;

                var step = new AnimlogStep();

                // type
                var typeObj = dict.Get(new PyString("type"));
                step.Type = typeObj is PyString typeStr ? typeStr.Value : "text";

                switch (step.Type)
                {
                    case "text":
                        // content
                        var contentObj = dict.Get(new PyString("content"));
                        step.Content = contentObj is PyString contentStr ? contentStr.Value : "";

                        // delay (optional)
                        var delayObj = dict.Get(new PyString("delay"));
                        if (delayObj != null && !(delayObj is PyNone))
                        {
                            step.Delay = PyObjectToFloat(delayObj, 0f);
                        }

                        // speed
                        var speedObj = dict.Get(new PyString("speed"));
                        if (speedObj != null && !(speedObj is PyNone))
                        {
                            step.Speed = PyObjectToFloat(speedObj, 50f);
                        }

                        // append
                        var appendObj = dict.Get(new PyString("append"));
                        step.Append = appendObj == null || appendObj is PyNone || appendObj.IsTrue();
                        break;

                    case "wait":
                        // duration
                        var durationObj = dict.Get(new PyString("duration"));
                        if (durationObj != null && !(durationObj is PyNone))
                        {
                            step.Duration = PyObjectToFloat(durationObj, 0f);
                        }
                        break;

                    case "callback":
                        // func
                        step.CallbackFunc = dict.Get(new PyString("func"));
                        step.CallbackArgs = dict.Get(new PyString("args"));
                        step.CallbackKwargs = dict.Get(new PyString("kwargs"));
                        break;

                    case "clear":
                        // 추가 속성 없음
                        break;
                }

                steps.Add(step);
            }

            return steps;
        }

        /// <summary>
        /// PyObject를 float로 변환 (PyFloat 또는 PyInt 지원)
        /// </summary>
        private static float PyObjectToFloat(PyObject obj, float defaultValue = 0f)
        {
            if (obj is PyFloat pf)
                return (float)pf.Value;
            if (obj is PyInt pi)
                return (float)pi.Value;
            return defaultValue;
        }
    }
}
