namespace Morld;

using System.Collections.Generic;
using System.Text.Json.Serialization;

#region JSON Data Classes

/// <summary>
/// Terrain JSON 데이터
/// </summary>
public class TerrainJsonData
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "unknown";

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
    public string Name { get; set; } = "unknown";

    [JsonPropertyName("description")]
    public Dictionary<string, string>? Description { get; set; }

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
    public string Name { get; set; } = "unknown";

    [JsonPropertyName("description")]
    public Dictionary<string, string>? Description { get; set; }

    [JsonPropertyName("inventory")]
    public Dictionary<int, int>? Inventory { get; set; }
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
    public int TimeAtoB { get; set; } = -1;

    [JsonPropertyName("timeBtoA")]
    public int TimeBtoA { get; set; } = -1;

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
    public string Name { get; set; } = "unknown";

    [JsonPropertyName("regionA")]
    public int RegionA { get; set; }

    [JsonPropertyName("localA")]
    public int LocalA { get; set; }

    [JsonPropertyName("regionB")]
    public int RegionB { get; set; }

    [JsonPropertyName("localB")]
    public int LocalB { get; set; }

    [JsonPropertyName("timeAtoB")]
    public int TimeAtoB { get; set; } = -1;

    [JsonPropertyName("timeBtoA")]
    public int TimeBtoA { get; set; } = -1;

    [JsonPropertyName("conditionsAtoB")]
    public Dictionary<string, int>? ConditionsAtoB { get; set; }

    [JsonPropertyName("conditionsBtoA")]
    public Dictionary<string, int>? ConditionsBtoA { get; set; }

    [JsonPropertyName("isBlocked")]
    public bool IsBlocked { get; set; }
}

#endregion
