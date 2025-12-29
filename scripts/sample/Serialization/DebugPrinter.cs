namespace PathFinding.Serialization;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Morld;
using PathFinding.Game;

/// <summary>
/// 디버그/시각화용 텍스트 출력
/// </summary>
public static class DebugPrinter
{
    #region World Summary

    /// <summary>
    /// World 전체 요약 출력
    /// </summary>
    public static string PrintWorld(World world, bool includeEdges = true, bool includeRegionEdges = true)
    {
        var sb = new StringBuilder();

        // 헤더
        sb.AppendLine("╔════════════════════════════════════════════════════════════╗");
        sb.AppendLine($"║  WORLD: {world.Name ?? "Unnamed",-49} ║");
        sb.AppendLine("╠════════════════════════════════════════════════════════════╣");
        sb.AppendLine($"║  Regions: {world.RegionCount,-5}  RegionEdges: {world.RegionEdgeCount,-5}                    ║");
        sb.AppendLine("╚════════════════════════════════════════════════════════════╝");
        sb.AppendLine();

        // 각 Region 출력
        foreach (var region in world.Regions.OrderBy(r => r.Id))
        {
            sb.AppendLine(PrintRegion(region, includeEdges));
        }

        // RegionEdges 출력
        if (includeRegionEdges && world.RegionEdgeCount > 0)
        {
            sb.AppendLine(PrintRegionEdges(world));
        }

        return sb.ToString();
    }

    /// <summary>
    /// Region 요약 출력
    /// </summary>
    public static string PrintRegion(Region region, bool includeEdges = true)
    {
        var sb = new StringBuilder();

        // Region 헤더
        sb.AppendLine($"┌─────────────────────────────────────────────────────────────┐");
        sb.AppendLine($"│ Region [{region.Id}]: {region.Name ?? "Unnamed",-44} │");
        sb.AppendLine($"├─────────────────────────────────────────────────────────────┤");
        sb.AppendLine($"│ Locations: {region.LocationCount,-5}  Edges: {region.EdgeCount,-5}                          │");
        sb.AppendLine($"└─────────────────────────────────────────────────────────────┘");

        // Locations 테이블
        sb.AppendLine();
        sb.AppendLine("  Locations:");
        sb.AppendLine("  ┌────────┬────────────────────────────────────────────────┐");
        sb.AppendLine("  │   ID   │ Name                                           │");
        sb.AppendLine("  ├────────┼────────────────────────────────────────────────┤");

        foreach (var loc in region.Locations.OrderBy(l => l.LocalId))
        {
            var name = loc.Name ?? "(unnamed)";
            if (name.Length > 46) name = name.Substring(0, 43) + "...";
            sb.AppendLine($"  │ {loc.LocalId,6} │ {name,-46} │");
        }
        sb.AppendLine("  └────────┴────────────────────────────────────────────────┘");

        // Edges 테이블
        if (includeEdges && region.EdgeCount > 0)
        {
            sb.AppendLine();
            sb.AppendLine("  Edges:");
            sb.AppendLine("  ┌────────┬────────┬──────────┬──────────┬─────────┐");
            sb.AppendLine("  │  From  │   To   │  A → B   │  B → A   │ Blocked │");
            sb.AppendLine("  ├────────┼────────┼──────────┼──────────┼─────────┤");

            var printed = new HashSet<string>();
            foreach (var edge in region.Edges)
            {
                var key = $"{Math.Min(edge.LocationA.LocalId, edge.LocationB.LocalId)}-{Math.Max(edge.LocationA.LocalId, edge.LocationB.LocalId)}";
                if (printed.Contains(key)) continue;
                printed.Add(key);

                var timeAB = edge.TravelTimeAtoB >= 0 ? edge.TravelTimeAtoB.ToString("F1") : "X";
                var timeBA = edge.TravelTimeBtoA >= 0 ? edge.TravelTimeBtoA.ToString("F1") : "X";
                var blocked = edge.IsBlocked ? "Yes" : "-";

                sb.AppendLine($"  │ {edge.LocationA.LocalId,6} │ {edge.LocationB.LocalId,6} │ {timeAB,8} │ {timeBA,8} │ {blocked,7} │");
            }
            sb.AppendLine("  └────────┴────────┴──────────┴──────────┴─────────┘");

            // 조건이 있는 Edge 표시
            var edgesWithConditions = region.Edges
                .Where(e => e.ConditionsAtoB.Count > 0 || e.ConditionsBtoA.Count > 0)
                .GroupBy(e => $"{Math.Min(e.LocationA.LocalId, e.LocationB.LocalId)}-{Math.Max(e.LocationA.LocalId, e.LocationB.LocalId)}")
                .Select(g => g.First())
                .ToList();

            if (edgesWithConditions.Count > 0)
            {
                sb.AppendLine();
                sb.AppendLine("  Edge Conditions:");
                foreach (var edge in edgesWithConditions)
                {
                    if (edge.ConditionsAtoB.Count > 0)
                    {
                        var conds = string.Join(", ", edge.ConditionsAtoB.Select(kv => $"{kv.Key}≥{kv.Value}"));
                        sb.AppendLine($"    {edge.LocationA.LocalId} → {edge.LocationB.LocalId}: {conds}");
                    }
                    if (edge.ConditionsBtoA.Count > 0)
                    {
                        var conds = string.Join(", ", edge.ConditionsBtoA.Select(kv => $"{kv.Key}≥{kv.Value}"));
                        sb.AppendLine($"    {edge.LocationB.LocalId} → {edge.LocationA.LocalId}: {conds}");
                    }
                }
            }
        }

        sb.AppendLine();
        return sb.ToString();
    }

