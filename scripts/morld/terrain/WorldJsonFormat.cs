namespace Morld;

using System.Collections.Generic;
using System.Text.Json.Serialization;

#region JSON Data Classes

/// <summary>
/// World JSON 데이터
/// </summary>
public class WorldJsonData
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("regions")]
    public List<RegionJsonData> Regions { get; set; } = new();

    [JsonPropertyName("regionEdges")]
    public List<RegionEdgeJsonData> RegionEdges { get; set; } = new();
}

/// <summary>
/// Region JSON 데이터
/// </summary>
public class RegionJsonData
{
    [JsonPropertyName("id")]
    public int Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("locations")]
    public List<LocationJsonData> Locations { get; set; } = new();

    [JsonPropertyName("edges")]
    public List<EdgeJsonData> Edges { get; set; } = new();
}

/// <summary>
/// Location JSON 데이터
/// </summary>
public class LocationJsonData
{
    [JsonPropertyName("id")]
    public int Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }
}

/// <summary>
/// Edge JSON 데이터
/// </summary>
public class EdgeJsonData
{
    [JsonPropertyName("a")]
    public int A { get; set; }

    [JsonPropertyName("b")]
    public int B { get; set; }

    [JsonPropertyName("timeAtoB")]
    public float? TimeAtoB { get; set; }

    [JsonPropertyName("timeBtoA")]
    public float? TimeBtoA { get; set; }

    [JsonPropertyName("conditionsAtoB")]
    public Dictionary<string, int>? ConditionsAtoB { get; set; }

    [JsonPropertyName("conditionsBtoA")]
    public Dictionary<string, int>? ConditionsBtoA { get; set; }

    [JsonPropertyName("isBlocked")]
    public bool IsBlocked { get; set; }
}

/// <summary>
/// RegionEdge JSON 데이터
/// </summary>
public class RegionEdgeJsonData
{
    [JsonPropertyName("id")]
    public int Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("regionA")]
    public int RegionA { get; set; }

    [JsonPropertyName("localA")]
    public int LocalA { get; set; }

    [JsonPropertyName("regionB")]
    public int RegionB { get; set; }

    [JsonPropertyName("localB")]
    public int LocalB { get; set; }

    [JsonPropertyName("timeAtoB")]
    public float? TimeAtoB { get; set; }

    [JsonPropertyName("timeBtoA")]
    public float? TimeBtoA { get; set; }

    [JsonPropertyName("conditionsAtoB")]
    public Dictionary<string, int>? ConditionsAtoB { get; set; }

    [JsonPropertyName("conditionsBtoA")]
    public Dictionary<string, int>? ConditionsBtoA { get; set; }

    [JsonPropertyName("isBlocked")]
    public bool IsBlocked { get; set; }
}

#endregion
