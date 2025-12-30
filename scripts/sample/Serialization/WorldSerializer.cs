// namespace PathFinding.Serialization;

// using System;
// using System.Collections.Generic;
// using System.Linq;
// using System.Text.Json;
// using System.Text.Json.Serialization;
// using Morld;
// using PathFinding.Game;
// using Godot;

// #region JSON Models

// /// <summary>
// /// 전체 저장 데이터 (통합)
// /// </summary>
// public class GameSaveData
// {
//     [JsonPropertyName("world")]
//     public WorldData? World { get; set; }

//     [JsonPropertyName("npcs")]
//     public List<NPCData> NPCs { get; set; } = new();

//     [JsonPropertyName("gameTime")]
//     public GameTimeData? GameTime { get; set; }

//     [JsonPropertyName("settings")]
//     public GameSettingsData? Settings { get; set; }
// }

// /// <summary>
// /// 세계 데이터 (World + GameTime + Settings)
// /// </summary>
// public class WorldSaveData
// {
//     [JsonPropertyName("world")]
//     public WorldData? World { get; set; }

//     [JsonPropertyName("gameTime")]
//     public GameTimeData? GameTime { get; set; }

//     [JsonPropertyName("settings")]
//     public GameSettingsData? Settings { get; set; }
// }

// /// <summary>
// /// NPC 데이터 (NPC 목록)
// /// </summary>
// public class NPCSaveData
// {
//     [JsonPropertyName("npcs")]
//     public List<NPCData> NPCs { get; set; } = new();
// }

// /// <summary>
// /// World 데이터
// /// </summary>
// public class WorldData
// {
//     [JsonPropertyName("name")]
//     public string? Name { get; set; }

//     [JsonPropertyName("regions")]
//     public List<RegionData> Regions { get; set; } = new();

//     [JsonPropertyName("regionEdges")]
//     public List<RegionEdgeData> RegionEdges { get; set; } = new();
// }

// /// <summary>
// /// Region 데이터
// /// </summary>
// public class RegionData
// {
//     [JsonPropertyName("id")]
//     public int Id { get; set; }

//     [JsonPropertyName("name")]
//     public string? Name { get; set; }

//     [JsonPropertyName("locations")]
//     public List<LocationData> Locations { get; set; } = new();

//     [JsonPropertyName("edges")]
//     public List<EdgeData> Edges { get; set; } = new();
// }

// /// <summary>
// /// Location 데이터
// /// </summary>
// public class LocationData
// {
//     [JsonPropertyName("id")]
//     public int Id { get; set; }

//     [JsonPropertyName("name")]
//     public string? Name { get; set; }
// }

// /// <summary>
// /// Edge 데이터
// /// </summary>
// public class EdgeData
// {
//     [JsonPropertyName("a")]
//     public int LocationA { get; set; }

//     [JsonPropertyName("b")]
//     public int LocationB { get; set; }

//     [JsonPropertyName("timeAtoB")]
//     public int TravelTimeAtoB { get; set; }

//     [JsonPropertyName("timeBtoA")]
//     public int TravelTimeBtoA { get; set; }

//     [JsonPropertyName("conditionsAtoB")]
//     public Dictionary<string, int>? ConditionsAtoB { get; set; }

//     [JsonPropertyName("conditionsBtoA")]
//     public Dictionary<string, int>? ConditionsBtoA { get; set; }

//     [JsonPropertyName("blocked")]
//     public bool IsBlocked { get; set; }
// }

// /// <summary>
// /// RegionEdge 데이터
// /// </summary>
// public class RegionEdgeData
// {
//     [JsonPropertyName("id")]
//     public int Id { get; set; }

//     [JsonPropertyName("name")]
//     public string? Name { get; set; }

//     [JsonPropertyName("regionA")]
//     public int RegionA { get; set; }

//     [JsonPropertyName("localA")]
//     public int LocalA { get; set; }

//     [JsonPropertyName("regionB")]
//     public int RegionB { get; set; }

//     [JsonPropertyName("localB")]
//     public int LocalB { get; set; }

