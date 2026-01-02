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

        public ScriptSystem()
        {
            _interpreter = new IntegratedPythonInterpreter();
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
        /// 모놀로그 스크립트 로드
        /// </summary>
        public void LoadMonologueScripts()
        {
            Godot.GD.Print("[ScriptSystem] Loading monologue scripts...");
            try
            {
                // 파일 내용을 읽어서 Execute로 직접 실행 (ExecuteFile 대신)
                string code;
                var filePath = "res://scripts/python/monologues.py";

                using var file = Godot.FileAccess.Open(filePath, Godot.FileAccess.ModeFlags.Read);
                if (file == null)
                {
                    var error = Godot.FileAccess.GetOpenError();
                    Godot.GD.PrintErr($"[ScriptSystem] Failed to open monologue file: {filePath} (Error: {error})");
                    return;
                }
                code = file.GetAsText();

                Godot.GD.Print($"[ScriptSystem] Monologue file loaded, {code.Length} chars");
                Godot.GD.Print($"[ScriptSystem] First 200 chars: {code.Substring(0, System.Math.Min(200, code.Length))}");

                // Execute로 직접 실행 (전역 스코프에 함수 등록)
                var execResult = Execute(code);
                Godot.GD.Print($"[ScriptSystem] Execute result: {execResult?.GetType().Name} = {execResult}");

                Godot.GD.Print("[ScriptSystem] Monologue scripts loaded successfully.");

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
        /// Python 함수 호출 (BBCode script: prefix용)
        /// </summary>
        /// <param name="functionName">호출할 함수 이름</param>
        /// <param name="args">콜론으로 구분된 인자들</param>
        /// <returns>함수 실행 결과 (문자열 변환)</returns>
        public string CallFunction(string functionName, string[] args)
        {
            Godot.GD.Print($"[ScriptSystem] CallFunction: {functionName}({string.Join(", ", args)})");

            try
            {
                // 인자를 Python 형태로 변환
                var pyArgs = new System.Collections.Generic.List<string>();
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

                // 결과를 문자열로 변환
                if (result is PyString pyStr)
                {
                    Godot.GD.Print($"[ScriptSystem] Returning PyString: {pyStr.Value}");
                    return pyStr.Value;
                }
                else if (result is PyInt pyInt)
                {
                    Godot.GD.Print($"[ScriptSystem] Returning PyInt: {pyInt.Value}");
                    return pyInt.Value.ToString();
                }
                else if (result is PyNone)
                {
                    Godot.GD.Print($"[ScriptSystem] Returning PyNone (null)");
                    return null;
                }
                else
                {
                    Godot.GD.Print($"[ScriptSystem] Returning other: {result?.ToString() ?? "null"}");
                    return result?.ToString() ?? "";
                }
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] CallFunction error: {ex.Message}");
                return $"Error: {ex.Message}";
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
        /// 이벤트 트리거 - Python on_event() 호출
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
}
