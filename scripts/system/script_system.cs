using ECS;
using SharpPy;

namespace SE
{
    /// <summary>
    /// Python 스크립트 실행을 담당하는 시스템
    /// sharpPy를 통해 Python 코드 실행
    /// </summary>
    public class ScriptSystem : ECS.System
    {
        private IntegratedPythonInterpreter _interpreter;

        // 게임 시스템 참조 (morld 모듈에서 사용)
        private InventorySystem _inventorySystem;
        private PlayerSystem _playerSystem;
        private UnitSystem _unitSystem;
        private TextUISystem _textUISystem;

        // 시나리오 경로
        private string _scenarioPath = "";
        public string ScenarioPath => _scenarioPath;
        public string ScenarioPythonPath => _scenarioPath + "python/";

        public ScriptSystem()
        {
            _interpreter = new IntegratedPythonInterpreter();

            // 기본 Godot res:// 경로를 sys.path에 추가
            AddGodotPathsToSysPath();
        }

        /// <summary>
        /// 시나리오 경로 설정 및 sys.path에 추가
        /// </summary>
        public void SetScenarioPath(string scenarioPath)
        {
            _scenarioPath = scenarioPath;
            Godot.GD.Print($"[ScriptSystem] Scenario path set to: {scenarioPath}");

            // 시나리오 Python 폴더를 sys.path에 추가
            AddScenarioPathToSysPath();
        }

        /// <summary>
        /// 시나리오 Python 폴더를 sys.path에 추가
        /// </summary>
        private void AddScenarioPathToSysPath()
        {
            if (string.IsNullOrEmpty(_scenarioPath)) return;

            try
            {
                var sysModule = PyImportSystem.Import("sys");
                if (sysModule.ModuleDict.TryGetValue("path", out PyObject pathObj) && pathObj is PyList pathList)
                {
                    // 시나리오 루트 경로 추가 (entities 등 다른 폴더 접근용)
                    pathList.Insert(0, new PyString(_scenarioPath));
                    Godot.GD.Print($"[ScriptSystem] Added scenario root path to sys.path: {_scenarioPath}");

                    // 시나리오 Python 경로를 맨 앞에 추가 (최우선)
                    pathList.Insert(0, new PyString(ScenarioPythonPath));
                    Godot.GD.Print($"[ScriptSystem] Added scenario Python path to sys.path: {ScenarioPythonPath}");
                }
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] Failed to add scenario path to sys.path: {ex.Message}");
            }
        }

