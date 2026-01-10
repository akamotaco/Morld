using SharpPy;
using Morld;

namespace SE
{
    /// <summary>
    /// ScriptSystem - Generator 처리 함수
    ///
    /// Python Generator 기반 Dialog 처리:
    /// - ProcessGenerator: Generator 첫 실행 및 yield 값 처리
    /// - ResumeGenerator: 사용자 입력 후 Generator 재개 (문자열)
    /// - ResumeGeneratorWithPyObject: Generator 재개 (PyObject)
    /// - CallProcCallback: @proc: 패턴 콜백 호출
    /// </summary>
    public partial class ScriptSystem
    {
        /// <summary>
        /// 제너레이터 처리 - MessageBox/Dialog yield 감지
        /// </summary>
        public ScriptResult ProcessGenerator(PyGenerator generator)
        {
            try
            {
                // 제너레이터의 첫 번째 yield 값 가져오기
                var yieldedValue = generator.Next();

                Godot.GD.Print($"[ScriptSystem] Generator yielded: {yieldedValue.GetType().Name ?? "null"}");

                // PyDialogRequest yield인 경우 (새 통합 API)
                if (yieldedValue is PyDialogRequest dialogRequest)
                {
                    var pageInfo = dialogRequest.Pages.Count > 1
                        ? $" (page {dialogRequest.CurrentPageIndex + 1}/{dialogRequest.Pages.Count})"
                        : "";
                    Godot.GD.Print($"[ScriptSystem] Dialog request{pageInfo}: {dialogRequest.Text.Substring(0, System.Math.Min(50, dialogRequest.Text.Length))}...");
                    return new GeneratorScriptResult
                    {
                        Type = "generator_dialog",
                        Generator = generator,
                        DialogText = dialogRequest.Text,
                        DialogRequest = dialogRequest
                    };
                }

                // 다른 값이 yield된 경우 (추후 확장 가능)
                Godot.GD.Print($"[ScriptSystem] Generator yielded unknown type: {yieldedValue.GetType().Name}");
                return new ScriptResult { Type = "message", Message = yieldedValue.ToString() ?? "" };
            }
            catch (PythonException ex) when (ex.PyException is PyStopIteration stopIter)
            {
                // 제너레이터가 완료됨 (yield 없이 return)
                Godot.GD.Print($"[ScriptSystem] Generator completed with value: {stopIter.Value}");

                // StopIteration.value가 결과
                var returnValue = stopIter.Value;
                if (returnValue is PyDict dict)
                {
                    return ParseDictResult(dict);
                }
                else if (returnValue is PyString pyStr)
                {
                    return new ScriptResult { Type = "message", Message = pyStr.Value };
                }
                else if (returnValue is PyNone || returnValue == null)
                {
                    return null;
                }
                return new ScriptResult { Type = "message", Message = returnValue.ToString() ?? "" };
            }
        }

        /// <summary>
        /// 제너레이터에 결과를 전달하고 계속 실행
        /// MetaActionHandler에서 다이얼로그 결과 전달 시 호출
        /// </summary>
        public ScriptResult ResumeGenerator(PyGenerator generator, string result)
        {
            try
            {
                Godot.GD.Print($"[ScriptSystem] Resuming generator with result: {result}");

                // 결과를 Python 문자열로 변환하여 send()
                var pyResult = new PyString(result);
                var yieldedValue = generator.Send(pyResult);

                Godot.GD.Print($"[ScriptSystem] Generator resumed, yielded: {yieldedValue.GetType().Name ?? "null"}");

                // 또 다른 Dialog yield인 경우 (새 통합 API)
                if (yieldedValue is PyDialogRequest dialogRequest)
                {
                    var pageInfo = dialogRequest.Pages.Count > 1
                        ? $" (page {dialogRequest.CurrentPageIndex + 1}/{dialogRequest.Pages.Count})"
                        : "";
                    Godot.GD.Print($"[ScriptSystem] Dialog request{pageInfo}: {dialogRequest.Text.Substring(0, System.Math.Min(50, dialogRequest.Text.Length))}...");
                    return new GeneratorScriptResult
                    {
                        Type = "generator_dialog",
                        Generator = generator,
                        DialogText = dialogRequest.Text,
                        DialogRequest = dialogRequest
                    };
                }

                // 다른 값이 yield된 경우
                return new ScriptResult { Type = "message", Message = yieldedValue.ToString() ?? "" };
            }
            catch (PythonException ex) when (ex.PyException is PyStopIteration stopIter)
            {
                // 제너레이터가 완료됨
                Godot.GD.Print($"[ScriptSystem] Generator completed after resume with value: {stopIter.Value}");

                var returnValue = stopIter.Value;
                if (returnValue is PyDict dict)
                {
                    return ParseDictResult(dict);
                }
                else if (returnValue is PyString pyStr)
                {
                    return new ScriptResult { Type = "message", Message = pyStr.Value };
                }
                else if (returnValue is PyNone || returnValue == null)
                {
                    return null;
                }
                return new ScriptResult { Type = "message", Message = returnValue.ToString() ?? "" };
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] ResumeGenerator error: {ex.Message}");
                return new ScriptResult { Type = "error", Message = ex.Message };
            }
        }

