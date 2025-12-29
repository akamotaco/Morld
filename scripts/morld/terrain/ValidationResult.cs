namespace Morld;

using System;
using System.Collections.Generic;

/// <summary>
/// ID 유효성 검사 결과
/// </summary>
public class ValidationResult
{
    private readonly List<string> _errors = new();
    private readonly List<string> _warnings = new();

    /// <summary>
    /// 오류 목록
    /// </summary>
    public IReadOnlyList<string> Errors => _errors;

    /// <summary>
    /// 경고 목록
    /// </summary>
    public IReadOnlyList<string> Warnings => _warnings;

    /// <summary>
    /// 유효한지 여부 (오류 없음)
    /// </summary>
    public bool IsValid => _errors.Count == 0;

    /// <summary>
    /// 오류 또는 경고가 있는지
    /// </summary>
    public bool HasIssues => _errors.Count > 0 || _warnings.Count > 0;

    /// <summary>
    /// 오류 추가
    /// </summary>
    public void AddError(string message)
    {
        _errors.Add(message);
    }

    /// <summary>
    /// 경고 추가
    /// </summary>
    public void AddWarning(string message)
    {
        _warnings.Add(message);
    }

    /// <summary>
    /// 다른 ValidationResult 병합
    /// </summary>
    public void Merge(ValidationResult other)
    {
        _errors.AddRange(other.Errors);
        _warnings.AddRange(other.Warnings);
    }

    /// <summary>
    /// 결과 요약 문자열
    /// </summary>
    public override string ToString()
    {
        if (!HasIssues)
            return "Validation passed: No issues found.";

        var lines = new List<string>();
        
        if (_errors.Count > 0)
        {
            lines.Add($"Errors ({_errors.Count}):");
            foreach (var err in _errors)
                lines.Add($"  ✗ {err}");
        }

        if (_warnings.Count > 0)
        {
            lines.Add($"Warnings ({_warnings.Count}):");
            foreach (var warn in _warnings)
                lines.Add($"  ⚠ {warn}");
        }

        return string.Join(Environment.NewLine, lines);
    }
}
