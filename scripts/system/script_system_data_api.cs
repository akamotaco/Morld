using System;
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
            //              describe_text=None, ground_id=None, geometry="line", length=0)
            morldModule.ModuleDict["add_location"] = new PyBuiltinFunction("add_location", (args, kwargs) =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("add_location(region_id, local_id, name, stay_duration=0, indoor=True, owner=None, describe_text=None, ground_id=None, geometry='line', length=0) requires at least 3 arguments");

                int regionId = args[0].ToInt();
                int localId = args[1].ToInt();
                string name = args[2].AsString();
                int stayDurationMin = args.Length >= 4 ? args[3].ToInt() : 0;
                bool isIndoor = args.Length >= 5 ? args[4].IsTrue() : true;
                string owner = args.Length >= 6 && args[5] is PyStr ownerStr ? ownerStr.Value : null;
                var describeText = args.Length >= 7 && args[6] is PyDict descDict
                    ? PyDictToStringDict(descDict)
                    : null;
                int? groundId = args.Length >= 8 && args[7] != PyNone.Instance ? args[7].ToInt() : null;
                string geometry = args.Length >= 9 ? args[8].AsString() : "line";
                float length = args.Length >= 10 ? args[9].ToFloat() : 0f;

                // kwargs 지원 — positional로 지정되지 않은 인자를 kwargs에서 추출
                if (kwargs != null)
                {
                    foreach (var kv in kwargs.InternalDict)
                    {
                        var key = kv.Key is PyStr ps ? ps.Value : kv.Key.ToString();
                        switch (key)
                        {
                            case "stay_duration": stayDurationMin = kv.Value.ToInt(); break;
                            case "indoor": isIndoor = kv.Value.IsTrue(); break;
                            case "owner": owner = kv.Value is PyStr os ? os.Value : null; break;
                            case "describe_text": describeText = kv.Value is PyDict dd ? PyDictToStringDict(dd) : null; break;
                            case "ground_id": groundId = kv.Value != PyNone.Instance ? kv.Value.ToInt() : null; break;
                            case "geometry": geometry = kv.Value.AsString(); break;
                            case "length": length = kv.Value.ToFloat(); break;
                            default:
                                throw PyTypeError.Create($"'{key}' is an invalid keyword argument for add_location()");
                        }
                    }
                }

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;

                var terrain = _worldSystem.GetTerrain();
                var region = terrain.GetRegion(regionId);
                if (region != null)
                {
                    // Region.AddLocation(localId, name)을 사용
                    var location = region.AddLocation(localId, name);
                    location.StayDuration = stayDurationMin * GameTime.MillisPerMinute; // 분 → 밀리초
                    location.IsIndoor = isIndoor;
                    location.Owner = owner;
                    location.GroundUnitId = groundId;

                    // Pi-World 2D 속성 설정
                    location.Geometry = geometry.ToLower() == "ring"
                        ? Morld.LocationGeometry.Ring
                        : Morld.LocationGeometry.Line;
                    location.Length = length;

                    // describe_text 설정
                    if (describeText != null)
                    {
                        foreach (var (key, value) in describeText)
                        {
                            location.DescribeText[key] = value;
                        }
                    }

                    Godot.GD.Print($"[morld] add_location: region={regionId}, local={localId}, name={name}, indoor={isIndoor}, geometry={geometry}, length={length}, stay={stayDurationMin}min");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // add_region_gate
            // add_region_gate 삭제 — cross-region은 add_gate로 통일
            // Gate의 connected_region != region_id이면 자동으로 cross-region 처리

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
                float x = args[3].ToFloat();
                int connectedRegion = args[4].ToInt();
                int connectedLocation = args[5].ToInt();
                float arrivalX = args[6].ToFloat();
                float arrivalY = args.Length >= 8 && args[7] is not PyDict ? args[7].ToFloat() : 0f;

                // arrival_y가 없거나 dict이면 다음 파라미터가 conditions
                int conditionsStartIdx = args.Length >= 8 && args[7] is PyDict ? 7 : 8;
                var conditionsForward = args.Length > conditionsStartIdx && args[conditionsStartIdx] is PyDict condFwdDict
                    ? PyDictToIntDict(condFwdDict)
                    : null;
                var conditionsBackward = args.Length > conditionsStartIdx + 1 && args[conditionsStartIdx + 1] is PyDict condBwdDict
                    ? PyDictToIntDict(condBwdDict)
                    : null;
                bool isBlocked = args.Length > conditionsStartIdx + 2 && args[conditionsStartIdx + 2].IsTrue();
                string name = args.Length > conditionsStartIdx + 3 && args[conditionsStartIdx + 3] is PyStr nameStr ? nameStr.Value : "";
                float gateDistance = args.Length > conditionsStartIdx + 4 ? (float)args[conditionsStartIdx + 4].ToDouble() : 0f; // Python: location units

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var region = terrain.GetRegion(regionId);

                if (region != null)
                {
                    var gate = region.AddGate(locationId, gateId, x, connectedRegion, connectedLocation, arrivalX, arrivalY);
                    gate.Name = name;
                    gate.Distance = gateDistance;
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

                    // cross-region도 Gate만으로 이동 가능 (BuildRawRoutes가 Gate에서 직접 처리)
                    // RegionGate 자동 생성 불필요 — RegionGate는 레거시 호환용

                    Godot.GD.Print($"[morld] add_gate: {regionId}:{locationId}:Gate{gateId}(X={x}) -> {connectedRegion}:{connectedLocation}(X={arrivalX})");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // remove_gate(region_id, location_id, gate_id) -> bool
            // Gate 제거 (동적 건축 시스템용)
            morldModule.ModuleDict["remove_gate"] = new PyBuiltinFunction("remove_gate", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("remove_gate(region_id, location_id, gate_id) requires 3 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();
                int gateId = args[2].ToInt();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var region = terrain.GetRegion(regionId);

                if (region != null && region.RemoveGate(locationId, gateId))
                {
                    Godot.GD.Print($"[morld] remove_gate: {regionId}:{locationId}:Gate{gateId}");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // remove_location(region_id, location_id) -> bool
            // Location 제거 (해당 Location의 Gate도 함께 정리됨)
            morldModule.ModuleDict["remove_location"] = new PyBuiltinFunction("remove_location", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("remove_location(region_id, location_id) requires 2 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var region = terrain.GetRegion(regionId);

                if (region != null && region.RemoveLocation(locationId))
                {
                    Godot.GD.Print($"[morld] remove_location: {regionId}:{locationId}");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // set_location_length(region_id, location_id, length) -> bool
            // Location 크기 변경 (방 확장용)
            morldModule.ModuleDict["set_location_length"] = new PyBuiltinFunction("set_location_length", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("set_location_length(region_id, location_id, length) requires 3 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();
                float length = args[2].ToFloat();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var location = terrain.GetLocation(new Morld.LocationRef(regionId, locationId));

                if (location != null)
                {
                    location.Length = length;
                    Godot.GD.Print($"[morld] set_location_length: {regionId}:{locationId} -> {length}");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // get_location_gates(region_id, location_id) -> list of dicts
            // Location의 Gate 목록 조회
            morldModule.ModuleDict["get_location_gates"] = new PyBuiltinFunction("get_location_gates", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("get_location_gates(region_id, location_id) requires 2 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var region = terrain.GetRegion(regionId);

                var result = new PyList();
                if (region != null)
                {
                    foreach (var gate in region.GetGates(locationId))
                    {
                        var dict = new PyDict();
                        dict["gate_id"] = new PyInt(gate.Id);
                        dict["x"] = new PyFloat(gate.X);
                        dict["connected_region"] = new PyInt(gate.ConnectedLocation.RegionId);
                        dict["connected_location"] = new PyInt(gate.ConnectedLocation.LocalId);
                        dict["arrival_x"] = new PyFloat(gate.ArrivalX);
                        dict["is_blocked"] = gate.IsBlocked ? PyBool.True : PyBool.False;
                        dict["name"] = new PyStr(gate.Name ?? "");
                        result.Append(dict);
                    }
                }
                return result;
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
            // 반환: {"id", "name", "locations": [{"id", "name", "gates": [...], "region_gates": [(to_region, to_local, region_name, distance), ...]}], ...}
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
                result["id"] = new PyInt(region.Id);
                result["name"] = new PyStr(region.Name ?? "");

                // Location 목록
                var locationsList = new PyList();
                foreach (var location in region.Locations)
                {
                    var locDict = new PyDict();
                    locDict["id"] = new PyInt(location.LocalId);
                    locDict["name"] = new PyStr(location.Name ?? "");
                    locDict["is_indoor"] = location.IsIndoor ? PyBool.True : PyBool.False;

                    // Pi-World: Location 2D 속성
                    locDict["length"] = new PyFloat(location.Length);
                    locDict["geometry"] = new PyStr(location.Geometry.ToString().ToLower());

                    // 이 Location에서 나가는 Gate 목록 (Pi-World)
                    var gatesList = new PyList();
                    foreach (var gate in region.GetGates(location.LocalId))
                    {
                        var gateDict = new PyDict();
                        gateDict["id"] = new PyInt(gate.Id);
                        gateDict["x"] = new PyFloat(gate.X);
                        gateDict["connected_region"] = new PyInt(gate.ConnectedLocation.RegionId);
                        gateDict["connected_local"] = new PyInt(gate.ConnectedLocation.LocalId);
                        gateDict["arrival_x"] = new PyFloat(gate.ArrivalX);
                        gateDict["arrival_y"] = new PyFloat(gate.ArrivalY);
                        gateDict["is_blocked"] = gate.IsBlocked ? PyBool.True : PyBool.False;
                        gateDict["distance"] = new PyFloat(gate.Distance);
                        gatesList.Append(gateDict);
                    }
                    locDict["gates"] = gatesList;

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
                                new PyStr(regionName),
                                new PyFloat(regionGate.Distance)
                            });
                            regionGatesList.Append(regionGateTuple);
                        }
                    }
                    locDict["region_gates"] = regionGatesList;

                    locationsList.Append(locDict);
                }
                result["locations"] = locationsList;

                return result;
            });

            // get_travel_time: 두 위치 간 이동 시간 계산 (경로 탐색 포함, 반환: 밀리초)
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
            // game_millis: 게임 시간 간격 (밀리초)
            morldModule.ModuleDict["set_auto_time_flow_interval"] = new PyBuiltinFunction("set_auto_time_flow_interval", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("set_auto_time_flow_interval(real_seconds, game_millis) requires 2 arguments");

                float realSeconds = args[0].ToFloat();
                int gameMillis = args[1].ToInt();

                var _autoTimeFlowSystem = this._hub.GetSystem("autoTimeFlowSystem") as AutoTimeFlowSystem;

                if (_autoTimeFlowSystem == null)
                    return PyBool.False;

                _autoTimeFlowSystem.RealTimeIntervalSeconds = realSeconds;
                _autoTimeFlowSystem.GameTimeIntervalMillis = gameMillis;

                int displayMin = gameMillis / GameTime.MillisPerMinute;
                Godot.GD.Print($"[morld] set_auto_time_flow_interval: {realSeconds}s -> {displayMin}min ({gameMillis}ms)");
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
            // 반환: (real_seconds, game_millis) 튜플
            morldModule.ModuleDict["get_auto_time_flow_interval"] = new PyBuiltinFunction("get_auto_time_flow_interval", args =>
            {
                var _autoTimeFlowSystem = this._hub.GetSystem("autoTimeFlowSystem") as AutoTimeFlowSystem;

                if (_autoTimeFlowSystem == null)
                    return new PyTuple(new PyObject[] { new PyFloat(5.0), new PyInt(GameTime.MillisPerMinute) });

                return new PyTuple(new PyObject[] {
                    new PyFloat(_autoTimeFlowSystem.RealTimeIntervalSeconds),
                    new PyInt(_autoTimeFlowSystem.GameTimeIntervalMillis)
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

            // advance_time_des(millis) - DES 기반 시간 진행 (유일한 시간 진행 API)
            //
            // - Step 단위로 시간 진행 (최소 NPC job duration 기준)
            // - 각 Step마다 think_all() 호출 (NPC AI 재계산)
            // - Move job 만료 시 NPC를 목표 location에 텔레포트
            // - time_elapsed 이벤트 Python에 전달 (survival/resource 처리)
            //
            // [아키텍처 주의]
            // 이 메서드는 ECS Step(GameEngine._Process → World.Step)과 별도 경로로 실행됨.
            // 역할 분리: C#은 시스템(이동/Job/시간), Python은 컨텐츠(think/이벤트).
            // 이 분리가 유지되는 한 실질적으로 단일 호출이지만,
            // C# 시스템 로직(JobBehaviorSystem 등) 변경 시 이 메서드도 동기화 필요.
            //
            // 반환: 실제 경과된 시간 (밀리초)
            morldModule.ModuleDict["advance_time_des"] = new PyBuiltinFunction("advance_time_des", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("advance_time_des(millis) requires 1 argument");

                int totalMillis = args[0].ToInt();
                if (totalMillis <= 0)
                    return new PyInt(0);

                int elapsed = AdvanceTimeDES(totalMillis);
                return new PyInt(elapsed);
            });
        }

        /// <summary>
        /// 유닛 이동 시뮬레이션 (advance_time_des용)
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

        /// <summary>
        /// DES (Discrete Event Simulation) 기반 시간 진행
        ///
        /// NPC의 job duration을 기준으로 step 단위 진행:
        /// 1. 전체 NPC 중 최소 남은 job duration 계산 → step size
        /// 2. 각 NPC의 이동 시뮬레이션 + job advance
        /// 3. Move job 만료 시 NPC를 목표 location에 텔레포트
        /// 4. GameTime 업데이트 + time_elapsed 이벤트 발생 + flush
        /// 5. think_all() 호출 (job이 소진된 NPC가 새 job 삽입)
        /// 6. 반복
        ///
        /// 안전장치: 최대 1000회 반복 (무한루프 방지)
        /// </summary>
        private int AdvanceTimeDES(int totalMillis)
        {
            var worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
            var unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
            var itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
            var eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;
            var playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

            var terrain = worldSystem.GetTerrain();
            var time = worldSystem.GetTime();
            int playerId = playerSystem?.PlayerId ?? -1;

            if (worldSystem.IsTimeFrozen())
            {
                Godot.GD.Print("[morld] advance_time_des: Time is frozen, skipping");
                return 0;
            }

            int remaining = totalMillis;
            int totalElapsed = 0;
            int maxIterations = 1000;  // 안전장치

            Godot.GD.Print($"[morld] advance_time_des: Starting DES loop ({totalMillis / GameTime.MillisPerMinute}min)");

            for (int iteration = 0; iteration < maxIterations && remaining > 0; iteration++)
            {
                // === 1. Step size 결정: 전체 NPC의 최소 job duration ===
                int step = remaining;
                foreach (var unit in unitSystem.Units.Values)
                {
                    if (unit.IsObject || unit.Id == playerId) continue;

                    var currentJob = unit.CurrentJob;
                    if (currentJob != null && currentJob.Duration > 0)
                    {
                        step = Math.Min(step, currentJob.Duration);
                    }
                }
                // step이 0이면 1분으로 강제 (빈 job 방지)
                if (step <= 0) step = Math.Min(GameTime.MillisPerMinute, remaining);

                // === 2. 각 NPC 이동 시뮬레이션 ===
                foreach (var unit in unitSystem.Units.Values)
                {
                    if (unit.IsObject || unit.Id == playerId) continue;

                    SimulateUnitMovement(unit, step, terrain, itemSystem);
                }

                // === 3. Move job 만료 전 정보 기록 (텔레포트용) ===
                // AdvanceJobs가 job을 제거하기 전에 move job 정보를 저장
                var moveJobsToTeleport = new System.Collections.Generic.List<(Morld.Unit unit, Morld.LocationRef goal, float targetX)>();
                foreach (var unit in unitSystem.Units.Values)
                {
                    if (unit.IsObject || unit.Id == playerId) continue;

                    var currentJob = unit.CurrentJob;
                    if (currentJob != null && currentJob.Action == "move" && currentJob.Duration <= step)
                    {
                        // 이 job은 이번 step에서 만료됨 → 텔레포트 대상
                        moveJobsToTeleport.Add((unit, currentJob.GetLocationRef(), currentJob.TargetX));
                    }
                }

                // === 4. Job advance (시간 소진) ===
                foreach (var unit in unitSystem.Units.Values)
                {
                    if (unit.IsObject || unit.Id == playerId) continue;
                    unit.AdvanceJobs(step);
                }

                // === 5. Move job 텔레포트 처리 ===
                foreach (var (unit, goalLocation, targetX) in moveJobsToTeleport)
                {
                    // 아직 도착하지 않았으면 텔레포트
                    if (unit.CurrentLocation != goalLocation)
                    {
                        unit.SetCurrentLocation(goalLocation);
                    }
                    unit.PositionX = targetX;
                    unit.CurrentMovement = null;
                    unit.ClearRoute();
                    // Gate Transit: 이동 완료 → 숨김 해제
                    if (unit.TraversalContext.GetProp("상태:이동중") == 1)
                        unit.TraversalContext.Props.Set("상태:이동중", 0);
                }

                // === 6. GameTime 업데이트 ===
                time.AddMillis(step);

                // === 7. time_elapsed 이벤트 발생 + 즉시 flush ===
                // Python의 survival/resource_agent/trap_agent 등이 처리됨
                // (플레이어 생존도 _on_time_elapsed에서 통합 처리)
                if (eventSystem != null)
                {
                    eventSystem.Enqueue(GameEvent.OnTimeElapsed(step));
                    // FlushEvents → 플레이어 기절 등 다이얼로그 발생 시 break
                    if (eventSystem.FlushEvents())
                    {
                        remaining -= step;
                        totalElapsed += step;
                        break;
                    }
                }

                // === 8. think_all() 호출 (job 소진된 NPC가 새 job 삽입) ===
                CallThinkAll();

                remaining -= step;
                totalElapsed += step;
            }

            if (remaining > 0)
            {
                Godot.GD.PrintErr($"[morld] advance_time_des: WARNING - {remaining}ms remaining after max iterations");
            }

            int displayMin = totalElapsed / GameTime.MillisPerMinute;
            Godot.GD.Print($"[morld] advance_time_des: Completed ({displayMin}min, {totalElapsed}ms)");
            return totalElapsed;
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
                    return new PyStr(region.CurrentWeather);
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
                string owner = args.Length >= 7 && args[6] is PyStr ownerStr ? ownerStr.Value : null;
                string uniqueId = args.Length >= 8 && args[7] is PyStr uidStr ? uidStr.Value : null;
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
                string uniqueId = args.Length >= 8 && args[7] is PyStr uidStr ? uidStr.Value : null;
                var actionProps = args.Length >= 9 && args[8] is PyDict apDict ? PyDictToIntDict(apDict) : null;
                string owner = args.Length >= 10 && args[9] is PyStr ownerStr ? ownerStr.Value : null;
                bool itemVisible = args.Length >= 11 && args[10].IsTrue();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = new Morld.Unit(id, name, regionId, locationId);
                unit.UniqueId = uniqueId;
                unit.Owner = owner;
                unit.ItemVisible = itemVisible;
                unit.Type = type.ToLower() switch
                {
                    "object" => Morld.UnitType.Object,
                    "creature" => Morld.UnitType.Creature,
                    _ => Morld.UnitType.Character
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

            // remove_unit: 유닛 제거 (동적 바닥 오브젝트 등)
            morldModule.ModuleDict["remove_unit"] = new PyBuiltinFunction("remove_unit", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("remove_unit(unit_id) requires 1 argument");

                int unitId = args[0].ToInt();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var _inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;

                _inventorySystem?.ClearInventory(InventorySystem.UnitKey(unitId));

                bool success = _unitSystem?.RemoveUnit(unitId) ?? false;

                Godot.GD.Print($"[morld] remove_unit: id={unitId}, success={success}");
                return PyBool.FromBool(success);
            });

            // set_unit_props: 유닛 Props 일괄 설정 (int + string 혼합 지원)
            morldModule.ModuleDict["set_unit_props"] = new PyBuiltinFunction("set_unit_props", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("set_unit_props(unit_id, props) requires 2 arguments");

                int unitId = args[0].ToInt();
                var propDict = args[1] as PyDict;
                if (propDict == null) return PyBool.False;

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null)
                {
                    var keys = propDict.Keys();
                    int count = 0;
                    for (int i = 0; i < keys.Length(); i++)
                    {
                        var key = keys.GetItem(i);
                        var keyStr = key is PyStr ks ? ks.Value : key.ToString();
                        var value = propDict.GetItem(key);

                        if (value is PyStr strVal)
                        {
                            unit.TraversalContext.SetStringProp(keyStr, strVal.Value);
                            unit.TraversalContext.SetProp(keyStr, 0);  // 동일 키 int 제거
                        }
                        else
                        {
                            var valueInt = value is PyBool vb ? (vb.IsTrue() ? 1 : 0)
                                         : value is PyInt vi ? (int)vi.Value
                                         : value is PyNone ? 0 : 0;
                            unit.TraversalContext.SetProp(keyStr, valueInt);
                            unit.TraversalContext.RemoveStringProp(keyStr);  // 동일 키 string 제거
                        }
                        count++;
                    }
                    Godot.GD.Print($"[morld] set_unit_props: unit={unitId}, props={count}");
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // set_unit_location (Pi-World 2D 위치 확장)
            // set_unit_location(unit_id, region_id, location_id, x=0, y=0)
            // 강제 이동 시 자동으로 stand_up 처리 (posture/seated_on 정리)
            morldModule.ModuleDict["set_unit_location"] = new PyBuiltinFunction("set_unit_location", (args, kwargs) =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("set_unit_location(unit_id, region_id, location_id, x=0, y=0) requires at least 3 arguments");

                int unitId = args[0].ToInt();
                int regionId = args[1].ToInt();
                int locationId = args[2].ToInt();
                float x = args.Length >= 4 ? args[3].ToFloat() : 0f;
                float y = args.Length >= 5 ? args[4].ToFloat() : 0f;

                if (kwargs != null)
                {
                    foreach (var kv in kwargs.InternalDict)
                    {
                        var key = kv.Key is PyStr ps ? ps.Value : kv.Key.ToString();
                        switch (key)
                        {
                            case "x": x = kv.Value.ToFloat(); break;
                            case "y": y = kv.Value.ToFloat(); break;
                            default:
                                throw PyTypeError.Create($"'{key}' is an invalid keyword argument for set_unit_location()");
                        }
                    }
                }

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null)
                {
                    // === 자동 stand_up 처리: 앉아있으면 자동으로 일어남 ===
                    var seatedOn = unit.TraversalContext.Props.GetByType("seated_on").FirstOrDefault();
                    if (seatedOn.Prop.IsValid)
                    {
                        Godot.GD.Print($"[morld] set_unit_location: unit={unitId} is seated, auto stand_up");

                        // 1. 오브젝트의 seated_by 정리
                        if (int.TryParse(seatedOn.Prop.Name, out int objectId))
                        {
                            var obj = _unitSystem.FindUnit(objectId);
                            if (obj != null)
                            {
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

                        // 2. 캐릭터 seated_on 제거
                        unit.TraversalContext.Props.Remove(seatedOn.Prop);

                        // 3. 캐릭터 posture 제거 (standing으로 복귀)
                        var postureProps = unit.TraversalContext.Props.GetByType("posture").ToList();
                        foreach (var postureProp in postureProps)
                        {
                            unit.TraversalContext.Props.Remove(postureProp.Prop);
                        }
                    }
                    // === 자동 stand_up 처리 끝 ===

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
                float x = args[1].ToFloat();
                float y = args.Length >= 3 ? args[2].ToFloat() : 0f;

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

            // get_location_size: Location 크기 조회
            // get_location_size(region_id, location_id) -> (width, height)
            morldModule.ModuleDict["get_location_size"] = new PyBuiltinFunction("get_location_size", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("get_location_size(region_id, location_id) requires 2 arguments");

                int regionId = args[0].ToInt();
                int locationId = args[1].ToInt();

                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var terrain = _worldSystem.GetTerrain();
                var location = terrain?.GetLocation(new LocationRef(regionId, locationId));
                if (location != null)
                {
                    return new PyTuple(new PyObject[]
                    {
                        new PyFloat(location.Length),
                        new PyFloat(location.HeightMax - location.HeightMin)
                    });
                }
                return PyNone.Instance;
            });

            // set_collision_enabled: Unit 충돌 활성화/비활성화
            // set_collision_enabled(unit_id, enabled)
            morldModule.ModuleDict["set_collision_enabled"] = new PyBuiltinFunction("set_collision_enabled", args =>
            {
                if (args.Length < 2)
                    throw PyTypeError.Create("set_collision_enabled(unit_id, enabled) requires 2 arguments");

                int unitId = args[0].ToInt();
                bool enabled = args[1].IsTrue();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null)
                {
                    unit.CollisionEnabled = enabled;
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // get_map_viewport: 던전 맵 뷰포트 데이터 조회
            // get_map_viewport(rooms_data, corridors_data, fog_data, player_room_id, cam_x, cam_y, view_w, view_h, bsp_w, bsp_h)
            // rooms_data: [{id, x, y, w, h, type, name}], corridors_data: [(a,b)], fog_data: {id: vis}
            // Returns: {rooms: [{id,gx,gy,type,name,vis,is_current,is_adjacent}], corridors: [{ax,ay,bx,by,dim,highlight}], cam_x, cam_y}
            morldModule.ModuleDict["get_map_viewport"] = new PyBuiltinFunction("get_map_viewport", args =>
            {
                if (args.Length < 10)
                    throw PyTypeError.Create("get_map_viewport requires 10 arguments");

                var roomsList = args[0] as PyList;
                var corrList = args[1] as PyList;
                var fogDict = args[2] as PyDict;
                int playerRoomId = args[3].ToInt();
                int camX = args[4].ToInt();
                int camY = args[5].ToInt();
                int viewW = args[6].ToInt();
                int viewH = args[7].ToInt();
                int bspW = args[8].ToInt();
                int bspH = args[9].ToInt();

                if (roomsList == null || corrList == null || fogDict == null)
                    return PyNone.Instance;

                // 내부 그리드 크기 (뷰포트보다 넉넉하게)
                int gridW = System.Math.Max(viewW * 3, 80);
                int gridH = System.Math.Max(viewH * 3, 40);
                bspW = System.Math.Max(bspW, 1);
                bspH = System.Math.Max(bspH, 1);

                // Room 파싱 + 그리드 좌표 매핑
                var roomPositions = new System.Collections.Generic.Dictionary<int, (int gx, int gy)>();
                var roomData = new System.Collections.Generic.List<(int id, int gx, int gy, string type, string name, int vis)>();
                var adjacency = new System.Collections.Generic.Dictionary<int, System.Collections.Generic.HashSet<int>>();

                foreach (PyObject item in roomsList.Items)
                {
                    if (item is PyDict rd)
                    {
                        int id = rd["id"]?.ToInt() ?? 0;
                        int rx = rd["x"]?.ToInt() ?? 0;
                        int ry = rd["y"]?.ToInt() ?? 0;
                        int rw = rd["w"]?.ToInt() ?? 0;
                        int rh = rd["h"]?.ToInt() ?? 0;
                        string rtype = rd["type"]?.AsString() ?? "normal";
                        string rname = rd["name"]?.AsString() ?? "";

                        // BSP → 그리드 좌표
                        int cx = rx + rw / 2;
                        int cy = ry + rh / 2;
                        int gx = cx * (gridW - 8) / bspW + 4;
                        int gy = cy * (gridH - 8) / bspH + 3;
                        gx = System.Math.Clamp(gx, 4, gridW - 5);
                        gy = System.Math.Clamp(gy, 2, gridH - 4);

                        // fog 상태
                        int vis = 0;
                        var idKey = new PyInt(id);
                        if (fogDict.InternalDict.TryGetValue(idKey, out var visObj))
                            vis = visObj.ToInt();

                        roomPositions[id] = (gx, gy);
                        roomData.Add((id, gx, gy, rtype, rname, vis));
                    }
                }

                // Corridor 파싱 + adjacency 생성
                var corrData = new System.Collections.Generic.List<(int roomA, int roomB)>();
                foreach (PyObject item in corrList.Items)
                {
                    if (item is PyTuple t && t.Items.Length >= 2)
                    {
                        int a = t.Items[0].ToInt();
                        int b = t.Items[1].ToInt();
                        corrData.Add((a, b));
                        if (!adjacency.ContainsKey(a)) adjacency[a] = new();
                        if (!adjacency.ContainsKey(b)) adjacency[b] = new();
                        adjacency[a].Add(b);
                        adjacency[b].Add(a);
                    }
                }

                // 자동 센터링: 플레이어 위치 기준
                if (camX == -1 && camY == -1 && roomPositions.ContainsKey(playerRoomId))
                {
                    var (px, py) = roomPositions[playerRoomId];
                    camX = px - viewW / 2;
                    camY = py - viewH / 2;
                }
                camX = System.Math.Clamp(camX, 0, System.Math.Max(0, gridW - viewW));
                camY = System.Math.Clamp(camY, 0, System.Math.Max(0, gridH - viewH));

                // 뷰포트 내 rooms 필터링
                var resultRooms = new PyList();
                foreach (var (id, gx, gy, rtype, rname, vis) in roomData)
                {
                    // 뷰포트 좌표로 변환
                    int vgx = gx - camX;
                    int vgy = gy - camY;

                    // 뷰포트 밖이면 스킵 (여유 2칸)
                    if (vgx < -2 || vgx >= viewW + 2 || vgy < -2 || vgy >= viewH + 2)
                        continue;

                    bool isCurrent = (id == playerRoomId);
                    bool isAdj = adjacency.ContainsKey(playerRoomId)
                        && adjacency[playerRoomId].Contains(id);

                    var rd = new PyDict();
                    rd["id"] = new PyInt(id);
                    rd["gx"] = new PyInt(vgx);
                    rd["gy"] = new PyInt(vgy);
                    rd["type"] = new PyStr(rtype);
                    rd["name"] = new PyStr(rname);
                    rd["vis"] = new PyInt(vis);
                    rd["is_current"] = PyBool.FromBool(isCurrent);
                    rd["is_adjacent"] = PyBool.FromBool(isAdj);
                    resultRooms.Append(rd);
                }

                // 뷰포트 내 corridors 필터링
                var resultCorrs = new PyList();
                foreach (var (roomA, roomB) in corrData)
                {
                    if (!roomPositions.ContainsKey(roomA) || !roomPositions.ContainsKey(roomB))
                        continue;
                    var (ax, ay) = roomPositions[roomA];
                    var (bx, by) = roomPositions[roomB];
                    int vax = ax - camX, vay = ay - camY;
                    int vbx = bx - camX, vby = by - camY;

                    // 양쪽 다 뷰포트 밖이면 스킵
                    bool aIn = vax >= -2 && vax < viewW + 2 && vay >= -2 && vay < viewH + 2;
                    bool bIn = vbx >= -2 && vbx < viewW + 2 && vby >= -2 && vby < viewH + 2;
                    if (!aIn && !bIn) continue;

                    int visA = 0, visB = 0;
                    var kaKey = new PyInt(roomA);
                    var kbKey = new PyInt(roomB);
                    if (fogDict.InternalDict.TryGetValue(kaKey, out var va)) visA = va.ToInt();
                    if (fogDict.InternalDict.TryGetValue(kbKey, out var vb)) visB = vb.ToInt();

                    bool bothVisible = visA >= 2 && visB >= 2;  // VISIBLE=2
                    bool dim = !bothVisible;
                    bool highlight = (roomA == playerRoomId || roomB == playerRoomId)
                        && adjacency.ContainsKey(playerRoomId)
                        && (adjacency[playerRoomId].Contains(roomA) || adjacency[playerRoomId].Contains(roomB));

                    var cd = new PyDict();
                    cd["ax"] = new PyInt(vax);
                    cd["ay"] = new PyInt(vay);
                    cd["bx"] = new PyInt(vbx);
                    cd["by"] = new PyInt(vby);
                    cd["dim"] = PyBool.FromBool(dim);
                    cd["highlight"] = PyBool.FromBool(highlight);
                    resultCorrs.Append(cd);
                }

                var result = new PyDict();
                result["rooms"] = resultRooms;
                result["corridors"] = resultCorrs;
                result["cam_x"] = new PyInt(camX);
                result["cam_y"] = new PyInt(camY);
                result["grid_w"] = new PyInt(gridW);
                result["grid_h"] = new PyInt(gridH);
                return result;
            });

            // set_unit_prop: 단일 Prop 설정 ("타입:이름" 형식)
            // int 값은 PropSet에, 문자열 값은 StringProps에 저장
            morldModule.ModuleDict["set_unit_prop"] = new PyBuiltinFunction("set_unit_prop", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("set_unit_prop(unit_id, prop_name, value) requires 3 arguments");

                int unitId = args[0].ToInt();
                string propName = args[1].AsString();

                var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;

                var unit = _unitSystem.FindUnit(unitId);
                if (unit != null)
                {
                    if (args[2] is PyStr strVal)
                    {
                        // 문자열 값 → StringProps 저장 (동일 키 int prop 제거)
                        unit.TraversalContext.SetStringProp(propName, strVal.Value);
                        unit.TraversalContext.SetProp(propName, 0);
                        Godot.GD.Print($"[morld] set_unit_prop(str): unit={unitId}, {propName}=\"{strVal.Value}\"");
                    }
                    else
                    {
                        // 정수 값 → PropSet 저장 (동일 키 string prop 제거, None은 0 = 삭제)
                        int value = args[2] is PyNone ? 0 : args[2].ToInt();
                        unit.TraversalContext.SetProp(propName, value);
                        unit.TraversalContext.RemoveStringProp(propName);
                        Godot.GD.Print($"[morld] set_unit_prop: unit={unitId}, {propName}={value}");
                    }
                    return PyBool.True;
                }
                return PyBool.False;
            });

            // get_unit_prop: Prop 값 조회 ("타입:이름" 형식)
            // 문자열 prop이 있으면 PyStr 반환, 없으면 int prop → PyInt 반환 (기본값 0)
            // 호환성: int prop이 없을 때 0 반환 유지 (기존 코드에서 > 비교 등 사용)
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
                    // 문자열 prop 우선 조회
                    var strVal = unit.TraversalContext.GetStringProp(propName);
                    if (strVal != null)
                        return new PyStr(strVal);

                    // int prop 조회 (없으면 0 — 기존 호환성 유지)
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
            // 지원 필드: "name", "type"
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
                    case "type":
                        var typeStr = value.AsString();
                        unit.Type = typeStr.ToLower() switch
                        {
                            "object" => UnitType.Object,
                            "creature" => UnitType.Creature,
                            _ => UnitType.Character
                        };
                        Godot.GD.Print($"[morld] set_unit: unit={unitId}, type={typeStr}");
                        return PyBool.True;
                    default:
                        throw PyTypeError.Create($"set_unit: unknown field '{field}'");
                }
            });

            // get_unit_props_by_type: 특정 타입의 Prop만 조회 (int + string 병합)
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
                    // int props
                    foreach (var (name, value) in unit.TraversalContext.Props.GetNamesByType(type))
                    {
                        result[name] = new PyInt(value);
                    }
                    // string props (key = "타입:이름" 형식에서 타입 매칭)
                    var strProps = unit.TraversalContext.StringProps;
                    if (strProps != null)
                    {
                        string prefix = type + ":";
                        foreach (var (fullName, strVal) in strProps)
                        {
                            if (fullName.StartsWith(prefix))
                            {
                                var name = fullName.Substring(prefix.Length);
                                result[name] = new PyStr(strVal);
                            }
                        }
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
                        result.Append(new PyStr(type));
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
                        result[kv.Key.FullName] = new PyInt(kv.Value);
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
                        // 이미 같은 오브젝트에 앉아있으면 실패
                        if (int.TryParse(seatedOn.Prop.Name, out int currentObjId) && currentObjId == objectId)
                        {
                            Godot.GD.Print($"[morld] sit_on: unit={unitId} is already seated on object={objectId}");
                            return PyBool.False;
                        }

                        // 다른 오브젝트에 앉아있으면 먼저 일어나기
                        Godot.GD.Print($"[morld] sit_on: unit={unitId} auto-standing up from current seat");

                        // 현재 오브젝트의 seated_by 슬롯 해제
                        if (int.TryParse(seatedOn.Prop.Name, out int prevObjId))
                        {
                            var prevObj = _unitSystem.FindUnit(prevObjId);
                            if (prevObj != null)
                            {
                                var seatProps = prevObj.TraversalContext.Props.GetByType("seated_by");
                                foreach (var (prop, value) in seatProps)
                                {
                                    if (value == unitId)
                                    {
                                        prevObj.TraversalContext.Props.Set(prop, -1);
                                        break;
                                    }
                                }
                            }
                        }

                        // 캐릭터 seated_on 제거
                        unit.TraversalContext.Props.Remove(seatedOn.Prop);

                        // posture는 새 오브젝트에 앉을 때 덮어씌워지므로 여기서 제거 불필요
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

                    // 4. 오브젝트의 posture prop을 읽어서 캐릭터의 posture 설정
                    // 오브젝트 posture: "sit" → 캐릭터: posture:sitting = 1
                    //                   "lie" → 캐릭터: posture:lying = 1
                    var objPostureProps = obj.TraversalContext.Props.GetByType("posture").FirstOrDefault();
                    if (objPostureProps.Prop.IsValid)
                    {
                        string objPosture = objPostureProps.Prop.Name;  // "sit", "lie" 등
                        string unitPosture = objPosture switch
                        {
                            "sit" => "sitting",
                            "lie" => "lying",
                            _ => objPosture + "ing"  // 기타: crouch → crouching 등
                        };
                        // 기존 posture 모두 제거 후 새 posture 설정
                        var existingPostures = unit.TraversalContext.Props.GetByType("posture").ToList();
                        if (existingPostures.Count >= 2)
                        {
                            Godot.GD.PrintErr($"[morld] sit_on: WARNING - unit={unitId} has {existingPostures.Count} posture props (should be <= 1)! Removing all.");
                        }
                        foreach (var existing in existingPostures)
                        {
                            unit.TraversalContext.Props.Remove(existing.Prop);
                        }
                        unit.TraversalContext.Props.Set($"posture:{unitPosture}", 1);

                        // 검증: posture가 정확히 1개인지 확인
                        var postureCount = unit.TraversalContext.Props.GetByType("posture").Count();
                        if (postureCount != 1)
                        {
                            Godot.GD.PrintErr($"[morld] sit_on: ERROR - unit={unitId} posture count is {postureCount} after setting (expected 1)!");
                        }
                    }

                    // 캐릭터를 오브젝트 X 좌표로 이동 (+ 시간 소모)
                    float fromX = unit.PositionX;
                    float toX = obj.PositionX;
                    unit.PositionX = toX;
                    unit.CurrentMovement = null;

                    // 플레이어인 경우 이동 시간 소모
                    var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;
                    if (_playerSystem != null && unitId == _playerSystem.PlayerId)
                    {
                        var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                        bool isTimeFrozen = _worldSystem?.IsTimeFrozen() ?? false;
                        if (!isTimeFrozen)
                        {
                            var terrain = _worldSystem?.GetTerrain();
                            var location = terrain?.GetLocation(unit.CurrentLocation);
                            if (location != null)
                            {
                                float distance = location.CalculateDistance(fromX, toX);
                                if (distance > 0f)
                                {
                                    var itemSystem = this._hub.GetSystem("itemSystem") as ItemSystem;
                                    var inventorySystem = this._hub.GetSystem("inventorySystem") as InventorySystem;
                                    var inventory = inventorySystem?.GetUnitInventory(unit.Id);
                                    var equippedItems = inventorySystem?.GetUnitEquippedItems(unit.Id);
                                    int speedPercent = unit.GetMovementSpeed(itemSystem, inventory, equippedItems);
                                    float speedModifier = speedPercent / 100f;
                                    int travelTimeMs = location.CalculateTravelTime(fromX, toX, speedModifier);
                                    if (travelTimeMs > 0)
                                    {
                                        _playerSystem.RequestTimeAdvance(travelTimeMs, "이동");
                                    }
                                }
                            }
                        }
                    }

                    // 은신 상태 해제 (앉기/눕기 시 은신 불가)
                    if (unit.TraversalContext.Props.Get("status:stealth") != 0)
                    {
                        unit.TraversalContext.Props.Set("status:stealth", 0);
                        Godot.GD.Print($"[morld] sit_on: unit={unitId} stealth cleared (sitting/lying)");
                    }

                    Godot.GD.Print($"[morld] sit_on: unit={unitId} sat on object={objectId}, seat={seatName}, x={toX}");
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

                    // 4. 캐릭터 posture 초기화 (기본: 서기) - 모든 posture 제거
                    var postureProps = unit.TraversalContext.Props.GetByType("posture").ToList();
                    if (postureProps.Count >= 2)
                    {
                        Godot.GD.PrintErr($"[morld] stand_up: WARNING - unit={unitId} has {postureProps.Count} posture props (should be <= 1)! Removing all.");
                    }
                    foreach (var postureProp in postureProps)
                    {
                        unit.TraversalContext.Props.Remove(postureProp.Prop);
                    }

                    // 검증: posture가 0개인지 확인 (서있는 상태)
                    var postureCount = unit.TraversalContext.Props.GetByType("posture").Count();
                    if (postureCount != 0)
                    {
                        Godot.GD.PrintErr($"[morld] stand_up: ERROR - unit={unitId} posture count is {postureCount} after removal (expected 0)!");
                    }

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
            // get_vehicle_destinations: 차량 위치에서 직접 연결된 실외 Location 목록
            // get_vehicle_destinations(vehicle_id) → [{region_id, location_id, name, distance}, ...]
            morldModule.ModuleDict["get_vehicle_destinations"] = new PyBuiltinFunction("get_vehicle_destinations", args =>
            {
                if (args.Length < 1)
                    throw PyTypeError.Create("get_vehicle_destinations(vehicle_id) requires 1 argument");

                int vehicleId = args[0].ToInt();

                var result = new PyList();

                var actionSystem = _hub.GetSystem("actionSystem") as ActionSystem;
                if (actionSystem == null) return result;

                var destinations = actionSystem.GetVehicleDestinations(vehicleId);
                foreach (var (regionId, locationId, name, distance) in destinations)
                {
                    var dict = new PyDict();
                    dict["region_id"] = new PyInt(regionId);
                    dict["location_id"] = new PyInt(locationId);
                    dict["name"] = new PyStr(name);
                    dict["distance"] = new PyFloat(distance);
                    result.Append(dict);
                }

                return result;
            });

            // vehicle_relocate: 차량 + 탑승자 일괄 이동 (seated 유지)
            // vehicle_relocate(vehicle_id, region_id, location_id) → int (이동된 유닛 수)
            morldModule.ModuleDict["vehicle_relocate"] = new PyBuiltinFunction("vehicle_relocate", args =>
            {
                if (args.Length < 3)
                    throw PyTypeError.Create("vehicle_relocate(vehicle_id, region_id, location_id) requires 3 arguments");

                int vehicleId = args[0].ToInt();
                int regionId = args[1].ToInt();
                int locationId = args[2].ToInt();

                var actionSystem = _hub.GetSystem("actionSystem") as ActionSystem;
                if (actionSystem == null) return new PyInt(0);

                int movedCount = actionSystem.VehicleRelocate(vehicleId, regionId, locationId);
                return new PyInt(movedCount);
            });

            // reconnect_interior_gate: 대형 차량 내부 Location의 Gate 외부 연결점 변경
            // reconnect_interior_gate(int_region, int_local, new_ext_region, new_ext_local) → bool
            morldModule.ModuleDict["reconnect_interior_gate"] = new PyBuiltinFunction("reconnect_interior_gate", args =>
            {
                if (args.Length < 4)
                    throw PyTypeError.Create("reconnect_interior_gate(int_region, int_local, new_ext_region, new_ext_local) requires 4 arguments");

                int intRegion = args[0].ToInt();
                int intLocal = args[1].ToInt();
                int newExtRegion = args[2].ToInt();
                int newExtLocal = args[3].ToInt();

                var actionSystem = _hub.GetSystem("actionSystem") as ActionSystem;
                if (actionSystem == null) return PyBool.False;

                bool ok = actionSystem.ReconnectInteriorGate(intRegion, intLocal, newExtRegion, newExtLocal);
                return ok ? PyBool.True : PyBool.False;
            });
        }

        #endregion

        #region Time Query API

        /// <summary>
        /// Time Query API 등록 (시간 정보 조회)
        /// </summary>
        private void RegisterTimeQueryAPI(PyModule morldModule)
        {
            // get_game_time: 현재 게임 시간 (밀리초 단위) 반환
            morldModule.ModuleDict["get_game_time"] = new PyBuiltinFunction("get_game_time", args =>
            {
                var _worldSystem = this._hub.GetSystem("worldSystem") as WorldSystem;
                var time = _worldSystem.GetTime();
                return new PyInt(time.MillisOfDay);
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
                result["year"] = new PyInt(time.Year);
                result["month"] = new PyInt(time.Month);
                result["day"] = new PyInt(time.Day);
                result["weekday"] = new PyStr(time.WeekdayName);
                result["hour"] = new PyInt(time.Hour);
                result["minute"] = new PyInt(time.Minute);

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
                result["weather"] = new PyStr(weather);
                result["region_name"] = new PyStr(regionName);
                result["location_name"] = new PyStr(locationName);

                // Pi-World 정보: geometry (0=ring, 1=line)
                result["geometry"] = new PyInt(geometry);
                result["position_x"] = new PyFloat(positionX);
                result["location_length"] = new PyFloat(locationLength);

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
                unit.JobList.FillFromSchedule(schedule, time.MillisOfDay, GameTime.MillisPerDay, currentLoc.RegionId, currentLoc.LocalId);
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

                // DES 호환: move job의 duration이 0 이하면 이동 시간 자동 계산
                // Python은 이동 시간을 모르므로 duration=0으로 삽입하고,
                // C#이 PathFinder/CalculateTravelTime으로 최소 이동 시간을 설정한다.
                if (job.Action == "move" && job.Duration <= 0)
                {
                    job.Duration = EstimateMoveTravelTime(unit, job);
                }

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

                // DES 호환: move job duration 자동 계산
                if (job.Action == "move" && job.Duration <= 0)
                {
                    job.Duration = EstimateMoveTravelTime(unit, job);
                }

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

                // DES 호환: move job duration 자동 계산
                if (job.Action == "move" && job.Duration <= 0)
                {
                    job.Duration = EstimateMoveTravelTime(unit, job);
                }

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
        /// Python survival.process_time_elapsed(player_id, millis) 호출
        /// </summary>
        private void ProcessSurvivalTimeElapsed(int millis)
        {
            try
            {
                var playerSystem = _hub.GetSystem("playerSystem") as PlayerSystem;
                if (playerSystem == null)
                    return;

                int playerId = playerSystem.PlayerId;

                // Python survival 모듈의 process_time_elapsed 호출
                Execute($"import survival; survival.process_time_elapsed({playerId}, {millis})");
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