        /// <summary>
        /// 제너레이터에 PyObject 결과를 직접 전달하고 계속 실행
        /// @finish 처리 시 result 파라미터(PyObject) 전달용
        /// </summary>
        public ScriptResult ResumeGeneratorWithPyObject(PyGenerator generator, PyObject result)
        {
            try
            {
                Godot.GD.Print($"[ScriptSystem] Resuming generator with PyObject: {result.GetTypeName()}");

                // PyObject를 직접 send()
                var yieldedValue = generator.Send(result);

                Godot.GD.Print($"[ScriptSystem] Generator resumed, yielded: {yieldedValue.GetType().Name ?? "null"}");

                // 또 다른 Dialog yield인 경우
                if (yieldedValue is PyDialogRequest dialogRequest)
                {
                    var pageInfo = dialogRequest.Pages.Count > 1
                        ? $" (page {dialogRequest.CurrentPageIndex + 1}/{dialogRequest.Pages.Count})"
                        : "";
                    Godot.GD.Print($"[ScriptSystem] Dialog request{pageInfo}: {dialogRequest.Text.Substring(0, System.Math.Min(50, dialogRequest.Text.Length))}...");
                    return new GeneratorScriptResult
                    {
                        Type = "generator_dialog",
                        Generator = generator,
                        DialogText = dialogRequest.Text,
                        DialogRequest = dialogRequest
                    };
                }

                // 다른 값이 yield된 경우
                return new ScriptResult { Type = "message", Message = yieldedValue.ToString() ?? "" };
            }
            catch (PythonException ex) when (ex.PyException is PyStopIteration stopIter)
            {
                // 제너레이터가 완료됨
                Godot.GD.Print($"[ScriptSystem] Generator completed after resume with value: {stopIter.Value}");

                var returnValue = stopIter.Value;
                if (returnValue is PyDict dict)
                {
                    return ParseDictResult(dict);
                }
                else if (returnValue is PyString pyStr)
                {
                    return new ScriptResult { Type = "message", Message = pyStr.Value };
                }
                else if (returnValue is PyNone || returnValue == null)
                {
                    return null;
                }
                return new ScriptResult { Type = "message", Message = returnValue.ToString() ?? "" };
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] ResumeGeneratorWithPyObject error: {ex.Message}");
                return new ScriptResult { Type = "error", Message = ex.Message };
            }
        }

        /// <summary>
        /// proc 콜백 함수 호출 (dialogEx의 proc 파라미터)
        /// @proc:값 클릭 시 호출되어 새 텍스트 반환 또는 종료 신호
        /// </summary>
        /// <param name="procCallback">Python 콜백 함수</param>
        /// <param name="value">@proc:값에서 추출한 값</param>
        /// <returns>(새 텍스트, 종료 여부) - 텍스트가 null이고 shouldFinish가 false면 변경 없음</returns>
        public (string newText, bool shouldFinish) CallProcCallback(PyObject procCallback, string value)
        {
            if (procCallback == null)
            {
                return (null, false);
            }

            try
            {
                Godot.GD.Print($"[ScriptSystem] Calling proc callback with value: {value}");

                // Python 함수 호출
                var pyValue = new PyString(value);
                var result = procCallback.Call(new PyObject[] { pyValue }, null);

                // 결과 처리:
                // - None/null/False: 변경 없음, 다이얼로그 유지
                // - True: 다이얼로그 종료
                // - str: 텍스트 업데이트, 다이얼로그 유지
                if (result is PyNone || result == null)
                {
                    Godot.GD.Print("[ScriptSystem] proc callback returned None");
                    return (null, false);
                }

                if (result is PyBool pyBool)
                {
                    bool boolValue = pyBool.IsTrue();
                    Godot.GD.Print($"[ScriptSystem] proc callback returned bool: {boolValue}");
                    return (null, boolValue);  // True면 종료, False면 유지
                }

                var newText = result.AsString();
                Godot.GD.Print($"[ScriptSystem] proc callback returned: {newText.Substring(0, System.Math.Min(50, newText.Length))}...");
                return (newText, false);
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] CallProcCallback error: {ex.Message}");
                return (null, false);
            }
        }
    }
}