//     [JsonPropertyName("timeAtoB")]
//     public int TravelTimeAtoB { get; set; }

//     [JsonPropertyName("timeBtoA")]
//     public int TravelTimeBtoA { get; set; }

//     [JsonPropertyName("conditionsAtoB")]
//     public Dictionary<string, int>? ConditionsAtoB { get; set; }

//     [JsonPropertyName("conditionsBtoA")]
//     public Dictionary<string, int>? ConditionsBtoA { get; set; }

//     [JsonPropertyName("blocked")]
//     public bool IsBlocked { get; set; }
// }

// /// <summary>
// /// NPC 데이터
// /// </summary>
// public class NPCData
// {
//     [JsonPropertyName("id")]
//     public string Id { get; set; } = "";

//     [JsonPropertyName("name")]
//     public string Name { get; set; } = "";

//     [JsonPropertyName("regionId")]
//     public int RegionId { get; set; }

//     [JsonPropertyName("locationId")]
//     public int LocationId { get; set; }

//     [JsonPropertyName("tags")]
//     public Dictionary<string, int>? Tags { get; set; }

//     [JsonPropertyName("schedule")]
//     public List<ScheduleEntryData> Schedule { get; set; } = new();
// }

// /// <summary>
// /// 스케줄 항목 데이터
// /// </summary>
// public class ScheduleEntryData
// {
//     [JsonPropertyName("name")]
//     public string Name { get; set; } = "";

//     [JsonPropertyName("regionId")]
//     public int RegionId { get; set; }

//     [JsonPropertyName("locationId")]
//     public int LocationId { get; set; }

//     [JsonPropertyName("start")]
//     public int Start { get; set; }

//     [JsonPropertyName("end")]
//     public int End { get; set; }
// }

// /// <summary>
// /// 게임 시간 데이터
// /// </summary>
// public class GameTimeData
// {
//     [JsonPropertyName("month")]
//     public int Month { get; set; } = 1;

//     [JsonPropertyName("day")]
//     public int Day { get; set; } = 1;

//     [JsonPropertyName("hour")]
//     public int Hour { get; set; } = 6;

//     [JsonPropertyName("minute")]
//     public int Minute { get; set; } = 0;
// }

// /// <summary>
// /// 게임 설정 데이터
// /// </summary>
// public class GameSettingsData
// {
//     [JsonPropertyName("stepMinutes")]
//     public int StepMinutes { get; set; } = 15;
// }

// #endregion

// #region Validation

// /// <summary>
// /// NPC 검증 결과
// /// </summary>
// public class NPCValidationResult
// {
//     public bool IsValid => Errors.Count == 0;
//     public List<string> Errors { get; } = new();
//     public List<string> Warnings { get; } = new();

//     public void AddError(string message) => Errors.Add(message);
//     public void AddWarning(string message) => Warnings.Add(message);

//     public void Merge(NPCValidationResult other)
//     {
//         Errors.AddRange(other.Errors);
//         Warnings.AddRange(other.Warnings);
//     }

//     public override string ToString()
//     {
//         if (IsValid && Warnings.Count == 0)
//             return "Validation passed";

//         var lines = new List<string>();
//         if (Errors.Count > 0)
//         {
//             lines.Add($"Errors ({Errors.Count}):");
//             lines.AddRange(Errors.Select(e => $"  ✗ {e}"));
//         }
//         if (Warnings.Count > 0)
//         {
//             lines.Add($"Warnings ({Warnings.Count}):");
//             lines.AddRange(Warnings.Select(w => $"  ⚠ {w}"));
//         }
//         return string.Join(System.Environment.NewLine, lines);
//     }
// }

// #endregion

// #region Serializer

// /// <summary>
// /// World/NPC JSON 직렬화/역직렬화
// /// </summary>
// public static class WorldSerializer
// {
//     private static readonly JsonSerializerOptions _jsonOptions = new()
//     {
//         WriteIndented = true,
//         DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
//         PropertyNamingPolicy = JsonNamingPolicy.CamelCase
//     };

//     #region Export - 통합

