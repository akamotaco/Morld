using ECS;
using SharpPy;
using Morld;

namespace SE
{
    /// <summary>
    /// Python 스크립트 실행을 담당하는 시스템
    /// sharpPy를 통해 Python 코드 실행
    ///
    /// partial 파일 구조:
    /// - script_system.cs: 코어 기능 (생성자, 경로, 실행)
    /// - script_system_morld_api.cs: morld 모듈 기본 API (RegisterMorldModule)
    /// - script_system_data_api.cs: 데이터 조작 API (RegisterDataManipulationAPI)
    /// - script_system_npc_api.cs: NPC Job API (RegisterNpcJobAPI)
    /// - script_system_generator.cs: Generator 처리 (ProcessGenerator, ResumeGenerator)
    /// </summary>
    public partial class ScriptSystem : ECS.System
    {
        private IntegratedPythonInterpreter _interpreter;

        // 시나리오 경로
        private string _scenarioPath = "";
        public string ScenarioPath => _scenarioPath;
        public string ScenarioPythonPath => _scenarioPath + "python/";

        public ScriptSystem()
        {
            _interpreter = new IntegratedPythonInterpreter();

            // 기본 Godot res:// 경로를 sys.path에 추가
            AddGodotPathsToSysPath();

            RegisterMorldModule();
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
                var valueStr = value is PyString vs ? vs.Value : value.ToString() ?? "";
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
        /// PyObject(Dict)를 Job으로 변환
        /// job_dict: {"name": str, "action": str, "region_id": int, "location_id": int, "duration": int, "target_id": int?}
        /// </summary>
        private Morld.Job? PyDictToJob(PyObject obj)
        {
            if (obj is not PyDict dict)
                return null;

            var job = new Morld.Job();

            // name (필수)
            if (dict.Contains(new PyString("name")).Value)
            {
                var nameObj = dict.GetItem(new PyString("name"));
                job.Name = nameObj is PyString ps ? ps.Value : nameObj.ToString() ?? "";
            }

            // action (기본값 "stay")
            if (dict.Contains(new PyString("action")).Value)
            {
                var actionObj = dict.GetItem(new PyString("action"));
                job.Action = actionObj is PyString ps ? ps.Value : actionObj.ToString() ?? "stay";
            }

            // region_id
            if (dict.Contains(new PyString("region_id")).Value)
            {
                job.RegionId = dict.GetItem(new PyString("region_id")).ToInt();
            }

            // location_id
            if (dict.Contains(new PyString("location_id")).Value)
            {
                job.LocationId = dict.GetItem(new PyString("location_id")).ToInt();
            }

            // duration (필수)
            if (dict.Contains(new PyString("duration")).Value)
            {
                job.Duration = dict.GetItem(new PyString("duration")).ToInt();
            }

            // target_id (optional)
            if (dict.Contains(new PyString("target_id")).Value)
            {
                var targetObj = dict.GetItem(new PyString("target_id"));
                if (targetObj != null && targetObj is not PyNone)
                {
                    job.TargetId = targetObj.ToInt();
                }
            }

            // start_offset (optional, Merge용)
            if (dict.Contains(new PyString("start_offset")).Value)
            {
                job.StartOffset = dict.GetItem(new PyString("start_offset")).ToInt();
            }

            return job;
        }

        /// <summary>
        /// Python 리스트를 DailySchedule로 변환
        /// schedule_list: [{"name": str, "region_id": int, "location_id": int, "start": int, "end": int, "activity": str}, ...]
        /// </summary>
        private Morld.DailySchedule? PyListToDailySchedule(PyObject obj)
        {
            if (obj is not PyList list)
                return null;

            var schedule = new Morld.DailySchedule();

            for (int i = 0; i < list.Length(); i++)
            {
                var item = list.GetItem(i);
                if (item is not PyDict dict)
                    continue;

                // name
                string name = "";
                if (dict.Contains(new PyString("name")).Value)
                {
                    var nameObj = dict.GetItem(new PyString("name"));
                    name = nameObj is PyString ps ? ps.Value : nameObj.ToString() ?? "";
                }

                // region_id
                int regionId = 0;
                if (dict.Contains(new PyString("region_id")).Value)
                {
                    regionId = dict.GetItem(new PyString("region_id")).ToInt();
                }
                // regionId 대체 키
                if (dict.Contains(new PyString("regionId")).Value)
                {
                    regionId = dict.GetItem(new PyString("regionId")).ToInt();
                }

                // location_id
                int locationId = 0;
                if (dict.Contains(new PyString("location_id")).Value)
                {
                    locationId = dict.GetItem(new PyString("location_id")).ToInt();
                }
                // locationId 대체 키
                if (dict.Contains(new PyString("locationId")).Value)
                {
                    locationId = dict.GetItem(new PyString("locationId")).ToInt();
                }

                // start
                int start = 0;
                if (dict.Contains(new PyString("start")).Value)
                {
                    start = dict.GetItem(new PyString("start")).ToInt();
                }

                // end
                int end = 0;
                if (dict.Contains(new PyString("end")).Value)
                {
                    end = dict.GetItem(new PyString("end")).ToInt();
                }

                // activity
                string activity = "";
                if (dict.Contains(new PyString("activity")).Value)
                {
                    var actObj = dict.GetItem(new PyString("activity"));
                    activity = actObj is PyString ps ? ps.Value : actObj.ToString() ?? "";
                }

                var entry = new Morld.ScheduleEntry(name, regionId, locationId, start, end, activity);
                schedule.AddEntry(entry);
            }

            return schedule.Entries.Count > 0 ? schedule : null;
        }

        /// <summary>
        /// Job을 PyDict로 변환
        /// </summary>
        private PyDict JobToPyDict(Morld.Job job)
        {
            var dict = new PyDict();
            dict.SetItem(new PyString("name"), new PyString(job.Name ?? ""));
            dict.SetItem(new PyString("action"), new PyString(job.Action ?? "stay"));
            dict.SetItem(new PyString("region_id"), new PyInt(job.RegionId));
            dict.SetItem(new PyString("location_id"), new PyInt(job.LocationId));
            dict.SetItem(new PyString("duration"), new PyInt(job.Duration));
            dict.SetItem(new PyString("target_id"), job.TargetId.HasValue ? new PyInt(job.TargetId.Value) : PyNone.Instance);
            return dict;
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
                result.Add(item is PyString ps ? ps.Value : item.ToString() ?? "");
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
                Godot.GD.Print($"[ScriptSystem] Execute result: {execResult.GetType().Name} = {execResult}");

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
    from characters import get_character_event_handler, get_all_describe_texts
except ImportError:
    get_character_event_handler = lambda unit_id: None
    get_all_describe_texts = lambda unit_ids: []

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

            // ID Generator 리셋 (첫 로드 시에도 1부터 시작하도록)
            IdGenerator.Reset();

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
        /// Python Asset 인스턴스 메서드 호출 (BBCode call: prefix용)
        /// assets.call_instance_method(instance_id, method_name)을 통해 호출
        /// </summary>
        /// <param name="instanceId">인스턴스 ID (Focus의 TargetUnitId)</param>
        /// <param name="methodName">호출할 메서드 이름</param>
        /// <param name="args">메서드 인자 (optional)</param>
        /// <returns>메서드 실행 결과 (ScriptResult)</returns>
        public ScriptResult CallInstanceMethod(int instanceId, string methodName, string[] args = null)
        {
            var argsStr = args != null && args.Length > 0 ? string.Join(", ", args) : "";
            Godot.GD.Print($"[ScriptSystem] CallInstanceMethod: {methodName}({argsStr}) on instance {instanceId}");

            try
            {
                // assets 모듈이 로드되어 있는지 확인하고 import
                Execute("import assets");

                // assets.call_instance_method(instance_id, method_name, *args) 호출
                var argsCode = args != null && args.Length > 0 ? ", " + string.Join(", ", args) : "";
                var code = $"assets.call_instance_method({instanceId}, '{methodName}'{argsCode})";
                Godot.GD.Print($"[ScriptSystem] Evaluating: {code}");

                var result = Eval(code);

                Godot.GD.Print($"[ScriptSystem] Result type: {result.GetType().Name ?? "null"}, value: {result}");

                // 제너레이터인 경우 - yield morld.dialog(...) 지원
                if (result is PyGenerator generator)
                {
                    return ProcessGenerator(generator);
                }

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
                    return new ScriptResult { Type = "message", Message = result.ToString() ?? "" };
                }
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] CallInstanceMethod error: {ex.Message}");
                return new ScriptResult { Type = "error", Message = ex.Message };
            }
        }