    /// <summary>
    /// RegionEdges 요약 출력
    /// </summary>
    public static string PrintRegionEdges(World world)
    {
        var sb = new StringBuilder();

        sb.AppendLine("┌─────────────────────────────────────────────────────────────┐");
        sb.AppendLine($"│ Region Edges ({world.RegionEdgeCount})                                             │");
        sb.AppendLine("├─────────────────────────────────────────────────────────────┤");
        sb.AppendLine("│  ID  │ Name                 │ From        │ To          │TT │");
        sb.AppendLine("├──────┼──────────────────────┼─────────────┼─────────────┼───┤");

        foreach (var edge in world.RegionEdges.OrderBy(e => e.Id))
        {
            var name = edge.Name ?? "-";
            if (name.Length > 20) name = name.Substring(0, 17) + "...";

            var from = $"R{edge.LocationA.RegionId}:L{edge.LocationA.LocalId}";
            var to = $"R{edge.LocationB.RegionId}:L{edge.LocationB.LocalId}";
            var tt = edge.TravelTimeAtoB >= 0 ? edge.TravelTimeAtoB.ToString("F0") : "X";

            sb.AppendLine($"│ {edge.Id,4} │ {name,-20} │ {from,-11} │ {to,-11} │{tt,3}│");
        }
        sb.AppendLine("└──────┴──────────────────────┴─────────────┴─────────────┴───┘");

        // 조건이 있는 RegionEdge 표시
        var edgesWithConditions = world.RegionEdges
            .Where(e => e.ConditionsAtoB.Count > 0 || e.ConditionsBtoA.Count > 0)
            .ToList();

        if (edgesWithConditions.Count > 0)
        {
            sb.AppendLine();
            sb.AppendLine("  RegionEdge Conditions:");
            foreach (var edge in edgesWithConditions)
            {
                if (edge.ConditionsAtoB.Count > 0)
                {
                    var conds = string.Join(", ", edge.ConditionsAtoB.Select(kv => $"{kv.Key}≥{kv.Value}"));
                    sb.AppendLine($"    [{edge.Id}] {edge.LocationA} → {edge.LocationB}: {conds}");
                }
                if (edge.ConditionsBtoA.Count > 0)
                {
                    var conds = string.Join(", ", edge.ConditionsBtoA.Select(kv => $"{kv.Key}≥{kv.Value}"));
                    sb.AppendLine($"    [{edge.Id}] {edge.LocationB} → {edge.LocationA}: {conds}");
                }
            }
        }

        sb.AppendLine();
        return sb.ToString();
    }