//     /// <summary>
//     /// GameWorld를 단일 JSON 파일로 저장
//     /// </summary>
//     public static void SaveToFile(GameWorld gameWorld, string filePath)
//     {
//         var data = ExportAll(gameWorld);
//         var json = JsonSerializer.Serialize(data, _jsonOptions);

//         // Godot FileAccess 사용
//         using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Write);
//         if (file == null)
//         {
//             throw new InvalidOperationException($"Failed to open file for writing: {filePath}");
//         }
//         file.StoreString(json);
//     }

//     /// <summary>
//     /// GameWorld를 JSON 문자열로 변환
//     /// </summary>
//     public static string SaveToString(GameWorld gameWorld)
//     {
//         var data = ExportAll(gameWorld);
//         return JsonSerializer.Serialize(data, _jsonOptions);
//     }

//     /// <summary>
//     /// GameWorld를 GameSaveData로 변환
//     /// </summary>
//     public static GameSaveData ExportAll(GameWorld gameWorld)
//     {
//         var data = new GameSaveData
//         {
//             World = ExportWorld(gameWorld.World),
//             GameTime = ExportGameTime(gameWorld.CurrentTime),
//             Settings = new GameSettingsData { StepMinutes = gameWorld.StepMinutes }
//         };

//         foreach (var npc in gameWorld.NPCs)
//         {
//             data.NPCs.Add(ExportNPC(npc));
//         }

//         return data;
//     }

//     #endregion

//     #region Export - 분리

//     /// <summary>
//     /// World 데이터를 별도 JSON 파일로 저장
//     /// </summary>
//     public static void SaveWorldToFile(GameWorld gameWorld, string filePath)
//     {
//         var data = ExportWorldData(gameWorld);
//         var json = JsonSerializer.Serialize(data, _jsonOptions);

//         // Godot FileAccess 사용
//         using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Write);
//         if (file == null)
//         {
//             throw new InvalidOperationException($"Failed to open file for writing: {filePath}");
//         }
//         file.StoreString(json);
//     }

//     /// <summary>
//     /// NPC 데이터를 별도 JSON 파일로 저장
//     /// </summary>
//     public static void SaveNPCsToFile(GameWorld gameWorld, string filePath)
//     {
//         var data = ExportNPCData(gameWorld);
//         var json = JsonSerializer.Serialize(data, _jsonOptions);

//         // Godot FileAccess 사용
//         using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Write);
//         if (file == null)
//         {
//             throw new InvalidOperationException($"Failed to open file for writing: {filePath}");
//         }
//         file.StoreString(json);
//     }

//     /// <summary>
//     /// World 데이터 추출 (World + GameTime + Settings)
//     /// </summary>
//     public static WorldSaveData ExportWorldData(GameWorld gameWorld)
//     {
//         return new WorldSaveData
//         {
//             World = ExportWorld(gameWorld.World),
//             GameTime = ExportGameTime(gameWorld.CurrentTime),
//             Settings = new GameSettingsData { StepMinutes = gameWorld.StepMinutes }
//         };
//     }

//     /// <summary>
//     /// NPC 데이터 추출
//     /// </summary>
//     public static NPCSaveData ExportNPCData(GameWorld gameWorld)
//     {
//         var data = new NPCSaveData();
//         foreach (var npc in gameWorld.NPCs)
//         {
//             data.NPCs.Add(ExportNPC(npc));
//         }
//         return data;
//     }

//     #endregion

//     #region Export Helpers

//     private static WorldData ExportWorld(World world)
//     {
//         var data = new WorldData { Name = world.Name };

//         foreach (var region in world.Regions)
//         {
//             data.Regions.Add(ExportRegion(region));
//         }

//         foreach (var edge in world.RegionEdges)
//         {
//             data.RegionEdges.Add(ExportRegionEdge(edge));
//         }

//         return data;
//     }

//     private static RegionData ExportRegion(Region region)
//     {
//         var data = new RegionData
//         {
//             Id = region.Id,
//             Name = region.Name
//         };