        /// <summary>
        /// Python 함수 호출 - 구조화된 결과 반환
        /// </summary>
        /// <param name="functionName">호출할 함수 이름</param>
        /// <param name="args">콜론으로 구분된 인자들</param>
        /// <param name="contextUnitId">현재 Focus의 UnitId (없으면 null)</param>
        /// <returns>함수 실행 결과 (ScriptResult)</returns>
        public ScriptResult CallFunctionEx(string functionName, string[] args, int? contextUnitId = null)
        {
            Godot.GD.Print($"[ScriptSystem] CallFunctionEx: {functionName}({string.Join(", ", args)}) [contextUnitId={contextUnitId.ToString() ?? "null"}]");

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

                Godot.GD.Print($"[ScriptSystem] Result type: {result.GetType().Name ?? "null"}, value: {result}");

                // 제너레이터인 경우 - yield morld.messagebox(...) 지원
                if (result is PyGenerator generator)
                {
                    return ProcessGenerator(generator);
                }

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
                    return new ScriptResult { Type = "message", Message = result.ToString() ?? "" };
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
        /// message 타입만 지원 (monologue 레거시 제거됨)
        /// </summary>
        private ScriptResult ParseDictResult(PyDict dict)
        {
            var typeObj = dict.Get(new PyString("type"));
            var type = (typeObj as PyString)?.Value ?? "message";

            // 메시지 결과 - Get()으로 안전하게 조회
            var messageObj = dict.Get(new PyString("message"));
            var message = (messageObj as PyString)?.Value ?? "";
            return new ScriptResult { Type = type, Message = message };
        }

        /// <summary>
        /// Python 함수 호출 - 문자열 결과 반환 (레거시)
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
        /// 모듈 함수 호출 (인자 없음)
        /// 예: CallModuleFunction("ui", "get_action_text") → ui.get_action_text()
        /// </summary>
        public PyObject CallModuleFunction(string moduleName, string functionName)
        {
            try
            {
                var code = $"import {moduleName}; {moduleName}.{functionName}()";
                return Eval(code);
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] CallModuleFunction error ({moduleName}.{functionName}): {ex.Message}");
                return null;
            }
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
        /// EventSystem용 단일 이벤트 핸들러 호출 - Python on_single_event() 호출
        /// </summary>
        /// <param name="evt">단일 이벤트</param>
        /// <returns>스크립트 결과 (모놀로그 등)</returns>
        public ScriptResult CallSingleEventHandler(Morld.GameEvent evt)
        {
            if (evt == null) return null;

            try
            {
                // 이벤트를 Python 리스트 리터럴로 변환
                var tuple = evt.ToPythonTuple();
                var items = new System.Collections.Generic.List<string>();
                foreach (var item in tuple)
                {
                    if (item is string s)
                        items.Add($"'{s}'");
                    else if (item is int i)
                        items.Add(i.ToString());
                    else
                        items.Add($"'{item.ToString() ?? ""}'");
                }

                var eventLiteral = $"[{string.Join(", ", items)}]";
                var code = $"on_single_event({eventLiteral})";
#if DEBUG_LOG
                Godot.GD.Print($"[ScriptSystem] Evaluating: {code}");
#endif

                // on_single_event() 호출
                var result = Eval(code);

                if (result is PyNone || result == null)
                {
                    return null;
                }

                // PyGenerator 반환 시 ProcessGenerator() 호출
                if (result is PyGenerator generator)
                {
#if DEBUG_LOG
                    Godot.GD.Print($"[ScriptSystem] CallSingleEventHandler: Generator returned, processing...");
#endif
                    return ProcessGenerator(generator);
                }

#if DEBUG_LOG
                Godot.GD.Print($"[ScriptSystem] Unknown event result type: {result.GetType().Name}");
#endif
                return null;
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] CallSingleEventHandler error: {ex.Message}");
                Godot.GD.PrintErr($"[ScriptSystem] Stack trace: {ex.StackTrace}");
                return null;
            }
        }