    /// <summary>
    /// World 그래프를 ASCII로 시각화 (간단한 인접 리스트 형태)
    /// </summary>
    public static string PrintWorldGraph(World world)
    {
        var sb = new StringBuilder();

        sb.AppendLine("═══════════════════════════════════════════════════════════════");
        sb.AppendLine($"  WORLD GRAPH: {world.Name ?? "Unnamed"}");
        sb.AppendLine("═══════════════════════════════════════════════════════════════");
        sb.AppendLine();

        foreach (var region in world.Regions.OrderBy(r => r.Id))
        {
            sb.AppendLine($"  Region [{region.Id}] {region.Name ?? ""}");
            sb.AppendLine($"  {"─".PadRight(55, '─')}");

            foreach (var loc in region.Locations.OrderBy(l => l.LocalId))
            {
                var neighbors = region.GetNeighbors(loc);
                var neighborStr = neighbors.Any()
                    ? string.Join(", ", neighbors.Select(n => $"{n.LocalId}"))
                    : "(isolated)";

                sb.AppendLine($"    [{loc.LocalId,2}] {loc.Name ?? "(unnamed)",-25} → {neighborStr}");
            }

            // 이 Region에서 나가는 RegionEdge
            var exits = world.RegionEdges
                .Where(e => e.LocationA.RegionId == region.Id || e.LocationB.RegionId == region.Id)
                .ToList();

            if (exits.Count > 0)
            {
                sb.AppendLine();
                sb.AppendLine("    [Region Exits]");
                foreach (var exit in exits)
                {
                    var isFromThis = exit.LocationA.RegionId == region.Id;
                    var localLoc = isFromThis ? exit.LocationA : exit.LocationB;
                    var remoteLoc = isFromThis ? exit.LocationB : exit.LocationA;
                    var remoteRegion = world.GetRegion(remoteLoc.RegionId);

                    sb.AppendLine($"      L{localLoc.LocalId} ⟷ Region[{remoteLoc.RegionId}] {remoteRegion?.Name ?? ""} (L{remoteLoc.LocalId})");
                }
            }

            sb.AppendLine();
        }

        return sb.ToString();
    }

    #endregion

    #region NPC Summary

    /// <summary>
    /// 전체 NPC 목록 요약 출력
    /// </summary>
    public static string PrintNPCs(GameWorld gameWorld, bool includeSchedule = true)
    {
        var sb = new StringBuilder();

        sb.AppendLine("╔════════════════════════════════════════════════════════════╗");
        sb.AppendLine($"║  NPCs ({gameWorld.NPCCount})                                                   ║");
        sb.AppendLine("╚════════════════════════════════════════════════════════════╝");
        sb.AppendLine();

        foreach (var npc in gameWorld.NPCs.OrderBy(n => n.Id))
        {
            sb.AppendLine(PrintNPC(npc, gameWorld.World, includeSchedule));
        }

        return sb.ToString();
    }

    /// <summary>
    /// 단일 NPC 요약 출력
    /// </summary>
    public static string PrintNPC(NPC npc, World? world = null, bool includeSchedule = true)
    {
        var sb = new StringBuilder();

        // NPC 헤더
        sb.AppendLine($"┌─────────────────────────────────────────────────────────────┐");
        sb.AppendLine($"│ NPC: {npc.Name,-20} ID: {npc.Id,-27} │");
        sb.AppendLine($"├─────────────────────────────────────────────────────────────┤");

        // 현재 상태
        var stateStr = npc.State.ToString();
        var locStr = FormatLocation(npc.CurrentLocation, world);
        sb.AppendLine($"│ State: {stateStr,-10} Location: {locStr,-33} │");

        // 이동 중이면 이동 정보 표시
        if (npc.IsMoving && npc.Movement != null)
        {
            var m = npc.Movement;
            var destStr = FormatLocation(m.FinalDestination, world);
            sb.AppendLine($"│ Moving to: {destStr,-50} │");
            sb.AppendLine($"│ Progress: {m.ProgressPercent,5:F1}%  Remaining: {m.RemainingTime,5:F0} min              │");
        }

        // 현재 스케줄
        if (npc.CurrentSchedule != null)
        {
            var schedName = npc.CurrentSchedule.Name;
            if (schedName.Length > 40) schedName = schedName.Substring(0, 37) + "...";
            sb.AppendLine($"│ Current: {schedName,-52} │");
        }

        // Tags
        if (npc.TraversalContext.Tags.Count > 0)
        {
            var tagsStr = string.Join(", ", npc.TraversalContext.Tags.Select(kv => $"{kv.Key}={kv.Value}"));
            if (tagsStr.Length > 50) tagsStr = tagsStr.Substring(0, 47) + "...";
            sb.AppendLine($"│ Tags: {tagsStr,-55} │");
        }

        sb.AppendLine($"└─────────────────────────────────────────────────────────────┘");

        // 스케줄 출력
        if (includeSchedule && npc.Schedule.Entries.Count > 0)
        {
            sb.AppendLine();
            sb.AppendLine(PrintSchedule(npc.Schedule, world));
        }

        return sb.ToString();
    }