//         foreach (var loc in region.Locations)
//         {
//             data.Locations.Add(new LocationData
//             {
//                 Id = loc.LocalId,
//                 Name = loc.Name
//             });
//         }

//         var processedEdges = new HashSet<string>();
//         foreach (var edge in region.Edges)
//         {
//             var key = $"{Math.Min(edge.LocationA.LocalId, edge.LocationB.LocalId)}-{Math.Max(edge.LocationA.LocalId, edge.LocationB.LocalId)}";
//             if (processedEdges.Contains(key))
//                 continue;
//             processedEdges.Add(key);

//             var edgeData = new EdgeData
//             {
//                 LocationA = edge.LocationA.LocalId,
//                 LocationB = edge.LocationB.LocalId,
//                 TravelTimeAtoB = edge.TravelTimeAtoB,
//                 TravelTimeBtoA = edge.TravelTimeBtoA,
//                 IsBlocked = edge.IsBlocked
//             };

//             if (edge.ConditionsAtoB.Count > 0)
//                 edgeData.ConditionsAtoB = new Dictionary<string, int>(edge.ConditionsAtoB);
//             if (edge.ConditionsBtoA.Count > 0)
//                 edgeData.ConditionsBtoA = new Dictionary<string, int>(edge.ConditionsBtoA);

//             data.Edges.Add(edgeData);
//         }

//         return data;
//     }

//     private static RegionEdgeData ExportRegionEdge(RegionEdge edge)
//     {
//         var data = new RegionEdgeData
//         {
//             Id = edge.Id,
//             Name = edge.Name,
//             RegionA = edge.LocationA.RegionId,
//             LocalA = edge.LocationA.LocalId,
//             RegionB = edge.LocationB.RegionId,
//             LocalB = edge.LocationB.LocalId,
//             TravelTimeAtoB = edge.TravelTimeAtoB,
//             TravelTimeBtoA = edge.TravelTimeBtoA,
//             IsBlocked = edge.IsBlocked
//         };

//         if (edge.ConditionsAtoB.Count > 0)
//             data.ConditionsAtoB = new Dictionary<string, int>(edge.ConditionsAtoB);
//         if (edge.ConditionsBtoA.Count > 0)
//             data.ConditionsBtoA = new Dictionary<string, int>(edge.ConditionsBtoA);

//         return data;
//     }

//     private static NPCData ExportNPC(NPC npc)
//     {
//         var data = new NPCData
//         {
//             Id = npc.Id,
//             Name = npc.Name,
//             RegionId = npc.CurrentLocation.RegionId,
//             LocationId = npc.CurrentLocation.LocalId
//         };

//         if (npc.TraversalContext.Tags.Count > 0)
//         {
//             data.Tags = new Dictionary<string, int>(npc.TraversalContext.Tags);
//         }

//         foreach (var entry in npc.Schedule.Entries)
//         {
//             data.Schedule.Add(new ScheduleEntryData
//             {
//                 Name = entry.Name,
//                 RegionId = entry.Destination.RegionId,
//                 LocationId = entry.Destination.LocalId,
//                 Start = entry.TimeRange.StartMinute,
//                 End = entry.TimeRange.EndMinute
//             });
//         }

//         return data;
//     }

//     private static GameTimeData ExportGameTime(GameTime time)
//     {
//         return new GameTimeData
//         {
//             Month = time.Month,
//             Day = time.Day,
//             Hour = time.Hour,
//             Minute = time.Minute
//         };
//     }

//     #endregion

//     #region Import - 통합

//     /// <summary>
//     /// 단일 JSON 파일에서 GameWorld 로드
//     /// </summary>
//     public static GameWorld LoadFromFile(string filePath)
//     {
//         // Godot FileAccess 사용
//         using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Read);
//         if (file == null)
//         {
//             throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
//         }
//         var json = file.GetAsText();
//         return LoadFromString(json);
//     }

//     /// <summary>
//     /// JSON 문자열에서 GameWorld 로드
//     /// </summary>
//     public static GameWorld LoadFromString(string json)
//     {
//         var data = JsonSerializer.Deserialize<GameSaveData>(json, _jsonOptions);
//         if (data == null)
//             throw new InvalidOperationException("Failed to parse JSON data");