        /// <summary>
        /// 캐릭터 describe text 조회 - Python get_all_describe_texts() 호출
        /// 플레이어와 같은 위치에 있는 캐릭터들의 상황 묘사 텍스트 반환
        /// </summary>
        /// <param name="unitIds">캐릭터 ID 목록</param>
        /// <returns>describe text 리스트</returns>
        public System.Collections.Generic.List<string> GetCharacterDescribeTexts(
            System.Collections.Generic.List<int> unitIds)
        {
            var result = new System.Collections.Generic.List<string>();
            if (unitIds == null || unitIds.Count == 0) return result;

            try
            {
                // Python 리스트 리터럴 생성
                var idsLiteral = $"[{string.Join(", ", unitIds)}]";
                var code = $"get_all_describe_texts({idsLiteral})";

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
                Godot.GD.PrintErr($"[ScriptSystem] GetCharacterDescribeTexts error: {ex.Message}");
            }

            return result;
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
    /// 스크립트 함수 호출 결과 기본 클래스
    /// </summary>
    public class ScriptResult
    {
        public string Type { get; set; }  // "message", "generator_dialog", "error" 등
        public string Message { get; set; }
    }

    /// <summary>
    /// 제너레이터 스크립트 결과 - Dialog yield 시 반환
    /// 다이얼로그 결과를 generator.Send()로 전달하여 스크립트 재개
    /// </summary>
    public class GeneratorScriptResult : ScriptResult
    {
        /// <summary>
        /// 일시 정지된 제너레이터 (결과 전달 후 재개용)
        /// </summary>
        public PyGenerator Generator { get; set; }

        /// <summary>
        /// yield된 Dialog 텍스트 (현재 페이지)
        /// BBCode URL 포함 (@ret:값, @proc:값 패턴)
        /// </summary>
        public string DialogText { get; set; }

        /// <summary>
        /// 멀티페이지 다이얼로그 요청 객체 (페이지 진행용)
        /// </summary>
        public PyDialogRequest DialogRequest { get; set; }
    }
}