    /// <summary>
    /// NPC 스케줄 출력
    /// </summary>
    public static string PrintSchedule(DailySchedule schedule, World? world = null)
    {
        var sb = new StringBuilder();

        sb.AppendLine("  Schedule:");
        sb.AppendLine("  ┌───────────────┬────────────────────────────┬─────────────────┐");
        sb.AppendLine("  │     Time      │ Activity                   │ Destination     │");
        sb.AppendLine("  ├───────────────┼────────────────────────────┼─────────────────┤");

        foreach (var entry in schedule.Entries)
        {
            var timeStr = FormatTimeRange(entry.TimeRange);
            var name = entry.Name;
            if (name.Length > 26) name = name.Substring(0, 23) + "...";

            var destStr = FormatLocationShort(entry.Destination, world);

            sb.AppendLine($"  │ {timeStr,-13} │ {name,-26} │ {destStr,-15} │");
        }

        sb.AppendLine("  └───────────────┴────────────────────────────┴─────────────────┘");

        return sb.ToString();
    }

    /// <summary>
    /// NPC 현재 상태 간략 출력 (한 줄)
    /// </summary>
    public static string PrintNPCStatus(NPC npc, World? world = null)
    {
        var locStr = FormatLocationShort(npc.CurrentLocation, world);
        var stateStr = npc.IsMoving ? "Moving" : "Idle";

        string activity;
        if (npc.IsMoving && npc.Movement != null)
        {
            var destStr = FormatLocationShort(npc.Movement.FinalDestination, world);
            activity = $"→ {destStr} ({npc.Movement.ProgressPercent:F0}%)";
        }
        else if (npc.CurrentSchedule != null)
        {
            activity = npc.CurrentSchedule.Name;
        }
        else
        {
            activity = "-";
        }

        return $"[{npc.Id}] {npc.Name,-10} @ {locStr,-12} [{stateStr,-6}] {activity}";
    }

    /// <summary>
    /// 전체 NPC 상태 테이블 출력
    /// </summary>
    public static string PrintNPCStatusTable(GameWorld gameWorld)
    {
        var sb = new StringBuilder();

        sb.AppendLine("┌────────────┬────────────┬────────────────┬────────┬──────────────────────────────┐");
        sb.AppendLine("│ ID         │ Name       │ Location       │ State  │ Activity                     │");
        sb.AppendLine("├────────────┼────────────┼────────────────┼────────┼──────────────────────────────┤");

        foreach (var npc in gameWorld.NPCs.OrderBy(n => n.Id))
        {
            var id = npc.Id;
            if (id.Length > 10) id = id.Substring(0, 7) + "...";

            var name = npc.Name;
            if (name.Length > 10) name = name.Substring(0, 7) + "...";

            var locStr = FormatLocationShort(npc.CurrentLocation, gameWorld.World);
            if (locStr.Length > 14) locStr = locStr.Substring(0, 11) + "...";

            var stateStr = npc.IsMoving ? "Moving" : "Idle";

            string activity;
            if (npc.IsMoving && npc.Movement != null)
            {
                var destStr = FormatLocationShort(npc.Movement.FinalDestination, gameWorld.World);
                activity = $"→ {destStr} ({npc.Movement.ProgressPercent:F0}%)";
            }
            else if (npc.CurrentSchedule != null)
            {
                activity = npc.CurrentSchedule.Name;
            }
            else
            {
                activity = "-";
            }
            if (activity.Length > 28) activity = activity.Substring(0, 25) + "...";

            sb.AppendLine($"│ {id,-10} │ {name,-10} │ {locStr,-14} │ {stateStr,-6} │ {activity,-28} │");
        }

        sb.AppendLine("└────────────┴────────────┴────────────────┴────────┴──────────────────────────────┘");

        return sb.ToString();
    }

    #endregion

    #region GameWorld Summary

