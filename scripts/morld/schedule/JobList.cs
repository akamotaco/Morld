namespace Morld;

using System.Collections.Generic;

/// <summary>
/// 유닛의 작업 목록 (시간 기반 선형 리스트)
/// - 시간 경과 시 앞에서부터 duration 잘라냄
/// - Override 삽입 시 기존 job을 잘라서 새 job 끼워넣기
/// </summary>
public class JobList
{
	private readonly LinkedList<Job> _jobs = new();

	/// <summary>
	/// 모든 Job 목록 (읽기 전용)
	/// </summary>
	public IEnumerable<Job> Jobs => _jobs;

	/// <summary>
	/// Job 개수
	/// </summary>
	public int Count => _jobs.Count;

	/// <summary>
	/// 현재 Job (첫 번째)
	/// </summary>
	public Job? Current => _jobs.First?.Value;

	/// <summary>
	/// JobList가 비어있는지
	/// </summary>
	public bool IsEmpty => _jobs.Count == 0;

	/// <summary>
	/// 시간 경과 - 앞에서부터 duration만큼 잘라냄
	/// </summary>
	/// <param name="minutes">경과 시간 (분)</param>
	public void Advance(int minutes)
	{
		if (minutes <= 0) return;

		int remaining = minutes;

		while (remaining > 0 && _jobs.Count > 0)
		{
			var current = _jobs.First!.Value;

			if (current.Duration <= remaining)
			{
				// 현재 Job 완전히 소진
				remaining -= current.Duration;
				_jobs.RemoveFirst();
			}
			else
			{
				// 현재 Job 일부만 소진
				current.Duration -= remaining;
				remaining = 0;
			}
		}
	}

	/// <summary>
	/// Override 삽입 - 현재 시점에 새 job 끼워넣기
	/// 기존 job들은 뒤로 밀리며, 새 job duration만큼 잘림
	/// </summary>
	/// <param name="newJob">삽입할 새 Job</param>
	public void InsertOverride(Job newJob)
	{
		if (newJob == null || newJob.Duration <= 0) return;

		int overrideDuration = newJob.Duration;

		// 1. 기존 Job들에서 override duration만큼 잘라내기
		int toTrim = overrideDuration;
		var node = _jobs.First;

		while (toTrim > 0 && node != null)
		{
			var next = node.Next;
			var job = node.Value;

			if (job.Duration <= toTrim)
			{
				// 이 Job 전체가 잘림
				toTrim -= job.Duration;
				_jobs.Remove(node);
			}
			else
			{
				// 이 Job 일부만 잘림
				job.Duration -= toTrim;
				toTrim = 0;
			}

			node = next;
		}

		// 2. 새 Job을 맨 앞에 삽입
		_jobs.AddFirst(newJob);
	}

	/// <summary>
	/// Merge 삽입 - 시작 시간에 맞춰 빈 공간에 끼워넣기
	/// 기존 job과 겹치면 기존 job 우선 (새 job이 잘림/밀림)
	///
	/// 예시:
	/// [사냥:20분] merge [현재+따라가기:40분] → [사냥:20분 > 따라가기:20분]
	/// [따라가기:48시간] merge [현재+사냥:20분] → [따라가기:48시간] (새 job 무시)
	/// [따라가기:30분] merge [20분후+사냥:40분] → [따라가기:30분 > 사냥:30분]
	/// </summary>
	/// <param name="newJob">삽입할 새 Job (StartOffset으로 시작 시간 지정)</param>
	public void InsertMerge(Job newJob)
	{
		if (newJob == null || newJob.Duration <= 0) return;

		int desiredStart = newJob.StartOffset;
		int newJobDuration = newJob.Duration;

		// 1. 기존 job들의 총 duration 및 삽입 위치 찾기
		int accumulatedTime = 0;
		LinkedListNode<Job>? insertAfterNode = null;

		foreach (var node in IterateNodes())
		{
			int jobEnd = accumulatedTime + node.Value.Duration;

			if (jobEnd <= desiredStart)
			{
				// 이 job은 원하는 시작 시간 전에 끝남 → 다음으로
				accumulatedTime = jobEnd;
				insertAfterNode = node;
			}
			else
			{
				// 이 job이 원하는 시작 시간을 덮음 → 이 job 끝날 때까지 기다려야 함
				accumulatedTime = jobEnd;
				insertAfterNode = node;
				// 계속 탐색해서 완전히 빈 공간 찾기
			}
		}

		// 2. 실제 시작 가능 시간 (기존 job들이 끝난 후)
		int actualStart = System.Math.Max(desiredStart, accumulatedTime);

		// 3. 기존 job들이 원하는 기간을 완전히 덮으면 삽입 안 함
		int desiredEnd = desiredStart + newJobDuration;
		if (actualStart >= desiredEnd)
		{
			// 새 job의 전체 구간이 기존 job에 의해 덮힘
			return;
		}

		// 4. 삽입 가능한 duration 계산 (desiredEnd까지만)
		int insertDuration = desiredEnd - actualStart;

		if (insertDuration <= 0) return;

		// 5. 새 Job 삽입
		var jobToInsert = newJob.Clone();
		jobToInsert.Duration = insertDuration;
		jobToInsert.StartOffset = 0;

		if (insertAfterNode == null)
		{
			_jobs.AddFirst(jobToInsert);
		}
		else
		{
			_jobs.AddAfter(insertAfterNode, jobToInsert);
		}
	}

