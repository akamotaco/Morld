using SharpPy;
using Morld;

namespace SE
{
    /// <summary>
    /// ScriptSystem partial - 데이터 조작 API 등록
    ///
    /// World/Location/Item/Unit 등 게임 데이터 생성/조작 API
    /// Python에서 직접 게임 오브젝트를 생성하기 위한 API
    /// </summary>
    public partial class ScriptSystem
    {
        /// <summary>
        /// morld 모듈에 데이터 조작 API 추가 (Python에서 직접 게임 데이터 생성)
        /// </summary>
        public void RegisterDataManipulationAPI()
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
                        throw PyTypeError.Create("add_region(id, name, describe_text=None, weather='맑음') requires at least 2 arguments");

                    int id = args[0].ToInt();
                    string name = args[1].AsString();
                    var describeText = args.Length >= 3 && args[2] is PyDict appDict
                        ? PyDictToStringDict(appDict)
                        : null;
                    string weather = args.Length >= 4 ? args[3].AsString() : "맑음";

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                    var terrain = _worldSystem.GetTerrain();
                    var region = new Morld.Region(id, name);
                    if (describeText != null)
                    {
                        foreach (var (key, value) in describeText)
                            region.DescribeText[key] = value;
                    }
                    region.CurrentWeather = weather;
                    terrain.AddRegion(region);
                    Godot.GD.Print($"[morld] add_region: id={id}, name={name}, weather={weather}");
                    return PyBool.True;
                });

                morldModule.ModuleDict["add_location"] = new PyBuiltinFunction("add_location", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("add_location(region_id, local_id, name, stay_duration=0, indoor=True, owner=None) requires at least 3 arguments");

                    int regionId = args[0].ToInt();
                    int localId = args[1].ToInt();
                    string name = args[2].AsString();
                    int stayDuration = args.Length >= 4 ? args[3].ToInt() : 0;
                    bool isIndoor = args.Length >= 5 ? args[4].IsTrue() : true;
                    string owner = args.Length >= 6 && args[5] is PyString ownerStr ? ownerStr.Value : null;

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                    var terrain = _worldSystem.GetTerrain();
                    var region = terrain.GetRegion(regionId);
                    if (region != null)
                    {
                        // Region.AddLocation(localId, name)을 사용
                        var location = region.AddLocation(localId, name);
                        location.StayDuration = stayDuration;
                        location.IsIndoor = isIndoor;
                        location.Owner = owner;
                        Godot.GD.Print($"[morld] add_location: region={regionId}, local={localId}, name={name}, indoor={isIndoor}");
                        return PyBool.True;
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

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

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

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

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

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                    
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

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                    var time = _worldSystem.GetTime();
                    // SetTime(year, month, day, hour, minute)
                    time.SetTime(year, month, day, hour, minute);
                    Godot.GD.Print($"[morld] set_time: {year}/{month}/{day} {hour}:{minute:D2}");
                    return PyBool.True;
                });

                morldModule.ModuleDict["advance_time"] = new PyBuiltinFunction("advance_time", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("advance_time(minutes) requires 1 argument");

                    int minutes = args[0].ToInt();

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                    var time = _worldSystem.GetTime();
                    time.AddMinutes(minutes);
                    Godot.GD.Print($"[morld] advance_time: +{minutes} minutes");

                    // 생존 시스템 처리 (플레이어만)
                    ProcessSurvivalTimeElapsed(minutes);

                    return PyBool.True;
                });

                // === Weather API ===
                morldModule.ModuleDict["set_weather"] = new PyBuiltinFunction("set_weather", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_weather(region_id, weather) requires 2 arguments");

                    int regionId = args[0].ToInt();
                    string weather = args[1].AsString();

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                    var terrain = _worldSystem.GetTerrain();
                    var region = terrain.GetRegion(regionId);
                    if (region != null)
                    {
                        region.CurrentWeather = weather;
                        Godot.GD.Print($"[morld] set_weather: region={regionId}, weather={weather}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                morldModule.ModuleDict["get_weather"] = new PyBuiltinFunction("get_weather", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_weather(region_id) requires 1 argument");

                    int regionId = args[0].ToInt();

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                    var terrain = _worldSystem.GetTerrain();
                    var region = terrain.GetRegion(regionId);
                    if (region != null)
                    {
                        return new PyString(region.CurrentWeather);
                    }
                    return PyNone.Instance;
                });

                // === Item API (ItemSystem) ===
                // add_item 함수 정의 (람다로 재사용)
                PyBuiltinFunction addItemFunc = new PyBuiltinFunction("add_item", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("add_item(id, name, passive_props=None, equip_props=None, value=0, actions=None, owner=None, unique_id=None) requires at least 2 arguments");

                    int id = args[0].ToInt();
                    string name = args[1].AsString();
                    var passiveProps = args.Length >= 3 && args[2] is PyDict ptDict ? PyDictToIntDict(ptDict) : null;
                    var equipProps = args.Length >= 4 && args[3] is PyDict etDict ? PyDictToIntDict(etDict) : null;
                    int value = args.Length >= 5 ? args[4].ToInt() : 0;
                    var actions = args.Length >= 6 && args[5] is PyList actList ? PyListToStringList(actList) : null;
                    string owner = args.Length >= 7 && args[6] is PyString ownerStr ? ownerStr.Value : null;
                    string uniqueId = args.Length >= 8 && args[7] is PyString uidStr ? uidStr.Value : null;

                    var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;

                    var item = new Morld.Item(id, name);
                    item.Value = value;
                    item.Owner = owner;
                    item.UniqueId = uniqueId;
                    if (passiveProps != null)
                        foreach (var (k, v) in passiveProps) item.PassiveProps[k] = v;
                    if (equipProps != null)
                        foreach (var (k, v) in equipProps) item.EquipProps[k] = v;
                    if (actions != null)
                        item.Actions.AddRange(actions);

                    _itemSystem.AddItem(item);
                    Godot.GD.Print($"[morld] add_item: id={id}, name={name}, unique_id={uniqueId}");
                    return PyBool.True;
                });
                morldModule.ModuleDict["add_item"] = addItemFunc;
                morldModule.ModuleDict["add_item_def"] = addItemFunc;  // 레거시 별칭

                // === Unit API (UnitSystem) ===
                morldModule.ModuleDict["add_unit"] = new PyBuiltinFunction("add_unit", args =>
                {
                    if (args.Length < 4)
                        throw PyTypeError.Create("add_unit(id, name, region_id, location_id, type='male', actions=None, mood=None, unique_id=None) requires at least 4 arguments");

                    int id = args[0].ToInt();
                    string name = args[1].AsString();
                    int regionId = args[2].ToInt();
                    int locationId = args[3].ToInt();
                    string type = args.Length >= 5 ? args[4].AsString() : "male";
                    var actions = args.Length >= 6 && args[5] is PyList actList ? PyListToStringList(actList) : null;
                    var mood = args.Length >= 7 && args[6] is PyList moodList ? PyListToStringList(moodList) : null;
                    string uniqueId = args.Length >= 8 && args[7] is PyString uidStr ? uidStr.Value : null;

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var unit = new Morld.Unit(id, name, regionId, locationId);
                    unit.UniqueId = uniqueId;
                    unit.Type = type.ToLower() switch
                    {
                        "female" => Morld.UnitType.Female,
                        "object" => Morld.UnitType.Object,
                        _ => Morld.UnitType.Male
                    };
                    if (actions != null)
                        unit.Actions.AddRange(actions);
                    if (mood != null)
                        foreach (var m in mood) unit.Mood.Add(m);

                    _unitSystem.AddUnit(unit);

                    // unique_id가 "player"이면 PlayerSystem.PlayerId 자동 설정
                    if (uniqueId == "player")
                    {
                        var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
                        if (_playerSystem != null)
                        {
                            _playerSystem.PlayerId = id;
                            Godot.GD.Print($"[morld] add_unit: Player registered with id={id}");
                        }
                    }

                    Godot.GD.Print($"[morld] add_unit: id={id}, name={name}, type={type}");
                    return PyBool.True;
                });

                // set_unit_props: 유닛 Props 일괄 설정
                morldModule.ModuleDict["set_unit_props"] = new PyBuiltinFunction("set_unit_props", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_unit_props(unit_id, props) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    var props = args[1] is PyDict propDict ? PyDictToIntDict(propDict) : null;

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    if (props != null)
                    {
                        var unit = _unitSystem.FindUnit(unitId);
                        if (unit != null)
                        {
                            unit.TraversalContext.SetProps(props);
                            Godot.GD.Print($"[morld] set_unit_props: unit={unitId}, props={props.Count}");
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

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        unit.SetCurrentLocation(new Morld.LocationRef(regionId, locationId));
                        unit.CurrentEdge = null;  // 이동 중이었다면 취소
                        Godot.GD.Print($"[morld] set_unit_location: unit={unitId} -> {regionId}:{locationId}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                // === Clear API (챕터 전환용) ===
                morldModule.ModuleDict["clear_units"] = new PyBuiltinFunction("clear_units", args =>
                {
                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    _unitSystem.ClearUnits();
                    Godot.GD.Print("[morld] clear_units: All units cleared");
                    return PyBool.True;
                });

                morldModule.ModuleDict["clear_items"] = new PyBuiltinFunction("clear_items", args =>
                {
                    var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
                    _itemSystem.ClearItems();
                    Godot.GD.Print("[morld] clear_items: All items cleared");
                    return PyBool.True;
                });

                morldModule.ModuleDict["clear_inventory"] = new PyBuiltinFunction("clear_inventory", args =>
                {
                    var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                    _inventorySystem.ClearData();
                    Godot.GD.Print("[morld] clear_inventory: All inventory data cleared");
                    return PyBool.True;
                });

                morldModule.ModuleDict["clear_world"] = new PyBuiltinFunction("clear_world", args =>
                {
                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                    var terrain = _worldSystem.GetTerrain();
                    terrain.Clear();
                    Godot.GD.Print("[morld] clear_world: Terrain cleared");
                    return PyBool.True;
                });

                morldModule.ModuleDict["clear_all"] = new PyBuiltinFunction("clear_all", args =>
                {
                    (this._hub.GetSystem("worldSystem") as WorldSystem).GetTerrain().Clear();
                    (this._hub.GetSystem("unitSystem") as UnitSystem).ClearUnits();
                    (this._hub.GetSystem("itemSystem") as ItemSystem).ClearItems();
                    (this._hub.GetSystem("inventorySystem") as InventorySystem).ClearData();

                    Godot.GD.Print("[morld] clear_all: All game data cleared");
                    return PyBool.True;
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

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        // JobList에 이동 Job 삽입
                        var job = new Morld.Job
                        {
                            Name = "이동",
                            Action = "move",
                            RegionId = regionId,
                            LocationId = locationId,
                            Duration = 1440  // 목적지 도착까지 (하루)
                        };
                        unit.InsertJobWithClear(job);
                        Godot.GD.Print($"[morld] move_unit: unit={unitId} -> {regionId}:{locationId}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                // wait_unit: 대기 Job 삽입
                morldModule.ModuleDict["wait_unit"] = new PyBuiltinFunction("wait_unit", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("wait_unit(unit_id, duration) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    int duration = args[1].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        // JobList에 대기 Job 삽입
                        var job = new Morld.Job
                        {
                            Name = "대기",
                            Action = "stay",
                            Duration = duration
                        };
                        unit.InsertJobWithClear(job);
                        Godot.GD.Print($"[morld] wait_unit: unit={unitId}, duration={duration}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                // set_unit_prop: 단일 Prop 설정 ("타입:이름" 형식)
                morldModule.ModuleDict["set_unit_prop"] = new PyBuiltinFunction("set_unit_prop", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("set_unit_prop(unit_id, prop_name, value) requires 3 arguments");

                    int unitId = args[0].ToInt();
                    string propName = args[1].AsString();
                    int value = args[2].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        unit.TraversalContext.SetProp(propName, value);
                        Godot.GD.Print($"[morld] set_unit_prop: unit={unitId}, {propName}={value}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                // get_unit_prop: Prop 값 조회 ("타입:이름" 형식)
                morldModule.ModuleDict["get_unit_prop"] = new PyBuiltinFunction("get_unit_prop", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("get_unit_prop(unit_id, prop_name) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    string propName = args[1].AsString();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        return new PyInt(unit.TraversalContext.GetProp(propName));
                    }
                    return new PyInt(0);
                });

                // set_unit_mood: 감정 상태 설정
                morldModule.ModuleDict["set_unit_mood"] = new PyBuiltinFunction("set_unit_mood", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_unit_mood(unit_id, moods) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    var moods = args[1] is PyList moodList ? PyListToStringList(moodList) : null;

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    if (moods != null)
                    {
                        var unit = _unitSystem.FindUnit(unitId);
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

                // set_unit: 유닛 필드 설정
                // set_unit(unit_id, field, value)
                // 지원 필드: "name"
                morldModule.ModuleDict["set_unit"] = new PyBuiltinFunction("set_unit", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("set_unit(unit_id, field, value) requires 3 arguments");

                    int unitId = args[0].ToInt();
                    string field = args[1].AsString();
                    var value = args[2];

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null)
                        return PyBool.False;

                    switch (field)
                    {
                        case "name":
                            unit.Name = value.AsString();
                            Godot.GD.Print($"[morld] set_unit: unit={unitId}, name={value.AsString()}");
                            return PyBool.True;
                        default:
                            throw PyTypeError.Create($"set_unit: unknown field '{field}'");
                    }
                });

                // get_unit_props_by_type: 특정 타입의 Prop만 조회
                // 예: get_unit_props_by_type(unit_id, "스탯") → {"힘": 10, "민첩": 8}
                morldModule.ModuleDict["get_unit_props_by_type"] = new PyBuiltinFunction("get_unit_props_by_type", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("get_unit_props_by_type(unit_id, type) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    string type = args[1].AsString();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        var result = new PyDict();
                        foreach (var (name, value) in unit.TraversalContext.Props.GetNamesByType(type))
                        {
                            result.SetItem(new PyString(name), new PyInt(value));
                        }
                        return result;
                    }
                    return new PyDict();
                });

                // get_unit_prop_types: 유닛이 가진 모든 Prop 타입 조회
                // 예: get_unit_prop_types(unit_id) → ["스탯", "상태", "스킬"]
                morldModule.ModuleDict["get_unit_prop_types"] = new PyBuiltinFunction("get_unit_prop_types", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_unit_prop_types(unit_id) requires 1 argument");

                    var result = new PyList();
                    int unitId = args[0].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        foreach (var type in unit.TraversalContext.Props.GetTypes())
                        {
                            result.Append(new PyString(type));
                        }
                        return result;
                    }
                    return result;
                });

                // get_unit_actual_props: 아이템 효과가 반영된 최종 Prop (특정 타입만 필터링 가능)
                // 예: get_unit_actual_props(unit_id, ["스탯", "상태"]) → {"스탯:힘": 15, "상태:피로": 3}
                morldModule.ModuleDict["get_unit_actual_props"] = new PyBuiltinFunction("get_unit_actual_props", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_unit_actual_props(unit_id, types=None) requires at least 1 argument");

                    int unitId = args[0].ToInt();
                    List<string>? types = null;

                    // types 파라미터 파싱
                    if (args.Length >= 2 && args[1] is PyList typeList)
                    {
                        types = new List<string>();
                        for (int i = 0; i < typeList.Length(); i++)
                        {
                            var item = typeList.GetItem(i);
                            types.Add(item.AsString());
                        }
                    }

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                    var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        var inventory = _inventorySystem.GetUnitInventory(unitId);
                        var equippedItems = _inventorySystem.GetUnitEquippedItems(unitId);

                        Morld.TraversalContext actualProps;
                        if (types != null)
                            actualProps = unit.GetActualPropsEx(types, _itemSystem, inventory, equippedItems);
                        else
                            actualProps = unit.GetActualProps(_itemSystem, inventory, equippedItems);

                        var result = new PyDict();
                        foreach (var kv in actualProps.Props)
                        {
                            result.SetItem(new PyString(kv.Key.FullName), new PyInt(kv.Value));
                        }
                        return result;
                    }
                    return new PyDict();
                });

                // sit_on: 캐릭터를 오브젝트의 좌석에 앉히기
                // sit_on(unit_id, object_id, seat_name) → True/False
                morldModule.ModuleDict["sit_on"] = new PyBuiltinFunction("sit_on", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("sit_on(unit_id, object_id, seat_name) requires 3 arguments");

                    int unitId = args[0].ToInt();
                    int objectId = args[1].ToInt();
                    string seatName = args[2].AsString();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    var obj = _unitSystem.FindUnit(objectId);

                    if (unit != null && obj != null && obj.IsObject)
                    {
                        // 1. 캐릭터가 이미 앉아있는지 확인
                        var seatedOn = unit.TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
                        if (seatedOn.Prop.IsValid)
                        {
                            Godot.GD.PrintErr($"[morld] sit_on: unit={unitId} is already seated");
                            return PyBool.False;
                        }

                        // 2. 좌석이 비어있는지 확인
                        var seatPropName = $"seated_by:{seatName}";
                        int seatOccupant = obj.TraversalContext.Props.Get(seatPropName);
                        if (seatOccupant != -1)
                        {
                            Godot.GD.PrintErr($"[morld] sit_on: seat {seatName} is occupied");
                            return PyBool.False;
                        }

                        // 3. 양방향 설정
                        unit.TraversalContext.Props.Set($"seated_on:{objectId}", seatName.GetHashCode());
                        obj.TraversalContext.Props.Set(seatPropName, unitId);

                        Godot.GD.Print($"[morld] sit_on: unit={unitId} sat on object={objectId}, seat={seatName}");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                // stand_up: 캐릭터를 일어나게 하기
                // stand_up(unit_id) → True/False
                morldModule.ModuleDict["stand_up"] = new PyBuiltinFunction("stand_up", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("stand_up(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        // 1. seated_on에서 오브젝트 ID 추출
                        var seatedOn = unit.TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
                        if (!seatedOn.Prop.IsValid)
                        {
                            Godot.GD.PrintErr($"[morld] stand_up: unit={unitId} is not seated");
                            return PyBool.False;
                        }

                        // Prop 이름에서 오브젝트 ID 추출
                        if (int.TryParse(seatedOn.Prop.Name, out int objectId))
                        {
                            var obj = _unitSystem.FindUnit(objectId);
                            if (obj != null)
                            {
                                // 2. 오브젝트에서 해당 좌석 찾기
                                var seatProps = obj.TraversalContext.Props.GetByType("seated_by");
                                foreach (var (prop, value) in seatProps)
                                {
                                    if (value == unitId)
                                    {
                                        obj.TraversalContext.Props.Set(prop, -1);
                                        break;
                                    }
                                }
                            }
                        }

                        // 3. 캐릭터 seated_on 제거
                        unit.TraversalContext.Props.Remove(seatedOn.Prop);

                        Godot.GD.Print($"[morld] stand_up: unit={unitId} stood up");
                        return PyBool.True;
                    }
                    return PyBool.False;
                });

                // is_seated: 캐릭터가 앉아있는지 확인
                // is_seated(unit_id) → object_id or -1
                morldModule.ModuleDict["is_seated"] = new PyBuiltinFunction("is_seated", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("is_seated(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit != null)
                    {
                        var seatedOn = unit.TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
                        if (seatedOn.Prop.IsValid && int.TryParse(seatedOn.Prop.Name, out int objectId))
                        {
                            return new PyInt(objectId);
                        }
                    }
                    return new PyInt(-1);
                });

                // ===== Vehicle APIs (운전 시스템) =====

                // can_drive: 유닛이 현재 운전 가능한 상태인지 확인
                // can_drive(unit_id) → True/False
                morldModule.ModuleDict["can_drive"] = new PyBuiltinFunction("can_drive", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("can_drive(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null) return PyBool.False;

                    var actionSystem = _hub.GetSystem("actionSystem") as ActionSystem;
                    if (actionSystem == null) return PyBool.False;

                    return actionSystem.CanDrive(unit) ? PyBool.True : PyBool.False;
                });

                // get_drivable_destinations: 운전 가능한 목적지 목록 가져오기
                // get_drivable_destinations(unit_id) → [{region_id, location_id, name, travel_time}, ...]
                morldModule.ModuleDict["get_drivable_destinations"] = new PyBuiltinFunction("get_drivable_destinations", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_drivable_destinations(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    var result = new PyList();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null) return result;

                    var actionSystem = _hub.GetSystem("actionSystem") as ActionSystem;
                    if (actionSystem == null) return result;

                    var destinations = actionSystem.GetDrivableDestinations(unit);
                    foreach (var (regionId, locationId, name, travelTime) in destinations)
                    {
                        var dict = new PyDict();
                        dict.SetItem(new PyString("region_id"), new PyInt(regionId));
                        dict.SetItem(new PyString("location_id"), new PyInt(locationId));
                        dict.SetItem(new PyString("name"), new PyString(name));
                        dict.SetItem(new PyString("travel_time"), new PyInt(travelTime));
                        result.Append(dict);
                    }

                    return result;
                });

                // drive_to: 차량 운전하여 목적지로 이동
                // drive_to(unit_id, region_id, location_id) → {success, message, time_consumed}
                morldModule.ModuleDict["drive_to"] = new PyBuiltinFunction("drive_to", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("drive_to(unit_id, region_id, location_id) requires 3 arguments");

                    int unitId = args[0].ToInt();
                    int regionId = args[1].ToInt();
                    int locationId = args[2].ToInt();

                    var resultDict = new PyDict();
                    resultDict.SetItem(new PyString("success"), PyBool.False);
                    resultDict.SetItem(new PyString("message"), new PyString("Unknown error"));
                    resultDict.SetItem(new PyString("time_consumed"), new PyInt(0));

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null)
                    {
                        resultDict.SetItem(new PyString("message"), new PyString($"Unit {unitId} not found"));
                        return resultDict;
                    }

                    var actionSystem = _hub.GetSystem("actionSystem") as ActionSystem;
                    if (actionSystem == null)
                    {
                        resultDict.SetItem(new PyString("message"), new PyString("ActionSystem not found"));
                        return resultDict;
                    }

                    var result = actionSystem.ApplyDriveAction(unit, regionId, locationId);

                    resultDict.SetItem(new PyString("success"), result.Success ? PyBool.True : PyBool.False);
                    resultDict.SetItem(new PyString("message"), new PyString(result.Message));
                    resultDict.SetItem(new PyString("time_consumed"), new PyInt(result.TimeConsumed));

                    if (result.Success)
                    {
                        Godot.GD.Print($"[morld] drive_to: unit={unitId} drove to region={regionId}, location={locationId}");
                    }
                    else
                    {
                        Godot.GD.PrintErr($"[morld] drive_to: failed - {result.Message}");
                    }

                    return resultDict;
                });

                // set_unit_activity: [DEPRECATED] JobList 기반에서는 activity가 CurrentJob.Name으로 자동 결정됨
                // 스케줄의 activity 필드를 통해 설정하세요
                morldModule.ModuleDict["set_unit_activity"] = new PyBuiltinFunction("set_unit_activity", args =>
                {
                    Godot.GD.PrintErr("[morld] set_unit_activity is DEPRECATED. Activity is now determined by CurrentJob.Name from schedule.");
                    return PyBool.False;
                });

                // get_game_time: 현재 게임 시간 (분 단위) 반환
                morldModule.ModuleDict["get_game_time"] = new PyBuiltinFunction("get_game_time", args =>
                {
                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                    var time = _worldSystem.GetTime();
                    return new PyInt(time.MinuteOfDay);
                });

                // set_region_weather: 지역 날씨 설정 (기존 set_weather와 동일하지만 명확한 이름)
                morldModule.ModuleDict["set_region_weather"] = new PyBuiltinFunction("set_region_weather", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("set_region_weather(region_id, weather) requires 2 arguments");

                    int regionId = args[0].ToInt();
                    string weather = args[1].AsString();

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                    var terrain = _worldSystem.GetTerrain();
                    var region = terrain.GetRegion(regionId);
                    if (region != null)
                    {
                        region.CurrentWeather = weather;
                        Godot.GD.Print($"[morld] set_region_weather: region={regionId}, weather={weather}");
                        return PyBool.True;
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

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;

                    var terrain = _worldSystem.GetTerrain();
                    var from = new Morld.LocationRef(fromRegion, fromLoc);
                    var to = new Morld.LocationRef(toRegion, toLoc);

                    // 유닛 기반 경로 탐색 (조건 체크용)
                    Morld.Unit unit = null;
                    if (unitId.HasValue)
                        unit = _unitSystem.FindUnit(unitId.Value);

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

                // get_unit_location(unit_id) - 유닛 현재 위치 조회
                // 반환: (region_id, location_id) 또는 None
                morldModule.ModuleDict["get_unit_location"] = new PyBuiltinFunction("get_unit_location", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("get_unit_location(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null)
                        return PyNone.Instance;

                    return new PyTuple(new PyObject[] {
                        new PyInt(unit.CurrentLocation.RegionId),
                        new PyInt(unit.CurrentLocation.LocalId)
                    });
                });

                // clear_route(unit_id) - 경로 초기화
                morldModule.ModuleDict["clear_route"] = new PyBuiltinFunction("clear_route", args =>
                {
                    if (args.Length < 1)
                        throw PyTypeError.Create("clear_route(unit_id) requires 1 argument");

                    int unitId = args[0].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null)
                        return PyBool.False;

                    unit.ClearRoute();
                    return PyBool.True;
                });

                // ========================================
                // JobList API
                // ========================================

                // fill_schedule_jobs_from(unit_id, schedule_list) - Python에서 전달한 스케줄로 JobList 채우기
                // schedule_list: [{"name": str, "region_id": int, "location_id": int, "start": int, "end": int, "activity": str}, ...]
                morldModule.ModuleDict["fill_schedule_jobs_from"] = new PyBuiltinFunction("fill_schedule_jobs_from", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("fill_schedule_jobs_from(unit_id, schedule_list) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    var scheduleArg = args[1];

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null)
                        return PyBool.False;

                    // Python 리스트를 DailySchedule로 변환
                    var schedule = PyListToDailySchedule(scheduleArg);
                    if (schedule == null)
                        return PyBool.False;

                    var time = _worldSystem.GetTime();
                    var currentLoc = unit.CurrentLocation;
                    unit.JobList.FillFromSchedule(schedule, time.MinuteOfDay, 1440, currentLoc.RegionId, currentLoc.LocalId);
                    return PyBool.True;
                });

                // insert_job(unit_id, job_dict) - Job 삽입 (기존 Job 제거 후)
                // job_dict: {"name": str, "action": str, "region_id": int, "location_id": int, "duration": int, "target_id": int?}
                morldModule.ModuleDict["insert_job"] = new PyBuiltinFunction("insert_job", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("insert_job(unit_id, job_dict) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    var jobArg = args[1];

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null)
                        return PyBool.False;

                    var job = PyDictToJob(jobArg);
                    if (job == null)
                        return PyBool.False;

                    unit.InsertJobWithClear(job);
                    return PyBool.True;
                });

                // insert_job_override(unit_id, job_dict) - Job Override 삽입 (기존 Job 잘라내고 끼워넣기)
                morldModule.ModuleDict["insert_job_override"] = new PyBuiltinFunction("insert_job_override", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("insert_job_override(unit_id, job_dict) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    var jobArg = args[1];

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null)
                        return PyBool.False;

                    var job = PyDictToJob(jobArg);
                    if (job == null)
                        return PyBool.False;

                    unit.InsertJobOverride(job);
                    return PyBool.True;
                });

                // insert_job_merge(unit_id, job_dict) - Job Merge 삽입 (기존 Job 우선, 빈 공간에 끼워넣기)
                morldModule.ModuleDict["insert_job_merge"] = new PyBuiltinFunction("insert_job_merge", args =>
                {
                    if (args.Length < 2)
                        throw PyTypeError.Create("insert_job_merge(unit_id, job_dict) requires 2 arguments");

                    int unitId = args[0].ToInt();
                    var jobArg = args[1];

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null)
                        return PyBool.False;

                    var job = PyDictToJob(jobArg);
                    if (job == null)
                        return PyBool.False;

                    unit.InsertJobMerge(job);
                    return PyBool.True;
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
                    return PyBool.True;
                });

                // get_current_job(unit_id) - 현재 Job 조회
                // 반환: {"name": str, "action": str, "region_id": int, "location_id": int, "duration": int, "target_id": int?} 또는 None
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

                    return JobToPyDict(job);
                });

                // === 챕터 전환 API ===

                // clear_world() - 모든 게임 데이터 초기화 (챕터 전환 시 사용)
                morldModule.ModuleDict["clear_world"] = new PyBuiltinFunction("clear_world", args =>
                {
                    Godot.GD.Print("[morld] clear_world: Clearing all game data...");

                    var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                    var _eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;

                    // 1. Terrain 초기화 (Region, Location, Edge 모두 제거)
                    _worldSystem?.ClearTerrain();

                    // 2. Unit 초기화 (Player, NPC, Object 모두 제거)
                    _unitSystem?.Clear();

                    // 3. Inventory 초기화
                    _inventorySystem?.Clear();

                    // 4. EventSystem 상태 초기화
                    _eventSystem?.ClearState();

                    // 5. Python 측 캐시 초기화 (assets.characters._instances 등)
                    try
                    {
                        Execute("from assets.characters import clear_instances; clear_instances()");
                    }
                    catch { /* 함수가 없으면 무시 */ }

                    try
                    {
                        Execute("from think import clear_agents; clear_agents()");
                    }
                    catch { /* 함수가 없으면 무시 */ }

                    // 6. ID Generator 리셋
                    IdGenerator.Reset();

                    Godot.GD.Print("[morld] clear_world: Done.");
                    return PyBool.True;
                });

                // reinitialize_locations() - EventSystem 위치 재초기화 (챕터 로드 후 호출)
                morldModule.ModuleDict["reinitialize_locations"] = new PyBuiltinFunction("reinitialize_locations", args =>
                {
                    var _eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;
                    _eventSystem?.InitializeLocations();
                    Godot.GD.Print("[morld] reinitialize_locations: Done.");
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
        /// 생존 시스템 시간 경과 처리 (advance_time에서 호출)
        /// Python survival.process_time_elapsed(player_id, minutes) 호출
        /// </summary>
        private void ProcessSurvivalTimeElapsed(int minutes)
        {
            try
            {
                var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
                if (playerSystem == null)
                    return;

                int playerId = playerSystem.PlayerId;

                // Python survival 모듈의 process_time_elapsed 호출
                Execute($"import survival; survival.process_time_elapsed({playerId}, {minutes})");
            }
            catch (System.Exception)
            {
                // survival 모듈이 없거나 에러 시 무시 (아직 구현되지 않은 시나리오 호환)
            }
        }
    }
}