    /// <summary>
    /// GameWorld 전체 요약 (World + NPC + 시간)
    /// </summary>
    public static string PrintGameWorld(GameWorld gameWorld, bool detailed = false)
    {
        var sb = new StringBuilder();

        // 헤더
        sb.AppendLine("╔════════════════════════════════════════════════════════════════════════╗");
        sb.AppendLine($"║  GAME WORLD SUMMARY                                                    ║");
        sb.AppendLine("╠════════════════════════════════════════════════════════════════════════╣");
        sb.AppendLine($"║  Time: {gameWorld.CurrentTime,-20} Step: {gameWorld.StepMinutes} min                    ║");
        sb.AppendLine($"║  World: {gameWorld.World.Name ?? "Unnamed",-15} Regions: {gameWorld.World.RegionCount,-3} NPCs: {gameWorld.NPCCount,-3}              ║");
        sb.AppendLine("╚════════════════════════════════════════════════════════════════════════╝");
        sb.AppendLine();

        if (detailed)
        {
            sb.AppendLine(PrintWorld(gameWorld.World, includeEdges: true, includeRegionEdges: true));
            sb.AppendLine(PrintNPCs(gameWorld, includeSchedule: true));
        }
        else
        {
            // 간략 버전
            sb.AppendLine("  Regions:");
            foreach (var region in gameWorld.World.Regions.OrderBy(r => r.Id))
            {
                sb.AppendLine($"    [{region.Id}] {region.Name ?? "Unnamed"}: {region.LocationCount} locations");
            }

            sb.AppendLine();
            sb.AppendLine("  NPCs:");
            sb.AppendLine(PrintNPCStatusTable(gameWorld));
        }

        return sb.ToString();
    }

    /// <summary>
    /// 현재 시점의 스냅샷 출력
    /// </summary>
    public static string PrintSnapshot(GameWorld gameWorld)
    {
        var sb = new StringBuilder();

        sb.AppendLine($"═══ Snapshot @ {gameWorld.CurrentTime} ═══");
        sb.AppendLine();
        sb.AppendLine(PrintNPCStatusTable(gameWorld));

        return sb.ToString();
    }

    #endregion

    #region Helpers

    private static string FormatLocation(LocationRef locRef, World? world)
    {
        if (world == null)
            return $"R{locRef.RegionId}:L{locRef.LocalId}";

        var region = world.GetRegion(locRef.RegionId);
        var location = region?.GetLocation(locRef.LocalId);

        if (location?.Name != null)
            return $"{location.Name} (R{locRef.RegionId}:L{locRef.LocalId})";

        return $"R{locRef.RegionId}:L{locRef.LocalId}";
    }

    private static string FormatLocationShort(LocationRef locRef, World? world)
    {
        if (world == null)
            return $"R{locRef.RegionId}:L{locRef.LocalId}";

        var region = world.GetRegion(locRef.RegionId);
        var location = region?.GetLocation(locRef.LocalId);

        if (location?.Name != null)
        {
            var name = location.Name;
            if (name.Length > 12) name = name.Substring(0, 9) + "...";
            return name;
        }

        return $"R{locRef.RegionId}:L{locRef.LocalId}";
    }

    private static string FormatTimeRange(TimeRange range)
    {
        return $"{FormatMinutes(range.StartMinute)}-{FormatMinutes(range.EndMinute)}";
    }

    private static string FormatMinutes(int minutes)
    {
        return $"{minutes / 60:D2}:{minutes % 60:D2}";
    }

    #endregion

    #region Console Output Helpers

    /// <summary>
    /// World 요약을 콘솔에 출력
    /// </summary>
    public static void DumpWorld(World world, bool includeEdges = true)
    {
        Console.WriteLine(PrintWorld(world, includeEdges));
    }

    /// <summary>
    /// NPC 목록을 콘솔에 출력
    /// </summary>
    public static void DumpNPCs(GameWorld gameWorld, bool includeSchedule = true)
    {
        Console.WriteLine(PrintNPCs(gameWorld, includeSchedule));
    }

    /// <summary>
    /// GameWorld 전체를 콘솔에 출력
    /// </summary>
    public static void DumpGameWorld(GameWorld gameWorld, bool detailed = false)
    {
        Console.WriteLine(PrintGameWorld(gameWorld, detailed));
    }

    /// <summary>
    /// 현재 스냅샷을 콘솔에 출력
    /// </summary>
    public static void DumpSnapshot(GameWorld gameWorld)
    {
        Console.WriteLine(PrintSnapshot(gameWorld));
    }

    #endregion
}
