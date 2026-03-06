using System.Collections.Generic;
using SharpPy;

namespace Morld;

/// <summary>
/// 애니메이션 UI 모드
/// </summary>
public enum AnimlogMode
{
    /// <summary>header/footer 보이고 입력 가능 (기본)</summary>
    Normal,
    /// <summary>header/footer 가림 (레터박스), 집중 연출용</summary>
    Lock,
    /// <summary>header/footer 보이지만 입력 불가, 전투용</summary>
    Block
}

/// <summary>
/// 애니메이션 로그 요청 - 실시간 기반 애니메이션 시퀀스
/// Python에서 yield ui.Animlog().play() 호출 시 반환되는 객체
///
/// 사용법:
///   anim = ui.Animlog()
///   anim.text("텍스트")
///   anim.wait(0.5)
///   yield anim.play(mode="lock")
///
/// UI 모드:
///   - normal: header/footer 보이고 입력 가능
///   - lock: header/footer 가림 (레터박스), 집중 연출용
///   - block: header/footer 보이지만 입력 불가, 전투용
/// </summary>
public class PyAnimlogRequest : PyObject
{
    /// <summary>
    /// 애니메이션 스텝 목록
    /// </summary>
    public List<AnimlogStep> Steps { get; }

    /// <summary>
    /// 현재 스텝 인덱스
    /// </summary>
    public int CurrentStepIndex { get; set; } = 0;

    /// <summary>
    /// 현재 스텝 경과 시간 (초)
    /// </summary>
    public float StepElapsedTime { get; set; } = 0f;

    /// <summary>
    /// 현재 표시 중인 텍스트 (누적)
    /// </summary>
    public string DisplayText { get; set; } = "";

    /// <summary>
    /// 현재 text 스텝에서 표시된 문자 수
    /// </summary>
    public int CurrentCharIndex { get; set; } = 0;

    /// <summary>
    /// 재생 속도 배율 (기본 1.0)
    /// </summary>
    public float Scale { get; set; } = 1.0f;

    /// <summary>
    /// UI 모드
    /// </summary>
    public AnimlogMode Mode { get; set; } = AnimlogMode.Normal;

    /// <summary>
    /// 애니메이션 완료 여부
    /// </summary>
    public bool IsCompleted => CurrentStepIndex >= Steps.Count;

    /// <summary>
    /// 현재 스텝 (완료 시 null)
    /// </summary>
    public AnimlogStep? CurrentStep =>
        CurrentStepIndex < Steps.Count ? Steps[CurrentStepIndex] : null;

    public PyAnimlogRequest(List<AnimlogStep> steps, float scale = 1.0f, AnimlogMode mode = AnimlogMode.Normal)
    {
        Steps = steps ?? new List<AnimlogStep>();
        Scale = scale;
        Mode = mode;
    }

    public override string GetTypeName() => "AnimlogRequest";

    public override PyStr ToStr()
    {
        var modeStr = Mode.ToString().ToLower();
        return new PyStr($"<AnimlogRequest steps={Steps.Count} scale={Scale} mode={modeStr}>");
    }

    public override PyStr ToRepr()
    {
        return new PyStr($"AnimlogRequest(steps={Steps.Count}, scale={Scale}, mode={Mode})");
    }
}

/// <summary>
/// 애니메이션 단일 스텝
/// </summary>
public class AnimlogStep
{
    /// <summary>
    /// 스텝 타입: "text", "wait", "callback", "clear"
    /// </summary>
    public string Type { get; set; } = "text";

    // === text 스텝 속성 ===

    /// <summary>
    /// 표시할 텍스트 (text 타입)
    /// </summary>
    public string Content { get; set; } = "";

    /// <summary>
    /// 글자당 초 (설정 시 Speed 무시)
    /// </summary>
    public float? Delay { get; set; }

    /// <summary>
    /// 초당 글자 수 (기본 50)
    /// </summary>
    public float Speed { get; set; } = 50f;

    /// <summary>
    /// true: 이전 텍스트에 누적, false: 화면 교체
    /// </summary>
    public bool Append { get; set; } = true;

    // === wait 스텝 속성 ===

    /// <summary>
    /// 대기 시간 (초)
    /// </summary>
    public float Duration { get; set; }

    // === callback 스텝 속성 ===

    /// <summary>
    /// 호출할 Python 함수
    /// </summary>
    public PyObject? CallbackFunc { get; set; }

    /// <summary>
    /// 위치 인자 (tuple)
    /// </summary>
    public PyObject? CallbackArgs { get; set; }

    /// <summary>
    /// 키워드 인자 (dict)
    /// </summary>
    public PyObject? CallbackKwargs { get; set; }
}
