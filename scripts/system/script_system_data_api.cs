using SharpPy;
using Morld;
using System.Collections.Generic;

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

                // 카테고리별 API 등록
                RegisterTerrainAPI(morldModule);
                RegisterTimeAPI(morldModule);
                RegisterWeatherAPI(morldModule);
                RegisterItemAPI(morldModule);
                RegisterUnitAPI(morldModule);
                RegisterClearAPI(morldModule);
                RegisterActionPropsAPI(morldModule);
                RegisterUnitCommandAPI(morldModule);
                RegisterSeatAPI(morldModule);
                RegisterVehicleAPI(morldModule);
                RegisterTimeQueryAPI(morldModule);
                RegisterPathAPI(morldModule);
                RegisterJobListAPI(morldModule);
                RegisterChapterAPI(morldModule);
                RegisterGameControlAPI(morldModule);

                // === 초기화 완료 플래그 ===
                morldModule.ModuleDict["data_api_ready"] = PyBool.True;

                Godot.GD.Print("[ScriptSystem] Data manipulation API registered successfully.");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] RegisterDataManipulationAPI error: {ex.Message}");
            }
        }

        #region Terrain API (Region/Location/Gate)

        /// <summary>
        /// Terrain API 등록 (Region, Location, Gate)
        /// </summary>
        private void RegisterTerrainAPI(PyModule morldModule)
        {
            // add_region
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

            // add_location (Pi-World 2D 속성 확장)
            // add_location(region_id, local_id, name, stay_duration=0, indoor=True, owner=None,
            //              describe_text=None, ground_id=None, geometry="line", length=0, base_speed=10)
            morldModule.ModuleDict["add_location"] = new PyBuiltinFunction("add_location", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("add_location(region_id, local_id, name, stay_duration=0, indoor=True, owner=None, describe_text=None, ground_id=None, geometry='line', length=0, base_speed=10) requires at least 3 arguments");

                int regionId = args[0].ToInt();
                int localId = args[1].ToInt();
                string name = args[2].AsString();
                int stayDuration = args.Length >= 4 ? args[3].ToInt() : 0;
                bool isIndoor = args.Length >= 5 ? args[4].IsTrue() : true;
                string owner = args.Length >= 6 && args[5] is PyString ownerStr ? ownerStr.Value : null;
                var describeText = args.Length >= 7 && args[6] is PyDict descDict
                    ? PyDictToStringDict(descDict)
                    : null;
                int? groundId = args.Length >= 8 && args[7] != PyNone.Instance ? args[7].ToInt() : null;

                // Pi-World 2D 속성
                string geometry = args.Length >= 9 ? args[8].AsString() : "line";
                float length = args.Length >= 10 ? (float)args[9].ToFloat() : 0f;
                float baseSpeed = args.Length >= 11 ? (float)args[10].ToFloat() : 10f;

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
                    location.GroundUnitId = groundId;

                    // Pi-World 2D 속성 설정
                    location.Geometry = geometry.ToLower() == "ring"
                        ? Morld.LocationGeometry.Ring
                        : Morld.LocationGeometry.Line;
                    location.Length = length;
                    location.BaseSpeed = baseSpeed;

                    // describe_text 설정
                    if (describeText != null)
                    {
                        foreach (var (key, value) in describeText)
                        {
                            location.DescribeText[key] = value;
                        }
                    }

                    Godot.GD.Print($"[morld] add_location: region={regionId}, local={localId}, name={name}, indoor={isIndoor}, geometry={geometry}, length={length}, base_speed={baseSpeed}");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // add_region_gate
            morldModule.ModuleDict["add_region_gate"] = new PyBuiltinFunction("add_region_gate", args =>
            {
                if (args.Length < 4)
                    throw PyTypeError.Create("add_region_gate(from_region, from_local, to_region, to_local, time_ab=30, time_ba=30) requires at least 4 arguments");

                int fromRegion = args[0].ToInt();
                int fromLocal = args[1].ToInt();
                int toRegion = args[2].ToInt();
                int toLocal = args[3].ToInt();
                int timeAB = args.Length >= 5 ? args[4].ToInt() : 30;
                int timeBA = args.Length >= 6 ? args[5].ToInt() : timeAB;

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                var terrain = _worldSystem.GetTerrain();
                // RegionGate(id, regionIdA, localIdA, regionIdB, localIdB) 생성자 사용
                var regionGate = new Morld.RegionGate(
                    terrain.RegionGates.Count,
                    fromRegion, fromLocal,
                    toRegion, toLocal
                );
                regionGate.SetTravelTime(timeAB, timeBA);
                terrain.AddRegionGate(regionGate);
                Godot.GD.Print($"[morld] add_region_gate: {fromRegion}:{fromLocal} <-> {toRegion}:{toLocal}");
                return PyBool.True;
            });

            // add_gate: Pi-World Gate 추가 (Location 간 연결)
            // add_gate(region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x,
            //          arrival_y=0, conditions_forward=None, conditions_backward=None, is_blocked=False, name="", travel_time=0)
            morldModule.ModuleDict["add_gate"] = new PyBuiltinFunction("add_gate", args =>
            {
                if (args.Length < 7)
                    throw PyTypeError.Create("add_gate(region_id, location_id, gate_id, x, connected_region, connected_location, arrival_x, arrival_y=0, conditions_forward=None, conditions_backward=None, is_blocked=False, name='') requires at least 7 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();
                int gateId = args[2].ToInt();
                float x = (float)args[3].ToFloat();
                int connectedRegion = args[4].ToInt();
                int connectedLocation = args[5].ToInt();
                float arrivalX = (float)args[6].ToFloat();
                float arrivalY = args.Length >= 8 && args[7] is not PyDict ? (float)args[7].ToFloat() : 0f;

                // arrival_y가 없거나 dict이면 다음 파라미터가 conditions
                int conditionsStartIdx = args.Length >= 8 && args[7] is PyDict ? 7 : 8;
                var conditionsForward = args.Length > conditionsStartIdx && args[conditionsStartIdx] is PyDict condFwdDict
                    ? PyDictToIntDict(condFwdDict)
                    : null;
                var conditionsBackward = args.Length > conditionsStartIdx + 1 && args[conditionsStartIdx + 1] is PyDict condBwdDict
                    ? PyDictToIntDict(condBwdDict)
                    : null;
                bool isBlocked = args.Length > conditionsStartIdx + 2 && args[conditionsStartIdx + 2].IsTrue();
                string name = args.Length > conditionsStartIdx + 3 && args[conditionsStartIdx + 3] is PyString nameStr ? nameStr.Value : "";
                int travelTime = args.Length > conditionsStartIdx + 4 ? args[conditionsStartIdx + 4].ToInt() : 0;

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var region = terrain.GetRegion(regionId);

                if (region != null)
                {
                    var gate = region.AddGate(locationId, gateId, x, connectedRegion, connectedLocation, arrivalX, arrivalY);
                    gate.Name = name;
                    gate.TravelTime = travelTime;
                    gate.IsBlocked = isBlocked;

                    if (conditionsForward != null)
                    {
                        foreach (var (key, value) in conditionsForward)
                            gate.AddConditionForward(key, value);
                    }
                    if (conditionsBackward != null)
                    {
                        foreach (var (key, value) in conditionsBackward)
                            gate.AddConditionBackward(key, value);
                    }

                    Godot.GD.Print($"[morld] add_gate: {regionId}:{locationId}:Gate{gateId}(X={x}) -> {connectedRegion}:{connectedLocation}(X={arrivalX})");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // region_exists: Region 존재 여부 확인 (챕터별 Region 선택적 로드용)
            morldModule.ModuleDict["region_exists"] = new PyBuiltinFunction("region_exists", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("region_exists(region_id) requires 1 argument");

                int regionId = args[0].ToInt();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                return terrain.GetRegion(regionId) != null ? PyBool.True : PyBool.False;
            });

            // set_location_ground_id: Location의 바닥 오브젝트 ID 설정
            morldModule.ModuleDict["set_location_ground_id"] = new PyBuiltinFunction("set_location_ground_id", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("set_location_ground_id(region_id, location_id, ground_unit_id) requires 3 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();
                int? groundUnitId = args[2] != PyNone.Instance ? args[2].ToInt() : null;

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var location = terrain.GetLocation(new Morld.LocationRef(regionId, locationId));

                if (location != null)
                {
                    location.GroundUnitId = groundUnitId;
                    Godot.GD.Print($"[morld] set_location_ground_id: {regionId}:{locationId} -> ground_id={groundUnitId?.ToString() ?? "null"}");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // get_location_ground_id: Location의 바닥 오브젝트 ID 조회
            morldModule.ModuleDict["get_location_ground_id"] = new PyBuiltinFunction("get_location_ground_id", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("get_location_ground_id(region_id, location_id) requires 2 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var location = terrain.GetLocation(new Morld.LocationRef(regionId, locationId));

                if (location != null && location.GroundUnitId.HasValue)
                {
                    return new PyInt(location.GroundUnitId.Value);
                }
                return PyNone.Instance;
            });

            // get_region_info: Region 정보 조회 (지도 기능용)
            // 반환: {"id", "name", "locations": [{"id", "name", "gates": [...], "region_gates": [(to_region, to_local, region_name), ...]}], ...}
            morldModule.ModuleDict["get_region_info"] = new PyBuiltinFunction("get_region_info", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_region_info(region_id) requires 1 argument");

                int regionId = args[0].ToInt();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var region = terrain.GetRegion(regionId);

                if (region == null)
                    return PyNone.Instance;

                var result = new PyDict();
                result.SetItem(new PyString("id"), new PyInt(region.Id));
                result.SetItem(new PyString("name"), new PyString(region.Name ?? ""));

                // Location 목록
                var locationsList = new PyList();
                foreach (var location in region.Locations)
                {
                    var locDict = new PyDict();
                    locDict.SetItem(new PyString("id"), new PyInt(location.LocalId));
                    locDict.SetItem(new PyString("name"), new PyString(location.Name ?? ""));
                    locDict.SetItem(new PyString("is_indoor"), location.IsIndoor ? PyBool.True : PyBool.False);

                    // Pi-World: Location 2D 속성
                    locDict.SetItem(new PyString("length"), new PyFloat(location.Length));
                    locDict.SetItem(new PyString("geometry"), new PyString(location.Geometry.ToString().ToLower()));
                    locDict.SetItem(new PyString("base_speed"), new PyFloat(location.BaseSpeed));

                    // 이 Location에서 나가는 Gate 목록 (Pi-World)
                    var gatesList = new PyList();
                    foreach (var gate in region.GetGates(location.LocalId))
                    {
                        var gateDict = new PyDict();
                        gateDict.SetItem(new PyString("id"), new PyInt(gate.Id));
                        gateDict.SetItem(new PyString("x"), new PyFloat(gate.X));
                        gateDict.SetItem(new PyString("connected_region"), new PyInt(gate.ConnectedLocation.RegionId));
                        gateDict.SetItem(new PyString("connected_local"), new PyInt(gate.ConnectedLocation.LocalId));
                        gateDict.SetItem(new PyString("arrival_x"), new PyFloat(gate.ArrivalX));
                        gateDict.SetItem(new PyString("arrival_y"), new PyFloat(gate.ArrivalY));
                        gateDict.SetItem(new PyString("is_blocked"), gate.IsBlocked ? PyBool.True : PyBool.False);
                        gatesList.Append(gateDict);
                    }
                    locDict.SetItem(new PyString("gates"), gatesList);

                    // 이 Location에서 다른 Region으로 가는 RegionGate 목록
                    var regionGatesList = new PyList();
                    foreach (var regionGate in terrain.RegionGates)
                    {
                        int? toRegionId = null;
                        int? toLocalId = null;

                        if (regionGate.LocationA.RegionId == regionId && regionGate.LocationA.LocalId == location.LocalId)
                        {
                            toRegionId = regionGate.LocationB.RegionId;
                            toLocalId = regionGate.LocationB.LocalId;
                        }
                        else if (regionGate.LocationB.RegionId == regionId && regionGate.LocationB.LocalId == location.LocalId)
                        {
                            toRegionId = regionGate.LocationA.RegionId;
                            toLocalId = regionGate.LocationA.LocalId;
                        }

                        if (toRegionId.HasValue && toLocalId.HasValue)
                        {
                            var targetRegion = terrain.GetRegion(toRegionId.Value);
                            var regionName = targetRegion?.Name ?? "";
                            var regionGateTuple = new PyTuple(new PyObject[] {
                                new PyInt(toRegionId.Value),
                                new PyInt(toLocalId.Value),
                                new PyString(regionName)
                            });
                            regionGatesList.Append(regionGateTuple);
                        }
                    }
                    locDict.SetItem(new PyString("region_gates"), regionGatesList);

                    locationsList.Append(locDict);
                }
                result.SetItem(new PyString("locations"), locationsList);

                return result;
            });

            // get_travel_time: 두 위치 간 이동 시간 계산 (경로 탐색 포함)
            morldModule.ModuleDict["get_travel_time"] = new PyBuiltinFunction("get_travel_time", args =>
            {
                if (args.Length < 4)
                    throw PyTypeError.Create("get_travel_time(from_region, from_loc, to_region, to_loc, unit_id=None) requires at least 4 arguments");

                int fromRegion = args[0].ToInt();
                int fromLoc = args[1].ToInt();
                int toRegion = args[2].ToInt();
                int toLoc = args[3].ToInt();
                int? unitId = args.Length > 4 && args[4] != PyNone.Instance ? args[4].ToInt() : null;

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;

                var terrain = _worldSystem.GetTerrain();
                var from = new Morld.LocationRef(fromRegion, fromLoc);
                var to = new Morld.LocationRef(toRegion, toLoc);

                // 이미 같은 위치면 0
                if (from == to)
                    return new PyInt(0);

                // 유닛 기반 경로 탐색 (조건 체크용)
                Morld.TraversalContext? props = null;
                if (unitId.HasValue)
                {
                    var unit = _unitSystem.FindUnit(unitId.Value);
                    if (unit != null)
                    {
                        var inventory = _inventorySystem.GetUnitInventory(unit.Id);
                        var equippedItems = _inventorySystem.GetUnitEquippedItems(unit.Id);
                        props = unit.GetActualProps(_itemSystem, inventory, equippedItems);
                    }
                }

                var pathResult = terrain.FindPath(from, to, props);

                if (pathResult == null || !pathResult.Found || pathResult.Path.Count < 2)
                    return new PyInt(-1);

                // 유닛이 있으면 현재 X 좌표와 이동 속도 사용
                float startX = 0f;
                float speedModifier = 1.0f;
                if (unitId.HasValue)
                {
                    var unit = _unitSystem.FindUnit(unitId.Value);
                    if (unit != null)
                    {
                        startX = unit.PositionX;
                        var inventory = _inventorySystem.GetUnitInventory(unit.Id);
                        var equippedItems = _inventorySystem.GetUnitEquippedItems(unit.Id);
                        int movementSpeedPercent = unit.GetMovementSpeed(_itemSystem, inventory, equippedItems);
                        speedModifier = movementSpeedPercent / 100f;
                    }
                }

                return new PyInt(terrain.CalculatePathTravelTime(pathResult, startX, speedModifier));
            });
        }

        #endregion

        #region Time API (GameTime, TimeFrozen)

        /// <summary>
        /// Time API 등록 (GameTime 설정/조작, 시간 정지)
        /// </summary>
        private void RegisterTimeAPI(PyModule morldModule)
        {
            // set_time
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

            // advance_time
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

            // set_time_frozen
            morldModule.ModuleDict["set_time_frozen"] = new PyBuiltinFunction("set_time_frozen", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("set_time_frozen(frozen) requires 1 argument");

                bool frozen = args[0].IsTrue();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                _worldSystem.SetTimeFrozen(frozen);

                return PyBool.True;
            });

            // is_time_frozen
            morldModule.ModuleDict["is_time_frozen"] = new PyBuiltinFunction("is_time_frozen", args =>
            {
                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                return _worldSystem.IsTimeFrozen() ? PyBool.True : PyBool.False;
            });

            // ========================================
            // 자동 시간 흐름 API
            // ========================================

            // set_auto_time_flow: 자동 시간 흐름 활성화/비활성화
            morldModule.ModuleDict["set_auto_time_flow"] = new PyBuiltinFunction("set_auto_time_flow", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("set_auto_time_flow(enabled) requires 1 argument");

                bool enabled = args[0].IsTrue();
                var _autoTimeFlowSystem = this._hub.GetSystem("autoTimeFlowSystem") as AutoTimeFlowSystem;

                if (_autoTimeFlowSystem == null)
                    return PyBool.False;

                if (enabled)
                    _autoTimeFlowSystem.Enable();
                else
                    _autoTimeFlowSystem.Disable();

                return PyBool.True;
            });

            // is_auto_time_flow: 자동 시간 흐름 활성화 여부 반환
            morldModule.ModuleDict["is_auto_time_flow"] = new PyBuiltinFunction("is_auto_time_flow", args =>
            {
                var _autoTimeFlowSystem = this._hub.GetSystem("autoTimeFlowSystem") as AutoTimeFlowSystem;

                if (_autoTimeFlowSystem == null)
                    return PyBool.False;

                return _autoTimeFlowSystem.Enabled ? PyBool.True : PyBool.False;
            });

            // set_auto_time_flow_interval: 자동 시간 흐름 간격 설정
            // real_seconds: 실시간 간격 (초)
            // game_minutes: 게임 시간 간격 (분)
            morldModule.ModuleDict["set_auto_time_flow_interval"] = new PyBuiltinFunction("set_auto_time_flow_interval", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("set_auto_time_flow_interval(real_seconds, game_minutes) requires 2 arguments");

                float realSeconds = (float)args[0].ToFloat();
                int gameMinutes = args[1].ToInt();

                var _autoTimeFlowSystem = this._hub.GetSystem("autoTimeFlowSystem") as AutoTimeFlowSystem;

                if (_autoTimeFlowSystem == null)
                    return PyBool.False;

                _autoTimeFlowSystem.RealTimeIntervalSeconds = realSeconds;
                _autoTimeFlowSystem.GameTimeIntervalMinutes = gameMinutes;

                Godot.GD.Print($"[morld] set_auto_time_flow_interval: {realSeconds}s -> {gameMinutes}min");
                return PyBool.True;
            });

            // reset_auto_time_flow_timer: 자동 시간 흐름 타이머 리셋
            morldModule.ModuleDict["reset_auto_time_flow_timer"] = new PyBuiltinFunction("reset_auto_time_flow_timer", args =>
            {
                var _autoTimeFlowSystem = this._hub.GetSystem("autoTimeFlowSystem") as AutoTimeFlowSystem;

                if (_autoTimeFlowSystem == null)
                    return PyBool.False;

                _autoTimeFlowSystem.ResetTimer();
                return PyBool.True;
            });

            // get_auto_time_flow_interval: 자동 시간 흐름 간격 조회
            // 반환: (real_seconds, game_minutes) 튜플
            morldModule.ModuleDict["get_auto_time_flow_interval"] = new PyBuiltinFunction("get_auto_time_flow_interval", args =>
            {
                var _autoTimeFlowSystem = this._hub.GetSystem("autoTimeFlowSystem") as AutoTimeFlowSystem;

                if (_autoTimeFlowSystem == null)
                    return new PyTuple(new PyObject[] { new PyFloat(5.0), new PyInt(1) });

                return new PyTuple(new PyObject[] {
                    new PyFloat(_autoTimeFlowSystem.RealTimeIntervalSeconds),
                    new PyInt(_autoTimeFlowSystem.GameTimeIntervalMinutes)
                });
            });

            // ========================================
            // 타이핑 효과 API
            // ========================================

            // get_typing_speed: 타이핑 속도 조회 (초당 문자 수, 0 = 즉시 출력)
            morldModule.ModuleDict["get_typing_speed"] = new PyBuiltinFunction("get_typing_speed", args =>
            {
                var _textUISystem = this._hub.GetSystem("textUISystem") as TextUISystem;

                if (_textUISystem == null)
                    return new PyInt(50); // 기본값

                return new PyInt((int)_textUISystem.TypingSpeed);
            });

            // set_typing_speed: 타이핑 속도 설정 (초당 문자 수, 0 = 즉시 출력)
            morldModule.ModuleDict["set_typing_speed"] = new PyBuiltinFunction("set_typing_speed", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("set_typing_speed(chars_per_second) requires 1 argument");

                int speed = args[0].ToInt();
                var _textUISystem = this._hub.GetSystem("textUISystem") as TextUISystem;

                if (_textUISystem == null)
                    return PyBool.False;

                _textUISystem.TypingSpeed = speed;
                Godot.GD.Print($"[morld] set_typing_speed: {speed} chars/sec");
                return PyBool.True;
            });

            // advance_time_simulate: 시간 진행 + NPC JobBehavior 실행 (연애 모드용)
            // ThinkSystem은 호출하지 않음 (NPC AI 재계산 불필요)
            // 반환: 경과된 총 시간 (분)
            morldModule.ModuleDict["advance_time_simulate"] = new PyBuiltinFunction("advance_time_simulate", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("advance_time_simulate(minutes) requires 1 argument");

                int minutes = args[0].ToInt();
                if (minutes <= 0)
                    return new PyInt(0);

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;

                var terrain = _worldSystem.GetTerrain();
                var time = _worldSystem.GetTime();

                // 시간 정지 상태면 시뮬레이션하지 않음
                if (_worldSystem.IsTimeFrozen())
                {
                    Godot.GD.Print($"[morld] advance_time_simulate: Time is frozen, skipping simulation");
                    return new PyInt(0);
                }

                // 각 유닛에 대해 이동 시뮬레이션 (플레이어 제외)
                var playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
                int playerId = playerSystem?.PlayerId ?? -1;

                foreach (var unit in _unitSystem.Units.Values)
                {
                    // 오브젝트와 플레이어는 스킵
                    if (unit.IsObject) continue;
                    if (unit.Id == playerId) continue;

                    // 현재 Job 기반 이동 처리
                    SimulateUnitMovement(unit, minutes, terrain, _itemSystem);

                    // JobList Advance (시간 경과)
                    unit.AdvanceJobs(minutes);
                }

                // GameTime 업데이트
                time.AddMinutes(minutes);

                // 생존 시스템 처리 (플레이어만)
                ProcessSurvivalTimeElapsed(minutes);

                // 시간 경과 이벤트 발생 (EventSystem으로 전달)
                var _eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;
                if (_eventSystem != null)
                {
                    _eventSystem.Enqueue(GameEvent.OnTimeElapsed(minutes));
                }

                Godot.GD.Print($"[morld] advance_time_simulate: +{minutes} minutes, NPCs simulated");
                return new PyInt(minutes);
            });
        }

        /// <summary>
        /// 유닛 이동 시뮬레이션 (advance_time_simulate용)
        /// JobBehaviorSystem.ProcessJobMovement와 유사하지만, 독립적으로 동작
        /// </summary>
        private void SimulateUnitMovement(Morld.Unit unit, int duration, Morld.Terrain terrain, ItemSystem itemSystem)
        {
            var currentJob = unit.CurrentJob;
            if (currentJob == null) return;

            // move 액션인 경우만 처리
            if (currentJob.Action == "move")
            {
                var goalLocation = currentJob.GetLocationRef();
                if (unit.CurrentLocation == goalLocation)
                    return;  // 이미 도착

                // 경로가 없으면 계산
                if (!unit.HasPlannedRoute)
                {
                    var pathResult = terrain.FindPath(unit.CurrentLocation, goalLocation, unit, itemSystem, null);
                    if (pathResult != null && pathResult.Found && pathResult.Path.Count > 1)
                    {
                        // 첫 번째 요소(현재 위치) 제외하고 경로 설정
                        var route = pathResult.Path.GetRange(1, pathResult.Path.Count - 1)
                            .Select(loc => new Morld.LocationRef(loc)).ToList();
                        unit.SetRoute(route);
                    }
                    else
                    {
                        return;  // 경로 없음
                    }
                }

                // Pi-World: 이동 처리는 JobBehaviorSystem에서 담당
                // 여기서는 CurrentMovement가 있으면 진행 처리
                if (unit.CurrentMovement != null)
                {
                    int remaining = duration;
                    while (remaining > 0 && unit.CurrentMovement != null)
                    {
                        int timeUsed = unit.CurrentMovement.Advance(remaining);
                        remaining -= timeUsed;

                        if (unit.CurrentMovement.IsComplete)
                        {
                            // 이동 완료 - 위치는 JobBehaviorSystem에서 업데이트됨
                            unit.CurrentMovement = null;

                            // 목표 도착 체크
                            if (unit.CurrentLocation == goalLocation)
                                break;
                        }
                    }
                }
            }
            else if (currentJob.Action == "follow" && currentJob.TargetId.HasValue)
            {
                // follow 액션: 대상 위치로 이동 (간소화된 처리)
                var targetUnit = (this._hub.GetSystem("unitSystem") as UnitSystem)?.FindUnit(currentJob.TargetId.Value);
                if (targetUnit != null && targetUnit.CurrentLocation != unit.CurrentLocation)
                {
                    // 즉시 대상 위치로 이동 (간소화)
                    unit.SetCurrentLocation(targetUnit.CurrentLocation);
                    unit.CurrentMovement = null;
                    unit.ClearRoute();
                }
            }
            // stay, flee 등 다른 액션은 이동 없음
        }

        #endregion

        #region Weather API

        /// <summary>
        /// Weather API 등록
        /// </summary>
        private void RegisterWeatherAPI(PyModule morldModule)
        {
            // set_weather
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

            // get_weather
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
        }

        #endregion

        #region Item API (ItemSystem)

        /// <summary>
        /// Item API 등록
        /// </summary>
        private void RegisterItemAPI(PyModule morldModule)
        {
            // add_item 함수 정의 (람다로 재사용)
            PyBuiltinFunction addItemFunc = new PyBuiltinFunction("add_item", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("add_item(id, name, passive_props=None, equip_props=None, value=0, actions=None, owner=None, unique_id=None, action_props=None) requires at least 2 arguments");

                int id = args[0].ToInt();
                string name = args[1].AsString();
                var passiveProps = args.Length >= 3 && args[2] is PyDict ptDict ? PyDictToIntDict(ptDict) : null;
                var equipProps = args.Length >= 4 && args[3] is PyDict etDict ? PyDictToIntDict(etDict) : null;
                int value = args.Length >= 5 ? args[4].ToInt() : 0;
                var actions = args.Length >= 6 && args[5] is PyList actList ? PyListToStringList(actList) : null;
                string owner = args.Length >= 7 && args[6] is PyString ownerStr ? ownerStr.Value : null;
                string uniqueId = args.Length >= 8 && args[7] is PyString uidStr ? uidStr.Value : null;
                var actionProps = args.Length >= 9 && args[8] is PyDict apDict ? PyDictToIntDict(apDict) : null;

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
                if (actionProps != null)
                    foreach (var (k, v) in actionProps) item.ActionProps[k] = v;

                _itemSystem.AddItem(item);
                Godot.GD.Print($"[morld] add_item: id={id}, name={name}, unique_id={uniqueId}");
                return PyBool.True;
            });
            morldModule.ModuleDict["add_item"] = addItemFunc;
            morldModule.ModuleDict["add_item_def"] = addItemFunc;  // 레거시 별칭
        }

        #endregion

        #region Unit API (UnitSystem)

        /// <summary>
        /// Unit API 등록 (Unit CRUD 및 Props 조작)
        /// </summary>
        private void RegisterUnitAPI(PyModule morldModule)
        {
            // add_unit
            morldModule.ModuleDict["add_unit"] = new PyBuiltinFunction("add_unit", args =>
            {
                if (args.Length < 4)
                    throw PyTypeError.Create("add_unit(id, name, region_id, location_id, type='male', actions=None, mood=None, unique_id=None, action_props=None, owner=None, item_visible=False) requires at least 4 arguments");

                int id = args[0].ToInt();
                string name = args[1].AsString();
                int regionId = args[2].ToInt();
                int locationId = args[3].ToInt();
                string type = args.Length >= 5 ? args[4].AsString() : "male";
                var actions = args.Length >= 6 && args[5] is PyList actList ? PyListToStringList(actList) : null;
                var mood = args.Length >= 7 && args[6] is PyList moodList ? PyListToStringList(moodList) : null;
                string uniqueId = args.Length >= 8 && args[7] is PyString uidStr ? uidStr.Value : null;
                var actionProps = args.Length >= 9 && args[8] is PyDict apDict ? PyDictToIntDict(apDict) : null;
                string owner = args.Length >= 10 && args[9] is PyString ownerStr ? ownerStr.Value : null;
                bool itemVisible = args.Length >= 11 && args[10].IsTrue();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = new Morld.Unit(id, name, regionId, locationId);
                unit.UniqueId = uniqueId;
                unit.Owner = owner;
                unit.ItemVisible = itemVisible;
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
                if (actionProps != null)
                    foreach (var (k, v) in actionProps) unit.ActionProps[k] = v;

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

            // set_unit_location (Pi-World 2D 위치 확장)
            // set_unit_location(unit_id, region_id, location_id, x=0, y=0)
            morldModule.ModuleDict["set_unit_location"] = new PyBuiltinFunction("set_unit_location", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("set_unit_location(unit_id, region_id, location_id, x=0, y=0) requires at least 3 arguments");

                int unitId = args[0].ToInt();
                int regionId = args[1].ToInt();
                int locationId = args[2].ToInt();
                float x = args.Length >= 4 ? (float)args[3].ToFloat() : 0f;
                float y = args.Length >= 5 ? (float)args[4].ToFloat() : 0f;

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null)
                {
                    unit.SetLocation2D(new Morld.LocationRef(regionId, locationId), x, y);
                    Godot.GD.Print($"[morld] set_unit_location: unit={unitId} -> {regionId}:{locationId} (X={x}, Y={y})");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // get_unit_position: Pi-World 2D 위치 조회
            // get_unit_position(unit_id) -> (x, y) 또는 None
            morldModule.ModuleDict["get_unit_position"] = new PyBuiltinFunction("get_unit_position", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_unit_position(unit_id) requires 1 argument");

                int unitId = args[0].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null)
                {
                    return new PyTuple(new PyObject[]
                    {
                        new PyFloat(unit.PositionX),
                        new PyFloat(unit.PositionY)
                    });
                }
                return PyNone.Instance;
            });

            // set_unit_position: Pi-World 2D 위치 설정 (Location 유지)
            // set_unit_position(unit_id, x, y=0)
            morldModule.ModuleDict["set_unit_position"] = new PyBuiltinFunction("set_unit_position", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("set_unit_position(unit_id, x, y=0) requires at least 2 arguments");

                int unitId = args[0].ToInt();
                float x = (float)args[1].ToFloat();
                float y = args.Length >= 3 ? (float)args[2].ToFloat() : 0f;

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null)
                {
                    unit.PositionX = x;
                    unit.PositionY = y;
                    // 이동 중이었다면 취소
                    unit.CurrentMovement = null;
                    Godot.GD.Print($"[morld] set_unit_position: unit={unitId} -> X={x}, Y={y}");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // set_unit_prop: 단일 Prop 설정 ("타입:이름" 형식)
            // Note: prop 값은 항상 정수. None이 전달되면 0으로 처리 (의미론적으로 동등)
            morldModule.ModuleDict["set_unit_prop"] = new PyBuiltinFunction("set_unit_prop", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("set_unit_prop(unit_id, prop_name, value) requires 3 arguments");

                int unitId = args[0].ToInt();
                string propName = args[1].AsString();
                // None은 0으로 처리 (prop은 항상 정수, 0 이하는 "없음"과 동등)
                int value = args[2] is PyNone ? 0 : args[2].ToInt();

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

            // set_unit_mood: 감정 상태 설정 (기존 mood 덮어쓰기)
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

            // add_unit_mood: 감정 상태 추가 (기존 mood 유지)
            morldModule.ModuleDict["add_unit_mood"] = new PyBuiltinFunction("add_unit_mood", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("add_unit_mood(unit_id, mood) requires 2 arguments");

                int unitId = args[0].ToInt();
                string mood = args[1].AsString();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null)
                {
                    // HashSet이므로 중복 자동 무시
                    unit.Mood.Add(mood);
                    Godot.GD.Print($"[morld] add_unit_mood: unit={unitId}, added mood={mood}");
                    return PyBool.True;
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
        }

        #endregion

        #region Clear API (챕터 전환용)

        /// <summary>
        /// Clear API 등록 (데이터 초기화)
        /// </summary>
        private void RegisterClearAPI(PyModule morldModule)
        {
            // clear_units
            morldModule.ModuleDict["clear_units"] = new PyBuiltinFunction("clear_units", args =>
            {
                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                _unitSystem.ClearUnits();
                Godot.GD.Print("[morld] clear_units: All units cleared");
                return PyBool.True;
            });

            // clear_items
            morldModule.ModuleDict["clear_items"] = new PyBuiltinFunction("clear_items", args =>
            {
                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
                _itemSystem.ClearItems();
                Godot.GD.Print("[morld] clear_items: All items cleared");
                return PyBool.True;
            });

            // clear_inventory
            morldModule.ModuleDict["clear_inventory"] = new PyBuiltinFunction("clear_inventory", args =>
            {
                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                _inventorySystem.ClearData();
                Godot.GD.Print("[morld] clear_inventory: All inventory data cleared");
                return PyBool.True;
            });

            // clear_all
            morldModule.ModuleDict["clear_all"] = new PyBuiltinFunction("clear_all", args =>
            {
                (this._hub.GetSystem("worldSystem") as WorldSystem).GetTerrain().Clear();
                (this._hub.GetSystem("unitSystem") as UnitSystem).ClearUnits();
                (this._hub.GetSystem("itemSystem") as ItemSystem).ClearItems();
                (this._hub.GetSystem("inventorySystem") as InventorySystem).ClearData();

                Godot.GD.Print("[morld] clear_all: All game data cleared");
                return PyBool.True;
            });
        }

        #endregion

        #region ActionProps API

        /// <summary>
        /// ActionProps API 등록
        /// </summary>
        private void RegisterActionPropsAPI(PyModule morldModule)
        {
            // set_item_action_prop: 아이템 ActionProps 설정
            morldModule.ModuleDict["set_item_action_prop"] = new PyBuiltinFunction("set_item_action_prop", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("set_item_action_prop(item_id, action, value) requires 3 arguments");

                int itemId = args[0].ToInt();
                string action = args[1].AsString();
                int value = args[2].ToInt();

                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
                var item = _itemSystem.FindItem(itemId);
                if (item != null)
                {
                    item.ActionProps[action] = value;
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // get_item_action_prop: 아이템 ActionProps 조회
            morldModule.ModuleDict["get_item_action_prop"] = new PyBuiltinFunction("get_item_action_prop", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("get_item_action_prop(item_id, action) requires 2 arguments");

                int itemId = args[0].ToInt();
                string action = args[1].AsString();

                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
                var item = _itemSystem.FindItem(itemId);
                if (item != null && item.ActionProps.TryGetValue(action, out int value))
                {
                    return new PyInt(value);
                }
                // 키가 없으면 0 반환 (prop은 항상 정수, 0 이하는 "없음"과 동등)
                return new PyInt(0);
            });

            // set_unit_action_prop: 유닛 ActionProps 설정
            morldModule.ModuleDict["set_unit_action_prop"] = new PyBuiltinFunction("set_unit_action_prop", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("set_unit_action_prop(unit_id, action, value) requires 3 arguments");

                int unitId = args[0].ToInt();
                string action = args[1].AsString();
                int value = args[2].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null)
                {
                    unit.ActionProps[action] = value;
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // get_unit_action_prop: 유닛 ActionProps 조회
            // Note: 키가 없으면 0 반환 (prop은 항상 정수, 0 이하는 "없음"과 동등)
            morldModule.ModuleDict["get_unit_action_prop"] = new PyBuiltinFunction("get_unit_action_prop", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("get_unit_action_prop(unit_id, action) requires 2 arguments");

                int unitId = args[0].ToInt();
                string action = args[1].AsString();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null && unit.ActionProps.TryGetValue(action, out int value))
                {
                    return new PyInt(value);
                }
                return new PyInt(0);
            });
        }

        #endregion

        #region Unit Command API (move_unit, wait_unit)

        /// <summary>
        /// Unit Command API 등록 (캐릭터 행동 명령)
        /// </summary>
        private void RegisterUnitCommandAPI(PyModule morldModule)
        {
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

            // set_unit_activity: [DEPRECATED] JobList 기반에서는 activity가 CurrentJob.Name으로 자동 결정됨
            // 스케줄의 activity 필드를 통해 설정하세요
            morldModule.ModuleDict["set_unit_activity"] = new PyBuiltinFunction("set_unit_activity", args =>
            {
                Godot.GD.PrintErr("[morld] set_unit_activity is DEPRECATED. Activity is now determined by CurrentJob.Name from schedule.");
                return PyBool.False;
            });

            // request_player_command: 플레이어 명령 요청 (시간 진행 포함)
            // 사용 예: morld.request_player_command("이동:0:1") 또는 morld.request_player_command("휴식:30")
            morldModule.ModuleDict["request_player_command"] = new PyBuiltinFunction("request_player_command", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("request_player_command(command) requires 1 argument");

                string command = args[0].AsString();

                var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
                if (_playerSystem != null)
                {
                    _playerSystem.RequestCommand(command);
                    Godot.GD.Print($"[morld] request_player_command: {command}");
                    return PyBool.True;
                }
                return PyBool.False;
            });
        }

        #endregion

        #region Seat API

        /// <summary>
        /// Seat API 등록 (앉기/일어서기)
        /// </summary>
        private void RegisterSeatAPI(PyModule morldModule)
        {
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
        }

        #endregion

        #region Vehicle API

        /// <summary>
        /// Vehicle API 등록 (운전 시스템)
        /// </summary>
        private void RegisterVehicleAPI(PyModule morldModule)
        {
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
        }

        #endregion

        #region Time Query API

        /// <summary>
        /// Time Query API 등록 (시간 정보 조회)
        /// </summary>
        private void RegisterTimeQueryAPI(PyModule morldModule)
        {
            // get_game_time: 현재 게임 시간 (분 단위) 반환
            morldModule.ModuleDict["get_game_time"] = new PyBuiltinFunction("get_game_time", args =>
            {
                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var time = _worldSystem.GetTime();
                return new PyInt(time.MinuteOfDay);
            });

            // get_time_info: 현재 시간 정보 (year, month, day, weekday, hour, minute, weather, region_name, location_name) 반환
            morldModule.ModuleDict["get_time_info"] = new PyBuiltinFunction("get_time_info", args =>
            {
                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

                var time = _worldSystem.GetTime();
                if (time == null)
                    return PyNone.Instance;

                var result = new PyDict();
                result.SetItem(new PyString("year"), new PyInt(time.Year));
                result.SetItem(new PyString("month"), new PyInt(time.Month));
                result.SetItem(new PyString("day"), new PyInt(time.Day));
                result.SetItem(new PyString("weekday"), new PyString(time.WeekdayName));
                result.SetItem(new PyString("hour"), new PyInt(time.Hour));
                result.SetItem(new PyString("minute"), new PyInt(time.Minute));

                // 날씨 및 위치 정보: 플레이어 위치 기준
                string weather = "";
                string regionName = "";
                string locationName = "";
                // Pi-World 정보 (디버깅용)
                // geometry: 0 = ring (원), 1 = line (선)
                int geometry = 0;
                float positionX = 0f;
                float locationLength = 0f;

                var player = _playerSystem?.FindPlayerUnit();
                if (player != null)
                {
                    var terrain = _worldSystem.GetTerrain();
                    var location = terrain.GetLocation(player.CurrentLocation);
                    if (location != null)
                    {
                        locationName = location.Name ?? "";

                        // 날씨는 실외일 때만
                        if (!location.IsIndoor)
                        {
                            var region = terrain.GetRegion(player.CurrentLocation.RegionId);
                            weather = region?.CurrentWeather ?? "";
                        }

                        // Pi-World 정보: ring=0, line=1
                        geometry = location.Geometry == Morld.LocationGeometry.Ring ? 0 : 1;
                        locationLength = location.Length;
                    }

                    var playerRegion = terrain.GetRegion(player.CurrentLocation.RegionId);
                    regionName = playerRegion?.Name ?? "";

                    // 플레이어 X 좌표
                    positionX = player.PositionX;
                }
                result.SetItem(new PyString("weather"), new PyString(weather));
                result.SetItem(new PyString("region_name"), new PyString(regionName));
                result.SetItem(new PyString("location_name"), new PyString(locationName));

                // Pi-World 정보: geometry (0=ring, 1=line)
                result.SetItem(new PyString("geometry"), new PyInt(geometry));
                result.SetItem(new PyString("position_x"), new PyFloat(positionX));
                result.SetItem(new PyString("location_length"), new PyFloat(locationLength));

                return result;
            });
        }

        #endregion

        #region Path API (경로 탐색)

        /// <summary>
        /// Path API 등록 (경로 탐색)
        /// </summary>
        private void RegisterPathAPI(PyModule morldModule)
        {
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
        }

        #endregion

        #region JobList API

        /// <summary>
        /// JobList API 등록
        /// </summary>
        private void RegisterJobListAPI(PyModule morldModule)
        {
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
        }

        #endregion

        #region Chapter API (챕터 전환)

        /// <summary>
        /// Chapter API 등록 (챕터 전환)
        /// </summary>
        private void RegisterChapterAPI(PyModule morldModule)
        {
            // clear_world() - 모든 게임 데이터 초기화 (챕터 전환 시 사용)
            morldModule.ModuleDict["clear_world"] = new PyBuiltinFunction("clear_world", args =>
            {
                Godot.GD.Print("[morld] clear_world: Clearing all game data...");

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var _itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                var _eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;

                // 1. Terrain 초기화 (Region, Location, Gate 모두 제거)
                _worldSystem?.ClearTerrain();

                // 2. Unit 초기화 (Player, NPC, Object 모두 제거)
                _unitSystem?.Clear();

                // 3. Item 초기화
                _itemSystem?.ClearItems();

                // 4. Inventory 초기화
                _inventorySystem?.Clear();

                // 5. EventSystem 상태 초기화
                _eventSystem?.ClearState();

                // 6. Python 측 캐시 초기화 (assets._instances 등)
                try
                {
                    Execute("from assets.characters import clear_instances; clear_instances()");
                }
                catch { /* 함수가 없으면 무시 */ }

                try
                {
                    Execute("from assets.items import clear_instances; clear_instances()");
                }
                catch { /* 함수가 없으면 무시 */ }

                try
                {
                    Execute("from assets.objects import clear_instances; clear_instances()");
                }
                catch { /* 함수가 없으면 무시 */ }

                try
                {
                    Execute("from think import clear_agents; clear_agents()");
                }
                catch { /* 함수가 없으면 무시 */ }

                // 7. ID Generator 리셋
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
        }

        #endregion

        #region Helper: Survival System

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

        #endregion

        #region Game Control API

        /// <summary>
        /// Game Control API 등록 (게임 종료 등)
        /// </summary>
        private void RegisterGameControlAPI(PyModule morldModule)
        {
            // quit_game() - 게임 종료
            morldModule.ModuleDict["quit_game"] = new PyBuiltinFunction("quit_game", args =>
            {
                Godot.GD.Print("[morld] quit_game: Exiting game...");

                // Godot 게임 종료
                var sceneTree = Godot.Engine.GetMainLoop() as Godot.SceneTree;
                sceneTree?.Quit();

                return PyBool.True;
            });
        }

        #endregion
    }
}
