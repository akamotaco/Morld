/*
 * This file is commented out for Godot integration.
 * The code below is a console application demo and is not needed in Godot.
 * Keep it for reference purposes.
 */

/*
using PathFinding.Game;
using PathFinding.Serialization;

Console.WriteLine("=== NPC Daily Schedule Simulation ===\n");

// ============================================
// 1. 분리된 JSON 파일에서 로드
// ============================================
string basePath = Path.Combine(Directory.GetCurrentDirectory(), "Data");

// 개발 환경에서 파일 찾기
if (!Directory.Exists(basePath))
{
    basePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Data");
}

string worldPath = Path.Combine(basePath, "world_data.json");
string npcPath = Path.Combine(basePath, "npc_data.json");

// World 파일 확인
if (!File.Exists(worldPath))
{
    Console.WriteLine($"Error: world_data.json 파일을 찾을 수 없습니다.");
    Console.WriteLine($"검색 경로: {worldPath}");
    return;
}

// NPC 파일 확인
if (!File.Exists(npcPath))
{
    Console.WriteLine($"Error: npc_data.json 파일을 찾을 수 없습니다.");
    Console.WriteLine($"검색 경로: {npcPath}");
    return;
}

// ============================================
// 2. World 로드
// ============================================
Console.WriteLine($"World 로드: {worldPath}");

GameWorld gameWorld;
try
{
    gameWorld = WorldSerializer.LoadWorldFromFile(worldPath);
    Console.WriteLine("✓ World 로드 성공!");
}
catch (Exception ex)
{
    Console.WriteLine($"Error: World 로드 실패 - {ex.Message}");
    return;
}

// ============================================
// 3. NPC 로드 (검증 포함)
// ============================================
Console.WriteLine($"\nNPC 로드: {npcPath}");

// 먼저 검증만 수행
var validationResult = WorldSerializer.ValidateNPCFile(gameWorld.World, npcPath);

if (!validationResult.IsValid)
{
    Console.WriteLine("\n✗ NPC 검증 실패!");
    Console.WriteLine(validationResult);
    return;
}

if (validationResult.Warnings.Count > 0)
{
    Console.WriteLine("\n⚠ 경고 발견:");
    foreach (var warning in validationResult.Warnings)
    {
        Console.WriteLine($"  {warning}");
    }
}

// 검증 통과 후 실제 로드
var loadResult = WorldSerializer.LoadNPCsFromFile(gameWorld, npcPath);
Console.WriteLine($"✓ NPC 로드 성공! ({gameWorld.NPCCount}명)");

// ============================================
// 4. 로드된 정보 출력
// ============================================
Console.WriteLine($"\n{'='} 로드된 데이터 {'='}");
Console.WriteLine($"World: {gameWorld.World.Name}");
Console.WriteLine($"Regions: {gameWorld.World.RegionCount}");
foreach (var region in gameWorld.World.Regions)
{
    Console.WriteLine($"  [{region.Id}] {region.Name}: {region.LocationCount} locations, {region.EdgeCount} edges");
}
Console.WriteLine($"Region Edges: {gameWorld.World.RegionEdgeCount}");

Console.WriteLine($"\nNPCs: {gameWorld.NPCCount}");
foreach (var npc in gameWorld.NPCs)
{
    Console.WriteLine($"  - {npc.Name} @ {npc.CurrentLocation}");
    Console.WriteLine($"    스케줄: {npc.Schedule.Entries.Count}개 항목");
}

Console.WriteLine($"\n시작 시간: {gameWorld.CurrentTime}");
Console.WriteLine($"Step 간격: {gameWorld.StepMinutes}분");

// ============================================
// 5. 이벤트 핸들러 등록
// ============================================
gameWorld.OnNPCMovementStart += (gw, e) =>
{
    var m = e.Movement;
    var scheduleInfo = m.Schedule != null ? $" [{m.Schedule.Name}]" : "";
    Console.WriteLine($"  → {m.NPC.Name} 이동 시작{scheduleInfo}: {m.From} → {m.To}");
};

gameWorld.OnNPCArrival += (gw, e) =>
{
    var a = e.Arrival;
    Console.WriteLine($"  ★ {a.NPC.Name} 도착: {a.Destination}");
};

// ============================================
// 6. 시뮬레이션 실행 (매초 1 step)
// ============================================
Console.WriteLine("\n" + new string('=', 50));
Console.WriteLine("시뮬레이션 시작 (1초 = 15분)");
Console.WriteLine("종료하려면 Ctrl+C를 누르세요");
Console.WriteLine("'s' 키: 현재 상태 저장 (분리)");
Console.WriteLine("'a' 키: 현재 상태 저장 (통합)");
Console.WriteLine("'w' 키: World 정보 출력");
Console.WriteLine("'n' 키: NPC 정보 출력");
Console.WriteLine("'d' 키: 전체 상세 정보 출력");
Console.WriteLine("'g' 키: World 그래프 출력");
Console.WriteLine(new string('=', 50) + "\n");

// 취소 토큰 설정
var cts = new CancellationTokenSource();
Console.CancelKeyPress += (s, e) =>
{
    e.Cancel = true;
    cts.Cancel();
};

int stepCount = 0;
var lastDay = gameWorld.CurrentTime.Day;

try
{
    while (!cts.Token.IsCancellationRequested)
    {
        // 키 입력 확인 (비동기)
        if (Console.KeyAvailable)
        {
            var key = Console.ReadKey(intercept: true);
            if (key.KeyChar == 's' || key.KeyChar == 'S')
            {
                // 분리 저장
                var worldSavePath = Path.Combine(basePath, "world_save.json");
                var npcSavePath = Path.Combine(basePath, "npc_save.json");
                try
                {
                    WorldSerializer.SaveWorldToFile(gameWorld, worldSavePath);
                    WorldSerializer.SaveNPCsToFile(gameWorld, npcSavePath);
                    Console.WriteLine($"\n  [분리 저장됨: world_save.json, npc_save.json]\n");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"\n  [저장 실패: {ex.Message}]\n");
                }
            }
            else if (key.KeyChar == 'a' || key.KeyChar == 'A')
            {
                // 통합 저장
                var savePath = Path.Combine(basePath, "game_save.json");
                try
                {
                    WorldSerializer.SaveToFile(gameWorld, savePath);
                    Console.WriteLine($"\n  [통합 저장됨: game_save.json]\n");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"\n  [저장 실패: {ex.Message}]\n");
                }
            }
            else if (key.KeyChar == 'w' || key.KeyChar == 'W')
            {
                // World 정보 출력
                Console.WriteLine();
                DebugPrinter.DumpWorld(gameWorld.World);
            }
            else if (key.KeyChar == 'n' || key.KeyChar == 'N')
            {
                // NPC 정보 출력
                Console.WriteLine();
                DebugPrinter.DumpNPCs(gameWorld);
            }
            else if (key.KeyChar == 'd' || key.KeyChar == 'D')
            {
                // 전체 상세 정보 출력
                Console.WriteLine();
                DebugPrinter.DumpGameWorld(gameWorld, detailed: true);
            }
            else if (key.KeyChar == 'g' || key.KeyChar == 'G')
            {
                // World 그래프 출력
                Console.WriteLine();
                Console.WriteLine(DebugPrinter.PrintWorldGraph(gameWorld.World));
            }
        }

        // 날짜가 바뀌면 구분선 출력
        if (gameWorld.CurrentTime.Day != lastDay)
        {
            lastDay = gameWorld.CurrentTime.Day;
            Console.WriteLine($"\n{'─'} {gameWorld.CurrentTime.ToDateString()} {'─'}\n");
        }

        // Step 실행
        var result = gameWorld.Step();
        stepCount++;

        // 시간 출력
        Console.WriteLine($"[{result.CurrentTime.ToTimeString()}] Step #{stepCount}");

        // NPC 상태 출력
        foreach (var npc in gameWorld.NPCs)
        {
            string status;
            if (npc.IsMoving && npc.Movement != null)
            {
                status = $"이동중 → {npc.Movement.NextLocation} ({npc.Movement.ProgressPercent:F0}%)";
            }
            else
            {
                status = npc.CurrentSchedule?.Name ?? "대기";
            }
            Console.WriteLine($"    {npc.Name}: {status}");
        }

        // 1초 대기
        Thread.Sleep(1000);

        // 하루가 지나면 요약 출력
        if (stepCount % 96 == 0) // 96 steps = 24시간
        {
            Console.WriteLine($"\n=== {stepCount / 96}일 경과 ===\n");
        }
    }
}
catch (OperationCanceledException)
{
    // 정상 종료
}

// ============================================
// 7. 최종 요약 및 저장
// ============================================
Console.WriteLine($"\n{'='} 시뮬레이션 종료 {'='}");
Console.WriteLine($"총 {stepCount} steps 실행 ({stepCount * gameWorld.StepMinutes}분 = {stepCount * gameWorld.StepMinutes / 60}시간)");
Console.WriteLine($"최종 시간: {gameWorld.CurrentTime}");

Console.WriteLine("\nNPC 최종 상태:");
foreach (var npc in gameWorld.NPCs)
{
    Console.WriteLine($"  {npc.GetStatusSummary()}");
}

// 최종 상태 분리 저장
try
{
    WorldSerializer.SaveWorldToFile(gameWorld, Path.Combine(basePath, "world_final.json"));
    WorldSerializer.SaveNPCsToFile(gameWorld, Path.Combine(basePath, "npc_final.json"));
    Console.WriteLine($"\n최종 상태 저장됨: world_final.json, npc_final.json");
}
catch (Exception ex)
{
    Console.WriteLine($"\n최종 상태 저장 실패: {ex.Message}");
}
*/
