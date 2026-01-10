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
                var inventory = _inventorySystem.GetUnitInventory(unitId);
                if (inventory.TryGetValue(itemId, out int owned))
                {
                    return PyBool.FromBool(owned >= count);
                }
                return PyBool.False;
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
        }

        /// <summary>
        /// 유닛 정보 API 등록
        /// </summary>
        private void RegisterUnitInfoAPI(PyModule morldModule)
        {
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

                // 이동 중인지 여부
                result.SetItem(new PyString("is_moving"), PyBool.FromBool(unit.IsMoving));

                return result;
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

                var _textUISystem = this._hub.GetSystem("textUISystem") as TextUISystem;

                _textUISystem.AddActionLog(message);
                Godot.GD.Print($"[morld] add_action_log: {message}");
                return PyBool.True;
            });

            morldModule.ModuleDict["mark_all_logs_read"] = new PyBuiltinFunction("mark_all_logs_read", args =>
            {
                var _textUISystem = this._hub.GetSystem("textUISystem") as TextUISystem;
                _textUISystem?.MarkAllLogsAsRead();
                return PyBool.True;
            });

            // get_actions_list() - 현재 상황의 행동 옵션 BBCode 리스트 반환
            morldModule.ModuleDict["get_actions_list"] = new PyBuiltinFunction("get_actions_list", args =>
            {
                var describeSystem = this._hub.GetSystem("describeSystem") as DescribeSystem;
                var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

                // PlayerSystem에서 현재 LookResult 가져오기
                var lookResult = _playerSystem.Look();
                if (lookResult == null)
                    return new PyList();

                // DescribeSystem에서 행동 아이템 리스트 가져오기
                var actionItems = describeSystem.GetActionItems(lookResult);

                // PyList로 변환
                var pyList = new PyList();
                foreach (var item in actionItems)
                {
                    pyList.Append(new PyString(item));
                }
                return pyList;
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
            // morld.dialog(text_or_pages, autofill="next", proc=None, result=None)
            // Python에서 yield로 사용:
            //   yield morld.dialog("텍스트")  # 단일 페이지, 기본 autofill
            //   yield morld.dialog(["페이지1", "페이지2"])  # 멀티 페이지
            //   yield morld.dialog(["페이지1", "페이지2"], autofill="book")  # 이전/다음 왕복
            //   result = yield morld.dialog("텍스트", autofill="off", proc=my_proc, result=state)
            //
            // autofill 타입:
            //   "next" (기본값) - [다음] 버튼만, 마지막 페이지는 [종료]
            //   "book" - [이전][다음] 왕복 가능
            //   "scroll" - 텍스트 누적 + [다음]
            //   "off" - 자동 버튼 없음 (커스텀 UI)
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
                    throw PyTypeError.Create("dialog(text_or_pages, autofill='next', proc=None, result=None) requires at least 1 argument");

                var firstArg = args[0];

                // kwargs에서 파라미터 추출
                DialogAutofill autofill = DialogAutofill.Next;
                PyObject procCallback = null;
                PyObject resultObject = null;

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
                            "scroll" => DialogAutofill.Scroll,
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
                }

                // 리스트인 경우 멀티페이지
                if (firstArg is PyList pageList)
                {
                    var pages = new System.Collections.Generic.List<string>();
                    foreach (var item in pageList.Items)
                    {
                        pages.Add(item.AsString());
                    }
                    return new PyDialogRequest(pages, null, procCallback, autofill, resultObject);
                }

                // 단일 텍스트
                string text = firstArg.AsString();
                return new PyDialogRequest(text, null, procCallback, autofill, resultObject);
            });
        }
    }
}
