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
            Godot.GD.Print("[ScriptSystem] Loading monologue scripts...");

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
                var filePath = ScenarioPythonPath + "monologues.py";

                using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
                if (file == null)
                {
                    var error = Godot.FileAccess.GetOpenError();
                    Godot.GD.PrintErr($"[ScriptSystem] Failed to open monologue file: {filePath} (Error: {error})");
                    return;
                }
                code = file.GetAsText();

                Godot.GD.Print($"[ScriptSystem] Monologue file loaded from: {filePath} ({code.Length} chars)");
                Godot.GD.Print($"[ScriptSystem] First 200 chars: {code.Substring(0, System.Math.Min(200, code.Length))}");

                // Execute로 직접 실행 (전역 스코프에 함수 등록)
                var execResult = Execute(code);
                Godot.GD.Print($"[ScriptSystem] Execute result: {execResult?.GetType().Name} = {execResult}");

                Godot.GD.Print("[ScriptSystem] Monologue scripts loaded successfully.");

                // events.py 로드 (EventSystem용)
                LoadEventsScript();

                // 테스트: 함수가 정의되었는지 확인 (Eval 모드로 호출)
                var testResult = Eval("get_monologue_page_count('intro_001')");
                Godot.GD.Print($"[ScriptSystem] Test get_monologue_page_count: {testResult?.GetType().Name} = {testResult}");

                // 비교 테스트: RegisterTestFunctions에서 등록한 함수 호출
                var testDialogueResult = Eval("test_dialogue('테스트')");
                Godot.GD.Print($"[ScriptSystem] test_dialogue result: {testDialogueResult?.GetType().Name} = {testDialogueResult}");
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
                var doneCallbackObj = dict.Get(new PyString("done_callback"));
                var cancelCallbackObj = dict.Get(new PyString("cancel_callback"));
                string doneCallback = (doneCallbackObj as PyString)?.Value;
                string cancelCallback = (cancelCallbackObj as PyString)?.Value;

                Godot.GD.Print($"[ScriptSystem] Parsed {type} result: {pages.Count} pages, {timeConsumed}min, button={buttonType}");
                return new MonologueScriptResult
                {
                    Type = type,  // "monologue" 또는 "update"
                    Pages = pages,
                    TimeConsumed = timeConsumed,
                    ButtonType = buttonType,
                    DoneCallback = doneCallback,
                    CancelCallback = cancelCallback
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
    }
}
