namespace Morld;

using System;
using System.Collections.Generic;

/// <summary>
/// Location 내의 통과 지점 (Pi-World)
/// Location 간 연결을 담당
/// Gate는 Location 내 특정 위치(X, Y)에 존재하며, 다른 Location의 Gate와 연결됨
/// 통과는 즉시 이루어지며, 이동 시간은 캐릭터 위치에서 Gate까지의 거리로 계산
/// </summary>
public class Gate
{
    private bool _isBlocked;

    /// <summary>
    /// Gate ID (Location 내에서 고유)
    /// </summary>
    public int Id { get; }

    /// <summary>
    /// 소속 Location 참조
    /// </summary>
    public LocationRef OwnerLocation { get; }

    /// <summary>
    /// Gate의 X 좌표 (Location 내 위치)
    /// Line: 거리, Ring: 각도
    /// </summary>
    public float X { get; set; }

    /// <summary>
    /// Gate의 Y 좌표 (확장용, 현재 미사용)
    /// </summary>
    public float Y { get; set; } = 0f;

    /// <summary>
    /// 연결된 Location
    /// </summary>
    public LocationRef ConnectedLocation { get; }

    /// <summary>
    /// Gate 통과 시 도착 X 좌표
    /// </summary>
    public float ArrivalX { get; set; }

    /// <summary>
    /// Gate 통과 시 도착 Y 좌표 (확장용, 기본값 0)
    /// </summary>
    public float ArrivalY { get; set; } = 0f;

    /// <summary>
    /// Forward 방향 (이 Gate → 연결된 Gate) 통과 조건
    /// Forward 통과 조건
    /// </summary>
    public Dictionary<string, int> ConditionsForward { get; } = new();

    /// <summary>
    /// Backward 방향 (연결된 Gate → 이 Gate) 통과 조건
    /// Backward 통과 조건
    /// </summary>
    public Dictionary<string, int> ConditionsBackward { get; } = new();

    /// <summary>
    /// Gate 차단 여부
    /// </summary>
    public bool IsBlocked
    {
        get => _isBlocked;
        set
        {
            if (_isBlocked != value)
            {
                _isBlocked = value;
                OwnerRegion?.MarkAsChanged();
            }
        }
    }

    /// <summary>
    /// Gate 이름 (표시용)
    /// </summary>
    public string Name { get; set; } = "";

    /// <summary>
    /// 추가 데이터
    /// </summary>
    public object? Tag { get; set; }

    /// <summary>
    /// 소속 Region 참조 (변경 추적용)
    /// </summary>
    internal Region? OwnerRegion { get; set; }

    /// <summary>
    /// Gate 생성
    /// </summary>
    /// <param name="id">Gate ID (Location 내 고유)</param>
    /// <param name="ownerLocation">소속 Location</param>
    /// <param name="x">X 좌표</param>
    /// <param name="connectedLocation">연결된 Location</param>
    /// <param name="arrivalX">도착 X 좌표</param>
    /// <param name="arrivalY">도착 Y 좌표 (기본값 0)</param>
    public Gate(int id, LocationRef ownerLocation, float x, LocationRef connectedLocation, float arrivalX, float arrivalY = 0f)
    {
        Id = id;
        OwnerLocation = ownerLocation;
        X = x;
        ConnectedLocation = connectedLocation;
        ArrivalX = arrivalX;
        ArrivalY = arrivalY;
    }

    /// <summary>
    /// Forward 방향 조건 추가
    /// </summary>
    public Gate AddConditionForward(string tag, int requiredValue)
    {
        ConditionsForward[tag] = requiredValue;
        OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// Backward 방향 조건 추가
    /// </summary>
    public Gate AddConditionBackward(string tag, int requiredValue)
    {
        ConditionsBackward[tag] = requiredValue;
        OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// 양방향 동일한 조건 추가
    /// </summary>
    public Gate AddCondition(string tag, int requiredValue)
    {
        ConditionsForward[tag] = requiredValue;
        ConditionsBackward[tag] = requiredValue;
        OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// Forward 방향 조건 제거
    /// </summary>
    public Gate RemoveConditionForward(string tag)
    {
        if (ConditionsForward.Remove(tag))
            OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// Backward 방향 조건 제거
    /// </summary>
    public Gate RemoveConditionBackward(string tag)
    {
        if (ConditionsBackward.Remove(tag))
            OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// 양방향 조건 제거
    /// </summary>
    public Gate RemoveCondition(string tag)
    {
        bool changed = ConditionsForward.Remove(tag);
        changed |= ConditionsBackward.Remove(tag);
        if (changed)
            OwnerRegion?.MarkAsChanged();
        return this;
    }

    /// <summary>
    /// Forward 방향으로 통과 가능한지 확인 (이 Gate → 연결된 Gate)
    /// </summary>
    public bool CanTraverseForward(TraversalContext? context = null)
    {
        if (IsBlocked) return false;
        return CheckConditions(ConditionsForward, context);
    }

    /// <summary>
    /// Backward 방향으로 통과 가능한지 확인 (연결된 Gate → 이 Gate)
    /// </summary>
    public bool CanTraverseBackward(TraversalContext? context = null)
    {
        if (IsBlocked) return false;
        return CheckConditions(ConditionsBackward, context);
    }

    private static bool CheckConditions(Dictionary<string, int> conditions, TraversalContext? context)
    {
        if (conditions.Count == 0) return true;
        if (context == null) return false;

        foreach (var (propName, requiredValue) in conditions)
        {
            if (!context.HasProp(propName, requiredValue))
                return false;
        }
        return true;
    }

    /// <summary>
    /// 이 Gate의 전체 참조
    /// </summary>
    public GateRef GetGateRef() => new(OwnerLocation, Id);

    public override string ToString()
    {
        var name = string.IsNullOrEmpty(Name) ? $"Gate{Id}" : Name;
        return $"{name}@{OwnerLocation}(X={X:F1}) -> {ConnectedLocation}(X={ArrivalX:F1})";
    }
}

/// <summary>
/// Gate 참조 (Location 참조 + Gate ID)
/// </summary>
public readonly struct GateRef : IEquatable<GateRef>
{
    /// <summary>
    /// Gate가 속한 Location
    /// </summary>
    public LocationRef Location { get; }

    /// <summary>
    /// Gate ID
    /// </summary>
    public int GateId { get; }

    public GateRef(LocationRef location, int gateId)
    {
        Location = location;
        GateId = gateId;
    }

    public GateRef(int regionId, int localId, int gateId)
    {
        Location = new LocationRef(regionId, localId);
        GateId = gateId;
    }

    public bool Equals(GateRef other) =>
        Location.Equals(other.Location) && GateId == other.GateId;

    public override bool Equals(object? obj) => obj is GateRef other && Equals(other);

    public override int GetHashCode() => HashCode.Combine(Location, GateId);

    public override string ToString() => $"{Location}:Gate{GateId}";

    public static bool operator ==(GateRef left, GateRef right) => left.Equals(right);
    public static bool operator !=(GateRef left, GateRef right) => !left.Equals(right);
}