//         return ImportAll(data);
//     }

//     /// <summary>
//     /// GameSaveData에서 GameWorld 생성
//     /// </summary>
//     public static GameWorld ImportAll(GameSaveData data)
//     {
//         var world = ImportWorld(data.World ?? throw new InvalidOperationException("World data is required"));

//         var stepMinutes = data.Settings?.StepMinutes ?? 15;
//         var gameWorld = new GameWorld(world, stepMinutes);

//         if (data.GameTime != null)
//         {
//             gameWorld.SetTime(
//                 data.GameTime.Month,
//                 data.GameTime.Day,
//                 data.GameTime.Hour,
//                 data.GameTime.Minute);
//         }

//         foreach (var npcData in data.NPCs)
//         {
//             ImportNPC(gameWorld, npcData);
//         }

//         return gameWorld;
//     }

//     #endregion

//     #region Import - 분리

//     /// <summary>
//     /// World 파일에서 GameWorld 로드 (NPC 없음)
//     /// </summary>
//     public static GameWorld LoadWorldFromFile(string filePath)
//     {
//         // Godot FileAccess 사용
//         using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Read);
//         if (file == null)
//         {
//             throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
//         }
//         var json = file.GetAsText();
//         var data = JsonSerializer.Deserialize<WorldSaveData>(json, _jsonOptions);
//         if (data == null)
//             throw new InvalidOperationException("Failed to parse World JSON data");

//         return ImportWorldData(data);
//     }

//     /// <summary>
//     /// WorldSaveData에서 GameWorld 생성
//     /// </summary>
//     public static GameWorld ImportWorldData(WorldSaveData data)
//     {
//         var world = ImportWorld(data.World ?? throw new InvalidOperationException("World data is required"));

//         var stepMinutes = data.Settings?.StepMinutes ?? 15;
//         var gameWorld = new GameWorld(world, stepMinutes);

//         if (data.GameTime != null)
//         {
//             gameWorld.SetTime(
//                 data.GameTime.Month,
//                 data.GameTime.Day,
//                 data.GameTime.Hour,
//                 data.GameTime.Minute);
//         }

//         return gameWorld;
//     }

//     /// <summary>
//     /// NPC 파일에서 NPC 목록 로드 및 GameWorld에 추가
//     /// </summary>
//     public static NPCValidationResult LoadNPCsFromFile(GameWorld gameWorld, string filePath)
//     {
//         // Godot FileAccess 사용
//         using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Read);
//         if (file == null)
//         {
//             throw new InvalidOperationException($"Failed to open file for reading: {filePath}");
//         }
//         var json = file.GetAsText();
//         var data = JsonSerializer.Deserialize<NPCSaveData>(json, _jsonOptions);
//         if (data == null)
//             throw new InvalidOperationException("Failed to parse NPC JSON data");

//         return ImportNPCData(gameWorld, data);
//     }

//     /// <summary>
//     /// NPCSaveData에서 NPC 목록을 GameWorld에 추가
//     /// </summary>
//     public static NPCValidationResult ImportNPCData(GameWorld gameWorld, NPCSaveData data)
//     {
//         var result = new NPCValidationResult();

//         foreach (var npcData in data.NPCs)
//         {
//             var npcValidation = ValidateNPCData(gameWorld.World, npcData);
//             result.Merge(npcValidation);

//             if (npcValidation.IsValid)
//             {
//                 ImportNPC(gameWorld, npcData);
//             }
//         }

//         return result;
//     }

//     #endregion

//     #region Validation

//     /// <summary>
//     /// NPC 데이터 검증 (World 기준)
//     /// </summary>
//     public static NPCValidationResult ValidateNPCData(World world, NPCData npcData)
//     {
//         var result = new NPCValidationResult();
//         var npcId = npcData.Id;