	/// <summary>
	/// LinkedList 노드 순회용 헬퍼
	/// </summary>
	private System.Collections.Generic.IEnumerable<LinkedListNode<Job>> IterateNodes()
	{
		var node = _jobs.First;
		while (node != null)
		{
			yield return node;
			node = node.Next;
		}
	}

	/// <summary>
	/// 빈 시간 채우기 (Think용) - 스케줄 기반으로 Job 생성
	/// </summary>
	/// <param name="schedule">DailySchedule</param>
	/// <param name="currentTimeOfDay">현재 시간 (분, 0~1439)</param>
	/// <param name="lookAheadMinutes">미리 채울 시간 (분, 기본 1440 = 하루)</param>
	public void FillFromSchedule(DailySchedule? schedule, int currentTimeOfDay, int lookAheadMinutes = 1440)
	{
		if (schedule == null || schedule.Entries.Count == 0) return;

		// 이미 있는 Job들의 총 duration 계산
		int existingDuration = 0;
		foreach (var job in _jobs)
		{
			existingDuration += job.Duration;
		}

		// lookAhead까지 채워야 할 남은 시간
		int needToFill = lookAheadMinutes - existingDuration;
		if (needToFill <= 0) return;

		// 현재 시간 + 기존 Job 시간 = 시작 시점
		int fillStartTime = (currentTimeOfDay + existingDuration) % 1440;

		// 스케줄 엔트리들을 순회하며 Job 생성
		int filled = 0;
		int safetyCounter = 0; // 무한 루프 방지

		while (filled < needToFill && safetyCounter < 100)
		{
			safetyCounter++;

			// 현재 시점의 스케줄 엔트리 찾기
			int checkTime = (fillStartTime + filled) % 1440;
			var entry = schedule.GetEntryAt(checkTime);

			if (entry == null)
			{
				// 스케줄 빈 시간 - 다음 분으로 스킵
				filled++;
				continue;
			}

			// 이 엔트리에서 남은 시간 계산
			int entryRemaining = CalculateRemainingInEntry(entry.TimeRange, checkTime);
			int jobDuration = System.Math.Min(entryRemaining, needToFill - filled);

			if (jobDuration > 0)
			{
				var job = new Job
				{
					Name = entry.Activity,  // 스케줄의 Activity를 표시용 이름으로
					Action = "move",        // 해당 위치로 이동 (이미 있으면 머무름)
					RegionId = entry.Location.RegionId,
					LocationId = entry.Location.LocalId,
					Duration = jobDuration,
					TargetId = null
				};

				_jobs.AddLast(job);
				filled += jobDuration;
			}
		}
	}

	/// <summary>
	/// TimeRange 내에서 현재 시간부터 종료까지 남은 시간 계산
	/// </summary>
	private int CalculateRemainingInEntry(TimeRange range, int currentMinute)
	{
		if (range.SpansMidnight)
		{
			// 자정 넘는 경우
			if (currentMinute >= range.StartMinute)
			{
				// 시작 후 ~ 자정
				return (1440 - currentMinute) + range.EndMinute;
			}
			else
			{
				// 자정 후 ~ 종료
				return range.EndMinute - currentMinute;
			}
		}
		else
		{
			return range.EndMinute - currentMinute;
		}
	}

	/// <summary>
	/// 모든 Job 제거
	/// </summary>
	public void Clear()
	{
		_jobs.Clear();
	}

	/// <summary>
	/// 끝에 Job 추가
	/// </summary>
	public void AddLast(Job job)
	{
		if (job != null && job.Duration > 0)
		{
			_jobs.AddLast(job);
		}
	}

	/// <summary>
	/// Clear 후 삽입 - 기존 Job 모두 제거 후 새 Job 추가
	/// 플레이어처럼 스케줄이 없는 유닛용
	/// </summary>
	public void InsertWithClear(Job job)
	{
		_jobs.Clear();
		if (job != null && job.Duration > 0)
		{
			_jobs.AddLast(job);
		}
	}

	/// <summary>
	/// 전체 남은 시간 (모든 Job duration 합)
	/// </summary>
	public int TotalDuration
	{
		get
		{
			int total = 0;
			foreach (var job in _jobs)
			{
				total += job.Duration;
			}
			return total;
		}
	}

	public override string ToString()
	{
		if (_jobs.Count == 0) return "JobList (empty)";

		var sb = new System.Text.StringBuilder();
		sb.Append($"JobList ({_jobs.Count} jobs, {TotalDuration}분): ");

		int count = 0;
		foreach (var job in _jobs)
		{
			if (count > 0) sb.Append(" → ");
			sb.Append($"[{job.Name}:{job.Action} {job.Duration}분]");
			count++;
			if (count >= 3)
			{
				sb.Append(" ...");
				break;
			}
		}

		return sb.ToString();
	}
}
