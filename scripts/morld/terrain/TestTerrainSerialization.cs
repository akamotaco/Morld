namespace Morld;

using System;

/// <summary>
/// World JSON 직렬화/역직렬화 테스트
/// </summary>
public static class TestWorldSerialization
{
    /// <summary>
    /// location_data.json을 로드하고 다시 저장하여 동일성 테스트
    /// </summary>
    public static void TestRoundTrip()
    {
        Console.WriteLine("=== World Serialization Round-Trip Test ===\n");

        try
        {
            // 1. location_data.json 로드
            Console.WriteLine("1. Loading location_data.json...");
            var world = Terrain.LoadFromFile("res://scripts/morld/terrain/location_data.json");
            Console.WriteLine($"   Loaded: {world}");
            Console.WriteLine($"   Regions: {world.RegionCount}");
            Console.WriteLine($"   RegionEdges: {world.RegionEdgeCount}");

            // 2. JSON으로 다시 직렬화
            Console.WriteLine("\n2. Exporting to JSON...");
            var exportedJson = world.ToJson();

            // 3. 직렬화된 JSON을 다시 로드
            Console.WriteLine("\n3. Re-importing from exported JSON...");
            var world2 = Terrain.LoadFromJson(exportedJson);
            Console.WriteLine($"   Re-loaded: {world2}");
            Console.WriteLine($"   Regions: {world2.RegionCount}");
            Console.WriteLine($"   RegionEdges: {world2.RegionEdgeCount}");

            // 4. 비교
            Console.WriteLine("\n4. Comparing...");
            bool isIdentical = CompareWorlds(world, world2);

            if (isIdentical)
            {
                Console.WriteLine("   ✓ SUCCESS: Import/Export produces identical results!");
            }
            else
            {
                Console.WriteLine("   ✗ FAILED: Import/Export mismatch detected!");
            }

            // 5. 새 파일로 저장 (선택)
            Console.WriteLine("\n5. Saving to location_data_test.json...");
            world2.SaveToFile("res://scripts/morld/terrain/location_data_test.json");
            Console.WriteLine("   Saved successfully!");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"\n✗ ERROR: {ex.Message}");
            Console.WriteLine(ex.StackTrace);
        }

        Console.WriteLine("\n=== Test Complete ===");
    }

    /// <summary>
    /// 두 World 객체 비교
    /// </summary>
    private static bool CompareWorlds(Terrain w1, Terrain w2)
    {
        bool identical = true;

        // Name 비교
        if (w1.Name != w2.Name)
        {
            Console.WriteLine($"   - Name mismatch: '{w1.Name}' vs '{w2.Name}'");
            identical = false;
        }

        // Region 수 비교
        if (w1.RegionCount != w2.RegionCount)
        {
            Console.WriteLine($"   - Region count mismatch: {w1.RegionCount} vs {w2.RegionCount}");
            identical = false;
        }

        // RegionEdge 수 비교
        if (w1.RegionEdgeCount != w2.RegionEdgeCount)
        {
            Console.WriteLine($"   - RegionEdge count mismatch: {w1.RegionEdgeCount} vs {w2.RegionEdgeCount}");
            identical = false;
        }

        // 각 Region 비교
        foreach (var region1 in w1.Regions)
        {
            var region2 = w2.GetRegion(region1.Id);
            if (region2 == null)
            {
                Console.WriteLine($"   - Region {region1.Id} missing in world2");
                identical = false;
                continue;
            }

            if (region1.Name != region2.Name)
            {
                Console.WriteLine($"   - Region {region1.Id} name mismatch: '{region1.Name}' vs '{region2.Name}'");
                identical = false;
            }

            if (region1.LocationCount != region2.LocationCount)
            {
                Console.WriteLine($"   - Region {region1.Id} location count mismatch: {region1.LocationCount} vs {region2.LocationCount}");
                identical = false;
            }

            if (region1.EdgeCount != region2.EdgeCount)
            {
                Console.WriteLine($"   - Region {region1.Id} edge count mismatch: {region1.EdgeCount} vs {region2.EdgeCount}");
                identical = false;
            }
        }

        if (identical)
        {
            Console.WriteLine("   - All basic properties match!");
        }

        return identical;
    }
}