        /// <summary>
        /// Godot 환경용 기본 경로를 sys.path에 추가 (sharpPy Lib만)
        /// 시나리오별 Python 경로는 SetScenarioPath에서 추가됨
        /// </summary>
        private void AddGodotPathsToSysPath()
        {
            try
            {
                // sys 모듈 가져오기
                var sysModule = PyImportSystem.Import("sys");
                if (sysModule.ModuleDict.TryGetValue("path", out PyObject pathObj) && pathObj is PyList pathList)
                {
                    // sharpPy Lib 경로만 추가 (Python 표준 라이브러리)
                    pathList.Insert(0, new PyString("res://util/sharpPy/Lib"));
                    Godot.GD.Print("[ScriptSystem] Added sharpPy Lib to sys.path");
                }
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] Failed to add Godot paths to sys.path: {ex.Message}");
            }
        }

        // 추가 시스템 참조 (데이터 조작용)
        private WorldSystem _worldSystem;
        private ItemSystem _itemSystem;

        /// <summary>
        /// 게임 시스템 참조 설정 및 morld 모듈 등록
        /// </summary>
        public void SetSystemReferences(InventorySystem inventorySystem, PlayerSystem playerSystem, UnitSystem unitSystem = null, TextUISystem textUISystem = null)
        {
            _inventorySystem = inventorySystem;
            _playerSystem = playerSystem;
            _unitSystem = unitSystem;
            _textUISystem = textUISystem;

            RegisterMorldModule();
        }

        /// <summary>
        /// 데이터 시스템 참조 설정 (Python에서 데이터 조작용)
        /// </summary>
        public void SetDataSystemReferences(WorldSystem worldSystem, UnitSystem unitSystem, ItemSystem itemSystem, InventorySystem inventorySystem)
        {
            _worldSystem = worldSystem;
            _unitSystem = unitSystem;
            _itemSystem = itemSystem;
            _inventorySystem = inventorySystem;

            // morld 모듈에 데이터 조작 API 추가
            RegisterDataManipulationAPI();
        }

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

                // === 플레이어 API ===
                morldModule.ModuleDict["get_player_id"] = new PyBuiltinFunction("get_player_id", args =>
                {
                    if (_playerSystem == null) return new PyInt(-1);
                    return new PyInt(_playerSystem.PlayerId);
                });

                // === 인벤토리 API ===
                morldModule.ModuleDict["give_item"] = new PyBuiltinFunction("give_item", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("give_item(unit_id, item_id, count=1) requires at least 2 arguments");

                    int unitId = args[0].ToInt();
                    int itemId = args[1].ToInt();
                    int count = args.Length >= 3 ? args[2].ToInt() : 1;

                    if (_inventorySystem != null)
                    {
                        _inventorySystem.AddItemToUnit(unitId, itemId, count);
                        Godot.GD.Print($"[morld] give_item: unit={unitId}, item={itemId}, count={count}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["remove_item"] = new PyBuiltinFunction("remove_item", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("remove_item(unit_id, item_id, count=1) requires at least 2 arguments");

                    int unitId = args[0].ToInt();
                    int itemId = args[1].ToInt();
                    int count = args.Length >= 3 ? args[2].ToInt() : 1;

                    if (_inventorySystem != null)
                    {
                        bool success = _inventorySystem.RemoveItemFromUnit(unitId, itemId, count);
                        Godot.GD.Print($"[morld] remove_item: unit={unitId}, item={itemId}, count={count}, success={success}");
                        return PyBool.FromBool(success);
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["lost_item"] = new PyBuiltinFunction("lost_item", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("lost_item(unit_id, item_id, count=1) requires at least 2 arguments");

                    int unitId = args[0].ToInt();
                    int itemId = args[1].ToInt();
                    int count = args.Length >= 3 ? args[2].ToInt() : 1;

                    if (_inventorySystem != null)
                    {
                        bool success = _inventorySystem.LostItemFromUnit(unitId, itemId, count);
                        Godot.GD.Print($"[morld] lost_item: unit={unitId}, item={itemId}, count={count}, success={success}");
                        return PyBool.FromBool(success);
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["get_inventory"] = new PyBuiltinFunction("get_inventory", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_inventory(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    if (_inventorySystem != null)
                    {
                        var inventory = _inventorySystem.GetUnitInventory(unitId);
                        var pyDict = new PyDict();
                        foreach (var kvp in inventory)
                        {
                            pyDict.SetItem(new PyInt(kvp.Key), new PyInt(kvp.Value));
                        }
                        return pyDict;
                    }
                    return new PyDict();
                });

                morldModule.ModuleDict["has_item"] = new PyBuiltinFunction("has_item", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("has_item(unit_id, item_id, count=1) requires at least 2 arguments");

                    int unitId = args[0].ToInt();
                    int itemId = args[1].ToInt();
                    int count = args.Length >= 3 ? args[2].ToInt() : 1;

                    if (_inventorySystem != null)
                    {
                        var inventory = _inventorySystem.GetUnitInventory(unitId);
                        if (inventory.TryGetValue(itemId, out int owned))
                        {
                            return PyBool.FromBool(owned >= count);
                        }
                    }
                    return PyBool.False;
                });

                // === 유닛 API ===
                morldModule.ModuleDict["get_unit_info"] = new PyBuiltinFunction("get_unit_info", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_unit_info(unit_id) requires 1 argument");

                    // None 체크
                    if (args[0] is PyNone)
                        return PyNone.Instance;

                    int unitId = args[0].ToInt();

                    if (_unitSystem == null)
                        return PyNone.Instance;

                    var unit = _unitSystem.GetUnit(unitId);
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

                    // 현재 스케줄/활동 정보
                    var currentSchedule = unit.CurrentSchedule;
                    if (currentSchedule != null)
                    {
                        result.SetItem(new PyString("activity"), new PyString(currentSchedule.Activity ?? ""));
                        result.SetItem(new PyString("schedule_name"), new PyString(currentSchedule.Name ?? ""));
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

                // === 태그/플래그 API (플레이어 태그 기반) ===
                morldModule.ModuleDict["set_flag"] = new PyBuiltinFunction("set_flag", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("set_flag(flag_name, value=1) requires at least 1 argument");

                    string flagName = args[0].AsString();
                    int value = args.Length >= 2 ? args[1].ToInt() : 1;

                    if (_playerSystem == null || _unitSystem == null)
                        return PyBool.False;

                    var player = _unitSystem.GetUnit(_playerSystem.PlayerId);
                    if (player == null)
                        return PyBool.False;

                    player.TraversalContext.SetTag(flagName, value);
                    Godot.GD.Print($"[morld] set_flag: {flagName} = {value}");
                    return new PyInt(value);
                });

                morldModule.ModuleDict["get_flag"] = new PyBuiltinFunction("get_flag", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_flag(flag_name) requires 1 argument");

                    string flagName = args[0].AsString();

                    if (_playerSystem == null || _unitSystem == null)
                        return new PyInt(0);

                    var player = _unitSystem.GetUnit(_playerSystem.PlayerId);
                    if (player == null)
                        return new PyInt(0);

                    int value = player.TraversalContext.GetTagValue(flagName);
                    return new PyInt(value);
                });

                morldModule.ModuleDict["clear_flag"] = new PyBuiltinFunction("clear_flag", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("clear_flag(flag_name) requires 1 argument");

                    string flagName = args[0].AsString();

                    if (_playerSystem == null || _unitSystem == null)
                        return PyBool.False;

                    var player = _unitSystem.GetUnit(_playerSystem.PlayerId);
                    if (player == null)
                        return PyBool.False;

                    player.TraversalContext.SetTag(flagName, 0);
                    Godot.GD.Print($"[morld] clear_flag: {flagName}");
                    return PyBool.True;
                });

                // === 시나리오 API ===
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

                // === 액션 로그 API ===
                morldModule.ModuleDict["add_action_log"] = new PyBuiltinFunction("add_action_log", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("add_action_log(message) requires 1 argument");

                    string message = args[0].AsString();

                    if (_textUISystem != null)
                    {
                        _textUISystem.AddActionLog(message);
                        Godot.GD.Print($"[morld] add_action_log: {message}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                // === 스크립트 함수 등록 API ===
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
        /// morld 모듈에 데이터 조작 API 추가 (Python에서 직접 게임 데이터 생성)
        /// </summary>
        private void RegisterDataManipulationAPI()
        {
            Godot.GD.Print("[ScriptSystem] Registering data manipulation API...");

            try
            {
                // 기존 morld 모듈 가져오기
                var morldModule = PyImportSystem.Import("morld");

                // === Region/Location API (WorldSystem) ===
                morldModule.ModuleDict["add_region"] = new PyBuiltinFunction("add_region", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("add_region(id, name, appearance=None, weather='맑음') requires at least 2 arguments");

                    int id = args[0].ToInt();
                    string name = args[1].AsString();
                    var appearance = args.Length >= 3 && args[2] is PyDict appDict
                        ? PyDictToStringDict(appDict)
                        : null;
                    string weather = args.Length >= 4 ? args[3].AsString() : "맑음";

                    if (_worldSystem != null)
                    {
                        var terrain = _worldSystem.GetTerrain();
                        var region = new Morld.Region(id, name);
                        if (appearance != null)
                        {
                            foreach (var (key, value) in appearance)
                                region.Appearance[key] = value;
                        }
                        region.CurrentWeather = weather;
                        terrain.AddRegion(region);
                        Godot.GD.Print($"[morld] add_region: id={id}, name={name}, weather={weather}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["add_location"] = new PyBuiltinFunction("add_location", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("add_location(region_id, local_id, name, appearance=None, stay_duration=0, indoor=True) requires at least 3 arguments");

                    int regionId = args[0].ToInt();
                    int localId = args[1].ToInt();
                    string name = args[2].AsString();
                    var appearance = args.Length >= 4 && args[3] is PyDict appDict
                        ? PyDictToStringDict(appDict)
                        : null;
                    int stayDuration = args.Length >= 5 ? args[4].ToInt() : 0;
                    bool isIndoor = args.Length >= 6 ? args[5].IsTrue() : true;

                    if (_worldSystem != null)
                    {
                        var terrain = _worldSystem.GetTerrain();
                        var region = terrain.GetRegion(regionId);
                        if (region != null)
                        {
                            // Region.AddLocation(localId, name)을 사용
                            var location = region.AddLocation(localId, name);
                            if (appearance != null)
                            {
                                foreach (var (key, value) in appearance)
                                    location.Appearance[key] = value;
                            }
                            location.StayDuration = stayDuration;
                            location.IsIndoor = isIndoor;
                            Godot.GD.Print($"[morld] add_location: region={regionId}, local={localId}, name={name}, indoor={isIndoor}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["add_edge"] = new PyBuiltinFunction("add_edge", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("add_edge(region_id, from_id, to_id, travel_time=5, conditions=None) requires at least 3 arguments");

                    int regionId = args[0].ToInt();
                    int fromId = args[1].ToInt();
                    int toId = args[2].ToInt();
                    int travelTime = args.Length >= 4 ? args[3].ToInt() : 5;
                    var conditions = args.Length >= 5 && args[4] is PyDict condDict
                        ? PyDictToIntDict(condDict)
                        : null;

                    if (_worldSystem != null)
                    {
                        var terrain = _worldSystem.GetTerrain();
                        var region = terrain.GetRegion(regionId);
                        if (region != null)
                        {
                            // Region.AddEdge(localIdA, localIdB, travelTime)을 사용
                            var edge = region.AddEdge(fromId, toId, travelTime);
                            if (conditions != null)
                            {
                                foreach (var (key, value) in conditions)
                                    edge.AddCondition(key, value);
                            }
                            Godot.GD.Print($"[morld] add_edge: region={regionId}, {fromId}<->{toId}, time={travelTime}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                // 양방향 조건을 지원하는 edge 추가
                morldModule.ModuleDict["add_edge_with_conditions"] = new PyBuiltinFunction("add_edge_with_conditions", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("add_edge_with_conditions(region_id, from_id, to_id, time_ab=1, time_ba=1, conditions_ab={}, conditions_ba={}) requires at least 3 arguments");

                    int regionId = args[0].ToInt();
                    int fromId = args[1].ToInt();
                    int toId = args[2].ToInt();
                    int timeAB = args.Length >= 4 ? args[3].ToInt() : 1;
                    int timeBA = args.Length >= 5 ? args[4].ToInt() : timeAB;
                    var conditionsAB = args.Length >= 6 && args[5] is PyDict condDictAB
                        ? PyDictToIntDict(condDictAB)
                        : null;
                    var conditionsBA = args.Length >= 7 && args[6] is PyDict condDictBA
                        ? PyDictToIntDict(condDictBA)
                        : null;

                    if (_worldSystem != null)
                    {
                        var terrain = _worldSystem.GetTerrain();
                        var region = terrain.GetRegion(regionId);
                        if (region != null)
                        {
                            var edge = region.AddEdge(fromId, toId, timeAB);
                            edge.SetTravelTime(timeAB, timeBA);
                            if (conditionsAB != null)
                            {
                                foreach (var (key, value) in conditionsAB)
                                    edge.AddConditionAtoB(key, value);
                            }
                            if (conditionsBA != null)
                            {
                                foreach (var (key, value) in conditionsBA)
                                    edge.AddConditionBtoA(key, value);
                            }
                            Godot.GD.Print($"[morld] add_edge_with_conditions: region={regionId}, {fromId}<->{toId}, time={timeAB}/{timeBA}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["add_region_edge"] = new PyBuiltinFunction("add_region_edge", args =>
                {
                    if (args.Length < 4)
                        throw PyTypeError.Create("add_region_edge(from_region, from_local, to_region, to_local, time_ab=30, time_ba=30) requires at least 4 arguments");

                    int fromRegion = args[0].ToInt();
                    int fromLocal = args[1].ToInt();
                    int toRegion = args[2].ToInt();
                    int toLocal = args[3].ToInt();
                    int timeAB = args.Length >= 5 ? args[4].ToInt() : 30;
                    int timeBA = args.Length >= 6 ? args[5].ToInt() : timeAB;

                    if (_worldSystem != null)
                    {
                        var terrain = _worldSystem.GetTerrain();
                        // RegionEdge(id, regionIdA, localIdA, regionIdB, localIdB) 생성자 사용
                        var regionEdge = new Morld.RegionEdge(
                            terrain.RegionEdges.Count,
                            fromRegion, fromLocal,
                            toRegion, toLocal
                        );
                        regionEdge.SetTravelTime(timeAB, timeBA);
                        terrain.AddRegionEdge(regionEdge);
                        Godot.GD.Print($"[morld] add_region_edge: {fromRegion}:{fromLocal} <-> {toRegion}:{toLocal}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                // === Time API (GameTime) ===
                morldModule.ModuleDict["set_time"] = new PyBuiltinFunction("set_time", args =>
                {
                    if (args.Length < 4)
                        throw PyTypeError.Create("set_time(year, month, day, hour, minute=0) requires at least 4 arguments");

                    int year = args[0].ToInt();
                    int month = args[1].ToInt();
                    int day = args[2].ToInt();
                    int hour = args[3].ToInt();
                    int minute = args.Length >= 5 ? args[4].ToInt() : 0;

                    if (_worldSystem != null)
                    {
                        var time = _worldSystem.GetTime();
                        // SetTime(year, month, day, hour, minute)
                        time.SetTime(year, month, day, hour, minute);
                        Godot.GD.Print($"[morld] set_time: {year}/{month}/{day} {hour}:{minute:D2}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["advance_time"] = new PyBuiltinFunction("advance_time", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("advance_time(minutes) requires 1 argument");

                    int minutes = args[0].ToInt();

                    if (_worldSystem != null)
                    {
                        var time = _worldSystem.GetTime();
                        time.AddMinutes(minutes);
                        Godot.GD.Print($"[morld] advance_time: +{minutes} minutes");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                // === Weather API ===
                morldModule.ModuleDict["set_weather"] = new PyBuiltinFunction("set_weather", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_weather(region_id, weather) requires 2 arguments");

                    int regionId = args[0].ToInt();
                    string weather = args[1].AsString();

                    if (_worldSystem != null)
                    {
                        var terrain = _worldSystem.GetTerrain();
                        var region = terrain.GetRegion(regionId);
                        if (region != null)
                        {
                            region.CurrentWeather = weather;
                            Godot.GD.Print($"[morld] set_weather: region={regionId}, weather={weather}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["get_weather"] = new PyBuiltinFunction("get_weather", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_weather(region_id) requires 1 argument");

                    int regionId = args[0].ToInt();

                    if (_worldSystem != null)
                    {
                        var terrain = _worldSystem.GetTerrain();
                        var region = terrain.GetRegion(regionId);
                        if (region != null)
                        {
                            return new PyString(region.CurrentWeather);
                        }
                    }
                    return PyNone.Instance;
                });

                // === Item API (ItemSystem) ===
                // add_item 함수 정의 (람다로 재사용)
                PyBuiltinFunction addItemFunc = new PyBuiltinFunction("add_item", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("add_item(id, name, passive_tags=None, equip_tags=None, value=0, actions=None) requires at least 2 arguments");

                    int id = args[0].ToInt();
                    string name = args[1].AsString();
                    var passiveTags = args.Length >= 3 && args[2] is PyDict ptDict ? PyDictToIntDict(ptDict) : null;
                    var equipTags = args.Length >= 4 && args[3] is PyDict etDict ? PyDictToIntDict(etDict) : null;
                    int value = args.Length >= 5 ? args[4].ToInt() : 0;
                    var actions = args.Length >= 6 && args[5] is PyList actList ? PyListToStringList(actList) : null;

                    if (_itemSystem != null)
                    {
                        var item = new Morld.Item(id, name);
                        item.Value = value;
                        if (passiveTags != null)
                            foreach (var (k, v) in passiveTags) item.PassiveTags[k] = v;
                        if (equipTags != null)
                            foreach (var (k, v) in equipTags) item.EquipTags[k] = v;
                        if (actions != null)
                            item.Actions.AddRange(actions);

                        _itemSystem.AddItem(item);
                        Godot.GD.Print($"[morld] add_item: id={id}, name={name}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });
                morldModule.ModuleDict["add_item"] = addItemFunc;
                morldModule.ModuleDict["add_item_def"] = addItemFunc;  // 레거시 별칭

                // === Unit API (UnitSystem) ===
                morldModule.ModuleDict["add_unit"] = new PyBuiltinFunction("add_unit", args =>
                {
                    if (args.Length < 4)
                        throw PyTypeError.Create("add_unit(id, name, region_id, location_id, type='male', actions=None, appearance=None, mood=None) requires at least 4 arguments");

                    int id = args[0].ToInt();
                    string name = args[1].AsString();
                    int regionId = args[2].ToInt();
                    int locationId = args[3].ToInt();
                    string type = args.Length >= 5 ? args[4].AsString() : "male";
                    var actions = args.Length >= 6 && args[5] is PyList actList ? PyListToStringList(actList) : null;
                    var appearance = args.Length >= 7 && args[6] is PyDict appDict ? PyDictToStringDict(appDict) : null;
                    var mood = args.Length >= 8 && args[7] is PyList moodList ? PyListToStringList(moodList) : null;

                    if (_unitSystem != null)
                    {
                        var unit = new Morld.Unit(id, name, regionId, locationId);
                        unit.Type = type.ToLower() switch
                        {
                            "female" => Morld.UnitType.Female,
                            "object" => Morld.UnitType.Object,
                            _ => Morld.UnitType.Male
                        };
                        if (actions != null)
                            unit.Actions.AddRange(actions);
                        if (appearance != null)
                            foreach (var (k, v) in appearance) unit.Appearance[k] = v;
                        if (mood != null)
                            foreach (var m in mood) unit.Mood.Add(m);

                        _unitSystem.AddUnit(unit);
                        Godot.GD.Print($"[morld] add_unit: id={id}, name={name}, type={type}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["set_unit_tags"] = new PyBuiltinFunction("set_unit_tags", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_unit_tags(unit_id, tags) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    var tags = args[1] is PyDict tagDict ? PyDictToIntDict(tagDict) : null;

                    if (_unitSystem != null && tags != null)
                    {
                        var unit = _unitSystem.GetUnit(unitId);
                        if (unit != null)
                        {
                            unit.TraversalContext.SetTags(tags);
                            Godot.GD.Print($"[morld] set_unit_tags: unit={unitId}, tags={tags.Count}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["set_unit_location"] = new PyBuiltinFunction("set_unit_location", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("set_unit_location(unit_id, region_id, location_id) requires 3 arguments");

                    int unitId = args[0].ToInt();
                    int regionId = args[1].ToInt();
                    int locationId = args[2].ToInt();

                    if (_unitSystem != null)
                    {
                        var unit = _unitSystem.GetUnit(unitId);
                        if (unit != null)
                        {
                            unit.SetCurrentLocation(new Morld.LocationRef(regionId, locationId));
                            unit.CurrentEdge = null;  // 이동 중이었다면 취소
                            Godot.GD.Print($"[morld] set_unit_location: unit={unitId} -> {regionId}:{locationId}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["push_schedule"] = new PyBuiltinFunction("push_schedule", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("push_schedule(unit_id, name, end_type=None, end_param=None, schedule=None) requires at least 2 arguments");

                    int unitId = args[0].ToInt();
                    string name = args[1].AsString();
                    string endType = args.Length >= 3 && args[2] is not PyNone ? args[2].AsString() : null;
                    string endParam = args.Length >= 4 && args[3] is not PyNone ? args[3].AsString() : null;
                    var scheduleData = args.Length >= 5 && args[4] is PyList schedList ? schedList : null;

                    if (_unitSystem != null)
                    {
                        var unit = _unitSystem.GetUnit(unitId);
                        if (unit != null)
                        {
                            Morld.DailySchedule schedule = null;
                            if (scheduleData != null && scheduleData.Length() > 0)
                            {
                                schedule = new Morld.DailySchedule();
                                for (int i = 0; i < scheduleData.Length(); i++)
                                {
                                    if (scheduleData.GetItem(i) is PyDict entry)
                                    {
                                        var entryName = GetPyDictString(entry, "name", "");
                                        var entryRegion = GetPyDictInt(entry, "regionId", 0);
                                        var entryLocation = GetPyDictInt(entry, "locationId", 0);
                                        var start = GetPyDictInt(entry, "start", 0);
                                        var end = GetPyDictInt(entry, "end", 0);
                                        var activity = GetPyDictString(entry, "activity", "");
                                        schedule.AddEntry(entryName, entryRegion, entryLocation, start, end, activity);
                                    }
                                }
                            }

                            unit.PushSchedule(new Morld.ScheduleLayer
                            {
                                Name = name,
                                Schedule = schedule,
                                EndConditionType = endType,
                                EndConditionParam = endParam
                            });
                            Godot.GD.Print($"[morld] push_schedule: unit={unitId}, name={name}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                // === Clear API (챕터 전환용) ===
                morldModule.ModuleDict["clear_units"] = new PyBuiltinFunction("clear_units", args =>
                {
                    if (_unitSystem != null)
                    {
                        _unitSystem.ClearUnits();
                        Godot.GD.Print("[morld] clear_units: All units cleared");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["clear_items"] = new PyBuiltinFunction("clear_items", args =>
                {
                    if (_itemSystem != null)
                    {
                        _itemSystem.ClearItems();
                        Godot.GD.Print("[morld] clear_items: All items cleared");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["clear_inventory"] = new PyBuiltinFunction("clear_inventory", args =>
                {
                    if (_inventorySystem != null)
                    {
                        _inventorySystem.ClearData();
                        Godot.GD.Print("[morld] clear_inventory: All inventory data cleared");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["clear_world"] = new PyBuiltinFunction("clear_world", args =>
                {
                    if (_worldSystem != null)
                    {
                        var terrain = _worldSystem.GetTerrain();
                        terrain.Clear();
                        Godot.GD.Print("[morld] clear_world: Terrain cleared");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["clear_all"] = new PyBuiltinFunction("clear_all", args =>
                {
                    bool success = true;

                    if (_worldSystem != null)
                    {
                        _worldSystem.GetTerrain().Clear();
                    }
                    else success = false;

                    if (_unitSystem != null)
                    {
                        _unitSystem.ClearUnits();
                    }
                    else success = false;

                    if (_itemSystem != null)
                    {
                        _itemSystem.ClearItems();
                    }
                    else success = false;

                    if (_inventorySystem != null)
                    {
                        _inventorySystem.ClearData();
                    }
                    else success = false;

                    Godot.GD.Print("[morld] clear_all: All game data cleared");
                    return PyBool.FromBool(success);
                });

                // === 신규 API: 캐릭터 행동 명령 ===

                // move_unit: 이동 스케줄 push
                morldModule.ModuleDict["move_unit"] = new PyBuiltinFunction("move_unit", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("move_unit(unit_id, region_id, location_id) requires 3 arguments");

                    int unitId = args[0].ToInt();
                    int regionId = args[1].ToInt();
                    int locationId = args[2].ToInt();

                    if (_unitSystem != null)
                    {
                        var unit = _unitSystem.GetUnit(unitId);
                        if (unit != null)
                        {
                            // 이동 스케줄 push
                            unit.PushSchedule(new Morld.ScheduleLayer
                            {
                                Name = "이동",
                                Schedule = null,
                                EndConditionType = "이동",
                                EndConditionParam = $"{regionId}:{locationId}"
                            });
                            Godot.GD.Print($"[morld] move_unit: unit={unitId} -> {regionId}:{locationId}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                // wait_unit: 대기 스케줄 push
                morldModule.ModuleDict["wait_unit"] = new PyBuiltinFunction("wait_unit", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("wait_unit(unit_id, duration) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    int duration = args[1].ToInt();

                    if (_unitSystem != null)
                    {
                        var unit = _unitSystem.GetUnit(unitId);
                        if (unit != null)
                        {
                            // 대기 스케줄 push (RemainingLifetime 사용)
                            unit.PushSchedule(new Morld.ScheduleLayer
                            {
                                Name = "대기",
                                Schedule = null,
                                EndConditionType = "대기",
                                RemainingLifetime = duration
                            });
                            Godot.GD.Print($"[morld] wait_unit: unit={unitId}, duration={duration}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                // set_unit_tag: 단일 태그 설정
                morldModule.ModuleDict["set_unit_tag"] = new PyBuiltinFunction("set_unit_tag", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("set_unit_tag(unit_id, tag_name, value) requires 3 arguments");

                    int unitId = args[0].ToInt();
                    string tagName = args[1].AsString();
                    int value = args[2].ToInt();

                    if (_unitSystem != null)
                    {
                        var unit = _unitSystem.GetUnit(unitId);
                        if (unit != null)
                        {
                            unit.TraversalContext.SetTag(tagName, value);
                            Godot.GD.Print($"[morld] set_unit_tag: unit={unitId}, {tagName}={value}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                // set_unit_mood: 감정 상태 설정
                morldModule.ModuleDict["set_unit_mood"] = new PyBuiltinFunction("set_unit_mood", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_unit_mood(unit_id, moods) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    var moods = args[1] is PyList moodList ? PyListToStringList(moodList) : null;

                    if (_unitSystem != null && moods != null)
                    {
                        var unit = _unitSystem.GetUnit(unitId);
                        if (unit != null)
                        {
                            unit.Mood.Clear();
                            foreach (var m in moods) unit.Mood.Add(m);
                            Godot.GD.Print($"[morld] set_unit_mood: unit={unitId}, moods=[{string.Join(", ", moods)}]");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                // set_unit_activity: 활동 상태 설정 (CurrentSchedule.Activity)
                morldModule.ModuleDict["set_unit_activity"] = new PyBuiltinFunction("set_unit_activity", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_unit_activity(unit_id, activity) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    string activity = args[1] is PyNone ? null : args[1].AsString();

                    if (_unitSystem != null)
                    {
                        var unit = _unitSystem.GetUnit(unitId);
                        if (unit != null)
                        {
                            // CurrentSchedule의 Activity 설정 (CurrentSchedule이 없으면 임시 생성)
                            var currentSchedule = unit.CurrentSchedule;
                            if (currentSchedule != null)
                            {
                                currentSchedule.Activity = activity;
                            }
                            else if (!string.IsNullOrEmpty(activity))
                            {
                                // 현재 스케줄이 없으면 Activity만 설정할 수 있는 임시 항목 생성 불가
                                // 대신 unit에 직접 Activity 저장 필드가 필요 (현재 설계상 CurrentSchedule 경유)
                                Godot.GD.PrintErr($"[morld] set_unit_activity: unit={unitId} has no CurrentSchedule");
                                return PyBool.False;
                            }
                            Godot.GD.Print($"[morld] set_unit_activity: unit={unitId}, activity={activity ?? "null"}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                // get_game_time: 현재 게임 시간 (분 단위) 반환
                morldModule.ModuleDict["get_game_time"] = new PyBuiltinFunction("get_game_time", args =>
                {
                    if (_worldSystem != null)
                    {
                        var time = _worldSystem.GetTime();
                        return new PyInt(time.MinuteOfDay);
                    }
                    return new PyInt(0);
                });

                // set_region_weather: 지역 날씨 설정 (기존 set_weather와 동일하지만 명확한 이름)
                morldModule.ModuleDict["set_region_weather"] = new PyBuiltinFunction("set_region_weather", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_region_weather(region_id, weather) requires 2 arguments");

                    int regionId = args[0].ToInt();
                    string weather = args[1].AsString();

                    if (_worldSystem != null)
                    {
                        var terrain = _worldSystem.GetTerrain();
                        var region = terrain.GetRegion(regionId);
                        if (region != null)
                        {
                            region.CurrentWeather = weather;
                            Godot.GD.Print($"[morld] set_region_weather: region={regionId}, weather={weather}");
                            return PyBool.True;
                        }
                    }
                    return PyBool.False;
                });

                // === ThinkSystem용 API (경로 계획) ===

                // find_path(from_region, from_location, to_region, to_location, unit_id=None)
                // 경로 탐색 - [(region_id, location_id), ...] 리스트 반환
                morldModule.ModuleDict["find_path"] = new PyBuiltinFunction("find_path", args =>
                {
                    if (args.Length < 4)
                        throw PyTypeError.Create("find_path(from_region, from_loc, to_region, to_loc, unit_id=None) requires at least 4 arguments");

                    int fromRegion = args[0].ToInt();
                    int fromLoc = args[1].ToInt();
                    int toRegion = args[2].ToInt();
                    int toLoc = args[3].ToInt();
                    int? unitId = args.Length > 4 && args[4] != PyNone.Instance ? args[4].ToInt() : null;

                    if (_worldSystem == null)
                        return PyNone.Instance;

                    var terrain = _worldSystem.GetTerrain();
                    var from = new Morld.LocationRef(fromRegion, fromLoc);
                    var to = new Morld.LocationRef(toRegion, toLoc);

                    // 유닛 기반 경로 탐색 (조건 체크용)
                    Morld.Unit unit = null;
                    if (unitId.HasValue && _unitSystem != null)
                        unit = _unitSystem.GetUnit(unitId.Value);

                    var pathResult = terrain.FindPath(from, to, unit, _itemSystem);

                    if (pathResult == null || !pathResult.Found || pathResult.Path.Count == 0)
                        return PyNone.Instance;

                    // Python 리스트로 변환: [(region_id, location_id), ...]
                    var pyList = new PyList();
                    foreach (var loc in pathResult.Path)
                    {
                        var tuple = new PyTuple(new PyObject[] {
                            new PyInt(loc.RegionId),
                            new PyInt(loc.LocalId)
                        });
                        pyList.Append(tuple);
                    }
                    return pyList;
                });

                // set_route(unit_id, path) - Unit.PlannedRoute 설정
                // path: [(region_id, location_id), ...] 리스트
                morldModule.ModuleDict["set_route"] = new PyBuiltinFunction("set_route", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_route(unit_id, path) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    var pathArg = args[1];

                    if (_unitSystem == null)
                        return PyBool.False;

                    var unit = _unitSystem.GetUnit(unitId);
                    if (unit == null)
                        return PyBool.False;

                    var route = new System.Collections.Generic.List<Morld.LocationRef>();

                    if (pathArg is PyList pyList)
                    {
                        for (int i = 0; i < pyList.Length(); i++)
                        {
                            var item = pyList.GetItem(i);
                            if (item is PyTuple tuple && tuple.Length() >= 2)
                            {
                                int regionId = tuple.GetItem(0).ToInt();
                                int locationId = tuple.GetItem(1).ToInt();
                                route.Add(new Morld.LocationRef(regionId, locationId));
                            }
                        }
                    }

                    unit.SetRoute(route);
                    return PyBool.True;
                });

                // get_route(unit_id) - 현재 경로 조회
                // 반환: {"path": [...], "index": N} 또는 None
                morldModule.ModuleDict["get_route"] = new PyBuiltinFunction("get_route", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_route(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    if (_unitSystem == null)
                        return PyNone.Instance;

                    var unit = _unitSystem.GetUnit(unitId);
                    if (unit == null || !unit.HasPlannedRoute)
                        return PyNone.Instance;

                    var pathList = new PyList();
                    foreach (var loc in unit.PlannedRoute)
                    {
                        var tuple = new PyTuple(new PyObject[] {
                            new PyInt(loc.RegionId),
                            new PyInt(loc.LocalId)
                        });
                        pathList.Append(tuple);
                    }

                    var result = new PyDict();
                    result.SetItem(new PyString("path"), pathList);
                    result.SetItem(new PyString("index"), new PyInt(unit.RouteIndex));
                    return result;
                });

                // get_unit_location(unit_id) - 유닛 현재 위치 조회
                // 반환: (region_id, location_id) 또는 None
                morldModule.ModuleDict["get_unit_location"] = new PyBuiltinFunction("get_unit_location", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_unit_location(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    if (_unitSystem == null)
                        return PyNone.Instance;

                    var unit = _unitSystem.GetUnit(unitId);
                    if (unit == null)
                        return PyNone.Instance;

                    return new PyTuple(new PyObject[] {
                        new PyInt(unit.CurrentLocation.RegionId),
                        new PyInt(unit.CurrentLocation.LocalId)
                    });
                });

                // get_schedule_entry(unit_id, minute_of_day=None) - 스케줄 엔트리 조회
                // 반환: {"name": str, "region_id": int, "location_id": int, "activity": str|None} 또는 None
                morldModule.ModuleDict["get_schedule_entry"] = new PyBuiltinFunction("get_schedule_entry", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_schedule_entry(unit_id, minute_of_day=None) requires at least 1 argument");

                    int unitId = args[0].ToInt();

                    if (_unitSystem == null || _worldSystem == null)
                        return PyNone.Instance;

                    var unit = _unitSystem.GetUnit(unitId);
                    if (unit == null)
                        return PyNone.Instance;

                    // 현재 스케줄 레이어의 DailySchedule에서 엔트리 찾기
                    var layer = unit.CurrentScheduleLayer;
                    if (layer == null || layer.Schedule == null)
                        return PyNone.Instance;

                    // minute_of_day로 GameTime을 사용해서 조회
                    var currentTime = _worldSystem.GetTime();
                    var entry = layer.Schedule.GetCurrentEntry(currentTime);
                    if (entry == null)
                        return PyNone.Instance;

                    var result = new PyDict();
                    result.SetItem(new PyString("name"), new PyString(entry.Name ?? ""));
                    result.SetItem(new PyString("region_id"), new PyInt(entry.Location.RegionId));
                    result.SetItem(new PyString("location_id"), new PyInt(entry.Location.LocalId));
                    result.SetItem(new PyString("activity"), entry.Activity != null ? new PyString(entry.Activity) : PyNone.Instance);
                    return result;
                });

                // clear_route(unit_id) - 경로 초기화
                morldModule.ModuleDict["clear_route"] = new PyBuiltinFunction("clear_route", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("clear_route(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    if (_unitSystem == null)
                        return PyBool.False;

                    var unit = _unitSystem.GetUnit(unitId);
                    if (unit == null)
                        return PyBool.False;

                    unit.ClearRoute();
                    return PyBool.True;
                });

                // === 초기화 완료 플래그 ===
                morldModule.ModuleDict["data_api_ready"] = PyBool.True;

                Godot.GD.Print("[ScriptSystem] Data manipulation API registered successfully.");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] RegisterDataManipulationAPI error: {ex.Message}");
            }
        }

        /// <summary>
        /// PyDict를 Dictionary<string, string>으로 변환
        /// </summary>
        private System.Collections.Generic.Dictionary<string, string> PyDictToStringDict(PyDict dict)
        {
            var result = new System.Collections.Generic.Dictionary<string, string>();
            var keys = dict.Keys();  // PyList 반환
            for (int i = 0; i < keys.Length(); i++)
            {
                var key = keys.GetItem(i);
                var keyStr = key is PyString ks ? ks.Value : key.ToString();
                var value = dict.GetItem(key);
                var valueStr = value is PyString vs ? vs.Value : value?.ToString() ?? "";
                result[keyStr] = valueStr;
            }
            return result;
        }

        /// <summary>
        /// PyDict를 Dictionary<string, int>으로 변환
        /// </summary>
        private System.Collections.Generic.Dictionary<string, int> PyDictToIntDict(PyDict dict)
        {
            var result = new System.Collections.Generic.Dictionary<string, int>();
            var keys = dict.Keys();  // PyList 반환
            for (int i = 0; i < keys.Length(); i++)
            {
                var key = keys.GetItem(i);
                var keyStr = key is PyString ks ? ks.Value : key.ToString();
                var value = dict.GetItem(key);
                var valueInt = value is PyInt vi ? (int)vi.Value : 0;
                result[keyStr] = valueInt;
            }
            return result;
        }

        /// <summary>
        /// PyList를 List<string>으로 변환
        /// </summary>
        private System.Collections.Generic.List<string> PyListToStringList(PyList list)
        {
            var result = new System.Collections.Generic.List<string>();
            for (int i = 0; i < list.Length(); i++)
            {
                var item = list.GetItem(i);
                result.Add(item is PyString ps ? ps.Value : item?.ToString() ?? "");
            }
            return result;
        }

        /// <summary>
        /// PyDict에서 문자열 값 추출
        /// </summary>
        private string GetPyDictString(PyDict dict, string key, string defaultValue)
        {
            var value = dict.Get(new PyString(key));
            return value is PyString ps ? ps.Value : defaultValue;
        }

        /// <summary>
        /// PyDict에서 정수 값 추출
        /// </summary>
        private int GetPyDictInt(PyDict dict, string key, int defaultValue)
        {
            var value = dict.Get(new PyString(key));
            return value is PyInt pi ? (int)pi.Value : defaultValue;
        }

        /// <summary>
        /// Python 코드 실행 (File 모드 - 함수 정의, import 등)
        /// </summary>
        public PyObject Execute(string code)
        {
            return _interpreter.Execute(code);
        }

        /// <summary>
        /// Python 표현식 평가 (Eval 모드)
        /// CompileMode.Eval로 표현식을 컴파일하여 결과 반환
        /// </summary>
        public PyObject Eval(string expression)
        {
            return _interpreter.ExecuteEval(expression);
        }

        /// <summary>
        /// Python 파일 실행
        /// </summary>
        public PyObject ExecuteFile(string filePath)
        {
            string code;

            // res:// 경로는 Godot FileAccess로 읽기
            if (filePath.StartsWith("res://"))
            {
                using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
                if (file == null)
                {
                    var error = Godot.FileAccess.GetOpenError();
                    Godot.GD.PrintErr($"[ScriptSystem] Failed to open file: {filePath} (Error: {error})");
                    return PyNone.Instance;
                }
                code = file.GetAsText();
            }
            else
            {
                // 일반 파일 시스템 경로
                if (!System.IO.File.Exists(filePath))
                {
                    Godot.GD.PrintErr($"[ScriptSystem] File not found: {filePath}");
                    return PyNone.Instance;
                }
                code = System.IO.File.ReadAllText(filePath);
            }

            return _interpreter.Execute(code, filePath, false, false, false);
        }

        /// <summary>
        /// 모놀로그 스크립트 로드 (시나리오 경로 기반)
        /// </summary>
        public void LoadMonologueScripts()
        {
            Godot.GD.Print("[ScriptSystem] Loading scenario scripts...");

            // 시나리오 경로가 설정되지 않은 경우 경고
            if (string.IsNullOrEmpty(_scenarioPath))
            {
                Godot.GD.PrintErr("[ScriptSystem] Scenario path not set! Call SetScenarioPath() first.");
                return;
            }

            try
            {
                // 파일 내용을 읽어서 Execute로 직접 실행 (ExecuteFile 대신)
                string code;
                var filePath = ScenarioPythonPath + "scripts.py";

                using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
                if (file == null)
                {
                    var error = Godot.FileAccess.GetOpenError();
                    Godot.GD.PrintErr($"[ScriptSystem] Failed to open scripts file: {filePath} (Error: {error})");
                    return;
                }
                code = file.GetAsText();

                Godot.GD.Print($"[ScriptSystem] Scripts file loaded from: {filePath} ({code.Length} chars)");
                Godot.GD.Print($"[ScriptSystem] First 200 chars: {code.Substring(0, System.Math.Min(200, code.Length))}");

                // Execute로 직접 실행 (전역 스코프에 함수 등록)
                var execResult = Execute(code);
                Godot.GD.Print($"[ScriptSystem] Execute result: {execResult?.GetType().Name} = {execResult}");

                Godot.GD.Print("[ScriptSystem] Scenario scripts loaded successfully.");

                // events.py 로드 (EventSystem용)
                LoadEventsScript();
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] LoadMonologueScripts error: {ex.Message}");
            }
        }

        /// <summary>
        /// 이벤트 스크립트 로드 (EventSystem용)
        /// </summary>
        private void LoadEventsScript()
        {
            try
            {
                var filePath = ScenarioPythonPath + "events.py";

                using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
                if (file == null)
                {
                    // events.py는 선택적이므로 경고만 출력
                    Godot.GD.Print($"[ScriptSystem] events.py not found (optional): {filePath}");
                    return;
                }
                var code = file.GetAsText();

                Godot.GD.Print($"[ScriptSystem] Events file loaded from: {filePath} ({code.Length} chars)");

                // Execute로 직접 실행 (전역 스코프에 함수 등록)
                Execute(code);

                Godot.GD.Print("[ScriptSystem] Events script loaded successfully.");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] LoadEventsScript error: {ex.Message}");
            }
        }

        /// <summary>
        /// Python 패키지 스타일 시나리오 로드 (scenario03+)
        /// __init__.py가 있는 시나리오는 import로 로드
        /// </summary>
        public bool LoadScenarioPackage()
        {
            var initPath = ScenarioPythonPath + "__init__.py";

            using var file = Godot.FileAccess.Open(initPath, Godot.FileAccess.ModeFlags.Read);
            if (file == null)
            {
                Godot.GD.Print($"[ScriptSystem] Not a package-style scenario (no __init__.py)");
                return false;
            }

            Godot.GD.Print($"[ScriptSystem] Loading package-style scenario...");

            try
            {
                // 필수 모듈 import (모든 시나리오에 있어야 함)
                var coreImportCode = @"
from events import *
";
                Execute(coreImportCode);

                // 선택적 모듈 import (시나리오에 따라 없을 수 있음)
                var optionalImportCode = @"
# world, items는 initialize_scenario에서 이미 로드됨

# scripts 모듈 (오브젝트 상호작용 스크립트)
try:
    from scripts import *
except ImportError:
    pass  # 없으면 무시

# characters 모듈 (NPC가 있는 시나리오)
try:
    from characters import get_character_event_handler, get_all_presence_texts
except ImportError:
    get_character_event_handler = lambda unit_id: None
    get_all_presence_texts = lambda region_id, location_id: []

# objects 모듈 (오브젝트가 있는 시나리오)
try:
    from objects import get_all_objects
except (ImportError, AttributeError):
    get_all_objects = lambda: []

# 시나리오별 선택적 함수들
try:
    from objects.furniture import mirror_look
except (ImportError, AttributeError):
    mirror_look = lambda ctx: None

try:
    from characters.player.events import job_select, job_confirm
except (ImportError, AttributeError):
    job_select = lambda ctx, job: None
    job_confirm = lambda ctx, job: None
";
                Execute(optionalImportCode);

                // entities 모듈 로드 시도 (새로운 Python Entity System)
                TryLoadEntitiesModule();

                Godot.GD.Print("[ScriptSystem] Package-style scenario loaded successfully.");
                return true;
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] LoadScenarioPackage error: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// entities 모듈 로드 시도 (새로운 Python Entity System)
        /// entities/__init__.py가 있으면 로드
        /// </summary>
        private void TryLoadEntitiesModule()
        {
            try
            {
                // entities 폴더 존재 여부 확인 (Python 측에서)
                var checkCode = @"
try:
    import entities
    entities.load_all_entities()
    _entities_loaded = True
except ImportError:
    _entities_loaded = False
except Exception as e:
    print(f'[entities] Load error: {e}')
    _entities_loaded = False
_entities_loaded
";
                var result = Eval(checkCode);

                if (result is PyBool pyBool && pyBool.Value)
                {
                    Godot.GD.Print("[ScriptSystem] Python Entity System loaded successfully.");
                }
                else
                {
                    Godot.GD.Print("[ScriptSystem] Python Entity System not found (using classic mode).");
                }
            }
            catch (System.Exception ex)
            {
                Godot.GD.Print($"[ScriptSystem] Entity System check skipped: {ex.Message}");
            }
        }

        /// <summary>
        /// Python에서 world 데이터 로드
        /// </summary>
        public PyObject LoadWorldDataFromPython()
        {
            try
            {
                return Eval("get_world_data()");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] LoadWorldDataFromPython error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Python에서 time 데이터 로드
        /// </summary>
        public PyObject LoadTimeDataFromPython()
        {
            try
            {
                return Eval("get_time_data()");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] LoadTimeDataFromPython error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Python에서 item 데이터 로드
        /// </summary>
        public PyObject LoadItemDataFromPython()
        {
            try
            {
                return Eval("get_item_data()");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] LoadItemDataFromPython error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Python에서 unit 데이터 로드 (캐릭터 + 오브젝트)
        /// </summary>
        public PyObject LoadUnitDataFromPython()
        {
            try
            {
                return Eval("get_all_unit_data()");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] LoadUnitDataFromPython error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Python 시나리오의 initialize_scenario() 함수 호출
        /// __init__.py를 import하고 initialize_scenario() 실행
        /// </summary>
        public void CallInitializeScenario()
        {
            Godot.GD.Print("[ScriptSystem] Calling initialize_scenario()...");

            try
            {
                // 시나리오 패키지를 import하고 initialize_scenario() 호출
                // sys.path에 이미 시나리오 python 폴더가 추가되어 있음
                var code = @"
import __init__
__init__.initialize_scenario()
";
                Execute(code);

                Godot.GD.Print("[ScriptSystem] initialize_scenario() completed.");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] CallInitializeScenario error: {ex.Message}");
            }
        }

        /// <summary>
        /// Hello World 테스트
        /// </summary>
        public void TestHelloWorld()
        {
            Godot.GD.Print("[ScriptSystem] Testing Python Hello World...");

            try
            {
                var result = Execute("print('Hello, World from Python!')");
                Godot.GD.Print($"[ScriptSystem] Execution completed. Result: {result}");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] Error: {ex.Message}");
            }
        }

        /// <summary>
        /// Python 함수 호출 (BBCode script: prefix용) - 구조화된 결과 반환
        /// </summary>
        /// <param name="functionName">호출할 함수 이름</param>
        /// <param name="args">콜론으로 구분된 인자들</param>
        /// <param name="contextUnitId">현재 Focus의 UnitId (없으면 null)</param>
        /// <returns>함수 실행 결과 (ScriptResult)</returns>
        public ScriptResult CallFunctionEx(string functionName, string[] args, int? contextUnitId = null)
        {
            Godot.GD.Print($"[ScriptSystem] CallFunctionEx: {functionName}({string.Join(", ", args)}) [contextUnitId={contextUnitId?.ToString() ?? "null"}]");

            try
            {
                // 인자를 Python 형태로 변환
                var pyArgs = new System.Collections.Generic.List<string>();

                // 첫 번째 인자로 context_unit_id 추가 (None 또는 정수)
                pyArgs.Add(contextUnitId.HasValue ? contextUnitId.Value.ToString() : "None");

                foreach (var arg in args)
                {
                    // 숫자인지 확인
                    if (int.TryParse(arg, out _) || double.TryParse(arg, out _))
                    {
                        pyArgs.Add(arg);
                    }
                    else
                    {
                        // 문자열로 처리
                        pyArgs.Add($"'{arg}'");
                    }
                }

                var code = $"{functionName}({string.Join(", ", pyArgs)})";
                Godot.GD.Print($"[ScriptSystem] Evaluating: {code}");

                // Eval 모드로 실행해야 함수 호출 결과를 반환받을 수 있음
                var result = Eval(code);

                Godot.GD.Print($"[ScriptSystem] Result type: {result?.GetType().Name ?? "null"}, value: {result}");

                // PyDict인 경우 구조화된 결과로 파싱
                if (result is PyDict dict)
                {
                    return ParseDictResult(dict);
                }
                // 문자열 결과
                else if (result is PyString pyStr)
                {
                    return new ScriptResult { Type = "message", Message = pyStr.Value };
                }
                else if (result is PyInt pyInt)
                {
                    return new ScriptResult { Type = "message", Message = pyInt.Value.ToString() };
                }
                else if (result is PyNone || result == null)
                {
                    return null;
                }
                else
                {
                    return new ScriptResult { Type = "message", Message = result?.ToString() ?? "" };
                }
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] CallFunctionEx error: {ex.Message}");
                return new ScriptResult { Type = "error", Message = ex.Message };
            }
        }

        /// <summary>
        /// PyDict 결과를 ScriptResult로 파싱
        /// </summary>
        private ScriptResult ParseDictResult(PyDict dict)
        {
            var typeObj = dict.GetItem(new PyString("type"));
            var type = (typeObj as PyString)?.Value;

            if (type == "monologue" || type == "update")
            {
                var pagesObj = dict.GetItem(new PyString("pages"));
                var timeObj = dict.Get(new PyString("time_consumed"));  // Get()으로 변경 (없으면 None)
                // button_type은 선택적 필드 - Get()은 키가 없으면 None 반환
                var buttonTypeObj = dict.Get(new PyString("button_type"));

                var pages = new System.Collections.Generic.List<string>();
                if (pagesObj is PyList pagesList)
                {
                    for (int i = 0; i < pagesList.Length(); i++)
                    {
                        var page = pagesList.GetItem(i);
                        if (page is PyString pageStr)
                        {
                            pages.Add(pageStr.Value);
                        }
                    }
                }

                int timeConsumed = 0;
                if (timeObj is PyInt timeInt)
                {
                    timeConsumed = (int)timeInt.Value;
                }

                // button_type 파싱 ("ok", "none", "yesno")
                var buttonType = Morld.MonologueButtonType.Ok;
                if (buttonTypeObj is PyString buttonTypeStr)
                {
                    buttonType = buttonTypeStr.Value.ToLower() switch
                    {
                        "none" => Morld.MonologueButtonType.None,
                        "yesno" => Morld.MonologueButtonType.YesNo,
                        _ => Morld.MonologueButtonType.Ok
                    };
                }

                // 콜백 파싱 (선택적)
                // done_callback: 확인(Ok) 또는 승낙(YesNo) 시 호출
                // cancel_callback: 거절(YesNo) 시 호출
                var doneCallbackObj = dict.Get(new PyString("done_callback"));
                var cancelCallbackObj = dict.Get(new PyString("cancel_callback"));
                string doneCallback = (doneCallbackObj as PyString)?.Value;
                string cancelCallback = (cancelCallbackObj as PyString)?.Value;

                // freeze_others 파싱 (선택적) - 같은 위치 유닛들 이동 중단
                var freezeOthersObj = dict.Get(new PyString("freeze_others"));
                bool freezeOthers = freezeOthersObj is PyBool freezeBool && freezeBool.Value;

                Godot.GD.Print($"[ScriptSystem] Parsed {type} result: {pages.Count} pages, {timeConsumed}min, button={buttonType}, freeze={freezeOthers}");
                return new MonologueScriptResult
                {
                    Type = type,  // "monologue" 또는 "update"
                    Pages = pages,
                    TimeConsumed = timeConsumed,
                    ButtonType = buttonType,
                    DoneCallback = doneCallback,
                    CancelCallback = cancelCallback,
                    FreezeOthers = freezeOthers
                };
            }

            // 기본 메시지 결과 - Get()으로 안전하게 조회
            var messageObj = dict.Get(new PyString("message"));
            var message = (messageObj as PyString)?.Value ?? "";
            return new ScriptResult { Type = type ?? "unknown", Message = message };
        }

        /// <summary>
        /// Python 함수 호출 (BBCode script: prefix용) - 문자열 결과 반환 (레거시)
        /// </summary>
        /// <param name="functionName">호출할 함수 이름</param>
        /// <param name="args">콜론으로 구분된 인자들</param>
        /// <returns>함수 실행 결과 (문자열 변환)</returns>
        public string CallFunction(string functionName, string[] args)
        {
            var result = CallFunctionEx(functionName, args);
            if (result == null) return null;
            return result.Message;
        }

        /// <summary>
        /// 테스트용 Python 함수 등록
        /// </summary>
        public void RegisterTestFunctions()
        {
            Godot.GD.Print("[ScriptSystem] Registering test functions...");

            var testCode = @"
def test_dialogue(character_name):
    print(f'[Python] test_dialogue called with: {character_name}')
    return f'{character_name}와(과)의 대화를 시작합니다.'

def get_greeting(name):
    print(f'[Python] get_greeting called with: {name}')
    return f'안녕하세요, {name}님!'

def calculate(a, b):
    print(f'[Python] calculate called with: {a}, {b}')
    return a + b
";

            try
            {
                Execute(testCode);
                Godot.GD.Print("[ScriptSystem] Test functions registered successfully.");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] RegisterTestFunctions error: {ex.Message}");
            }
        }

        /// <summary>
        /// EventSystem용 이벤트 핸들러 호출 - Python on_event_list() 호출
        /// </summary>
        /// <param name="events">이벤트 목록</param>
        /// <returns>스크립트 결과 (모놀로그 등)</returns>
        public ScriptResult CallEventHandler(System.Collections.Generic.List<Morld.GameEvent> events)
        {
            if (events == null || events.Count == 0) return null;

            Godot.GD.Print($"[ScriptSystem] CallEventHandler: {events.Count} events");

            try
            {
                // 이벤트 목록을 Python 리스트 리터럴로 변환
                var eventStrings = new System.Collections.Generic.List<string>();
                foreach (var evt in events)
                {
                    var tuple = evt.ToPythonTuple();
                    var items = new System.Collections.Generic.List<string>();
                    foreach (var item in tuple)
                    {
                        if (item is string s)
                            items.Add($"'{s}'");
                        else if (item is int i)
                            items.Add(i.ToString());
                        else
                            items.Add($"'{item?.ToString() ?? ""}'");
                    }
                    eventStrings.Add($"[{string.Join(", ", items)}]");
                }

                var listLiteral = $"[{string.Join(", ", eventStrings)}]";
                var code = $"on_event_list({listLiteral})";
                Godot.GD.Print($"[ScriptSystem] Evaluating: {code}");

                // on_event_list() 호출
                var result = Eval(code);

                if (result is PyNone || result == null)
                {
                    return null;
                }

                // PyDict에서 결과 파싱
                if (result is PyDict dict)
                {
                    return ParseDictResult(dict);
                }

                Godot.GD.Print($"[ScriptSystem] Unknown event result: {result}");
                return null;
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] CallEventHandler error: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// 캐릭터 presence text 조회 - Python get_all_presence_texts() 호출
        /// 플레이어와 같은 위치에 있는 캐릭터들의 상황 묘사 텍스트 반환
        /// </summary>
        /// <param name="unitIds">캐릭터 ID 목록</param>
        /// <param name="regionId">현재 위치 region</param>
        /// <param name="locationId">현재 위치 location</param>
        /// <returns>presence text 리스트</returns>
        public System.Collections.Generic.List<string> GetCharacterPresenceTexts(
            System.Collections.Generic.List<int> unitIds, int regionId, int locationId)
        {
            var result = new System.Collections.Generic.List<string>();
            if (unitIds == null || unitIds.Count == 0) return result;

            try
            {
                // Python 리스트 리터럴 생성
                var idsLiteral = $"[{string.Join(", ", unitIds)}]";
                var code = $"get_all_presence_texts({idsLiteral}, {regionId}, {locationId})";

                var pyResult = Eval(code);

                if (pyResult is PyList pyList)
                {
                    for (int i = 0; i < pyList.Length(); i++)
                    {
                        var item = pyList.GetItem(i);
                        if (item is PyString pyStr)
                        {
                            result.Add(pyStr.Value);
                        }
                    }
                }
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] GetCharacterPresenceTexts error: {ex.Message}");
            }

            return result;
        }

        /// <summary>
        /// 이벤트 트리거 - Python on_event() 호출 (레거시, 호환용)
        /// </summary>
        /// <param name="eventName">이벤트 이름 (예: "ready", "enter_forest")</param>
        /// <returns>이벤트 결과 (EventResult)</returns>
        public EventResult TriggerEvent(string eventName)
        {
            Godot.GD.Print($"[ScriptSystem] TriggerEvent: {eventName}");

            try
            {
                var result = Eval($"on_event('{eventName}')");

                if (result is PyNone || result == null)
                {
                    return null;
                }

                // PyDict에서 결과 파싱
                if (result is PyDict dict)
                {
                    var typeObj = dict.GetItem(new PyString("type"));
                    var type = (typeObj as PyString)?.Value;

                    if (type == "monologue")
                    {
                        // pages 배열과 time_consumed 직접 파싱
                        var pagesObj = dict.GetItem(new PyString("pages"));
                        var timeObj = dict.GetItem(new PyString("time_consumed"));

                        var pages = new System.Collections.Generic.List<string>();
                        if (pagesObj is PyList pagesList)
                        {
                            for (int i = 0; i < pagesList.Length(); i++)
                            {
                                var page = pagesList.GetItem(i);
                                if (page is PyString pageStr)
                                {
                                    pages.Add(pageStr.Value);
                                }
                            }
                        }

                        int timeConsumed = 0;
                        if (timeObj is PyInt timeInt)
                        {
                            timeConsumed = (int)timeInt.Value;
                        }

                        Godot.GD.Print($"[ScriptSystem] Event result: monologue ({pages.Count} pages, {timeConsumed}min)");
                        return new MonologueEventResult
                        {
                            Type = "monologue",
                            Pages = pages,
                            TimeConsumed = timeConsumed
                        };
                    }
                }

                Godot.GD.Print($"[ScriptSystem] Unknown event result: {result}");
                return null;
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] TriggerEvent error: {ex.Message}");
                return null;
            }
        }

        // ========================================
        // ThinkSystem 지원
        // ========================================

        /// <summary>
        /// think 모듈이 사용 가능한지 확인
        /// </summary>
        public bool IsThinkModuleAvailable()
        {
            try
            {
                var result = Eval("'think' in dir() or 'think_all' in dir()");
                if (result is PyBool pyBool && pyBool.Value)
                    return true;

                // think 모듈 import 시도
                Execute("import think");
                return true;
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Python think.think_all() 호출 - 모든 NPC Agent의 경로 계획
        /// </summary>
        public void CallThinkAll()
        {
            try
            {
                Execute("import think; think.think_all()");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] CallThinkAll error: {ex.Message}");
            }
        }
    }

    /// <summary>
    /// 이벤트 결과 기본 클래스
    /// </summary>
    public class EventResult
    {
        public string Type { get; set; }  // "monologue", "dialogue" 등
    }

    /// <summary>
    /// 모놀로그 이벤트 결과 - 페이지 데이터 포함
    /// </summary>
    public class MonologueEventResult : EventResult
    {
        public System.Collections.Generic.List<string> Pages { get; set; } = new();
        public int TimeConsumed { get; set; }
    }

    /// <summary>
    /// 스크립트 함수 호출 결과 기본 클래스
    /// </summary>
    public class ScriptResult
    {
        public string Type { get; set; }  // "message", "monologue", "error" 등
        public string Message { get; set; }
    }

    /// <summary>
    /// 모놀로그 스크립트 결과 - 페이지 데이터 포함
    /// </summary>
    public class MonologueScriptResult : ScriptResult
    {
        public System.Collections.Generic.List<string> Pages { get; set; } = new();
        public int TimeConsumed { get; set; }
        public Morld.MonologueButtonType ButtonType { get; set; } = Morld.MonologueButtonType.Ok;
        public string DoneCallback { get; set; }
        public string CancelCallback { get; set; }
        /// <summary>
        /// true면 플레이어와 같은 위치의 다른 유닛들 이동 중단 (CurrentEdge = null)
        /// 이벤트 중 시간이 흘러도 NPC가 바로 떠나지 않게 함
        /// </summary>
        public bool FreezeOthers { get; set; } = false;
    }
}