//         // 1. NPC 시작 위치 검증
//         var startLocation = world.GetLocation(npcData.RegionId, npcData.LocationId);
//         if (startLocation == null)
//         {
//             result.AddError($"[{npcId}] 시작 위치가 존재하지 않음: Region={npcData.RegionId}, Location={npcData.LocationId}");
//         }

//         // 2. 스케줄 검증
//         for (int i = 0; i < npcData.Schedule.Count; i++)
//         {
//             var entry = npcData.Schedule[i];
//             var entryResult = ValidateScheduleEntry(world, npcId, i, entry);
//             result.Merge(entryResult);
//         }

//         // 3. 스케줄 시간 겹침 검증
//         var overlapResult = ValidateScheduleOverlap(npcId, npcData.Schedule);
//         result.Merge(overlapResult);

//         return result;
//     }

//     /// <summary>
//     /// 스케줄 항목 검증
//     /// </summary>
//     private static NPCValidationResult ValidateScheduleEntry(World world, string npcId, int index, ScheduleEntryData entry)
//     {
//         var result = new NPCValidationResult();
//         var prefix = $"[{npcId}] 스케줄[{index}] \"{entry.Name}\"";

//         // 목적지 위치 검증
//         var destLocation = world.GetLocation(entry.RegionId, entry.LocationId);
//         if (destLocation == null)
//         {
//             result.AddError($"{prefix}: 목적지가 존재하지 않음 - Region={entry.RegionId}, Location={entry.LocationId}");
//         }

//         // 시간 범위 검증
//         if (entry.Start < 0 || entry.Start >= 1440)
//         {
//             result.AddError($"{prefix}: 시작 시간이 유효하지 않음 - {entry.Start} (0~1439)");
//         }
//         if (entry.End < 0 || entry.End >= 1440)
//         {
//             result.AddError($"{prefix}: 종료 시간이 유효하지 않음 - {entry.End} (0~1439)");
//         }

//         // 같은 시작/종료 시간 경고
//         if (entry.Start == entry.End)
//         {
//             result.AddWarning($"{prefix}: 시작과 종료 시간이 동일함 - {entry.Start}");
//         }

//         return result;
//     }

//     /// <summary>
//     /// 스케줄 시간 겹침 검증
//     /// </summary>
//     private static NPCValidationResult ValidateScheduleOverlap(string npcId, List<ScheduleEntryData> schedule)
//     {
//         var result = new NPCValidationResult();

//         for (int i = 0; i < schedule.Count; i++)
//         {
//             for (int j = i + 1; j < schedule.Count; j++)
//             {
//                 var a = schedule[i];
//                 var b = schedule[j];

//                 if (TimeRangesOverlap(a.Start, a.End, b.Start, b.End))
//                 {
//                     result.AddWarning($"[{npcId}] 스케줄 시간 겹침: \"{a.Name}\" ({FormatTime(a.Start)}~{FormatTime(a.End)}) <-> \"{b.Name}\" ({FormatTime(b.Start)}~{FormatTime(b.End)})");
//                 }
//             }
//         }

//         return result;
//     }

//     /// <summary>
//     /// 두 시간 범위가 겹치는지 확인
//     /// </summary>
//     private static bool TimeRangesOverlap(int startA, int endA, int startB, int endB)
//     {
//         bool aSpansMidnight = startA > endA;
//         bool bSpansMidnight = startB > endB;

//         if (!aSpansMidnight && !bSpansMidnight)
//         {
//             // 둘 다 자정 안 넘음
//             return startA < endB && startB < endA;
//         }
//         else if (aSpansMidnight && !bSpansMidnight)
//         {
//             // A만 자정 넘음
//             return startB < endA || endB > startA;
//         }
//         else if (!aSpansMidnight && bSpansMidnight)
//         {
//             // B만 자정 넘음
//             return startA < endB || endA > startB;
//         }
//         else
//         {
//             // 둘 다 자정 넘음 - 무조건 겹침
//             return true;
//         }
//     }

//     /// <summary>
//     /// 시간 포맷팅 (분 -> HH:MM)
//     /// </summary>
//     private static string FormatTime(int minutes)
//     {
//         return $"{minutes / 60:D2}:{minutes % 60:D2}";
//     }

