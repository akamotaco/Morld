namespace Morld;

using System;
using System.Collections.Generic;

/// <summary>
/// NxN 인접 행렬에서 Region을 생성하는 빌더
/// </summary>
public class RegionBuilder
{
    private readonly int _regionId;
    private readonly int _size;
    private readonly float[,] _matrix;
    private readonly Dictionary<(int, int), Dictionary<string, int>> _conditionsAtoB = new();
    private readonly string?[] _locationNames;
    private string? _regionName;

    /// <summary>
    /// Region ID
    /// </summary>
    public int RegionId => _regionId;

    /// <summary>
    /// Location 수
    /// </summary>
    public int Size => _size;

    /// <summary>
    /// RegionBuilder 생성자
    /// </summary>
    /// <param name="regionId">Region 고유 ID</param>
    /// <param name="size">Location 수 (NxN 행렬)</param>
    public RegionBuilder(int regionId, int size)
    {
        if (size <= 0)
            throw new ArgumentException("Size must be positive", nameof(size));

        _regionId = regionId;
        _size = size;
        _matrix = new float[size, size];
        _locationNames = new string?[size];

        // 초기화: 모든 연결을 -1로 (이동 불가)
        for (int i = 0; i < size; i++)
            for (int j = 0; j < size; j++)
                _matrix[i, j] = -1;
    }

    /// <summary>
    /// 기존 인접 행렬로 빌더 생성
    /// </summary>
    /// <param name="regionId">Region 고유 ID</param>
    /// <param name="matrix">인접 행렬 (0 이하: 이동 불가, 양수: 이동 시간)</param>
    public RegionBuilder(int regionId, float[,] matrix)
    {
        if (matrix.GetLength(0) != matrix.GetLength(1))
            throw new ArgumentException("Matrix must be square (NxN)");

        _regionId = regionId;
        _size = matrix.GetLength(0);
        _matrix = new float[_size, _size];
        _locationNames = new string?[_size];

        // 행렬 복사 (양수만 복사, 나머지는 -1)
        for (int i = 0; i < _size; i++)
        {
            for (int j = 0; j < _size; j++)
            {
                _matrix[i, j] = matrix[i, j] > 0 ? matrix[i, j] : -1;
            }
        }
    }

    /// <summary>
    /// Region 이름 설정
    /// </summary>
    public RegionBuilder SetRegionName(string name)
    {
        _regionName = name;
        return this;
    }

    /// <summary>
    /// Location 이름 설정
    /// </summary>
    public RegionBuilder SetLocationName(int localId, string name)
    {
        ValidateLocalId(localId);
        _locationNames[localId] = name;
        return this;
    }

    /// <summary>
    /// 양방향 동일한 이동 시간 설정
    /// </summary>
    public RegionBuilder SetTravelTime(int localIdA, int localIdB, float travelTime)
    {
        ValidateLocalId(localIdA);
        ValidateLocalId(localIdB);

        _matrix[localIdA, localIdB] = travelTime;
        _matrix[localIdB, localIdA] = travelTime;
        return this;
    }

    /// <summary>
    /// 방향별 다른 이동 시간 설정
    /// </summary>
    public RegionBuilder SetTravelTime(int localIdA, int localIdB, float travelTimeAtoB, float travelTimeBtoA)
    {
        ValidateLocalId(localIdA);
        ValidateLocalId(localIdB);

        _matrix[localIdA, localIdB] = travelTimeAtoB;
        _matrix[localIdB, localIdA] = travelTimeBtoA;
        return this;
    }

    /// <summary>
    /// 단방향 이동 시간 설정
    /// </summary>
    public RegionBuilder SetOneWayTravelTime(int fromId, int toId, float travelTime)
    {
        ValidateLocalId(fromId);
        ValidateLocalId(toId);

        _matrix[fromId, toId] = travelTime;
        return this;
    }

    /// <summary>
    /// 연결 제거
    /// </summary>
    public RegionBuilder RemoveConnection(int localIdA, int localIdB)
    {
        ValidateLocalId(localIdA);
        ValidateLocalId(localIdB);

        _matrix[localIdA, localIdB] = -1;
        _matrix[localIdB, localIdA] = -1;
        return this;
    }

    /// <summary>
    /// A → B 방향 조건 추가
    /// </summary>
    public RegionBuilder AddCondition(int fromId, int toId, string tag, int requiredValue)
    {
        ValidateLocalId(fromId);
        ValidateLocalId(toId);

        var key = (fromId, toId);
        if (!_conditionsAtoB.ContainsKey(key))
            _conditionsAtoB[key] = new Dictionary<string, int>();

        _conditionsAtoB[key][tag] = requiredValue;
        return this;
    }

    /// <summary>
    /// 양방향 동일한 조건 추가
    /// </summary>
    public RegionBuilder AddConditionBoth(int localIdA, int localIdB, string tag, int requiredValue)
    {
        AddCondition(localIdA, localIdB, tag, requiredValue);
        AddCondition(localIdB, localIdA, tag, requiredValue);
        return this;
    }

    /// <summary>
    /// Region 빌드
    /// </summary>
    public Region Build()
    {
        var region = new Region(_regionId, _regionName);

        // Location 생성
        for (int i = 0; i < _size; i++)
        {
            region.AddLocation(i, _locationNames[i]);
        }

        // Edge 생성 (중복 방지를 위해 i < j인 경우만 처리)
        for (int i = 0; i < _size; i++)
        {
            for (int j = i + 1; j < _size; j++)
            {
                var timeAtoB = _matrix[i, j];
                var timeBtoA = _matrix[j, i];

                // 양방향 모두 연결이 없으면 스킵 (둘 다 0 미만)
                if (timeAtoB < 0 && timeBtoA < 0)
                    continue;

                var edge = region.AddEdge(i, j, timeAtoB, timeBtoA);

                // 조건 추가
                if (_conditionsAtoB.TryGetValue((i, j), out var condAtoB))
                {
                    foreach (var (tag, value) in condAtoB)
                        edge.AddConditionAtoB(tag, value);
                }

                if (_conditionsAtoB.TryGetValue((j, i), out var condBtoA))
                {
                    foreach (var (tag, value) in condBtoA)
                        edge.AddConditionBtoA(tag, value);
                }
            }
        }

        return region;
    }

    /// <summary>
    /// 현재 인접 행렬 반환 (디버깅용)
    /// </summary>
    public float[,] GetMatrix()
    {
        var copy = new float[_size, _size];
        Array.Copy(_matrix, copy, _matrix.Length);
        return copy;
    }

    private void ValidateLocalId(int id)
    {
        if (id < 0 || id >= _size)
            throw new ArgumentOutOfRangeException(nameof(id), $"Local ID must be between 0 and {_size - 1}");
    }
}
