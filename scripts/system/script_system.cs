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
        /// Python 코드 실행
        /// </summary>
        public PyObject Execute(string code)
        {
            return _interpreter.Execute(code);
        }

        /// <summary>
        /// Python 파일 실행
        /// </summary>
        public PyObject ExecuteFile(string filePath)
        {
            if (!System.IO.File.Exists(filePath))
            {
                Godot.GD.PrintErr($"[ScriptSystem] File not found: {filePath}");
                return PyNone.Instance;
            }

            var code = System.IO.File.ReadAllText(filePath);
            return _interpreter.Execute(code, filePath, false, false, false);
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
    }
}