//     /// <summary>
//     /// NPC 파일 전체 검증 (로드하지 않고 검증만)
//     /// </summary>
//     public static NPCValidationResult ValidateNPCFile(World world, string filePath)
//     {
//         // Godot FileAccess 사용
//         using var file = FileAccess.Open(filePath, FileAccess.ModeFlags.Read);
//         if (file == null)
//         {
//             var errorResult = new NPCValidationResult();
//             errorResult.AddError($"Failed to open file for reading: {filePath}");
//             return errorResult;
//         }
//         var json = file.GetAsText();
//         var data = JsonSerializer.Deserialize<NPCSaveData>(json, _jsonOptions);
//         if (data == null)
//         {
//             var errorResult = new NPCValidationResult();
//             errorResult.AddError("Failed to parse NPC JSON data");
//             return errorResult;
//         }

//         var result = new NPCValidationResult();
//         foreach (var npcData in data.NPCs)
//         {
//             var npcValidation = ValidateNPCData(world, npcData);
//             result.Merge(npcValidation);
//         }

//         return result;
//     }

//     #endregion

//     #region Import Helpers

//     private static World ImportWorld(WorldData data)
//     {
//         var world = new World(data.Name);

//         foreach (var regionData in data.Regions)
//         {
//             var region = ImportRegion(regionData);
//             world.AddRegion(region);
//         }

//         foreach (var edgeData in data.RegionEdges)
//         {
//             var edge = world.AddRegionEdge(
//                 edgeData.Id,
//                 edgeData.RegionA, edgeData.LocalA,
//                 edgeData.RegionB, edgeData.LocalB,
//                 edgeData.TravelTimeAtoB,
//                 edgeData.TravelTimeBtoA);

//             edge.Name = edgeData.Name;
//             edge.IsBlocked = edgeData.IsBlocked;

//             if (edgeData.ConditionsAtoB != null)
//             {
//                 foreach (var (tag, value) in edgeData.ConditionsAtoB)
//                     edge.AddConditionAtoB(tag, value);
//             }
//             if (edgeData.ConditionsBtoA != null)
//             {
//                 foreach (var (tag, value) in edgeData.ConditionsBtoA)
//                     edge.AddConditionBtoA(tag, value);
//             }
//         }

//         return world;
//     }

//     private static Region ImportRegion(RegionData data)
//     {
//         var region = new Region(data.Id, data.Name);

//         foreach (var locData in data.Locations)
//         {
//             region.AddLocation(locData.Id, locData.Name);
//         }

//         foreach (var edgeData in data.Edges)
//         {
//             var edge = region.AddEdge(
//                 edgeData.LocationA,
//                 edgeData.LocationB,
//                 edgeData.TravelTimeAtoB,
//                 edgeData.TravelTimeBtoA);

//             edge.IsBlocked = edgeData.IsBlocked;

//             if (edgeData.ConditionsAtoB != null)
//             {
//                 foreach (var (tag, value) in edgeData.ConditionsAtoB)
//                     edge.AddConditionAtoB(tag, value);
//             }
//             if (edgeData.ConditionsBtoA != null)
//             {
//                 foreach (var (tag, value) in edgeData.ConditionsBtoA)
//                     edge.AddConditionBtoA(tag, value);
//             }
//         }

//         return region;
//     }

//     private static void ImportNPC(GameWorld gameWorld, NPCData data)
//     {
//         var npc = gameWorld.AddNPC(data.Id, data.Name, data.RegionId, data.LocationId);

//         if (data.Tags != null)
//         {
//             foreach (var (tag, value) in data.Tags)
//             {
//                 npc.TraversalContext.SetTag(tag, value);
//             }
//         }

//         foreach (var entryData in data.Schedule)
//         {
//             npc.Schedule.AddEntry(
//                 entryData.Name,
//                 entryData.RegionId,
//                 entryData.LocationId,
//                 entryData.Start,
//                 entryData.End);
//         }
//     }

//     #endregion
// }

// #endregion
