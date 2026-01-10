using SharpPy;
using Morld;

namespace SE
{
    /// <summary>
    /// ScriptSystem partial - NPC Job API 등록
    ///
    /// NPC Job 관련 API (set_npc_job, set_npc_time_consume)
    /// EventSystem 참조가 필요하므로 별도 메서드로 분리
    /// </summary>
    public partial class ScriptSystem
    {
        /// <summary>
        /// NPC Job 관련 API 등록 (set_npc_job, set_npc_time_consume)
        /// EventSystem 참조가 필요하므로 별도 메서드로 분리
        /// </summary>
        public void RegisterNpcJobAPI()
        {
            Godot.GD.Print("[ScriptSystem] Registering NPC Job API...");

            try
            {
                // 기존 morld 모듈 가져오기
                var morldModule = PyImportSystem.Import("morld");

                // === set_npc_job - NPC Job 설정 (시간 경과 없음) ===
                // morld.set_npc_job(unit_id, action, duration, target_id=None)
                morldModule.ModuleDict["set_npc_job"] = new PyBuiltinFunction("set_npc_job", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("set_npc_job(unit_id, action, duration, target_id=None) requires at least 3 arguments");

                    int unitId = args[0].ToInt();
                    string action = args[1].AsString();
                    int duration = args[2].ToInt();
                    int? targetId = null;
                    if (args.Length >= 4 && args[3] is not PyNone)
                        targetId = args[3].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null || unit.IsObject)
                    {
                        Godot.GD.PrintErr($"[morld.set_npc_job] Unit {unitId} not found or is object");
                        return PyBool.False;
                    }

                    // 이동 중단
                    unit.CurrentEdge = null;
                    unit.RemainingStayTime = 0;

                    // Job 이름 결정
                    string jobName = action switch
                    {
                        "follow" => "따라가기",
                        "flee" => "도망",
                        _ => "대기"
                    };

                    // follow/flee는 target_id 필요 (기본값: 플레이어)
                    if ((action == "follow" || action == "flee") && !targetId.HasValue)
                    {
                        targetId = _playerSystem.PlayerId;
                    }

                    // JobList 클리어 후 새 Job 삽입
                    var job = new Morld.Job
                    {
                        Name = jobName,
                        Action = action,
                        Duration = duration,
                        TargetId = targetId
                    };
                    unit.JobList.InsertWithClear(job);

#if DEBUG_LOG
                    Godot.GD.Print($"[morld.set_npc_job] Unit {unitId}: action={action}, duration={duration}, target={targetId}");
#endif

                    return PyBool.True;
                });

                // === set_npc_time_consume - NPC Job 설정 + 다이얼로그 시간 경과 ===
                // morld.set_npc_time_consume(unit_id, action, duration, target_id=None)
                // 다이얼로그 이벤트 전용 - lastDialogTime += duration
                morldModule.ModuleDict["set_npc_time_consume"] = new PyBuiltinFunction("set_npc_time_consume", args =>
                {
                    if (args.Length < 3)
                        throw PyTypeError.Create("set_npc_time_consume(unit_id, action, duration, target_id=None) requires at least 3 arguments");

                    int unitId = args[0].ToInt();
                    string action = args[1].AsString();
                    int duration = args[2].ToInt();
                    int? targetId = null;
                    if (args.Length >= 4 && args[3] is not PyNone)
                        targetId = args[3].ToInt();

                    var _unitSystem = this._hub.GetSystem("unitSystem") as UnitSystem;
                    var _playerSystem = this._hub.GetSystem("playerSystem") as PlayerSystem;

                    var unit = _unitSystem.FindUnit(unitId);
                    if (unit == null || unit.IsObject)
                    {
                        Godot.GD.PrintErr($"[morld.set_npc_time_consume] Unit {unitId} not found or is object");
                        return PyBool.False;
                    }

                    // 이동 중단
                    unit.CurrentEdge = null;
                    unit.RemainingStayTime = 0;

                    // Job 이름 결정
                    string jobName = action switch
                    {
                        "follow" => "따라가기",
                        "flee" => "도망",
                        _ => "대기"
                    };

                    // follow/flee는 target_id 필요 (기본값: 플레이어)
                    if ((action == "follow" || action == "flee") && !targetId.HasValue)
                    {
                        targetId = _playerSystem.PlayerId;
                    }

                    // JobList 클리어 후 새 Job 삽입
                    var job = new Morld.Job
                    {
                        Name = jobName,
                        Action = action,
                        Duration = duration,
                        TargetId = targetId
                    };
                    unit.JobList.InsertWithClear(job);

                    // 다이얼로그 시간 경과 설정 (EventSystem에 누적)
                    var _eventSystem = this._hub.GetSystem("eventSystem") as EventSystem;
                    _eventSystem.AddDialogTimeConsumed(duration);

                    // 행동 로그 추가: "XX와 대화했다. XX분이 흘렀다."
                    var _textUISystem = this._hub.GetSystem("textUISystem") as TextUISystem;
                    var npcName = unit.Name ?? "누군가";
                    _textUISystem?.AddActionLog($"{npcName}와(과) 대화했다. {duration}분이 흘렀다.");

#if DEBUG_LOG
                    Godot.GD.Print($"[morld.set_npc_time_consume] Unit {unitId}: action={action}, duration={duration}, target={targetId} (dialog time +{duration})");
#endif

                    return PyBool.True;
                });

                Godot.GD.Print("[ScriptSystem] NPC Job API registered successfully.");
            }
            catch (System.Exception ex)
            {
                Godot.GD.PrintErr($"[ScriptSystem] RegisterNpcJobAPI error: {ex.Message}");
            }
        }
    }
}
